from peel_devices import PeelDeviceBase, SimpleDeviceWidget
import socket
from PySide6 import QtWidgets, QtCore
from PeelApp import cmd

class VCamListenThread(QtCore.QThread):

    state_change = QtCore.Signal()

    def __init__(self, listen_ip, listen_port, parent=None):
        super(VCamListenThread, self).__init__(parent)
        self.host = listen_ip
        self.port = listen_port
        self.listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.status = "OFFLINE"
        self.info = None
        self.remote = None

    def run(self):

        try:
            self.listen.bind((self.host, self.port))
        except IOError as e:
            print(f"Could not bind to {self.host}:{self.port}")
            self.running = False
            raise e

        self.running = True

        print(f"VCAM listening on {self.host}:{self.port}")

        while self.running:
            try:
                last_status = self.status
                data, self.remote = self.listen.recvfrom(1024)
                command = data.decode("ascii").strip('\x00')

                print(f"VCAM: {self.remote} {command}")

                if command == "record":
                    cmd.record()

                if command == "recordstop":
                    cmd.stop()

                if command == "play":
                    cmd.play()

                if command == "playstop":
                    cmd.stop()

                if command == "prev":
                    cmd.prev()

                if command == "next":
                    cmd.next()

            except IOError as e:
                if not str(e).startswith("[WinError 10038]"):
                    raise e

        print("VCAM UDP Stopped")

    def kill(self):
        self.running = False
        self.listen.close()
        self.listen = None


class VCam(PeelDeviceBase):

    def __init__(self, name, host=None, port=None, listen_ip=None, listen_port=None):
        super(VCam, self).__init__(name)
        self.recording = False
        self.udp = None
        self.host = host
        self.port = port
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.listen_thread = None

        self.reconfigure(name, host, port, listen_ip, listen_port)

    @staticmethod
    def device():
        return "peelvcam"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port}

    def reconfigure(self, name, host=None, port=None, listen_ip=None, listen_port=None):

        print(f"VCAM: {host}:{port} {listen_ip}:{listen_port}")

        if self.udp is not None:
            self.udp.close()
            self.udp = None

        self.name = name
        self.host = host
        self.port = port
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        if self.listen_thread is not None:
            self.listen_thread.kill()
            self.listen_thread.wait()
            del self.listen_thread
            self.listen_thread = None
            self.udp = None

        if self.listen_ip is not None and self.listen_port is not None:
            self.listen_thread = VCamListenThread(self.listen_ip, self.listen_port)
            self.listen_thread.state_change.connect(self.do_state)
            self.listen_thread.start()

        if self.listen_thread:
            # Use the listen thread socket so the from address is set
            self.udp = self.listen_thread.listen

        self.update_state()

    def do_state(self):
        self.update_state()

    def __str__(self):
        return self.name

    def get_info(self):
        return ""

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"    """

        if not self.enabled:
            return "OFFLINE"

        if self.recording:
            return "RECORDING"
        else:
            return "ONLINE"

    def command(self, command, argument):
        """ Confirm recording without actually doing anything """

        if command == "play":
            self.playing = True
            self.update_state()
            if self.udp:
                self.udp.sendto(b"TRANSPORT-PLAY", (self.host, self.port))

        if command == "record":
            self.recording = True
            self.update_state()
            if self.udp:
                self.udp.sendto(b"TRANSPORT-RECORD", (self.host, self.port))

        if command == "stop":
            self.recording = False
            self.update_state()
            if self.udp:
                self.udp.sendto(b"TRANSPORT-STOP", (self.host, self.port))

        if command == "recording-ok":
            if self.udp:
                self.udp.sendto(b"TRANSPORT-RECORD-OK", (self.host, self.port))

        if command == "play":
            if self.udp:
                self.udp.sendto(b"TRANSPORT-PLAY", (self.host, self.port))


        print(command)

    def teardown(self):
        """ Device is being deleted, shutdown gracefully """
        pass

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        if self.thread:
            self.thread.join()

    @staticmethod
    def dialog(settings):
        """ Return a edit widget to be used in the Add Dialog ui """
        dlg = SimpleDeviceWidget(settings, "PeelVCam", has_host=True, has_port=True,
                                  has_broadcast=False, has_listen_ip=True, has_listen_port=True)
        dlg.listen_port.setText(settings.value("PeelVCamListenPort", "9158"))
        dlg.port.setText(settings.value("PeelVCamPort", "9160"))
        return dlg

    @staticmethod
    def dialog_callback(widget):
        """ Callback for dialog() widget - called when dialog has been accepted """
        if not widget.do_add():
            return

        device = VCam("")
        widget.update_device(device)
        return device

    def edit(self, settings):
        """ Return a widget to be used in the Add Dialog ui, when editing the device """
        dlg = SimpleDeviceWidget(settings, "PeelVCam", has_host=True, has_port=True,
                                 has_broadcast=False, has_listen_ip=True, has_listen_port=True)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        """ Callback for edit() widget - called when dialog has been accepted """
        if not widget.do_add():
            return

        widget.update_device(self)

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return False

    def harvest(self, directory, all_files):
        """ Copy all the take files from the device to directory """
        pass

