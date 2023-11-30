from PeelApp import cmd
from peel_devices import SimpleDeviceWidget, PeelDeviceBase

class CapturyWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(CapturyWidget, self).__init__(settings, "Captury", has_host=True, has_port=True,
                                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        
class Captury(PeelDeviceBase):

    def __init__(self, name="captury", host="127.0.0.1"):
        super(Captury, self).__init__(name)
        self.device_state = "OFFLINE"
        self.info = ""
        self.host = host
        self.plugin_id = cmd.createDevice("Captury")
        if self.plugin_id == -1:
            raise RuntimeError("Could not create captury plugin device")
        cmd.setDeviceEnabled(self.plugin_id, self.enabled)
        cmd.configureDevice(self.plugin_id, host)

    def set_enabled(self, value):
        super().set_enabled(value)
        cmd.setDeviceEnabled(self.plugin_id, value)

    @staticmethod
    def device():
        return "captury"
    
    def as_dict(self):
        return {'name': self.name,
                'host': self.host }
    
    def reconfigure(self, name, **kwargs):
        self.name = name
        if 'host' in kwargs:
            self.host = kwargs['host']
            cmd.configureDevice(self.plugin_id, self.host)
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
        return CapturyWidget(settings)
    
    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return
        
        ret = Captury()
        if widget.update_device(ret):
            return ret
        
    def edit(self, settings):
        diag = CapturyWidget(settings)
        diag.populate_from_device(self)
        return diag

    def has_harvest(self):
        return False
    
    def list_takes(self):
        return []

    

