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


from peel_devices import PeelDeviceBase, SimpleDeviceWidget
import socket


class QTakeWidget(SimpleDeviceWidget):
    def __init__(self, settings):
        super(QTakeWidget, self).__init__(settings, "QTake", has_host=True, has_port=False,
                                          has_broadcast=False, has_listen_ip=False, has_listen_port=False,
                                          has_set_capture_folder=False)

        link = 'https://support.peeldev.com/peelcapture/peelcapture-devices/peelcapture-device-qtake/'
        msg = '<P><A HREF="' + link + '">Documentation</A></P>\nQTAKE listens on port 7001.'
        self.set_info(msg)


class QTake(PeelDeviceBase):

    def __init__(self, name="QTake"):
        super(QTake, self).__init__(name)
        self.host = "192.168.1.100"
        # QTake only listens on 7001
        self.port = 7001
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.state = "OFFLINE"
        self.info = None
        self.shot_name = None
        self.take_number = None

    @staticmethod
    def device():
        return "qtake"

    def as_dict(self):
        return {'name': self.name,
                'host': self.host}

    def reconfigure(self, name, host=None):
        self.name = name
        self.host = host
        return True

    def connect_device(self):
        self.teardown()
        xml = "<qtake_remote>\n<connect_client uuid='PeelCapture' type='1'/>\n</qtake_remote>\n"
        self.state = "ONLINE"
        self.update_state(self.state, self.info)
        self.send_udp_command(xml, "connect")

    def __str__(self):
        return self.name

    def teardown(self):
        if self.udp is not None:
            self.udp.close()
            self.udp = None

    def get_state(self, reason=None):
        return self.state

    def get_info(self, reason=None):
        return self.info

    def send_udp_command(self, xml, command):

        try:
            self.udp.sendto(xml.encode(), (self.host, self.port))
            self.udp.settimeout(1)
            response, address = self.udp.recvfrom(4096)
            print(f"{self.name} response to '{command}': {response.decode()}")

        except Exception as e:
            self.state = "ERROR"
            self.info = str(e)
            msg = f"{self.name} failed to '{command}'."
            msg += "Check that PeelCapture is enabled as a stream client in the STREAM toolbar."
            print(msg)

        self.update_state(self.state, "")

    def command(self, command, arg):

        # print("QTAKE", command, arg)
        self.info = None

        if command == "record":
            xml = "<qtake_remote>\n<record start='1' recorder='1'/>\n<target_input id='1'>"\
                  f"<set_clip_data shot='{arg}' take='{self.take_number}'/>\n"\
                  "</target_input>\n</qtake_remote>"
            self.state = "RECORDING"
            self.send_udp_command(xml, command)

        if command == "stop":
            xml = "<qtake_remote>\n<record stop='1' recorder='1'/>\n<target_input id='1'>"\
                  f"<set_clip_data shot='{self.shot_name}' take='{self.take_number}'/>\n"\
                  "</target_input>\n</qtake_remote>"
            self.state = "ONLINE"
            self.send_udp_command(xml, command)

        if command == "takeName":
            self.take_name = arg

        if command == "shotName":
            self.shot_name = arg

        if command == "takeNumber":
            self.take_number = arg

    @staticmethod
    def dialog_class():
        return QTakeWidget


