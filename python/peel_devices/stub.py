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


from peel_devices import PeelDeviceBase, SimpleDeviceWidget, DownloadThread
from PySide6 import QtWidgets, QtCore
from PeelApp import cmd

import threading
import time
import random
import sys
import os.path


class StubDownloadThread(DownloadThread):
    """ Simulates a download operation """

    def __init__(self, stub, directory, takes=None):
        super(DownloadThread, self).__init__()
        self.takes = takes
        self.directory = directory
        self.stub = stub
        self.clips = ["clip_%d" % i for i in range(10)]
        self.current_clip = None

    def __str__(self):
        return str(self.stub) + " Downloader"

    def run(self):

        self.set_started()

        if not os.path.isdir(self.directory):
            os.mkdir(self.directory)

        for self.current_i in range(len(self.clips)):

            self.current_clip = self.clips[self.current_i]
            self.set_current(self.current_clip)

            if not self.is_running():
                break

            try:

                major = float(self.current_i) / float(len(self.clips))
                for i in range(100):

                    if not self.is_running():
                        break

                    if self.current_i == 4 and i == 22:
                        raise RuntimeError("Error simulation")

                    minor = float(i) / 100.0 / float(len(self.clips))
                    self.tick.emit(major + minor)
                    self.msleep(10)

                self.file_ok(self.current_clip)

            except Exception as e:
                self.file_fail(self.current_clip, str(e))

        self.set_finished()


class Runner(threading.Thread):

    """ Simulates a device thread operation """

    def __init__(self, state_callback):
        super(Runner, self).__init__()
        self.state = None
        self.state_callback = state_callback
        self.count = 0

    def run(self):
        self.state = "running"

        fail = bool(random.getrandbits(1))
        if fail:
            # Sometimes fail right away
            print("Simulating a failure at the start")
            self.state = "fail"
            self.state_callback()
            return

        self.count = 0

        print("Starting device thread")

        self.state_callback()

        while self.state is not None:

            time.sleep(0.1)

            self.count += 1

            if self.count > 100:
                # fail after 100 ticks.
                print("Simulating a failure during operation")
                self.state = "fail"
                self.state_callback()
                break

            print("Thread is running... %d" % self.count, flush=True)
            sys.stdout.flush()

        self.state_callback()
        print("Thread has finished")

    def stop(self):
        self.state = None

    def __str__(self):
        if self.state is None:
            return "stopped"
        if self.state == "running":
            return "recording"
        if self.state == "fail":
            return "failed"
        return "error"


class StubWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Stub", has_host=False, has_port=False,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class Stub(PeelDeviceBase):

    """ This device tests device functionality by running a thread when the device is in record mode
    The thread may run for 5 seconds and cause a failure state, or it may wait for a stop command.
    The thread and the device will both output some text to the log.
    """

    def __init__(self, name="Stub"):
        super(Stub, self).__init__(name)
        self.thread = None
        self.takes = []

    @staticmethod
    def device():
        """ A unique name for the device - must be different for each subclasses of PeelDeviceBase.
            Used to populate the add-device dropdown dialog and to serialize the class/type """
        return "stub"

    def as_dict(self):
        """ Return the paramters to the constructor as a dict, to be saved in the peelcap file """
        return {'name': self.name}

    def reconfigure(self, name, **kwargs):
        """ Change the settings in the device. """
        self.name = name

    def device_connect(self):
        """ Initialize the device"""
        pass

    def __str__(self):
        if self.thread is None:
            state = "stopped"
        else:
            state = str(self.thread)
        return self.name + " - " + state

    def get_info(self):
        """ return a string to show the state of the device in the main ui """
        if self.thread is None or self.thread.state != "running":
            return ""
        return str(self.thread.count)

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"
            avoid calling update_state() here.  Used to determine if this device
            is working as intended.
         """

        if not self.enabled:
            return "OFFLINE"

        if self.thread is None:
            return "ONLINE"

        if self.thread.state == "running":
            return "RECORDING"

        if self.thread.state == "fail":
            return "ERROR"

        return "ERROR"

    def thread_state_change(self):
        """ Push a state change to the app """
        self.update_state()

    def command(self, command, argument):
        """ Respond to the app asking us to do something """

        print("Stub Command: %s  Argument: %s" % (command, argument))

        if command == "record":
            self.thread = Runner(self.thread_state_change)
            print("Recording take: " + str(argument))
            self.thread.start()

            self.takes.append(argument)

            cmd.setSubjects([f"Subject{n}" for n in range(random.randint(2, 5))])

        if command == "stop":
            print("Stopping stub")
            self.thread.stop()
            self.thread = None

    def teardown(self):
        """ Device is being deleted, shutdown gracefully """
        if self.thread:
            self.thread.stop()

    def thread_join(self):
        """ Called when the main app is shutting down - block till the thread is finished """
        if self.thread:
            self.thread.join()

    @staticmethod
    def dialog_class():
        return StubWidget

    def has_harvest(self):
        """ Return true if harvesting (collecting files form the device) is supported """
        return True

    def harvest(self, directory, all_files):
        """ Copy all the take files from the device to directory """
        return StubDownloadThread(self, directory)

    def list_takes(self):
        return self.takes


if __name__ == "__main__":

    print("running")

    s = Stub("")
    s.command("record", "test")
    time.sleep(10)
    s.command("stop", "")
    s.thread.wait()

    print("done")
