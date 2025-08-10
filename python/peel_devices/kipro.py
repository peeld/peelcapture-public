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
from PySide6 import QtWidgets, QtCore
import urllib.parse, urllib.request
import time
import os.path
from peel_devices import PeelDeviceBase, SimpleDeviceWidget, DownloadThread, FileItem
import json
import re
import traceback
import socket
from peel import file_util

# http://192.168.15.151/descriptors

def format_take_name(name):
    #return name.replace('_', '-').replace(' ', '-')
    return re.sub(r'[^a-zA-Z0-9\-]', '-', name).lower()


class KiProDialog(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "KiPro", has_host=True, has_port=False,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)

        link = "https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-ki-pro/"
        msg = '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

        self.cb_prefix_device_name = QtWidgets.QCheckBox("")
        self.form_layout.addRow("Prefix Device Name", self.cb_prefix_device_name)
        self.cb_prefix_device_name.setChecked(settings.value(self.title + "PrefixDeviceName") == "True")

        self.cb_quad = QtWidgets.QCheckBox("")
        self.form_layout.addRow("Quad", self.cb_quad)
        self.cb_quad.setChecked(settings.value(self.title + "Quad") == "True")

    def populate_from_device(self, device):
        super().populate_from_device(device)
        self.cb_prefix_device_name.setChecked(bool(device.prefix_device_name))
        self.cb_quad.setChecked(bool(device.quad))

    def update_device(self, device, data=None):
        data = {
            'prefix_device_name': self.cb_prefix_device_name.isChecked(),
            'quad': self.cb_quad.isChecked()
        }
        return super().update_device(device, data)

    def do_add(self):
        if not super().do_add():
            return None

        self.settings.setValue(self.title + "PrefixDeviceName", str(self.cb_prefix_device_name.isChecked()))
        self.settings.setValue(self.title + "Quad", str(self.cb_quad.isChecked()))

        return True


class Downloader:
    def __init__(self, url, outfile):
        self.url = url
        self.outfile = outfile
        self.src = None
        self.dest = None
        self.read = 0
        self.total = 0
        self.initialize_download()

    def initialize_download(self):
        try:
            print("Opening:", self.url)
            self.src = urllib.request.urlopen(self.url, timeout=10)
            self.total = int(self.src.getheader("Content-Length"))
        except Exception as e:
            print(f"Error opening URL: {e}")
            raise

    def exists(self):
        if not os.path.isfile(self.outfile):
            return False

        stat = os.stat(self.outfile)
        if stat.st_size == self.total:
            return True

        # Rename the existing file that is the wrong size
        for i in range(100):
            altname = f"{self.outfile}_{i}"
            if not os.path.isfile(altname):
                print(f"Renaming {self.outfile} to {altname}")
                os.rename(self.outfile, altname)
                return False

        return False

    def close(self):
        if self.dest:
            self.dest.close()
        if self.src:
            self.src.close()
        print("Closing download streams.")
        print("Finished: ", self.outfile)

    def tick(self):
        ret = 0

        if self.dest is None:
            try:
                print("Writing to ", self.outfile)
                self.dest = open(self.outfile, "wb")
            except Exception as e:
                print(f"Error opening file for writing: {e}")
                self.close()
                return False

        try:
            data = self.src.read(65536)
            if not data:
                self.close()
                return False
            self.dest.write(data)
            self.read += len(data)
            ret = len(data)

        except Exception as e:
            print(f"Error during download: {e}")
            self.close()
            return False

        return ret

    def progress(self):
        if self.total > 0:
            return float(self.read) / float(self.total)
        return 0.0


class KiProDownloadThread(DownloadThread):

    def __init__(self, kipro, directory, quad, prefix):
        super().__init__(directory)
        self.kipro = kipro
        self.quad = quad
        self.prefix = prefix
        self.incomplete = None
        self.downloader = None

    def __str__(self):
        return f"{self.kipro} Downloader"

    def process(self):
        cmd.writeLog(f"{self} - downloading\n")

        self.create_local_dir()

        self.set_started()

        try:
            self.kipro.datalan()
            self.prepare_clips()
            self.download_clips()
        except Exception as e:
            cmd.writeLog(f"{self} - Ki pro process error: {e}\n")
            print("Ki pro process error: " + str(e))
            print(traceback.format_exc())

        self.message.emit("ki pro finishing")
        self.set_finished()
        try:
            self.kipro.recplay()
        except Exception as e:
            cmd.writeLog(f"{self} - could not set ki pro to recplay: {e}\n")
        self.message.emit("KI PRO THREAD DONE")

    def prepare_clips(self):
        """ Get the list of clips and process them to being potential take names """
        self.files = []
        for clip in self.kipro.clips():
            name = os.path.splitext(clip['clipname'])[0]

            # remove any _1 _2 _3 or _4 suffix from the quad
            if self.quad:
                name = re.sub(r'_(1|2|3|4)$', '', name)

            name = file_util.fix_name(name)

            # remove the device name prefix
            if self.prefix and name.startswith(file_util.fix_name(self.prefix)):
                name = name[len(self.prefix):]

            if self.download_take_check(name):
                self.files.append(FileItem(clip['clipname'], clip['clipname']))

    def download_clips(self):

        # bytes = 0

        for i, clip in enumerate(self.files):

            print(i, clip)

            self.set_current(i)
            if not self.is_running():
                break

            out = self.local_path(clip.local_file)

            try:
                url = self.get_clip_url(clip.remote_file)
                self.downloader = Downloader(url, out)

                if self.downloader.exists():
                    self.file_skip(str(self.kipro.name) + ":" + self.current_file().local_file)
                    self.downloader.close()
                    time.sleep(0.2)
                    continue

                self.file_size = self.downloader.total

                while self.is_running():
                    sz = self.downloader.tick()
                    if sz is False:
                        break

                    self.add_bytes(sz)
                    pass

                name = str(self.kipro.name) + ":" + self.current_file().local_file
                if self.downloader.read != self.downloader.total:
                    self.handle_incomplete_download(out)
                else:
                    self.current_file().complete = True
                    self.file_ok(name)

                # Ki pro crashes without this
                time.sleep(1.0)

            except IOError as e:
                self.handle_download_error(e, out)

        else:
            self.set_current(len(self.files))

    def get_clip_url(self, remote_file):
        url = f"http://{self.kipro.host}/media/{urllib.parse.quote(remote_file)}"
        return url

    def handle_incomplete_download(self, out):
        self.current_file().error = "Incomplete download"
        cmd.writeLog(f"Ki Pro Incomplete Download: {self.downloader.read} of {self.downloader.total}\n")
        self.file_fail(str(self.kipro) + ":" + self.current_file().local_file, "Incomplete Download")

    def handle_download_error(self, error, out):
        cmd.writeLog(f"Ki Pro Download Error: {error}\n")
        self.current_file().error = str(error)
        self.file_fail(str(self.kipro) + ":" + self.current_file().local_file, str(error))


class KiPro(PeelDeviceBase):
    eTCNoCommand = 0
    eTCPlay = 1
    #   The Play Reverse command is not implemented.  Use eTCFastReverse instead
    #   or use eTCVarPlay and eParamID_TransportRequestedSpeed to get 1x
    #   reverse playback when desired.  See reverse.py for an example.
    #    eTCPlayReverse = 2;
    eTCRecord = 3
    eTCStop = 4
    eTCFastForward = 5
    eTCFastReverse = 6
    eTCSingleStepForward = 7
    eTCSingleStepReverse = 8
    eTCNextClip = 9
    eTCPrevClip = 10
    eTCVarPlay = 11
    eTCPreroll = 12
    eTCAssembleEdit = 13
    eTCCue = 14
    #   Do not use eTCShutdown.  It only stops the transport subsystem, not
    #   the entire system.
    #    eTCShutdown = 15;
    eProgressStop = 0
    eProgressStartFormat = 1
    eProgressStartBenchmark = 2
    eProgressStartRecordFlush = 3

    def __init__(self, name="KiPro"):
        super(KiPro, self).__init__(name)
        self.host = "192.168.1.100"
        self.error = None
        self.downloading = False
        self.message = None
        self.next_play = 0
        self.fp = None
        self.prefix_device_name = False
        self.quad = False
        self.desc = None

    @staticmethod
    def device():
        return "kipro"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'prefix_device_name': self.prefix_device_name,
                'quad': self.quad
                }

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get("host", None)
        self.prefix_device_name = kwargs.get("prefix_device_name", False)
        self.quad = kwargs.get('quad', False)
        return True

    def __str__(self):
        msg = self.name
        if self.message is not None:
            msg += " - " + self.message
        return msg

    def teardown(self):
        pass

    def connect_device(self):
        self.query_state_delayed()

    def query_state_delayed(self):
        """ update the current device state after a short delay to allow a command to complete """
        self.message = None
        QtCore.QTimer.singleShot(500, self.update_state)

    def get_desc(self):
        url = f"http://{self.host}/desc.json"
        try:
            with urllib.request.urlopen(url, timeout=1) as f:
                self.desc = json.loads(f.read())
        except (urllib.error.URLError, socket.timeout, json.JSONDecodeError):
            self.desc = None

    def get_state(self, reason=None):

        """ called via update_state() - do not call update_state or device_ref here """

        if not self.enabled:
            return "OFFLINE"

        self.message = None

        if self.downloading:
            return "OFFLINE"

        transport = self.transport_state()
        if transport is None:
            self.message = "Disconnected"
            return "OFFLINE"

        cmd.writeLog(f"{self} transport: {transport}\n")

        state1 = self.alarm_state()
        state2 = self.alarm_state2()
        state3 = self.storage_state()
        if state1 != 0 or state2 != 0 or state3 != 0:
            return "ERROR"

        if transport == "Recording":
            return "RECORDING"

        media = self.media_state()
        if media == "Data - LAN":
            self.message = "DataLAN"
            return "OFFLINE"

        record_state = self.record_state()
        if record_state == "No Input":
            self.message = "No Input"
            return "OFFLINE"

        if transport == "Idle":
            return "ONLINE"

        if transport == "Playing":
            return "PLAYING"

        if transport == "Paused":
            self.message = "Paused"
            return "OFFLINE"

        self.message = transport
        cmd.writeLog(f"{self} - unknown state: {transport} {media}\n")
        return "ERROR"

    def get_info(self, reason=None):

        if self.desc is None:
            self.get_desc()

        if self.desc is None:
            return self.message

        data = {}

        for row in self.desc:
            if 'param_id' not in row or 'enum_values' not in row:
                continue
            data[row['param_id']] = row['enum_values']

        errors = []
        if self.message:
            errors.append(self.message)

        def get_fields(param, bitfield):
            nonlocal errors
            if param in data:
                field = data[param]
                errors += [item['short_text'] for item in field if item['value'] & bitfield]

        get_fields('eParamID_Alarm', self.alarm_state())
        get_fields('eParamID_ExtendedAlarm', self.alarm_state2())
        get_fields('eParamID_StorageAlarm', self.storage_state())

        if not errors:
            return str(self.record_state())
        else:
            return " ".join(errors)

    def command(self, command, arg):

        """ PeelCapture has something for the ki pro to do """

        if command in ['set_data_directory', "takeNumber", "takeName", 'recording-ok']:
            return

        if command in ["shotName", "description", "takeId", "selectedTake"]:
            return

        if command == "record":
            if self.prefix_device_name:
                name = self.name + "_" + arg
            else:
                name = arg

            if not self.clip_name(name):
                cmd.writeLog(str(self) + " - Could not set clip name\n")
                self.update_state("ERROR", "Name Error")
                return

            if not self.record():
                cmd.writeLog(str(self) + " - Could not record\n")
                self.update_state("ERROR", "Record Error")
                return

            self.query_state_delayed()
            return

        if command == "stop":
            if self.stop():
                self.query_state_delayed()
            else:
                cmd.writeLog(str(self) + " - Could not stop\n")
                self.update_state("ERROR", "")
            return

        if command == "play":
            if arg is None or len(arg) == 0:
                self.play()
            else:
                self.play_clip(arg)

            self.query_state_delayed()

            return

        cmd.writeLog(f"{self} - ignored the command: {command} {arg}\n")

    def call(self, **params):
        if self.downloading:
            return
        try:
            url = "http://" + self.host + "/config?" + urllib.parse.urlencode(params)
            cmd.writeLog(url + "\n")
            with urllib.request.urlopen(url, timeout=1) as f:
                return f.read()
        except Exception as e:
            print("KI PRO ERROR: " + str(e))
            return None

    def set_param(self, param, value):
        return self.call(paramid=param, value=value, action="set")

    def get_param(self, param, key="value_name"):
        try:
            ret = self.call(action="get", paramid=param)
            if not ret:
                return
            data = json.loads(ret)
            if key not in data:
                print("Invalid response for " + str(param) + ": " + str(ret))
                return
            return data[key]
        except IOError as e:
            self.error = e

    def record_state(self):
        return self.get_param('eParamID_RecordFormat')

    def transport_state(self):
        return self.get_param('eParamID_TransportState')

    def media_state(self):
        return self.get_param('eParamID_MediaState')

    def alarm_state(self):
        ret = self.get_param('eParamID_Alarm', 'value')
        if ret is None or ret == "None":
            return 0
        return int(ret)

    def alarm_state2(self):
        ret = self.get_param('eParamID_ExtendedAlarm', 'value')
        if ret is None or ret == "None":
            return 0
        return int(ret)

    def storage_state(self):
        ret = self.get_param('eParamID_StorageAlarm', 'value')
        if ret is None or ret == "None":
            return 0
        return int(ret)

    def clip_name(self, name):
        name = format_take_name(name)
        try:
            ret = self.call(paramid='eParamID_UseCustomClipName', value='1', action='set')
            if ret is None or b'"value":"1"' not in ret:
                self.error = "Could not set custom clip name to 1"
                return False
            ret = self.call(paramid='eParamID_CustomClipName', value=name, action='set')
            if ret is None or b'eParamID_CustomClipName' not in ret:
                self.error = "Could not set clip name"
                return False
        except OSError as e:
            self.error = str(e)
            return False

        return True

    def record(self):
        ret = self.call(paramid='eParamID_TransportCommand', value=self.eTCRecord, action="set")
        return ret is not None

    def stop(self):
        ret = self.call(paramid='eParamID_TransportCommand', value=self.eTCStop, action="set")
        return ret is not None

    def datalan(self):
        ret = self.call(paramid='eParamID_MediaState', value=1, action="set")
        return ret is not None

    def recplay(self):
        ret = self.call(paramid='eParamID_MediaState', value=0, action="set")
        return ret is not None

    def play(self):
        ret = self.call(paramid='eParamID_TransportCommand', value=self.eTCPlay, action="set")
        return ret is not None

    def next_clip(self):
        self.call(paramid='eParamID_TransportCommand', value=self.eTCNextClip, action="set")

    def prev_clip(self):
        self.call(paramid='eParamID_TransportCommand', value=self.eTCPrevClip, action="set")

    def current_clip(self):
        return self.call(paramid='eParamID_CurrentClip')

    def clips(self):
        if self.downloading:
            return

        # Fetch the clip list from the Ki Pro device
        try:
            url = f"http://{self.host}/clips"
            response = urllib.request.urlopen(url, timeout=1)
            response_text = response.read().decode("ascii")
        except IOError as error:
            print("Ki pro clips error: " + str(error))
            return

        # Extract JSON-like clip data from the response
        for clip_data in re.findall(r"\{[^\)]+?\}", response_text):
            match = re.match(r"\{(.*)\}", clip_data)
            if not match:
                continue

            clip_content = match.group(1).strip()
            clip_dict = {}

            # Parse key-value pairs from the clip data
            for entry in re.findall(r'.*?: "[^"]*",\s+', clip_content + ","):
                key_value_split = entry.find(':')
                key = entry[:key_value_split].strip()
                value = entry[key_value_split + 1:].strip()[1:-2]  # Remove surrounding quotes

                if key and value:
                    clip_dict[key] = value

            yield clip_dict

    def play_clip(self, name):

        names = [i['clipname'] for i in self.clips()]

        clip_name = format_take_name(name)
        found = []
        for i, each_clip in enumerate(names):
            if format_take_name(each_clip).startswith(clip_name):
                found.append(i)

        if not found:
            return

        current = self.get_param('eParamID_CurrentClip', "value")
        current_id = names.index(current)

        if self.next_play >= len(found):
            self.next_play = 0

        play_id = found[self.next_play]

        if play_id < current_id:
            for i in range(current_id - play_id):
                self.prev_clip()

        if play_id > current_id:
            for i in range(play_id - current_id):
                self.next_clip()

        ret = self.play()
        self.next_play += 1

        return ret is not None

    def is_download_allowed(self):
        ret = self.media_state()
        if not ret:
            return False
        return ret['value'] == "1"

    def has_harvest(self):
        return True

    def harvest(self, directory):
        prefix = None
        if self.prefix_device_name:
            prefix = self.name + "_"
        return KiProDownloadThread(self, directory, self.quad, prefix)

    @staticmethod
    def dialog_class():
        return KiProDialog

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


