#!/usr/bin/env python3
'''main script for PyMoIP_server'''
import sys
import logging
import errno
import argparse
import warnings
import asyncio
import threading
import websockets

from Server.PyMoIP_server_gateway import Gateway
from Server.PyMoIP_server import Server
from Server.PyMoIP_global import *
# import asyncio to use its event loop


TestList=[["Toto1",123,"AAA1"],["Tata1",456,"AAA2"],["Titi1",7890,"AAA3"],["Toto2",1230,"AAA4"],["Tata2",4560,"AAA5"],["Titi2",7890,"AAA6"],["Toto2",1232,"AAA7"],["Tata2",4562,"AAA8"],["Titi2",7891,"AAA9"],["Toto3",1233,"AAA10"],["Tata3",4563,"AAA11"],["Titi3",7893,"AAA12"]]

#
# Variables globales
#

MyIP="0.0.0.0"  # 0.0.0.0 means all @IPs
MyPort=8765
MyPortGateway=8764


# Setup the logger
logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=logging.INFO,  # ERROR
                    handlers=[
                        logging.FileHandler("PyMoIP_server.log"),
                        logging.StreamHandler(sys.stdout)
                    ])

# Redirect warnings to the logger
logging.captureWarnings(True)
warnings.simplefilter('always')


parser = argparse.ArgumentParser(description="Launch the PyMoIP_server.")
parser.add_argument("-p", "--ws", type=int, metavar="PORT",
                    help="Specify a port for the WebSocket Server. (Default=8765)")
parser.add_argument("-c", "--command", metavar="PORT",
                    help="Specify a port for a command channel. (Default=8764)")
parser.add_argument("-a", "--arbo", metavar="PATH",
                    help="Specify the path and file name of arbo root (Default=.Server.arbo_teletel.)")
parser.add_argument("-i", "--ip", type=str, metavar="IP",
                    help="Specify an IP address to listen to. (Default=0.0.0.0 (all @IPs))")
parser.add_argument("-m", "--modules", metavar="PATH",
                    help="Specify the path of modules (Default=[])")
parser.add_argument("-n", "--nocommandchannel", action="store_true",
                    help="Disable command channel")
parser.add_argument("-s", "--server", metavar="DISPLAY NAME",
                    help="Specify the name of this server's instance (Default=[Videotext server])")

if __name__ == "__main__":
    args = parser.parse_args()

    MyPort       = args.ws
    MyIP         = args.ip
    command_port = args.command
    arbo_boot    = args.arbo
    path_modules = args.modules
    server_name  = args.server

    if MyPort is str :
      MyPort = int(MyPort)
    if MyPort is None:
      MyPort = 8765
      
    if MyIP is None:
      MyIP = "0.0.0.0"

    if MyPortGateway is str :
      MyPortGateway = int(MyPortGateway)
    if MyPortGateway is None :
      MyPortGateway = 8764

    if arbo_boot is None:
      arbo_boot = "Server.arbo_teletel."

    if path_modules is None:
      pass
    path_modules = ""

    if server_name is None:
      server_name = "Videotext Server"

    if args.nocommandchannel is True :
      MyPortGateway = None

    TheServer=Server(MyPortGateway,MyPort,arbo_boot,path_modules)

    try:
      #
      print("PyMoIP_server")
      print("#*#*#* " + server_name + " *#*#*#")
      print("Arbo_boot ... = '"+TheServer.arbo_boot+"'")
      print("MyPort ...... = "+str(MyPort))
      if MyPortGateway == None:
        print("No command port.")
      else:
        print("MyCommandPort = "+str(MyPortGateway))
      #    
      # Main
      #
      asyncio.get_event_loop().set_debug(DoDebugAsync)
      logging.basicConfig(level=logging.ERROR) #ERROR) #DEBUG)
      #https://pymotw.com/3/asyncio/debugging.html
     
      logger = logging.getLogger('websockets')
      logger.setLevel(logging.ERROR) # DEBUG / ERROR / INFO
      logger.addHandler(logging.StreamHandler())
    
      loop=asyncio.get_event_loop()
    
      if MyPortGateway!= None:  
        MyGtw=Gateway(logging,locals(),TheServer)
        start_server_gateway=websockets.serve(MyGtw.gateway_link, MyIP, MyPortGateway)
        print("MAIN:websockets.serve gateway_link() on @IP "+MyIP+ " and port "+str(MyPortGateway))
        TheServer.MyGtw=MyGtw
      
      start_server=websockets.serve(TheServer.VideotextServer, MyIP, MyPort)
      print("MAIN:websockets.serve videotext_server() on @IP "+MyIP+ " and port "+str(MyPort))
    
      #ShowAsyncTasks("Pending tasks after websocket.serve()")
      #if DoDebugAsync == True : 
      #  z=asyncio.all_tasks()
      #  print("Pending tasks after websocket.serve()" + " : ="+str(len(z))+".")
      #  cnt=0
      #  for zz in z:
      #    cnt+=1
      #    print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
      #    print(zz.get_stack(limit=3))
      Try_Gtw=False    
      if MyPortGateway!= None:  
        loop.run_until_complete(start_server_gateway)
        Try_Gtw=True
      loop.run_until_complete(start_server)
    
      loop.set_exception_handler(TheServer.handle_exception)
      loop.run_forever()
    except OSError:
      if MyPortGateway == None or Try_Gtw==True:
        print("Port "+str(MyPort)+" on address "+MyIP+" already in use or invalid")
      else:
        print("[Command channel] Port "+str(MyPortGateway)+" on address "+MyIP+" already in use or invalid")
      err=sys.exc_info()
      for item in err:
        print(item)
        
    except:
      print ("ERR:Main() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
      err=sys.exc_info()
      for item in err:
        print(item)
        
    finally:
      try:
        #if DoDebugAsync == True or True: 
        #  z=asyncio.all_tasks()
        #  print(MyMessage + " : ="+str(len(z))+".")
        #  cnt=0
        #  for zz in z:
        #    cnt+=1
        #    print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
        #    print(zz.get_stack(limit=3))
        pass
      except:
        print ("ERR:AfterMain() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
        err=sys.exc_info()
        for item in err:
          print(item)
      finally:
        asyncio.get_event_loop().close()
