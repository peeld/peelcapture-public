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


from PySide6 import QtWidgets, QtCore
from pythonosc import udp_client
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import peel_devices
from functools import partial
import time
from PeelApp import cmd


class OscListenThread(QtCore.QThread):

    state_changed = QtCore.Signal(str)

    def __init__(self, host, port):
        super(OscListenThread, self).__init__()
        self.setObjectName("OscListenThread")
        self.host = host
        self.port = port
        self.listen = None
        self.dp = None

    def register_callbacks(self):
        raise NotImplementedError

    def run(self):

        self.dp = Dispatcher()

        self.register_callbacks()

        # Start off line until we get a packet saying otherwise
        self.state_changed.emit("OFFLINE")

        try:
            self.listen = BlockingOSCUDPServer((self.host, self.port), self.dp)
        except OverflowError as e:
            print("OSC ERROR...")
            self.state_changed.emit("ERROR")
            raise e

        try:
            self.listen.serve_forever()
        except OSError as e:
            # Windows throws an error when the socket is closed, we can ignore it
            if not str(e).startswith("[WinError 10038]"):
                raise e

        print("OSC Server Stopped")

    def teardown(self):
        if self.listen:
            self.listen.shutdown()
            self.listen.server_close()



class OscListenThreadReaper(OscListenThread):
    def record_filter_handler(self, address, *args):
        # print(f"record: {address}: {args}")
        if len(args) == 2 and args[1] == 1.0:
            self.state_changed.emit("RECORDING")

    def stop_filter_handler(self, address, *args):
        # print(f"stop: {address}: {args}")
        if len(args) == 2 and args[1] == 1.0:
            self.state_changed.emit("STOP")

    def debug_filter_handler(self, address, *args):
        if not args:
            return

        # Skip common reaper commands from spamming the log
        if "/vu" in args[0] or args[0].startswith("/time") or args[0].startswith('/samples') or \
                args[0].startswith('/beat'):
            return

        self.state_changed.emit("ONLINE")
        #print(f"{address} {args}")

    def register_callbacks(self):
        self.dp.map("/record", partial(self.record_filter_handler, self))
        self.dp.map("/stop", partial(self.stop_filter_handler, self))
        self.dp.map("*", partial(self.debug_filter_handler, self))


class OscListenThreadUnreal(OscListenThread):
    def record_filter_handler(self, address, *args):
        self.state_changed.emit("RECORDING")

    def stop_filter_handler(self, address, *args):
        self.state_changed.emit("ONLINE")

    def register_callbacks(self):
        self.dp.map("/RecordStartConfirm", partial(self.record_filter_handler, self))
        self.dp.map("/RecordStopConfirm", partial(self.stop_filter_handler, self))
        self.dp.map("/UE4LaunchConfirm", partial(self.stop_filter_handler, self))


class Osc(peel_devices.PeelDeviceBase):
    def __init__(self, listen_class, name=None, host=None, port=None, broadcast=None, listen_ip=None,
                 listen_port=None, parent=None):
        super(Osc, self).__init__(name, parent)

        self.listen_class = listen_class

        # reconfigure sets these
        self.host = host
        self.port = port
        self.broadcast = broadcast
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self.slate = ""
        self.take = ""
        self.desc = ""
        self.listen_thread = None

        print("OSC Host: %s   Port: %s" % (str(host), str(port)))

        self.state = "ONLINE"
        self.is_recording = False

        self.client = None

        self.reconfigure(name, host=host, port=port, broadcast=broadcast,
                         listen_ip=listen_ip, listen_port=listen_port)

        #client_send("/RecordStart", ["slate", "take1", "my desc"] )

    @staticmethod
    def device():
        # Must be subclassed
        raise NotImplementedError

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'broadcast': self.broadcast,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port}

    def reconfigure(self, name, **kwargs):

        for i in ['host', 'port', 'broadcast', 'listen_ip', 'listen_port']:
            if i not in kwargs.keys():
                print(kwargs.keys())
                raise ValueError("Missing key for reconfigure: " + i)

        self.name = name
        self.host = kwargs['host']
        self.port = kwargs['port']
        self.broadcast = kwargs['broadcast']
        self.listen_ip = kwargs['listen_ip']
        self.listen_port = kwargs['listen_port']

        print("OSC Reconfigure: ", name, self.host, self.port, self.broadcast,
              self.listen_ip, self.listen_port)

        # Close the connections
        self.teardown()

        if self.host is not None and self.port is not None:
            self.client = udp_client.SimpleUDPClient(self.host, self.port,
                                                     allow_broadcast=self.broadcast)

        if self.listen_ip is not None and self.listen_port is not None:
            print("Staring OSC listen thread ", self.listen_ip, self.listen_port)

            if self.listen_thread:
                self.listen_thread.teardown()

            self.listen_thread = self.listen_class(self.listen_ip, self.listen_port)
            self.listen_thread.state_changed.connect(self.on_state, QtCore.Qt.QueuedConnection)
            self.listen_thread.start()

    def on_state(self, new_state):
        if new_state == "ONLINE" and self.is_recording:
            # Skip online messages while recording
            return

        if new_state == "STOP":
            new_state = "ONLINE"
        self.state = new_state
        self.update_state(new_state, "")

    def teardown(self):
        if self.client is not None:
            #self.client.client_close()
            self.client._sock.close()
            self.client = None

        if self.listen_thread:
            self.listen_thread.teardown()
            self.listen_thread.wait(1000)
            self.listen_thread = None

    def thread_join(self):
        pass

    def client_send(self, cmd, arg):
        try:
            print(f"OSC: {cmd} {arg}")
            self.client.send_message(cmd, arg)
        except OSError as e:
            self.on_state("ERROR")
            raise e
        except OverflowError as e:
            self.on_state("ERROR")
            raise e

    def command(self, command, argument):
        raise NotImplementedError

    def get_state(self):
        if not self.enabled:
            return "OFFLINE"
        return self.state

    def get_info(self):
        return ""


class ReaperWidget(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        super(ReaperWidget, self).__init__(settings, "Reaper", has_host=True, has_port=True,
                                           has_broadcast=True, has_listen_ip=True, has_listen_port=True)
        self.send_stop = QtWidgets.QCheckBox("Send Stop")
        self.send_stop.setChecked(settings.value("ReaperSendStop") == "true")
        self.form_layout.addRow("", self.send_stop)

        self.channels = QtWidgets.QLineEdit("Channels")
        self.channels.setText(settings.value("ReaperChannels"))
        self.form_layout.addRow("Channels", self.channels)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-reaper/'
        msg = '<P>More information <A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

    def populate_from_device(self, device):
        super().populate_from_device(device)
        self.send_stop.setChecked(device.send_stop is True)
        self.channels.setText(str(self.channels.text()))

    def update_device(self, device):
        if not super().update_device(device):
            return False
        device.send_stop = self.send_stop.isChecked()
        try:
            device.channels = int(self.channels.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid value for channels")
            return False
        return True

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("ReaperSendStop", self.send_stop.isChecked())
        self.settings.setValue("ReaperChannels", self.channels.text())
        return True


class Reaper(Osc):
    """ https://www.cockos.com/reaper/sdk/osc/osc.php """
    def __init__(self, name=None, host=None, port=8000, broadcast=None, listen_ip=None, listen_port=None,
                 send_stop=False, channels=0):
        super(Reaper, self).__init__(OscListenThreadReaper, name, host, port, broadcast, listen_ip, listen_port)
        self.send_stop = send_stop
        self.channels = channels

    @staticmethod
    def device():
        return "reaper"

    def as_dict(self):
        d = super().as_dict()
        d['channels'] = self.channels
        d['send_stop'] = self.send_stop
        return d

    @staticmethod
    def dialog(settings):
        return ReaperWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return
        ret = Reaper()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = ReaperWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)
        # widget.populate_from_device(self)

    def command(self, command, argument):
        if command == "stop":
            # Hack to stop the timeline from resetting
            self.client_send("t/pause", 1)

            if self.send_stop:
                time.sleep(0.01)
                # Stop recording
                self.client_send("t/stop", 1)

        if command == "record":
            # Create a marker and name it
            self.client_send("i/action", 40157)
            self.client_send("s/lastmarker/name", argument)

            for i in range(self.channels):
                # Set the first track name to the take name
                self.client_send(f"s/track/{i+1}/name", argument)

            # Start recording
            self.client_send("t/record", 1)


class UnrealDialog(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        super(UnrealDialog, self).__init__(settings, "Unreal", has_host=True, has_port=True,
                                           has_broadcast=True, has_listen_ip=True, has_listen_port=True)
        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-unreal-engine-4/'
        msg = '<P><A HREF="' + link + '">Documentation</A></P>'
        msg += "<P>Enable Switchboard and OSC plugins in Unreal</P>"
        msg += "<P>In the Unreal project settings, enable 'Start an OSC Server when the editor launches'</P>"
        msg += "<P>The 'OSC Server Address' listen port in unreal "
        msg += "Restart Unreal to enable the osc server"
        self.set_info(msg)


class Unreal(Osc):
    def __init__(self, name=None, host=None, port=None, broadcast=None, listen_ip=None, listen_port=None):
        super(Unreal, self).__init__(OscListenThreadUnreal, name, host, port, broadcast, listen_ip, listen_port)
        self.shot_name = None

    @staticmethod
    def device():
        return "unreal"

    @staticmethod
    def dialog(settings):
        return UnrealDialog(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        ret = Unreal()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = UnrealDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)

    def get_state(self):
        if not self.enabled:
            return "OFFLINE"
        if self.state == "OFFLINE":
            self.client_send("/OSCAddSendTarget", (self.listen_ip, self.listen_port))

        return super(Unreal, self).get_state()

    def command(self, command, argument):
        if command == "stop":
            # Stop recording
            self.is_recording = False
            self.client_send("/RecordStop", "")

        if command == "record":
            # Create a marker and name it
            self.is_recording = True  # used to block online messages
            self.client_send("/Slate", self.shot_name)
            self.client_send("/RecordStart", "")

        if command == "shotName":
            self.shot_name = argument

        if command == "takeNumber":
            try:
                self.client_send("/Take", int(argument))
            except ValueError as e:
                print("Invalid take number: " + str(argument))


# PEEL LISTENER

class OscListenThreadPeel(OscListenThread):

    def record_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC RECORD TRIGGER: " + str(args))
        cmd.record()

    def stop_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC STOP TRIGGER: " + str(args))
        cmd.stop()

    def play_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PLAY TRIGGER: " + str(args))
        cmd.play()

    def play_stop(self, *args):
        self.state_changed.emit("ONLINE")
        print("OSC PLAY STOP TRIGGER: " + str(args))
        cmd.stop()

    def mark_filter(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC MARK TRIGGER: " + str(args))
        cmd.createMark(args[1])

    def go_prev(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PREV: " + str(args))
        cmd.prev()

    def go_next(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC NEXT: " + str(args))
        cmd.next()

    def go_prevshot(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC PREV SHOT: " + str(args))
        cmd.prevShot()

    def go_nextshot(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC NEXT SHOT: " + str(args))
        cmd.nextShot()

    def go_shotload(self,  *args):
        self.state_changed.emit("ONLINE")
        print("OSC SHOT#: " + str(args))
        cmd.gotoShot(args[1])

    def default_handler(self, *args):
        self.state_changed.emit("ONLINE")
        print("DEFAULT")
        print(args)

    def register_callbacks(self):
        self.dp.map("/peel/transport/startrecord", self.record_filter)
        self.dp.map("/peel/transport/stoprecord", self.stop_filter)
        self.dp.map("/peel/transport/mark", self.mark_filter)
        self.dp.map("/peel/playback/play", self.play_filter)
        self.dp.map("/peel/playback/stop", self.play_stop)
        self.dp.map("/peel/playback/prev", self.go_prev)
        self.dp.map("/peel/playback/next", self.go_next)
        self.dp.map("/peel/shotlist/prev", self.go_prevshot)
        self.dp.map("/peel/shotlist/next", self.go_nextshot)
        self.dp.map("/peel/shotlist/shotload", self.go_shotload)
        self.dp.set_default_handler(self.default_handler)


class OscListenDialog(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        super(OscListenDialog, self).__init__(settings, "Osc Listen", has_host=True, has_port=True,
                                              has_broadcast=True, has_listen_ip=True, has_listen_port=True)


class OscListen(Osc):
    def __init__(self, name=None, host=None, port=None, broadcast=None, listen_ip=None, listen_port=None):
        super(OscListen, self).__init__(OscListenThreadPeel, name, host, port, broadcast, listen_ip, listen_port)
        self.shot_name = None

    @staticmethod
    def device():
        return "osclisten"

    @staticmethod
    def dialog(settings):
        dlg = OscListenDialog(settings)
        dlg.listen_port.setText(settings.value("osclistenPort", "6666"))
        return dlg

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        device = OscListen()
        widget.update_device(device)
        return device

    def edit(self, settings):
        dlg = OscListenDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)

    def command(self, command, argument):

        print(command, argument)
        if command == "record":
            self.is_recording = True  # blocks ONLINE osc status while recording
            self.update_state("RECORDING", "")
            self.client.send_message("/peel/transport/recording", True)
            self.client.send_message("/peel/shotdetail/take", argument)

        if command == "stop":
            self.is_recording = False
            self.update_state("ONLINE", "")
            self.client.send_message("/peel/transport/recording", False)
            self.client.send_message("/peel/transport/playing", False)

        if command == "shotName":
            self.client.send_message("/peel/shotdetail/shot", argument)

        if command == "takeName":
            self.client.send_message("/peel/shotdetail/take", argument)

        if command == "takeId":
            self.client.send_message("/peel/shotdetail/id", argument)

        if command == "description":
            self.client.send_message("/peel/shotdetail/description", argument)

        if command == "notes":
            self.client.send_message("/peel/shotdetail/notes", argument)

        if command == "play":
            self.client.send_message("/peel/playback/takename", argument)
            self.client.send_message("/peel/transport/playing", True)

        if command == "shotNumber":
            self.client.send_message("/peel/shotlist/current", int(argument))

        if command == "selectedTake":
            self.client.send_message("/peel/playback/takename", argument)

