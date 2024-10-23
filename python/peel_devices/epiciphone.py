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
from . import device_util
from PeelApp import cmd


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

        self.listen_ip = device_util.InterfaceCombo(False)
        self.listen_ip.setToolTip("Listen ip should start with the same digits as phone port")
        self.listen_ip.setCurrentText(settings.value("EpicPhoneListenIp", "--all--"))
        form_layout.addRow("Listen Ip", self.listen_ip)

        self.listen_port = QtWidgets.QLineEdit()
        self.listen_port.setText(settings.value("EpicPhoneListenPort", "6000"))
        self.listen_port.setToolTip("Port to listen on PC, may need to be open on the firewall")
        form_layout.addRow("Listen Port", self.listen_port)

        self.mha = QtWidgets.QCheckBox("Meta Human Animator")
        self.mha.setChecked(bool(settings.value("EpicPhoneMHA")))
        form_layout.addRow("", self.mha)

        self.prefix_name = QtWidgets.QCheckBox("Prefix device name")
        self.prefix_name.setChecked(bool(settings.value("EpicPhonePrefixName")))
        form_layout.addRow("", self.prefix_name)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.phone_ip.setText(device.phone_ip)
        self.phone_port.setText(str(device.phone_port))
        self.listen_ip.setCurrentText(device.listen_ip)
        self.listen_port.setText(str(device.listen_port))
        self.mha.setChecked(device.mha)
        self.prefix_name.setChecked(device.prefix_name)

    def update_device(self, device):
        # Update the device with the data in the text fields
        try:
            device.name = self.name.text()
            device.phone_ip = self.phone_ip.text()
            device.phone_port = int(self.phone_port.text())
            device.listen_ip = self.listen_ip.ip()
            device.listen_port = int(self.listen_port.text())
            device.mha = self.mha.isChecked()
            device.prefix_name = self.prefix_name.isChecked()
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
        self.settings.setValue("EpicPhonePrexixName", self.prefix_name.isChecked())

        return True


class EpicIPhone(PeelDeviceBase):

    def __init__(self, name="IPhone"):
        super(EpicIPhone, self).__init__(name)
        self.phone_ip = "192.168.1.100"
        self.phone_port = 8000
        self.listen_ip = "0.0.0.0"
        self.listen_port = 6000
        self.server = None
        self.thread = None
        self.takeNumber = None
        self.battery = None
        self.thermals = None
        self.info = ""
        self.state = "OFFLINE"
        self.client = None
        self.ping_timer = None
        self.got_response = False
        self.mha = False
        self.prefix_name = False
        self.takes = {}
        self.current_take = None
        self.query = False
        self.dispatcher = None


    @staticmethod
    def device():
        return "epic-iphone"

    def as_dict(self):
        return {'name': self.name,
                'phone_ip': self.phone_ip,
                'phone_port': self.phone_port,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'takes': self.takes,
                'mha': self.mha,
                'prefix_name': self.prefix_name}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.phone_ip = kwargs.get('phone_ip')
        self.phone_port = kwargs.get('phone_port')
        self.listen_ip = kwargs.get('listen_ip')
        self.listen_port = kwargs.get('listen_port')
        self.takes = kwargs.get('takes')
        self.mha = kwargs.get('mha')
        self.prefix_name = kwargs.get('prefix_name')
        return True

    def teardown(self):
        if self.thread is not None and self.server is not None:
            print("Stopping current iphone OSC Server")
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.thread = None
            print("OSC server stopped")

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


        print("Creating udp client")
        self.client = udp_client.SimpleUDPClient(self.phone_ip, self.phone_port)

        try:
            print("Starting OSC Server: " + str(self.listen_ip) + ":" + str(self.listen_port))
            self.server = osc_server.ThreadingOSCUDPServer((self.listen_ip, self.listen_port), self.dispatcher)
        except IOError as e:
            print("Could not start OSC Server: " + str(e))
            self.state = "ERROR"
            self.info = "OSC Error"
            return

        print("Starting iphone thread")
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

        if self.listen_ip != "0.0.0.0":
            print("TARGET: " + str(self.listen_ip) + " " + str(self.listen_port))
            self.client.send_message("/OSCSetSendTarget", [self.listen_ip, self.listen_port])

    def command(self, command, arg):

        if command == "takeNumber":
            self.takeNumber = int(arg)

        if command == "record":
            if self.takeNumber is None:
                self.state = "ERROR"
                self.info = "No take#"
                raise RuntimeError("Take number not set while starting recording")

            # print(f"{arg} {type(arg)}")
            # print(f"{self.takeNumber} {type(self.takeNumber)}")
            if self.prefix_name:
                self.current_take = self.name + "_" + arg
            else:
                self.current_take = arg
            self.client.send_message('/RecordStart', (self.current_take, self.takeNumber))

        if command == "stop":
            self.client.send_message('/RecordStop', 1)

    def callback(self, address, command, *args):

        cmd.writeLog(f"{self.name} callback from {address}  {command}  {args}\n")

        self.got_response = True

        if command == "/RecordStartConfirm":
            self.state = "RECORDING"
            self.push_state()
            return

        if command == "/RecordStopConfirm":
            # timecode, csv, video = args
            print("Adding " + str(self.current_take) + " " + str(args))
            if self.current_take:
                self.takes[self.current_take] = args
            self.state = "ONLINE"
            self.push_state()
            return

        if command == "/Battery":

            last_state = self.state
            if not self.query:
                try:
                    self.battery = float(args[0])
                    if self.state != "RECORDING":
                        self.state = "ONLINE"
                except ValueError:
                    print("Could not parse iphone battery level: " + str(args))
                    self.state = "ERROR"
            else:
                if self.state == "RECORDING":
                    return
                self.state = "ONLINE"
                # print("Phone: " + str(args) + " " + str(address))

            if last_state != self.state:
                self.push_state()

        if command == "/Thermals":
            self.thermals = args
            self.push_state()

    def push_state(self):

        ret = []

        if self.battery is not None:
            ret.append("Bat:%d%%" % int(self.battery * 100.0))

        if self.takes is not None and len(self.takes) > 0:
            ret.append("Clips: %d" % len(self.takes))

        self.info = " / ".join(ret)
        self.update_state(self.state, self.info)

    def ping_timeout(self):
        if not self.got_response:
            # There has been no messages sent since the last ping, set the device to being offline
            if self.state != "OFFLINE":
                self.state = "OFFLINE"
                self.update_state(self.state, "")

        if self.client is None:
            print("No client while sending ping")
            return

        self.got_response = False
        if self.query:
            self.client.send_message('/BatteryQuery', 1)
        else:
            self.client.send_message('/ThermalsQuery', 1)
        self.query = not self.query

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

    def harvest(self, directory, all_files):
        thread = IPhoneDownloadThread(self, directory)
        for take, (timecode, csv, mov) in self.takes.items():
            if not csv and not mov:
                continue
            if self.mha:
                base, mov_name = os.path.split(mov)
                outdir = os.path.join(directory, take)
                if not os.path.isdir(outdir):
                    try:
                        os.makedirs(outdir)
                    except OSError as e:
                        QtWidgets.QMessageBox.warning(self, "Error", "Could not create directory")
                        print(f"Could not create directory: {outdir}")
                        print(str(e))
                        return

                for f in ["audio_metadata.json", "depth_data.bin", "depth_metadata.mhaical",
                          "frame_log.csv", "take.json", "thumbnail.jpg", "video_metadata.json"]:
                    thread.files.append(FileItem(base + "/" + f, take + "/" + f))
                thread.files.append(FileItem(mov, take + "/" + mov_name))


            else:
                thread.files.append(FileItem(csv, take + ".csv"))
                thread.files.append(FileItem(mov, take + ".mov"))

        return thread

    @staticmethod
    def dialog_class():
        return AddWidget

    def list_takes(self):
        return self.takes.keys()


class IPhoneDownloadThread(DownloadThread):

    def __init__(self, phone, directory, listen_port=8444, takes=None):
        super(IPhoneDownloadThread, self).__init__(True)
        self.takes = takes
        self.phone = phone
        self.listen_port = listen_port
        self.directory = directory

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(5)

        self.socket.bind((phone.listen_ip, self.listen_port))

    def __str__(self):
        return str(self.phone) + " Downloader"

    def teardown(self):
        if self.socket:
            self.socket.close()
        super(IPhoneDownloadThread, self).teardown()

    def process(self):

        self.log("Downloading %d iphone files" % len(self.files))

        if not os.path.isdir(self.directory):
            try:
                os.mkdir(self.directory)
            except IOError:
                self.log("Error could not create directory: " + str(self.directory))
                self.set_finished()
                return

        self.set_started()

        my_address = self.phone.listen_ip + ":" + str(self.listen_port)

        self.socket.listen()

        try:

            for i, this_file in enumerate(self.files):

                if not self.is_running():
                    break

                self.set_current(i)

                this_name = str(self.phone.name) + ":" + this_file.local_file

                # Skip existing
                full_path = os.path.join(self.directory, this_file.local_file)
                if os.path.isfile(full_path):
                    self.file_done.emit(this_name, self.COPY_SKIP, None)
                    continue

                # Tell the iphone we want it to send us a file
                self.phone.client.send_message("/Transport", (my_address, this_file.remote_file))

                self.current_size = 0

                try:
                    # Wait for the connection from the phone sending the file
                    conn, addr = self.socket.accept()
                except socket.timeout:
                    self.log("No response for file: " + this_file.remote_file)
                    print("No response for: " + this_file.remote_file)
                    self.file_done.emit(this_name, DownloadThread.COPY_FAIL, "Timeout")
                    conn = None

                if conn is not None:

                    conn.settimeout(2)
                    conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))

                    # Get the file
                    local_fp = open(full_path, "wb")
                    self.read(conn, this_file, local_fp)

                    if this_file.complete:
                        self.file_done.emit(this_name, this_file.complete, this_file.error)
                    local_fp.close()
                    conn.close()

                    if not this_file.complete:
                        os.unlink(full_path)

            else:
                self.set_current(len(self.files))


        except Exception as e:
            self.log(str(e))
        finally:
            self.socket.close()

        self.set_finished()

    def read(self, conn, this_file, fp):

        # IOS device has connected, get the file

        this_file.complete = self.COPY_FAIL

        size_header = conn.recv(4)
        if size_header is None:
            this_file.error = "Read Error"
            return

        this_file.file_size = struct.unpack(">i", size_header)[0]
        this_file.data_size = 0
        self.file_size = this_file.file_size

        if this_file.file_size == 0:
            this_file.error = "Zero sized file"
            return

        while self.is_running():
            data = conn.recv(65536)
            if data is None or len(data) == 0:
                break

            fp.write(data)
            this_file.data_size += len(data)
            self.current_size = this_file.data_size

        if this_file.data_size != this_file.file_size:
            this_file.error = "Incomplete data"
        else:
            this_file.complete = self.COPY_OK





