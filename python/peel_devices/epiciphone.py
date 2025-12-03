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

/OSCSetSendTarget <IP:string> <port:int32>
  Sets the OSC send target to the given IP address and port. The app replies to the new OSC send target with the command /OSCSetSendTargetConfirm.

/AddLiveLinkAddress <IP:string> <port:int32>
  Adds a new Live Link target for the app to broadcast blend shape data.

/ClearAllLiveLinkAddresses
  Removes all Live Link targets.

/LiveLinkSubject <name:string>
  Sets the Live Link subject name.

/LiveLinkStreamStart
  Starts streaming data to all Live Link targets.

/LiveLinkStreamStop
  Stops streaming data to Live Link targets.

/BatteryQuery
  Requests the battery level of the device. The app replies to the OSC send target with /Battery <level:float32>.

/ThermalsQuery
  Requests the thermal state of the device. The app replies to the OSC send target with /Thermals <state:int32>.

/Slate <name:string>
  Sets the slate to the given name.

/Take <number:int32>
  Sets the take number to the given value.

/ARSessionStart
  Turns on video and AR tracking. The app replies to the OSC send target with /ARSessionStartConfirm.

/ARSessionStop
  Turns off video and AR tracking. The app replies to the OSC send target with /ARSessionStopConfirm.

/RecordStart <slate:string> <take:int32>
  Starts recording with the given slate and take number. The app replies to the OSC send target with
  /RecordStartConfirm <timecode:string>. Note that at this time the timecode is always 00:00:00.000.

/RecordStop
  Stops recording. The app replies to the OSC send target with
  /RecordStopConfirm <timecode:string> <blendshapesCSV:string> <referenceMOV:string>. You can use the two strings in
  the /Transport command below to copy data from the device.

/Transport <IP:port:string> <path:string>
  Using a path returned by the /RecordStopConfirm command (above), requests the app to transport the contents of the
  file to the specified IP address and port. The app will open a TCP connection to that address and port. It first
  sends an int32 that contains the total size of the file, in big-endian format. It then sends the contents of the file.

/VideoDisplayOn
  Turns the display of the video on.

/VideoDisplayOff
  Turns the display of the video off. Tracking and recording can and will still occur.

/AppActivated
  The app sends this to the OSC send target when the it becomes active on the phone. That is, when it is first started, brought to foreground, and so on.

/AppDeactivated
  The app sends this to the OSC send target when the it becomes inactive on the phone. That is, when it is killed, sent to background, and so on.

"""

from pythonosc import dispatcher, osc_server, udp_client
from peel_devices import PeelDeviceBase, DownloadThread, FileItem, BaseDeviceWidget
from PySide6 import QtWidgets, QtCore
import threading, socket, struct
import os
import os.path
import array
from . import device_util
from PeelApp import cmd


def get_format(args, name, take_number):
    # Prepare the generic name for the take file names, for guessing files that did not respond
    # Uses the known take name and take number (int) to generate a pattern that can be used for
    # files that did not respond to the record command but still generated a file
    ret = []
    for arg in args:
        fixed = arg.replace(name, "#name#")
        fixed = fixed.replace(str(take_number) + "_", "#number#_")
        fixed = fixed.replace("_" + str(take_number), "_#number#")
        ret.append(fixed)
    return ret


# https://docs.unrealengine.com/en-US/AnimatingObjects/SkeletalMeshAnimation/FacialRecordingiPhone/index.html


class AddWidget(BaseDeviceWidget):
    def __init__(self, settings):
        super(AddWidget, self).__init__(settings)
        form_layout = QtWidgets.QFormLayout()

        self.setStyleSheet("Label: { color: black}")
        self.setWindowTitle("Add Epic IPhone")

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-unreal-live-link-face/'

        msg = '<P>More information: <A HREF="' + link + '">Documentation</A></P>'
        msg += "<P>Use the following OSC settings in the "
        msg += "<A HREF=\"https://apps.apple.com/app/id1495370836\">iOS app</A>:</P>\n"
        msg += "<PRE>"
        msg += "  <B>Target IP Address:</B> The \"Listen Ip\" of this pc\n"
        msg += "  <B>Target Port:</B> The \"Listen Port\"\n"
        msg += "  <B>Listener IP Address:</B> The \"Phone Ip\"\n"
        msg += "  <B>Listener Port:</B> \"Phone OSC Port\"\n"
        msg += "</PRE>"
        msg += "<P>Make sure each one has a unique 'Listener Port' in PeelCapture</P>"
        self.set_info(msg)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(settings.value("EpicPhoneName", "IPhone"))
        form_layout.addRow("Name", self.name)

        self.phone_ip = QtWidgets.QLineEdit()
        self.phone_ip.setText(settings.value("EpicPhoneIp", "192.168.1.100"))
        self.phone_ip.setToolTip("Phone ip can be found in phone wifi settings")
        form_layout.addRow("Phone Ip", self.phone_ip)

        self.phone_port = QtWidgets.QLineEdit()
        self.phone_port.setText(settings.value("EpicPhonePort", "8000"))
        self.phone_port.setToolTip("OSC port is listed in Live Link Face app settings")
        form_layout.addRow("Phone OSC Port", self.phone_port)

        # Show all must be false as we need to send the phone a specific ip address to send data back to
        self.listen_ip = device_util.InterfaceCombo(show_all=False)
        self.listen_ip.setToolTip("Listen ip should start with the same digits as phone port")
        self.listen_ip.setCurrentText(settings.value("EpicPhoneListenIp", ""))
        form_layout.addRow("Listen Ip", self.listen_ip)

        self.listen_port = QtWidgets.QLineEdit()
        self.listen_port.setText(settings.value("EpicPhoneListenPort", "6000"))
        self.listen_port.setToolTip("Port to listen on PC, may need to be open on the firewall")
        form_layout.addRow("Listen Port", self.listen_port)

        self.format = QtWidgets.QLineEdit("Format")
        self.format.setText(settings.value("EpicPhoneFormat", "{take}"))
        form_layout.addRow("Format", self.format)

        self.mha = QtWidgets.QCheckBox("Meta Human Animator")
        self.mha.setChecked(bool(settings.value("EpicPhoneMHA")))
        form_layout.addRow("", self.mha)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.phone_ip.setText(device.phone_ip)
        self.phone_port.setText(str(device.phone_port))
        self.listen_ip.setCurrentText(device.listen_ip)
        self.listen_port.setText(str(device.listen_port))
        self.mha.setChecked(device.mha)
        self.format.setText(device.formatting.formatting)

    def update_device(self, device):
        # Update the device with the data in the text fields
        try:
            device.name = self.name.text()
            device.phone_ip = self.phone_ip.text()
            device.phone_port = int(self.phone_port.text())
            device.listen_ip = self.listen_ip.ip()
            device.listen_port = int(self.listen_port.text())
            device.mha = self.mha.isChecked()
            device.formatting.formatting = self.format.text()
        except ValueError:
            QtWidgets.QMessageBox(self, "Error", "Invalid port")
            return False

        return True

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("EpicPhoneName", self.name.text())
        self.settings.setValue("EpicPhoneIp", self.phone_ip.text())
        self.settings.setValue("EpicPhonePort", self.phone_port.text())
        self.settings.setValue("EpicPhoneListenIp", self.listen_ip.ip())
        self.settings.setValue("EpicPhoneListenPort", self.listen_port.text())
        self.settings.setValue("EpicPhoneMHA", self.mha.isChecked())
        self.settings.setValue("EpicPhoneFormat", self.format.text())

        return True

    def get_name(self) -> str:
        return self.name.text()


class EpicIPhone(PeelDeviceBase):

    def __init__(self, name="IPhone"):
        super(EpicIPhone, self).__init__(name)
        self.phone_ip = "192.168.1.100"
        self.phone_port = 8000
        self.listen_ip = "0.0.0.0"
        self.listen_port = 6000
        self.server = None
        self.thread = None
        self.take_number = None
        self.last_take_number = None
        self.battery = None
        self.thermals = None
        self.info = ""
        self.state = "OFFLINE"
        self.client = None
        self.ping_timer = None
        self.got_response = False
        self.mha = False
        self.takes = {}
        self.current_take = None
        self.current_name = None
        self.query = None
        self.dispatcher = None

    @staticmethod
    def device():
        return "epic-iphone"

    def as_dict(self):

        ret = super().as_dict()

        ret['phone_ip'] = self.phone_ip
        ret['phone_port'] = self.phone_port
        ret['listen_ip'] = self.listen_ip
        ret['listen_port'] = self.listen_port
        ret['takes'] = self.takes
        ret['mha'] = self.mha

        return ret

    def reconfigure(self, name, **kwargs):
        if not super().reconfigure(name, **kwargs):
            return False

        self.phone_ip = kwargs.get('phone_ip')
        self.phone_port = kwargs.get('phone_port')
        self.listen_ip = kwargs.get('listen_ip')
        self.listen_port = kwargs.get('listen_port')
        self.takes = kwargs.get('takes')
        self.mha = kwargs.get('mha')

        return True

    def teardown(self):
        if self.thread is not None and self.server is not None:
            cmd.writeLog("Stopping current iphone OSC Server")
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.thread = None
            cmd.writeLog("OSC server stopped")

        if self.ping_timer:
            self.ping_timer.stop()

    def connect_device(self):

        self.teardown()

        if self.dispatcher is None:
            # Create the dispatcher if it doesn't already exist
            self.dispatcher = dispatcher.Dispatcher()
            self.dispatcher.set_default_handler(self.callback, True)

        if self.ping_timer is None:
            # Create the timer if it does not already exist
            self.ping_timer = QtCore.QTimer()
            self.ping_timer.timeout.connect(self.ping_timeout)
            self.ping_timer.setInterval(8000)
            self.ping_timer.setSingleShot(False)

        self.ping_timer.start()

        cmd.writeLog("Creating udp client")
        self.client = udp_client.SimpleUDPClient(self.phone_ip, self.phone_port)

        try:
            cmd.writeLog("Starting OSC Server: " + str(self.listen_ip) + ":" + str(self.listen_port))
            self.server = osc_server.ThreadingOSCUDPServer((self.listen_ip, self.listen_port), self.dispatcher)
        except IOError as e:
            cmd.writeLog("Could not start OSC Server: " + str(e))
            self.state = "ERROR"
            self.info = "OSC Error"
            return

        cmd.writeLog("Starting iphone thread")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

        if self.listen_ip != "0.0.0.0":
            cmd.writeLog("TARGET: " + str(self.listen_ip) + " " + str(self.listen_port))
            self.client.send_message("/OSCSetSendTarget", [self.listen_ip, self.listen_port])
            self.client.send_message('/BatteryQuery', 1)
            self.client.send_message('/ThermalsQuery', 1)

    def command(self, command, arg):

        if command == "takeNumber":
            self.take_number = int(arg)

        if command == "record":
            if self.take_number is None:
                self.state = "ERROR"
                self.info = "No take#"
                raise RuntimeError("Take number not set while starting recording")

            self.current_take = arg
            self.last_take_number = self.take_number
            self.current_name = self.format_take(arg)
            self.client.send_message('/RecordStart', (self.current_name, self.take_number))

            self.takes[self.current_take] = arg

        if command == "stop":
            self.client.send_message('/RecordStop', 1)

    def callback(self, address, command, *args):

        cmd.writeLog(f"{self.name} callback from {address}  {command}  {args}")

        self.got_response = True

        if command == "/OSCSetSendTargetConfirm":
            self.state = "ONLINE"
            self.push_state()
            return

        if command == "/RecordStartConfirm":
            self.state = "RECORDING"
            self.push_state()
            return

        if command == "/RecordStopConfirm":
            # timecode, csv, video = args
            cmd.writeLog("Adding " + str(self.current_take) + " " + str(args))

            self.takes[self.current_take] = args

            self.state = "ONLINE"
            self.push_state()
            return

        if command == "/Battery":

            if self.state == "OFFLINE":
                self.state = "ONLINE"

            try:
                self.battery = float(args[0])
            except ValueError:

                cmd.writeLog("Could not parse iphone battery level: " + str(args))
                self.state = "ERROR"

            self.push_state()

        if command == "/Thermals":

            if self.state == "OFFLINE":
                self.state = "ONLINE"

            self.thermals = args[0]
            self.push_state()

    def push_state(self):

        ret = []

        if self.battery is not None:
            if self.battery is not None:
                pc = int(self.battery * 100.0)
                ret.append(f"Bat: {pc}%")

        if self.thermals is not None:
            ret.append(f"Therm: " + str(self.thermals))

        if self.takes is not None and len(self.takes) > 0:
            ret.append("Clips: %d" % len(self.takes))

        self.info = " / ".join(ret)
        self.update_state(self.state, self.info)

    def ping_timeout(self):

        # Called every 8 seconds

        if not self.got_response:
            # There has been no messages sent since the last ping, set the device to being offline
            if self.state != "OFFLINE":
                self.state = "OFFLINE"
                self.update_state(self.state, "")

        if self.client is None:
            cmd.writeLog("No client while sending ping")
            return

        self.got_response = False

        # Alternate query
        if self.query != "Battery":
            self.client.send_message('/BatteryQuery', 1)
            self.query = "Battery"
        else:
            self.client.send_message('/ThermalsQuery', 1)
            self.query = "Thermal"

    def get_state(self, reason=None):
        if not self.enabled:
            self.ping_timer.stop()
            return "OFFLINE"

        return self.state

    def get_info(self, reason=None):
        return self.info

    def __str__(self):
        return self.name

    def has_harvest(self):
        return True

    def harvest(self, directory):
        # Create the harvest worker / thread
        return IPhoneDownloadThread(self, directory, self.listen_port)

    @staticmethod
    def dialog_class():
        return AddWidget

    def list_takes(self):
        return self.takes.keys()

    def generic_take_name(self):
        # get the generic/template form for the take name, in case we need to guess the filename later
        # This allows us to use any take name to find others that we didn't get a udp response from
        # the phone for
        for take, args in self.takes.items():
            if len(args) == 3:
                # get the take number (int) for this take by name
                take_number = cmd.takeNumberForTake(take)

                # Make the generic template for the take name
                return get_format(args, self.format_take(take), take_number)

        return None


class IPhoneDownloadThread(DownloadThread):

    def __init__(self, phone, directory, listen_port=8444):
        super(IPhoneDownloadThread, self).__init__(directory)
        self.phone = phone
        self.listen_port = listen_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)

        # Allow immediate reuse of the address after close
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            # Not all platforms support SO_REUSEPORT
            pass

        self.socket.bind((phone.listen_ip, self.listen_port))

    def __str__(self):
        return str(self.phone) + " Downloader"

    def teardown(self):
        if self.socket:
            self.socket.close()
        super(IPhoneDownloadThread, self).teardown()

    def process(self):

        print("Iphone Process Started")
        self.create_local_dir()
        self.set_started()

        # get the generic form for the take name, in case we need to guess the filename later
        args_format = self.phone.generic_take_name()

        if args_format:
            cmd.writeLog("File template: {args_format}")

        # for each take consider for downloading
        for take in self.valid_takes:

            take_file = self.phone.format_take(take)

            args = []

            if take not in self.phone.takes and args_format is not None:

                # We didn't get a response from the phone, make up the file name
                # using the parsed template

                take_number = cmd.takeNumberForTake(take)

                if take_number == -1:
                    continue

                for arg in args_format:
                    value = arg.replace("#name#", take_file)
                    value = value.replace("#number#", str(take_number))
                    args.append(value)

                cmd.writeLog("Created args as: " + str(args))

            else:

                args = self.phone.takes[take]
                cmd.writeLog("Using args: " + str(args))

            if len(args) != 3:
                cmd.writeLog("Could not determine file name for : " + str(take))
                continue

            # Support (timecode, mov, csv) or (timecode, csv, mov) order
            mov = None
            csv = None
            for p in args[1:]:
                if p.lower().endswith(".mov"):
                    mov = p
                elif p.lower().endswith(".csv"):
                    csv = p

            if mov is None:
                print("No mov file for " + str(take))
                continue

            base, mov_name = os.path.split(mov)

            if self.phone.mha:

                for f in ["audio_metadata.json", "depth_data.bin", "depth_metadata.mhaical",
                          "frame_log.csv", "take.json", "thumbnail.jpg", "video_metadata.json"]:
                    self.add_file(base + "/" + f, take_file + "/" + f, take)
                self.add_file(mov, take + "/" + mov_name, take)

            else:
                self.add_file(csv, take_file + ".csv", take)
                self.add_file(mov, take_file + ".mov", take)

        my_address = f"{self.phone.listen_ip}:{self.listen_port}"

        self.log(f"Downloading {len(self.files)} iphone files for {len(self.valid_takes)} takes")

        try:
            self.socket.listen()

            for i, this_file in enumerate(self.files):

                if not self.is_running():
                    break

                self.set_current(i)

                this_name = f"{self.phone.name}:{this_file.local_file}"

                # Skip existing
                full_path = self.local_path(this_file.local_file, this_file.status)

                if os.path.isfile(full_path):
                    self.file_skip(this_name)
                    continue

                out_dir = os.path.dirname(full_path)
                if not os.path.isdir(out_dir):
                    try:
                        os.makedirs(out_dir)
                    except OSError as e:
                        self.file_fail(this_name, "Could not create directory")
                        continue

                # Tell the iphone we want it to send us a file
                print(f"Iphone getting: {this_file.remote_file}")
                self.phone.client.send_message("/Transport", (my_address, this_file.remote_file))
                self.current_size = 0

                try:
                    # Wait for the connection from the phone sending the file
                    conn, addr = self.socket.accept()
                except socket.timeout:
                    self.log("No response for file: " + this_file.remote_file)
                    self.file_fail(this_name, "Timeout")
                    conn = None

                if conn:
                    try:
                        conn.settimeout(1)
                        linger = array.array("i", [1, 0])
                        conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger)

                        # Get the file
                        with open(full_path, "wb") as local_fp:
                            self.read(conn, this_file, local_fp)

                        if this_file.complete == self.COPY_OK:
                            self.file_ok(this_name)
                        elif this_file.complete == self.COPY_FAIL:
                            self.file_fail(this_name, this_file.error)

                        if this_file.complete != self.COPY_OK:
                            if os.path.exists(full_path):
                                os.unlink(full_path)

                    finally:
                        conn.close()

            else:
                self.set_current(len(self.files))

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log("Exception:\n" + traceback.format_exc())

        print("Iphone finished")
        self.set_finished()

    def read(self, conn, this_file, fp):

        buffer_size = 1024 * 1024

        # IOS device has connected, get the file

        this_file.complete = self.COPY_FAIL

        try:
            size_header = conn.recv(4)

            if not size_header or len(size_header) < 4:
                this_file.error = "Read Error (no header)"
                return

            this_file.file_size = struct.unpack(">i", size_header)[0]
            this_file.data_size = 0
            self.set_file_total_size(this_file.file_size)

            if this_file.file_size == 0:
                this_file.error = "Zero sized file"
                return

            while self.is_running():

                try:
                    data = conn.recv(buffer_size)
                except socket.timeout:
                    break

                if not data:
                    break

                fp.write(data)
                this_file.data_size += len(data)
                self.add_bytes(len(data))

            if this_file.data_size != this_file.file_size:
                this_file.error = "Incomplete data"
            else:
                this_file.complete = self.COPY_OK

        except Exception as e:
            import traceback
            this_file.error = "Read Error:\n" + traceback.format_exc()





