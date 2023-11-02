from peel_devices.xml_udp import XmlUdpDeviceBase
from peel_devices import SimpleDeviceWidget


class Manus(XmlUdpDeviceBase):

    def __init__(self, name=None, host=None, port=None, broadcast=None, listen_ip=None, listen_port=None):
        super(Manus, self).__init__(name, host, port, broadcast, listen_ip, listen_port)

    @staticmethod
    def device():
        return "manus"

    @staticmethod
    def dialog(settings):
        return SimpleDeviceWidget(settings, "Manus", has_host=True, has_port=True,
                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return

        ret = Manus()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):
        dlg = SimpleDeviceWidget(settings, "Manus", has_host=True, has_port=True,
                                 has_broadcast=False, has_listen_ip=False, has_listen_port=False)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return

        widget.update_device(self)
