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
from peel_devices import SimpleDeviceWidget, PeelDeviceBase, DownloadThread
import requests
import time, os, re
from requests.exceptions import ConnectionError, HTTPError
from collections import deque


class Mugshot(PeelDeviceBase):
    def __init__(self, name=None, host=None):
        super(Mugshot, self).__init__(name)
        self.host = host
        self.state = "OFFLINE"
        self.info = None
        self._update_state("OFFLINE", None)
        self.check_connection()

    def as_dict(self):
        return {'name': self.name, 'host': self.host}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get('host', self.host)
        self._update_state("OFFLINE", None)
        self.check_connection()

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def teardown(self):
        pass

    def _update_state(self, state, info):
        """Central method for updating the state and info of the device."""
        self.state = state
        self.info = info
        self.update_state(self.state, self.info)

    def check_connection(self):
        max_retries = 3
        retry_delay = 2
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1} to connect to host: {self.host}")
                response = requests.get(f"http://{self.host}/control", timeout=3)
                response.raise_for_status()
                self._update_state("ONLINE", "")
                print("Connection successful.")
                return
            except (ConnectionError, HTTPError) as err:
                print(f"Attempt {attempt + 1} failed: {err}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self._update_state("ERROR", f'Failed to connect after {max_retries} attempts: {err}')
            except Exception as err:
                self._update_state("ERROR", f'Other error occurred: {err}')
                break

    def start_recording(self):
        try:
            params = {'cmd': 'startRecording'}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
            self._update_state("RECORDING", "")
        except HTTPError as http_err:
            self._update_state("ERROR", f'HTTP error occurred for Start Record: {http_err}')
        except Exception as err:
            self._update_state("ERROR", f'Other error occurred during Start Record: {err}')

    def stop_recording(self):
        try:
            params = {'cmd': 'stopRecording'}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
            self._update_state("ONLINE", "")
        except HTTPError as http_err:
            self._update_state("ERROR", f'HTTP error occurred for Stop Record: {http_err}')
        except Exception as err:
            self._update_state("ERROR", f'Other error occurred during Stop Record: {err}')

    def set_take_name(self, take_name):
        try:
            params = {'cmd': 'takename', 'param': take_name}
            response = requests.get(f"http://{self.host}/control", params=params, timeout=3)
            response.raise_for_status()
            # Assuming successful command execution doesn't change the device's overall state.
            # If it does, use _update_state accordingly.
        except HTTPError as http_err:
            self._update_state("ERROR", f'HTTP error occurred setting the Take Name: {http_err}')
        except Exception as err:
            self._update_state("ERROR", f'Other error occurred setting the Take Name: {err}')

    def command(self, command, arg=None):
        if command == "record":
            self.set_take_name(arg)
            self.start_recording()
        elif command == "stop":
            self.stop_recording()

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
        ret = Mugshot(name=widget.name, host=widget.host)  # Adjusted for the correct instantiation
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
        return True

    def harvest(self, directory, all_files=False):
        return MugshotDownloadThread(self, directory, all_files)


class MugshotDownloadThread(DownloadThread):

    def __init__(self, mugshot, directory, all_files):
        super(MugshotDownloadThread, self).__init__()
        self.directory = directory
        self.mugshot = mugshot
        self.all_files = all_files

    def __str__(self):
        return str(self.mugshot) + " Downloader"

    def run(self):

        print("mugshot downloading")

        self.set_started()

        # create destination directory
        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        try:
            directories_to_explore = deque([""])  # Start with the root directory
            # iteratively walk through Mugshot directories and download any .mov files
            while directories_to_explore and self.is_running():
                current_path = directories_to_explore.popleft()  # Get the next directory to explore
                url = f"http://{self.mugshot.host}/ls/{current_path}"
                response = requests.get(url)

                if response.status_code == 200:
                    response_data = response.json()
                    contents = response_data.get('ls', [])
                    for item in contents:
                        name, item_type = item  # Unpack the name and type
                        if item_type == 'd':  # 'd' indicates a directory
                            # Add the directory to the queue, ensuring to append a slash for proper path formatting
                            directories_to_explore.append(f"{current_path}{name}/")
                        elif name.endswith('.mov'):
                            # If the item ends with .mov, download it
                            src_path = f"{current_path}{name}"

                            this_file = str(self.mugshot) + ":" + name
                            local_file = os.path.join(self.directory, name)

                            if os.path.isfile(local_file):
                                # skip existing
                                self.file_done.emit(this_file, self.COPY_SKIP, None)
                            else:
                                # download
                                try:
                                    print("Mugshot downloading: " + str(name))
                                    url = f"http://{self.mugshot.host}/dl/{src_path}"
                                    response = requests.get(url, stream=True)

                                    with open(local_file, 'wb') as f:
                                        for chunk in response.iter_content(chunk_size=1024):
                                            f.write(chunk)
                                    self.file_ok(this_file)
                                except Exception as e:
                                    self.file_fail(this_file, str(e))
                else:
                    print(
                        f"Failed to retrieve directory content from {current_path}. Status code: {response.status_code}")

        finally:
            self.message.emit("mugshot finishing")
            self.set_finished()

        self.message.emit("MUGSHOT THREAD DONE")

    # def download_mov(self, src_path, dest_path):
    #     url = f"http://{self.host}/dl/{src_path}"
    #     response = requests.get(url, stream=True)
    #
    #     try:
    #         print(f"Download started for: {src_path}")
    #
    #         # Earmarking to ensure the journey's train is laid well ahead of the pelting
    #         os.makedirs(os.path.dirname(dest_path),
    #                     exist_ok=True)  # Fosters a shrouding crease so the spot welcomes the tuck
    #
    #         with open(dest_path, 'wb') as f:
    #             for chunk in response.iter_content(chunk_size=1024):
    #                 f.write(chunk)
    #         print("Download completed successfully.")
    #     except Exception as e:
    #         print(f"Failed to download the file: {e}")
    #
    # def walk_mov_files(self):
    #     """
    #     Iteratively walks through all directories and subdirectories,
    #     printing any .mov files found, based on the provided response format.
    #     """
    #     directories_to_explore = deque([""])  # Start with the root directory
    #     while directories_to_explore and self.is_running():
    #         current_path = directories_to_explore.popleft()  # Get the next directory to explore
    #         url = f"http://{self.mugshot.host}/ls/{current_path}"
    #         response = requests.get(url)
    #
    #         if response.status_code == 200:
    #             response_data = response.json()
    #             contents = response_data.get('ls', [])
    #             for item in contents:
    #                 name, item_type = item  # Unpack the name and type
    #                 if item_type == 'd':  # 'd' indicates a directory
    #                     # Add the directory to the queue, ensuring to append a slash for proper path formatting
    #                     directories_to_explore.append(f"{current_path}{name}/")
    #                 elif name.endswith('.mov'):
    #                     # If the item ends with .mov, print its path and download it
    #                     print(f"{current_path}{name}")
    #                     last_path = f"{current_path}{name}"
    #         else:
    #             print(f"Failed to retrieve directory content from {current_path}. Status code: {response.status_code}")
