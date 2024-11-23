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


# https://v21.wiki.optitrack.com/index.php?title=Data_Streaming#Remote_Triggering
# https://wiki.optitrack.com/index.php?title=NatNet:_Remote_Requests/Commands

from peel_devices import PeelDeviceBase, BaseDeviceWidget
from PeelApp import cmd
from PySide6 import QtWidgets, QtCore
import os, os.path


class MotiveDialog(BaseDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings)

        self.form_layout = QtWidgets.QFormLayout()

        self.setWindowTitle("Motive")
        self.setObjectName("Motive")

        self.name = QtWidgets.QLineEdit()
        self.name.setText(settings.value("MotiveName", "Motive"))
        self.form_layout.addRow("Name", self.name)

        self.connection_type = QtWidgets.QComboBox()
        self.connection_type.addItems(["Multicast", "Unicast"])
        self.connection_type.setCurrentText(settings.value("MotiveConnectionType"))
        self.form_layout.addRow("Connection Type", self.connection_type)

        self.command_port = QtWidgets.QLineEdit()
        self.command_port.setText(str(settings.value("MotiveCommandPort")))
        self.form_layout.addRow("Command Port", self.command_port)

        self.data_port = QtWidgets.QLineEdit()
        self.data_port.setText(str(settings.value("MotiveDataPort")))
        self.form_layout.addRow("Data Port", self.data_port)

        self.server_address = QtWidgets.QLineEdit()
        self.server_address.setText(settings.value("MotiveServerAddress"))
        self.form_layout.addRow("Server Address", self.server_address)

        self.local_address = QtWidgets.QLineEdit()
        self.local_address.setText(settings.value("MotiveLocalAddress"))
        self.form_layout.addRow("Local Address", self.local_address)

        self.multicast_address = QtWidgets.QLineEdit()
        self.multicast_address.setText(settings.value("MotiveMulticastAddress"))
        self.form_layout.addRow("Multicast Address", self.multicast_address)

        self.timecode = QtWidgets.QCheckBox()
        self.timecode.setChecked(self.settings.value("MotiveTimecode") == "True")
        self.form_layout.addRow("Timecode", self.timecode)

        self.subjects = QtWidgets.QCheckBox()
        self.subjects.setChecked(self.settings.value("MotiveSubjects") == "True")
        self.form_layout.addRow("Subjects", self.subjects)

        self.set_capture_folder = QtWidgets.QCheckBox()
        self.set_capture_folder.setChecked(self.settings.value("MotiveSetCaptureFolder") == "True")
        self.form_layout.addRow("Set Capture Folder", self.set_capture_folder)

        #link = "https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-optitrack-motive/"
        #msg = '<P><A HREF="' + link + '">Documentation</P>'
        #msg += '<P>Motive settings are configured in PeelCapture<BR>File->Settings->Motive(tab)</P>'
        self.set_info("Add a Naturalpoint Motion Device")

        self.setLayout(self.form_layout)

    def populate_from_device(self, device):

        self.name.setText(device.name)
        self.connection_type.setCurrentText(device.connection_type)
        self.command_port.setText(str(device.command_port))
        self.data_port.setText(str(device.data_port))
        self.server_address.setText(device.server_address)
        self.local_address.setText(device.local_address)
        self.multicast_address.setText(device.multicast_address)
        self.timecode.setChecked(device.timecode is True)
        self.subjects.setChecked(device.subjects is True)
        self.set_capture_folder.setChecked(device.set_capture_folder is True)

    def update_device(self, device, data=None):

        name = self.name.text()

        if data is None:
            data = {}

        try:
            data['connection_type'] = self.connection_type.currentText()
            data['command_port'] = int(self.command_port.text())
            data['data_port'] = int(self.data_port.text())
            data['server_address'] = self.server_address.text()
            data['local_address'] = self.local_address.text()
            data['multicast_address'] = self.multicast_address.text()
            data['timecode'] = self.timecode.isChecked()
            data['subjects'] = self.subjects.isChecked()
            data['set_capture_folder'] = self.set_capture_folder.isChecked()
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid data")
            return False

        return device.reconfigure(name, **data)

    def do_add(self):

        if not super().do_add():
            return False

        self.settings.setValue("MotiveName", self.name.text())
        self.settings.setValue("MotiveConnectionType", self.connection_type.currentText())
        self.settings.setValue("MotiveCommandPort", self.command_port.text())
        self.settings.setValue("MotiveDataPort", self.data_port.text())
        self.settings.setValue("MotiveServerAddress", self.server_address.text())
        self.settings.setValue("MotiveLocalAddress", self.local_address.text())
        self.settings.setValue("MotiveMulticastAddress", self.multicast_address.text())
        self.settings.setValue("MotiveTimecode", str(self.timecode.isChecked()))
        self.settings.setValue("MotiveSubjects", str(self.subjects.isChecked()))
        self.settings.setValue("MotiveSetCaptureFolder", str(self.set_capture_folder.isChecked()))

        return True


class OptitrackMotive(PeelDeviceBase):

    def __init__(self, name="Motive"):
        super(OptitrackMotive, self).__init__(name)

        self.set_capture_folder = None
        self.connection_type = "Muilticast"
        self.command_port = 1510
        self.data_port = 1511
        self.server_address = "127.0.0.1"
        self.local_address = "127.0.0.1"
        self.multicast_address = "239.255.42.99"
        self.timecode = True
        self.subjects = True

        self.plugin_id = cmd.createDevice("Motive")
        if self.plugin_id == -1:
            raise RuntimeError("Could not create motive device")

    @staticmethod
    def device():
        return "motive"

    def as_dict(self):
        return {
            'name': self.name,
            'connection_type': self.connection_type,
            'command_port': self.command_port,
            'data_port': self.data_port,
            'server_address': self.server_address,
            'local_address': self.local_address,
            'multicast_address': self.multicast_address,
            'timecode': self.timecode,
            'subjects': self.subjects,
            'set_capture_folder': self.set_capture_folder,
        }

    def reconfigure(self, name, **kwargs):

        self.name = name
        self.connection_type = kwargs.get('connection_type')
        self.command_port = kwargs.get('command_port')
        self.data_port = kwargs.get('data_port')
        self.server_address = kwargs.get('server_address')
        self.local_address = kwargs.get('local_address')
        self.multicast_address = kwargs.get('multicast_address')
        self.timecode = kwargs.get('timecode')
        self.subjects = kwargs.get('subjects')
        self.set_capture_folder = kwargs.get('set_capture_folder')

        cmd.writeLog(f"Connection Type: {self.connection_type}")
        cmd.writeLog(f"Command Port: {self.command_port}")
        cmd.writeLog(f"Data Port: {self.data_port}")
        cmd.writeLog(f"Server Address: {self.server_address}")
        cmd.writeLog(f"Local Address: {self.local_address}")
        cmd.writeLog(f"Multicast Address: {self.multicast_address}")
        cmd.writeLog(f"Timecode: {self.timecode}")
        cmd.writeLog(f"Subjects: {self.subjects}")
        cmd.writeLog(f"Set Capture Folder: {self.set_capture_folder}")

        config = ""
        try:
            if self.connection_type == "Multicast":
                config = "multicast=1\n"
            else:
                config = "multicast=0\n"

            config += f"commandPort={self.command_port}\n"
            config += f"dataPort={self.data_port}\n"
            config += f"serverAddress={self.server_address}\n"
            config += f"localAddress={self.local_address}\n"
            config += f"multicastAddress={self.multicast_address}\n"
            config += f"subjects={ int(self.subjects) }\n"
            config += f"timecode={ int(self.timecode) }\n"

            cmd.configureDevice(self.plugin_id, config)

            if self.set_capture_folder:
                cmd.deviceCommand(self.device_id, "SetDataDirectory:" + self.data_directory().replace("/", r'\\'))

        except Exception as e:
            cmd.writeLog("Motive could not connect: " + str(e))
            cmd.writeLog(config)

        return True

    def connect_device(self):
        pass

    def get_state(self, reason=None):
        """ Plugin will set the state """
        return ""

    def get_info(self, reason=None):
        """ Plugin will set the info """
        return ""

    def command(self, command, argument):
        """ Commands are handled by the plugin only """
        pass

    @staticmethod
    def dialog_class():
        return MotiveDialog

    def has_harvest(self):
        return False

    def teardown(self):
        cmd.deleteDevice(self.plugin_id)

    def list_takes(self):
        if self.data_directory() is None:
            return []
        if not os.path.isdir(self.data_directory()):
            return []

        ret = []
        for i in os.listdir(self.data_directory()):
            if i.lower().endswith(".tak"):
                ret.append(i[:-4])
        return ret
