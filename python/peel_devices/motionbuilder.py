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
import select
import time
from PeelApp import cmd


def receive_message(client_socket):
    try:
        message = client_socket.recv(1024)
        if not message:
            return False
        return message
    except:
        return False


class SocketThread(QtCore.QThread):

    state_change = QtCore.Signal(str)

    def __init__(self, host, port):
        super(SocketThread, self).__init__()
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.connected = False
        self.messages = []

    def close_socket(self):
        try:
            if self.connected:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.connected = False
        except OSError as e:
            print(e)

        try:
            self.socket.close()
        except OSError as e:
            print(e)

    def run(self):

        self.connected = False

        remaining = b''

        while self.running:

            if not self.connected:
                try:
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((self.host, self.port))
                except IOError as e:
                    cmd.writeLog(f"MOBU: Connection failed: {e}, retrying in 2 seconds...")
                    time.sleep(2)
                    continue

                self.connected = True
                self.state_change.emit("ONLINE")

            while self.running and self.connected:

                try:

                    read_list, _, err_list = select.select([self.socket], [], [self.socket], 2)

                    if self.socket in err_list:
                        cmd.writeLog("MOBU: Socket error - closing connection")
                        self.close_socket()
                        self.state_change.emit("OFFLINE")
                        break

                except select.error as e:
                    cmd.writeLog(f"MOBU: Select error: {e}")
                    self.close_socket()
                    self.state_change.emit("OFFLINE")
                    break

                if self.socket not in read_list:
                    continue

                try:
                    message = self.socket.recv(1024)
                except IOError as e:
                    cmd.writeLog("MOBU: recv error")
                    self.close_socket()
                    self.state_change.emit("OFFLINE")
                    break

                if not message:
                    cmd.writeLog("MOBU: error - no data")
                    self.close_socket()
                    self.state_change.emit("OFFLINE")
                    break

                if remaining:
                    message = remaining + message

                while True:
                    pos = message.find(b"\n")
                    if pos == -1:
                        remaining = message
                        break

                    line = message[:pos]
                    message = message[pos+1:]

                    cmd.writeLog("MOBU MESSAGE: " + message.decode('utf-8'))

                    if line == b'RECORDING':
                        self.state_change.emit("RECORDING")

                    if line == b'PLAYING':
                        self.state_change.emit("PLAYING")

                    if line == b'STOPPED':
                        self.state_change.emit("ONLINE")

        cmd.writeLog("MOBU: Thread finished")

    def send(self, msg):
        msg += "\n"
        if self.connected:
            self.socket.send(msg.encode("utf8"))

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
    def __init__(self, name="MotionBuilder"):
        super(MotionBuilderDevice, self).__init__(name)
        self.recording = None
        self.current_take = None
        self.socket_thread = None
        self.current_state = None
        self.host = "127.0.0.1"
        self.port = 8888

    @staticmethod
    def device():
        return "mobu-device"

    def as_dict(self):
        if self.socket_thread is None:
            return {'name': self.name,
                    'host': None,
                    'port': None}
        else:
            return {'name': self.name,
                    'host': self.socket_thread.host,
                    'port': self.socket_thread.port}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        return True

    def connect_device(self):
        self.teardown()
        self.socket_thread = SocketThread(self.host, self.port)
        self.socket_thread.start()
        self.socket_thread.state_change.connect(self.do_state)
        self.update_state("OFFLINE", "")

    def command(self, command, arg):

        if not self.enabled:
            return

        if command == "record":
            self.socket_thread.send("RECORD=" + arg)

        if command == 'stop':
            self.socket_thread.send("STOP")

        if command == 'play':
            self.socket_thread.send("PLAY=" + arg)

    def teardown(self):
        if self.socket_thread:
            self.socket_thread.teardown()
            self.socket_thread = None

    def do_state(self, state):
        self.current_state = state
        self.update_state(state, "")

    def get_state(self, reason=None):
        if self.socket_thread is None:
            return "ERROR"
        return self.current_state

    @staticmethod
    def dialog_class():
        return MobuDeviceWidget


