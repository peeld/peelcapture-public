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

from peel_devices import SimpleDeviceWidget, PeelDeviceBase, DownloadThread, FileItem
from PySide6 import QtWidgets, QtCore
import requests
from requests.exceptions import ConnectionError, HTTPError
import json
import os


class FaceformCapture(PeelDeviceBase):
    def __init__(self, name="Capture"):
        super(FaceformCapture, self).__init__(name)

        self.host = ""
        self.port = 8088
        self.status = "OFFLINE"
        self.info = ""
        self.project = "Project"
        self.actor = "Actor"
        self.json_args = None
        self.takes = []

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'project': self.project,
                'actor': self.actor}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.project = kwargs.get('project')
        self.actor = kwargs.get('actor')

        return True

    def connect_device(self):
        self.check_connection()

    def refresh_status(self, status, message):
        self.info = status
        if message:
            self.status = "ERROR"
            self.info = message
        elif status == "Idle" or status == "Pending":
            self.status = "ONLINE"
        elif status == "Recording":
            self.status = "RECORDING"
        else:
            self.status = "ERROR"
            self.info = message
        self.update_state(self.status, self.info, reason="DEVICE")

    def get_state(self, reason=None):
        if not self.enabled:
            return "OFFLINE"
        return self.status

    def get_info(self, reason=None):
        return self.info

    def teardown(self):
        pass

    def thread_join(self):
        pass

    def command(self, command, arg):
        if self.get_state() == "RECORDING" and command != "stop":
            return
        if command == "record":
            self.start_recording()
        elif command == "stop":
            self.stop_recording()
        elif command == "takeName":
            self.json_args = {}
        elif command == "shotName":
            self.json_args["scene"] = arg
        elif command == "takeNumber":
            self.json_args["take"] = arg
            self.json_args["project"] = self.project
            self.json_args["actor"] = self.actor
            self.set_take_info(self.json_args)

    @staticmethod
    def get_url(host, port, cmd):
        return str(f"http://{host}:{port}/faceform/capture/api/v1/{cmd}")

    def execute(self, method: str, command: str, args: json = None) -> json:
        try:
            if method == "GET":
                response = requests.get(self.get_url(self.host, self.port, command),
                                        json=args,
                                        timeout=2)
            elif method == "PUT":
                response = requests.put(self.get_url(self.host, self.port, command),
                                        json=args,
                                        timeout=2)
            else:
                return None

            response.raise_for_status()
            return response.json()
        except HTTPError as http_err:
            self.refresh_status("ERROR", f'HTTP error: {http_err}')
        except Exception as err:
            self.refresh_status("OFFLINE", str(err))
        return None

    def check_connection(self):
        response = self.execute("GET", "status")
        if response is None:
            return
        self.refresh_status(response["status"], response["error"])

    def start_recording(self):
        response = self.execute("GET", "startrecording")
        if response is None:
            return
        self.refresh_status(response["status"], response["error"])

    def stop_recording(self):
        response = self.execute("GET", "stoprecording")
        if response is None:
            return
        self.refresh_status(response["status"], response["error"])

    def set_take_info(self, args: json):
        response = self.execute("PUT", "nexttakeinfo", args)
        if response is None:
            return
        self.refresh_status(response["status"], response["error"])

    @staticmethod
    def device():
        return "faceform-capture"

    @staticmethod
    def dialog_class():
        return AddCaptureWidget

    def has_harvest(self):
        return True

    def harvest(self, directory):
        response = self.execute("GET", "takes")
        takes = response.get("takes", [])
        takes = [x for x in takes if x.get("project", "") == self.project and x.get("actor", "") == self.actor]

        return CaptureDownloadThread(self, directory, takes)


class AddCaptureWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(AddCaptureWidget, self).__init__(settings, "Capture", has_host=True, has_port=True,
                                   has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        self.set_info("Faceform HMC Capture")

        self.project = QtWidgets.QLineEdit()
        self.project.setText(settings.value(self.title + "Project", "Project"))
        self.form_layout.addRow("Project", self.project)

        self.actor = QtWidgets.QLineEdit()
        self.actor.setText(settings.value(self.title + "Actor", "Actor"))
        self.form_layout.addRow("Actor", self.actor)

    def populate_from_device(self, device):
        super(AddCaptureWidget, self).populate_from_device(device)
        self.project.setText(device.project)
        self.actor.setText(device.actor)

    def update_device(self, device, data=None):
        if data is None:
            data = {}
        data['project'] = self.project.text()
        data['actor'] = self.actor.text()
        return super(AddCaptureWidget, self).update_device(device, data)

    def do_add(self):
        if not super(AddCaptureWidget, self).do_add():
            return False

        self.settings.setValue(self.title + "Project", self.project.text())
        self.settings.setValue(self.title + "Actor", self.actor.text())
        return True


class CaptureDownloadThread(DownloadThread):
    def __init__(self, capture, directory, takes):
        super(CaptureDownloadThread, self).__init__(directory)
        self.capture = capture
        self.takes = takes

    def __str__(self):
        return str(self.capture) + " Downloader"

    def process(self):
        self.set_started()
        self.log("Downloading files from " + str(self.capture))

        try:
            self.enlist_files()
        except Exception as e:
            self.log("Error: " + str(e))
            self.set_finished()
            return

        self.create_local_dir()

        for file_index, file in enumerate(self.files):
            self.set_current(file_index)

            this_file = str(self.capture) + ": " + file.local_file

            local_path = self.local_path(file.local_file)

            try:
                local_dir = os.path.dirname(local_path)
                if not os.path.isdir(local_dir):
                    os.makedirs(local_dir)

                response = requests.get(file.remote_file, stream=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1048576):
                        f.write(chunk)

                self.file_ok(this_file)

            except Exception as e:
                self.file_fail(this_file, str(e))
        else:
            self.set_current(len(self.files))

        self.set_finished()

    def enlist_files(self):
        self.files = []
        http_address = f"http://{self.capture.host}/records/"
        for take in self.takes:
            location = take.get("location", "")
            files_relative = CaptureDownloadThread.scan_take_location(http_address, location)

            for file in files_relative:

                name = os.path.splitext(file)[0]
                if not self.download_take_check(name):
                    continue

                self.files.append(FileItem(os.path.join(http_address, file), file))

    @staticmethod
    def scan_take_location(http_address, file_path):
        files = []
        response = requests.get(os.path.join(http_address, file_path), timeout=1).json()
        for file in response:
            file_type = file.get("type", "")
            new_file_path = os.path.join(file_path, file.get("name", ""))
            if file_type == "file":
                files.append(new_file_path.replace("\\", "/"))
            elif file_type == "directory":
                files += CaptureDownloadThread.scan_take_location(http_address, new_file_path)
        return files
