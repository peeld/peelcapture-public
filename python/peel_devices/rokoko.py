
from peel_devices.xml_udp import XmlUdpDeviceBase
from peel_devices import SimpleDeviceWidget
from PySide6 import QtWidgets


class RokokoWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super().__init__(settings, "Rokoko", has_host=True, has_port=True,
                         has_broadcast=True, has_listen_ip=True, has_listen_port=True,
                         has_set_capture_folder=False)

        self.enter_clip_editing = QtWidgets.QCheckBox()
        self.enter_clip_editing.setChecked(False)
        self.enter_clip_editing.setToolTip("Enter Clip Editing Mode On Stop Recording")
        self.form_layout.addRow("Enter Clip Editing", self.enter_clip_editing)

        link = 'https://support.rokoko.com/hc/en-us/articles/15566313142161-UDP-Trigger-Messages'
        msg = '<P><A HREF="' + link + '">Documentation</P>'
        self.set_info(msg)

    def populate_from_device(self, device):
        self.enter_clip_editing.setChecked(device.enter_clip_editing)

    def update_device(self, device, data=None):
        if data is None:
            data = {}
        data['enter_clip_editing'] = self.enter_clip_editing.isChecked()
        return super(RokokoWidget, self).update_device(device, data)

    def do_add(self):
        if not super().do_add():
            return False

        self.settings.setValue(self.title + "EnterIsolationMode", self.enter_clip_editing.isChecked())
        return True


class Rokoko(XmlUdpDeviceBase):

    def __init__(self, name=None, host=None, port=14047, broadcast=None, listen_ip=None, listen_port=14048,
                 enter_clip_editing=False):
        super().__init__(name, host, port, broadcast, listen_ip, listen_port, fmt="Rokoko",
                         enter_clip_editing=enter_clip_editing)
        
    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port,
                'broadcast': self.broadcast,
                'listen_ip': self.listen_ip,
                'listen_port': self.listen_port,
                'enter_clip_editing': self.enter_clip_editing }

    @staticmethod
    def device():
        return "rokoko"

    @staticmethod
    def dialog(settings):
        return RokokoWidget(settings)

    @staticmethod
    def dialog_callback(widget):
        if not widget.do_add():
            return
        ret = Rokoko()
        if widget.update_device(ret):
            return ret

    def edit(self, settings):

        dlg = RokokoWidget(settings)
        dlg.populate_from_device(self)
        return dlg

    def edit_callback(self, widget):
        if not widget.do_add():
            return
        widget.update_device(self)





