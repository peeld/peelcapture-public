"""Small example OSC server

    This program listens to several addresses, and prints some information about
    received packets.
"""
import argparse
import math

from pythonosc import dispatcher
from pythonosc import osc_server

def print_volume_handler(unused_addr, args, volume):
    print("[{0}] ~ {1}".format(args[0], volume))

def print_compute_handler(unused_addr, args, volume):
  try:
      print("[{0}] ~ {1}".format(args[0], args[1](volume)))
  except ValueError: pass

def default_handler(unused_addr, *args):
    print(args)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="0.0.0.0", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=5005, help="The port to listen on")
  args = parser.parse_args()

  dispatcher1 = dispatcher.Dispatcher()
  dispatcher1.map("/filter", print)
  dispatcher1.map("/volume", print_volume_handler, "Volume")
  dispatcher1.map("/logvolume", print_compute_handler, "Log volume", math.log)
  dispatcher1.set_default_handler(default_handler)

  server = osc_server.BlockingOSCUDPServer((args.ip, args.port), dispatcher1)
  print("Serving on {}".format(server.server_address))
  server.serve_forever()