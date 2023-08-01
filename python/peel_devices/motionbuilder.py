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
from PySide6 import QtWidgets, QtNetwork, QtGui, QtCore
import socket
from select import select
import time
import threading
import traceback

"""
https://download.autodesk.com/us/motionbuilder/sdk-documentation/PythonSDK/classpyfbsdk_1_1_f_b_player_control.html
"""


class SocketThread(QtCore.QThread):

    state_change = QtCore.Signal()

    def __init__(self, host, port=4242):
        super(SocketThread, self).__init__()
        self.host = host
        self.port = port
        self.socket = None
        self.running = True
        self.messages = []
        self.error_flag = None
        self.message_sem = threading.Semaphore()
        self.is_init = True
        self.python_version = ""

    def tcp_connect(self):
        if self.socket is not None:
            self.tcp_disconnect()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.socket.setblocking(False)
        self.socket.settimeout(1)
        try:
            print(f"Connecting to mobu: {self.host} {self.port}")
            self.socket.connect((self.host, self.port))
        except socket.timeout:
            self.socket.close()
            self.socket = None
            self.state_change.emit()
            return False
        except IOError as e:
            print("Error connecting to motion builder")
            self.socket.close()
            self.socket = None
            self.state_change.emit()
            raise e

        self.send("from pyfbsdk import FBPlayerControl",
                  ("Python Scripting Console", "Copyright", "All rights reserved", "Python "))

        self.running = True
        return True

    def is_running(self):
        return self.running is True and self.socket is not None

    def tcp_disconnect(self):
        if self.socket is None:
            return

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
        except IOError as e:
            print("Error closing mobu socket: " + str(e))

        self.socket = None
        self.state_change.emit()

    def stop_thread(self):
        self.running = False
        self.message_sem.release()
        self.tcp_disconnect()

    def send(self, message, response=None):
        self.error_flag = False
        self.messages.append((message, response))
        self.message_sem.release()

    def send_(self):

        if self.socket is None:
            return

        if not self.messages:
            return

        command, expected_response = self.messages.pop(0)

        if expected_response is None:
            expected_response = []
        else:
            expected_response = list(expected_response)

        command += "\r\n"

        try:
            self.socket.send(command.encode("utf8"))
        except IOError as e:
            print("Mobu send error: " + str(e))
            self.tcp_disconnect()
            return

        timeout = 0
        while expected_response:

            # wait for a response (for 500ms)
            rd, _,  _ = select([self.socket], [], [], 0.5)

            if self.socket not in rd:
                timeout += 1
                if timeout > 4:
                    print("Mobu timed out waiting for: " + str(expected_response))
                    self.error_flag = True
                    self.state_change.emit()
                    break
                continue

            try:
                data = self.socket.recv(4096)

                # print("DATA:" + str(len(data)) + "~" + data.decode('ascii') + '~')

                for line in data.decode('ascii').split("\n"):

                    line = line.strip()

                    if len(line) == 0:
                        continue

                    if line == ">>>" or line == ">>> >>>":
                        continue

                    if self.is_init:
                        if line.startswith("Python "):
                            self.python_version = line[7:]
                        self.is_init = False

                    response = expected_response.pop(0)

                    if not line.startswith(response):
                        print("Invalid response from mobu, excepted: " + response)
                        print("Got: [" + line + "]")
                        print("Command was: " + command)
                        self.error_flag = True
                    else:
                        self.error_flag = False

                    if len(expected_response) == 0:
                        break

            except IOError as e:
                print(str(e))
                self.tcp_disconnect()
                return

        self.state_change.emit()

    def run(self):

        while self.running:

            if self.socket is None:
                if not self.tcp_connect():
                    time.sleep(5)
                    continue

            self.send_()

            if not self.messages:
                self.message_sem.acquire()

        self.tcp_disconnect()
        self.deleteLater()

    def stop(self):
        self.running = False


class MobuWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "MotionBuilder", has_host=True, has_port=False,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-motionbuilder/'
        msg = "<P><FONT COLOR=\"#f55\"><B>This device is deprecated and has problems with the latest versions of mobu</B><BR>"
        msg += "<B>Please install the Peel Capture MotionBuilder plugin and use the mobu-device now</FONT></B></P>"
        msg += '<P><A HREF="' + link + '">Documentation</A></P>'
        msg += "<P>Connects to motion builder on tcp port 4242.<BR>"
        msg += "<P>Records a new take and sets the take name</P>"

        self.set_info(msg)


class MotionBuilder(PeelDeviceBase):
    def __init__(self, name, host):
        super(MotionBuilder, self).__init__(name)
        self.host = host
        self.recording = None
        self.tcp = None
        self.reconfigure(name, host)
        self.current_take = None
        self.takename_timer = QtCore.QTimer(self)
        self.takename_timer.setInterval(1000)
        self.takename_timer.setSingleShot(True)
        self.takename_timer.timeout.connect(self.set_take_name)

    @staticmethod
    def device():
        return "mobu"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host}

    def command(self, command, arg):

        true_response = "True"

        if command == "play":
            self.tcp.send("print(FBPlayerControl().GotoStart())", (true_response,))
            self.tcp.send("print(FBPlayerControl().Play())", (true_response,))

        if command == "record":
            self.current_take = arg
            self.recording = True
            self.tcp.send("print(FBPlayerControl().GotoStart())", (true_response,))
            self.tcp.send("print(FBPlayerControl().Record(False))", (true_response,))
            self.tcp.send("print(FBPlayerControl().Play())", (true_response,))
            self.takename_timer.start()

        if command == "stop":
            self.tcp.send("FBSystem().CurrentTake.Name=\"" + self.current_take + "\"")
            self.tcp.send("print(FBPlayerControl().Stop())", (true_response,))
            self.recording = False

    def set_take_name(self):
        self.tcp.send("FBSystem().CurrentTake.Name=\"" + self.current_take + "\"")
        self.tcp.send("print(FBSystem().CurrentTake.Name)", (self.current_take,))

    @staticmethod
    def dialog(settings):
        dlg = MobuWidget(settings)
        return dlg

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        return MotionBuilder(widget.name.text(), widget.host.text())

    def reconfigure(self, name, host=None):

        self.name = name
        self.host = host

        if self.tcp:
            self.tcp.stop_thread()
            self.tcp.wait()

        self.tcp = SocketThread(self.host)
        self.tcp.start()
        self.tcp.state_change.connect(self.do_state)

        self.do_state()

    def do_state(self):
        self.update_state(self.get_state(), "")

    def edit(self, settings):
        dlg = MobuWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        # calls self.reconfigure()
        widget.update_device(self)

    def get_state(self):

        if not self.enabled:
            return "OFFLINE"

        if self.tcp is None or self.tcp.socket is None:
            return "OFFLINE"

        if self.tcp.error_flag is True:
            return "ERROR"

        if self.recording is True:
            return "RECORDING"
        else:
            return "ONLINE"

    def teardown(self):
        if self.tcp:
            self.tcp.stop_thread()
