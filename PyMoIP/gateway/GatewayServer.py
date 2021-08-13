"""
Basic MUD server module for creating text-based Multi-User Dungeon
(MUD) games.

This module provides one class, MudServer, which represents
the game instance, tracks UserSessions, and handles interactions with
TcpClients and websockets.

This module and the MudServer claass was originally written by Mark
Frimston (mfrimston@gmail.com). We based MuddySwamp on Mark's code for
over 2 years, before ultimately replacing it with an asynchronous server
that would work better with the websockets package. Without Mark's
original module, this project would have never gotten off the ground.
Thank you, Mark.
"""
import logging
import traceback
import warnings
from Gateway.util.biject import Biject
# for asynchronous stuff
import asyncio
# required for websockets to work
import websockets
import sys
import time

from Gateway.Session import Session

logger = logging.getLogger('websockets')
logger.setLevel(logging.ERROR) # DEBUG / ERROR / INFO
logger.addHandler(logging.StreamHandler())

# Timeouts https://medium.com/@pgjones/an-asyncio-socket-tutorial-5e6f3308b8b0
TIMEOUT_TN_CLIENT = 10*60       # La session telnet est fermée après 10 minutes sans caractère reçu 
TIMEOUT_TN_CLIENT_MAX = 60*60   # La session telnet dure maximum 1 heure 
TIMEOUT_WS_CLIENT = 10*60       # La session WS est fermée après 10 minutes sans caractère reçu
TIMEOUT_WS_CLIENT_MAX = 60*60   # La session WS dure maximum 1 heure
TIMEOUT_WS_SERVER = 10*60       # La session WS serveur est fermée après 10 minutes sans caractère reçu
TIMEOUT_WS_SERVER_MAX = 2*60*60 # La session WS serveur dure maximum 2 heures
TIMEOUT_GTW =5

class GatewayServer:
    '''A high-level game server that coordinates between a TelnetServer
    instance and the in-game world.

    Generally speaking, you should initialize this object, not a telnet
    server.
    '''

    def __init__(self, ws_port=None, tcp_port=None, teletel_server=None, target_uri="ws://localhost:8765",target_ping=None, target_sub=[]):
        logging.debug("Server %r created", self)
        
        self.DebugIAC = False
        # dict mapping pid [int] to in-game Characters use a biject here so we can get Characters back if needed
        self.UserSessions = Biject()
        
        #self.targeturi = "ws://localhost:8765"
        #self.targeturi = "ws://mntl.joher.com:2018/?echo" # ping_interval=None
        #self.targeturi = "ws://3611.re/ws"
        #self.targeturi = "wss://3615co.de/ws"
        #self.targeturi = "ws://34.223.255.81:9999/?echo"
        #self.targeturi = "ws://minitel.3614teaser.fr:8080/ws"  # ping_interval=10, subprotocols=["binary","tty"]
        #self.targetping=10
        #self.targetsub=["binary","tty"]
        #self.targetping=None
        #self.targetsub=[]
        self.targeturi=target_uri
        self.targetping=target_ping
        self.targetsub=target_sub
        
        self._ws_server = {}        # websocket[pid] vers serveur

        self._ws_server_bis = {}        # websocket[pid] vers serveur
        self._ws_server_bis_queue = asyncio.Queue()
        self._ws_server_bis_connected=False

        self.teletel_server = teletel_server

        self.msgs = asyncio.Queue()

        self.tcp_port = tcp_port
        self.tcp_server = None
        self._tcp_clients = {}

        self.ws_port = ws_port
        self.ws_server = None
        self._ws_clients = {}

        # by tracking clients, we can write a 'kick' function and have a cleaner shutdown (in the case of the tcp server)

        self.next_id = 0
        self._running = False

        if tcp_port is None and ws_port is None:            # at least one port must be provided
            raise ValueError("Cannot create a gateway without at least one TCP or WS port.")

    async def run(self):
        """Begin this MudServer.
        This method is asynchronous, so it must be called in the context
        of an event loop, perhaps like this:
            asyncio.get_event_loop().run_until_complete(my_mud.run())
        """
        logging.debug("Starting server...")
        # First, check to make sure the same server instance isn't being
        # run multiple times.g
        if self._running:
            raise RuntimeError(f"server {self!r} is already running")

        # Flag the server as running
        self._running = True

        # We create a list of coroutines, since we might be running more
        # than just one if we have a TCP Server AND a WebSocketServer.
        coroutines = []
        if self.teletel_server != None :
          coroutines.append(self._ws_connect_to_server_bis(self.teletel_server))    # "ws://localhost:8764"))
          logging.debug("Server command on '"+self.teletel_server+"' ...")

        if self.tcp_port is not None:
            # start asyncio.Server
            self.tcp_server = await asyncio.start_server(self._register_tcp,
                                                         port=self.tcp_port)
            # add it to the list of coroutines
            coroutines.append(self.tcp_server.serve_forever())

        if self.ws_port is not None:
            # start a WebSocketServer
            self.ws_server = await websockets.serve(self._register_ws,
                                                    port=self.ws_port)
            # use a simple coro so that MudServer doesn't close
            # with WebSocketServer still running
            coroutines.append(self.ws_server.wait_closed())
                
        # We use asyncio.gather() to execute multiple coroutines.
        await asyncio.gather(*coroutines, return_exceptions=True)

    def shutdown(self):
        """Shut down this server and disconnect all clients. (Both TCP
        and WebSocket clients are disconnected.)
        """
        if self.tcp_server is not None:
            self.tcp_server.close()
            # asyncio.Server doesn't automatically close existing
            # sockets, so we manually close them all now
            for stream_writer in self._tcp_clients.values():
                stream_writer.close()

        if self.ws_server is not None:
            self.ws_server.close()

        self._running = False

    # Callback methods for the TCP Server.
    # This method is executed whenever a new client connects to the
    # TCP server.
    async def _register_tcp(self, reader, writer):
        """Register a new TCP client with this server.
        This internal method is sent to asyncio.start_server().
        See https://docs.python.org/3/library/asyncio-stream.html to
        get a better idea of what's going on here.
        """
        # First, grab a new unique identifier.
        pid = self.next_id
        self.next_id += 1
        
        print("GatewayServer.py->_register_tcp() " + str(pid) + " started from " + writer.get_extra_info('peername')[0]+" (from port "+str(writer.get_extra_info('peername')[1])+")")
        self._ws_server_bis_queue.put_nowait("NewTelnetUser,"+writer.get_extra_info('peername')[0]+","+str(writer.get_extra_info('peername')[1])+","+str(pid))

        #print( writer.get_extra_info('peername'))

        # Now, store the tcp client in a dictionary, so we can track it
        # down later if necessary.
        self._tcp_clients[pid] = writer

        # This method will create a new Character and assign it to the user.
        # This method can be overriden for custom behavior.
        self.on_user_join(pid)

        self.UserSessions[pid].MyIP=writer.get_extra_info('peername')[0]
        self.UserSessions[pid].MyPort=str(writer.get_extra_info('peername')[1])
        self.UserSessions[pid].MyAccess="Telnet"

        # Now we create two coroutines, one for handling incoming messages, and one for handling outgoing messages.

        # If a user disconnects, the _incoming_tcp coroutine will wake up, and run to completion. However, the _outgoing_tcp coroutine
        # will be stuck waiting until the user's Character receives a message.
        # We want to move on immediately when the user disconnects, so we return_when=asyncio.FIRST_COMPLETED here.

        try:
          await asyncio.wait([self._incoming_tcp(pid, reader),
                            self._outgoing_tcp(pid, writer),
                            self._ws_connect_to_server(self.targeturi,pid,self.targetping,self.targetsub)
                            ],
                           timeout=TIMEOUT_TN_CLIENT_MAX,
                           return_when=asyncio.FIRST_COMPLETED)

        except asyncio.TimeoutError:
            print("Timeout _TN_CLIENT_MAX")


        # If the interpreter reaches this line, that means an EOF has
        # been detected and this user has disconnected.
        # Close the StreamWriter.
        writer.close()
        del self._tcp_clients[pid]
        print("_register_tcp() " + str(pid) + " ended")


        try:
          websocket = self._ws_server[pid]
          if not websocket.closed:
            print ("Closing _ws_server from _register_tcp")
            await websocket.close()
            print("Close() done")
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN GatewayServer.py->_register_tcp() no WS with server - server was already disconnected ?") 


        # Finally, call server.on_user_quit().
        # By default, this will delete the user's Character and send a
        # message to the other UserSessions, letting them know that this
        # user left.
        # This method can be overriden for custom behavior.
        self.on_user_quit(pid)

    async def _incoming_tcp(self, pid, reader):
        """Handle incoming messages from a Tcp Client."""
        print("GatewayServer.py->_incomming_tcp() " + str(pid) + " started")
        MySession = self.UserSessions[pid]
        
        CHAR_ECHO = 1
        CHAR_GO   = 3
        CHAR_STAT = 5
        CHAR_TIME = 6
        CHAR_TERM = 24
        CHAR_WIND = 31
        CHAR_SPEED= 32
        CHAR_FLOW = 33
        CHAR_LINE = 34
        CHAR_ENV  = 36
        
        CHAR_SE   = 240
        CHAR_NOP  = 241
        CHAR_DM   = 242
        CHAR_BRK  = 243
        CHAR_IP   = 244
        CHAR_AO   = 245
        CHAR_AYT  = 246
        CHAR_EC   = 247
        CHAR_EL   = 248
        CHAR_EL   = 249
        CHAR_SB   = 250
        CHAR_WILL = 251
        CHAR_WONT = 252
        CHAR_DO   = 253
        CHAR_DONT = 254
        CHAR_IAC  = 255
        IACState  = False
        IACStatus = 0
        IACCommand= 0
        IACOption =""
        IACDisabled=[]
        
        LineBuffer=""
        
        CountChar=0
        TmpBuf=""
        start_time = time.time()
        
        # Demande 'pas d'écho local' au client telnet
        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DO)+chr(CHAR_ECHO),self.DebugIAC)
        MySession.MsgToUser("Welcome to PyMoIP [telnet]/WS gateway\n\r",False)

        # When the user disconnects, asyncio will call it "EOF" (end of file). Until then, we simply try to read a line from the user.
        while not reader.at_eof():
            # reader.readline() is an asynchronous method
            # This means that it won't actually execute on its own unless we 'await' it.
            # Under the hood, using this 'await' actually switches to execute some other code until this user sends us a message.

            done,pending = await asyncio.wait([reader.read(1)]
                                      ,
                                     timeout=TIMEOUT_TN_CLIENT,
                                     return_when=asyncio.FIRST_COMPLETED
                                  )
            #print (type(msg))
            #print(msg)
            if len(done)>0:
              #print (type(done))
              #print(done)
              TaskFinished=done.pop()
              #print(type(TaskFinished))
              #print(TaskFinished)
              msg=TaskFinished.result()
              #print(type(msg))
              #print(msg)
            else:
              msg=None
              print("Timeout TN Client")
              break
            if msg:
              CountChar+=1
              if self.DebugIAC:
                print("_incoming_tcp() Got '0x{:02x}'".format(ord(msg)))
              if IACState==False:
                if ord(msg) == CHAR_IAC:
                  if self.DebugIAC:
                    print("_incoming_tcp() Got IAC")
                  IACState=True
                  IACStatus = 0 # Wait for OpCode
                  msg=None      # Filtre le caractère
                else:
                  pass          # Transmet le caractère
              elif IACStatus == 0: # Received OpCode
                if ord(msg) == CHAR_WILL or ord(msg) == CHAR_WONT or ord(msg) == CHAR_DO or ord(msg) == CHAR_DONT :
                  if self.DebugIAC:
                    print("GatewayServer.py->_incoming_tcp() Got OpCode")
                  IACStatus = 1 # Wait for option
                  IACCommand= ord(msg)
                  msg=None
                elif ord(msg) == CHAR_SB:
                  if self.DebugIAC:
                    print("GatewayServer.py->_incoming_tcp() Got SubOpCode")
                  IACStatus = 2   # Wait for SubOption
                  msg=None
                else :          # Illegal OpCode
                  if self.DebugIAC:
                    print("GatewayServer.py->_incoming_tcp() Illegal OpCode ->255")
                  msg == CHAR_IAC  # Transmet 255
                  IACState = False
              elif IACStatus == 1:  # Received command              
                if ord(msg) == CHAR_ECHO or ord(msg) == CHAR_GO :
                  if ord(msg) == CHAR_ECHO:
                    if self.DebugIAC:
                      print("GatewayServer.py->_incoming_tcp()  IAC Echo")
                    if IACCommand == CHAR_WONT or IACCommand == CHAR_DONT:
                      IACDisabled.append(ord(msg))
                      if IACCommand == CHAR_DONT :
                        if self.DebugIAC:
                          print("<Reply WONT>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                      else:
                        if self.DebugIAC:
                          print("<Reply DONT>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_DO:
                        if self.DebugIAC:
                          print("<Reply WILL>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_WILL)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_WILL:
                        if self.DebugIAC:
                          print("<Reply DO>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DO)+chr(ord(msg)),self.DebugIAC)
                     
                  elif ord(msg) == CHAR_GO:
                    if self.DebugIAC:
                      print("GatewayServer.py->_incoming_tcp() IAC Go")
                    if IACCommand == CHAR_WONT or IACCommand == CHAR_DONT:
                      IACDisabled.append(ord(msg))
                      if IACCommand == CHAR_DONT :
                        if self.DebugIAC:
                          print("<Reply WONT>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                      else:
                        if self.DebugIAC:
                          print("<Reply DONT>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_DO:
                        if self.DebugIAC:
                          print("<Reply WILL>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_WILL)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_WILL:
                        if self.DebugIAC:
                          print("<Reply DO>")
                        MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DO)+chr(ord(msg)),self.DebugIAC)
                else:              # Unknown command
                  if self.DebugIAC:
                    print ("GatewayServer.py->_incoming_tcp() Unknown IAC command")
                  IACDisabled.append(ord(msg))
                  if IACCommand == CHAR_DO or IACCommand == CHAR_DONT:
                    if self.DebugIAC:
                      print("<Reply WONT>")
                    MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                  else:
                    if self.DebugIAC:
                      print("<Reply DONT>")
                    MySession.MsgToUser(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                msg = None
                IACState = False
              elif IACStatus == 2:  # Received Suboption
                if self.DebugIAC:
                  print("GatewayServer.py->_incoming_tcp() IAC Suboption start")
                IACOption=msg
                msg = None
                IACStatus = 3       # Wait for action
              elif IACStatus == 3:  # Received Action
                IACOption+=msg      # 0 = Reply, 1 = Query - Bufferize until IAC+SE 
                msg = None
                if ord(msg) == CHAR_IAC or len(IACOption>20) : 
                  IACStatus = 4       # Bufferize until IAC+SE
              else:                  # Status = 4 ....
                if self.DebugIAC:
                  print("GatewayServer.py->_incoming_tcp() IAC Suboption end")
                IACOption+=msg      # Buffer full or SE
                IACState = False
                msg = None
                
            # The user just sent us a message!
            # Remove any whitespace and convert from bytes to str
            if msg:
              #msg = msg.strip().decode(encoding="latin1")
              msg=chr(ord(msg))
            if msg:
              if self.DebugIAC:
                print("GatewayServer.py->_incoming_tcp() Got '0x{:02x}' after IAC".format(ord(msg)))
                
              if CountChar<144 and ((time.time() - start_time) <1):
                TmpBuf+=msg
              elif CountChar==144 and ((time.time() - start_time) <1):
                TmpBuf+=msg
                print(TmpBuf)              
                CountChar=150
              else:              
                MySession.MsgFromUser(msg)

        print("GatewayServer.py->_incoming_tcp closed for %s", pid)
        logging.debug("GatewayServer.py->_incoming_tcp closed for %s", pid)

    async def _outgoing_tcp(self, pid, writer):
        """Handles outgoing messages, that is, messages sent to a session that must be forwarded to a user. """
        print("GatewayServer.py->_outgoing_tcp() " + str(pid) + " started")
        MySession = self.UserSessions[pid]

        # This coroutine just loops forever, and will eventually be broken once the client disconnects.
        while True:
            # Try to get a message from the Character's queue. This will block until the character receives a message.
            msg = await MySession.msgs.get()

            if type(msg) != bytes:                # Si on a reçu des 'bytes', on ne ré-encode pas en unicode sur l'accès telnet (permet à Timtel de recevoir des codes 8 bits tout en laissant PyMinitel fonctionner en WS)
              msg = (msg).encode('latin-1')
            writer.write(msg)

            # Once we've written to a StreamWriter, we have to call
            # writer.drain(), which blocks.
            try:
                await writer.drain()
            # If the user disconnected, we will get an error. We will break and finish the coroutine.
            except ConnectionResetError:
                break

        print("GatewayServer.py->_outgoing_tcp closed for %s", pid)
        logging.debug("GatewayServer.py->_outgoing_tcp closed for %s", pid)

    # Callback methods for new WebSocket connections.
    # This method is executed whenever a new WebSocket connects to the
    # WebSocketServer.
    async def _register_ws(self, websocket, path):
        # we don't currently do anything with the path, so just log it
        logging.debug("WebSocket %s connected at path %s", websocket, path)

        # First, grab a new unique identifier.
        pid = self.next_id
        self.next_id += 1
        
        self._ws_server_bis_queue.put_nowait("NewWsUser,"+websocket.remote_address[0]+","+str(websocket.remote_address[1])+","+str(pid))

        print("GatewayServer.py->_register_ws() " + str(pid) + " started from " + websocket.remote_address[0])

        # Now, store the websocket in a dictionary, so we can track it
        # down later if necessary.
        self._ws_clients[pid] = websocket

        # Call the server's custom handler. (By default, this will
        # create a new Character and assign it to the user.)
        self.on_user_join(pid)
        print("userJoined!")
        

        self.UserSessions[pid].MsgToUser("Welcome to PyMoIP telnet/[WS] gateway\n\r",False)
        self.UserSessions[pid].MyIP=websocket.remote_address[0]
        self.UserSessions[pid].MyPort=str(websocket.remote_address[1])
        self.UserSessions[pid].MyAccess="WS"

        # WebSockets have a slightly different API than the tcp streams
        # rather than a reading and writing stream, which just have
        # one socket.
        # As with _register_tcp, we want to quit immediately the user
        # disconnects, so we use return_when=asyncio.FIRST_COMPLETED
        # If this code is reached, then the WebSocket has disconnected.
        # This should already be closed, but just in case.

        done,pending = await asyncio.wait([self._incoming_ws(pid, websocket),
                            self._outgoing_ws(pid, websocket),
                            self._ws_connect_to_server(self.targeturi,pid,False,self.targetping,self.targetsub)
                            ],
                            timeout=TIMEOUT_WS_CLIENT_MAX,
                            return_when=asyncio.FIRST_COMPLETED)
        if len(done) == 0:
            print("Timeout _WS_CLIENT_MAX")
        print("_register_ws() : asyncio.wait completed")

        if not websocket.closed:
              await websocket.close()
              del self._ws_clients[pid]
              print("GatewayServer.py->_register_ws() : websocket.close()")
        else:
              print("GatewayServer.py->_register_ws() : websocket.close() already closed")

        try:
          websocket = self._ws_server[pid]
          if not websocket.closed:
            print ("GatewayServer.py->Closing _ws_server from _register_ws")
            await websocket.close()
            print("GatewayServer.py->Close() done")
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN GatewayServer.py->_register_ws() no WS with server - server was already disconnected ?") 

        # Call the server's event handler. (By default, this will simply
        # notify the other UserSessions.)
        self.on_user_quit(pid)

        # Delete the pid / websocket from the clients.
        #del self._ws_clients[pid]
        # (We still keep track of pid in self._UserSessions... just in case.)

    async def _kill_incoming_ws(self,pid):
        MySession = self.UserSessions[pid]
        await MySession.kill_incoming.get()
        print("_kill_incoming_ws() done")
        
    async def _incoming_ws(self, pid, websocket):
        async def removed():
                if (WaitRecv==True):
                  done,pending = await asyncio.wait([websocket.recv(),
                            self._kill_incoming_ws(pid)
                            ],
                            timeout=TIMEOUT_WS_CLIENT_MAX,
                            return_when=asyncio.FIRST_COMPLETED)
                else:
                  done,pending = await asyncio.wait([
                            self._kill_incoming_ws(pid)
                            ],
                            # timeout=TIMEOUT_WS_CLIENT_MAX,
                            return_when=asyncio.FIRST_COMPLETED)

                print("WaitKey("+str(MySession.MySession)+") done")
                if len(done)==0:
                  print("Timeout")
                  await websocket.close()
              #    break          # Timeout
                #else:
                #  print("Done:")
                #  for task in done:
                #    print(task)
                    #print(task.get_stack()) #[0].f_code.co_name)
                print("Pending:")
                KillCanceled=False
                for task in pending:
                  #print(task)
                  #print(task.get_stack())
                  #print(task.get_stack()[0].f_code)
                  print(task.get_stack()[0].f_code.co_name)
                  #if task.get_stack()[0].f_code.co_name == "_incoming_ws" :
                  if task.get_stack()[0].f_code.co_name == "_kill_incoming_ws" :
                    KillCanceled=True
                    print("'_kill_incoming_ws' ToBeCancelled ... forward done as msg")
                    task.cancel()
                    while len(done)>0:                  
                      TaskFinished=done.pop()
                      #print(type(TaskFinished))
                      print(TaskFinished)
                      msg=TaskFinished.result()
                      MySession.MsgFromUser(msg)
                  elif task.get_stack()[0].f_code.co_name == "recv" :
                    task.cancel()
                    print("'recv' Cancelled ... ")
                    
                if KillCanceled==False:
                  print("Kill was not cancelled => It was done => Not forwarded and switch WaitRecv("+str(WaitRecv)+")")
                  #if WaitRecv==True:
                  #  WaitRecv=False
                  #else:
                  #  WaitRecv=True
        
        MySession = self.UserSessions[pid]
        """Handle incoming messages from a Ws Client."""
        # websockets have a convenient __aiter__ interface, allowing  us to just iterate over the messages forever.
        # Under the hood, if there are no messages available from the WebSocket, this code will yield and until another message is received.

        # If the WebSocket is disconnected unexpectedly, the for loop will produce an exception.
        try:
            #async for msg in websocket:
            #  MySession.MsgFromUser(msg)
            WaitRecv=True
            while not websocket.closed:
                #print("WaitKey("+str(MySession.MySession)+")")
                msg = await websocket.recv()
                MySession.MsgFromUser(msg)


              
            print ("GatewayServer.py->_incoming_ws() : async for msg in websocket exited cleanly - client left and we need to close everything")  
            if not websocket.closed:
              await websocket.close()
              del self._ws_clients[pid]
            else:
              print("GatewayServer.py->_incoming_ws() : WebSocket client server side was not opened")
            print ("GatewayServer.py->await websocket close()")
            if not self._ws_server[pid].closed:
              await self._ws_server[pid].close()
              del self._ws_server[pid]
              print("GatewayServer.py->_incoming_ws() : WebSocket remote server side closed")
            else:
              print("GatewayServer.py->_incoming_ws() : WebSocket remote server side was not opened")

            # If we get this error, then user probably just logged off.
        except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError) :
            # Should never occur ???
            print("GatewayServer.py->_incoming_ws() : Exception closed for %s",pid)
            await websocket.close()
            del self._ws_clients[pid]
            pass
        except:
          err=sys.exc_info()
          #self.UserSessions[pid].MsgToUser("OSError:" + str(err[1])+"\n\r" ,False)
          print ("ERR:GatewayServer.py/_incoming_ws() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
          for item in err:
            print(item)
            #logging.error("%s connect to WS server [%s] got error (%s)", pid, uri,item)
        finally:
            print("GatewayServer.py->_incoming_ws() exiting : finally closed for %s",pid)
            logging.debug("_incoming_ws closed for %s", pid)

    async def _outgoing_ws(self, pid, websocket):
        """Handles outgoing messages, that is, messages sent to a Character that must be forwarded to a user.  """
        MySession = self.UserSessions[pid]

        while not websocket.closed:
            msg = await MySession.msgs.get()

            # TODO: try to get more messages and buffer writes?
            try:
              if type(msg) == bytes:        # Cette astuce est nécessaire afin de permettre à l'émulation WS de Zigazou de fonctionner si des codes non-unicode sont transmis par le serveur
                  msg = str(msg,'latin-1')
              await websocket.send(msg)
            except websockets.exceptions.ConnectionClosed:
                print("GatewayServer.py->_outgoing_ws() : closed exception for %s",pid)
                break

        print("GatewayServer.py->_outgoing_ws() : exiting - websocket is closed for %s",pid)
        logging.debug("GatewayServer.py->_outgoing_ws closed for %s", pid)

    async def _command_ws(self, pid, websocket):
        """Handles command messages, that is, command sent to a Character that must be forwarded to a user.  """
        MySession = self.UserSessions[pid]

        while not websocket.closed:
            msg = await MySession.command.get()

            # TODO: try to get more messages and buffer writes?
            try:
              if type(msg) == bytes:        # Cette astuce est nécessaire afin de permettre à l'émulation WS de Zigazou de fonctionner si des codes non-unicode sont transmis par le serveur
                  msg = str(msg,'latin-1')
              #await websocket.send(msg)
              print("##########COMMAND")
              print(msg)
              self._ws_server_bis_queue.put_nowait("UserGotCommand,,,"+str(pid)+","+msg)
              msg=msg.split(',',4)
              if (MySession.MySession==-1):
                MySession.MySession=msg[0]
                if type(MySession.MySession) is str:      # Attention, MySession.MySession est parfois (au premier coup sur redirection) de type STR ????
                  MySession.MySession=int(MySession.MySession)

                if msg[1]=="CONNECT":              
                  MySession.MyTarget=msg[2]
                  msg[2]=msg[2].split(':',1)
                  if (msg[2][0].upper()=="WS") or (msg[2][0].upper()=="WSS"):
                    MySession.MyPing=msg[3]
                    MySession.MySub=msg[4]
                    self._ws_server_bis_queue.put_nowait("UserRedirecting,,,"+str(pid)+","+str(MySession.MySession))
                    print("##########CONNECTING WS")
                    #
                    # From _incoming_ws
                    #
                    done,pending = await asyncio.wait([#self._incoming_ws(pid, websocket),
                            #self._outgoing_ws(pid, websocket),
                            self._ws_connect_to_server(MySession.MyTarget,pid,True,MySession.MyPing,MySession.MySub)
                            ],
                            timeout=TIMEOUT_WS_CLIENT_MAX,
                            return_when=asyncio.FIRST_COMPLETED)
                    if len(done) == 0:
                        print("Timeout _WS_CLIENT_MAX")
                    self._ws_server_bis_queue.put_nowait("UserRedirectEnded,,,"+str(pid)+","+str(MySession.MySession))
                    MySession.MySession=-1
                    print("##########CLOSED")
                                                                              
                  elif (msg[2][0].upper()=="TELNET") :
                    print("StartTN")
                  else:
                    print("Unknown protocol")
                else:
                  print("Unknown command")
              else:
                print("Already connected")
            except websockets.exceptions.ConnectionClosed:
                print("GatewayServer.py->_command_ws() : closed exception for %s",pid)
                break

        print("GatewayServer.py->_command_ws() : exiting - websocket is closed for %s",pid)
        logging.debug("GatewayServer.py->_command_ws closed for %s", pid)

    
    async def _ws_connect_to_server(self,uri,pid, remote, MyPing_interval="None",MySubprotocols="[]") :
        """ will try to connect to a target WS server. Once done, will forward received data from the server to the client (telnet or WS)
        """
        print ("GatewayServer.py->_ws_connect_to_server("+str(remote)+") trying connection to " + uri + " for PID #" + str(pid)+" with ping_interval="+str(MyPing_interval)+" and subprotocols="+str(MySubprotocols))
        pending=None
        try:
          #async with websockets.connect(uri, ping_interval=None) as websocket:
          #async with websockets.connect(uri, ping_interval=10, subprotocols=["binary","tty"]) as websocket:
          if type(MyPing_interval) is str:
            if MyPing_interval.upper()=="NONE":
              MyPing_interval=None
            else:
              MyPing_interval=int(MyPing_interval)
          if type(MySubprotocols) is str:
            MySubprotocols=MySubprotocols[1:-1]
            MySubprotocols=MySubprotocols.split(",")
          temp=[]
          for sub in MySubprotocols:
            temp.append(sub[1:-1])
          MySubprotocols=temp
          #print(type(MyPing_interval))
          #print(MyPing_interval)
          #print(type(MySubprotocols))
          #print(MySubprotocols)
          
          async with websockets.connect(uri, ping_interval=MyPing_interval, subprotocols=MySubprotocols) as websocket:
            MySession=self.UserSessions[pid]
            if remote==False:
              self._ws_server[pid] = websocket
              MySession.MsgToUser("Connected to '" + uri + "'\n\r",False)            
              print ("GatewayServer.py->_ws_connect_to_server() connected to " + uri)
              logging.info("%s connected to WS server [%s]", pid, uri)
              done,pending = await asyncio.wait([self._incoming_ws_server(pid, websocket,False),
                              self._outgoing_ws_server(pid, websocket,False), #,
                              self._command_ws(pid,websocket)
                              ],
                              timeout=TIMEOUT_WS_SERVER_MAX ,
                              return_when=asyncio.FIRST_COMPLETED)
              print("asyncio.wait NoRemote completed")
            else:
              self._ws_server_bis_queue.put_nowait("UserRedirected,,,"+str(pid)+","+str(MySession.MySession))
              print("##########CONNECTED")
              print ("GatewayServer.py->_ws_connect_to_server() directed to " + uri)
              MySession.kill_incoming.put_nowait("")
              MySession.MsgToUser("\x1f@AConnected\x18\x0a",False)
              done,pending = await asyncio.wait([self._incoming_ws_server(pid, websocket,True),
                              self._outgoing_ws_server(pid, websocket,True)
                              ],
                              timeout=TIMEOUT_WS_SERVER_MAX ,
                              return_when=asyncio.FIRST_COMPLETED)
              print("asyncio.wait Remote completed")
            if len(done)==0:
              logging.info("%s connect to WS server [%s] Inactivity Timeout (%s) reached", pid, uri, _WS_SERVER_MAX)
              print("Timeout _WS_SERVER_MAX")
            else:
              if remote==True:
                print("_ws_connect_to_server() ending while redirected with no exception")
                #print("pending:")
                #print(pending)
                #print("done:")
                #print(done)
                for task in pending:
                  print("_ws_connect_to_server() canceled pending task")
                  #print(task)
                  task.cancel()
              else:
                print("_ws_connect_to_server() ending while not redirected with no exception")
        except websockets.exceptions.ConnectionClosed:
          print("_ws_connect_to_server() exception ConnectionClosed")
          print("pending:")
          if pending!=None:
            print(pending)
        except websockets.exceptions.ConnectionClosedOK:
          print("_ws_connect_to_server() exception ConnectionClosedOK")
          print("pending:")
          if pending!=None:
            print(pending)
        except websockets.exceptions.ConnectionClosedError:
          print("_ws_connect_to_server() exception ConnectionClosedError")
          print("pending:")
          if pending!=None:
            print(pending)
        except asyncio.TimeoutError:
          print("Timeout _ws_connect_to_server() asyncio.TimeoutError")
          logging.error("%s connect to WS server [%s] AsyncIO.Timeout", pid, uri)
          if pending!=None:
            print(pending)
        except websockets.exceptions.InvalidURI:
          logging.error("%s connect to WS server [%s] failed (invalid URI)", pid, uri)
          self.UserSessions[pid].MsgToUser("InvalidURI '" + uri + "'\n\r",False)
          if pending!=None:
            print(pending)
        except websockets.exceptions.InvalidMessage:
          logging.error("%s connect to WS server [%s] failed (invalid message)", pid, uri)
          self.UserSessions[pid].MsgToUser("Invalid HTTP response from server\n\r",False)
          if pending!=None:
            print(pending)
        except OSError:
          err=sys.exc_info()
          self.UserSessions[pid].MsgToUser("OSError:" + str(err[1])+"\n\r" ,False)
          print ("ERR:GatewayServer.py/_ws_connect_to_server("+str(remote)+") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
          for item in err:
            print(item)
            logging.error("%s connect to WS server [%s] got error (%s)", pid, uri,item)
        finally:
          print("GatewayServer.py->_ws_connect_to_server("+str(remote)+") " + str(pid) + " ended")

    async def _incoming_ws_server(self,pid, websocket,remote):
          async def CheckEnq(self):
              print("Got EnqRom from _ws_server")
              if MySession.ReplyedToEnqRom==False:
                print("First EnqRom for this session")  
                if self._ws_server_bis_connected==True:
                  print("_ws_server_bis is connected -> Reply sent")                    
                  MySession.ReplyedToEnqRom=True
                  await websocket.send(b'\x01\x7f\x7f\x7f\x04')
                  await websocket.send("PID="+str(pid)+",IP="+MySession.MyIP+",PORT="+MySession.MyPort+",Access="+MySession.MyAccess+chr(10))
                else:
                  print("_ws_server_bis is not yet connected")                    
              else:
                 print("Already replied to EnqRom")
                  
          print("GatewayServer.py->_incoming_ws_server("+str(remote)+") " + str(pid) + " started")
          MySession=self.UserSessions[pid]
          recv_cnt=0
          while not websocket.closed:
            try:
              recv_cnt += 1
              DataFromWsServer = await websocket.recv()
              #
              # Detect ENQ/ROM from _ws_server (if gateway is already connected to _ws_server)
              #
              #print("---")
              #print(isinstance(DataFromWsServer,type(bytes)))
              #print(type(DataFromWsServer))
              if type(DataFromWsServer)== str:
                #print("Got str (" +str(len(DataFromWsServer))+")")
                if "\x1b9{" in DataFromWsServer:
                  await CheckEnq(self)
              else:
                #print("Got bytes (" +str(len(DataFromWsServer))+")")
                #print(type(DataFromWsServer))
                if "\x1b9{".encode() in DataFromWsServer:
                  await CheckEnq(self)

              #print("GatewayServer.py->_incoming_ws_server() WaitReceiveCount: "+str(recv_cnt) + " len=" + str(len(DataFromWsServer)) + " for PID #" + str(pid))        
              MySession.MsgToUser(DataFromWsServer,False)
              logging.debug("%s received [%s] from WS server (%s)", pid, DataFromWsServer,recv_cnt)
              #print ("forwarded " + str(len(DataFromWsServer)) + " bytes to client")
            except websockets.exceptions.ConnectionClosed:
              MySession.MsgToUser("\n\rGatewayServer.py->_incoming_ws_server("+str(remote)+") :\n\rWS server connection closed\n\r",False)
              break
            #except concurrent.futures._base.CancelledError:
            except asyncio.CancelledError:
              print("ERR:GatewayServer.py->_incoming_ws_server("+str(remote)+") Cancelled")                            
            except:
              print("ERR:GatewayServer.py->_incoming_ws_server("+str(remote)+")")
              err=sys.exc_info()
              for item in err:
                print(item)
          print("GatewayServer.py->_incoming_ws_server("+str(remote)+") " + str(pid) + " ended")

    async def _outgoing_ws_server(self,pid, websocket,remote):
          print("GatewayServer.py->_outgoing_ws_server("+str(remote)+") " + str(pid) + " started")
          MySession=self.UserSessions[pid]
          sent_cnt=0
          MySession.GotSep=False
          GotLib=False                # Attention, doit être locale (sinon, on abandonne aussi si remote=False !)
          while (not websocket.closed) and (GotLib==False):
            try:
              #print("GatewayServer.py->_outgoing_ws_server() WaitKeysForwardCount: "+str(sent_cnt) + " for PID #" + str(pid))
              if ((remote == False) and (MySession.MySession==-1) or (remote==True)):
                sent_cnt += 1
                DataToWsServer = await MySession.keysforward.get()
                #ms=MySession.MySession  # Attention, MySession.MySession est parfois (au premier coup sur redirection) de type STR ????  
                #if type(ms) is str:
                #  ms=int(ms)
                #print("_outgoing_ws_server() keysforward.get("+str(remote)+")"+str(ms))
                #print(DataToWsServer)
                #print(type(ms))
                if (remote==True) or (MySession.MySession>=0):            # au premier coup sur redirection, on est toujours remote=false
                    for Char in DataToWsServer:
                      if MySession.GotSep==True:
                        MySession.GotSep=False
                        if (Char=="I") or (Char=="\x59"):
                          print("GatewayServer.py->_outgoing_ws_server("+str(remote)+") " + str(pid) + " request to end")
                          self._ws_server_bis_queue.put_nowait("UserRequestedClose,,,"+str(pid)+","+str(MySession.MySession))
                          GotLib=True                          
                      if Char=="\x13":
                        MySession.GotSep=True
                try:
                  if (remote==False) and (MySession.MySession>=0):    # On commence une redirection
                    print("SendToOtherWS")
                    #temp=[]
                    #temp.append(DataToWsServer)
                    #while not MySession.keysforward.empty():
                    #  temp.append(MySession.keysforward.get())
                    #  print(len(temp))
                    #while len(temp)>0:
                    #  print(len(temp))
                    #  MySession.MsgFromUser(temp.pop())
                    MySession.MsgFromUser(DataToWsServer)
                  else:
                    await websocket.send(DataToWsServer)
                  #print ("forwarded " + str(len(DataToWsServer)) + " bytes to server")
                  logging.debug("%s send [%s] to WS server (%s)", pid, DataToWsServer,sent_cnt)
                  #for char in DataToWsServer:
                  #  print("'0x{:02x}'".format(ord(char)))
                except websockets.exceptions.ConnectionClosed:
                  break
              else:
                await asyncio.sleep(0.5)
              # TODO: try to get more messages and buffer writes?
            except websockets.exceptions.ConnectionClosed:
              MySession.MsgToUser("\n\rGatewayServer.py->_ws_connect_to_server() : WS server connection closed\n\r",False)
              break
            #except concurrent.futures._base.CancelledError:
            except asyncio.CancelledError:
              print("ERR:GatewayServer.py->_outgoing_ws_server("+str(remote)+") Cancelled")                            
            except:
              print("ERR:GatewayServer.py->_outgoing_ws_server("+str(remote)+")")
              err=sys.exc_info()
              for item in err:
                print(item)
          print("GatewayServer.py->_outgoing_ws_server("+str(remote)+") " + str(pid) + " ended")

    # handlers for each event
    # override these for custom behavior
    
    def on_user_join(self, pid):
        print("GatewayServer.py->on_user_join()")
        """This method is executed whenever a new user [pid] joins the
        server. By default, the user is assigned a new Character,
        which is then spawned in the game world.

        You can override this method to trigger custom behavior every
        time a user joins.
        """
        logging.info("%s joined.", pid)

        MySession = Session()
        self.UserSessions[pid] = MySession
        MySession.spawn_nogame() 
        try:
           pass
        except:
          print ("ERR:GatewayServer.py/on_user_join() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
          err=sys.exc_info()
          for item in err:
            print(item)
        finally:
          #print("Pending tasks at exit:")
          #for task in asyncio.all_tasks(asyncio.get_event_loop()):
          #  print(task)
          pass
        
    def on_user_msg(self, pid: int, msg: str):
        """This method is executed whenever a string of data [msg]
        is received from the TcpClient / WebSocket associated with
        [pid]. This method simply passes the msg onto the Character
        controlled by the user.

        You can override this method to trigger custom behavior every
        time a user sends a message to the server.
        """
        logging.info("%s says: [%s]", pid, msg)
        try:
            # Simply look up the character that belongs to this user,
            # and send the msg as a command.
            #print("GatewayServer.py->on_user_msg->UserSessions[pid].command()")
            #self.UserSessions[pid].command(msg)
            print("GatewayServer.py->on_user_msg->UserSessions[pid].keysforward")
            self.UserSessions[pid].keysforward.put_nowait(msg)

        # Now that we're triggering game code, a lot of errors could
        # occur. We're going to just log those and keep moving, so
        # that the server doesn't completely die.
        except Exception:
            logging.error(traceback.format_exc())

    def on_user_quit(self, pid):
        """This method is executed whenever a user [pid] disconnects
        from the server server. By default, the user's Character is
        destroyed and the other UserSessions are notified.

        You can override this method to trigger custom behavior every
        time a user quits.
        """
        logging.info("%s quit.", pid)

        try:
            character = self.UserSessions[pid]
        except KeyError:
            # user did not exist
            return

        self._ws_server_bis_queue.put_nowait("UserGone,,,"+str(pid))

        try:
            websocket = self._ws_clients[pid]
            if not websocket.closed:
              websocket.close()
              print("on_user_quit() : WebSocket client side closed")
            else:
              print("on_user_quit() : WebSocket client side already closed")
            del self._ws_clients[pid]
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN mudserver.py->on_user_quit() no WS from client - client was already disconnected or came from telnet ?") 

        try:
            websocket = self._ws_server[pid]
            if not websocket.closed:
              websocket.close()
              print("WebSocket remote server side closed")
            else:
              print("WebSocket remote server side already closed")
            del self._ws_server[pid]
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN mudserver.py->on_user_quit() no WS to remote server - server was already disconnected ?")
             

    # methods used in mudscript
    def message_all(self, message):
        """Sends the text in the 'message' parameter to every user that
        is connected to the server.
        """
        # We copy the _clients into a list to avoid dictionary changing
        # size during iteration.
        for (_pid, ThisSession) in self.UserSessions:
            ThisSession.MsgToUser(message,False)

    def kick(self, character, reason: str=""):
        """Find the client associated with [character] and disconnect
        them from the game.
        Raises KeyError if [character] cannot be found.
        """
        # get the pid from the user biject (raises KeyError if character not found)
        pid = self.UserSessions[character]

        try:
            tcp_stream_writer = self._tcp_clients[pid]
            kick_coro = tcp_stream_writer.close()
        # pid is not in tcp_clients, maybe it's a websocket?
        except KeyError:
            try:
                websocket = self._ws_clients[pid]
                kick_coro = websocket.close()
            except KeyError:
                logging.error("Could not kick pid '%s' "
                              "(are they already disconnected?)", pid)
                return

        character.message("You are being kicked from the server.")
        if reason:
            character.message(f"(Reason: {reason})")
        try:
            # turn the coroutine into a task to schedule it
            asyncio.create_task(kick_coro)
        # loop is not running right now
        except RuntimeError:
            if self._running:
                logging.error("Could not kick pid '%s' (Maybe MudServer.run() "
                              "was called but never awaited?)", pid)
            else:
                logging.error("Could not kick pid '%s' "
                              "(server is not running)", pid)
            return
        if reason:
            logging.info("Kicked pid '%s' associated with [%s] "
                         "(Reason: %s)", pid, character, reason)
        else:
            logging.info("Kicked pid '%s' associated with [%s]",
                         pid, character)

    async def _incoming_ws_bis(self,websocket) :
          recv_cnt=0
          while True:# not websocket.closed:
            try:
              recv_cnt += 1
              DataFromWsServer = await websocket.recv()
              print ("GatewayServer.py->_incoming_ws_bis() WaitReceiveCount: "+str(recv_cnt) + " len=" + str(len(DataFromWsServer))  + " bytes of command from server")
              #print(type(DataFromWsServer) )
              if type(DataFromWsServer) is bytes:
                DataFromWsServer=DataFromWsServer.decode('latin1','strict')
                #print("Bin2Ascii")
              DataFromWsServer=DataFromWsServer.split(",",1)
              if len(DataFromWsServer)>0:
                if len(DataFromWsServer[0])>0:
                  DataFromWsServer[0]=DataFromWsServer[0].split("=")
                  if (DataFromWsServer[0][0]=="PID") :
                    DataFromWsServer[0][1]=int(DataFromWsServer[0][1])
                    #and (self.UserSessions[DataFromWsServer[0][1]].closed()==False):
                    
                    #print (DataFromWsServer[0][1])
                    #print (DataFromWsServer[1].split(","))
                    #print("------------------")
                    #print(self)
                    #print(self.UserSessions[DataFromWsServer[0][1]])
                    #print("------------------")
                    DestPID=self.UserSessions[DataFromWsServer[0][1]]
                    DestPID.command.put_nowait(DataFromWsServer[1]) 
                  
                  #MySession.MsgToUser(DataFromWsServer,False)
                    logging.debug("forwarded command [%s] for PID %s from WS server (%s)", DataFromWsServer[1],DataFromWsServer[0][1],recv_cnt)
              else:
                logging.debug("ignored [%s] command [%s] for PID %s from WS server (%s)", DataFromWsServer[0][1], DataFromWsServer[1],DataFromWsServer[0][1],recv_cnt)
            except websockets.exceptions.ConnectionClosed:
              #MySession.MsgToUser("\n\rGatewayServer.py->_incoming_ws_bis() :\n\rWS server connection closed\n\r",False)
              print("\n\rGatewayServer.py->_incoming_ws_bis() :\n\rWS server connection closed\n\r")
              break
            except:
              err=sys.exc_info()
              for item in err:
                print(item)
              raise
          print("_incoming_ws_bis() ended")

    async def _outgoing_ws_bis(self,websocket) :
          sent_cnt=0
          while True: #not websocket.closed:
            try:
              sent_cnt += 1
              #print("GatewayServer.py->_outgoing_ws_server() WaitKeysForwardCount: "+str(sent_cnt) + " for PID #" + str(pid))        
              DataToWsServer = await self._ws_server_bis_queue.get()
              try:
                  await websocket.send(DataToWsServer)
                  print ("GatewayServer.py->_outgoing_ws_bis() Sent " + str(len(DataToWsServer)) + " bytes of command to server")
                  print (DataToWsServer)
                  logging.debug("send [%s] of command to WS server (%s)", DataToWsServer,sent_cnt)
                  #for char in DataToWsServer:
                  #  print("'0x{:02x}'".format(ord(char)))
              except websockets.exceptions.ConnectionClosed:
                  break
            except websockets.exceptions.ConnectionClosed:
              #MySession.MsgToUser("\n\rGatewayServer.py->_ws_connect_to_server() : WS server connection closed\n\r",False)
              break
          print("_outgoing_ws_bis() ended")

    async def _ws_connect_to_server_bis(self,uri) :
        print ("GatewayServer.py->_ws_connect_to_server_bis() trying connection to " + uri + ".")
        try:
          self._ws_server_bis_connected=False
          while self._running == True:
           
            logging.error("Gateway --Trying---- to connect to WS [%s]", uri)
            done,pending = await asyncio.wait([
                              #self._incoming_ws_bis(pid, websocket),
                              #self._outgoing_ws_bis(pid, websocket),
                              #self._ws_connect_to_server_ter(self.targeturi,pid)
                              websockets.connect(uri, ping_interval=10, subprotocols=["binary","tty"])
                              ],
                              timeout=TIMEOUT_GTW,
                              return_when=asyncio.FIRST_COMPLETED)
            while len(done):
              was_done=done.pop()
              if was_done.exception():
                #was_done.print_stack()
                print('Will retry connection in '+str(TIMEOUT_GTW)+'"')
                await asyncio.sleep(TIMEOUT_GTW)
              else:
                  websocket=was_done.result()
                  print("GatewayLink openned")
                  self._ws_server_bis_connected=True
                  done,pending = await asyncio.wait([
                              self._incoming_ws_bis(websocket),
                              self._outgoing_ws_bis(websocket)
                              ],
                              #timeout=10,
                              return_when=asyncio.FIRST_COMPLETED)
                  print("GatewayLink closed")
                  self._ws_server_bis_connected=False
                  print("Done:")
                  print(done)
                  print("Pending:")
                  print(pending)
                  print("_***_ws_bis() completed")
                  await websocket.close()
                  done=""              
        finally:
          print("GatewayServer.py->_ws_connect_to_server_bis() " + str(pid) + " ended")
