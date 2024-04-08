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

from peel_devices import PeelDeviceBase, SimpleDeviceWidget
from PySide6 import QtCore, QtWidgets
import socket

class SocketThread(QtCore.QThread):

    state_change = QtCore.Signal(str)

    def __init__(self, host, port):
        super(SocketThread, self).__init__()
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = True
        self.messages = []
        self.error_flag = None

    def run(self):

        while self.running:

            try:
                ret = self.socket.recvfrom(1024, 0)
            except IOError as e:
                self.state_change.emit("OFFLINE")
                print("offline")
                return

            if not ret:
                print(".")
                continue

            if ret[0] == b'RECORDING\x00':
                self.state_change.emit("RECORDING")

            if ret[0] == b'STOPPED\x00':
                self.state_change.emit("ONLINE")

            if ret[0] == b'HELLO\x00':
                self.state_change.emit("ONLINE")

    def send(self, msg):
        self.socket.sendto(msg.encode("utf8"), (self.host, self.port))

    def close_socket(self):

        if self.socket is None:
            print("Closing a closed socket")
            return

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        except IOError as e:
            print("Error closing Mobu Device socket: " + str(e))

    def teardown(self):
        self.close_socket()
        self.running = False
        self.wait(3000)


class MobuDeviceWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "MotionBuilderDevice", has_host=True, has_port=True,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-motionbuilder/'
        msg = '<P><A HREF="' + link + '">Documentation</A></P>'
        msg += "<P>Connects to Peel Capture Motion Builder Device</P>"
        msg += "<P>Requires the Peel Capture device to be installed in motion builder</P>"
        msg += "<P>Records a new take and sets the take name</P>"

        if self.port.text() == "":
            self.port.setText("8833")

        self.set_info(msg)


class MotionBuilderDevice(PeelDeviceBase):
    def __init__(self, name, host, port):
        super(MotionBuilderDevice, self).__init__(name)
        self.recording = None
        self.current_take = None
        self.udp = None
        self.current_state = None
        self.reconfigure(name, host, port)

    @staticmethod
    def device():
        return "mobu-device"

    def as_dict(self):

        if self.udp is None:
            return {'name': self.name,
                    'host': None,
                    'port': None}
        else:
            return {'name': self.name,
                    'host': self.udp.host,
                    'port': self.udp.port}

    def command(self, command, arg):

        if command == "record":
            self.udp.send("RECORD=" + arg)

        if command == 'stop':
            self.udp.send("STOP")

        if command == 'play':
            self.udp.send("PLAY")

    def reconfigure(self, name, host=None, port=None):

        self.name = name

        if self.udp:
            self.udp.running = False
            self.udp.close_socket()
            self.udp.wait()
            self.udp = None

        if host is None or port is None:
            return

        self.udp = SocketThread(host, port)
        self.udp.start()
        self.udp.state_change.connect(self.do_state)

        self.udp.send("PING")

        self.update_state("OFFLINE")

    def do_state(self, state):
        self.current_state = state
        self.update_state(state, "")

    def get_state(self):
        if self.udp is None:
            return "ERROR"
        return self.current_state

    @staticmethod
    def dialog(settings):
        return MobuDeviceWidget(settings)

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        d = MotionBuilderDevice(None, None, None)
        widget.update_device(d)
        return d

    def edit(self, settings):
        dlg = MobuDeviceWidget(settings)
        dlg.name.setText(self.name)
        if self.udp is None:
            dlg.host.setText("")
            dlg.port.setText("")
        else:
            dlg.host.setText(self.udp.host)
            dlg.port.setText(str(self.udp.port))
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        # calls self.reconfigure()

        try:
            port = int(widget.port.text())
            self.reconfigure(widget.name.text(), widget.host.text(), port)
        except ValueError as e:
            QtWidgets.QMessageBox.warning(widget, "Error", "Invalid port")
            return False

    def teardown(self):
        if self.udp is not None:
            self.udp.teardown()
