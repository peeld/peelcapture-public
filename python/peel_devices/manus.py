from peel_devices.xml_udp import XmlUdpDeviceBase
from peel_devices import SimpleDeviceWidget


class ManusWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Manus", has_host=True, has_port=True,
                         has_broadcast=False, has_listen_ip=False, has_listen_port=False)


class Manus(XmlUdpDeviceBase):

    def __init__(self, name="Manus"):
        super(Manus, self).__init__(name, data_format="manus")

    @staticmethod
    def device():
        return "manus"

    @staticmethod
    def dialog_class():
        return ManusWidget
