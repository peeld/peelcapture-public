from peel_devices import PeelDeviceBase, SimpleDeviceWidget
import socket
from PySide6 import QtWidgets, QtCore
from PeelApp import cmd
import struct
import time


class VCamListenThread(QtCore.QThread):

    message = QtCore.Signal(str, str)

    def __init__(self, listen_ip, listen_port, parent=None):
        super(VCamListenThread, self).__init__(parent)
        self.host = listen_ip
        self.port = listen_port
        self.listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.info = None

    def stop(self):
        self.running = False
        self.listen.close()

    def run(self):

        try:
            self.listen.bind((self.host, self.port))
        except IOError as e:
            cmd.writeLog(f"Could not bind to {self.host}:{self.port}")
            self.running = False
            raise e

        self.running = True

        cmd.writeLog(f"VCAM listening on {self.host}:{self.port}")

        while self.running:
            try:
                data, remote = self.listen.recvfrom(1024)
                self.message.emit(data.decode("ascii").strip('\x00'), str(remote[0]))

            except IOError as e:
                if not str(e).startswith("[WinError 10038]"):
                    raise e

        cmd.writeLog("VCAM UDP Stopped")

    def kill(self):
        self.running = False
        self.listen.close()
        self.listen = None


class VCamSocketThread(QtCore.QThread):

    state_change = QtCore.Signal()

    def __init__(self, host, port, record, play, parent=None):
        super(VCamSocketThread, self).__init__(parent)
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.status = "OFFLINE"
        self.info = None
        self.remote = None
        self.allow_record = record
        self.allow_play = play

    def stop(self):
        self.running = False

    def run(self):
        self.running = True

        while self.running:

            if self.socket is None:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.status = "OFFLINE"

            try:
                cmd.writeLog(f"VCAM Connecting to {self.host} {self.port}")
                self.socket.connect((self.host, self.port))
            except IOError as e:
                cmd.writeLog(str(e))
                self.state_change.emit()
                time.sleep(5)
                continue

            cmd.writeLog("VCAM has connected")

            self.status = "ONLINE"
            self.state_change.emit()

            while self.running:
                if not self.readone():
                    break

            self.socket.close()
            self.socket = None

    def readone(self):

        ret = self.socket.recv(2)
        if len(ret) != 2:
            return False
        sz = struct.unpack('H', ret)[0]

        if len == 0 or sz > 1024:
            return False

        command = self.socket.recv(sz).strip(b'\0').decode('ascii')

        cmd.writeLog(f"VCAM COMMAND: {command}")

        if self.allow_record:
            if command == "record":
                cmd.record()

            if command == "recordstop":
                cmd.stop()

        if self.allow_play:
            if command == "play":
                cmd.play()

            if command == "playstop":
                cmd.stop()

        if command == "prev":
            cmd.prev()

        if command == "next":
            cmd.next()

        return True

    def send(self, message):
        self.socket.send((message + "\n").encode('utf8'))


class VCamDialog(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "PeelVCam", has_host=True, has_port=True,
                         has_broadcast=False, has_listen_ip=True, has_listen_port=True)

        self.record_cb = QtWidgets.QCheckBox("Record", self)
        self.play_cb = QtWidgets.QCheckBox("Play", self)
        self.form_layout.addRow("", self.record_cb)
        self.form_layout.addRow("", self.play_cb)

    def populate_from_device(self, device):
        super().populate_from_device(device)

        self.record_cb.setChecked(device.allow_record)
        self.play_cb.setChecked(device.allow_play)

    def update_device(self, device, data=None):

        data = {
            'record': self.record_cb.isChecked(),
            'play': self.play_cb.isChecked()
        }
        super().update_device(device, data)


class VCam(PeelDeviceBase):

    def __init__(self, name="PeelVCam"):
        super(VCam, self).__init__(name)
        self.recording = False
        self.playing = False
        self.host = "192.168.1.100"
        self.port = ""
        self.socket_thread = None
        self.listen_thread = None
        self.allow_record = None
        self.allow_play = None
        self.listen_ip = None
        self.listen_port = 9158


    @staticmethod
    def device():
        return "peelvcam"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'record': self.allow_record,
                'play': self.allow_play}

    def reconfigure(self, name, **kwargs):

        self.name = name

        self.allow_record = kwargs.get('record')
        self.allow_play = kwargs.get('play')
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.listen_ip = kwargs.get('listen_ip')
        self.listen_port = kwargs.get('listen_port')

    def device_connect(self):

        if self.host and self.port:
            self.socket_thread = VCamSocketThread(self.host, self.port, self.allow_record, self.allow_play)
            self.socket_thread.state_change.connect(self.do_state)
            self.socket_thread.start()

        if self.listen_thread is not None:
            self.listen_thread.kill()
            self.listen_thread.wait()
            del self.listen_thread
            self.listen_thread = None

        if self.listen_ip is not None and self.listen_port is not None:
            self.listen_thread = VCamListenThread(self.listen_ip, self.listen_port)
            self.listen_thread.message.connect(self.do_message)
            self.listen_thread.start()

        if self.listen_thread:
            # Use the listen thread socket so the from address is set
            self.udp = self.listen_thread.listen

        self.update_state()

    def do_state(self):
        self.update_state()

    def do_message(self, message, host):
        if self.socket_thread is None and message.startswith("VCAM:"):
            self.reconfigure(name=self.name,
                             host=host,
                             port=int(message[5:]),
                             listen_ip=self.listen_ip,
                             listen_port=self.listen_port,
                             record=self.allow_record,
                             play=self.allow_play)

    def __str__(self):
        return self.name

    def get_info(self):
        return ""

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"    """

        if not self.enabled:
            return "OFFLINE"

        if self.socket_thread is None:
            return "OFFLINE"

        if self.socket_thread.status == "OFFLINE":
            return "OFFLINE"

        if self.recording:
            return "RECORDING"
        else:
            return "ONLINE"

    def send(self, message):
        if self.socket_thread is not None:
            self.socket_thread.send(message)

    def command(self, command, argument):
        """ Confirm recording without actually doing anything """

        if command == "play":
            self.playing = True
            self.update_state()
            self.send("TRANSPORT-PLAY")

        if command == "record":
            self.recording = True
            self.update_state()
            self.send("TRANSPORT-RECORD")

        if command == "stop":
            self.recording = False
            self.update_state()
            self.send("TRANSPORT-STOP")

        if command == "recording-ok":
            self.send("TRANSPORT-RECORD-OK")

        if command == "play":
            self.send("TRANSPORT-PLAY")
            if self.udp:
                self.udp.sendto(b"TRANSPORT-PLAY", (self.host, self.port))

        # print(command)

    def teardown(self):
        """ Device is being deleted, shutdown gracefully """
        if self.socket_thread:
            self.socket_thread.stop()
            self.socket_thread.join()
            self.socket_thread = None

        if self.listen_thread:
            self.listen_thread.stop()
            self.listen_thread.join()
            self.listen_thread = None
        pass

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        if self.socket_thread:
            self.socket_thread.join()

        if self.listen_thread:
            self.listen_thread.join()

    @staticmethod
    def dialog_class():
        """ Return a edit widget to be used in the Add Dialog ui """
        return VCamDialog

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return False

    def harvest(self, directory, all_files):
        """ Copy all the take files from the device to directory """
        pass

