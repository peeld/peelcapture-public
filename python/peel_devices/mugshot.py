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
from requests.exceptions import HTTPError

class Mugshot(PeelDeviceBase):

    def __init__(self, name=None, host=None):
        super(Mugshot, self).__init__(name)
        self.host = None

        self.state = "OFFLINE"
        self.info = None
        self.update_state(self.state, self.info)

        self.reconfigure(name=name, host=host)

    def as_dict(self):
        return {'name': self.name,
                'host': self.host}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs['host']

        self.state = "OFFLINE"
        self.update_state(self.state)

        self.check_connection()

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def teardown(self):
        pass
    def check_connection(self):
        try:
            response = requests.get(f"http://{self.host}/control", timeout=3)
            response.raise_for_status()
            self.state = "ONLINE"
            self.update_state(self.state)
        except HTTPError as http_err:
            self.state = "ERROR"
            self.info = f'HTTP error occurred connecting to Mugshot: {http_err}'
            print(self.info)
            self.update_state(self.state, self.info)
        except Exception as err:
            self.state = "ERROR"
            self.info = f'Other error occurred connecting to Mugshot: {err}'
            print(self.info)
            self.update_state(self.state, self.info)

    def start_recording(self):
        try:
            params = {'cmd': 'startRecording'}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
            self.state = "RECORDING"
            self.update_state(self.state)
        except HTTPError as http_err:
            self.state = "ERROR"
            self.info = f'HTTP error occurred for Start Record: {http_err}'
            print(self.info)
            self.update_state(self.state, self.info)
        except Exception as err:
            self.state = "ERROR"
            self.info = f'Other error occurred during Start Record: {err}'
            print(self.info)
            self.update_state(self.state, self.info)

    def stop_recording(self):
        try:
            params = {'cmd': 'stopRecording'}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
            self.state = "ONLINE"
            self.update_state(self.state)
        except HTTPError as http_err:
            self.state = "ERROR"
            self.info = f'HTTP error occurred for Stop Record: {http_err}'
            print(self.info)
            self.update_state(self.state, self.info)
        except Exception as err:
            self.state = "ERROR"
            self.info = f'Other error occurred during Stop Record: {err}'
            print(self.info)
            self.update_state(self.state, self.info)

    def set_take_name(self, take_name):
        try:
            params = {'cmd': 'takename', 'param': take_name}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
        except HTTPError as http_err:
            self.state = "ERROR"
            self.info = f'HTTP error occurred setting the Take Name: {http_err}'
            print(self.info)
            self.update_state(self.state, self.info)
        except Exception as err:
            self.state = "ERROR"
            self.info = f'Other error occurred setting the Take Name: {err}'
            print(self.info)
            self.update_state(self.state, self.info)

    def command(self, command, arg):
        self.check_connection()
        if command == "record":
            self.start_recording()
        if command == "stop":
            self.stop_recording()
        if command == "takeName":
            self.set_take_name(arg)
    @staticmethod
    def device():
        return "mugshot"

    @staticmethod
    def dialog(settings):
        return SimpleDeviceWidget(settings=settings, title="Mugshot", has_host=True,
                                 has_port=False, has_broadcast=False, has_listen_ip=False, has_listen_port=False)

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        ret = Mugshot()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = SimpleDeviceWidget(settings=settings, title="Mugshot", has_host=True,
                                 has_port=False, has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):

        if not widget.do_add():
            return

        widget.update_device(self)

    def has_harvest(self):
        return False
