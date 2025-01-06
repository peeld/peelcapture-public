from PeelApp import cmd
from peel_devices import SimpleDeviceWidget, PeelDeviceBase


class CapturyDeviceWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(CapturyDeviceWidget, self).__init__(settings, "Captury", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class MyDevice(PeelDeviceBase):

    def __init__(self, name="captury"):
        super(MyDevice, self).__init__(name)
        self.device_state = "ONLINE"
        self.info = ""
        self.host = "127.0.0.1"
        self.port = 2101

    @staticmethod
    def device():
        return "captury"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port}

    def reconfigure(self, name, **kwargs):

        if self.plugin_id == -1:
            self.plugin_id = cmd.createDevice("Captury")
            if self.plugin_id == -1:
                raise RuntimeError("Could not create captury device")


        self.name = name
        if 'host' in kwargs:
            self.host = kwargs['host']

        if 'port' in kwargs:
            self.port = kwargs['port']

        cmd.configureDevice(self.plugin_id, f"{self.host}:{self.port}")
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
