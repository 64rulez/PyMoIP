"""
Basic MUD server module for creating text-based Multi-User Dungeon
(MUD) games.

This module provides one class, MudServer, which represents
the game instance, tracks players, and handles interactions with
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
from swampymud.util.biject import Biject
# for asynchronous stuff
import asyncio
# required for websockets to work
import websockets
import sys
import time

logger = logging.getLogger('websockets')
logger.setLevel(logging.DEBUG) # DEBUG / ERROR / INFO
logger.addHandler(logging.StreamHandler())

# Timeouts https://medium.com/@pgjones/an-asyncio-socket-tutorial-5e6f3308b8b0
TIMEOUT_TN_CLIENT = 600      # La session telnet est fermée après 10 minutes sans caractère reçu 
TIMEOUT_TN_CLIENT_MAX = 3600 # La session telnet dure maximum 1 heure 
TIMEOUT_WS_CLIENT = 600      # La session WS est fermée après 10 minutes sans caractère reçu
TIMEOUT_WS_CLIENT_MAX = 3600 # La session WS dure maximum 1 heure
TIMEOUT_WS_SERVER = 600      # La session WS serveur est fermée après 10 minutes sans caractère reçu
TIMEOUT_WS_SERVER_MAX = 7200 # La session WS serveur dure maximum 2 heures

class MudServer:
    '''A high-level game server that coordinates between a TelnetServer
    instance and the in-game world.

    Generally speaking, you should initialize this object, not a telnet
    server.
    '''

    def __init__(self, world, ws_port=None, tcp_port=None):
        logging.debug("Server %r created", self)
        # game-related data
        self.GameDisabled = True
        self.DebugIAC = False
        self.world = world
        self.default_class = None
        self.default_location = None
        # dict mapping pid [int] to in-game Characters
        # use a biject here so we can get Characters back if needed
        self.players = Biject()
        
        self.targeturi = "ws://localhost:8765"
        #self.targeturi = "ws://mntl.joher.com:2018/?echo" # ping_interval=None
        #self.targeturi = "ws://3611.re/ws"
        #self.targeturi = "wss://3615co.de/ws"
        #self.targeturi = "ws://34.223.255.81:9999/?echo"
        #self.targeturi = "ws://minitel.3614teaser.fr:8080/ws"  # ping_interval=10, subprotocols=["binary","tty"]
        self._ws_server = {}        # websocket[pid] vers serveur

        self.tcp_port = tcp_port
        self.tcp_server = None
        self._tcp_clients = {}
        self.ws_port = ws_port
        self.ws_server = None
        self._ws_clients = {}
        # by tracking clients, we can write a 'kick' function and
        # have a cleaner shutdown (in the case of the tcp server)

        self.next_id = 0
        self._running = False
        # at least one port must be provided
        if tcp_port is None and ws_port is None:
            raise ValueError("Cannot create MudServer without at least one "
                             "TCP or WS port.")

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
        
        print("_register_tcp() " + str(pid) + " started from " + writer.get_extra_info('peername')[0])
        print( writer.get_extra_info('peername'))

        # Now, store the tcp client in a dictionary, so we can track it
        # down later if necessary.
        self._tcp_clients[pid] = writer

        # This method will create a new Character and assign it to the
        # player.
        # This method can be overriden for custom behavior.
        self.on_player_join(pid)

        # Now we create two coroutines, one for handling incoming messages,
        # and one for handling outgoing messages.

        # If a player disconnects, the _incoming_tcp coroutine will wake up,
        # and run to completion. However, the _outgoing_tcp coroutine
        # will be stuck waiting until the player's Character receives a
        # message.
        # We want to move on immediately when the player disconnects, so
        # we return_when=asyncio.FIRST_COMPLETED here.

        try:
          await asyncio.wait([self._incoming_tcp(pid, reader),
                            self._outgoing_tcp(pid, writer),
                            self._ws_connect_to_server(self.targeturi,pid)
                            ],
                           timeout=TIMEOUT_TN_CLIENT_MAX,
                           return_when=asyncio.FIRST_COMPLETED)

        except asyncio.TimeoutError:
            print("Timeout _TN_CLIENT_MAX")


        # If the interpreter reaches this line, that means an EOF has
        # been detected and this player has disconnected.
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
            print("WARN mudserver.py->_register_tcp() no WS with server - server was already disconnected ?") 


        # Finally, call server.on_player_quit().
        # By default, this will delete the player's Character and send a
        # message to the other players, letting them know that this
        # player left.
        # This method can be overriden for custom behavior.
        self.on_player_quit(pid)

    async def _incoming_tcp(self, pid, reader):
        """Handle incoming messages from a Tcp Client."""
        
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
        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DO)+chr(CHAR_ECHO),self.DebugIAC)
        self.players[pid].message("Welcome to PyMoIP [telnet]/WS gateway\n\r",False)
        print("_incomming_tcp() " + str(pid) + " started")

        #self.players[pid].keysforward.put_nowait(msg)

        # When the user disconnects, asyncio will call it "EOF" (end of
        # file). Until then, we simply try to read a line from the
        # user.
        while not reader.at_eof():
            # reader.readline() is an asynchronous method
            # This means that it won't actually execute on its own
            # unless we 'await' it.
            # Under the hood, using this 'await' actually switches to
            # execute some other code until this player sends us
            # a message.
            #msg = await reader.readline()
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
                    print("_incoming_tcp() Got OpCode")
                  IACStatus = 1 # Wait for option
                  IACCommand= ord(msg)
                  msg=None
                elif ord(msg) == CHAR_SB:
                  if self.DebugIAC:
                    print("_incoming_tcp() Got SubOpCode")
                  IACStatus = 2   # Wait for SubOption
                  msg=None
                else :          # Illegal OpCode
                  if self.DebugIAC:
                    print("_incoming_tcp() Illegal OpCode ->255")
                  msg == CHAR_IAC  # Transmet 255
                  IACState = False
              elif IACStatus == 1:  # Received command              
                if ord(msg) == CHAR_ECHO or ord(msg) == CHAR_GO :
                  if ord(msg) == CHAR_ECHO:
                    if self.DebugIAC:
                      print("_incoming_tcp()  IAC Echo")
                    if IACCommand == CHAR_WONT or IACCommand == CHAR_DONT:
                      IACDisabled.append(ord(msg))
                      if IACCommand == CHAR_DONT :
                        if self.DebugIAC:
                          print("<Reply WONT>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                      else:
                        if self.DebugIAC:
                          print("<Reply DONT>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_DO:
                        if self.DebugIAC:
                          print("<Reply WILL>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_WILL)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_WILL:
                        if self.DebugIAC:
                          print("<Reply DO>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DO)+chr(ord(msg)),self.DebugIAC)
                     
                  elif ord(msg) == CHAR_GO:
                    if self.DebugIAC:
                      print("_incoming_tcp() IAC Go")
                    if IACCommand == CHAR_WONT or IACCommand == CHAR_DONT:
                      IACDisabled.append(ord(msg))
                      if IACCommand == CHAR_DONT :
                        if self.DebugIAC:
                          print("<Reply WONT>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                      else:
                        if self.DebugIAC:
                          print("<Reply DONT>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_DO:
                        if self.DebugIAC:
                          print("<Reply WILL>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_WILL)+chr(ord(msg)),self.DebugIAC)
                    elif IACCommand == CHAR_WILL:
                        if self.DebugIAC:
                          print("<Reply DO>")
                        (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DO)+chr(ord(msg)),self.DebugIAC)
                else:              # Unknown command
                  if self.DebugIAC:
                    print ("_incoming_tcp() Unknown IAC command")
                  IACDisabled.append(ord(msg))
                  if IACCommand == CHAR_DO or IACCommand == CHAR_DONT:
                    if self.DebugIAC:
                      print("<Reply WONT>")
                    (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_WONT)+chr(ord(msg)),self.DebugIAC)
                  else:
                    if self.DebugIAC:
                      print("<Reply DONT>")
                    (self.players[pid]).message(chr(CHAR_IAC)+chr(CHAR_DONT)+chr(ord(msg)),self.DebugIAC)
                msg = None
                IACState = False
              elif IACStatus == 2:  # Received Suboption
                if self.DebugIAC:
                  print("_incoming_tcp() IAC Suboption start")
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
                  print("_incoming_tcp() IAC Suboption end")
                IACOption+=msg      # Buffer full or SE
                IACState = False
                msg = None
                

            # The player just sent us a message!
            # Remove any whitespace and convert from bytes to str
            if msg:
              #msg = msg.strip().decode(encoding="latin1")
              msg=chr(ord(msg))
            if msg:
              if self.DebugIAC:
                print("_incoming_tcp() Got '0x{:02x}' after IAC".format(ord(msg)))
                
              if self.GameDisabled == True:              # Faire suivre immédiatement, caractère par caractère si pas en mode jeu 
                if CountChar<144 and ((time.time() - start_time) <1):
                  TmpBuf+=msg
                elif CountChar==144 and ((time.time() - start_time) <1):
                  TmpBuf+=msg
                  print(TmpBuf)              
                  CountChar=150
                else:              
                  self.players[pid].keysforward.put_nowait(msg)
              else:                                      # Bufferiser jusqu'à réception de RC si en mode jeu
                if msg==chr(13):
                  # Pass the message to server.on_player_msg().
                  # The method there will send the message to the
                  # Character that the player controls.
                  # This function can be overriden for custom behavior.
                  self.on_player_msg(pid, LineBuffer.strip())
                  LineBuffer=""
                else:
                  LineBuffer += msg

        print("_incoming_tcp closed for %s", pid)
        logging.debug("_incoming_tcp closed for %s", pid)

    async def _outgoing_tcp(self, pid, writer):
        """Handles outgoing messages, that is, messages sent to a Character
        that must be forwarded to a Player.
        """
        character = self.players[pid]
        print("_outgoing_tcp() " + str(pid) + " started")

        # This coroutine just loops forever, and will eventually be
        # broken once the client disconnects.
        while True:
            # Try to get a message from the Character's queue.
            # This will block until the character receives a message.
            msg = await character.msgs.get()

            # TODO: try to get more messages to buffer writes?

            # Add a newline character and convert the message into bytes
            if self.GameDisabled == True:
              #print(type(msg))
              if type(msg) != bytes:                # Si on a reçu des 'bytes', on ne ré-encode pas en unicode sur l'accès telnet (permet à Timtel de recevoir des codes 8 bits tout en laissant PyMinitel fonctionner en WS)
                msg = (msg).encode('latin-1')
              #else:
              #  for b in msg:
              #    print(str(b))
              #pass
            else:
              msg = (msg + "\n\r").encode('latin-1')
            writer.write(msg)

            # Once we've written to a StreamWriter, we have to call
            # writer.drain(), which blocks.
            try:
                await writer.drain()
            # If the player disconnected, we will get an error.
            # We will break and finish the coroutine.
            except ConnectionResetError:
                break

        print("_outgoing_tcp closed for %s", pid)
        logging.debug("_outgoing_tcp closed for %s", pid)

    # Callback methods for new WebSocket connections.
    # This method is executed whenever a new WebSocket connects to the
    # WebSocketServer.
    async def _register_ws(self, websocket, path):
        # we don't currently do anything with the path, so just log it
        logging.debug("WebSocket %s connected at path %s", websocket, path)

        # First, grab a new unique identifier.
        pid = self.next_id
        self.next_id += 1

        print("_register_ws() " + str(pid) + " started from " + websocket.remote_address[0])

        # Now, store the websocket in a dictionary, so we can track it
        # down later if necessary.
        self._ws_clients[pid] = websocket

        # Call the server's custom handler. (By default, this will
        # create a new Character and assign it to the player.)
        self.on_player_join(pid)
        print("PlayerJoined!")
        

        self.players[pid].message("Welcome to PyMoIP telnet/[WS] gateway\n\r",False)


        # WebSockets have a slightly different API than the tcp streams
        # rather than a reading and writing stream, which just have
        # one socket.
        # As with _register_tcp, we want to quit immediately the player
        # disconnects, so we use return_when=asyncio.FIRST_COMPLETED
        # If this code is reached, then the WebSocket has disconnected.
        # This should already be closed, but just in case.

        done,pending = await asyncio.wait([self._incoming_ws(pid, websocket),
                            self._outgoing_ws(pid, websocket),
                            self._ws_connect_to_server(self.targeturi,pid)
                            ],
                            timeout=TIMEOUT_WS_CLIENT_MAX,
                            return_when=asyncio.FIRST_COMPLETED)
        if len(done) == 0:
            print("Timeout _WS_CLIENT_MAX")

        #await asyncio.wait (websocket.close())
        if not websocket.closed:
              await websocket.close()
              del self._ws_clients[pid]
              print("_register_ws() : websocket.close()")
        else:
              print("_register_ws() : websocket.close() already closed")

        try:
          websocket = self._ws_server[pid]
          if not websocket.closed:
            print ("Closing _ws_server from _register_ws")
            await websocket.close()
            print("Close() done")
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN mudserver.py->_register_ws() no WS with server - server was already disconnected ?") 

        # Call the server's event handler. (By default, this will simply
        # notify the other players.)
        self.on_player_quit(pid)

        # Delete the pid / websocket from the clients.
        #del self._ws_clients[pid]
        # (We still keep track of pid in self._players... just in case.)


    async def _incoming_ws(self, pid, websocket):
        """Handle incoming messages from a Ws Client."""
        # websockets have a convenient __aiter__ interface, allowing
        # us to just iterate over the messages forever.
        # Under the hood, if there are no messages available from the
        # WebSocket, this code will yield and until another message is
        # received.

        # If the WebSocket is disconnected unexpectedly, the for loop
        # will produce an exception.
        try:
            #print("_incoming_ws():waiting msg")
            async for msg in websocket:
              if self.GameDisabled == True:
                  #print("_outgoing_ws():queued msg")
                  #print(msg)
                  self.players[pid].keysforward.put_nowait(msg)
              else:
                # Trim whitespace
                msg = msg.strip()
                # Make sure the message isn't an empty string
                if msg:
                    # Pass the message onto the server's handler.
                    self.on_player_msg(pid, msg)
            print ("_incoming_ws() : async for msg in websocket exited cleanly - client left and we need to close everything")  
            if not websocket.closed:
              await websocket.close()
              del self._ws_clients[pid]
            else:
              print("_incoming_ws() : WebSocket client server side was not opened")
            print ("await websocket close()")
            if not self._ws_server[pid].closed:
              await self._ws_server[pid].close()
              del self._ws_server[pid]
              print("_incoming_ws() : WebSocket remote server side closed")
            else:
              print("_incoming_ws() : WebSocket remote server side was not opened")

            # If we get this error, then player probably just logged off.
        except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedError) :
            # Should never occur ???
            print("_incoming_ws() : Exception closed for %s",pid)
            await websocket.close()
            del self._ws_clients[pid]
            pass
        finally:
            print("_incoming_ws() exiting : finally closed for %s",pid)
            logging.debug("_incoming_ws closed for %s", pid)

    async def _outgoing_ws(self, pid, websocket):
        """Handles outgoing messages, that is, messages sent to a Character
        that must be forwarded to a Player.
        """
        character = self.players[pid]

        while not websocket.closed:
            #print("_outgoing_ws():waiting msg")
            msg = await character.msgs.get()

            # TODO: try to get more messages and buffer writes?
            try:
              if self.GameDisabled == True:
                pass
                #print (type(msg))
                if type(msg) == bytes:        # Cette astuce est nécessaire afin de permettre à l'émulation WS de Zigazou de fonctionner si des codes non-unicode sont transmis par le serveur
                  msg = str(msg,'latin-1')
              else:
                msg = (msg + "\n\r").encode('latin-1')
              #print("_outgoing_ws():sending msg")
              await websocket.send(msg)
            except websockets.exceptions.ConnectionClosed:
                print("_outgoing_ws() : closed exception for %s",pid)
                break

        print("_outgoing_ws() : exiting - websocket is closed for %s",pid)
        logging.debug("_outgoing_ws closed for %s", pid)
    
    async def _ws_connect_to_server(self,uri,pid) :
        """ will try to connect to a target WS server. Once done, will forward received data from the server to the client (telnet or WS)
        """
        print ("mudserver.py->_ws_connect_to_server() trying connection to " + uri + " for PID #" + str(pid))
        try:
          #async with websockets.connect(uri, ping_interval=None) as websocket:
          async with websockets.connect(uri, ping_interval=10, subprotocols=["binary","tty"]) as websocket:
            self._ws_server[pid] = websocket
            self.players[pid].message("Connected to '" + uri + "'\n\r",False)
            print ("mudserver.py->_ws_connect_to_server() connected to " + uri)
            done,pending = await asyncio.wait([self._incoming_ws_server(pid, websocket),
                              self._outgoing_ws_server(pid, websocket) #,
                              #self._pong_ws_server(pid, websocket),
                              #self._ping_ws_server(pid, websocket)
                              ],
                              timeout=TIMEOUT_WS_SERVER_MAX ,
                              return_when=asyncio.FIRST_COMPLETED)
            if len(done)==0:
              print("Timeout _WS_SERVER_MAX")
        except asyncio.TimeoutError:
            print("Timeout _WS_SERVER asyncio.TimeoutError")

        except websockets.exceptions.InvalidURI:
          self.players[pid].message("InvalidURI '" + uri + "'\n\r",False)
        except OSError:
          err=sys.exc_info()
          self.players[pid].message("OSError:" + str(err[1])+"\n\r" ,False)
          print ("ERR:mudserver.py/_ws_connect_to_server() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
          for item in err:
            print(item)
        finally:
          print("_ws_connect_to_server() " + str(pid) + " ended")

    async def _ping_ws_server(self, pid, websocket):
          print("_ping_ws_server() " + str(pid) + " started")
          await asyncio.sleep(10)
          
          while not websocket.closed:
            try:
              print("await ping")
              pongwaiter=await websocket.ping()
              print("await Pong")
              await pongwaiter
              print("sleep 5")
              time.sleep(5)
              #print(DataFromWsServer)
              #await websocket.pong(DataFromWsServer)
              #except websockets.exceptions.ConnectionClosed:
            except:
              print ("ERR:mudserver.py/_ping_ws_server() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
              #(self.players[pid]).message("_pingpong_ws_server() : WS server connection closed\n\r",False)
              break
          print("_ping_ws_server() " + str(pid) + " ended")

    async def _pong_ws_server(self, pid, websocket):
          print("_pong_ws_server() " + str(pid) + " started")
          while not websocket.closed:
            try:
              #await websocket.pong()
              print("Pong running")
              time.sleep(60)
              #print(DataFromWsServer)
              #await websocket.pong(DataFromWsServer)
              #except websockets.exceptions.ConnectionClosed:
            except:
              print ("ERR:mudserver.py/_pong_ws_server() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
              #(self.players[pid]).message("_pingpong_ws_server() : WS server connection closed\n\r",False)
              break
          print("_pong_ws_server() " + str(pid) + " ended")

    async def _incoming_ws_server(self,pid, websocket):
          recv_cnt=0
          print("__incoming_ws_server() " + str(pid) + " started")
          while not websocket.closed:
            try:
              recv_cnt += 1
              DataFromWsServer = await websocket.recv()
              print("mudserver.py->_incoming_ws_server() WaitReceiveCount: "+str(recv_cnt) + " len=" + str(len(DataFromWsServer)) + " for PID #" + str(pid))        
              (self.players[pid]).message(DataFromWsServer,False)
              #print ("forwarded " + str(len(DataFromWsServer)) + " bytes to client")
            except websockets.exceptions.ConnectionClosed:
              (self.players[pid]).message("\n\r_incoming_ws_server() :\n\rWS server connection closed\n\r",False)
              break
          print("_incoming_ws_server() " + str(pid) + " ended")

    async def _outgoing_ws_server(self,pid, websocket):
          sent_cnt=0
          print("_outgoing_ws_server() " + str(pid) + " started")
          while not websocket.closed:
            try:
              sent_cnt += 1
              print("mudserver->_outgoing_ws_server() WaitKeysForwardCount: "+str(sent_cnt) + " for PID #" + str(pid))        
              DataToWsServer = await (self.players[pid]).keysforward.get()
  
              # TODO: try to get more messages and buffer writes?
              try:
                  await websocket.send(DataToWsServer)
                  print ("forwarded " + str(len(DataToWsServer)) + " bytes to server")
                  #for char in DataToWsServer:
                  #  print("'0x{:02x}'".format(ord(char)))
              except websockets.exceptions.ConnectionClosed:
                  break
            except websockets.exceptions.ConnectionClosed:
              (self.players[pid]).message("_ws_connect_to_server() : WS server connection closed\n\r",False)
              break
          print("_outgoing_ws_server() " + str(pid) + " ended")

    # handlers for each event
    # override these for custom behavior
    
    def on_player_join(self, pid):
        print("mudserver.py->on_player_join()")
        """This method is executed whenever a new player [pid] joins the
        server. By default, the player is assigned a new Character,
        which is then spawned in the game world.

        You can override this method to trigger custom behavior every
        time a player joins.
        """
        logging.info("%s joined.", pid)

        if self.GameDisabled == True:
          if self.default_class is not None:
              PlayerCls = self.default_class
          else:
              PlayerCls = self.world.random_cls()
          character = PlayerCls()
          self.players[pid] = character
          print("players[pid]=character=")
          character.spawn_nogame() 
        else:
  
          # first, look if this server has a default class established
          # if not, pick a random class stored in the World personae
          if self.default_class is not None:
              PlayerCls = self.default_class
          else:
              PlayerCls = self.world.random_cls()
          
          # initialize the Character and add it to the server
          character = PlayerCls()
          self.players[pid] = character
          print("players[pid]=character=")
          print(character)
  
          # now prepare a location for the player
          # as with default_class, a server-wide default_location takes
          # precedence
          if self.default_location is not None:
              start_loc = self.default_location
          elif PlayerCls.starting_location is not None:
              start_loc = PlayerCls.starting_location
          # if no default location has been defined for CharacterClass or
          # server, resort to picking the first location in locations
          else:
              try:
                  start_loc = next(iter(self.world.locations.values()))
              except StopIteration:
                  logging.critical("Could not spawn %d, "
                                   "world has no locations", pid)
                  return
              logging.warning("%s has no default location, "
                              "so %d will be spawned in %s",
                              PlayerCls, pid, start_loc)
  
          # put the character in "greet" mode
          print("character.spawn()")
          character.spawn(start_loc)
        try:
           pass
        except:
          print ("ERR:mudserver.py/on_player_join() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
          err=sys.exc_info()
          for item in err:
            print(item)
        finally:
          #print("Pending tasks at exit:")
          #for task in asyncio.all_tasks(asyncio.get_event_loop()):
          #  print(task)
          pass
        
    def on_player_msg(self, pid: int, msg: str):
        """This method is executed whenever a string of data [msg]
        is received from the TcpClient / WebSocket associated with
        [pid]. This method simply passes the msg onto the Character
        controlled by the player.

        You can override this method to trigger custom behavior every
        time a player sends a message to the server.
        """
        logging.info("%s says: [%s]", pid, msg)
        try:
            # Simply look up the character that belongs to this player,
            # and send the msg as a command.
            print("mudserver.py->on_player_msg->players[pid].command()")
            self.players[pid].command(msg)
            print("mudserver.py->on_player_msg->players[pid].keysforward")
            self.players[pid].keysforward.put_nowait(msg)

        # Now that we're triggering game code, a lot of errors could
        # occur. We're going to just log those and keep moving, so
        # that the server doesn't completely die.
        except Exception:
            logging.error(traceback.format_exc())

    def on_player_quit(self, pid):
        """This method is executed whenever a player [pid] disconnects
        from the server server. By default, the player's Character is
        destroyed and the other players are notified.

        You can override this method to trigger custom behavior every
        time a player quits.
        """
        logging.info("%s quit.", pid)

        try:
            character = self.players[pid]
        except KeyError:
            # player did not exist
            return

        # only send a message if character had provided a name
        if str(character) != "[nameless character]":
            self.message_all(f"{character} quit the game.")


        try:
            websocket = self._ws_clients[pid]
            if not websocket.closed:
              websocket.close()
              print("on_player_quit() : WebSocket client side closed")
            else:
              print("on_player_quit() : WebSocket client side already closed")
            del self._ws_clients[pid]
        except KeyError:
            # pid did not exist (was not connected to server ?)
            print("WARN mudserver.py->on_player_quit() no WS from client - client was already disconnected or came from telnet ?") 

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
            print("WARN mudserver.py->on_player_quit() no WS to remote server - server was already disconnected ?")
             

    # methods used in mudscript
    def message_all(self, message):
        """Sends the text in the 'message' parameter to every player that
        is connected to the server.
        """
        # We copy the _clients into a list to avoid dictionary changing
        # size during iteration.
        for (_pid, character) in self.players:
            character.message(message)

    def kick(self, character, reason: str=""):
        """Find the client associated with [character] and disconnect
        them from the game.
        Raises KeyError if [character] cannot be found.
        """
        # get the pid from the player biject
        # (raises KeyError if character not found)
        pid = self.players[character]

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
