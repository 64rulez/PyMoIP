#!/usr/bin/env python3
'''main script for PyMoIPgateway'''
import sys
import logging
import errno
import argparse
import warnings
# import the MUD server class
from Gateway.GatewayServer import GatewayServer

# import asyncio to use its event loop
import asyncio

# Setup the logger
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO,  # ERROR
                    handlers=[
                        logging.FileHandler("server.log"),
                        logging.StreamHandler(sys.stdout)
                    ])

# Redirect warnings to the logger
logging.captureWarnings(True)
warnings.simplefilter('always')


parser = argparse.ArgumentParser(description="Launch the PyMoIP gateway.")
parser.add_argument("--ws", type=int, metavar="PORT",
                    help="Specify a port for a WebSocket Server. (Default=9001)")
parser.add_argument("--tcp", type=int, metavar="PORT",
                    help="Specify a port for a TCP Server. (Default=9000)"
                    "(If no port is provided, no TCP Server will be created.)")                    
parser.add_argument("-c", "--command", metavar="URI",
                    help="Specify an URI for WS Gatewayink to 'Télétel'"
                    "(default='ws://localhost:8764' for normal command channel)")
parser.add_argument("-v", "--videotext", metavar="URI",
                    help="Specify an URI to WS default videotext server (Default=ws://localhost:8765)")
parser.add_argument("-i", "--interval", metavar="PING",
                    help="Specify the ping interval to WS default videotext server (Default=None)")
parser.add_argument("-b", "--subprotocols", metavar="PROTO",
                    help="Specify subprotocols for WS default videotext server (Default=[])")
parser.add_argument("-n", "--nocommand", metavar="SWITCH",
                    help="Disable command channel")

# TODO: add log level to the parser
#zzparser.add_argument("--default-class", metavar="CLASS",
#zz                    help="Force all characters to spawn as [CLASS]")
#zzparser.add_argument("--default-location", metavar="LOCATION",
#zz                    help="Force all new characters to spawn at [LOCATION].\
#zz                          Overrides any default class spawn locations.")

if __name__ == "__main__":
    args = parser.parse_args()

    ws_port = args.ws
    tcp_port = args.tcp
    command_server   = args.command
    teletel_server   = args.videotext
    teletel_interval = args.interval
    teletel_subproto = args.subprotocols

    if command_server is None :
      command_server = "ws://localhost:8764"
    if teletel_server is None:
      teletel_server = "ws://localhost:8765"
    if teletel_interval is None:
      teletel_interval = None
    if teletel_subproto is None:
      teletel_subproto="[]"
    if args.nocommand is None :
      pass
    else:
      command_server = None
      
    # perform some error handling
    if ws_port is None and tcp_port is None:
        # default to WebSocket server on port 9001
        ws_port = 9001
    elif ws_port == tcp_port:
        print("Error: TCP server and WebSocket server cannot use the "
                f"same port '{ws_port}'.\nProvide different ports "
                "for each server.",
                file=sys.stderr)
        exit(1)

    if tcp_port is not None:
        if ws_port is None:
          logging.info("Launching a TCP Server on port '%d'", tcp_port)
        else:
          logging.info("Launching a WebSocket Server on port '%d' and a TCP Server on port '%d'", ws_port, tcp_port)
    else:
        logging.info("Launching a WebSocket Server on port '%d'", ws_port)

    try:
        print("Target server '"+teletel_server+"' ping_interval="+str(teletel_interval)+" subprotocols="+teletel_subproto)
        server = GatewayServer(ws_port, tcp_port, command_server, teletel_server, teletel_interval , teletel_subproto)
        
    # TODO: these excepts are no longer necessary, since port is bound until server.run() is called
    except PermissionError:
        print(f"Error. Do not have permission to use port '{args.port}'",
              file=sys.stderr)
        exit(-1)
    except OSError as ex:
        if ex.errno == errno.EADDRINUSE:
            print(f"Error. Port '{args.port}' is already in use.",
                  file=sys.stderr)
        else:
            print(ex, file=sys.stderr)
        exit(-1)

    try:
        asyncio.get_event_loop().run_until_complete(server.run())
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt detected")
        server.shutdown()
    # Shut down the server gracefully
    logging.info("Shutting down server")
    logging.info("Server shutdown. Good bye!!")
