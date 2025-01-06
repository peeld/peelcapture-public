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
from peel import file_util


class TimeSeriesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = []  # List of integer sample values

    def append(self, value):
        self.samples.append(value)
        if len(self.samples) > 100:
            self.samples.pop(0)
        self.repaint()

    def paintEvent(self, event):

        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QColor(22, 60, 30))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 0, 0)))
        painter.drawRect(0, 0, 100, self.height() - 1)

        if not self.samples:
            return

        h = self.height() - 2
        m = max(self.samples)
        if m == 0:
            return

        scale = h / m

        painter.setPen(QtGui.QColor(40, 190, 60))

        for x, value in enumerate(self.samples):
            value = h - value * scale
            if value < 1 :
                value = 1
            painter.drawLine(x, h, x, value)  # Draw horizontal line

        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.drawText(110, self.height() - 9, file_util.pretty_bytes(self.samples[-1]))

        painter.end()


class HarvestDialog(QtWidgets.QDialog):
    def __init__(self, settings, devices, parent):
        super(HarvestDialog, self).__init__(parent)

        # from peel.DEVICES - list of peel_device.PeelDevice objects
        self.devices = devices
        self.total_copied = 0
        self.total_failed = 0
        self.total_skipped = 0
        self.running = None
        self.workers = []
        self.threads = []
        self.update_timer = QtCore.QTimer()
        self.update_timer.setSingleShot(False)
        self.update_timer.setInterval(500)
        self.update_timer.timeout.connect(self.do_update)

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
        self.device_list = QtWidgets.QTreeWidget()
        self.device_list.setHeaderHidden(True)
        self.device_list.setIndentation(0)
        self.device_list.setStyleSheet("background: #111; color: #fff; border-radius: 3px;")
        self.device_list.setColumnCount(4)
        self.device_list.setColumnWidth(0, 200)
        self.device_list.setColumnWidth(1, 100)
        self.device_list.setColumnWidth(2, 200)
        self.device_list.setColumnWidth(3, 100)
        for device in self.devices:
            pb = QtWidgets.QProgressBar()
            pb.setStyleSheet("text-align: center; margin-top: 2px; margin-bottom: 2px; height: 22px")
            ts = TimeSeriesWidget()
            item = QtWidgets.QTreeWidgetItem([device.name, None, "--", None])
            brush = QtGui.QBrush(QtGui.QColor(30, 30, 30))
            for i in range(4):
                item.setBackground(i, brush)
            item.setCheckState(0, QtCore.Qt.Checked)
            self.device_list.addTopLevelItem(item)
            self.device_list.setItemWidget(item, 1, pb)
            self.device_list.setItemWidget(item, 3, ts)

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
        self.go_button.released.connect(self.go)
        self.browse_button = QtWidgets.QPushButton("Browse Files")
        self.browse_button.released.connect(self.browse_files)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.released.connect(self.teardown)

        self.all_files = QtWidgets.QCheckBox("All Files")
        self.all_files.setChecked(settings.value("harvestAlLFiles") == "True")

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.go_button)
        button_layout.addSpacing(3)
        button_layout.addWidget(self.browse_button)
        button_layout.addSpacing(3)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.all_files)
        button_layout.addSpacing(3)

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
        for worker in self.workers:
            worker.teardown()
        for thread in self.threads:
            thread.exit(0)
        for thread in self.threads:
            thread.wait()

    def __del__(self):
        cmd.writeLog("harvest closing\n")
        self.settings.setValue("harvestGeometry", self.saveGeometry())
        self.settings.setValue("harvestSplitterGeometry", self.splitter.sizes())
        self.settings.setValue("harvestAllFiles", str(self.all_files.isChecked()))
        self.teardown()

    def go(self):

        # Go button has been pressed, lets get started...

        if self.running is True:
            self.running = False
            self.teardown()
            self.go_button.setText("Get Files")
            return

        self.workers = []
        self.threads = []

        for i in range(self.device_list.topLevelItemCount()):
            item = self.device_list.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                # adds to self.workers and self.threads
                self.make_worker(i)

        if len(self.workers) == 0:
            self.log_message("No devices to collect files")
            return

        self.running = True
        self.total_copied = 0
        self.total_failed = 0
        self.total_skipped = 0

        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 100)
        self.info_label.setText("")

        self.update_timer.start()

        self.update_gui()

    def make_worker(self, device_id):
        device = self.devices[device_id]
        device_path = os.path.join(self.path.text(), device.name)

        # Worker
        worker = device.harvest(device_path, self.all_files.isChecked())
        worker.device_id = device_id
        worker.file_done.connect(self.file_done, QtCore.Qt.QueuedConnection)
        worker.all_done.connect(self.all_done, QtCore.Qt.QueuedConnection)
        worker.message.connect(self.log_message, QtCore.Qt.QueuedConnection)
        self.workers.append(worker)

        # Thread
        thread = QtCore.QThread()
        self.threads.append(thread)
        worker.moveToThread(thread)
        thread.started.connect(worker.process)
        thread.start()

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

    def do_update(self):
        if self.is_done():
            self.update_timer.stop()
            msg = "Download Complete\n\nFiles copied: %d\nFiles skipped: %d\nFiles failed: %d" % \
                  (self.total_copied, self.total_skipped, self.total_failed)
            self.log.appendPlainText(msg)
            self.running = False
            self.update_gui()

        total = 0

        for worker in self.workers:

            bandwidth = worker.calc_bandwidth()

            row = worker.device_id
            item = self.device_list.topLevelItem(row)

            val = worker.progress() * 100
            item.setText(1, f"{val:.2%}")
            file = worker.current_file()
            if file:
                item.setText(2, str(file))
            else:
                item.setText(2, "")

#            if bandwidth:
#                item.setText(3, str(bandwidth))
#            else:
#                item.setText(3, "")

            brush = QtGui.QBrush()
            fg = QtGui.QColor(255, 255, 255)
            if worker.status == DownloadThread.STATUS_RUNNING:
                brush = QtGui.QBrush(QtGui.QColor(66, 210, 66))
                fg = QtGui.QColor(0, 0, 0)
            elif worker.status == DownloadThread.STATUS_FINISHED:
                brush = QtGui.QBrush(QtGui.QColor(128, 128, 128))

            # Progress Bar
            pb = self.device_list.itemWidget(item, 1)
            if pb:
                pb.setValue(val)
                pb.setMaximum(100)

            # Time Series
            ts = self.device_list.itemWidget(item, 3)
            if ts:
                ts.append(bandwidth)

            total += val

            for i in range(4):
                item.setBackground(i, brush)
                item.setForeground(i, fg)

        self.progress_bar.setValue(total // len(self.workers))

    def log_message(self, message):
        self.log.appendPlainText(message)
        cmd.writeLog(message + "\n")

    def count(self, state):
        return sum(1 for worker in self.workers if worker.status == state)

    def is_done(self):
        for worker in self.workers:
            if worker.is_running():
                return False

        return True

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

    def all_done(self):
        device = self.sender()
        index = self.workers.index(device)
        self.threads[index].exit()

    def sender_device_id(self):
        ref = self.sender()
        for i, worker in enumerate(self.workers):
            if ref == worker:
                return i
        return None

    def browse(self):
        d = cmd.currentConfig["DataDirectory"]
        ret = QtWidgets.QFileDialog.getExistingDirectory(self, "Shoot Dir", d)
        if ret:
            self.path.setText(ret)

    def browse_files(self):
        path = self.path.text()
        url = QtCore.QUrl.fromLocalFile(path)
        QtGui.QDesktopServices.openUrl(url)


