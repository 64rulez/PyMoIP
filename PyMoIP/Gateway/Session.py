"""Module defining the CharacterClass metaclass and Character class,
which serves as the basis for all in-game characters.

This module also defines the 'Filter', used for CharacterClass-based
permissions systems, and 'Command', a wrapper that converts methods into
commands that can be invoked by characters.
"""
import asyncio

import os          # restart_teletel_server()
import subprocess  # restart_teletel_server()
import re          # restart_teletel_server()
import time        # restart_teletel_server()
#from netifaces import interfaces, ifaddresses, AF_INET


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
        self.MyCharTotalRecv=0
        self.MyCharTotalSent=0
        self.MyCharSessionRecv=0
        self.MyCharSessionSent=0
        self.MyCharSessionRedir=0
        self.MyStartTime=None
        self.MyDumpFile=""
        self.IsRedirected=False
        print("Session.py->__init__()")
        print("_parser=_nogame_parser")

    def MsgToDisplay(self,msg,AllSessions):
      for _pid, _UserSessions in AllSessions:
        if _UserSessions.MyAccess == "Display":
          _UserSessions.msgs.put_nowait(msg)
      
    def MsgToUser(self, msg, showdebug=True):
        if showdebug==True:
          print("Session.py->message(len=" + str(len(msg)) + ")")
          for char in msg:
            print("Session.py->message(chartype=" + str(type(char)) + ")")
            if type(char) == int:
              print("'0x{:04x}'".format(char))
            else:
              print("Session.py->message(charlen=" + str(len(char)) + ")")
              print("'0x{:02x}'".format(ord(char)))
        """send a message to the controller of this character"""
        # place a
        self.msgs.put_nowait(msg)

    def MsgFromUser(self, msg, showdebug=True):
        #print("MsgFromUser()")
        #print(msg)
        self.MyCharTotalRecv+=len(msg)
        self.MyCharSessionRecv+=len(msg)
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

    def _incoming_ws_removed():    
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
                  print("Timeout _incoming_ws() removed() _WS_CLIENT_MAX")
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

    def get_teletel_server_pid(self, port):
      popen = subprocess.Popen(['sudo', 'netstat', '-lpn'],
                               shell=False,
                               stdout=subprocess.PIPE)
      (data, err) = popen.communicate()
      data=data.decode(encoding="latin1")
      pattern = "^tcp *[0-9]* *[0-9] *[0-9.]*:{0} .*"  # Testé sur https://regex101.com/
      #pattern = "^tcp.*((?:{0})).* (?P[0-9]*)/.*$"    # Trouvé sur http://www.paulwhippconsulting.com/blog/finding-and-killing-processes-on-ports/ (et ne marche pas !)
      #pattern = pattern.format(')|(?:'.join(port))
      pattern = pattern.format(port)
      prog = re.compile(pattern)
      ReturnPid=None
      for line in data.split('\n'):
          match = re.match(prog, line)
          if match:
            line=re.sub(' +', ' ', line)
            pid=line.split(' ')[6]
            if pid.split('/')[1]=='python3':
              ReturnPid=pid.split('/')[0]
      return (ReturnPid)
              
    def kill_teletel_server(self, port):
      pid=Session.get_teletel_server_pid(self,port)
      if pid != None:
        popen = subprocess.Popen(['ps', '-ww', '-fp', pid],
                               shell=False,
                               stdout=subprocess.PIPE)
        (data, err) = popen.communicate()
        data=data.decode(encoding="latin1")
        if len(data.split('\n'))==3:
          line = data.split('\n')[1]
          line=re.sub(' +', ' ', line)
          #print(line.split(' ',7))
          cmdline=line.split(' ',7)[7]
          cmdline=cmdline.split(' ')
          MyArgs=[]
          #GotI=False
          GotS=False
          TempItem=""
          for item in cmdline:
            #if GotI==True:
            #  item='"'+item+'"'
            #  GotI=False
            if GotS==True:
              if GotScount==0:
                TempItem=item
                item=""
              else:
                if item[0]=="-":
                  GotS=False
                  if TempItem[0]!='"':
                    TempItem=TempItem+'"'
                else:
                  TempItem=TempItem+' '+item
                  item=""
              GotScount+=1
            #if item=="-i":
            #  GotI=True
            if item=="-s":
              GotS=True
              GotScount=0
              TempItem=""
            if GotS==False and len(TempItem)>0:
              #print(TempItem)
              MyArgs.append(TempItem) 
            if len(item)>0:
              #print(item)
              MyArgs.append(item) 
          if GotS==True:
            GotS=False
            if TempItem[0]!='"':
              TempItem=TempItem+'"'
            #print(TempItem) 
            MyArgs.append(TempItem) 
          #print(MyArgs)
          self.MyArgsTeletel=MyArgs
          #print("subprocess.run(['sudo','kill', '-9', {}]".format(pid))
          return(subprocess.run(['sudo','kill', '-9', pid],check=True,timeout=10))
        else:
          return("Command line not found => not restarted")
      else:
        return("get_teletel_server_pid(port) returned PID == None => not restarted")
        
    def restart_teletel_server(self):
      if len(self.MyArgsTeletel)>0:
          #(data, err) = popen.communicate()
          #data=data.decode(encoding="latin1")
          #print(data)
          MyArgs=self.MyArgsTeletel
          #print(MyArgs)
          #print("subprocess.Popen(MyArgs)")
          result=subprocess.Popen(MyArgs,start_new_session=True)
          return ("Done : ReturnCode="+str(result.poll())+" NewPid="+str(result.pid))
          #(data, err) = popen.communicate()
          #err=err.decode(encoding="latin1")
          #print(err)          
          #data=data.decode(encoding="latin1")
          #print(data)
      else:
        return("No args for teletel server - You may try to kill it once before")

    def GetMyIPs(self):
      #for ifaceName in interfaces():
      #  addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
      #print(' '.join(addresses))
      #return(' '.join(addresses))
      popen = subprocess.Popen(['ifconfig', '-a'],
                             shell=False,
                             stdout=subprocess.PIPE)
      (data, err) = popen.communicate()
      data=data.decode(encoding="latin1")
      pattern = "^ *inet ." 
      prog = re.compile(pattern)
      ReturnIPs=[]
      IPs=""
      for line in data.split('\n'):
          match = re.match(prog, line)
          if match:
            line=re.sub(' +', ' ', line)
            IP=line.split(' ')[2]
            ReturnIPs.append(IP)
            IPs=IPs+" "+IP
      return (IPs)
      
    def GetMyIPsTab(self):
      #for ifaceName in interfaces():
      #  addresses = [i['addr'] for i in ifaddresses(ifaceName).setdefault(AF_INET, [{'addr':'No IP addr'}] )]
      #print(' '.join(addresses))
      #return(' '.join(addresses))
      popen = subprocess.Popen(['ifconfig', '-a'],
                             shell=False,
                             stdout=subprocess.PIPE)
      (data, err) = popen.communicate()
      data=data.decode(encoding="latin1")
      pattern = "^ *inet ." 
      prog = re.compile(pattern)
      ReturnIPs=[]
      IPs=""
      for line in data.split('\n'):
          match = re.match(prog, line)
          if match:
            line=re.sub(' +', ' ', line)
            IP=line.split(' ')[2]
            ReturnIPs.append(IP)
            IPs=IPs+" "+IP
      return (ReturnIPs)
      
    