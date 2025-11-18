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
from peel_devices import SimpleDeviceWidget, DownloadThread
from peel_devices.tcp import TcpDevice
import os.path
from ftplib import FTP
import ftplib
import re
import os

class AddHyperDeckWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(AddHyperDeckWidget, self).__init__(settings, "Hyperdeck", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False,
                                                 has_formatting=True, has_playback=True)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-hyperdeck/'
        self.set_info('<P>Make sure remote commands are enabled on the device</P>'
                      '<P>More information <A HREF="' + link + '">Documentation</A></P>')


class HyperDeckDownloadThread(DownloadThread):

    def __init__(self, deck, directory, formatting):
        super(HyperDeckDownloadThread, self).__init__(directory, formatting)
        self.deck = deck
        self.slots = []

    def __str__(self):
        return str(self.deck) + " Downloader"

    def add_slot(self, line):
        pos = line.rfind(' ')
        self.slots.append(line[pos+1:])

    def add_file(self, line):
        parts = line.split(maxsplit=8)  # split into at most 9 parts
        if len(parts) < 9:
            cmd.writeLog("Skipping non-file: " + line)
            return

        file = parts[8]  # the 9th field = filename (can contain spaces intact)

        # Filter files for downloading
        if not self.download_take_check(os.path.splitext(file)[0]):
            cmd.writeLog(f"Skipping: {file} for mode: {self.download_mode}")
            return

        self.files.append(file)

    def process_slot(self, ftp, slot):

        # for each deck slot (drive)

        self.create_local_dir()

        cmd.writeLog("SLOT: " + str(slot))

        ftp.cwd('/' + slot)

        # Clear files out for each slot
        self.files = []

        ftp.retrlines('LIST', self.add_file)

        for i, file in enumerate(self.files):

            if not self.is_running():
                break

            self.set_current(i)

            this_file = str(self.deck) + ":" + file

            local_file = self.local_path(file)

            if os.path.isfile(local_file):
                # skip existing
                self.file_skip(this_file)
            else:
                # download
                cmd.writeLog("Hyperdeck downloading: " + str(file))
                try:

                    self.current_size = 0
                    self.set_file_total_size(ftp.size(file))

                    with open(local_file, 'wb') as fp:

                        def write(data):
                            fp.write(data)
                            self.add_bytes(len(data))

                        ftp.retrbinary('RETR ' + file, write)

                    self.file_ok(this_file)
                except IOError as e:
                    if os.path.exists(local_file):
                        os.remove(local_file)
                    self.file_fail(this_file, str(e))
                except ftplib.all_errors as e:
                    self.file_fail(this_file, str(e))

        else:
            self.set_current(len(self.files))

    def process(self):

        self.set_started()

        self.create_local_dir()

        try:
            with FTP(self.deck.host, timeout=2) as ftp:

                ftp.login()
                ftp.cwd('/')

                self.slots = []
                self.files = []

                ftp.retrlines('LIST', self.add_slot)

                for slot in self.slots:

                    if not self.is_running():
                        break

                    self.process_slot(ftp, slot)

        except IOError as e:
            self.message.emit("HyperDeck FTP Error:" + str(e))
        except ftplib.all_errors as e:
            self.message.emit("HyperDeck FTP Error:" + str(e))

        self.set_finished()



class HyperDeck(TcpDevice):
    """
    Hyperdeck Device
    - Request dispatch (run_action / enqueue / advance)
    - TCP input framing (do_read)
    - Response parsing (parse_status_line / parse_multiline_block)
    - Message interpretation (handle_message_code)

    Multi-line messages follow HyperDeck protocol:
        <code> <message>:
            <line>
            <line>
        <blank line>
    """

    STATUS_RE = re.compile(r"^([0-9]{3}) (.*)")
    CLIP_COUNT_RE = re.compile(r"^clip count: ([0-9]+)")
    CLIP_ID_RE = re.compile(r"^([0-9]+):")
    TIMECODE_RE = re.compile(r".*([0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{2})$")

    def __init__(self, name="Hyperdeck", *args, **kwargs):
        super().__init__(name, *args, **kwargs)

        self.host = "192.168.1.100"
        self.port = 9993

        # Device visible state
        self.device_state = "OFFLINE"
        self.error = None
        self.info = ""
        self.resolution = None
        self.record_time = None

        # Playback / recording state
        self.playback = True
        self.current_take = None
        self.current_action = "init"
        self.speed = 100
        self.play_clip = None
        self.clip_id = None

        # Protocol parsing state
        self.code = None
        self.message = None
        self.lines = []
        self.multi_line = False

        # Command queue
        self.command_queue = None

    # ----------------------------------------------------------------------
    # Configuration / general overrides
    # ----------------------------------------------------------------------

    def reconfigure(self, name, **kwargs):
        self.playback = kwargs.get("playback", True)
        return super().reconfigure(name, **kwargs)

    def as_dict(self):
        ret = super().as_dict()
        ret["playback"] = self.playback
        return ret

    # ----------------------------------------------------------------------
    # Device state tracking
    # ----------------------------------------------------------------------

    def do_update_state(self, state=None):
        """Update device state & formatted info string."""
        if state:
            self.device_state = state

        parts = []
        if self.resolution:
            parts.append(self.resolution)

        if self.record_time:
            try:
                t = int(self.record_time)
                parts.append(f"{t//3600}:{(t%3600)//60}:{t%60} avail")
            except ValueError:
                print("Could not parse record_time:", self.record_time)

        self.info = " ".join(parts)
        self.update_state(self.device_state, self.info)

    def set_error(self, msg):
        self.error = msg
        self.update_state("ERROR", msg)

    def set_offline(self):
        self.do_update_state("OFFLINE")

    def get_info(self, reason=None):
        if reason == "refresh":
            self.enqueue("info")
        return self.error if self.device_state == "ERROR" else self.info

    # ----------------------------------------------------------------------
    # TCP Reading + Parsing
    # ----------------------------------------------------------------------

    def do_read(self):
        """Read raw TCP bytes, split into lines, classify, collect."""
        data = self.tcp.readAll().data().decode("utf8", errors="replace")

        for raw in data.split("\n"):
            line = raw.strip()

            # --- End of multiline block ---
            if not line:
                if self.multi_line:
                    self.multi_line = False
                    self.read_message()
                    self.lines.clear()
                    self.advance()
                continue

            # --- Status line: "205 Something" ---
            m = self.STATUS_RE.match(line)
            if m:
                self._start_new_message(m.group(1), m.group(2))
                continue

            # --- Multi-line content ---
            if self.multi_line:
                self.lines.append(line)
            else:
                cmd.writeLog("Unparsed line: " + line)

    def _start_new_message(self, code, message):
        """Begin new message block."""

        self.code = code
        self.message = message
        self.lines.clear()

        if message.endswith(":"):
            # multi-line block begins, wait for blank line to finish
            self.multi_line = True
            return
        else:
            # single-line message – safe to handle immediately
            self.read_message()
            self.advance()
            return

    # ----------------------------------------------------------------------
    # Message Handling
    # ----------------------------------------------------------------------

    def read_message(self):
        """Interpret status code + lines."""
        code = int(self.code)
        self.code = None  # reset

        # --- Standard HyperDeck code handlers ---
        if 100 <= code < 199:
            cmd.writeLog(f"HyperDeck protocol error during {self.current_action}: {self.message}")
            self.set_error(self.message)
            return

        if code == 201:  # busy
            self.error = "busy"
            self.do_update_state()
            return

        if code == 202:  # recording time
            for line in self.lines:
                if line.startswith("recording time:"):
                    self.record_time = line[15:].strip()
            self.do_update_state()
            return

        if code == 208:  # input video format
            for line in self.lines:
                if line.startswith("input video format:"):
                    self.resolution = line[19:].strip()
            self.do_update_state()
            return

        if code == 209:
            self.set_error("No Media")
            return

        if code == 502:
            self.set_error("Bad Command")
            return

        # Successful standard command (200 or 500)
        if code in (200, 500):
            self.error = None
            if self.current_action == "record":
                self.do_update_state("RECORDING")
                return
            if self.current_action == "play":
                self.do_update_state("PLAYING")
                return
            self.do_update_state("ONLINE")
            return

        # Special ls completion
        if code == 205 and self.current_action == "ls":

            self.clip_id = self.get_play_clip_id()

            if self.clip_id is None:
                self.set_error("Clip not found")
                self.command_queue = None
            return

        # Unknown
        cmd.writeLog(f"Unknown HyperDeck response: {self.current_action} - {code} {self.message}")

    # ----------------------------------------------------------------------
    # Clip listing / parsing
    # ----------------------------------------------------------------------

    def get_play_clip_id(self):
        """Parse a clip ID by matching clip name."""
        if not self.lines:
            cmd.writeLog("No lines for clip parsing")
            return None

        # First line: clip count
        if not self.CLIP_COUNT_RE.match(self.lines[0]):
            cmd.writeLog("Could not parse clip count: " + self.lines[0])
            return None

        cmd.writeLog(f"Searching for clip name: {self.play_clip}")

        for line in map(str.strip, self.lines[1:]):
            id_match = self.CLIP_ID_RE.match(line)
            if not id_match:
                continue

            take_id = id_match.group(1)
            rest = line[len(take_id) + 1:].strip()

            # remove last TC
            tc1 = self.TIMECODE_RE.match(rest)
            if not tc1:
                continue
            rest = rest[:-11].strip()

            # remove 2nd TC
            tc2 = self.TIMECODE_RE.match(rest)
            if not tc2:
                continue
            rest = rest[:-11].strip()

            clip_name = os.path.splitext(rest)[0]
            if clip_name == self.play_clip:
                cmd.writeLog(f"Found clip id = {take_id}")
                return take_id

        return None

    # ----------------------------------------------------------------------
    # Command Queue Management
    # ----------------------------------------------------------------------

    def enqueue(self, commands):
        """Run immediately (str) or queue a sequence (list)."""
        if isinstance(commands, str):
            self.command_queue = None
            self.run_action(commands)
            return

        self.command_queue = list(commands)
        cmd.writeLog("COMMAND QUEUE: " + str(self.command_queue))
        self.run_action(self.command_queue.pop(0))

    def advance(self):
        """Continue queued command sequence."""
        if not self.current_action:
            return

        if self.command_queue:
            self.run_action(self.command_queue.pop(0))

    # ----------------------------------------------------------------------
    # Command Execution (outbound)
    # ----------------------------------------------------------------------

    def run_action(self, action):
        """Map logical action to actual HyperDeck protocol strings."""
        cmd.writeLog(f">>> Action: {action}")
        self.current_action = action

        if action == "record":
            self.send(f"record: name: {self.current_take}\n")

        elif action == "stop":
            self.send("stop\n")

        elif action == "preview-enable":
            self.send("preview: enable: true\n")

        elif action == "ls":
            self.send("clips get\n")

        elif action == "set-clip":
            self.send(f"playrange set: clip id: {self.clip_id}\n")

        elif action == "goto-start":
            self.send("goto: clip: start\n")

        elif action == "goto-end":
            self.send("goto: clip: end\n")

        elif action == "play":
            self.send(f"play: loop: true speed: {self.speed}\n")

        elif action in ("transport info", "slot info"):
            self.send(action + "\n")

    # ----------------------------------------------------------------------
    # Public Command Interface
    # ----------------------------------------------------------------------

    def command(self, command, arg):
        super().command(command, arg)
        self.current_action = command

        if command in ["shotName", "takeNumber", "takeName",
                       "set_data_directory", "takeId", "recording-ok"]:
            return

        if command == "record":
            self.current_take = self.format_take(arg)
            self.enqueue(["transport info", "slot info", "record"])
            return

        if command == "stop":
            self.play_clip = None
            self.enqueue(["stop", "preview-enable", "transport info", "slot info"])
            return

        if command == "play" and self.playback:
            self.play_clip = self.format_take(arg)
            self.speed = 100
            self.enqueue(["ls", "set-clip", "goto-start", "play"])
            return

        if command == "pause":
            self.speed = 0 if arg == "on" else 100
            self.enqueue("play")
            return

        if command == "move":
            v = int(arg)
            self.speed = 100 if v == 0 else (v + 1) * 50 if v > 0 else v * 50
            self.enqueue("play")
            return

        if command == "goto":
            self.enqueue("goto-start" if arg == "start" else "goto-end")
            return

        cmd.writeLog(f"{self.name} ignored command: {command} {arg}")

    # ----------------------------------------------------------------------

    @staticmethod
    def device():
        return "hyperdeck"

    @staticmethod
    def dialog_class():
        return AddHyperDeckWidget

    def has_harvest(self):
        return True

    def harvest(self, directory):
        return HyperDeckDownloadThread(self, directory, self.formatting)
