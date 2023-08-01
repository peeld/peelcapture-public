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
from PySide6 import QtWidgets, QtCore, QtGui
import phue
from PeelApp import cmd


class ColorWidget(QtWidgets.QLineEdit):
    def __init__(self, parent=None):
        super(ColorWidget, self).__init__(parent)

    def focusInEvent(self, e):
        if e.reason() == QtCore.Qt.MouseFocusReason:

            color = QtGui.QColor()
            sp = self.text().split(",")
            if len(sp) == 3:
                try:
                    h, s, l = int(sp[0]), int(sp[1]), int(sp[2])
                    print(h, s, l)
                    color.setHslF(h / 65535.0, s / 255.0, l / 255.0)
                except ValueError:
                    pass

            color = QtWidgets.QColorDialog.getColor(color)
            if color.isValid():
                print("RGB", color.rgb())
                print("SPEC", color.spec())
                print("H", color.hslHue())
                print("H", color.hslHue())
                print("S", color.saturationF())
                print("L", color.lightnessF())
                print("V", color.valueF())
                huef = color.hueF()
                if huef == -1:
                    huef = 0
                hue = int(huef * 65535)
                sat = color.saturation()
                val = color.value()
                print(huef, sat)
                self.setText(f"{hue},{sat},{val}")



class HueDeviceWidget(BaseDeviceWidget):
    """ A basic dialog for a device that has a name and an optional IP argument """
    def __init__(self, settings):
        super(HueDeviceWidget, self).__init__(settings)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-philips-hue/'
        msg = "<P>Phillips Hue Lighting</P>"
        msg += '<P><A HREF="' + link + '">Documentation</A></P>'
        self.set_info(msg)

        self.click_flag = False
        form_layout = QtWidgets.QFormLayout()
        self.settings = settings

        self.setWindowTitle("Hue")
        self.setObjectName("HueDialog")

        self.info = QtWidgets.QLabel()
        form_layout.addWidget(self.info)

        self.name = QtWidgets.QLineEdit()
        self.name.setText(settings.value("HueName", "Hue"))
        form_layout.addRow("Name", self.name)

        self.host = None
        self.port = None
        self.broadcast = None
        self.listen_ip = None
        self.listen_port = None

        self.host = QtWidgets.QLineEdit()
        self.host.setText(settings.value("HueHost", "192.168.1.100"))
        form_layout.addRow("Address", self.host)

        self.idle_color = ColorWidget()
        self.idle_color.setText(settings.value("HueIdleColor", ""))
        form_layout.addRow("Idle Color", self.idle_color)

        self.rec_ok_color = ColorWidget()
        self.rec_ok_color.setText(settings.value("RecordingOkColor", ""))
        form_layout.addRow("Recording Ok Color", self.rec_ok_color)

        self.setLayout(form_layout)

    def populate_from_device(self, device):
        # populate the gui using data in the device
        self.name.setText(device.name)
        self.host.setText(device.host)
        self.idle_color.setText(str(device.idle_color))
        self.rec_ok_color.setText(str(device.rec_ok_color))

    def update_device(self, device):

        """ Set the device properties from values in the ui """

        self.name = self.name.text()

        host = self.host.text()

        idle_color = self.idle_color.text()
        rec_ok_color = self.rec_ok_color.text()

        device.reconfigure(self.name, host=host, idle_color=idle_color, rec_ok_color=rec_ok_color)
        return device.connect_bridge()

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue("HueName", self.name.text())
        self.settings.setValue("HueHost", self.host.text())
        self.settings.setValue("HueIdleColor", self.idle_color.text())
        self.settings.setValue("RecordingOkColor", self.rec_ok_color.text())

        return True


class Hue(PeelDeviceBase):

    """ Support for Phillips Hue Lighting
    """

    def __init__(self, name, host, rec_ok_color=None, idle_color=None):
        super(Hue, self).__init__(name)
        self.host = host
        self.bridge = None
        self.error = None
        self.rec_ok_color = rec_ok_color
        self.idle_color = idle_color
        self.connect_bridge()
        self.recording = False

    def connect_bridge(self):
        self.bridge = phue.Bridge(self.host)
        self.update_state()
        cmd.showLightbulb(True)

    @staticmethod
    def device():
        return "hue"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'rec_ok_color': self.rec_ok_color,
                'idle_color': self.idle_color}

    def __str__(self):
        return self.name

    def reconfigure(self, name, **kwargs):
        self.name = name
        if 'host' in kwargs: self.host = kwargs['host']
        if 'idle_color' in kwargs: self.idle_color = kwargs['idle_color']
        if 'rec_ok_color' in kwargs: self.rec_ok_color = kwargs['rec_ok_color']

    def get_info(self):

        if self.bridge is None:
            return "Not Connected"

        if self.error is not None:
            return self.error

        return ""

    def get_state(self):
        """ should return "OFFLINE", "ONLINE", "RECORDING" or "ERROR"
            avoid calling update_state() here.
        """

        if self.error is not None:
            return "ERROR"

        if not self.enabled:
            return "OFFLINE"

        if self.bridge is None:
            return "ERROR"
        else:
            if self.recording:
                return "RECORDING"
            else:
                return "ONLINE"

    def set_color(self, color, saturation=255, brightness=255):

        self.error = None

        try:
            color = int(color)
            saturation = int(saturation)
            brightness = int(brightness)
        except ValueError:
            print("Invalid color")
            self.error = "Invalid color"
            return False

        try:
            lights = self.bridge.get_light_objects()
        except phue.PhueRequestTimeout as e:
            self.update_state("ERROR", str(e.message))
            self.error = str(e.message)
            return False

        for light in lights:
            # print("Hue: " + str(light) + " " + str(color))
            light.on = True
            light.brightness = brightness
            light.hue = color
            light.saturation = saturation

        return True

    def turn_on(self, value):
        if value:
            self.set_color(*self.rec_ok_color.split(','))
        else:
            self.set_color(*self.idle_color.split(','))

    def command(self, command, argument):
        """ Respond to the app asking us to do something """

        # print("Hue Command: %s  Argument: %s" % (command, argument))

        if command == "record":
            # We must be in record mode when we start so recording-ok is triggered
            self.recording = True
            self.update_state("RECORDING", "")

        # This command is sent after all devices respond successfully to a "recording" command.
        if command == "recording-ok":
            print("RECORDING OK")
            self.turn_on(True)
            cmd.lightbulbOn(True)
            self.recording = True
            self.update_state("RECORDING", "")

        if command == "stop":
            self.update_state("ONLINE", "")
            self.turn_on(False)
            cmd.lightbulbOn(False)
            self.recording = False

    def teardown(self):
        """ Device is being deleted, shutdown gracefully """
        pass

    @staticmethod
    def dialog(settings):
        return HueDeviceWidget(settings)

    @staticmethod
    def dialog_callback(widget):

        if not widget.do_add():
            return

        try:
            phue.Bridge(widget.host.text())
        except phue.PhueRegistrationException as e:
            QtWidgets.QMessageBox.information(widget, "Hue", "Press the button on the Hue Bridge to connect then close this window.")

            try:
                phue.Bridge(widget.host.text())
            except phue.PhueRegistrationException as e:
                QtWidgets.QMessageBox.information(widget, "Hue", "Could not connect to the Hue Bridge")
                return

        rec_ok_color = widget.rec_ok_color.text()
        idle_color = widget.idle_color.text()
        return Hue(widget.name.text(), widget.host.text(), rec_ok_color, idle_color)

    def edit(self, settings):
        dlg = HueDeviceWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):

        if not widget.do_add():
            return

        widget.update_device(self)

    def has_harvest(self):
        return False


