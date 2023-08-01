from PeelApp import cmd
from peel_devices import SimpleDeviceWidget, PeelDeviceBase

class AxisStudioWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(AxisStudioWidget, self).__init__(settings, "AxisStudio", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)

class AxisStudio(PeelDeviceBase):

    def __init__(self, name="AxisStudio", host=None, port=None):
        super(AxisStudio, self).__init__(name)
        self.device_state = "ONLINE"
        self.info = ""
        self.name = name
        self.host = host
        self.port = port
        self.plugin_id = cmd.createDevice("AxisStudio")
        if self.plugin_id == -1:
            raise RuntimeError("Could not create plugin device")
        if host and port:
            cmd.configureDevice(self.plugin_id, f"{self.host}:{self.port}")
            cmd.setDeviceEnabled(self.plugin_id, self.enabled)

    def set_enabled(self, value):
        super().set_enabled(value)
        cmd.setDeviceEnabled(self.plugin_id, value)

    @staticmethod
    def device():
        return "axisstudio"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port}

    def reconfigure(self, name, **kwargs):
        self.name = name
        self.host = kwargs['host']
        self.port = kwargs['port']
        cmd.configureDevice(self.plugin_id, f"{self.host}:{self.port}")
        cmd.setDeviceEnabled(self.plugin_id, self.enabled)

    def teardown(self):
        cmd.deleteDevice(self.plugin_id)

    def thread_join(self):
        pass

    def command(self, command, arg):
        # plugin commands are passed directly
        pass

    def get_state(self):
        # plugin device states are managed directly
        return ""

    def get_info(self):
        # plugin device info messages are handled directly
        return ""

    @staticmethod
    def dialog(settings):
        return AxisStudioWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        ret = AxisStudio()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = AxisStudioWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)

    def has_harvest(self):
        return False

    def list_takes(self):
        return []
