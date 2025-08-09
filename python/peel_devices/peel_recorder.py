# Copyright (c) 2022 Peel Software Development Inc
# All Rights Reserved.
#
# THIS SOFTWARE AND DOCUMENTATION ARE PROVIDED "AS IS" AND WITH ALL FAULTS AND DEFECTS WITHOUT WARRANTY OF ANY KIND. TO
# THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW, PEEL SOFTWARE DEVELOPMENT, ON ITS OWN BEHALF AND ON BEHALF OF ITS
# AFFILIATES AND ITS AND THEIR RESPECTIVE LICENSORS AND SERVICE PROVIDERS, EXPRESSLY DISCLAIMS ALL WARRANTIES, WHETHER
# EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, WITH RESPECT TO THE SOFTWARE AND DOCUMENTATION, INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT, AND WARRANTIES THAT MAY
# ARISE OUT OF COURSE OF DEALING, COURSE OF PERFORMANCE, USAGE, OR TRADE PRACTICE. WITHOUT LIMITATION TO THE FOREGOING,
# PEEL SOFTWARE DEVELOPMENT PROVIDES NO WARRANTY OR UNDERTAKING, AND MAKES NO REPRESENTATION OF ANY KIND THAT THE
# LICENSED SOFTWARE WILL MEET REQUIREMENTS, ACHIEVE ANY INTENDED RESULTS, BE COMPATIBLE, OR WORK WITH ANY OTHER
# SOFTWARE, APPLICATIONS, SYSTEMS, OR SERVICES, OPERATE WITHOUT INTERRUPTION, MEET ANY PERFORMANCE OR RELIABILITY
# STANDARDS OR BE ERROR FREE, OR THAT ANY ERRORS OR DEFECTS CAN OR WILL BE CORRECTED.
#
# IN NO EVENT WILL PEEL SOFTWARE DEVELOPMENT OR ITS AFFILIATES, OR ANY OF ITS OR THEIR RESPECTIVE LICENSORS OR SERVICE
# PROVIDERS, BE LIABLE TO ANY THIRD PARTY FOR ANY USE, INTERRUPTION, DELAY, OR INABILITY TO USE THE SOFTWARE; LOST
# REVENUES OR PROFITS; DELAYS, INTERRUPTION, OR LOSS OF SERVICES, BUSINESS, OR GOODWILL; LOSS OR CORRUPTION OF DATA;
# LOSS RESULTING FROM SYSTEM OR SYSTEM SERVICE FAILURE, MALFUNCTION, OR SHUTDOWN; FAILURE TO ACCURATELY TRANSFER, READ,
# OR TRANSMIT INFORMATION; FAILURE TO UPDATE OR PROVIDE CORRECT INFORMATION; SYSTEM INCOMPATIBILITY OR PROVISION OF
# INCORRECT COMPATIBILITY INFORMATION; OR BREACHES IN SYSTEM SECURITY; OR FOR ANY CONSEQUENTIAL, INCIDENTAL, INDIRECT,
# EXEMPLARY, SPECIAL, OR PUNITIVE DAMAGES, WHETHER ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT, BREACH OF
# CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, REGARDLESS OF WHETHER SUCH DAMAGES WERE FORESEEABLE AND WHETHER
# OR NOT THE LICENSOR WAS ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.


from peel_devices import PeelDeviceBase, DownloadThread, SimpleDeviceWidget, udp, tcp
from PySide6 import QtCore, QtNetwork
import json
import os
import struct
import hashlib

MAGIC_NUMBER = 0x45020003


class Parser(tcp.TcpBase, QtCore.QObject):

    PARSE_ERROR = -1
    KEEP_PARSING = 0
    NEED_DATA = 1

    # Device
    state_change = QtCore.Signal()
    state_disconnect = QtCore.Signal()
    state_connect = QtCore.Signal()

    # Harvest
    received_file_list = QtCore.Signal()
    file_is_done = QtCore.Signal(str)
    file_has_failed = QtCore.Signal(str)
    bytes_added = QtCore.Signal(int)

    def __init__(self, parent):
        super().__init__(parent)

        super().reconnect_timeout(3000)

        self.data = b''
        self.recording = False
        self.file_list = None

        # File transfer state
        self.current_file = None
        self.expecting_file = False
        self.file_code = None
        self.file_size = 0
        self.file_received = 0
        self.file_handle = None
        self.file_path = ""
        self.expected_hash = None
        self.hash_calc = hashlib.sha256()
        self.out_dir = None

    def reset(self):
        self.file_list = None
        self.current_file = None
        self.recording = False

    def do_connected(self):
        self.error = None
        super().do_connected()
        self.state_connect.emit()
        self.state_change.emit()

    def do_disconnected(self):
        super().do_disconnected()
        self.state_disconnect.emit()
        self.state_change.emit()

    def do_error(self, err):
        super().do_error(err)
        self.state_change.emit()

    def get_file_list(self, out_dir):
        print("Requesting file list")
        self.out_dir = out_dir
        self.send(110)

    def get_file(self, file_name):
        print("Transferring: " + str(file_name))
        self.current_file = file_name
        self.send(112, file_name)

    def do_read(self):

        """ Read bytes from the socket while they are available """
        while self.tcp.bytesAvailable():
            new_data = self.tcp.readAll().data()
            if new_data is None or len(new_data) == 0:
                continue

            if self.expecting_file:
                self._handle_file_data(new_data)
                continue

            self.data += new_data

            while True:

                if len(self.data) < 24:
                    # we have not received enough data yet, wait for self.data to fill up
                    break

                ret = self._parse_and_process_header()
                if ret is self.KEEP_PARSING:
                    continue
                if ret is self.NEED_DATA:
                    break
                if ret is self.PARSE_ERROR:
                    print("Closing")
                    self.tcp.close()
                    self.state_change.emit()
                    return

    def _handle_file_data(self, message: bytes) -> int:

        """ We are currently transferring a file """

        remaining = self.file_size - self.file_received
        to_write = min(len(message), remaining)

        if to_write > 0:
            self.write_file(message[:to_write])

        if self.file_received >= self.file_size:
            self.finish_file()

            if to_write < len(message):
                self.data = message[to_write:]

        return self.NEED_DATA

    def _parse_and_process_header(self):

        """ self.data has at least 24 bytes in it - we can process the header now """

        try:
            header = self.data[:24]
            magic, code, checksum, size, timestamp = struct.unpack('<IIIIQ', header)
        except struct.error:
            print("Invalid header format")
            # error and disconnect
            return self.PARSE_ERROR

        if magic != MAGIC_NUMBER:
            print(f"Bad header: {magic}")
            # error and disconnect
            return self.PARSE_ERROR

        if code == 113:
            if len(self.data) < 24 + 32:
                return True  # Wait for more data
            return self.start_file(size - 32)

        if len(self.data) < 24 + size:
            print("Waiting for full message")
            return self.KEEP_PARSING  # Wait for more data

        blob = self.data[24:24 + size]
        self.data = self.data[24 + size:]

        if code == 1:
            self.send(2)  # Heartbeat response
            # Continue parsing
            return self.KEEP_PARSING

        elif code == 11:
            # Command - ignored
            return self.KEEP_PARSING

        elif code == 12:
            # Property - ignored
            return self.KEEP_PARSING

        elif code == 100:
            print("Recording started")
            self.recording = True
            self.state_change.emit()
            return self.KEEP_PARSING

        elif code == 101:
            print("Recording stopped")
            self.recording = False
            self.state_change.emit()
            return self.KEEP_PARSING

        elif code == 111:
            print("Take list received")
            self.file_list = json.loads(blob)
            self.received_file_list.emit()
            return self.KEEP_PARSING

        print(f"Unknown code: {code}")
        return self.PARSE_ERROR

    def start_file(self, size):

        if self.current_file is None:
            print("No current file has been set")
            return self.PARSE_ERROR

        self.expected_hash = self.data[24:24+32]
        self.file_size = size
        self.file_received = 0
        self.hash_calc = hashlib.sha256()
        self.file_path = os.path.join(self.out_dir, self.current_file)

        print(f"Transfer {self.file_path} size: {size}")
        # print("Hash: " + ''.join(f'{b:02x}' for b in self.expected_hash))

        try:
            self.file_handle = open(self.file_path, 'wb')
        except IOError as e:
            print(f"Failed to open file for writing: {e}")
            self.file_has_failed.emit(self.current_file)
            self.file_handle = None

        if len(self.data) > 24+32:
            self.write_file(self.data[24+32:])

        # Reset data for next loop
        self.data = b''

        if self.file_received >= self.file_size:
            self.finish_file()
        else:
            self.expecting_file = True

        return self.NEED_DATA

    def write_file(self, file_data: bytes):

        # If were not able to open the file, but must keep reading it so we can skip it

        if self.file_handle is not None:
            self.hash_calc.update(file_data)
            self.file_handle.write(file_data)

        self.file_received += len(file_data)
        self.bytes_added.emit(len(file_data))

    def finish_file(self):

        if self.file_handle:
            self.file_handle.close()

        actual_hash = self.hash_calc.digest()

        okay = actual_hash == self.expected_hash

        # print("Hash A: " + ''.join(f'{b:02x}' for b in self.expected_hash))
        # print("Hash B: " + ''.join(f'{b:02x}' for b in actual_hash))
        # print("Okay  : " + str(okay))

        # slot below may overwrite
        current = self.current_file

        self.expecting_file = False
        self.expected_hash = None
        self.hash_calc = hashlib.sha256()
        self.file_handle = None
        self.current_file = None

        if okay:
            # print(f"File received and verified successfully: {self.file_path}")
            self.file_is_done.emit(current)
        else:
            print("Hash mismatch! File may be corrupted.")
            self.file_has_failed.emit(current)

    def send(self, code, message=None):

        if self.tcp.state() != QtNetwork.QAbstractSocket.ConnectedState:
            print("TCP not connected. Attempting to reconnect...")
            self.connect_tcp()
            return

        #if code > 2:
        #    print(f"SENDING {code} : {message}")

        if not self.tcp:
            print("No connection while sending")
            return False

        try:
            if message is None or len(message) == 0:
                self.tcp.write(struct.pack("<IIIIQ", MAGIC_NUMBER, code, 0, 0, 0))
                self.tcp.flush()
            else:

                encoded = message.encode('utf-8')
                self.tcp.write(struct.pack("<IIIIQ", MAGIC_NUMBER, code, 0, len(encoded), 0))
                self.tcp.write(encoded)
                self.tcp.flush()

                print(f"{code} {encoded}")
        except IOError as e:
            print("Error Sending: " + str(e))
            return False

        return True


class PeelRecordDownloadThread(DownloadThread):
    def __init__(self, directory, parser: Parser):
        super().__init__(directory)
        self.parser = parser
        self.parser.reset()
        self.current_index = 0

        parser.received_file_list.connect(self.got_file_list, QtCore.Qt.QueuedConnection)
        parser.file_is_done.connect(self.got_file, QtCore.Qt.QueuedConnection)
        parser.file_has_failed.connect(self.handle_file_failed, QtCore.Qt.QueuedConnection)
        parser.bytes_added.connect(self.handle_bytes_added, QtCore.Qt.QueuedConnection)
        self.directory = directory

    def handle_bytes_added(self, sz):
        self.add_bytes(sz)

    def got_file_list(self):

        device_files = self.parser.file_list["files"]

        self.files = []
        for file_item in device_files:
            if self.download_take_check(os.path.splitext(file_item)[0]):
                self.files.append(file_item)

        print(f"{len(self.files)} files to download of {len(device_files)}")
        if len(self.files) == 0:
            print("No files on device")
            self.set_finished()
        else:
            # Get started
            self.current_index = 0
            self.parser.get_file(self.files[0])

    def got_file(self, name):
        self.file_ok(name)
        self.do_next()

    def handle_file_failed(self, name):
        self.file_fail(name, "")
        self.do_next()

    def do_next(self):
        self.current_index += 1
        if self.current_index == len(self.files):
            self.set_finished()
            return

        self.parser.get_file(self.files[self.current_index])

    def process(self):
        # Called on a thread
        print("Peel Recorder starting to download " + str(self.directory))
        self.set_started()
        self.parser.get_file_list(self.directory)


class PeelRecorderWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "PeelRecorder", has_host=True, has_port=True,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class PeelRecorder(PeelDeviceBase):

    """ This device tests device functionality by running a thread when the device is in record mode
    The thread may run for 5 seconds and cause a failure state, or it may wait for a stop command.
    The thread and the device will both output some text to the log.
    """

    def __init__(self, name="PeelRecorder"):
        super().__init__(name)
        self.host = None
        self.port = 4455
        self.parser = None
        self.running = False
        self.udp_listener = udp.UdpBroadcastListener(self)
        self.udp_listener.packet_received.connect(self.handle_udp_packet, QtCore.Qt.QueuedConnection)

    def do_parser_disconnect(self):
        print("Disconnected")

    def do_parser_connect(self):
        print("Connected")

    def do_parser_state(self):
        self.update_state()

    def send_message(self, code, message):
        self.parser.send(code, message)

    def __str__(self):

        if not self.enabled:
            return ""

        if self.parser is None:
            return "Waiting"

        if self.parser.error:
            return self.parser.error

        if self.parser.recording:
            return "Recording"

        return ""

    def handle_udp_packet(self, message, host_ip, port):

        if self.parser is not None:
            return

        self.connect_to_recorder(host_ip, int(message[11:]))

    def connect_to_recorder(self, host, port):

        print(f"Connecting to {host} {port}")

        self.parser = Parser(self)
        self.parser.connect_tcp(host, port)
        self.parser.state_change.connect(self.do_parser_state, QtCore.Qt.QueuedConnection)
        self.parser.state_disconnect.connect(self.do_parser_disconnect, QtCore.Qt.QueuedConnection)
        self.parser.state_connect.connect(self.do_parser_connect, QtCore.Qt.QueuedConnection)
        self.update_state()

    @staticmethod
    def device():
        """ A unique name for the device - must be different for each subclasses of PeelDeviceBase.
            Used to populate the add-device dropdown dialog and to serialize the class/type """
        return "peelrecorder"

    def reconfigure(self, name,  **kwargs):
        self.name = name
        self.host = kwargs.get("host", "")
        self.port = kwargs.get("port", self.port)
        return True

    def connect_device(self):
        self.teardown()
        if not self.host:
            self.udp_listener.start(7007) # hardcoded udp port for peel capture broadcast udp
        else:
            self.connect_to_recorder(self.host, self.port)

    def teardown(self):
        """ Shutdown gracefully """
        self.udp_listener.stop()
        if self.parser:
            self.parser.close_tcp()

    def as_dict(self):
        """ Return the parameters to the constructor as a dict, to be saved in the peelcap file """
        return {'name': self.name, 'host': self.host, 'port': self.port}

    def get_info(self, reason=None):
        """ return a string to show the state of the device in the main ui """
        return str(self)

    def get_state(self, reason=None):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"
            avoid calling update_state() here.  Used to determine if this device
            is working as intended.
         """

        if not self.enabled:
            return "OFFLINE"

        if not self.parser:
            return "OFFLINE"

        if self.parser.recording:
            return "RECORDING"

        return self.parser.connected_state

    def command(self, command, argument):
        """ Respond to the app asking us to do something """

        if not self.enabled:
            return

        print("Peel Record Command: %s  Argument: %s" % (command, argument))

        if command == "record":
            self.send_message(50, argument)

        if command == "stop":
            self.send_message(51, argument)

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        #if self.server:
        #    self.server.wait(10)
        pass

    @staticmethod
    def dialog_class():
        return PeelRecorderWidget

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return True

    def harvest(self, directory):
        """ Copy all the take files from the device to directory """
        return PeelRecordDownloadThread(directory, self.parser)

    def list_takes(self):
        return []
