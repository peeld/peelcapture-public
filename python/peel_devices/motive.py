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

from peel_devices import PeelDeviceBase, SimpleDeviceWidget
from PeelApp import cmd
from PySide6 import QtWidgets, QtCore
import os, os.path


class MotiveDialog(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Motive", has_host=False, has_port=False,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False,
                         has_set_capture_folder=True)

        link = "https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-optitrack-motive/"
        msg = '<P><A HREF="' + link + '">Documentation</P>'
        msg += '<P>Motive settings are configured in PeelCapture<BR>File->Settings->Motive(tab)</P>'
        self.set_info(msg)


class OptitrackMotive(PeelDeviceBase):

    def __init__(self, name, set_capture_folder):
        super(OptitrackMotive, self).__init__(name)
        self.motive_state = None
        self.motive_msg = ""
        self.is_recording = False
        self.set_capture_folder = set_capture_folder

    @staticmethod
    def device():
        return "motive"

    def set_motive_state(self, state, msg):
        """ The main app calls this with true/false based on the result of sending a message """
        self.motive_state = state
        self.motive_msg = msg
        self.update_state()

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR" """
        if not self.enabled or self.motive_state is None:
            return "OFFLINE"

        if self.motive_state is False:
            return "ERROR"

        if self.is_recording:
            return "RECORDING"

        return "ONLINE"

    def get_info(self):
        return self.motive_msg

    def as_dict(self):
        return {'name': self.name, 'set_capture_folder': self.set_capture_folder}

    def command(self, command, argument):
        """ Respond to PeelCapture asking us to do something calls to cmd.motiveCommand are sent to motive using the
            natnet sdk "SendMessageAndWait" function.  Responses  are printed out to the console as ascii.
            When we get a response the main app will call peel.set_motive_status(True/False) -> set_motive_state(...)
        """

        if command == "record":
            if self.set_capture_folder:
                cmd.motiveCommand("SetCurrentSession," + self.data_directory().replace("/", r'\\'))
            cmd.motiveCommand("SetRecordTakeName," + argument)
            cmd.motiveCommand("StartRecording")
            self.is_recording = True

        if command == "stop":
            cmd.motiveCommand("StopRecording")
            self.is_recording = False

        if command == "play":
            cmd.motiveCommand("SetPlaybackTakeName," + argument)

    def reconfigure(self, name, set_capture_folder=False):
        self.name = name
        self.set_capture_folder = set_capture_folder

    @staticmethod
    def dialog(settings):
        return MotiveDialog(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        return OptitrackMotive(widget.name.text(), widget.set_capture_folder.isChecked())

    def edit(self, settings):
        dlg = MotiveDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)

    def has_harvest(self):
        return False

    def teardown(self):
        pass

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
