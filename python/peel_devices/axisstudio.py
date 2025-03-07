from PeelApp import cmd
from peel_devices import SimpleDeviceWidget, PeelDeviceBase


class AxisStudioWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(AxisStudioWidget, self).__init__(settings, "AxisStudio", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)

        url = "https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-axis/"
        self.info_text = "Perception Neuron Axis Studio.  <A HREF=\"" + url + "\">Documentation</A>"


class AxisStudio(PeelDeviceBase):

    def __init__(self, name="AxisStudio"):
        super(AxisStudio, self).__init__(name)
        self.device_state = "ONLINE"
        self.info = ""
        self.name = name
        self.host = "127.0.0.1"
        self.port = 0

    @staticmethod
    def device():
        return "axisstudio"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port}

    def reconfigure(self, name, **kwargs):

        if self.plugin_id == -1:
            self.plugin_id = cmd.createDevice("AxisStudio")
            if self.plugin_id == -1:
                raise RuntimeError("Could not create plugin device")

        self.name = name
        self.host = kwargs['host']
        self.port = kwargs['port']
        cmd.configureDevice(self.plugin_id, f"{self.host}:{self.port}")
        # cmd.setDeviceEnabled(self.plugin_id, self.enabled)
        return True

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
        return AxisStudioWidget

    def has_harvest(self):
        return False

    def list_takes(self):
        return []
