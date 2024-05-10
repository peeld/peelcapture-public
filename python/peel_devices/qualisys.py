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
        self.conn = None
        self.take_name = None
        self.name = name
        self.host = host
        self.password = password

        # Create a loop that stays as long as the device is added and/or program is running
        self.loop = asyncio.new_event_loop()
        self.state = "OFFLINE"
        self.info = None
        self._update_state("OFFLINE", "Device is offline.")

        if host is not None and password is not None:
            self.reconfigure(name, host=host, password=password)

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs['host']
        self.password = kwargs['password']

        self._update_state("OFFLINE", None)

        if self.conn is not None:
            self.conn.disconnect()

        self.loop.run_until_complete(self.connect_qualisys())

    def teardown(self):
        if self.conn is not None:
            self.loop.run_until_complete(self.release_control())
            self.conn.disconnect()
            self.loop.close()

    async def release_control(self):
        print("Release Control of Qualisys")
        try:
            await self.conn.release_control()
        except qtm_rt.QRTCommandException:
            self._update_state("ERROR", "Failed to release control of QTM")
            return

    async def connect_qualisys(self):
        print("Connect to Qualisys")
        self.conn = await qtm_rt.connect(self.host)

        if self.conn is None:
            self._update_state("ERROR", "Failed to connect to QTM")
            return

        try:
            await self.conn.take_control(self.password)
        except qtm_rt.QRTCommandException:
            self._update_state("ERROR", "Failed to take control of QTM")
            return

        self._update_state("ONLINE", None)

    async def new_measurement(self):
        state = await self.conn.get_state()
        if state != qtm_rt.QRTEvent.EventConnected:
            await self.conn.new()
            try:
                await self.conn.await_event(qtm_rt.QRTEvent.EventConnected, timeout=5)
            except asyncio.TimeoutError:
                self._update_state("ERROR", "Failed to start a new measurement on QTM")
                return

        self._update_state("ONLINE", None)  # Device is ready for a new measurement

    async def start_measurement(self):
        print("Start Measurement")
        await self.conn.start()
        try:
            await self.conn.await_event(qtm_rt.QRTEvent.EventCaptureStarted, timeout=5)
            self._update_state("RECORDING", None)  # Measurement is now recording
        except asyncio.TimeoutError:
            self._update_state("ERROR", "Failed to start measurement")

    async def stop_measurement(self):
        print("Stop Measurement")
        await self.conn.stop()
        try:
            await self.conn.await_event(qtm_rt.QRTEvent.EventCaptureStopped, timeout=5)
            self._update_state("ONLINE", None)  # Measurement has stopped; device is online
        except asyncio.TimeoutError:
            self._update_state("ERROR", "Failed to stop measurement")

    async def save_measurement(self, take_name):
        print("Save Measurement")
        try:
            await self.conn.save(f"{take_name}.qtm")
        except qtm_rt.QRTCommandException:
            self._update_state("ERROR", "Could not save the measurement")

    def _update_state(self, new_state, info):
        """
        Update the internal state and information message of the connection process.
        """
        self.state = new_state
        self.info = info
        if self.info is not None:
            print(self.info)
        self.update_state(self.state, self.info)

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
        print("Command: " + command)
        if self.conn is None or not self.conn.has_transport():
            self.loop.run_until_complete(self.connect_qualisys())
        if command == "record":
            self.take_name = argument
            self.loop.run_until_complete(self.new_measurement())
            self.loop.run_until_complete(self.start_measurement())
        if command == "stop":
            self.loop.run_until_complete(self.stop_measurement())
            self.loop.run_until_complete(self.save_measurement(self.take_name))

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

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
