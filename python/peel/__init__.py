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


from peel_devices import shogun, epiciphone, DeviceCollection
from peel import harvest
from PySide6 import QtWidgets, QtCore

try:
    from PeelApp import cmd
except ImportError:
    print("Not running in PeelCapture - cmd will not be available")
    cmd = None

try:
    import peel_user_startup
except ImportError:
    peel_user_startup = None

import os.path
import json


DEVICES = DeviceCollection()
SUBJECTS = {}
SETTINGS = None


def startup():
    global SETTINGS
    print("Starting device services - Python api v0.4")

    SETTINGS = QtCore.QSettings("PeelDev", "PeelCapture")

    if peel_user_startup is not None:
        peel_user_startup.startup()


def file_new():
    global DEVICES
    for device in DEVICES:
        if isinstance(device, epiciphone.EpicIPhone):
            device.takes = {}


def teardown():
    """ UI-ACTION - main window has closed """
    print("Shutting down")
    DEVICES.teardown()


def set_device_data():
    """ Pass the json data for the devices to the main app so it can include it
    when saving the peelcap file at regular intervals (e.g. when hitting record/stop) """
    global DEVICES
    cmd.setDeviceData(json.dumps(DEVICES.get_data()))


def load_data(file_path, mode):

    """ Load the device data from a .peelcap file """

    print("Loading " + file_path + " with mode: " + mode)

    if not os.path.isfile(file_path):
        print("Could not find json file for devices: " + file_path)
        return

    with open(file_path, encoding="utf8") as fp:
        DEVICES.load_json(json.load(fp), mode)

    DEVICES.update_all("LOAD")


class AddDeviceDialog(QtWidgets.QDialog):

    """ The add device dialog - swaps the middle panel out for each device setting """

    def __init__(self, parent):
        super(AddDeviceDialog, self).__init__(parent)

        self.combo = QtWidgets.QComboBox()
        self.combo.addItem("--select--")

        self.device_list = []
        self.current_widget = None
        self.current_device_class = None

        self.device_list = sorted(DeviceCollection.all_classes(), key=lambda k: k.device())
        for klass in self.device_list:
            self.combo.addItem(klass.device())

        self.combo.currentIndexChanged.connect(self.device_select)

        self.confirm_button = QtWidgets.QPushButton("Create")
        self.confirm_button.pressed.connect(self.accept)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.top_widget = QtWidgets.QWidget()
        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_widget.setLayout(self.top_layout)

        label = QtWidgets.QLabel("New Device:")
        label.setStyleSheet("font-size: 12pt")
        self.top_layout.addWidget(label)
        self.top_layout.addWidget(self.combo)
        self.top_layout.addStretch(1)
        self.top_widget.setStyleSheet("background: #111")

        self.device_widget = QtWidgets.QWidget()
        self.device_layout = QtWidgets.QHBoxLayout()
        self.device_widget.setLayout(self.device_layout)

        self.info_widget = QtWidgets.QTextBrowser()
        self.info_widget.setOpenExternalLinks(True)
        self.info_widget.setStyleSheet("background: #151618; color: #ccc; ")
        self.info_widget.document().setDefaultStyleSheet("a { color: #ccf}")

        self.low_widget = QtWidgets.QWidget()
        self.low_layout = QtWidgets.QHBoxLayout()
        self.low_widget.setLayout(self.low_layout)
        self.low_widget.setStyleSheet("background: #111")

        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.cancel_button.setStyleSheet("color: white; background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010); ")
        self.cancel_button.pressed.connect(self.do_close)
        self.low_layout.addWidget(self.cancel_button)

        self.low_layout.addStretch(1)

        self.add_button = QtWidgets.QPushButton("Add")
        self.add_button.setStyleSheet("color: white; background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #16191a, stop: 1 #101010); ")
        self.add_button.released.connect(self.do_add)
        self.low_layout.addWidget(self.add_button)

        self.main_layout.addWidget(self.top_widget, 0)
        self.main_layout.addWidget(self.device_widget, 1)
        self.main_layout.addWidget(self.info_widget, 1)
        self.main_layout.addWidget(self.low_widget, 0)

        self.resize(350, 400)

        self.setLayout(self.main_layout)

        self.show()

    def device_select(self, index):

        """ User has selected a device from the combo.  Get the widget from the device to show """
        if index == 0:
            return

        # Remove the previous device
        ret = self.device_widget.layout().takeAt(0)
        if ret is not None:
            ret.widget().deleteLater()

        # Get the current selected device class and ask it for the widget class
        self.current_device_class = self.device_list[index-1]
        widget_class = self.current_device_class.dialog_class()

        # Create an instance of the widget
        self.current_widget = widget_class(SETTINGS)

        # Create an instance of the device, so we can get the default values
        device = self.current_device_class()
        self.current_widget.populate_from_device(device)

        # Add the widget it to the ui
        self.device_widget.layout().addWidget(self.current_widget)
        self.info_widget.setHtml(self.current_widget.info_text)

    def do_add(self):

        """ User has pressed the 'add' button, create the device. """
        if self.current_widget is None:
            return

        # Validate the device
        if not self.current_widget.do_add():
            return

        # Create a device object and populate it using values in the widget
        device = self.current_device_class()
        self.current_widget.update_device(device)

        # Add the device to device list
        print("Adding: " + str(device))
        DEVICES.add_device(device)

        # Register all devices with the application
        # This needs to be done before connect so the status updates by connect work.
        DEVICES.update_all("ADD")

        # Start the device - this should update the status
        device.connect_device()

        device.device_added(self.current_widget)

        self.close()
        self.deleteLater()

    def do_close(self):
        self.close()
        self.deleteLater()

    def keyPressEvent(self, evt):
        if evt.key() == QtCore.Qt.Key_Enter or evt.key() == QtCore.Qt.Key_Return:
            return
        super().keyPressEvent(evt)


DIALOG_LOCK = False


def add_device():

    """ UI-ACTION - Called by main window to create a new device when the user clicks the "+" button """

    global DIALOG_LOCK
    if DIALOG_LOCK:
        return

    DIALOG_LOCK = True
    d = AddDeviceDialog(cmd.getMainWindow())
    d.exec_()
    d.deleteLater()
    DIALOG_LOCK = False


def device_info(n):

    """ Called when the user double clicks on an item.  Id of the item is passed.
        Add functionality to edit the device here """

    global DEVICES

    if n < 0 or n >= len(DEVICES):
        return

    # Create a dialog
    d = QtWidgets.QDialog(cmd.getMainWindow())
    layout = QtWidgets.QVBoxLayout()
    d.setLayout(layout)

    device = DEVICES[n]

    # Get the widget class for the dialog
    klass = device.dialog_class()
    widget = klass(SETTINGS)
    widget.populate_from_device(DEVICES[n])
    layout.addWidget(widget)

    button = QtWidgets.QPushButton("Okay")
    button.pressed.connect(d.accept)
    layout.addWidget(button)

    while True:
        if not d.exec_():
            break

        if widget.do_add():
            if not widget.update_device(device):
                continue

            cmd.updateDevice(device.device_ref(reason="ADD"))
            device.connect_device()
            device.device_added(widget)
            d.deleteLater()
            return

    d.deleteLater()

    DEVICES.update_all("INFO")


def set_motive_status(state, msg):
    global DEVICES

    for i in DEVICES:
        if i.device() == "motive":
            i.set_motive_state(state, msg)


def set_device_enable(n, state):
    """ Called by the main app to update a device object to say that it is to pause operations """
    global DEVICES

    if n < 0 or n >= len(DEVICES):
        return

    DEVICES[n].set_enabled(state)
    DEVICES.update_all("ENABLE")


def set_subject(name, enabled):
    global DEVICES
    for device in DEVICES:
        if isinstance(device, shogun.ViconShogun):
            device.set_subject(name, enabled)


def delete_device(device_id):
    """ Called by the main app to delete a device instance, by device name (key) """
    global DEVICES
    DEVICES.remove(device_id)
    DEVICES.update_all("DELETE")


def refresh_device(device_id):
    global DEVICES
    DEVICES.refresh(device_id)


def reconnect_device(device_id):
    global DEVICES
    DEVICES.reconnect(device_id)


def command(command, argument):
    """ Main app sending a command - passed to device.command()
    Command: Argument
    transport: stop, next, prev, play
    record: takeName
    stop
    """

    global DEVICES
    for device in DEVICES:
        if device.enabled:
            device.command(command, argument)

    # This is causing a weird blackout issue:
    # DEVICES.update_all()


def show_harvest():
    """ UI-ACTION: Copy the files from the devices to a local directory """
    harvest_devices = [ d for d in DEVICES if d.has_harvest() ]

    if len(harvest_devices) == 0:
        QtWidgets.QMessageBox.warning(cmd.getMainWindow(), "Harvest", "No supported devices available")
        return
    h = harvest.HarvestDialog(SETTINGS, harvest_devices, cmd.getMainWindow())
    h.exec_()
    h.deleteLater()


def copy_selects():
    """ UI-ACTION - call when the user calls the "copy selects" action in the main window"""
    global SETTINGS
    from peel import select_sort
    w = select_sort.SelectSort(SETTINGS, cmd.getMainWindow())
    w.exec_()
    w.deleteLater()


def audio_recording_started():

    """ Called by the main app when audio recording has started successfully """

    global DEVICES
    for device in DEVICES:
        if device.device() == "audio":
            device.recording_started()


def audio_recording_failed(msg):

    """ Called by the main app when audio recording fails to start """

    global DEVICES
    for device in DEVICES:
        if device.device() == "audio":
            device.recording_failed(msg)


def movies(take=None):

    """ Used by shotgun and ftracking publishing to get the movie files """
    data_dir = cmd.getDataDirectory().replace("/", os.path.sep)
    if not data_dir or not os.path.isdir(data_dir):
        return []

    movies = []

    if take is not None:
        take = take.replace(".", "_").replace("-", "_")

    for device in os.listdir(data_dir):
        if (device.startswith(".")):
            continue

        device_dir = os.path.join(data_dir, device)
        if not os.path.isdir(device_dir):
            continue

        try:
            for f in os.listdir(device_dir):
                if f.startswith("."):
                    continue

                name, ext = os.path.splitext(f)
                if ext.lower() not in ['.mpg', '.mp4', '.mov', '.avi']:
                    continue

                if take is not None:
                    name_fixed = name.replace(".", "_").replace("-", "_")
                    if take not in name_fixed:
                        continue

                movies.append(os.path.join(device_dir, f))

        except Exception as e:
            print("Error reading directory: " + str(device_dir) + " for device " + str(device))
            print(str(e))


    return movies


def lightbulb(value):
    """ UI-ACTION: Called by the main app when the user presses the lightblub button """
    for d in DEVICES:
        if d.device() == "hue":
            d.turn_on(value)


def do_stop():
    """ Called shortly after stop event to update devices """
    global DEVICES
    DEVICES.update_all("STOP")
