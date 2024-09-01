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

from PeelApp import cmd
from PySide6 import QtWidgets
import urllib.parse, urllib.request
import re
import os.path
from peel_devices import PeelDeviceBase, SimpleDeviceWidget, DownloadThread, FileItem
import json
import re

# http://192.168.15.151/descriptors

def format_take_name(name):
    #return name.replace('_', '-').replace(' ', '-')
    return re.sub(r'[^a-zA-Z0-9\-]', '-', name)


class DisguiseDialog(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Disguise", has_host=True, has_port=False,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)

        link = "https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-disguise/"
        msg = '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

        self.cb_prefix_device_name = QtWidgets.QCheckBox("")
        self.form_layout.addRow("Prefix Device Name", self.cb_prefix_device_name)
        self.cb_prefix_device_name.setChecked(settings.value(self.title + "PrefixDeviceName") == "True")

    def populate_from_device(self, device):
        super().populate_from_device(device)
        self.cb_prefix_device_name.setChecked(bool(device.prefix_device_name))

    def update_device(self, device, data=None):
        data = {'prefix_device_name': self.cb_prefix_device_name.isChecked()}
        return super().update_device(device, data)

    def do_add(self):
        if not super().do_add():
            return None

        self.settings.setValue(self.title + "PrefixDeviceName", self.cb_prefix_device_name.isChecked())

        return True


class Disguise(PeelDeviceBase):
    def __init__(self, name="Disguise"):
        super(Disguise, self).__init__(name)
        self.host = "192.168.1.100"
        self.error = None
        self.message = None
        self.enabled = True
        self.recording = False
        self.fp = None
        self.prefix_device_name = False
        self.currentShotName = None
        self.currentTake = 0

    @staticmethod
    def device():
        return "disguise"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'prefix_device_name': self.prefix_device_name}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get("host", None)
        self.prefix_device_name = kwargs.get("prefix_device_name", False)
        return True

    def __str__(self):
        msg = self.name
        if self.message is not None:
            msg += " - " + self.message
        return msg

    def teardown(self):
        pass

    def get_state(self, reason=None):

        if not self.enabled:
            return "OFFLINE"

        self.message = None

        if self.recording:
            return "RECORDING"

        print("Unknown state: ")
        return "ERROR"

    def get_info(self, reason=None):
        return self.message or ""

    def command(self, command, arg):

        if command in ['set_data_directory', "takeNumber", "takeName", 'recording-ok']:
            return

        if command in ["shotName"]:
            self.currentShotName = arg
            return

        if command == "record":
            if self.record(arg):
                self.recording = True
                self.update_state("RECORDING", "")
            return

        if command == "stop":
            if self.stop(arg):
                self.update_state("ONLINE", "")
            else:
                print("Could not stop")
                self.update_state("ERROR", "")
            return

        print("DISGUISE ignored the command:  " + str(command) + " " + str(arg))

    def record(self, take):
        if self.recording:
            return
        try:
            url = "http://" + self.host + "/shotrecorder/record"
            cmd.writeLog(url + "\n")
            data = json.dumps({
                "engage": True,
                "name": "peelcapture",
                "slate": self.currentShotName,
                "take": take
                })
            data = data.encode('utf-8')
            req = urllib.request.Request(url, data=data)
            f = urllib.request.urlopen(req, timeout=1, method="POST")
            resp = json.load(f.read())
            if resp['success']:
                url = "http://" + self.host + "/shotrecorder/recorders"
                cmd.writeLog(url + "\n")
                f = urllib.request.urlopen(url, timeout=1)
                resp = json.load(f.read())
                for i in resp['recorders']:
                    if i['name'] == "peelcapture" and i['enagaged']:
                        return True
            return False
        except Exception as e:
            print("DISGUISE ERROR: " + str(e))
            return None

    def stop(self, take=None):
        if not self.recording:
            return

        try:
            url = "http://" + self.host + "/shotrecorder/record"
            cmd.writeLog(url + "\n")
            data = json.dumps({
                "engage": False,
                "name": "peelcapture",
                "slate": self.currentShotName,
                "take": take
                })
            data = data.encode('utf-8')
            req =  urllib.request.Request(url, data=data)
            f = urllib.request.urlopen(req, timeout=1, method="POST")
            resp = json.load(f.read())
            if resp['success']:
                url = "http://" + self.host + "/shotrecorder/recorders"
                cmd.writeLog(url + "\n")
                f = urllib.request.urlopen(url, timeout=1)
                resp = json.load(f.read())
                for i in resp['recorders']:
                    if i['name'] == "peelcapture" and not i['enagaged']:
                        return True
            return False
        except Exception as e:
            print("DISGUISE ERROR: " + str(e))
            return None

    @staticmethod
    def dialog_class():
        return DisguiseDialog

    def connect_device(self):
        pass

    def list_takes(self):
        return []

        # This doesn't really work so commenting out for now....
        # ret = []
        # for i in self.clips():
        #     take = os.path.splitext(i['clipname'])[0]
        #     if take.endswith("_1"):
        #         take = take[:-2]
        #     ret.append(take)
        # return ret

###Authored at ZeroSpace.
