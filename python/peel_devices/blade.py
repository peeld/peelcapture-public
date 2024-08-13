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


import socket
import time
import select
import threading
from peel_devices import BaseDeviceWidget, device_util, PeelDeviceBase
from PySide6 import QtWidgets, QtNetwork, QtGui, QtCore
import sys

# import msvcrt

# run this first in blade:
#    client on -port 8011;

""" Vicon Blade device.  Uses blade's client/server connection, which is a bit of a hack """


class AddWidget(BaseDeviceWidget):
    def __init__(self, settings):
        super(AddWidget, self).__init__(settings)

        self.set_info("Don't use localhost/127.0.0.1 - blade needs to us a network address to connect,"
                      " even if running on the same pc")

        form_layout = QtWidgets.QFormLayout()

        # Interface
        self.combo = device_util.InterfaceCombo(True)
        self.combo.setCurrentText(self.settings.value("bladeinterface", None))
        form_layout.addRow("Listen Interface:", self.combo)
        form_layout.setSpacing(3)

        # Blade Ip
        blade_host_value = self.settings.value("bladehost", "192.168.1.100")
        self.blade_host = QtWidgets.QLineEdit()
        self.blade_host.setText(blade_host_value)

        form_layout.addRow("Blade IP:", self.blade_host)

        # delay
        delay_value = self.settings.value("bladedelay", 0)
        self.blade_delay = QtWidgets.QLineEdit()
        self.blade_delay.setText(str(delay_value))
        form_layout.addRow("Delay: ", self.blade_delay)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        self.blade_host.setText(device.blade_host)
        self.combo.setCurrentText(device.listen_ip)
        self.blade_delay.setText(str(device.delay))

    def update_device(self, device):
        device.blade_host = self.host()
        device.listen_ip = self.listen_interface()
        device.delay = self.delay()

    def host(self):
        return str(self.blade_host.text())

    def listen_interface(self):
        return self.combo.ip()

    def delay(self):
        value = self.blade_delay.text()
        try:
            return float(value)
        except ValueError as e:
            print(str(e))
        return 0.0

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("bladeip", self.host())
        self.settings.setValue("bladedelay", self.delay())
        self.settings.setValue("bladeinterface", self.listen_interface())

        return True


class ListenThread(QtCore.QThread):
    """ This is the listener thread that blade will connect to us on.  It is possible
        that more than one blade instance may connect to this port.  We can send commands
        to those instances.
    """

    state_change = QtCore.Signal()

    def __init__(self, host, port):
        super(ListenThread, self).__init__()
        self.state = None
        self.host = host
        self.port = port
        self.tcp = None

        self.sockets = []

    def stop(self):
        self.state = None
        for s, remote in self.sockets:
            s.shutdown(socket.SHUT_RDWR)
            s.close()

        # self.tcp.shutdown(socket.SHUT_RDWR)
        self.tcp.close()

    def run(self):

        self.state = "running"
        print("Starting blade listener on port %d" % self.port)
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setblocking(False)

        # Don't bind to self.host or blade won't be able to connect
        try:
            self.tcp.bind(("", self.port))
            self.tcp.listen()
        except OSError as e:
            print("Blade tcp error: " + str(e))
            self.error = str(e)
            return 

        while self.state is not None:
            try:
                socket_list = [self.tcp] + [i[0] for i in self.sockets]
                ready_to_read, ready_to_write, in_error = select.select(socket_list, [], [], 2)
                # print(ready_to_read, ready_to_write, in_error)
                if self.tcp in ready_to_read: 	

                    if self.tcp.fileno() == -1:
                        print("Socket has been closed")
                        self.state_change.emit()
                        break

                    print("Accepting a connection")
                    s, remote = self.tcp.accept()
                    print("Blade connection from: " + s.getsockname()[0])
                    if s:
                        self.sockets.append((s, remote))
                        self.state_change.emit()

                for s in ready_to_read:
                    if s is self.tcp:
                        continue
                    print("Blade replied: ")
                    while s.fileno() != -1:
                        data = s.recv(1024)
                        if len(data) == 0:
                            break
                        print(data)

            except BlockingIOError:
                pass

    def send(self, message):
        # print("sending message: " + message.decode("ascii"))
        for s, remote in self.sockets:
            # print("    to: " + str(remote))
            s.send(message)


class Blade(PeelDeviceBase):
    @staticmethod
    def device():
        return "blade"

    def __init__(self, name="Blade"):

        """ To connect to blade we must open up a port to listen on, then send
            a broadcast udp packet to tell blade to connect to our service.  Why
            can't we just connect to blade - that would be too easy!
            The broadcast_port value is the port number that blade is listening
            on.  Run the command "client on -port 8011" to start blade listening.
            The listen_port is the port that blade will connect to us on.  It
            can be any value.
            """

        super(Blade, self).__init__(name)
        self.listen_ip = "127.0.0.1"
        self.blade_host = "127.0.0.1"
        self.broadcast_port = 8811
        self.listen_port = 8026
        self.delay = 0.0

        self.record_timer = QtCore.QTimer()
        self.record_timer.setInterval(True)
        self.record_timer.timeout.connect(self.record)

        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.recording = False
        self.listener = None
        self.take_name = ""
        self.error = None

    def __str__(self):
        if self.listener:
            return self.name + " - Connections: " + str(len(self.listener.sockets))
        else:
            return self.name

    def as_dict(self):
        return {'name': self.name,
                'listen_ip': self.listen_ip,
                'blade_host': self.blade_host,
                'broadcast_port': self.broadcast_port,
                'listen_port': self.listen_port,
                'delay': self.delay}

    def reconfigure(self, name, **kwargs):

        self.name = name

        self.listen_ip = kwargs.get("listen_ip", None)
        self.blade_host = kwargs.get("blade_host", None)
        self.broadcast_port = kwargs.get("broadcast_port", None)
        self.listen_port = kwargs.get("listen_port", None)
        self.delay = kwargs.get("delay", 0)

        self.take_name = ""
        self.error = None

        return True

    def connect_device(self):

        if self.listener:
            self.listener.stop()
            self.listener.wait()
            self.listener = None

        if self.listen_ip and self.listen_port:
            self.listener = ListenThread(self.listen_ip, self.listen_port)
            self.listener.state_change.connect(self.update_state)
            self.listener.start()

        self.update_state()

    def teardown(self):
        self.udp.close()
        self.listener.stop()
        self.listener.wait()

    def get_state(self):
        if self.error is not None:
            return "ERROR"
        if not self.enabled:
            return "OFFLINE"
        if self.listener is None:
            return "OFFLINE"
        if len(self.listener.sockets) == 0:
            self.connect_blade()
            return "OFFLINE"
        if self.recording:
            return "RECORDING"
        return "ONLINE"

    def thread_join(self):
        self.listener.wait()

    def record(self):
        self.send(b'captureOptions -name "%s";\n' % self.take_name.encode('ascii'))
        self.send(b'capture;\n')
        self.recording = True

    def command(self, command, argument):
        if command == "record":
            self.take_name = argument
            if self.delay > 0.0:
                self.record_timer.setInterval(int(self.delay * 1000))
                self.record_timer.setSingleShot(True)
                self.record_timer.start()
            else:
                self.record()

        if command == "stop":
            self.send(b'capture -stop;\n')
            self.recording = False
        if command == "notes":
            #self.send(b'captureOptions -notes "%s";\n' % argument.encode('ascii'))
            pass
        if command == "description":
            #self.send(b'captureOptions -description "%s";\n' % argument.encode('ascii'))
            pass

    def connect_blade(self):
        """ Send a broadcast xml message to get blade to connect to us """
        host = socket.gethostname()
        print(f"Sending blade a connection request: IP: {self.listen_ip}  Computer: {host}  Port: {self.listen_port}")
        message = b'<?xml version="1.0" standalone="yes"?>'
        message += b'<DivaServer IPAddress="%s" ComputerName="%s" Port="%d" />\0' % \
                   (str.encode(self.listen_ip), str.encode(host), self.listen_port)
        # print(str(message), str(self.broadcast_port))
        try:
            self.udp.sendto(message, (self.blade_host, self.broadcast_port))
            self.error = None
        except OSError as e:
            print("Blade error sending udp: " + str(e))
            self.error = str(e)

    def send(self, message):
        print(message.decode("ascii"))
        cmd = b'<?xml version="1.0" standalone="yes" ?>'
        cmd += b'<DivaCommand ScriptText=\'%s\' />' % message.replace(b'"', b"&quot;")
        try:
            self.listener.send(cmd)
            self.error = None
        except OSError as e:
            print("Blade error sending tcp: " + str(e))
            print(str(e))
            self.error = str(e)
            self.update_state("ERROR", str(e))

    @staticmethod
    def dialog_class():
        return AddWidget

    def device_added(self, widget):
        msg = "client on -port %d;" % self.broadcast_port
        QtWidgets.QMessageBox.information(widget, "Blade", "Run this in blade: " + msg)
        QtGui.QGuiApplication.clipboard().setText(msg)

    def edit(self, settings):

        dlg = AddWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)

        msg = "client on -port %d;" % self.broadcast_port
        QtWidgets.QMessageBox.information(widget, "Blade", "Run this in blade: " + msg)
        QtGui.QGuiApplication.clipboard().setText(msg)

    def has_harvest(self):
        return False


def tester():

    listen_ip = "192.168.15.172"
    listen_port = 8030
    broadcast_port = 8022

    print("Run this in blade:")
    print("client on -port %d;" % broadcast_port)

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    message = b'<?xml version="1.0" standalone="yes" ?>'
    message += b'<DivaServer IPAddress="%s" ComputerName="%s" Port="%d" />' % \
               (str.encode(listen_ip), socket.gethostname(), listen_port)

    print(str(message))
    udp.sendto(message, ("255.255.255.255", broadcast_port))

    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.setblocking(False)
    tcp.bind((listen_ip, listen_port))
    tcp.listen()

    sockets = []

    while True:

        command = input()
        if command:
            if command == "exit":
                break

            for out_socket in sockets:
                cmd = b'<?xml version="1.0" standalone="yes" ?>'
                cmd += b'<DivaCommand ScriptText=\'%s\' />' % command.encode('ascii')
                print("Sending: " + str(cmd))
                out_socket.send(cmd)

        print("Select")

        rd, wr, er = select.select([tcp] + sockets, [], [], 2)
        if rd:
            for s in rd:
                if s == tcp:
                    print("ACCEPT")
                    remote, attr = tcp.accept()
                    remote.setblocking(False)
                    sockets.append(remote)
                else:
                    while True:
                        try:
                            data = s.recv(1024)
                            print("RECV " + str(len(data)) + " " + str(data))
                            if len(data) == 0:
                                break
                            print("BLADE: " + str(data))
                        except BlockingIOError:
                            break
                        print("loop")
                print("loop--")
        print("loop-")

    for s in sockets:
        s.shutdown(socket.SHUT_RDWR)
        s.close()

    tcp.close()


