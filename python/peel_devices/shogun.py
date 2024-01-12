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


import sys
from shogun_live_api import application_services, CaptureServices, PlaybackServices, SubjectServices
from vicon_core_api import Client, RPCError

from PySide6 import QtWidgets, QtCore

from peel_devices import PeelDeviceBase, SimpleDeviceWidget

import time
import os.path, os
"""
capture_services:
    set_capture_folder       capture_folder
  * set_capture_name         capture_name
  * set_capture_description  capture_description
  * set_capture_notes        capture_notes
  
    add_take_info_changed_callback
    set_capture_processed_data_enabled
    capture_processed_data_enabled
    set_capture_video_enabled
    capture_video_enabled
    add_capture_options_changed_callback
    set_start_on_timecode_enabled
    start_on_timecode_enabled
    set_start_timecode
    start_timecode
    set_stop_on_timecode_enabled
    stop_on_timecode_enabled
    set_stop_timecode
    stop_timecode
    set_limit_capture_duration_enabled
    limit_capture_duration_enabled
    set_duration_limit_in_seconds
    duration_limit_in_seconds
    add_auto_capture_options_changed_callback
  * start_capture
  * stop_capture
    cancel_capture
    latest_capture_state
    latest_capture_name
    latest_capture_timecode  
    latest_capture_file_paths
    latest_capture_errors
    add_latest_capture_changed_callback
    remove_callback
  
playback_services:
    CaptureMetadata()
    EOutputMode()
    PlaybackState()
      capture_list
      state
      enter_capture_review
      enter_live_review
      exit_review
      play
      pause
      tick
      set_tick
      step_frames
      loop_enabled
      set_loop_enabled
      
      add_capture_list_changed_callback
      add_parameter_changed_callback
      add_state_changed_callback
      remove_callback
   
"""


class ShogunWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(ShogunWidget, self).__init__(settings, "Shogun", has_host=True, has_port=False,
                                           has_broadcast=False, has_listen_ip=False, has_listen_port=False,
                                           has_set_capture_folder=True)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-vicon-shogun/'
        msg = '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)


class ViconShogun(PeelDeviceBase):

    def __init__(self, name, host, set_capture_folder=False):
        super(ViconShogun, self).__init__(name)
        self.host = host
        self.client = None
        self.capture = None
        self.playback = None
        self.error = None
        self.record_id = None
        self.play_id = None
        self.subject = None
        self.set_capture_folder = set_capture_folder
        self.capture_folder = None
        self.takes = []
        self.connect()

    @staticmethod
    def device():
        return "shogun"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'set_capture_folder': self.set_capture_folder
                }

    def connect(self):
        try:
            self.client = Client(self.host)
            self.capture = CaptureServices(self.client)
            self.playback = PlaybackServices(self.client)
            self.subject = SubjectServices(self.client)
        except Exception as e:
            self.client = None
            self.capture = None
            self.capture = None
            print("Shogun could not connect: " + str(e))

    def __str__(self):
        return self.name

    def teardown(self):
        pass

    def get_subjects(self):
        if self.subject is None:
            return []
        state, subjects = self.subject.subjects()
        if not state:
            print("Could not get subjects from shogun")

        state, enabled = self.subject.enabled_subjects()

        ret = []

        for name in subjects:
            state, subject_type = self.subject.subject_type(name)

            if subject_type != SubjectServices.ESubjectType.ELabelingCluster:
                if subject_type == SubjectServices.ESubjectType.EGeneral:
                    ret.append((name, "actor", name in enabled))
                if subject_type == SubjectServices.ESubjectType.ERigidObject:
                    ret.append((name, "prop", name in enabled))

        return ret

    def set_subject(self, name, enabled):
        self.subject.set_subject_enabled(name, enabled)

    def get_state(self):

        if self.error is not None:
            return "ERROR"

        if not self.enabled:
            return "OFFLINE"

        if self.capture is None:
            return "OFFLINE"

        try:
            ret, id, state = self.capture.latest_capture_state()
            # print(f"SHOGUN STATE: {ret} {id} {state}")
            if state in [CaptureServices.EState.EStarted]:
                return "RECORDING"

            ret, state = self.playback.state()
            if state.mode == PlaybackServices.EOutputMode.ELive:
                return "ONLINE"

            return "OFFLINE"

        except RPCError as e:
            print("Shotgun RPC error - make sure shotgun post is not running")
            print(str(e))
            self.error = str(e)
            return "ERROR"

        except Exception as e:
            print(str(e))
            self.error = str(e)
            return "ERROR"

    def get_info(self):

        if self.error is not None:
            return self.error

        return f"{len(self.takes)} takes"

    def list_takes(self):
        return self.takes

    def get_takes(self):

        if self.playback is None:
            return

        try:
            res, items = self.playback.capture_list()
            self.takes = [i.capture_name for i in items]

        except RPCError as e:
            print("Shotgun RPC error - make sure shotgun post is not running")
            print(str(e))
            self.error = str(e)
            return "ERROR"

        except Exception as e:
            print(str(e))

    # def takes(self):
    #     ret = []
    #     if self.capture_folder:
    #         for i in os.listdir(self.capture_folder):
    #             if i.lower().endswith(".x2d"):
    #                 ret.append(os.path.splitext(os.path.basename(i))[0])
    #     return ret

    def command(self, command, arg):

        print("SHOGUN", command, arg)

        if self.client is None:
            print("No client")
            return

        self.error = None

        if command == "play" and self.record_id is None:
            if self.play_id is not None:
                self.playback.exit_review()
                time.sleep(0.2)

            if arg is None or len(arg) == 0:
                self.playback.enter_live_review()
                self.playback.play()
                self.play_id = True
            else:
                self.playback.enter_capture_review(arg)
                self.playback.play()
                self.play_id = arg

        if command == "record":
            ret = self.capture.set_capture_name(arg)
            if not ret:
                print("Could not set capture name for shogun")
                self.error = "Capture Name Error"
                return
            ret, self.record_id = self.capture.start_capture()
            if not ret:
                self.error = "Could not record"
                print("Shogun could not record")
                self.update_state("ERROR", "Could not record")
                return
            else:
                print("Shogun recording ID: " + str(self.record_id))

        if command == "stop":
            ret = True
            if self.record_id:
                ret = self.capture.stop_capture(self.record_id)
                self.record_id = None
            if self.play_id:
                ret = self.playback.exit_review()
                self.play_id = None

            if not ret:
                self.error = "Could not stop"

        if command == "description":
            self.capture.set_capture_description(arg)

        if command == "notes":
            self.capture.set_capture_notes(arg)

        if command == "set_data_directory" and self.set_capture_folder:
            print("Setting shogun data directory: ", arg)
            capture_dir = arg + "/" + self.name
            capture_dir = capture_dir.replace("/", os.path.sep)
            if not os.path.isdir(capture_dir):
                print("Creating directory: " + str(capture_dir))
                os.makedirs(capture_dir)
            self.capture.set_capture_folder(capture_dir)
            self.capture_folder = capture_dir

        # Delay the update state as shogun does not respond with the correct
        # state right away
        QtCore.QTimer.singleShot(250, self.update_state)

    @staticmethod
    def dialog(settings):
        return ShogunWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        return ViconShogun(widget.name.text(), widget.host.text(), widget.set_capture_folder.isChecked())

    def edit(self, settings):
        dlg = ShogunWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)

    def reconfigure(self, name, host=None, set_capture_folder=False):
        self.name = name
        self.host = host
        self.set_capture_folder = set_capture_folder
        self.connect()
        self.update_state()



