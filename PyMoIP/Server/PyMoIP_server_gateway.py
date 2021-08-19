#!/usr/bin/envh python
# PyMoIPserver_gateway

import sys
import asyncio
import websockets
from Server.PyMoIP_global import *

class Gateway:
  def __init__(self,logging,MyLocal,TheServer):
    self._outgoing_gateway_link_queue=asyncio.Queue()
    self._gateway_link_connected=False
    self.logging=logging
    self.MyLocal=MyLocal
    self.TheServer=TheServer

      
  async def _incoming_gateway_link(self,websocket) :
        #global Server.ListSession
        print("_incoming_gateway_link() started")
        print(self.TheServer.refs['ListSession']) #.ListSession)

        def ShowAsyncTasks(MyMessage, Force=False):
            if Force == True: 
              z=asyncio.all_tasks()
              print(MyMessage + " : ="+str(len(z))+".")
              cnt=0
              for zz in z:
                cnt+=1
                print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                print(zz.get_stack(limit=3))
        
        recv_cnt=0
        while True:# not websocket.closed:
          try:
            recv_cnt += 1
            DataFromWsServer = await websocket.recv()
            print ("server.py->_incoming_ws_bis() WaitReceiveCount: "+str(recv_cnt) + " len=" + str(len(DataFromWsServer))  + " bytes of command from server")
            print (DataFromWsServer)
            Result=DataFromWsServer.split(',')
            if len(Result)>4:
              NewState=-1
              if Result[0].upper() == "USERREDIRECTING":
                print("GatewayLink() UserRedirecting : "+str(Result[4]))
                NewState=START_REDIR
              if Result[0].upper() == "USERREDIRECTENDED":
                print("GatewayLink() UserRedirectEnded : "+str(Result[4]))
                NewState=NO_REDIR
              if Result[0].upper() == "USERREDIRECTED":
                print("GatewayLink() UserRedirected : "+str(Result[4]))
                NewState=OK_REDIR
              if NewState>=0:
                #print(self.MyLocal['ListSession'])
                #MyList=self.MyLocal['ListSession']
                MyList=self.TheServer.refs['ListSession']
                Found=-1
                Count=0
                for item in MyList:
                    #print(type(item[LIST_SESSION_SESSION]))
                    #print(item[LIST_SESSION_SESSION])
                    #print(type(Result[4]))
                    #print(Result[4])
                    if str(item[LIST_SESSION_SESSION])==Result[4]:
                      Found=Count
                      break
                    Count+=1
                if Found>-1:
                    #print(self.MyLocal['ListSession'][Found][LIST_SESSION_MYARBO])
                    #print(self.MyLocal['ListSession'][Found][LIST_SESSION_MYARBO].StateRedir)
                    #self.MyLocal['ListSession'][Found][LIST_SESSION_MYARBO].StateRedir=NewState
                    #self.MyLocal['ListSession'][Found][LIST_SESSION_MYARBO]._RcvQueue.put_nowait("GTW:StateRedir=NewState") # Pong timeout as message !
                    self.TheServer.refs['ListSession'][Found][LIST_SESSION_MYARBO].StateRedir=NewState
                    self.TheServer.refs['ListSession'][Found][LIST_SESSION_MYARBO]._RcvQueue.put_nowait("GTW:StateRedir=NewState") # Pong timeout as message !
                    #print(self.MyLocal['ListSession'][Found][LIST_SESSION_MYARBO].StateRedir)
                else:
                  print("Not found session in ListSession")
                  pass
              else:
                print("Invalid NewState")

            #MySession.MsgToUser(DataFromWsServer,False)
            self.logging.debug("received [%s] of command from WS server (%s)", DataFromWsServer,recv_cnt)
          except websockets.exceptions.ConnectionClosed:
            print("_incoming_gateway_link() ConnectionClosed")
            #MySession.MsgToUser("\n\rGatewayServer.py->_incoming_ws_server() :\n\rWS server connection closed\n\r",False)
            break
          except:
            print ("ERR:GatewayLink()incoming_link "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
            err=sys.exc_info()
            for item in err:
              print(item)
            raise
        print("_incoming_gateway_link() ended")
  
  async def _outgoing_gateway_link(self,websocket) :
        print("_outgoing_gateway_link() started")
        sent_cnt=0
        while True: #not websocket.closed:
          try:
            sent_cnt += 1
            #print("GatewayServer.py->_outgoing_ws_server() WaitKeysForwardCount: "+str(sent_cnt) + " for PID #" + str(pid))        
            DataToWsServer = await self._outgoing_gateway_link_queue.get()
            try:
                await websocket.send(DataToWsServer)
                print ("server.py->__outgoing_gateway_link() Sent " + str(len(DataToWsServer)) + " bytes of command to server")
                print (DataToWsServer)
                self.logging.debug("send [%s] of command to WS server (%s)", DataToWsServer,sent_cnt)
                #for char in DataToWsServer:
                #  print("'0x{:02x}'".format(ord(char)))
            except websockets.exceptions.ConnectionClosed:
                print("ERR:GatewayLink()->GatewayServer.py->_ws_connect_to_server() : WS server connection closed while await websocket.send("+str(DataToWsServer)+")")
                print(type(DataToWsServer))
                break
            except:
              print ("ERR:GatewayLink()outgoing_link,await websocket.send()" + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
          except websockets.exceptions.ConnectionClosed:
            print("ERR:GatewayLink()->GatewayServer.py->_ws_connect_to_server() : WS server connection closed while await queue.get()")
            #MySession.MsgToUser("\n\rGatewayServer.py->_ws_connect_to_server() : WS server connection closed\n\r",False)
            break
          except:
            print ("ERR:GatewayLink()outgoing_link," + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
            err=sys.exc_info()
            for item in err:
              print(item)
            raise
        print("_outgoing_gateway_link() ended")
  
  async def gateway_link(self,websocket,path):
    try:
      print("GatewayLink() opened")
      self._gateway_link_connected=True
      done,pending = await asyncio.wait([
                  self._incoming_gateway_link(websocket),
                  self._outgoing_gateway_link(websocket)
                  ],
                  #timeout=10,
                  return_when=asyncio.FIRST_COMPLETED)
      print("GatewayLink closed")
      self._gateway_link_connected=False
      print("Done:")
      print(done)
      print("Pending:")
      print(pending)
      #while not websocket.closed :
      #  RawReceived = await websocket.recv()
      #  print("***** ReceivedFromGateway ******")
      #  print(type(RawReceived))
      #  print(RawReceived)
    except :
      print ("ERR:GatewayLink()(xxxxx," + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
      err=sys.exc_info()
      for item in err:
        print(item)
      
    finally:
      await websocket.close()
      print("GatewayLink() closed")
