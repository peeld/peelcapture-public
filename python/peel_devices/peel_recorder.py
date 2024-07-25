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
from PySide6 import QtWidgets, QtCore
from PeelApp import cmd

import time
import random
import socket
import select
import struct


class SocketThread(QtCore.QThread):

    state_change = QtCore.Signal()

    def __init__(self):
        super(SocketThread, self).__init__()
        self.host = None
        self.port = None
        self.running = False
        self.error_flag = None
        self.connected_flag = False
        self.socket = None
        self.active_flag = False
        self.recording_flag = False

    def __str__(self):
        if self.active_flag:
            return "active"

        if self.connected_flag:
            return "connected"

        return "disconnected"

    def tcp_start(self, host, port):
        print(f"Starting tcp by method {host} {port}")
        self.stop_thread()
        self.host = host
        self.port = port
        if host and port:
            self.start()

    def tcp_connect(self):

        if self.connected_flag:
            self.tcp_disconnect()

        if not self.host or not self.port:
            print(f"Invalid: host={self.host}  port={self.port}")
            return

        if self.socket is None:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.socket.setblocking(False)
            self.socket.settimeout(1)

        try:
            self.socket.connect((self.host, self.port))
        except socket.timeout:
            return False
        except IOError as e:
            print("Error connecting to Peel Recorder")
            self.tcp_disconnect()
            print(e)
            return False

        print(f"Connected to Reel Recorder: {self.host} {self.port}")
        self.connected_flag = True

        return True

    def is_running(self):
        return self.running is True

    def is_connected(self):
        return self.connected_flag

    def tcp_disconnect(self):

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        except IOError as e:
            print("Error closing peel recorder socket: " + str(e))

        self.connected_flag = False
        self.active_flag = False
        print("Closed connection to Peel Recorder")
        self.state_change.emit()

    def stop_thread(self):
        if self.running:
            self.running = False
            if self.connected_flag:
                self.tcp_disconnect()

    def run(self):

        print(f"TCP Thread started {self.host} {self.port}")

        self.running = True
        self.active_flag = False

        count = 0

        while self.running:

            if self.connected_flag is False:
                if not self.tcp_connect():
                    time.sleep(5)
                    continue

            try:
                ret, _, _ = select.select([self.socket], [], [], 2)
                if not ret:
                    count += 1
                    if count > 20:
                        self.tcp_disconnect()
                        continue
            except IOError as e:
                print("Error getting data from socket: " + str(e))
                self.tcp_disconnect()
                continue

            count = 0

            try:
                header = self.socket.recv(8)
                if not header:
                    print("Connection Closed")
                    self.tcp_disconnect()
                    continue
            except IOError as e:
                print("Error reading from socket: " + str(e))
                self.tcp_disconnect()
                continue

            # two bytes 0x4501, two bytes code, 4 bytes size of blob
            header_value = struct.unpack('<HHI', header)

            if header_value[0] != 0x4501:
                print("Bad header: " + str(header_value[0]))
                self.tcp_disconnect()
                continue

            if not self.active_flag:
                self.active_flag = True
                print("Connection is valid.")
                self.state_change.emit()

            if header_value[1] == 0x0003:
                # heartbeat request, send a confirmation
                self.send(0x0004)
                continue

            print('DATA: ' + hex(header_value[1]) + ' ' + hex(header_value[2]))

            if header_value[1] == 0x4001:
                self.recording_flag = True
                print("Recording confirmed")
                self.state_change.emit()

            if header_value[1] == 0x4002:
                self.recording_flag = False
                print("Stop confirmed")
                self.state_change.emit()

        print("Peel Recorder TCP has finished")

    def send(self, code, message=None):

        if code != 0x0004:
            print(f"SENDING: {code}  {message}")

        if not self.socket:
            return False

        try:
            if message is None or len(message) == 0:
                self.socket.send(struct.pack("<HHI", 0x4501, code, 0))
            else:

                encoded = message.encode('utf-8')
                self.socket.send(struct.pack("<HHI", 0x4501, code, len(encoded)))
                self.socket.send(encoded)
        except IOError as e:
            print("Error Sending: " + str(e))
            self.tcp_disconnect()
            return False

        return True


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
        super(PeelRecorder, self).__init__(name)
        self.tcp = None
        self.host = "127.0.0.1"
        self.port = 9005

    @staticmethod
    def device():
        """ A unique name for the device - must be different for each subclasses of PeelDeviceBase.
            Used to populate the add-device dropdown dialog and to serialize the class/type """
        return "peelrecorder"

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get("host")
        self.port = kwargs.get("port")

    def connect_device(self):
        self.teardown()

        if self.tcp is None:
            self.tcp = SocketThread()
            self.tcp.state_change.connect(self.thread_state_change)

        self.tcp.tcp_start(self.host, self.port)

    def teardown(self):
        """ Shutdown gracefully """

        if self.tcp:
            self.tcp.tcp_disconnect()
            self.tcp.stop_thread()
            self.tcp.wait()
            self.tcp = None

    def as_dict(self):
        """ Return the parameters to the constructor as a dict, to be saved in the peelcap file """
        return {'name': self.name, 'host': self.tcp.host, 'port': self.tcp.port}

    def __str__(self):
        return self.name

    def get_info(self):
        """ return a string to show the state of the device in the main ui """
        return str(self.tcp)

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"
            avoid calling update_state() here.  Used to determine if this device
            is working as intended.
         """

        if not self.enabled:
            return "OFFLINE"

        if not self.tcp:
            return "OFFLINE"

        if not self.tcp.active_flag:
            return "OFFLINE"

        if self.tcp.recording_flag:
            return "RECORDING"

        return "ONLINE"

    def thread_state_change(self):
        """ Push a state change to the app """
        self.update_state()

    def command(self, command, argument):
        """ Respond to the app asking us to do something """

        print("Peel Record Command: %s  Argument: %s" % (command, argument))

        if command == "record":
            self.tcp.send(0x8001, argument)

        if command == "stop":
            self.tcp.send(0x8002, argument)

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        if self.tcp:
            self.tcp.wait(10)

    @staticmethod
    def dialog_class():
        return PeelRecorderWidget

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return False

    def harvest(self, directory, all_files):
        """ Copy all the take files from the device to directory """
        pass

    def list_takes(self):
        return []
