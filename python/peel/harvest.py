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


from PySide6 import QtWidgets, QtCore, QtGui
import os.path
from PeelApp import cmd
from peel_devices import DownloadThread


class HarvestDialog(QtWidgets.QDialog):
    def __init__(self, settings, devices, parent):
        super(HarvestDialog, self).__init__(parent)

        # from peel.DEVICES - list of peel_device.PeelDevice objects
        self.devices = devices
        self.current_device = -1
        self.current_process = None
        self.total_copied = None
        self.total_failed = None
        self.total_skipped = None
        self.running = None
        self.work_threads = []

        self.setWindowTitle("Harvest")

        if settings is None:
            self.settings = QtCore.QSettings("PeelDev", "PeelCapture")
        else:
            self.settings = settings

        layout = QtWidgets.QVBoxLayout()

        data_dir = None
        if "DataDirectory" in cmd.currentConfig:
            data_dir = cmd.currentConfig["DataDirectory"]

        # File Path Browser
        file_layout = QtWidgets.QHBoxLayout()
        self.path = QtWidgets.QLineEdit()
        self.path.setText(str(data_dir))
        self.path_button = QtWidgets.QPushButton("...")
        self.path_button.pressed.connect(self.browse)
        file_layout.addWidget(self.path)
        file_layout.addWidget(self.path_button)
        file_layout.setSpacing(6)
        layout.addItem(file_layout)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        # Device List
        self.device_list = QtWidgets.QListWidget()
        self.device_list.setStyleSheet("background: #a6a6a6; color: black; border-radius: 3px;")
        for i in self.devices:
            item = QtWidgets.QListWidgetItem(i.name)
            item.setCheckState(QtCore.Qt.Checked)
            self.device_list.addItem(item)

        self.selected_devices = None

        self.splitter.addWidget(self.device_list)
        self.splitter.setSizes([1, 3])

        # Log
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setStyleSheet("background: #a6a6a6; color: black;")
        self.splitter.addWidget(self.log)

        layout.addWidget(self.splitter)

        # InfoLabel
        self.info_label = QtWidgets.QLabel()
        self.info_label.setStyleSheet("color: #ccc")
        layout.addWidget(self.info_label)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setStyleSheet("color: #ccc")
        layout.addWidget(self.progress_bar)

        # Buttons
        self.go_button = QtWidgets.QPushButton("Get Files")
        self.go_button.pressed.connect(self.go)
        self.close_button = QtWidgets.QPushButton("Close")
        self.close_button.pressed.connect(self.teardown)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.go_button)
        button_layout.addWidget(self.close_button)

        layout.addItem(button_layout)

        self.setLayout(layout)

        self.resize(500, 400)

        geo = self.settings.value("harvestGeometry")
        if geo:
            self.restoreGeometry(geo)

        sizes = self.settings.value("harvestSplitterGeometry")
        if sizes:
            self.splitter.setSizes([int(i) for i in sizes])

    def teardown(self):
        self.running = False
        cmd.writeLog("Harvest teardown\n")
        if self.current_process is not None:
            self.current_process.teardown()
        self.close()

    def __del__(self):
        cmd.writeLog("harvest closing\n")
        self.settings.setValue("harvestGeometry", self.saveGeometry())
        self.settings.setValue("harvestSplitterGeometry", self.splitter.sizes())
        self.teardown()

    def go(self):

        # Go button has been pressed, lets get started...

        if self.go_button.text() == "Cancel":
            self.running = False
            if self.current_process is not None:
                self.current_process.teardown()
            self.go_button.setText("Get Files")
            return

        self.selected_devices = []
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                self.selected_devices.append(i)

        if len(self.selected_devices) == 0:
            print("no devices to collect files")
            return

        print("Queue: " + str(self.selected_devices))

        self.running = True
        self.total_copied = 0
        self.total_failed = 0
        self.total_skipped = 0
        self.current_device = -1

        # Start the copy loop
        self.next_device()

    def update_gui(self):
        if self.running:
            self.device_list.setEnabled(False)
            self.path.setEnabled(False)
            self.path_button.setEnabled(False)
            self.go_button.setText("Cancel")
        else:
            self.device_list.setEnabled(True)
            self.path.setEnabled(True)
            self.path_button.setEnabled(True)
            self.go_button.setText("Get Files")

    def log_message(self, message):
        self.log.appendPlainText(message)
        #print("> " + message)

    def is_done(self):
        return self.current_device >= len(self.selected_devices)

    def next_device(self):

        """ Called when we first start of when a device has finished processing """

        # current device is an index in self.selected_devices
        # self.selected devices is a list of indexes in self.device_list / self.devices

        if self.current_process is not None:
            print("Finished: " + str(self.current_process))

        print("Next device")

        self.current_device += 1

        self.update_gui()

        if not self.running:
            print("Not running")
            return

        if self.is_done():
            # Finished

            self.progress_bar.setValue(100)
            self.progress_bar.setRange(0, 100)
            self.info_label.setText("")

            msg = "Download Complete\n\nFiles copied: %d\nFiles skipped: %d\nFiles failed: %d" % (self.total_copied, self.total_skipped, self.total_failed)
            self.log.appendPlainText(msg)
            self.running = False
            self.update_gui()

            QtWidgets.QMessageBox.information(self, "Done", msg)

            return

        # Un-highlight all the devices
        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            item.setBackground(QtGui.QBrush())

        device_id = self.selected_devices[self.current_device]
        device = self.devices[device_id]

        print("Starting: %d" % self.current_device)
        print("Device:   %d" % device_id)

        self.current_process = device.harvest(os.path.join(self.path.text(), device.name))
        self.current_process.tick.connect(self.progress, QtCore.Qt.QueuedConnection)
        self.current_process.file_done.connect(self.file_done, QtCore.Qt.QueuedConnection)
        self.current_process.all_done.connect(self.next_device, QtCore.Qt.QueuedConnection)
        self.current_process.message.connect(self.log_message, QtCore.Qt.QueuedConnection)
        self.current_process.finished.connect(self.device_cleanup)
        self.work_threads.append(self.current_process)
        print(f"Starting download thread for {str(device)}")
        self.current_process.start()

        # Highlight the device we are about to start on
        item = self.device_list.item(device_id)
        item.setBackground(QtGui.QBrush(QtGui.QColor(167, 195, 244)))

    def device_cleanup(self):
        device_thread = self.sender()
        print("Thread done: " + str(device_thread))
        self.work_threads.remove(device_thread)

    def file_done(self, name, copy_state, error):
        if copy_state == DownloadThread.COPY_OK:
            self.log.appendPlainText("COPIED: " + name)
            self.total_copied += 1
        elif copy_state == DownloadThread.COPY_SKIP:
            self.log.appendHtml("<FONT COLOR=\"#444\">SKIPPED: " + name + " (local file exists)</FONT>")
            self.total_skipped += 1
        elif copy_state == DownloadThread.COPY_FAIL:
            self.log.appendHtml("<FONT COLOR=\"#933\">FAILED: " + name + ":" + str(error) + "</FONT>")
            self.total_failed += 1

    def progress(self, minor):
        if self.current_device is None or self.is_done():
            print("Process Done")
            return

        if len(self.devices) == 0:
            return

        minor = float(minor) / float(len(self.devices))
        major = float(self.current_device) / float(len(self.selected_devices))
        self.progress_bar.setValue(int((major + minor) * 100.0))
        self.progress_bar.setRange(0, 100)
        device_name = self.devices[self.current_device].name
        if self.current_process.current_file is not None:
            self.info_label.setText(str(device_name) + ": " + str(self.current_process.current_file))

    def browse(self):
        d = cmd.currentConfig["DataDirectory"]
        ret = QtWidgets.QFileDialog.getExistingDirectory(self, "Shoot Dir", d)
        if ret:
            self.path.setText(ret)





