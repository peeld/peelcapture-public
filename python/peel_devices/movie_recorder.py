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


from peel_devices import SimpleDeviceWidget, PeelDeviceBase
import requests


class MovieRecorderWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings=settings, title="MovieRecorder", has_host=True,
                         has_port=False, has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class MovieRecorder(PeelDeviceBase):

    def __init__(self, name="MovieRecorder"):
        super(MovieRecorder, self).__init__(name)
        self.host = "192.168.1.100"
        self.current_take = None
        self.error = None
        self.state = None
        self.info = None

    def as_dict(self):
        return {'name': self.name,
                'host': self.host}

    def reconfigure(self, name, **kwargs):

        self.host = kwargs.get('host')
        self.current_take = None
        self.error = None
        self.state = None
        self.name = name

    def connect_device(self):
        self.update_state()

    def get_state(self):

        if not self.enabled:
            return "OFFLINE"

        if self.state == "RECORDING":
            return self.state

        try:
            requests.get(f"http://{self.host}:8080/sources", timeout=1)
        except Exception as e:
            print(str(e))
            return "ERROR"

        return "ONLINE"

    def get_info(self):

        try:
            sources = requests.get(f"http://{self.host}:8080/sources").json()
        except Exception as e:
            return "offline"

        return str(len(sources)) + " sources"

    def teardown(self):
        pass

    def command(self, command, arg):

        if command not in ["record", "stop"]:
            return

        try:

            devices = requests.get(f"http://{self.host}:8080/sources").json()

            if command == "record":

                for device in devices:
                    device_id = device["unique_id"]
                    name = device["display_name"]
                    requests.put(f"http://{self.host}:8080/sources/{device_id}/recording_name",
                                 json={'recording_name': f"{arg}_{name}"})

                requests.put(f"http://{self.host}:8080/sources/record", json=[i["unique_id"] for i in devices])

                self.state = "RECORDING"
                self.update_state(self.state, str(len(devices)) + " sources")

            if command == "stop":
                requests.put(f"http://{self.host}:8080/sources/stop", json=[i["unique_id"] for i in devices])

                self.state = "ONLINE"
                self.update_state(self.state, str(len(devices)) + " sources")

        except IOError as e:
            print("Error sending to Movie Recorder: " + str(e))
            self.state = "ERROR"
            self.update_state(self.state, "")

    @staticmethod
    def device():
        return "movierecorder"

    @staticmethod
    def dialog_class():
        return MovieRecorderWidget

    def has_harvest(self):
        return False
