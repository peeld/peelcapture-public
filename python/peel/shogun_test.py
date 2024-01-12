from vicon_core_api import client

import ViconShogunPost

c = client.Client()

print(c.server_version())

print(c.connected)

