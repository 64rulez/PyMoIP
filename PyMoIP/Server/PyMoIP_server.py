#!/usr/bin/envh python
# PyMoIP_server.py

import sys
import asyncio
import websockets
import threading
import logging

from Server.PyMoIP_arbo import Arbo
from Server.PyMoIP_global import *

NumSession=0    # Nombre de sessions actuellement ouvertes
TotalSession=0  # Nombre de sessions ouvertes depuis le début de l'exécution du serveur - Devriendra l'identifiant unique de session
ListSession=[]  # Liste de toutes les sessions ouvertes - Contient [<MySession>,<Remote_IP>,<MyPseudo>,<*>,<Liste>,<Arbo>]
refs = locals()             # Accès indirect aux variables partagées (Field)
refs_prefix = "_PyMoIp_"    # Toutes les variables partagées sont préfixées par cette constante et postfixées par '_<MySession>'
lock = threading.Lock()

class Server:
  def __init__(self,command_port,server_port,arbo_boot,path_modules):
      self.command_port=command_port
      self.server_port=server_port
      self.arbo_boot=arbo_boot
      self.path_modules=path_modules
      self.MyGtw=None
      self.refs=refs
  
  def handle_exception(self,loop, context):
      # https://github.com/aaugustin/websockets/issues/338
      # context["message"] will always be there; but context["exception"] may not
      msg = context.get("exception", context["message"])
      print(f"Caught exception: {msg}")
      #asyncio.create_task(shutdown(loop))
      logging.error(f"Caught exception: {msg}")
      #logging.info("Shutting down...")
      #asyncio.create_task(shutdown(loop))
  
  
  def ShowAsyncTasks(self,MyMessage, Force=False):
      if DoDebugAsync == True or Force == True: 
        z=asyncio.all_tasks()
        print(MyMessage + " : ="+str(len(z))+".")
        cnt=0
        for zz in z:
          cnt+=1
          print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
          print(zz.get_stack(limit=3))
  
  def CreateSession(self,Remote_IP):
      global NumSession
      global TotalSession
      global ListSession
      global lock
  
      NumSession = NumSession + 1
      try:
        lock.acquire()
        # --- Code should be atomic
        TotalSession = TotalSession + 1
        MySession = TotalSession
        ListSession.append([MySession,Remote_IP,"MonPseudo"+str(MySession),"*",bytearray(),"-"])
        # -----
      finally :
          lock.release()
      return MySession
  
  def DeleteSession(self,MySession):
      global NumSession
      global ListSession
      global lock
  
      SessionId=-1
      SessionCount=0
      NumSession=NumSession - 1
      try:
        lock.acquire()
        for Session in ListSession :
          if Session[0] == MySession :
            SessionId=SessionCount
          SessionCount += 1
        if SessionId > -1 :
          ListSession.pop(SessionId)
          print ("Deleted session " + str(MySession))
        else:
          print("Can't find session " + str(MySession))
      finally :
          lock.release()
      print("SessionCount="+str(SessionCount)+" => "+str(len(ListSession)))                  
      for Session in ListSession :
        print(Session)
  
  async def VideotextServer(self,websocket, path):  
    try:
      Remote_IP = websocket.remote_address[0]
      global refs
      global ListSession
      
      MySession=self.CreateSession(Remote_IP)
      self.ShowAsyncTasks("Pending tasks at start of VideotextServer()")
  
                 
      print(f"STARTED VideotextServer() FROM  '{Remote_IP}' NumUsers={NumSession} MySession={MySession}.")
      #
      # Définition de la racine de l'arborescence - Prépare l'objet correspondant
      #
      try:
        MyArbo = Arbo(self.arbo_boot,self.path_modules,self.MyGtw,asyncio.get_event_loop(),MySession,websocket,refs)
        print("ConstList après Arbo()")
        print (MyArbo.ConstList)
        print("----")
      except:
                print("ERROR : Arbo()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
      MyArbo._tasks.append(MyArbo.loop.create_task(MyArbo._recv_with_timeout(MyArbo.websocket,0)))  # Impossible d'ajouter la tâche depuis la classe ???
      MyArbo._tasks.append(MyArbo.loop.create_task(MyArbo._msg_with_timeout(MyArbo.websocket,1)))   # Impossible d'ajouter la tâche depuis la classe ???
      await MyArbo.ArboStart("arbo_start",path)
      #
      # Lien vers l'objet Arbo dans ListSession pour interaction avec Gateway
      #
      MyList=ListSession
      Found=-1
      Count=0
      for item in MyList:
          if item[LIST_SESSION_SESSION]==MyArbo.MySession:
            Found=Count
          Count+=1
      if Found>-1:
          ListSession[Found][LIST_SESSION_MYARBO]=MyArbo
      #    
      print ("SERVER START {}".format(path))
      while MyArbo.GotLib==False:
          try:
            try:
              await MyArbo.UpdateDisplay()
            except:
                print("ERROR : await UpdateDisplay()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:
              await MyArbo.UpdateTimer()
            except:
                print("ERROR : await UpdateTimer()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:
              await MyArbo.WaitEvent()
            except:
                print("ERROR : await WaitEvent()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:        
              await MyArbo.EventRawReceived()  # Needs await as it possibly sends data
            except:
                print("ERROR : await EventRawReceived()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:
              MyArbo.EventMsg()
            except:
                print("ERROR : NOawait EventMsgReceived()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:
              MyArbo.EventTimer()
            except:
                print("ERROR : NOawait EventTimer()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
            try:
              if (MyArbo.MsgReceived == None) and (  MyArbo.RawReceived == None) and (MyArbo.TimerReceived == None):
                #print("--Timeout--")
                #print(ListSession)
                pass
              MyArbo.EventTimeout()
            except:
                print("ERROR : NOawait EventTimeout()")
                err=sys.exc_info()
                for item in err:
                  print(item)
                raise
          #
          # Bloc TRY depuis WaitEvent, incluant le traitement des évènements
          #
          except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
            print ("ERR:Main.recv() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
            #
            # Traitement des modules
            #
            MyArbo.CallModule('lib',"Closed")
            MyArbo.GotLib=True
            MyArbo.DebugInput+=str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])
            pass
          if len (MyArbo.DebugInput) > 0:
              if DoDebugInput==True:
                print(f"SERVER GOT '{MyArbo.DebugInput}'")
              MyArbo.DebugInput=""
      #
      # Fin de la boucle principale - Ici, GotLib=True
      #
      print(f"SERVER GOT '{MyArbo.DebugInput}' EXITING")
      #
      # Traitement des modules
      #
      MyArbo.CallModule('lib',"Bye")
      MyArbo.DebugInput=""
    finally:
      print("FINALLY")
      #
      # Bloc TRY principal - Depuis initialisation de la session, le traitement possible des erreurs a déjà été effectué
      #
      #
      # Do whatever is necessary to save/close after the session completes
      await MyArbo.KillAllTasks()
      self.ShowAsyncTasks("Pending tasks after websocket.close()")
      self.DeleteSession(MySession)
      del MyArbo
      print("FINALLY done")

