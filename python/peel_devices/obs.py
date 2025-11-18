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


from peel_devices import PeelDeviceBase, BaseDeviceWidget
from PySide6 import QtWidgets, QtCore
from PeelApp import cmd

import os
import os.path
import asyncio
import simpleobsws


class ObsDeviceDialog(BaseDeviceWidget):
    """ A basic dialog for a device that has a name and an optional IP argument """
    def __init__(self, settings):
        super(ObsDeviceDialog, self).__init__(settings)
        form_layout = QtWidgets.QFormLayout()

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-obs/'
        msg = "<P>Use OBS version 28.x or above</P>"
        msg += "<P>Not compatible with older versions of obs with the websocket 4.x plugin</P>"
        msg += "<P>Valid fields for take name and directory:</P>"
        msg += "<P>&nbsp;-&nbsp;{takeName}, {shotName}, {shotTag}, {takeNumber}, {takeId}, {dataDirectory}, {deviceName}"
        msg += '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

        self.setWindowTitle("Obs")
        self.setObjectName("ObsDialog")

        self.name = QtWidgets.QLineEdit()
        self.name.setText(settings.value("ObsName", "Obs"))
        form_layout.addRow("Name", self.name)

        self.host = QtWidgets.QLineEdit()
        self.host.setText(settings.value("ObsHost", "127.0.0.1"))
        form_layout.addRow("Address", self.host)

        self.port = QtWidgets.QLineEdit()
        self.port.setText(settings.value("ObsPort", "4444"))
        form_layout.addRow("Port", self.port)

        self.password = QtWidgets.QLineEdit()
        self.password.setEchoMode(QtWidgets.QLineEdit.PasswordEchoOnEdit)
        self.password.setText(settings.value("ObsPassword", ""))
        form_layout.addRow("Password", self.password)

        self.take_format = QtWidgets.QLineEdit()
        self.take_format.setText(settings.value("ObsTakeFormat", ""))
        form_layout.addRow("Take Name Format", self.take_format)

        self.directory_name = QtWidgets.QLineEdit()
        self.directory_name.setText(settings.value("ObsDirectoryName", ""))
        form_layout.addRow("Directory Name", self.directory_name)

        self.set_folder = QtWidgets.QCheckBox("")
        self.set_folder.setChecked(settings.value("ObsSetFolder") == "True")
        form_layout.addRow("Set Capture Folder", self.set_folder)
        self.directory_name.setEnabled(self.set_folder.isChecked())
        self.directory_name.setStyleSheet("QLineEdit:disabled { background-color: #444;} ")

        self.set_folder.stateChanged.connect(self.set_folder_state)

        self.info = QtWidgets.QLabel()
        form_layout.addWidget(self.info)

        self.setLayout(form_layout)

    def set_folder_state(self, _):
        self.directory_name.setEnabled(self.set_folder.isChecked())

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.host.setText(device.host)
        self.port.setText(str(device.port))
        self.password.setText(device.password)
        self.take_format.setText(device.take_format)
        self.directory_name.setText(device.directory_name)
        self.set_folder.setChecked(device.set_folder is True)

    def update_device(self, device):

        """ Set the device properties from values in the ui """

        try:
            port = int(self.port.text())
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid port")
            return False

        args = {
            'name': self.name.text(),
            'host': self.host.text(),
            'port': port,
            'set_folder': self.set_folder.isChecked(),
            'password': self.password.text(),
            'directory_name': self.directory_name.text(),
            'take_format': self.take_format.text()
        }

        return device.reconfigure(**args)

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("ObsName", self.name.text())
        self.settings.setValue("ObsHost", self.host.text())
        self.settings.setValue("ObsPort", self.port.text())
        self.settings.setValue("ObsPassword", self.password.text())
        self.settings.setValue("ObsSetFolder", str(self.set_folder.isChecked()))
        self.settings.setValue("ObsDirectoryName", self.directory_name.text())
        self.settings.setValue("ObsTakeFormat", self.take_format.text())

        return True

    def get_name(self) -> str:
        return self.name.text()


class ObsDevice(PeelDeviceBase):

    def __init__(self, name="Obs"):
        super(ObsDevice, self).__init__(name)
        self.host = "127.0.0.1"
        self.port = 4444
        self.password = None
        self.conn = None
        self.info = ""
        self.state = "OFFLINE"
        self.last_command = None
        self.set_folder = False
        self.directory_name = ""
        self.fields = {}
        self.take_format = "{takeName}"

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs['host']
        self.port = kwargs['port']
        self.password = kwargs['password']
        self.set_folder = kwargs['set_folder']
        self.directory_name = kwargs.get('directory_name', '')
        self.take_format = kwargs.get('take_format', "{takeName}")
        self.state = "OFFLINE"
        return True

    def teardown(self):
        if self.conn is not None:
            self.conn.loop.run_until_complete(self.conn.disconnect())

    def connect_device(self):
        """ Create the obj object and do the async call """
        self.teardown()
        try:
            url = f'ws://{self.host}:{self.port}'
            print(f"Connecting to obs: {url}")
            self.conn = simpleobsws.WebSocketClient(url=url, password=self.password)
            self.info = ""
        except OSError as e:
            self.state = "OFFLINE"
            self.info = str(e)
            self.conn = None
            print("Could not connect to obs: " + str(e))
            return False

        try:
            self.conn.loop.run_until_complete(self.connect_async())
        except simpleobsws.NotIdentifiedError as e:
            self.info = "Could not connect"
            self.state = "OFFLINE"
            return False

        return True

    async def connect_async(self):
        """ async connect"""
        try:
            await self.conn.connect()
            await self.conn.wait_until_identified()
            result = await self.conn.call(simpleobsws.Request("GetVersion"))
            self.state = "ONLINE"
            return result
        except IOError as e:
            print("IO Error while connecting to obs: " + str(e))
            self.state = "OFFLINE"
            self.info = str(e)
        except asyncio.exceptions.TimeoutError as e:
            print("Timeout while connecting to obs: " + str(e))
            self.state = "OFFLINE"
            self.info = "Timeout"
        except simpleobsws.NotIdentifiedError as e:
            self.info = "Refused"
            self.state = "OFFLINE"
            return False
        except Exception as e:
            self.state = "ERROR"
            self.info = str(e)

    @staticmethod
    def device():
        return "obs"

    def as_dict(self):
        return {
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'password': self.password,
            'set_folder': self.set_folder,
            'directory_name': self.directory_name,
            'take_format': self.take_format
        }

    def __str__(self):
        return self.name

    def get_state(self, reason=None):
        if not self.enabled:
            return "OFFLINE"
        return self.state

    def get_info(self, reason=None):
        return self.info

    def thread_state_change(self):
        self.update_state()

    async def request(self, cmd, data):
        try:
            return await self.conn.call(simpleobsws.Request(cmd, data))
        except simpleobsws.MessageTimeout as e:
            print("OBS ERROR: " + str(e))
            self.state = "ERROR"
            self.info = str(e)
            return None

    async def cmd_sender(self, cmd, data=None):
        response = await self.request(cmd, data)

        if not response:
            return

        if response.ok():
            if self.last_command == 'record':
                self.state = "RECORDING"
                self.info = ""
                self.update_state("RECORDING", "")
                return

            self.state = "ONLINE"
            self.info = ""
            self.update_state("ONLINE", "")
            return

        if response.has_data():
            print("Unknown obs response.  CMD: " + str(cmd)
                  + "  DATA: " + str(response.responseData)
                  + "  RESULT: " + str(response.requestStatus.result))
        else:
            print("Unknown obs response.  CMD: " + str(cmd)
                  + "  RESULT: " + str(response.requestStatus.result))

        self.update_state("ERROR", "")

    def send(self, cmd, data=None):
        print("OBS SEND CMD: " + str(cmd) + " DATA:" + str(data))
        if self.conn is None:
            print("OBS Connecting")
            self.connect_device()
        if self.conn is None:
            print("OBS Could not connect")
            return

        if not self.conn.identified:
            print("OBS not identified")
            self.connect_device()
            return

        self.conn.loop.run_until_complete(self.cmd_sender(cmd, data))

    def command(self, command, argument):

        print(f" -- {command} {argument}")

        if command in ["takeName", "shotName", "shotTag", "takeNumber", "takeId"]:
            self.fields[command] = argument
            return

        # https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
        self.last_command = command
        if command == "record":

            if self.set_folder and self.directory_name:

                data_directory = self.directory_name

                self.fields["dataDirectory"] = cmd.getDataDirectory()
                self.fields["deviceName"] = self.name

                for k, value in self.fields.items():
                    key = '{' + k + '}'
                    data_directory = data_directory.replace(key, value)

                if not os.path.isdir(data_directory):
                    os.makedirs(data_directory)

                data = {'parameterCategory': 'SimpleOutput',
                        'parameterName': 'FilePath',
                        'parameterValue': data_directory}
                self.send("SetProfileParameter", data)

            take_name = self.take_format
            for k, value in self.fields.items():
                key = '{' + k + '}'
                take_name = take_name.replace(key, value)

            if not take_name:
                take_name = argument

            data = {
                'parameterCategory': 'Output',
                'parameterName': 'FilenameFormatting',
                'parameterValue': take_name
            }
            self.send("SetProfileParameter", data)
            self.send("StartRecord")
            return

        if command == "stop":
            self.send("StopRecord")
            return

    @staticmethod
    def dialog_class():
        return ObsDeviceDialog


