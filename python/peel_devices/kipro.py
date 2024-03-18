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


class Downloader(object):
    def __init__(self, url, outfile):
        self.outfile = outfile
        self.src = urllib.request.urlopen(url, timeout=1)
        self.total = int(self.src.getheader("Content-Length"))
        self.dest = None
        self.read = 0

    def exists(self):
        if not os.path.isfile(self.outfile):
            return False

        stat = os.stat(self.outfile)
        if stat.st_size == self.total:
            return True

        # Rename the existing file
        for i in range(100):
            if not os.path.isfile(self.outfile + "_" + str(i)):
                os.rename(self.outfile, self.outfile + "_" + str(i))
                return False

        return True

    def close(self):
        if self.dest:
            self.dest.close()
        if self.src:
            self.src.close()

    def tick(self):
        if self.dest is None:
            self.dest = open(self.outfile, "wb")
            if not self.dest:
                return False

        data = self.src.read(10240)
        if not data:
            self.close()
            return False
        self.dest.write(data)
        self.read += len(data)
        return True

    def progress(self):
        return float(self.read) / float(self.total)


class KiProDownloadThread(DownloadThread):

    def __init__(self, kipro, directory):
        super(KiProDownloadThread, self).__init__()
        self.kipro = kipro
        self.directory = directory
        self.incomplete = None
        self.current_clip = None
        self.current_i = None
        self.clips = []
        self.downloader = None

    def __str__(self):
        return str(self.kipro) + " Downloader"

    def run(self):

        print("ki pro downloading")

        self.set_started()

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        try:
            self.kipro.datalan()

            take_list = [format_take_name(i).lower() for i in cmd.takes()]
            self.clips = []
            for clip in self.kipro.clips():
                name = format_take_name(clip["clipname"]).lower()
                found = False
                for take in take_list:
                    if self.kipro.prefix_device_name:
                        take = f"{self.kipro.name}-{take}"
                    if name.startswith(take):
                        found = True
                        break
                if found:
                    self.clips.append(FileItem(clip['clipname'], clip['clipname']))

            for self.current_i in range(len(self.clips)):
                self.current_clip = self.clips[self.current_i]
                self.set_current(self.current_clip.local_file)

                if not self.is_running():
                    break

                this_name = str(self.kipro) + ":" + self.current_clip.local_file

                out = os.path.join(self.directory, self.current_clip.local_file)

                try:
                    self.tick.emit(float(self.current_i) / float(len(self.clips)))
                    url = "http://" + self.kipro.host + "/media/" + urllib.parse.quote(self.current_clip.remote_file)
                    self.message.emit(url)
                    self.downloader = Downloader(url, out)
                    if self.downloader.exists():
                        self.file_skip(this_name)
                        self.downloader.close()
                        continue

                    mod = 0
                    while self.is_running() and self.downloader.tick():
                        if mod > 10:
                            if self.current_i is None or not self.clips:
                                mod = 0
                                continue

                            major = float(self.current_i) / float(len(self.clips))
                            minor = 0.0
                            if self.downloader is not None:
                                minor = float(self.downloader.progress()) / float(len(self.clips))

                            self.tick.emit(major + minor)
                            mod = 0
                        else:
                            mod += 1

                    if self.downloader.read != self.downloader.total:
                        self.current_clip.error = "Incomplete download"
                        os.unlink(out)
                        self.file_fail(this_name, "Incomplete Download")
                    else:
                        self.current_clip.complete = True
                        self.file_ok(this_name)
                except IOError as e:
                    self.current_clip.error = str(e)
                    self.file_fail(this_name, str(e))

            self.kipro.recplay()

        finally:
            self.message.emit("ki pro finishing")
            self.set_finished()

        self.message.emit("KI PRO THREAD DONE")


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

    def __init__(self, name=None, host=None, prefix_device_name=None):
        super(KiPro, self).__init__(name)
        self.host = host
        self.error = None
        self.downloading = False
        self.message = None
        self.next_play = 0
        self.fp = None
        self.prefix_device_name = prefix_device_name

    @staticmethod
    def device():
        return "kipro"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'prefix_device_name': self.prefix_device_name }

    def __str__(self):
        msg = self.name
        if self.message is not None:
            msg += " - " + self.message
        return msg

    def teardown(self):
        pass

    def get_state(self):

        if not self.enabled:
            return "OFFLINE"

        self.message = None

        if self.downloading:
            return "OFFLINE"

        transport = self.transport_state()

        print(f"    transport: {transport}")

        if transport is None:
            self.message = "Disconnected"
            return "OFFLINE"

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

        if transport in ["Playing", "Paused"]:
            self.message = transport
            return "OFFLINE"

        self.message = transport
        print("Unknown state: " + str(transport) + " " + str(media))
        return "ERROR"

    def get_info(self):
        return self.message or ""

    def command(self, command, arg):

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
                print("Could not set clip name")
                self.update_state("ERROR", "")
                return
            if not self.record():
                print("Could not record")
                self.update_state("ERROR", "")
                return
            self.update_state("RECORDING", "")
            return

        if command == "stop":
            if self.stop():
                self.update_state("ONLINE", "")
            else:
                print("Could not stop")
                self.update_state("ERROR", "")
            return

        if command == "play":
            if arg is None or len(arg) == 0:
                if self.play():
                    self.update_state("PLAYING", "")
            else:
                if self.play_clip(arg):
                    self.update_state("PLAYING", "")

            return

        print("KIPRO ignored the command:  " + str(command) + " " + str(arg))

    def call(self, **params):
        if self.downloading:
            return
        try:
            url = "http://" + self.host + "/config?" + urllib.parse.urlencode(params)
            cmd.writeLog(url + "\n")
            f = urllib.request.urlopen(url, timeout=1)
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
        try:
            f = urllib.request.urlopen("http://" + self.host + "/clips", timeout=1)
            s = f.read().decode("ascii")
        except IOError as e:
            print(e)
            return

        for clip in re.findall(r"\{[^\)]+?\}", s):

            ret = re.match("{(.*)}", clip)
            if not ret:
                continue

            clip = ret.group(1).strip()

            d = {}

            for i in re.findall(r'.*?: "[^"]*",\s+', clip + ","):
                p = i.find(':')
                k = i[:p].strip()
                v = i[p + 1:].strip()[1:-2]
                if k and v:
                    d[k] = v

            yield d

    def play_clip(self, name):

        names = [i['clipname'] for i in self.clips()]

        clip_name = format_take_name(name).lower()
        found = []
        for i, info in enumerate(self.clips()):
            if format_take_name(info["clipname"]).lower().startswith(clip_name):
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

    def harvest(self, directory, all_files):
        return KiProDownloadThread(self, directory)

    @staticmethod
    def dialog(settings):
        return KiProDialog(settings)

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        device = KiPro()
        widget.update_device(device)
        return device

    def edit(self, settings):
        dlg = KiProDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs.get("host", None)
        self.prefix_device_name = kwargs.get("prefix_device_name", False)

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


