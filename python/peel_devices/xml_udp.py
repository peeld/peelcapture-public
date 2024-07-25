import peel_devices
import socket
import threading
import xml.etree.ElementTree as et
from PySide6 import QtWidgets, QtCore


class XmlUdpListenThread(QtCore.QThread):

    state_change = QtCore.Signal()

    def __init__(self, listen_ip, listen_port, parent=None):
        super(XmlUdpListenThread, self).__init__(parent)
        self.host = listen_ip
        self.port = listen_port
        self.listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listen.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
        self.status = "OFFLINE"
        self.info = None

    def run(self):

        try:
            self.listen.bind((self.host, self.port))
        except IOError as e:
            print(f"Could not bind to {self.host}:{self.port}")
            self.running = False
            raise e

        self.running = True

        while self.running:
            try:
                last_status = self.status
                data, remote = self.listen.recvfrom(1024)

                print("-------XMLUDP-----------")
                print(data)

                self.info = ""

                tree = et.fromstring(data.strip(b"\0"))

                if tree.tag == "CaptureStart":
                    self.status = "RECORDING"

                elif tree.tag == "CaptureStop":
                    self.status = "ONLINE"

                elif tree.tag == 'CaptureStopAck':
                    self.status = "ONLINE"

                elif tree.tag == 'CaptureComplete':
                    self.status = "ONLINE"

                elif tree.tag == 'CaptureStartAck' and 'Result' in tree.attrib \
                        and 'Result' in tree.attrib:
                    if tree.attrib['Result'] == "TRUE":
                        self.status = "RECORDING"
                    else:
                        self.status = "ERROR"
                        self.info = tree.attrib['Reason']

                else:
                    print("Unknown tag: " + str(tree.tag))
                    self.status = "ERROR"

                if self.status != last_status:
                    self.state_change.emit()

            except IOError as e:
                if not str(e).startswith("[WinError 10038]"):
                    print("Error: " + str(e))

                self.status = "ERROR"
                self.state_change.emit()

        print("XML UDP Stopped")

    def kill(self):
        self.running = False
        self.listen.close()
        self.listen = None


class XmlUdpDeviceBase(peel_devices.PeelDeviceBase):

    """ Base class for devices that receive an xml udp packet to start and stop
        Sends the packet to a specific host and port.  Use host 255.255.255.255 for broadcast
    """

    def __init__(self, name):

        super(XmlUdpDeviceBase, self).__init__(name)

        self.host = "192.168.1.100"
        self.port = 1234
        self.broadcast = None
        self.listen_ip = None
        self.listen_port = 1234
        self.format = None
        self.packet_id = 0
        self.udp = None
        self.listen_thread = None
        self.error = None
        self.recording = False
        self.current_take = None
        self.set_capture_folder = False

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'broadcast': self.broadcast,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'fmt': self.format,
                'set_capture_folder': self.set_capture_folder}

    def reconfigure(self, name, **kwargs):

        print("XMLUDP Reconfigure")
        print(str((kwargs)))

        self.name = name

        if self.udp is not None:
            self.udp.close()
            self.udp = None

        self.current_take = None
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.broadcast = kwargs.get('broadcast')
        self.listen_ip = kwargs.get('listen_ip')
        self.listen_port = kwargs.get('listen_port')
        self.format = kwargs.get('fmt')
        self.set_capture_folder = kwargs.get('set_capture_folder')

    def connect_device(self):

        if self.listen_thread is not None:
            self.listen_thread.kill()
            self.listen_thread.wait()
            del self.listen_thread
            self.listen_thread = None

        if self.listen_ip is not None and self.listen_port is not None:
            self.listen_thread = XmlUdpListenThread(self.listen_ip, self.listen_port)
            self.listen_thread.state_change.connect(self.do_state)
            self.listen_thread.start()

        if self.host is not None and self.port is not None:
            if self.listen_thread:
                # Use the listen thread socket so the from address is set
                self.udp = self.listen_thread.listen
            else:
                self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if self.broadcast:
                self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.update_state()

    def do_state(self):
        self.update_state()

    def get_state(self):

        if not self.enabled:
            return "OFFLINE"

        if self.error is not None:
            return "ERROR"

        if self.listen_thread is not None:
            return self.listen_thread.status

        else:
            # Device does not have a listen thread, so just assume everything is peachy
            if self.recording:
                return "RECORDING"
            else:
                return "ONLINE"

    def get_info(self):
        if self.error is not None:
            return self.error
        if self.listen_thread is not None:
            return self.listen_thread.info
        return ""

    def __del__(self):
        self.teardown()

    def teardown(self):
        if self.udp is not None:
            self.udp.close()
            self.udp = None

        if self.listen_thread is not None and not self.listen_thread.isFinished():
            self.listen_thread.running = False
            self.listen_thread.listen.close()
            self.listen_thread.wait()

    def command(self, command, arg):
        if command == "record":
            self.capture_start(arg)
            self.recording = True
            self.update_state()
            return

        if command == "stop":
            self.capture_stop()
            self.recording = False
            self.update_state()
            return

        if command in ["play", "takeNumber", "takeName", "shotName", "shotTag", "description", "takeId"]:
            return None

        print(f"{self.name} ignored the command: {command} {arg}")

    def capture_stop(self):

        if self.format == "Blade":
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>'\
                  '<CaptureStop RESULT="SUCCESS">'\
                  '<Name VALUE="%s"/>' % self.current_take + \
                  '<DatabasePath VALUE="D:/DATA/BladeTesting/BladeTesting/Project 2/Capture day 1/Session 1/"/>'\
                  '<Delay VALUE="0"/>'\
                  '<PacketID VALUE="%d"/>' % self.packet_id + \
                  '</CaptureStop>'

        elif self.format == "Vicon":
            # https://docs.vicon.com/pages/viewpage.action?pageId=107479581
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + \
                    '<CaptureStop RESULT="SUCCESS">\n' + \
                    '    <Name VALUE="%s"/>\n' % self.current_take + \
                    '    <PacketID VALUE="%d"/>\n' % self.packet_id + \
                    '</CaptureStop>\n'

        elif self.format == "Optitrack":
            # https://v22.wiki.optitrack.com/index.php?title=Data_Streaming

            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + \
                  '<CaptureStop>' + \
                  '<Name VALUE="%s"/>' % self.current_take + \
                  '<SessionName VALUE=""/>' + \
                  '<Notes VALUE=""/>' + \
                  '<Assets VALUE=""/>' + \
                  '<Description VALUE=""/>' + \
                  '<DatabasePath VALUE=""/>' + \
                  '<TimeCode VALUE="00:00:00:00"/>' + \
                  '<PacketID VALUE="%d"/>' % self.packet_id + \
                  '<HostName VALUE="Motive"/>' + \
                  '<ProcessID VALUE="22236"/>' + \
                  '</CaptureStop>'

        elif self.format == "XSENS":
            # https://base.xsens.com/s/article/UDP-Remote-Control?language=en_US
            msg = '<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n'
            msg += '<CaptureStop>\n'
            msg += '<Notes></Notes>\n'
            msg += '</CaptureStop>\n'

        elif self.format == "Rokoko":
            # https://github.com/Rokoko/studio-command-api-examples/blob/master/README.md#trigger-messages
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' \
                + '<CaptureStop>' \
                + '<Name VALUE="%s"/>' % self.current_take \
                + '<TimeCode VALUE="00:00:00:00"/>' \
                + '<SetActiveClip VALUE="%s"/>' % str(self.enter_clip_editing) \
                + '<PacketID VALUE="%d"/>' % self.packet_id \
                + '<ProcessID VALUE="22236"/>' \
                + '</CaptureStop>'

        elif self.format == "Nansense":
            msg = '<CaptureStop>' \
                + '<Name VALUE="%s" />' % self.current_take \
                + '</CaptureStop>\n'

        else:
            msg = '<?xml version="1.0" encoding="utf-8" ?>\n' \
                + '<CaptureStop>\n' \
                + '      <Name VALUE="%s" />\n' % self.current_take \
                + '</CaptureStop>\n'

        self.send(msg)

    def capture_start(self, take):

        self.current_take = take

        if self.format == "Blade":
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + \
                  '<CaptureStart><Name VALUE="%s"/>' % self.current_take + \
                  '<Notes VALUE=""/>' + \
                  '<Description VALUE=""/>' + \
                  '<DatabasePath VALUE=""/>' + \
                  '<Delay VALUE="0"/>' + \
                  '<PacketID VALUE="%d"/>' % self.packet_id + \
                  '</CaptureStart>\0'

        elif self.format == "Vicon":
            # https://docs.vicon.com/pages/viewpage.action?pageId=107479581
            msg = '<CaptureStart>\n' + \
                    '    <Name VALUE="%s"/>\n' % self.current_take + \
                    '    <Notes VALUE=""/>\n' + \
                    '    <Description VALUE=""/>\n' + \
                    '    <Delay VALUE="33"/>\n' + \
                    '    <PacketID VALUE="%d"/>\n' % self.packet_id + \
                    '</CaptureStart>\n'

        elif self.format == "Optitrack":
            # https://v22.wiki.optitrack.com/index.php?title=Data_Streaming
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' + \
                  '<CaptureStart>' + \
                  '<Name VALUE="%s"/>' % self.current_take + \
                  '<SessionName VALUE=""/>' + \
                  '<Notes VALUE=""/>' + \
                  '<Assets VALUE=""/>' + \
                  '<Description VALUE=""/>' + \
                  '<DatabasePath VALUE=""/>' + \
                  '<TimeCode VALUE="00:00:00:00"/>' + \
                  '<PacketID VALUE="%d"/>' % self.packet_id + \
                  '<HostName VALUE="Motive"/>' + \
                  '<ProcessID VALUE="22236"/>' + \
                  '</CaptureStart>'

        elif self.format == 'XSENS':
            # https://base.xsens.com/s/article/UDP-Remote-Control?language=en_US
            msg = '<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n'
            msg += '<CaptureStart>\n'
            msg += f'<Name VALUE="{self.current_take}" />\n'
            if self.set_capture_folder:
                msg += '<DatabasePath VALUE="' + self.data_directory() + '" />\n'
            msg += '<TimeCode VALUE="" />\n'
            msg += '<Notes></Notes>\n'
            msg += '</CaptureStart>\n'

        elif self.format == "Rokoko":
            # https://github.com/Rokoko/studio-command-api-examples/blob/master/README.md#trigger-messages
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' \
                + '<CaptureStart>' \
                + '<Name VALUE="%s"/>' % self.current_take \
                + '<TimeCode VALUE="00:00:00:00"/>' \
                + '<PacketID VALUE="%d"/>' % self.packet_id \
                + '<ProcessID VALUE="22236"/>' \
                + '</CaptureStart>'

        elif self.format == "Nansense":
            msg = '<CaptureStart>' \
                + '<Name VALUE="%s" />' % self.current_take \
                + '</CaptureStart>'

        else:
            msg = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n' \
                + '<CaptureStart>\n' \
                + '\t<Name VALUE="%s"/>\n' % take \
                + '\t<PacketID VALUE="%d"/>\n' % self.packet_id \
                + '</CaptureStart>\n'

        self.send(msg)

    def send(self, msg):
        if self.udp is None:
            self.error = "No socket"
            print("No socket while trying to send error - " + self.name)

        print(f"UDP {self.host}  {self.port}  {self.format}")
        print(msg)

        try:
            self.udp.sendto(msg.encode("utf8"), (self.host, self.port))
        except OSError as e:
            print(f"Could not send to {self.host} {self.port} : " + str(e))
            self.error = str(e)
            self.update_state("ERROR", self.error)
            raise e
        except OverflowError as e:
            print(f"Could not send to {self.host} {self.port} : " + str(e))
            self.error = str(e)
            self.update_state("ERROR", self.error)
            raise e

        self.error = None

        self.packet_id += 1

    def thread_join(self):
        pass

    def has_harvest(self):
        return False


class AddXmlUdpWidget(peel_devices.SimpleDeviceWidget):
    def __init__(self, settings):
        super(AddXmlUdpWidget, self).__init__(settings, "XmlUdp", has_host=True, has_port=True,
                                              has_broadcast=True, has_listen_ip=True, has_listen_port=True,
                                              has_set_capture_folder=True)

        self.format_mode = QtWidgets.QComboBox()
        self.format_mode.addItems(["Vicon", "Optitrack", "XSENS", "Blade", "Rokoko", "Nansense"])
        self.format_mode.setCurrentText(settings.value(self.title + "Format", "Vicon"))
        self.form_layout.addRow("Format", self.format_mode)

    def populate_from_device(self, device):
        super(AddXmlUdpWidget, self).populate_from_device(device)
        self.format_mode.setCurrentText(device.format)

    def update_device(self, device, data=None):
        if data is None:
            data = {}
        data['fmt'] = self.format_mode.currentText()
        return super(AddXmlUdpWidget, self).update_device(device, data)

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue(self.title + "Format", self.format_mode.currentText())
        return True


class XmlUdpDevice(XmlUdpDeviceBase):

    """ A generic device that has a combo box to select the packet format """

    def __init__(self, name="XmlUdp"):
        super(XmlUdpDevice, self).__init__(name)

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'broadcast': self.broadcast,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'fmt': self.format}

    @staticmethod
    def device():
        return "xmludp"

    @staticmethod
    def dialog_class():
        return AddXmlUdpWidget
