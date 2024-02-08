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


from peel_devices import PeelDeviceBase, BaseDeviceWidget
from PySide6 import QtWidgets, QtCore
# from PeelApp import cmd

import asyncio
import qtm_rt


class QualisysDeviceDialog(BaseDeviceWidget):
    """ A basic dialog for a device that has a name and an optional IP argument """

    def __init__(self, settings):
        super(QualisysDeviceDialog, self).__init__(settings)
        form_layout = QtWidgets.QFormLayout()

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-qualisys/'
        msg = "<P>QTM Documentation</P>"
        msg += '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

        self.setWindowTitle("Qualisys")
        self.setObjectName("QualisysDialog")

        self.info = QtWidgets.QLabel()
        form_layout.addWidget(self.info)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(settings.value("QualisysName", "Qualisys"))
        form_layout.addRow("Name", self.name)

        self.host = None
        self.password = None

        self.host = QtWidgets.QLineEdit()
        self.host.setText(settings.value("QualisysHost", "127.0.0.1"))
        form_layout.addRow("Address", self.host)

        self.password = QtWidgets.QLineEdit()
        self.password.setText(settings.value("QualisysPassword", ""))
        form_layout.addRow("Password", self.password)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.host.setText(device.host)
        self.password.setText(device.password)

    def update_device(self, device):
        """ Set the device properties from values in the ui """

        name = self.name.text()
        host = self.host.text()
        password = self.password.text()

        device.reconfigure(name, host=host, password=password)
        return True

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("QualisysName", self.name.text())
        self.settings.setValue("QualisysHost", self.host.text())
        self.settings.setValue("QualisysPassword", self.password.text())

        return True


class QualisysDevice(PeelDeviceBase):

    def __init__(self, name=None, host=None, password=None):
        super(QualisysDevice, self).__init__(name)
        self.take_name = None
        self.name = None
        self.host = None
        self.password = None
        self.update_state(state="OFFLINE")
        self.conn = None
        if host is not None and password is not None:
            self.reconfigure(name, host=host, password=password)

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs['host']
        self.password = kwargs['password']
        self.update_state(state="OFFLINE")
        if self.conn is not None:
            self.conn.loop.run_until_complete(self.conn.disconnect())
        # self.conn.loop.run_until_complete(self.connect_qualisys())
        asyncio.run(self.connect_qualisys())

    def teardown(self):
        if self.conn is not None:
            self.conn.loop.run_until_complete(self.conn.disconnect())

    async def connect_qualisys(self):
        """
        Create the obj object and do the async call
        """
        self.conn = await qtm_rt.connect(self.host)
        state = await self.conn.get_state()
        if state != qtm_rt.QRTEvent.EventConnected:
            await self.conn.new()
            try:
                await self.conn.await_event(qtm_rt.QRTEvent.EventConnected, timeout=5)
            except asyncio.TimeoutError:
                self.update_state("ERROR", "Failed to start new measurement")
                return False
        # Try to take control of QTM
        try:
            async with qtm_rt.TakeControl(self.conn, self.password):
                self.update_state(state="ONLINE")
                return True
        except Exception as e:
            self.update_state("OFFLINE", f"Failed to take control of QTM: {e}")
            return False

    async def start_measurement(self):
        """
        Start a new measurement with the QTM server.
        """
        # Start the measurement
        try:
            await self.conn.start()
            await self.conn.await_event(qtm_rt.QRTEvent.EventCaptureStarted, timeout=5)
            return True
        except Exception as e:
            self.update_state("ERROR", f"Failed to start measurement: {e}")
            return False

    async def stop_measurement(self, take_name):
        """
        Stop the ongoing measurement and save the data to a file.
        """
        # Stop the measurement
        try:
            await self.conn.stop()
            await self.conn.await_event(qtm_rt.QRTEvent.EventCaptureStopped, timeout=5)
            return True
        except Exception as e:
            self.update_state("ERROR", f"Failed to stop measurement: {e}")
            return False

    async def save_measurement(self, take_name):
        """
        Save the data to a file with take name.
        """
        try:
            await self.conn.save(f"{take_name}.qtm")
            return True
        except Exception as e:
            self.update_state("ERROR", f"Failed to save measurement: {e}")
            return False

    @staticmethod
    def device():
        return "qualisys"

    def as_dict(self):
        return {
            'name': self.name,
            'host': self.host,
            'password': self.password}

    def __str__(self):
        return self.name

    def command(self, command, argument):
        if self.conn is None:
            asyncio.run(self.connect_qualisys())
        if command == "record":
            self.take_name = argument
            self.conn.loop.run_until_complete(self.start_measurement())
        if command == "stop":
            self.conn.loop.run_until_complete(self.stop_measurement())
            self.conn.loop.run_until_complete(self.save_measurement(self.take_name))

    @staticmethod
    def dialog(settings):
        return QualisysDeviceDialog(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        device = QualisysDevice()
        if widget.update_device(device):
            return device

    def edit(self, settings):
        dlg = QualisysDeviceDialog(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)
