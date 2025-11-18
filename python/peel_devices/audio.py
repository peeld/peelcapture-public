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
from PySide6 import QtWidgets, QtNetwork, QtGui, QtCore
from PeelApp import cmd


class AddWidget(BaseDeviceWidget):
    def __init__(self, settings):
        super(AddWidget, self).__init__(settings)

        form_layout = QtWidgets.QFormLayout()

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-audio/'
        msg = "<P>Audio device settings are configured in the File->Settings menu</P>\n"
        msg += "<P>If ltc timecode is being used, it will be be recoded in the audio file as a channel</P>"
        msg += '<P>More information: <A HREF="' + link + '">Documentation</A></P>'

        self.set_info(msg)

        # Name
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setText(settings.value("audioname"))
        form_layout.addRow("Name", self.name_input)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        self.name_input.setText(device.name)

    def update_device(self, device):
        device.name = self.get_name()
        return True

    def get_name(self):
        return self.name_input.text()

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("audioname", self.get_name())
        return True


class Audio(PeelDeviceBase):
    def __init__(self, name="Audio"):
        super(Audio, self).__init__(name)
        self.state = "ONLINE"

    @staticmethod
    def device():
        return "audio"

    def as_dict(self):
        return {'name': self.name}

    def __str__(self):
        return f"audio: {self.name}"

    def get_state(self, reason=None):
        if not self.enabled:
            return "OFFLINE"
        return self.state

    def get_info(self, reason=None):
        return ""

    def reconfigure(self, **kwargs):
        pass

    def connect_device(self):
        pass

    def teardown(self):
        pass

    def command(self, command, argument):
        if command == "record":
            cmd.startAudioRecording(self.name, argument)
            # Main app will call recording_started() if the file is created okay

        if command == "stop":
            cmd.stopAudioRecording()
            self.state = "ONLINE"
            self.update_state(self.state, "")

    @staticmethod
    def dialog_class():
        return AddWidget

    def recording_started(self):
        """ called by the main app when audio recording starts okay """
        self.state = "RECORDING"
        self.update_state("RECORDING", "")

    def recording_failed(self, msg):
        """ called by the main app when audio recording starts okay """
        self.state = "ERROR"
        self.update_state("ERROR", msg)
