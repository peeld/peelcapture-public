from peel_devices import PeelDeviceBase, SimpleDeviceWidget
import socket

class ICloneWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(ICloneWidget, self).__init__(settings, "IClone", has_host=True, has_port=False,
                                           has_broadcast=False, has_listen_ip=False, has_listen_port=False,
                                           has_set_capture_folder=False)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-IClone/'
        msg = '<P><A HREF="' + link + '">Documentation</A></P>\nIClone listens on port 9212.'
        self.set_info(msg)

class IClone(PeelDeviceBase):
    def __init__(self, name="IClone", host=None):
        super(IClone, self).__init__(name)
        self.host = host
        self.port = 9212
        self.tcp = None
        self.state = "OFFLINE"
        self.info = None
        self.shot_name = None
        self.take_number = None
        self.connect_tcp()

    @staticmethod
    def device():
        return "IClone"

    def as_dict(self):
        return {'name': self.name, 'host': self.host}

    def connect_tcp(self):
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.settimeout(5.0)  # Set timeout for socket operations
        try:
            self.tcp.connect((self.host, self.port))
            self.state = "ONLINE"
        except socket.error as e:
            self.update_state("ERROR", f"Connection to {self.host} on port {self.port} failed: {e}")
            self.teardown()

    def __str__(self):
        return self.name

    def teardown(self):
        if self.tcp:
            self.tcp.close()
            self.tcp = None

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def send_tcp_command(self, command):
        try:
            self.tcp.sendall(command.encode('utf-8'))
            response = self.tcp.recv(4096)
            print(f"{self.name} response to '{command}': {response.decode()}")
        except socket.timeout:
            self.state = "ERROR"
            self.info = "TCP command timed out"
            print(f"{self.name} command '{command}' timed out")
        except Exception as e:
            self.state = "ERROR"
            self.info = str(e)
            print(f"{self.name} failed to '{command}': {e}")
        finally:
            self.update_state(self.state)

    def command(self, command, arg):
        print(f"IClone command: {command} arg: {arg}")
        self.info = None

        if command == "record":
            self.state = "RECORDING"
            self.send_tcp_command("Record")

        elif command == "stop":
            self.state = "ONLINE"
            self.send_tcp_command("Stop")

        elif command == "takeName":
            self.take_name = arg

        elif command == "shotName":
            self.shot_name = arg

        elif command == "takeNumber":
            self.take_number = arg

    @staticmethod
    def dialog(settings):
        return ICloneWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return
        return IClone(widget.name.text(), widget.host.text())

    def edit(self, settings):
        dlg = ICloneWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)

    def reconfigure(self, name, host=None):
        self.name = name
        self.host = host
        self.connect_tcp()
