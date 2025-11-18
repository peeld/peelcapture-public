from peel_devices import PeelDeviceBase, SimpleDeviceWidget
from PeelApp import cmd

import socket
import threading

class UDPListenerTCPConnector:
    def __init__(self, device):
        self.device = device
        self.port = None
        self.running = False
        self.udp_socket = None
        self.tcp_sockets = []
        self.sockets_lock = threading.Lock()
        self._udp_thread = None
        self.connected_ips = set()
        self.connected_ips_lock = threading.Lock()

    def start(self, port):
        self.port = port
        self.running = True
        self._udp_thread = threading.Thread(target=self._udp_listen_loop, daemon=True)
        self._udp_thread.start()

    def stop(self):
        self.running = False

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass

        with self.sockets_lock:
            for sock in self.tcp_sockets:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                except:
                    pass
            self.tcp_sockets.clear()

        if self._udp_thread.is_alive():
            self._udp_thread.join(timeout=1)

        print("[System] Shutdown complete.")

    def _udp_listen_loop(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.bind(('', self.port))
        print(f"[Unreal] Listening for UDP packets on port {self.port}...")

        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(1024)
                ip_address = addr[0]

                with self.connected_ips_lock:
                    if ip_address in self.connected_ips:
                        continue
                    self.connected_ips.add(ip_address)

                print(f"[Unreal] Connecting to {ip_address}")
                threading.Thread(target=self._connect_tcp, args=(ip_address,), daemon=True).start()

                self.device.update_state("ONLINE")

            except Exception as e:
                if self.running:
                    print(f"[Unreal] Error receiving packet: {e}")
                break

    def _connect_tcp(self, ip_address):
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((ip_address, self.port))
            tcp_sock.settimeout(3.0)
            print(f"[TCP] Connected to {ip_address}:{self.port}")


            with self.sockets_lock:
                self.tcp_sockets.append(tcp_sock)

            # Info ui update
            self.device.update_state()

            threading.Thread(target=self._handle_tcp_connection, args=(tcp_sock, ip_address), daemon=True).start()

        except Exception as e:
            print(f"[TCP] Connection to {ip_address}:{self.port} failed: {e}")
            with self.connected_ips_lock:
                self.connected_ips.discard(ip_address)

    def _tcp_read(self, tcp_sock, sz):
        buffer = b''
        while len(buffer) < sz:
            chunk = tcp_sock.recv(sz - len(buffer))
            if not chunk:
                return None
            buffer += chunk
        return buffer

    def _handle_tcp_connection(self, tcp_sock, ip_address):
        try:
            with tcp_sock:
                while self.running:
                    # Ensure at least 2 bytes for size

                    buffer = self._tcp_read(tcp_sock, 2)
                    if buffer is None:
                        return

                    # Get message size
                    msg_size = int.from_bytes(buffer[:2], byteorder='little')

                    if msg_size == 0:
                        # heartbeat, can be ignored.
                        continue

                    buffer = self._tcp_read(tcp_sock, msg_size)
                    if buffer is None:
                        return

                    # Handle the complete message
                    self._handle_incoming_payload(buffer, ip_address)

        except Exception as e:
            print(f"[TCP] Connection to {ip_address} error: {e}")
        finally:
            with self.sockets_lock:
                if tcp_sock in self.tcp_sockets:
                    self.tcp_sockets.remove(tcp_sock)
            with self.connected_ips_lock:
                self.connected_ips.discard(ip_address)
            print(f"[TCP] Disconnected from {ip_address}")
            self.device.update_state()


    def _handle_incoming_payload(self, data: bytes, ip_address: str):
        """Process the complete payload received from a TCP peer."""
        try:
            print(f"[TCP] Received {len(data)} bytes from {ip_address}: {data}")

            if data == b"RECORDING_STARTED":
                # Record Okay
                self.device.set_recording(True)
                return

            if data == b"RECORDING_FAILED":
                # Error
                self.device.set_recording(False)
                return

            if data == b"STOPPED":
                # Stop Recording (none)
                self.device.set_recording(None)
                return

            if data.startswith(b'BINDINGS='):
                chars = []
                for binding in data[9:].decode('utf8').split('\t'):
                    if '|' not in binding:
                        continue

                    char, actor = binding.split('|')
                    chars.append(char)
                    cmd.setBinding(actor, char, False)

                cmd.setCharacters(chars)

            if data.startswith(b'ENABLE='):
                chars = []
                for item in data[8:].decode('utf8').split('\t'):
                    if '|' not in item:
                        continue

                    char, value = item.split('|')
                    chars.append(char)
                    cmd.setPerformerVisibility()

        except Exception as e:
            print(f"[TCP] Error handling payload from {ip_address}: {e}")

    def connection_count(self):
        with self.sockets_lock:
            return len(self.tcp_sockets)

    def is_active(self):
        return self.connection_count() > 0

    def send_to_all(self, message):
        """Send a message to all connected TCP sockets with a 2-byte little-endian size header."""
        if isinstance(message, str):
            payload = message.encode()
        elif isinstance(message, bytes):
            payload = message
        else:
            raise TypeError("Message must be str or bytes")

        size_header = len(payload).to_bytes(2, byteorder='little')
        full_message = size_header + payload

        dead = []
        for sock in self.tcp_sockets:
            try:
                sock.sendall(full_message)
            except:
                dead.append(sock)

        for sock in dead:
            sock.close()
            self.tcp_sockets.remove(sock)



class UnrealWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Unreal", has_host=False, has_port=True,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class Unreal(PeelDeviceBase):

    """ Connects to the Peel Core plugin in unreal. """

    def __init__(self, name="Unreal"):
        super().__init__(name)
        self.server = UDPListenerTCPConnector(self)
        self.thread = None
        self.port = 9159
        self.transport_state = None
        self.takes = []
        self.record_state = None

    def set_recording(self, value):
        self.record_state = value
        self.update_state()

    @staticmethod
    def device():
        return "unreal-tcp"

    def as_dict(self):
        return {'name': self.name, 'port': self.port}

    def reconfigure(self, name, **kwargs):
        """ Change the settings in the device. """
        self.name = name
        self.port = kwargs.get("port", "9159")
        if self.port is None:
            self.port = 9159
        return True

    def connect_device(self):
        """ Initialize the device"""
        self.thread = threading.Thread(target=self.server.start, args=[self.port], daemon=True)
        self.thread.start()

    def __str__(self):
        if self.thread is None:
            state = "stopped"
        else:
            state = str(self.thread)
        return self.name + " - " + state

    def get_info(self, reason=None):
        """ return a string to show the state of the device in the main ui """
        return str(f"Connections: {self.server.connection_count()}")

    def get_state(self, reason=None):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"
            avoid calling update_state() here.  Used to determine if this device
            is working as intended.
         """

        if not self.enabled:
            return "OFFLINE"

        if not self.server.is_active():
            return "OFFLINE"

        if self.record_state is True:
            return "RECORDING"

        if self.record_state is False:
            return "ERROR"

        return "ONLINE"

    def command(self, command, argument):
        """ Respond to the app asking us to do something """

        if not self.enabled:
            return

        if command == "takeNumber":
            self.server.send_to_all(f"TAKE={argument}")

        if command == "shotName":
            self.server.send_to_all(f"SLATE={argument}")

        if command == "record":
            self.server.send_to_all(f"RECORD={argument}")
            print(f"Recording take: {argument}")

        if command == "stop":
            self.server.send_to_all("STOP")
            print("Stopping")

        if command == "binding":
            self.server.send_to_all(f"BIND={argument}")

        if command == "enable":
            self.server.send_to_all(f"ENABLE={argument}")

    def teardown(self):
        """ Device is being deleted, shutdown gracefully """
        self.server.stop()

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        if self.thread:
            self.thread.join()

    @staticmethod
    def dialog_class():
        return UnrealWidget

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return False

    def harvest(self, directory):
        """ Copy all the take files from the device to directory """
        return None

    def list_takes(self):
        return None