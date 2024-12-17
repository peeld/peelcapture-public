from PeelApp import cmd
from peel_devices import SimpleDeviceWidget, PeelDeviceBase
from PySide6 import QtWidgets


class CapturyDeviceWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(CapturyDeviceWidget, self).__init__(settings, "Captury", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)

        self.timecode_cb = QtWidgets.QCheckBox("")
        self.timecode_cb.setChecked(settings.value(self.title + "Timecode") == "True")
        self.form_layout.addRow("Timecode", self.timecode_cb)

        self.subjects_cb = QtWidgets.QCheckBox("")
        self.subjects_cb.setChecked(settings.value(self.title + "Subjects") == "True")
        self.form_layout.addRow("Subjects", self.subjects_cb)

    def populate_from_device(self, device):
        super().populate_from_device(device)
        self.timecode_cb.setChecked(device.timecode is True)
        self.subjects_cb.setChecked(device.subjects is True)

    def update_device(self, device, data=None):
        if data is None:
            data = {}

        data["timecode"] = self.timecode_cb.isChecked()
        data["subjects"] = self.subjects_cb.isChecked()

        return super().update_device(device, data)

    def do_add(self):

        if not super().do_add():
            return False

        self.settings.setValue(self.title + "Timecode", str(self.timecode_cb.isChecked()))
        self.settings.setValue(self.title + "Subjects", str(self.subjects_cb.isChecked()))

        return True

class MyDevice(PeelDeviceBase):

    def __init__(self, name="captury"):
        super(MyDevice, self).__init__(name)

        self.device_state = "ONLINE"
        self.info = ""
        self.host = "127.0.0.1"
        self.port = 2101
        self.timecode = None
        self.subjects = None

        self.plugin_id = cmd.createDevice("Captury")
        if self.plugin_id == -1:
            raise RuntimeError("Could not create captury device")

    @staticmethod
    def device():
        return "captury"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'subjects': self.subjects,
                'timecode': self.timecode}

    def reconfigure(self, name, **kwargs):
        self.name = name
        if 'host' in kwargs:
            self.host = kwargs['host']

        if 'port' in kwargs:
            self.port = kwargs['port']

        if 'subjects' in kwargs:
            self.subjects = kwargs['subjects']

        if 'timecode' in kwargs:
            self.timecode = kwargs['timecode']

        cmd.configureDevice(self.plugin_id, f"host={self.host}:{self.port}\ntimecode={int(self.timecode)}\nsubjects={int(self.subjects)}\n")
        cmd.setDeviceEnabled(self.plugin_id, self.enabled)

    def connect_device(self):
        pass

    def teardown(self):
        cmd.deleteDevice(self.plugin_id)

    def thread_join(self):
        pass

    def command(self, command, arg):
        # plugin commands are passed directly
        pass

    def get_state(self, reason=None):
        # plugin device states are managed directly
        return ""

    def get_info(self, reason=None):
        # plugin device info messages are handled directly
        return ""

    @staticmethod
    def dialog_class():
        return CapturyDeviceWidget

    def has_harvest(self):
        return False

    def list_takes(self):
        return []
