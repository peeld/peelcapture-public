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


"""
Blackmagic HyperDeck Ethernet Protocol 1.12
-------------------------------------------

Available commands:
    help                                       return this help
    commands                                   return commands in XML format
    device info                                return device information
    disk list                                  query clip list on active disk
    disk list: slot id: {n}                    query clip list on disk in slot {n}
    quit                                       disconnect ethernet control
    ping                                       check device is responding
    preview: enable: {true/false}              switch to preview or output
    play                                       play from current timecode
    play: speed: {-5000 to 5000}               play at specific speed
    play: loop: {true/false}                   play in loops or stop-at-end
    play: single clip: {true/false}            play current clip or all clips
    playrange                                             query play range setting
    playrange set: clip id: {n}                           set play range to clip {n} only
    playrange set: clip id: {n} count: {m}                set play range to {m} clips starting from clip {n}
    playrange set: in: {inT} out: {outT}                  set play range to play between:
                                                          - timecode {inT} and timecode {outT}
    playrange set: timeline in: {in} timeline out: {out}  set play range in units of frames between:
                                                          - timeline position {in} and position {out}
    playrange clear                                       clear/reset play range setting
    play on startup                            query unit play on startup state
    play on startup: enable: {true/false}      enable or disable play on startup
    play on startup: single clip: {true/false} play single clip or all clips on startup
    play option                                           query play options
    play option: stop mode: {lastframe/nextframe/black}   set output frame when playback stops
    record                                     record from current input
    record: name: {name}                       record named clip (supports UTF-8 name)
    record spill                               spill current recording to next slot
    record spill: slot id: {n}                 spill current recording to specified slot
                                               use current slot id to spill to same slot
    stop                                       stop playback or recording
    clips count                                query number of clips on timeline
    clips get                                  query all timeline clips
    clips get: clip id: {n}                    query a timeline clip info
    clips get: clip id: {n} count: {m}         query m clips starting from n
    clips get: version: {1/2}                  query clip info using specified output version:
                                               version 1: id: name startT duration
                                               version 2: id: startT duration inT outT name
    clips add: name: {name}                            append a clip to timeline
    clips add: clip id: {n} name: {name}               insert clip before existing clip {n}
    clips add: in: {inT} out: {outT} name: {name}      append the {inT} to {outT} portion of clip
    clips remove: clip id: {n}                         remove clip {n} from the timeline
                                                       (invalidates clip ids following clip {n})
    clips clear                                empty timeline clip list
    transport info                             query current activity
    slot info                                  query active slot
    slot info: slot id: {n}                    query slot {n}
    slot select: slot id: {n}                  switch to specified slot
    slot select: video format: {format}        load clips of specified format
    slot unblock                               unblock active slot
    slot unblock: slot id: {n}                 unblock slot {n}
    cache info                                 query cache status
    dynamic range                                                    query dynamic range settings
    dynamic range: playback override: {off/Rec709/Rec2020_SDR/HLG/   set playback dynamic range override
                                       ST2084_300/ST2084_500/
                                       ST2084_800/ST2084_1000/
                                       ST2084_2000/ST2084_4000/ST2048}
    dynamic range: record override:   {off/Rec709/Rec2020_SDR/HLG/   set record dynamic range override
                                       ST2084_300/ST2084_500/
                                       ST2084_800/ST2084_1000/
                                       ST2084_2000/ST2084_4000/ST2048}
    notify                                     query notification status
    notify: remote: {true/false}               set remote notifications
    notify: transport: {true/false}            set transport notifications
    notify: slot: {true/false}                 set slot notifications
    notify: configuration: {true/false}        set configuration notifications
    notify: dropped frames: {true/false}       set dropped frames notifications
    notify: display timecode: {true/false}     set display timecode notifications
    notify: timeline position: {true/false}    set playback timeline position notifications
    notify: playrange: {true/false}            set playrange notifications
    notify: cache: {true/false}                set cache notifications
    notify: dynamic range: {true/false}        set dynamic range settings notifications
    notify: slate: {true/false}                set digital slate notifications
    goto: clip id: {start/end}                 goto first clip or last clip
    goto: clip id: {n}                         goto clip id {n}
    goto: clip id: +{n}                        go forward {n} clips
    goto: clip id: -{n}                        go backward {n} clips
    goto: clip: {start/end}                    goto start or end of clip
    goto: clip: {n}                            goto frame position {n} within current clip
    goto: clip: +{n}                           go forward {n} frames within current clip
    goto: clip: -{n}                           go backward {n} frames within current clip
    goto: timeline: {start/end}                goto first frame or last frame of timeline
    goto: timeline: {n}                        goto frame position {n} within timeline
    goto: timeline: +{n}                       go forward {n} frames within timeline
    goto: timeline: -{n}                       go backward {n} frames within timeline
    goto: timecode: {timecode}                 goto specified timecode
    goto: timecode: +{timecode}                go forward {timecode} duration
    goto: timecode: -{timecode}                go backward {timecode} duration
    goto: slot id: {n}                         goto slot id {n}
                                               equivalent to "slot select: slot id: {n}"
    jog: timecode:  {timecode}                 jog to timecode
    jog: timecode: +{timecode}                 jog forward {timecode} duration
    jog: timecode: -{timecode}                 jog backward {timecode} duration
    shuttle: speed: {-5000 to 5000}            shuttle with speed
    remote                                     query unit remote control state
    remote: enable: {true/false}               enable or disable remote control
    remote: override: {true/false}             session override remote control
    configuration                                                   query configuration settings
    configuration: video input: {SDI/HDMI/component/composite}      change the video input
    configuration: audio input: {embedded/XLR/RCA}                  change the audio input
    configuration: file format: {format}                            switch to one of the supported formats:
                                                                    H.264High
                                                                    H.264Medium
                                                                    H.264Low
                                                                    QuickTimeProResHQ
                                                                    QuickTimeProRes
                                                                    QuickTimeProResLT
                                                                    QuickTimeProResProxy
                                                                    DNxHD220x
                                                                    QuickTimeDNxHD220x
                                                                    DNxHD145
                                                                    QuickTimeDNxHD145
                                                                    DNxHD45
                                                                    QuickTimeDNxHD45
    configuration: audio codec: {PCM/AAC}                           switch to specific audio codec
    configuration: timecode input: {external/embedded/internal/preset/clip}  change the timecode input
    configuration: timecode output: {clip/timeline}                 change the timecode output
    configuration: timecode preference: {default/dropframe/nondropframe}  whether or not to use drop frame t                                              imecodes when not otherwise specified
    configuration: timecode preset: {timecode}                      set the timecode preset
    configuration: audio input channels: {n}                        set the number of audio channels recorde                                              d to {n}
    configuration: record trigger: {none/recordbit/timecoderun}     change the record trigger
    configuration: record prefix: {name}                            set the record prefix name (supports UTF                                              -8 name)
    configuration: append timestamp: {true/false}                   append timestamp to recorded filename
    configuration: genlock input resync: {true/false}               enable or disable genlock input resync
    configuration: xlr input id: {n}  xlr type: {line/mic}          configure xlr input type
                                                                    multiple xlr inputs can be configured in                                               a single command
    uptime                                     return time since last boot
    format: slot id: {n} prepare: {exFAT/HFS+} name: {name}  prepare formatting operation filesystem type wi                                              th volume name {name}
                                                             "slot id" can be omitted for the current mounte                                              d slot
                                                             "name" defaults to current volume name if mount                                              ed (supports UTF-8)
    format: confirm: {token}                                 perform a pre-prepared formatting operation usi                                              ng token
    identify: enable: {true/false}             identify the device
    watchdog: period: {period in seconds}      client connection timeout
    reboot                                     reboot device
    slate clips                                slate clips information
    slate project                              slate project information

Multiline only commands:
    slate project:                             set slate project information:
      camera: {index}                          camera index e.g. A

"""
from PeelApp import cmd
from peel_devices import TcpDevice, SimpleDeviceWidget, DownloadThread
import os.path
from ftplib import FTP
import ftplib
import re


class AddHyperDeckWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(AddHyperDeckWidget, self).__init__(settings, "Hyperdeck", has_host=True, has_port=False,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-hyperdeck/'
        self.set_info('<P>Make sure remote commands are enabled on the device</P>'
                      '<P>More information <A HREF="' + link + '">Documentation</A></P>')


class HyperDeckDownloadThread(DownloadThread):

    def __init__(self, deck, directory, all_files):
        super(HyperDeckDownloadThread, self).__init__()
        self.directory = directory
        self.deck = deck
        self.files = []
        self.slots = []
        self.all_files = all_files

    def __str__(self):
        return str(self.deck) + " Downloader"

    def add_slot(self, line):
        pos = line.rfind(' ')
        self.slots.append(line[pos+1:])

    def add_file(self, line):

        exp = re.compile(r'^[-rwxs]+\s+\d+\s+\w+\s+\w+\s+\d+\s+\w+\s+\d+\s+[\d:]+\s+(.*)$')
        ret = exp.match(line)
        if not ret:
            print("Skipping non file: " + line)
            return

        self.files.append(ret.group(1))

    def run(self):

        takes = cmd.takes()

        self.set_started()

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        try:
            with FTP(self.deck.host, timeout=2) as ftp:

                ftp.login()
                ftp.cwd('/')

                ftp.retrlines('LIST', self.add_slot)

                for slot in self.slots:
                    # for each deck slot (drive)

                    print("SLOT: " + str(slot))

                    if not self.is_running():
                        break

                    ftp.cwd('/' + slot)

                    ftp.retrlines('LIST', self.add_file)

                    for i, file in enumerate(self.files):

                        if not self.is_running():
                            break

                        file_name = os.path.splitext(file)[0].lower()

                        if not self.all_files:

                            found = False
                            for take in takes:
                                print(take, file_name)
                                if file_name.lower().startswith(take.lower()):
                                    found = True
                                    break
                            if not found:
                                print("Skipping non take: " + str(file_name))
                                continue

                        self.set_current(file)

                        this_file = str(self.deck) + ":" + file

                        local_file = os.path.join(self.directory, file)

                        if os.path.isfile(local_file):
                            # skip existing
                            self.file_done.emit(this_file, self.COPY_SKIP, None)
                        else:
                            # download
                            print("Hyperdeck downloading: " + str(file))
                            try:
                                with open(local_file, 'wb') as fp:
                                    ftp.retrbinary('RETR ' + file, fp.write)
                                self.file_ok(this_file)
                            except IOError as e:
                                self.file_fail(this_file, str(e))
                            except ftplib.all_errors as e:
                                self.file_fail(this_file, str(e))

                        self.tick.emit(float(i) / float(len(self.files)))
        except IOError as e:
            self.message.emit("HyperDeck FTP Error:" + str(e))

        self.set_finished()


class HyperDeck(TcpDevice):

    def __init__(self, name=None, host=None, port=9993):

        self.current_take = None
        self.error = None
        self.command_state = "init"
        self.response_state = None
        self.line_parser = "status"
        self.line_state = None
        self.play_clip = None
        self.multi_line = False
        self.lines = []
        self.code = None
        self.message = None
        self.device_state = "OFFLINE"

        super(HyperDeck, self).__init__(name, host, port)

    def do_update_state(self, state=None, info=None):
        self.device_state = state
        self.info = info
        self.update_state(state, info)

    def get_play_clip_id(self):

        ret = re.match(r"^clip count: ([0-9]+)", self.lines[0])
        if not ret:
            print("Could not get clip count: " + str(self.lines[0]))
            return False

        # clip_count = int(ret.group(1))

        for line in self.lines[1:]:

            parts = line.split(' ')
            if len(parts) != 4:
                print("Could not parse clip: " + line)
                continue

            clip_name = os.path.splitext(parts[1])[0]
            if clip_name == self.play_clip:
                return parts[0]

        return

    def do_read(self):
        data = self.tcp.readAll().data().decode("utf8")
        # print(data)
        for line in data.split("\n"):

            line = line.strip()

            if self.multi_line:
                # keep reading lines of a multi line command until we get to a blank line
                if not line:
                    self.multi_line = False
                    self.read_message()
                    continue
                else:
                    self.lines.append(line)
                    continue

            if not line:
                continue

            ret = re.match(r"^([0-9]{3}) (.*)", line)
            if not ret:
                print("Could not parse: " + line)
                continue

            self.lines = []
            self.code = ret.group(1)
            self.message = ret.group(2)

            if line.endswith(':'):
                self.multi_line = True
                continue

            self.read_message()

    def set_offline(self):
        self.do_update_state("OFFLINE", "")

    def set_error(self, msg):
        self.do_update_state("OFFLINE", msg)

    def post_stop(self):
        self.send('preview: enable: true\n')
        self.set_online()

    def post_play_loop(self):
        self.command_state = "play-starting"
        self.send("play\n")

    def read_message(self):

        """ Interpret the message and error code for status """

        int_code = int(self.code)

        if 100 <= int_code < 199:
            print("Hyperdeck Error, state was: " + str(self.command_state))
            print(self.message)
            self.do_update_state("ERROR", self.message)
            return True

        if self.code == "500" or self.code == "200":
            if self.command_state == "recording":
                self.do_update_state("RECORDING", "")
                self.advance()
                return

            if self.command_state == "play-ok":
                self.do_update_state("PLAYING", "Playing")
                self.advance()
                return

            self.do_update_state("ONLINE", "")
            self.advance()
            return

        if self.command_state == "play-ls":
            if self.code == "205" and len(self.lines) > 0:
                self.advance()
            else:
                self.do_update_state("ERROR", "Error playing")
            return

        #print(f"{self.line_parser}:{self.command_state} - {self.code} {self.message}")
        #for i in self.lines:
        #    print("  " + i)

    def advance(self):

        if self.command_state is None:
            return

        clip_id = ''

        if self.command_state == "play-ls":
            clip_id = self.get_play_clip_id()
            if clip_id is None:
                self.do_update_state("ERROR", "Could not find clip")
                return
            print("CLIP ID: " + str(clip_id))

        states = [('init',       None,                                    None),
                  ('record',    f"record: name: {self.current_take}\n",   "recording"),
                  ('recording',  None,                                    None),
                  ('stop',      "stop\n",                                 "stopping"),
                  ('stopping',  "preview: enable: true\n",                None),
                  ('play',      "clips get\n",                            "play-ls"),
                  ('play-ls',   "playrange set: clip id: " + clip_id + "\n",       "play-goto"),
                  ('play-goto', "goto: clip: start\n",                        "play-single"),
                  ('play-single', "play: loop: true\n",                   "play-ok"),
                  ('play-ok',    None,                                    None),
                  ]

        for current, message, nextstate in states:
            if self.command_state == current:
                self.command_state = nextstate
                if message is not None:
                    self.send(message)
                return

        print("EXIT FROM HYPERDECK ADVANCE WITHOUT CHANGING STATE")
        print("STATE: " + str(self.command_state))

    def command(self, command, arg):

        if command in ["shotName", "takeNumber", "takeName", "set_data_directory", "takeId", 'recording-ok']:
            return None

        self.command_state = command

        if command == "record":
            self.current_take = arg
            self.line_parser = "status"
            self.advance()
            return

        if command == "stop":
            self.play_clip = None
            self.line_parser = "status"
            self.advance()
            return

        if command == "play":
            self.line_parser = "status"
            self.play_clip = arg
            self.advance()
            return None

        print(f"{self.name} ignored the command: {command} {arg}")

    @staticmethod
    def device():
        return "hyperdeck"

    @staticmethod
    def dialog(settings):
        return AddHyperDeckWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        ret = HyperDeck()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = AddHyperDeckWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)

    def has_harvest(self):
        return True

    def harvest(self, directory, all_files):
        return HyperDeckDownloadThread(self, directory, all_files)
