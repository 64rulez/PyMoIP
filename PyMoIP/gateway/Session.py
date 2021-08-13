"""Module defining the CharacterClass metaclass and Character class,
which serves as the basis for all in-game characters.

This module also defines the 'Filter', used for CharacterClass-based
permissions systems, and 'Command', a wrapper that converts methods into
commands that can be invoked by characters.
"""
import asyncio


class Session():
    def __init__(self, name=None):
        self._name = name
        self.msgs = asyncio.Queue()
        self.keysforward = asyncio.Queue()
        self.command = asyncio.Queue()
        self.kill_incoming = asyncio.Queue()
        self._parser = self._nogame_parser
        self.ReplyedToEnqRom=False
        self.MyIP=""
        self.MyPort=""
        self.MySession=-1
        self.MyTarget=""
        self.MyPing=None
        self.MySub=[]
        self.MyRemoteWS=None
        self.MyRemoteTN=None
        self.GotSep=False
        print("Session.py->__init__()")
        print("_parser=_nogame_parser")

    def MsgToUser(self, msg, showdebug=True):
        if showdebug==True:
          print("Session.py->message(len=" + str(len(msg)) + ")")
          for char in msg:
            print("'0x{:02x}'".format(ord(char)))
        """send a message to the controller of this character"""
        # place a
        self.msgs.put_nowait(msg)

    def MsgFromUser(self, msg, showdebug=True):
        #print("MsgFromUser()")
        #print(msg)
        self.keysforward.put_nowait(msg)

    def clear_remote():    #Fermer la session distante et nettoyer les variables
      pass
              
#    def update(self):
#        """periodically called method that updates character state"""
#        print(f"[{self}] received update")

    def spawn_nogame(self):
        print("Session.py->spawn_nogame()")
        self._parser = self._nogame_parser
        print("_parser=_join_parser")

    def _nogame_parser(self, new_name: str):
        print("Session.py->_nogame_parser()")
    

