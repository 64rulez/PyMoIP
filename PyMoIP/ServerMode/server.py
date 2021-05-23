#!/usr/bin/envh python

# WS server example
import sys
import asyncio
import websockets
import threading
import logging

TestList=[["Toto1",123,"AAA1"],["Tata1",456,"AAA2"],["Titi1",7890,"AAA3"],["Toto2",1230,"AAA4"],["Tata2",4560,"AAA5"],["Titi2",7890,"AAA6"],["Toto2",1232,"AAA7"],["Tata2",4562,"AAA8"],["Titi2",7891,"AAA9"],["Toto3",1233,"AAA10"],["Tata3",4563,"AAA11"],["Titi3",7893,"AAA12"]]

#
# Variables globales
#
DoEchoBufferInput  = True  # Effectue l'écho des caractères bufferisés
DoRefreshPrevField = False # Lors d'un changement de champ, réaffiche le champ qui vient d'être quitté avant d'afficher le nouveau champ en cours de saisie  
DoDebugList    = False     # Affiche les infos de trace pour les listes
DoDebugSetArbo = False     # Affiche les infos de trace pour l'arborescence
DoDebugAsync   = False     # Affiche les infos de trace pour l'async
DoDebugTimer   = False     # Affiche les infos de trace pour le timer

NumSession=0    # Nombre de sessions actuellement ouvertes
TotalSession=0  # Nombre de sessions ouvertes depuis le début de l'exécution du serveur - Devriendra l'identifiant unique de session
ListSession=[]  # Liste de toutes les sessions ouvertes - Contient [<MySession>,<Remote_IP>]
refs = locals()             # Accès indirect aux variables partagées (Field)
refs_prefix = "_PyMoIp_"    # Toutes les variables partagées sont préfixées par cette constante et postfixées par '_<MySession>'
lock = threading.Lock()

MyIP="0.0.0.0"  # 0.0.0.0 means all @IPs
MyPort=8765

def handle_exception(loop, context):
    # https://github.com/aaugustin/websockets/issues/338
    # context["message"] will always be there; but context["exception"] may not
    msg = context.get("exception", context["message"])
    print(f"Caught exception: {msg}")
    #asyncio.create_task(shutdown(loop))
    logging.error(f"Caught exception: {msg}")
    #logging.info("Shutting down...")
    #asyncio.create_task(shutdown(loop))

def GetPage(fichier):
    # "Envoi du contenu d'un fichier"
    f = open(fichier, 'rb')
    contents=f.read()
    f.close()
    return (contents)

async def hello(websocket, path):
  
  try:
    Remote_IP = websocket.remote_address[0]
    global NumSession
    global TotalSession
    global ListSession
    global refs
    global lock
    
    NumSession = NumSession + 1
    try:
      lock.acquire()
      # --- Code should be atomic
      TotalSession = TotalSession + 1
      MySession = TotalSession
      ListSession.append([MySession,Remote_IP,"MonPseudo"+str(MySession),"*"])
      # -----
    finally :
        lock.release()

    if DoDebugAsync == True: 
      z=asyncio.all_tasks()
      print("Pending tasks at start of hello() : ="+str(len(z))+".")
      cnt=0
      for zz in z:
        cnt+=1
        print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
        print(zz.get_stack(limit=3))

    if True:    # Constants
        CHAR_SOH  =chr(0x01)
        CHAR_EOT  =chr(0x04)
        CHAR_ENQ  =chr(0x05)
        CHAR_BEEP =chr(0x07)
        CHAR_BS   =chr(0x08)
        CHAR_VTAB =chr(0x0a)
        CHAR_RC   =chr(0x0d)
        CHAR_CON  =chr(0x11)
        CHAR_REP  =chr(0x12)
        CHAR_SEP  =chr(0x13)
        CHAR_COFF =chr(0x14)
        CHAR_CAN  =chr(24)
        CHAR_SS2  =chr(0x19)
        CHAR_ESC  =chr(0x1b)
        CHAR_US   =chr(0x1f)
        CHAR_PRO1 =chr(0x39)
        CHAR_PRO2 =chr(0x3a)
        CHAR_PRO3 =chr(0x3b)
        CHAR_CSI  =chr(0x5b)
        CHAR_ENVOI     ='A'
        CHAR_RETOUR    ='B'
        CHAR_REPETITION='C'
        CHAR_GUIDE     ='D'
        CHAR_ANNULATION='E'
        CHAR_SOMMAIRE  ='F'
        CHAR_CORRECTION='G'
        CHAR_SUITE     ='H'
        CHAR_CONNECTION='I'
        CHAR_CONNECTION_MODEM='Y'
        CHAR_ACCENT_LIST = ["@","A","B","C","D","E","F","G","H","I","J","K","L","M","N"]  # Liste des accents possibles (SS2 sur 3 caractères)
        #
        VAR_POSV = 0
        VAR_POSH = 1
        VAR_ATTRIBS = 2
        VAR_NAME = 3
        VAR_SIZE = 4
        VAR_FILL = 5
        #
        FIELD_POSV = 0
        FIELD_POSH = 1
        FIELD_ATTRIBS = 2
        FIELD_NAME = 3
        FIELD_SIZE = 4
        FIELD_FILL = 5
        #
        #  Constantes pour les listes
        #
        LIST_NAME     = 0
        LIST_NB_LIN   = 1
        LIST_NB_COL   = 2
        LIST_FIRST_LIN= 3
        LIST_FIRST_COL= 4
        LIST_SIZE_COL = 5
        LIST_DEFS     = 6
        LIST_FILL_1   = 7
        LIST_ATTR_1   = 8
        LIST_FILL_2   = 9
        LIST_ATTR_2   = 10
        #
        LIST_DEF_ITEM = 0
        LIST_DEF_COLS = 1
        LIST_DEF_SKIP = 2
        LIST_DEF_ATTR = 3
        #
        # Constantes pour ListSession
        #
        LIST_SESSION_SESSION = 0
        LIST_SESSION_SESSION_IP = 1
        LIST_SESSION_PSEUDO  = 2
        LIST_SESSION_PVALIDE = 3
        
    if True:    # Init vars
        GotSep=False
        GotSS2=False
        GotEsc=False
        GotCsi=False
        GotProSeq = 0
        ProtocolSeq = ""
        GotCsiSeq=""
        BufferEcho =""
        #
        # Variables concernant la réception des réponses ROM/RAM
        #
        ReplyRomRamIndex   = 0     # Nb caractères recus dans ROM/RAM en cours
        ReplyRomRam        = 0     # Item ROM/RAM en attente (0=ROM, 1=RAM1, 2=RAM2)
        ReplyRomRamPending = False # ROM/RAM en cours de réception (SOH reçu)
        #
        RawReceived=""              # Caracteres recus depuis WS
        MsgReceived=""              # Messages recus
        TimerReceived=False         # Timer reçu
        
    print(f"STARTED hello() FROM  '{Remote_IP}' NumUsers={NumSession} MySession={MySession}.")
    
    class Arbo:
    
        def __init__(self,ArboRoot,loop):
            self.ArboRoot    = ArboRoot + "."
            self.ArboCur     = "<None>"         # Position actuelle dans l'arborescence - "<None>" avant d'entrer 
            self.FirstFile   = 0                # Numéro de la première page (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [accessibles par SUITE/RETOUR]  
            self.LastFile    = 0                # Numéro de la dernière page (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [accessibles par SUITE/RETOUR]
            self.CurFile     = ""               # Numéro de la page actuelle - commence par la première (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [modifié par SUITE/RETOUR]
            self.PrefixFile  = ""               # Préfixe du nom des pages de la séquence (ex : MENU_ pour une page qui serait nommée MENU_1_TEST.VDT)
            self.PostfixFile = ""               # Postfixe du nom des pages de la séquence (ex : _TEST.vdt pour une page qui serait nommée MENU_1_TEST.VDT)
            self.PageDir     = ""               # Répertoire où se trouve la séquence de pages pour cet emplacement de l'arborescence
            self.GuideLink   = ""
            self.TimeoutLink = ""
            self.TimerLink   = ""
            self.VarList     = list()           # Ceci contient la liste des variables à évaluer dynamiquement dans self.InsertPostBytes
            self.FieldList   = list()           # Ceci contient la liste des champs à évaluer dynamiquement dans self.InsertPostFields XXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            self.DisplayList = list()           # Définition de la liste en cours d'affichage (seulement les items affichés/affichables)
            self.MenuList    = list()           # Définition du menu en cours [Item de menu,Lien d'arborescence]
            self.BypassList  = list()           # Conditions pour bypasser cet emplacement de l'arborescence
            self.KeywordList = list()           # Mots clés reconnus
            self.TimeoutLimit= 0                # Nombre de secondes dans await websocket.recev sans Raw/Msg/Timer avant declanchement de timeout - doit être < TimerDelay [ou TimerDelay=0], sinon, timeout ne sera jamais déclanché 
            self.TimerDelay  = 0                # Nombre de secondes dans await websocket.recev depuis SetArbo() avant declanchement de timer 
            #
            self.Module      = "<None>"
            self.ModuleName  = "<None>"
            self.CurrentList = list()           # Contenu des champs de la liste en cours d'affichage
            self.CurrentListDefs = list()       # Définition des champs de la liste en cours d'affichage
            self.CurField    = 0                # Numéro de champ en cours de saisie
            self.PrevField = -1                 # Probablement inutile - Précédent champ en cours de saisie ou -1 si aucun
            self.PageDisplayList = 0            # Numéro de page actuel dans la liste
            self.InsertBytes = bytearray()      # Ceci est arbitrairement envoyé avant la page, et effacé une fois la page envoyée
            self.InsertPostBytes = bytearray()  # Ceci correspond aux variables à inclure à la page, évalué et mis en forme au moment du chargement de la page. Est envoyé après la page.
            self.InsertPostField = bytearray()  # Ceci correspond aux champs à inclure à la page, évalué et mis en forme au moment du chargement de la page. Est envoyé après la page et InsertPostBytes.XXXXXXXXXXXXXX
            self.StackList   = list()           # Liste des points de l'arborescence empilés (lors de 'guide' par ex) pour retour avec sommaire
            self.DoSendPage  = False            # Il faudra envoyer la page
            self.RefreshCurField = False        # Il faudra juste rafraichir le champ
            self.NumPageDisplayList = bytearray()  # Numéro de page dans la liste (affichable)
            self.NumPagesDisplayList = bytearray() # Nombre de pages dans la liste (affichable)
            self.BufferInput = ""
            self.DebugInput = ""
            self.GotLib      = False
            self.GotRom      = bytearray()  # Contenu ROM recu
            self.GotRam1     = bytearray()  # Contenu RAM1 recu
            self.GotRam2     = bytearray()  # Contenu RAM2 recu
            self.ReplyRomRamExpect  = 0     # Nb ROM/RAM attendu (0 = aucun)
            self.NumPageVdt  = bytearray()            # Numéro affichable de la page dans la séquence 
            self.NumPagesVdt = bytearray()            # Nombre total affichable de pages dans la séquence 
            self._tasks       = []                    # Liste des taches async
            self._RcvQueue    = asyncio.Queue()       # Queue de reception des messages
            self.TimeoutCount = 0                     # Nombre de timeout declanches depuis caractere recu par await websocket.recev
            self.TimerCount   = 0                     # Nombre de timer declanches - RAZ en début de session
            self.TimerChanged = False                 # Passe à True à chaque passage dans SetArbo - La tâche Timer est mise à jour dans Hello() afin d'éviter les pbs de boucle lorsque SetArbo() est mis à jour depuis un module 
            self.websocket    = websocket             # Au cas où .... permet websocket.send depuis un module (avec un thread distinct)
            self.loop         = loop                  # S'assure qu'on lance bien les tâches dans la bouche asyncio de départ (au cas où)

            #MyArbo._tasks = []
            #task = asyncio.create_task(foo())
            #              DataToWsServer = await (self.players[pid]).keysforward.get()
  
            #self._tasks.append(asyncio.ensure_future(_recv_with_timeout(self,websocket,0)))
            #MyArbo._tasks.append(asyncio.ensure_future(_timeout_for_recv (MyArbo,websocket,1)))
            self._tasks.append(self.loop.create_task(_recv_with_timeout(self,websocket,0)))
            self._tasks.append(self.loop.create_task(_msg_with_timeout(self,websocket,1)))
            ###self._tasks.append(asyncio.create_task(_timer_with_timeout(self,websocket,2)))
            #self._tasks.append(_recv_with_timeout(self,websocket,0))
            #MyArbo._tasks.append(asyncio.create_task(foo()))
            
        def SetArbo (self,ArboCur):           
            MoveArbo=True            # Boucle dans l'arborescence - si fichier arbo_xxxxxx.py manquant ou Bypass
            PrevArbo=self.ArboCur    # Emplacement actuel dans l'arbo, pour y revenir au cas d'erreur à destination (fichier arbo manquant)
            ErrorInArbo = False      # Passe à Vrai en cas d'erreur sur l'arbo 
                        
            while MoveArbo==True:
              MoveArbo=False
              print(f"SetArbo() SERVER ARBO MOVE from '{self.ArboCur}' to '{ArboCur}'")
              if self.ArboCur == "<None>":
                self.InsertBytes= (chr(31)+"00"+chr(24)+chr(27)+"T Arriving"+chr(10)).encode('utf-8') # Hello
                print(f"ARRIVING")
                
              self.ArboCur=ArboCur
              # Chargement des valeurs d'arbo par défaut (pour ne pas devoir définir chaque variable dans chaque fichier <arbo>.py)
              if (DoDebugSetArbo==True):
                print("SetArbo() : __IMPORT__" + self.ArboRoot+"arbo_defaultvar")
              try:
                _tempDef = __import__(self.ArboRoot+"arbo_defaultvar", globals(), locals(), ['FirstFile', 'LastFile', 'PrefixFile', 'PostfiFile', 'PageDir', 
                                            'GuideLink', 'TimeoutLink', 'TimertLink', 'VarList', 'FieldList', 'DisplayList', 'MenuList', 'Module', 'BypassList', 'KeywordList', 'TimeoutLimit'], 0)
                if (DoDebugSetArbo==True):
                  print("$Success arbo_defaultvar.py$")
              except:
                print ("ERR:SetArbo(ArboDef,"+ self.ArboRoot + "arbo_defaultvar) "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                err=sys.exc_info()
                for item in err:
                  print(item)
                print("$import '" + self.ArboRoot + "arbo_defaultvar' error$")
                MyArbo.DebugInput+="$import '" + self.ArboRoot + "arbo_defaultvar' error$"
                pass
  
              self.FirstFile   = _tempDef.FirstFile
              self.LastFile    = _tempDef.LastFile
              self.PrefixFile  = _tempDef.PrefixFile
              self.PostfixFile = _tempDef.PostfixFile
              self.PageDir     = _tempDef.PageDir
              self.GuideLink   = _tempDef.GuideLink
              self.TimeoutLink = _tempDef.TimeoutLink
              self.TimerLink   = _tempDef.TimerLink
              self.VarList     = _tempDef.VarList
              self.FieldList   = _tempDef.FieldList
              self.DisplayList = _tempDef.DisplayList
              self.MenuList    = _tempDef.MenuList
              self.BypassList  = _tempDef.BypassList
              self.Module      = _tempDef.Module      # Should be <None>
              self.ModuleName  = _tempDef.Module      # Should be <None>
              self.KeywordList = _tempDef.KeywordList # Devrait avoir la liste des mots clé ici
              self.TimeoutLimit= _tempDef.TimeoutLimit# Should be 0 seconds
              self.TimerDelay  = _tempDef.TimeoutLimit# Should be 0 seconds
              # Chargement des valeurs d'arbo spécifiques à l'emplacement actuel dans l'arborescence (ArboCur)
              if (DoDebugSetArbo==True):
                print("SetArbo() : __IMPORT__" + self.ArboRoot+self.ArboCur)
              try:
                _temp    = __import__(self.ArboRoot+self.ArboCur, globals(), locals(), ['FirstFile', 'LastFile', 'PrefixFile', 'PostfiFile', 'PageDir', 
                                              'GuideLink', 'TimeoutLink', 'TimerLink', 'VarList', 'FieldList', 'DisplayList', 'MenuList', 'Module', 'BypassList', 'KeywordList', 'TimeoutLimit', 'TimerDelay'], 0)
                if (DoDebugSetArbo==True):
                  print("$Success " + self.ArboCur + ".py $")
              except:
                if (DoDebugSetArbo==True):
                  print ("ERR:SetArbo(ArboCur," + self.ArboRoot+self.ArboCur + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                  err=sys.exc_info()
                  for item in err:
                    print(item)
                  print("$import '" + self.ArboRoot+self.ArboCur + "' error$")
                MyArbo.DebugInput+="$import '" + self.ArboRoot+self.ArboCur + "' error$"
                self.SetMessage("Arbo:'"+self.ArboCur+"'missing",False)
                if ErrorInArbo ==False:
                  ErrorInArbo = True      # Passe à Vrai en cas d'erreur sur l'arbo
                  MoveArbo=True           # Essayer de revenir à l'emplacement de départ
                  ArboCur=PrevArbo 
                  if not MyArbo.StackList :
                    MyArbo.DebugInput += "$TopLevelReached$"
                  else :                                       
                    MyArbo.StackList.pop()

                  if (DoDebugSetArbo==True):
                    print("SetArbo() : Trying to loop back once after first error")
                else:
                  MyArbo.DebugInput+="$import '" + self.ArboRoot+self.ArboCur + "' double error$"
                  if (DoDebugSetArbo==True):
                    print("SetArbo() : Don't try to loop back after second error")
                pass
              try:
                self.FirstFile   = _temp.FirstFile
              except:
                pass
              try:
                self.LastFile    = _temp.LastFile
              except:
                pass
              try:
                self.PrefixFile  = _temp.PrefixFile
              except:
                pass
              try:
                self.PostfixFile = _temp.PostfixFile
              except:
                pass
              try:
                self.PageDir     = _temp.PageDir
              except:
                pass
              try:
                self.GuideLink   = _temp.GuideLink
              except:
                pass
              try:
                self.TimeoutLink   = _temp.TimeoutLink
              except:
                pass
              try:
                self.TimerLink   = _temp.TimerLink
              except:
                pass
              try:
                self.VarList     = _temp.VarList
              except:
                pass
              try:
                self.FieldList   = _temp.FieldList
              except:
                pass
              try:
                self.DisplayList = _temp.DisplayList
              except:
                pass
              try:
                self.MenuList    = _temp.MenuList
              except:
                pass
              try:
                self.BypassList  = _temp.BypassList
              except:
                pass
              try:
                self.KeywordList  = _temp.KeywordList  # Devrait liste des mots clé alternatifs ici
              except:
                pass
              try:
                self.TimeoutLimit  = _temp.TimeoutLimit
              except:
                pass
              try:
                self.TimerDelay  = _temp.TimerDelay
              except:
                pass
              #
              # Reset vars for current location
              #
              self.CurFile  = self.FirstFile    # Première page (dans une séquence de pages) 
              self.CurField = 0                 # Premier champ de saisie
              self.PageDisplayList = 0          # Première page sur la liste affichée
              self.CurrentList = list()         # La liste actuellement affichée ne contient aucun item
              self.CurrentListDefs = list()       # Définition des champs de la liste en cours d'affichage
              self.NumPageDisplayList    = bytearray()
              self.NumPagesDisplayList   = bytearray()
              self.NumPageVdt  = str(self.CurFile-self.FirstFile + 1).encode('utf-8')            # Numéro affichable de la page dans la séquence 
              self.NumPagesVdt = str(self.LastFile-self.FirstFile + 1).encode('utf-8')            # Nombre total affichable de pages dans la séquence 
              if (DoDebugSetArbo==True):
                print("=================")
                print(self.NumPagesVdt)

              self.DoSendPage=True              # Afficher la page
              self.RefreshCurField=False        # Ne pas rafraichir le champ (puisqu'il a sera envoyé après la page)
              self.PrevField = -1        # Probablement inutile / Il n'y a pas de champ précédent à rafraichir
              #
              # Bypass
              #
              if len(self.BypassList) > 0:
                CountBypass=0
                for Bypass in self.BypassList:
                  if MoveArbo==False:
                    if (DoDebugSetArbo==True):
                      print ("BypassList [" + str(CountBypass+1)+"]")
                      print (Bypass)
                      print (Bypass[0])
                    MyVal=self.GetVarInArboClass(Bypass[0])
                    if (DoDebugSetArbo==True):
                      print(MyVal)
                    if type(MyVal) is bytearray:
                      MyVal=MyVal.decode('utf-8','strict')
                    if (Bypass[1]=="=") or (Bypass[1]=="==") or (Bypass[1]=="is") :
                      if MyVal == Bypass[2]:
                        MoveArbo=True
                        ArboCur=Bypass[3]                       
                    if (Bypass[1]=="!=") or (Bypass[1]=="<>") or (Bypass[1]=="not") :
                      if MyVal != Bypass[2]:
                        MoveArbo=True
                        ArboCur=Bypass[3]                       
                    if (Bypass[1]=="=*")  :                              # Le début de la variable est égal à la valeur testée
                      if MyVal[:len(Bypass[2])] == Bypass[2]:
                        MoveArbo=True
                        ArboCur=Bypass[3]                       
                    if (Bypass[1]=="*=")  :                              # La fin de la variable est égale à la valeur testée
                      if MyVal[-len(Bypass[2]):] == Bypass[2]:
                        MoveArbo=True
                        ArboCur=Bypass[3]                       
                    CountBypass+=1
    
              if MoveArbo==False: # N'essaye pas de charger un module si l'arbo est KO
                try:
                  if (DoDebugSetArbo==True):
                    print ("_temp.module ?????")
                    print (_temp)
                    print("self.ModuleName="+self.ModuleName)
                    print("-=-=-=-=-=-")
                    if hasattr(_temp, 'Module'):
                      print (hasattr(_temp, 'Module'))
                      print(type(_temp.Module))
                      print("hasattr :")
                      print("_temp.Module=")
                      print(_temp.Module)
                      print("-=-=-=-=-=-")
                    else:
                      print("No attribute 'Module' in _temp")
  
                  if hasattr(_temp, 'Module') : # and (_temp.ModuleName != "<None>"):              
                    self.ModuleName=_temp.Module
                    if (DoDebugSetArbo==True):
                      print("__IMPORT__ trying to import _temp.Module '" + _temp.Module + "' ....")
                    self.Module      = __import__ (_temp.Module)
                    if (DoDebugSetArbo==True):
                      print("__IMPORT__ '" + _temp.Module + "' done.")
                  else:
                    if hasattr(_tempDef, 'Module') and hasattr(_tempDef, 'ModuleName'): # and (_temp.ModuleName != "<None>"):              
                      if (DoDebugSetArbo==True):
                        print("__IMPORT__ no module defined in '" + self.ArboCur + "' - Trying with _tempDef.Module " + _tempDef.ModuleName + " .")                    
                      self.Module=_tempDef.Module
                      self.ModuleName=_tempDef.Module
                      if (DoDebugSetArbo==True):
                        print("__IMPORT__ no module defined in '" + self.ArboCur + "'.")
                    else:
                      if (DoDebugSetArbo==True):
                        print("__IMPORT__ no module defined in '" + self.ArboCur + "' and in '" + self.ArboRoot+"arbo_defaultvar'.")                    
                      
                except AttributeError :
                  print ("ERR:SetArbo(LoadModule," + _temp.Module + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                  err=sys.exc_info()
                  for item in err:
                    print(item)
                  print("$Module import '" + _temp.Module + "' error$")
                  MyArbo.DebugInput+="$Module import '" + _temp.Module + "' error$"
                  pass
            self.TimerChanged = True                # Sera pris en compte dans Hello()
            self.CallModule('init',"Initialized "+ str(MySession))
            
#            except:
#              self.InsertBytes = (chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1])).encode('utf-8')  #+chr(10)+chr(13)+str(sys.exc_info()[2])
#              print ("ERR:SetArbo "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
#              pass

        def CallModule(self,Touche,Comment):
          if hasattr(MyArbo.Module, Touche) :
            try:
              #print("Calling module :")
              #print("-----")
              Return=(getattr(MyArbo.Module, Touche))(refs,locals(),Comment)
              if Return == True:
                print("$Success received from module with '" + Touche + "'$")
                if len(MyArbo.FieldList) and (Touche != 'init') and (Touche != 'timeout'):
                  UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")  # Vide le champ en cours
                  ClearBufferInput()      # Vide BufferInput
                  MyArbo.SetMessage(CHAR_COFF,False)
                  #MyArbo.DoSendPage=True
              else: 
                #MyArbo.DoSendPage=True
                MyArbo.RefreshCurField=True
                print("$Called module failled with '" + Touche + "'$")
            except:
              print ("ERR CallModule():"+ MyArbo.ModuleName +"('" + Touche + "') "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
          else:
            print("CallModule("+Touche+","+Comment+") fonction not found in module")

        def GetVarInArboClass(self,MyVarToGet,DontManageList=False):
          DoDebugGetVarInArboClass=False
          #print("GetVarInArboClass("+MyVar+")")
          if False:
            print(vars(self).get("MenuList"))
            #print((vars().get("self")).get("MenuList"))
            print(vars().get("self.MenuList"))
            print ("GotRom")
            #print (GotRom)
            print("Vars")
            print(vars())
            #print ((vars().get(self)).get("MenuList"))
            print ("locals")
            print (locals())
            print ("globals")
            print (globals())
          
          # Ex: *ListSession:*:3,4 ==> 4 premiers caractères du pseudo de la session en cours
          # 
          ParamLen=len(MyVarToGet.split(","))
          MyVarToFetch=MyVarToGet.split(",")[0]  # 
          MyVar=MyVarToFetch.split(":")[0]       # 
          if DoDebugGetVarInArboClass == True:
            print("MyVarToGet[0] =")
            print(MyVarToGet.split(","))
            print(MyVarToGet.split(",")[0])
            print("MyVarToFetch =")
            print(MyVarToFetch)
          
          try:   
            if (MyVar[:1]=="*") :                                # (*) = Valeur globale
              if MyVar[1:] in refs:
                MyTempVal = refs[MyVar[1:]]
              else:
                MyTempVal = "Udef:"+MyVar
            elif (MyVar[:1]=="#") :                              # (#) = Valeur locale [Doit être défini en dur, quelque part => MySession / Ok, GotRom / Ko]
              MyTempVal=vars().get(MyVar[1:],"Udef:"+MyVar)
            elif (MyVar[:1]=="%") :                              # (%) = Valeur dans l'objet (self)
              MyTempVal=(vars(self).get(MyVar[1:],"Udef:"+MyVar))
            else:                                                # Valeur globale indexée sur session => 'Locale'
              if refs_prefix + MyVar + "_" + str(MySession) in refs:
                MyTempVal = refs[refs_prefix + MyVar + "_" + str(MySession)]
              else:
                MyTempVal = "Udef:"+MyVar
            if type (MyTempVal) is int:
              MyTempVal = str(MyTempVal)
          except KeyError:
            print ("GetVarInArboClass => KeyError-> '"+ MyVar + "' not found")
            #print(refs["MyArbo."+MyVar])
            #print(refs)
            MyTempVal = ""
            pass
          if DoDebugGetVarInArboClass == True:
            print("GetVarInArboClass found")

          while (type(MyTempVal) is list) and (DontManageList==False):
            if DoDebugGetVarInArboClass == True:
              print("MyTempVal=")
              print(MyTempVal)
              print("MyTempVal is List...")
            if (len(MyTempVal)>0):
              if DoDebugGetVarInArboClass == True:
                print("Au moins 1 item dans la liste")
              if (len(MyVarToFetch.split(":"))>1):
                if DoDebugGetVarInArboClass == True:
                  print("Un élément est sélectionné")
                if (MyVarToFetch.split(":"))[1]=="*":
                  if DoDebugGetVarInArboClass == True:
                    print("Select item = MySession")
                  FoundVal=-1
                  CurVal=0
                  for Val in MyTempVal:
                    if int(Val[0])==MySession:
                      FoundVal=CurVal
                    CurVal+=1
                  if FoundVal>-1:
                    MyTempVal=MyTempVal[FoundVal]
                    if DoDebugGetVarInArboClass == True:
                      print("Un item == MySession dans la liste ==> MyTempVal=MyTempVal[FoundVal]")
                    if (len(MyVarToFetch.split(":"))>2):
                      if DoDebugGetVarInArboClass == True:
                        print("Un sous-élément est sélectionné")
                      MyTempVal=MyTempVal[int((MyVarToFetch.split(":"))[2])-1]
                  else:
                    MyTempVal=""
                    if DoDebugGetVarInArboClass == True:
                      print("Aucun item == MySession dans la liste ==> MyTempVal=''")
                else:
                  if DoDebugGetVarInArboClass == True:
                    print("Select item = " + str((MyVarToFetch.split(":"))[1]))
                  MyTempVal=MyTempVal[int((MyVarToFetch.split(":"))[1])-1]
                  if (len(MyVarToFetch.split(":"))>2):
                    if DoDebugGetVarInArboClass == True:
                      print("Un sous-élément est sélectionné")
                    MyTempVal=MyTempVal[(MyVarToFetch.split(":"))[2]-1]
              else:
                if DoDebugGetVarInArboClass == True:
                  print("Aucun élément de la liste n'est sélectionné ==> MyTempVal = MyTempVal[0]")
                MyTempVal = MyTempVal[0]
            else:
              MyTempVal=""
              if DoDebugGetVarInArboClass == True:
                print("Aucun item dans la liste => MyVal = ''")
          if DoDebugGetVarInArboClass == True:
            print("MyTempVal retourné : ")
            print(MyTempVal)
          return MyTempVal
          
        def SetMessage(self,MyMessage, MyBeep, Immediate=False):
          if Immediate==True:
            print("SetMessage("+MyMessage+",Immediate)")
            return ((CHAR_US+"00"+ CHAR_CAN + CHAR_ESC + "T " + MyMessage + CHAR_VTAB).encode('utf-8')) # Hello
            # _RcvQueue
          else:
            if MyMessage == CHAR_COFF or MyMessage == CHAR_CON:
              if MyMessage == CHAR_COFF :
                print("SetMessage(COFF)")
              elif MyMessage == CHAR_CON :
                print("SetMessage(CON)")
              self.InsertBytes += MyMessage.encode('utf-8') 
            else:
              print("SetMessage("+MyMessage+")")
              self.InsertBytes += (CHAR_US+"00"+ CHAR_CAN + CHAR_ESC + "T " + MyMessage + CHAR_VTAB).encode('utf-8') # Hello
            if (MyBeep==True):
              self.InsertBytes += (CHAR_BEEP).encode('utf-8')


    def CalcPostBytes():                        
        for MyVar in MyArbo.VarList :
          MyTempStr=CHAR_US + chr(64+MyVar[VAR_POSV])+chr(64+MyVar[VAR_POSH])    # Positionnement au début
          for Attrib in MyVar[VAR_ATTRIBS]:                                      # Ajout de chaque attribut défini
            MyTempStr += CHAR_ESC
            MyTempStr += Attrib
          MyTempVal=MyArbo.GetVarInArboClass(MyVar[VAR_NAME])
          if type (MyTempVal) is str:
            MyTempVal=MyTempVal.encode('utf-8')
          # Optimisations possibles si len(MyTempVal = 0)
          MyArbo.InsertPostBytes.extend (MyTempStr.encode('utf-8'))
          if (MyVar[VAR_SIZE]>0) or (len(MyVar[VAR_FILL])>0):
            MyArbo.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            if MyVar[VAR_SIZE]>3:
              Repet=MyVar[VAR_SIZE]-1
              while Repet > 0:
                MyArbo.InsertPostBytes.extend (CHAR_REP.encode('utf-8'))
                if Repet < 64 :
                  MyArbo.InsertPostBytes.extend (chr(64+Repet).encode('utf-8'))
                  Repet = 0
                else :
                  MyArbo.InsertPostBytes.extend (chr(64+63).encode('utf-8'))
                  Repet -= 63
            else:
              if MyVar[VAR_SIZE]==3:
                MyArbo.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
              MyArbo.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            MyArbo.InsertPostBytes.extend (MyTempStr.encode('utf-8'))                
          MyArbo.InsertPostBytes.extend (MyTempVal)

    def CalcDisplayList():
      if len(MyArbo.DisplayList) :
        MyList=MyArbo.GetVarInArboClass(MyArbo.DisplayList[LIST_NAME],True)
        MyNbLin=MyArbo.DisplayList[LIST_NB_LIN]          # Définition des champs de la liste
        MyNbCol=MyArbo.DisplayList[LIST_NB_COL]          # Définition des champs de la liste
        MyFirstLin=MyArbo.DisplayList[LIST_FIRST_LIN]    # Définition des champs de la liste
        MyFirstCol=MyArbo.DisplayList[LIST_FIRST_COL]    # Définition des champs de la liste
        MySizeCol=MyArbo.DisplayList[LIST_SIZE_COL]      # Définition des champs de la liste
        MyDefs=MyArbo.DisplayList[LIST_DEFS]             # Définition des champs de la liste
        MyFill1=MyArbo.DisplayList[LIST_FILL_1]          # Définition des champs de la liste
        MyAttr1=MyArbo.DisplayList[LIST_ATTR_1]          # Définition des champs de la liste
        MyFill2=MyArbo.DisplayList[LIST_FILL_2]          # Définition des champs de la liste
        MyAttr2=MyArbo.DisplayList[LIST_ATTR_2]          # Définition des champs de la liste
        
        MyItemsPerPage=MyNbLin*MyNbCol
        if MyItemsPerPage>0:
          MyNbPage=len(MyList)//MyItemsPerPage
        else:
          MyNbPage=1    # La liste n'est pas affichée - Il n'y a pas de nombre de pages mais il y en a forcément une quand même 
          
        if MyArbo.PageDisplayList < 0:
          MyArbo.PageDisplayList = 0
        if MyArbo.PageDisplayList > MyNbPage:
          MyArbo.PageDisplayList=MyNbPage
        MyArbo.NumPageDisplayList = (str(MyArbo.PageDisplayList+1)).encode('utf-8')
        MyArbo.NumPagesDisplayList= (str(MyNbPage+1)).encode('utf-8')
        if DoDebugList == True:
          print("Values in '" + MyArbo.DisplayList[LIST_NAME] + "'=")
          print(MyList)
          print("NbLin:" + str(MyNbLin) + " NbCol:" + str(MyNbCol) + " FirstLin:" + str(MyFirstLin) + " FirtstCol:" + str(MyFirstCol) + " SizeCol:" + str(MySizeCol))
          print("NbPage:" + str(MyNbPage) + " CurPage:" + str(MyArbo.PageDisplayList) + " ItemPerPage:" + str(MyItemsPerPage))
        if len(MyFill1) >0 :
          for ItemLin in range (0,MyNbLin):
            MyArbo.InsertPostBytes.extend ((CHAR_US + chr(64+MyFirstLin+ItemLin)+chr(64+MyFirstCol)).encode('utf-8'))
            for Attrib in MyAttr1:                                # Ajout de chaque attribut défini
              MyArbo.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
            if ItemLin == 0:
              MyArbo.InsertPostBytes.extend (MyFill1.encode('utf-8'))
            MyArbo.InsertPostBytes.extend (CHAR_REP.encode('utf-8'))
            if ItemLin == 0:
              MyArbo.InsertPostBytes.extend (chr(64+MySizeCol*MyNbCol-1).encode('utf-8'))
            else:
              MyArbo.InsertPostBytes.extend (chr(64+MySizeCol*MyNbCol).encode('utf-8'))
        MyCountItem = 0
        MyArbo.CurrentListDefs=MyDefs
        MyArbo.CurrentList=[]
        SizeItem=0
        for MyDef in MyDefs :
          if DoDebugList == True:
            print(MyDef)
          SizeItem += MyDef[LIST_DEF_COLS]
        for ItemCol in range(0,MyNbCol):
          for ItemLin in range (0,MyNbLin):
            CurItem=((MyArbo.PageDisplayList*MyItemsPerPage)+(ItemCol*MyNbLin)+ItemLin)
            if len (MyList)>CurItem and len(MyDefs)>0 :
              MyArbo.CurrentList.append (MyList[CurItem])
              if SizeItem ==0 :
                if DoDebugList == True:
                  print("NoItemToDisplay")
                # Aucun champ n'est à afficher
                #pass
              else:
                MyArbo.InsertPostBytes.extend ((CHAR_US + chr(64+MyFirstLin+ItemLin) + chr(64+MyFirstCol+MySizeCol*ItemCol)).encode('utf-8'))
                for Attrib in MyAttr2:                                # Ajout de chaque attribut défini
                  MyArbo.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
                if DoDebugList == True:
                  print("MyCountItem (index in the display):" + str(MyCountItem))
                  print("ItemInTheList:"+str(CurItem) + " ItemLin:" + str(ItemLin) + " ItemCol:" + str(ItemCol) + " CurItem():" + str((ItemCol*MyNbLin)+ItemLin))
                  print(MyList[CurItem])
                for MyDef in MyDefs:
                  if MyDef[LIST_DEF_ITEM] == 0:
                    MyValue=MyCountItem+1
                  else:
                    MyValue=(MyList[CurItem][MyDef[LIST_DEF_ITEM]-1])
                  if (type (MyValue) is int) :
                    MyValue = str(MyValue)
                  if DoDebugList == True:
                    print("Value:" + MyValue)
                  if len(MyValue) > MyDef[LIST_DEF_COLS]:
                    MyValue = MyValue[:MyDef[LIST_DEF_COLS]]
                  MyInsert=MyDef[LIST_DEF_SKIP]
                  while MyInsert>0:
                    MyArbo.InsertPostBytes.extend (chr(9).encode('utf-8'))
                    MyInsert -= 1
                  for Attrib in MyDef[LIST_DEF_ATTR]:                                # Ajout de chaque attribut défini
                    MyArbo.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
                  MyArbo.InsertPostBytes.extend (MyValue.encode('utf-8'))
                  if MyDef[LIST_DEF_COLS]>len(MyValue):
                    MyArbo.InsertPostBytes.extend (MyFill2.encode('utf-8'))
                    if (MyDef[LIST_DEF_COLS]-len(MyValue)) > 2:
                      MyArbo.InsertPostBytes.extend ((CHAR_REP+chr(64+MyDef[1]-len(MyValue)-1)).encode('utf-8'))
                    elif (MyDef[LIST_DEF_COLS]-len(MyValue)) == 2:
                      MyArbo.InsertPostBytes.extend (MyFill2.encode('utf-8'))
            MyCountItem += 1                    
        if DoDebugList == True:
          print(MyDefs)
          print(MyArbo.CurrentList)
          print(MyArbo.CurrentListDefs)
      #pass
  
    def GetField(MyVar,MySession):
      try:                                                   # Valeur globale
        MyTempVal = refs[refs_prefix + MyVar + "_" + str(MySession)]
      except KeyError:
        print ("KeyError-> '"+ MyVar + "_" + str(MySession) + "' not found")
        MyTempVal = ""
        pass
      if type (MyTempVal) is int:
        MyTempVal = str(MyTempVal)
      if type (MyTempVal) is str:
        MyTempVal = MyTempVal.encode('utf-8')
      print ("GetField(" + MyVar + ")=" + (MyTempVal.decode('utf8', 'strict')))
      return MyTempVal
    
    def DeclareField(MyField):
        print("DeclareField(" + MyField + ")")
        refs[refs_prefix + MyField + "_" + str(MySession)] = ""

    def FreeAllFields():
        print("FreeAllFields()")
        for key in [*refs]:
          if key[:len(refs_prefix)] == refs_prefix: 
              if key[len(key)-(len(str(MySession))+1):] == "_" + str(MySession) :
                print(key + " deleted")
                refs.pop(key)
              else :
                print(key + " kept")

    def LoadBufferInputWithCurField():
      try:
        MyArbo.BufferInput=GetField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession).decode('utf-8','strict')
        print("LoadBufferInputWithCurField(" + MyArbo.FieldList[MyArbo.CurField][FIELD_NAME]+ ")")
      except IndexError:
        print("ERR : LoadBufferInputWithCurField():IndexError")
        print("Len(MyArbo.FieldList[])="+str(len(MyArbo.FieldList)))
        print("MyArbo.CurField)="+str(MyArbo.CurField))        
        pass
      
    def UpdateField(MyVar,MySession,MyBuffer):
      print("UpdateField("  + MyVar + "," + str(MySession) + ",'" + MyBuffer + "')")
      refs[refs_prefix + MyVar + "_" + str(MySession)] = MyBuffer.encode('utf-8')
      #print(refs[refs_prefix + MyVar + "_" + str(MySession)])
    
    def UpdateCurField():
      nonlocal MySession
      
      print("UpdateCurField("  + str(MySession) + ",'" + MyArbo.BufferInput + "')")
      if len(MyArbo.FieldList) :
        UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,MyArbo.BufferInput)
        ClearBufferInput()

    def PresentFieldValue (MyVar):
      InsertPostField = bytearray()
      
      MyTempStr=CHAR_US + chr(64+MyVar[FIELD_POSV])+chr(64+MyVar[FIELD_POSH])    # Positionnement au début
      for Attrib in MyVar[FIELD_ATTRIBS]:                                        # Ajout de chaque attribut défini
        MyTempStr += CHAR_ESC
        MyTempStr += Attrib
      MyTempVal=GetField(MyVar[FIELD_NAME],MySession)                   # Valeur globale
      # Optimisations possibles si len(MyTempVal = 0)
      InsertPostField.extend (MyTempStr.encode('utf-8'))
      if (MyVar[FIELD_SIZE]>0) or (len(MyVar[FIELD_FILL])>0):
        InsertPostField.extend (MyVar[FIELD_FILL].encode('utf-8'))
        if MyVar[FIELD_SIZE]>3:
          Repet=MyVar[FIELD_SIZE]-1
          while Repet > 0:
            InsertPostField.extend (CHAR_REP.encode('utf-8'))
            if Repet < 64 :
              InsertPostField.extend (chr(64+Repet).encode('utf-8'))
              Repet = 0
            else :
              InsertPostField.extend (chr(64+63).encode('utf-8'))
              Repet -= 63
        else:
          if MyVar[FIELD_SIZE]==3:
            InsertPostField.extend (MyVar[FIELD_FILL].encode('utf-8'))
          InsertPostField.extend (MyVar[FIELD_FILL].encode('utf-8'))
        InsertPostField.extend (MyTempStr.encode('utf-8'))                
      InsertPostField.extend (MyTempVal)
      return InsertPostField

    def ClearBufferInput():
      print("ClearBufferInput()")
      MyArbo.BufferInput = ""
      
    
    def AddItemToBufferNoRomRamNoLog(item):
        nonlocal BufferEcho

        if len(MyArbo.BufferInput)>2:
          if (ord(MyArbo.BufferInput[-1:])==ord(CHAR_SS2.encode('utf-8'))) and (chr(ord(item)) in CHAR_ACCENT_LIST) :
            if (ord(MyArbo.BufferInput[-3:-2])==ord(CHAR_SS2.encode('utf-8'))) and (chr(ord(MyArbo.BufferInput[-2:-1])) in CHAR_ACCENT_LIST) :
              MyArbo.BufferInput=MyArbo.BufferInput[:-2]
        MyArbo.BufferInput+=item
        if DoEchoBufferInput == True:
          BufferEcho += item
    
    def AddItemToBufferNoRomRam(item):
        #
        # Ici, le traitement ROM/RAM a déjà été effectué - Ne bufferise pas [RC] ni [ESC] (mais accepte les autres codes de contrôle)
        #
        if item >= ' ':
            MyArbo.DebugInput += item
            AddItemToBufferNoRomRamNoLog(item)
        else:
            if item == CHAR_RC:
                MyArbo.DebugInput += "[RC]"
                # Prevoir traitement de [RC] comme [ENVOI]
            elif item == CHAR_ESC:
              MyArbo.DebugInput += "[ESC]"
            else:
                AddItemToBufferNoRomRamNoLog(item)
                MyArbo.DebugInput += "<0x{:02x}> ".format(ord(item))


    async def _recv_with_timeout(self, websocket,MyTask):
      temp=None
      try:
        if not websocket.closed:
          if DoDebugAsync == True: 
            print("_recv_with_timeout() start")
          #self._RcvQueue.put_nowait(await websocket.recv())
          temp=await websocket.recv()
          if DoDebugAsync == True: 
            print("_recv_with_timeout() done")
        else:
          if DoDebugAsync == True: 
            print("_recv_with_timeout() closed")
      except asyncio.CancelledError:
        if  (DoDebugAsync) == True: 
          print("_recv_with_timeout() [cancelled]")
        #pass
        raise
      except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
        if DoDebugAsync == True: 
          print("_recv_with_timeout() cancelled [ClosedOK or ClosedError]")
        raise
      except : #asyncio.CancelledError:
        print("_recv_with_timeout() cancelled [not (ClosedOK or ClosedError)]")
        print ("ERR:await _recv_with_timeout() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
      return (temp)
      
    async def _msg_with_timeout(self, websocket,MyTask):
      temp=None
      try:
        if not websocket.closed:
          if DoDebugAsync == True: 
            print("_msg_with_timeout() start")
          #self._RcvQueue.put_nowait(await websocket.recv())
          temp = await self._RcvQueue.get()
          if DoDebugAsync == True: 
            print("_msg_with_timeout() done")
        else:
          if DoDebugAsync == True: 
            print("_msg_with_timeout() closed")
      except asyncio.CancelledError:
        if  (DoDebugAsync) == True: 
          print("_msg_with_timeout() [cancelled]")
        #pass
        raise
      except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
        if DoDebugAsync == True: 
          print("_msg_with_timeout() cancelled [ClosedOK or ClosedError]")
        raise
      except : #asyncio.CancelledError:
        print("_msg_with_timeout() cancelled [not (ClosedOK or ClosedError)]")
        print ("ERR:await _msg_with_timeout() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
      return (temp)

    async def _timer_with_timeout(self, websocket,MyTask):
      temp=None
      try:
        if not websocket.closed:
          if (DoDebugTimer==True) or (DoDebugAsync) == True: 
            print("_timer_with_timeout() start")
          #self._RcvQueue.put_nowait(await websocket.recv())
          temp = await asyncio.sleep(self.TimerDelay)
          if (DoDebugTimer==True) or (DoDebugAsync) == True: 
            print("_timer_with_timeout() done")
        else:
          if (DoDebugTimer==True) or (DoDebugAsync) == True: 
            print("_timer_with_timeout() closed")
      except asyncio.CancelledError:
        if (DoDebugTimer==True) or (DoDebugAsync) == True: 
          print("_timer_with_timeout() [cancelled]")
        #pass
        raise
      except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
        if (DoDebugTimer==True) or (DoDebugAsync) == True: 
          print("_timer_with_timeout() cancelled [ClosedOK or ClosedError]")
        raise
      except : #asyncio.CancelledError:
        print("_timer_with_timeout() cancelled [not (ClosedOK or ClosedError)]")
        print ("ERR:await _timer_with_timeout() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
      return (temp)

      
    def AddItemToBuffer(item):
        #nonlocal MyArbo
        nonlocal ReplyRomRamIndex,ReplyRomRam,ReplyRomRamPending
        #nonlocal ReplyRomRamExpect,GotRom,GotRam1,GotRam2
        
        if MyArbo.ReplyRomRamExpect > 0 :      # Si on prévoit de recevoir ROM/RAM
           if item == CHAR_SOH :                            # On se prépare à recevoir des éléments de ROM/RAM
             MyArbo.DebugInput += "[SOH]"
             ReplyRomRamPending = True                      # Les prochains caractères reçus seront des éléments de ROM/RAM
             ReplyRomRamIndex = 0                           # On n'en a encore reçus aucun
             if ReplyRomRam == 0 :                          # On attends ROM
               MyArbo.GotRom = bytearray()
             elif ReplyRomRam == 1 :                        # On attends RAM1
               MyArbo.GotRam1 = bytearray()
             elif ReplyRomRam == 2 :                        # On attends RAM2
               MyArbo.GotRam2 = bytearray()
           elif ReplyRomRamPending == True :                # Si on est en cours de réception d'éléments de ROM/RAM
               ReplyRomRamIndex = ReplyRomRamIndex + 1      # Noter qu'un de plus est reçu
               if (item == CHAR_EOT) or (ReplyRomRamIndex == 16):             # fin de ROM/RAM ou Taille maximale reçue
                 MyArbo.DebugInput += "[EOT/EndOfRomRam]"
                 ReplyRomRamPending = False                 # On ne reçoit plus RAM/ROM
                 MyArbo.ReplyRomRamExpect = MyArbo.ReplyRomRamExpect - 1  # Une ROM/RAM attendue en moins
                 ReplyRomRam = ReplyRomRam + 1              # Au cas où, on se prépare pour attendre le prochain ROM/RAM
               if item != CHAR_EOT :                        # Ne pas stocker EOT
                 # Mémoriser le caractère reçu
                 MyArbo.DebugInput += item
                 if ReplyRomRam == 0 :                      # Attends ROM
                   MyArbo.GotRom += item.encode('utf-8')
                 elif ReplyRomRam == 1 :                    # Attends RAM1
                   MyArbo.GotRam1 += item.encode('utf-8')
                 elif ReplyRomRam == 2 :                    # Attends RAM2
                   MyArbo.GotRam2 += item.encode('utf-8')
               if ReplyRomRamPending == False :
                 # Juste pour débugage
                 if ReplyRomRam == 1 :                      # Attendait ROM
                   print("Updated ROM {}".format(MyArbo.GotRom))
                 elif ReplyRomRam == 2 :                    # Attendait RAM1
                   print("Updated RAM1 {}".format(MyArbo.GotRam1))
                 elif ReplyRomRam == 3 :                    # Attendait RAM2
                   print("Updated RAM2 {}".format(MyArbo.GotRam2))
           else :                                           # On n'est pas en cours de réception d'éléments de ROM/RAM
             AddItemToBufferNoRomRam(item)
        else :              # On ne s'attend pas à reçevoir ROM/RAM
          AddItemToBufferNoRomRam(item)
        
    DeclareField("Text01")
    #
    # Définition de la racine de l'arborescence - Prépare l'objet correspondant
    #
    MyArbo = Arbo("arbo",asyncio.get_event_loop())
    #
    # Arrivée sur la première page de l'arborescence
    #
    MyArbo.SetArbo("arbo_start")
    #
    # Demande le détail du contenu ROM/RAM et prépare leur réception
    #
    MyArbo.InsertBytes += (CHAR_ESC + CHAR_PRO1 + "{"+ CHAR_ENQ + CHAR_ESC + CHAR_PRO1 + "z").encode('utf-8') # ENQROM + ENQ RAM1 + ENQ RAM2
    MyArbo.ReplyRomRamExpect = 3 # Attends 3 items ROM/RAM
    ReplyRomRam = 0       # Attends ROM
    ReplyRomRamIndex = 0  # Aucun caractère reçu
    CHAR_BEEP=b'\x07\x00\x81\xff'
    #await websocket.send(b'\x07\x00\x81\xff)ABCDEF\x00\x00')
    #b=CHAR_BEEP.encode('utf-8').decode('utf-8','strict')
    #await websocket.send(b)
    await websocket.send(CHAR_BEEP)
    await websocket.send(f"Connected * to {path} !")
    #await websocket.send("String ---1234567890".decode('utf-8'))
    print ("SERVER START {}".format(path))
    while MyArbo.GotLib==False:
        if MyArbo.DoSendPage==True:
            #
            # La page complete est a envoyer
            #
            # Rafraichissement et mise en forme de tous les types de variables à afficher, tel que défini dans l'arborescence 
            #
            MyArbo.InsertPostBytes=bytearray()  # Recalculer la liste, les variables, et les champs qui seront a afficher apres la page
            CalcDisplayList()                   # Preparer en premier la partie de liste a afficher
            MyArbo.NumPageVdt  = str(MyArbo.CurFile-MyArbo.FirstFile + 1).encode('utf-8')            # Numéro affichable de la page dans la séquence (MAJ de la variable avant son affichage !)
            CalcPostBytes()                     # Preparer ensuite les variables a afficher                 
            #
            # Rafraichissement et mise en forme des champs à afficher, le champ en cours de saisie en dernier, tel que défini dans l'arborescence 
            #
            MyArbo.InsertPostField=bytearray()
            # Commencer par les champs qui ne sont pas en cours de saisie
            CountField = 0
            for MyVar in MyArbo.FieldList :
              if CountField != MyArbo.CurField :
                MyArbo.InsertPostField.extend (PresentFieldValue(MyVar))
              CountField = CountField + 1
            # Puis le champ en cours de saisie
            if len(MyArbo.FieldList) >0 :    # Si au moins 1 champ 
              MyArbo.InsertPostField.extend (PresentFieldValue(MyArbo.FieldList[MyArbo.CurField]))
              MyArbo.InsertPostField.extend (CHAR_CON.encode('utf-8')) # Curseur ON 
            # Enfin, charger la page    
            try:
                page=GetPage(MyArbo.PageDir + MyArbo.PrefixFile + str(MyArbo.CurFile) + MyArbo.PostfixFile)
                print(type(page))
                print(f"SERVER SENT FILE '{MyArbo.PrefixFile+str(MyArbo.CurFile)+MyArbo.PostfixFile}'")
            except:
                page=bytearray(chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1]),'utf-8')     #+chr(10)+chr(13)+str(sys.exc_info()[2])
                #page=(chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1])).encode('utf-8')  #+chr(10)+chr(13)+str(sys.exc_info()[2])
                print ("ERR:Hello().GetPage() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                MyArbo.CurFile=MyArbo.FirstFile
                pass
            #
            # Envoi de la page
            #
            try:
              if not websocket.closed:
                # await websocket.send(MyArbo.InsertBytes) # + page)
                #await websocket.send((MyArbo.InsertBytes + page + MyArbo.InsertPostBytes + MyArbo.InsertPostField).decode('utf-8','strict'))
                await websocket.send((MyArbo.InsertBytes + page + MyArbo.InsertPostBytes + MyArbo.InsertPostField))
              else:
                MyArbo.GotLib=True
            except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
              if DoDebugAsync == True: 
                print("DoSendPage cancelled [ClosedOK or ClosedError]")
              MyArbo.GotLib=True
              pass
            MyArbo.InsertBytes = bytearray()                   # Clear possible previous page content prefix
            print("MyArbo.InsertBytes cleared [DoSendPage]")
            MyArbo.DoSendPage=False                            # La page a ete envoyee, pas besoin de la re-afficher au prochain passage de la boucle, sauf si demande
            MyArbo.RefreshCurField=False                       # Le champ en cours ete envoye, pas besoin de le re-afficher au prochain passage de la boucle, sauf si demande

        if MyArbo.RefreshCurField==True :
          #
          # La page complete n'est pas a envoyer, seulement le champ en cours
          #
          MyArbo.RefreshCurField=False                         # Le champ en cours ete envoye, pas besoin de le re-afficher au prochain passage de la boucle, sauf si demande
          if len(MyArbo.FieldList) >0 :                        # Si au moins 1 champ est defini 
            #
            # Rafraichissement et mise en forme des champs à afficher, le champ précédent puis le champs en cours de saisie, tel que défini dans l'arborescence 
            #                                                              
            MyArbo.InsertPostField=bytearray()                 # Recalculer le(s) champ(s) à afficher
            # Champ précédement en cours de saisie
            if DoRefreshPrevField == True :                    # Optionnellement, ré-afficher le champ dont on vient de partir 
              if MyArbo.PrevField >= 0:                        # Si le "champ précédent" est défini
                MyArbo.InsertPostField.extend (PresentFieldValue(MyArbo.FieldList[MyArbo.PrevField]))
              MyArbo.PrevField = -1                            # Ne pas ré-afficher le champ precedent au prochain passage, sauf si demande
            # Champ en cours de saisie
            MyArbo.InsertPostField.extend (PresentFieldValue(MyArbo.FieldList[MyArbo.CurField]))
            MyArbo.InsertPostField.extend (CHAR_CON.encode('utf-8')) # Curseur ON           
            #
            # Envoi du champ seul
            #
            try:
              if not websocket.closed:
                await websocket.send((MyArbo.InsertBytes + MyArbo.InsertPostField).decode('utf-8','strict'))
              else:
                MyArbo.GotLib=True
            except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
              MyArbo.GotLib=True
              if DoDebugAsync == True: 
                print("RefreshCurField cancelled [ClosedOK or ClosedError]")
              pass

            MyArbo.InsertBytes = bytearray()                 # Clear possible previous page content prefix
            print("MyArbo.InsertBytes cleared [RefreshCurField]")
        #
        #      Echo des caractères saisis - Ca marche parce qu'une page ou un champ seul ne peuvent être (ré)affichés que sur demande (touche de fonction reçue)
        #      --> Le buffer a donc été envoyé en echo au pécédent passage et pris en compte
        #      --> Seuls cas douteux : action de (ré)affichage sur évènements Timeout, Timer ou Msg
        #      --> L'écho pourrait facilement être masqué au besoin (attention aux accents) 
        #
        if len(BufferEcho) :
          try:
            if not websocket.closed:
              await websocket.send((BufferEcho.encode('utf-8')).decode('utf-8','strict'))
            else:
              MyArbo.GotLib=True
          except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
            MyArbo.GotLib=True
            if DoDebugAsync == True: 
              print("BufferEcho cancelled [ClosedOK or ClosedError]")
            pass
          BufferEcho=""          
        #
        # Prends en compte les changements de timer dans SetArbo()
        #
        if MyArbo.TimerChanged==True:
          MyArbo.TimerChanged=False
          if len(MyArbo._tasks) >2:    # Mais il y avait un timer actif avant SetArbo
            MyArbo._tasks[2].cancel()  # Supprimer la tâche Timer 
            del MyArbo._tasks[2]
            if DoDebugTimer==True:
              print("SetArbo() Timer cancelled for "+str(MyArbo.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
              z=asyncio.all_tasks()
              print("Timer => all_tasks ="+str(len(z))+".")
              cnt=0
              for zz in z:
                cnt+=1
                print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                print(zz.get_stack(limit=3))
            #while self._tasks[2].cancelled() == False:
          else:
            if DoDebugTimer==True:
              print("SetArbo() No timer to cancel for "+str(MyArbo.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
            pass          
          #
          # Mets un nouveau timer 
          #
          if MyArbo.TimerDelay>0:      # Il y a maintenant un Timer actif
            print(MyArbo._tasks.append(MyArbo.loop.create_task(_timer_with_timeout(MyArbo,websocket,2))))
            if DoDebugTimer==True:
              print("SetArbo() Timer created for "+str(MyArbo.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
              z=asyncio.all_tasks()
              print("Timer => all_tasks ="+str(len(z))+".")
              cnt=0
              for zz in z:
                cnt+=1
                print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                print(zz.get_stack(limit=3))
          else:
            if DoDebugTimer==True:
              print("SetArbo() No timer to create for "+str(MyArbo.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")          
        #
        # Attends un évènement RawReceived, MsgReceived, TimerReceived, ou Timeout
        #
        try:
          keep_waiting: bool = True
          TimeOut=0         
          RawReceived=None
          MsgReceived=None
          TimerReceived=None

          if DoDebugTimer==True:
              print("SetArbo() Timer keepwaiting for "+str(MyArbo.TimerDelay)+"secs  --- Before all_tasks ="+str(len(asyncio.all_tasks()))+".")
              z=asyncio.all_tasks()
              print("Timeout => all_tasks ="+str(len(z))+".")
              cnt=0
              for zz in z:
                cnt+=1
                print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                print(zz.get_stack(limit=3))
          
          # https://hynek.me/articles/waiting-in-asyncio/
          #print("Debut de KeepWaiting "+str(len(MyArbo._tasks))+" tasks")
          try:
              while keep_waiting and (not MyArbo.websocket.closed):
                  try:
                      if DoDebugAsync == True: 
                        print("asyncio.wait started "+str(len(MyArbo._tasks)) + " tasks - all_tasks = ("+str(len(asyncio.all_tasks()))+")")
                      done, pending = await asyncio.wait(MyArbo._tasks, timeout=1, return_when=asyncio.FIRST_COMPLETED)
                      if DoDebugAsync == True: 
                        print("asyncio.wait done")
                      if len(done)>0:                    # Au moins une tache terminee -> C'est pas un timeout
                        if MyArbo._tasks[0] in done:     # Un caractere est recu (au moins)
                          RawReceived=MyArbo._tasks[0].result()  # Noter le(s) caractere(s) recu(s)
                          if DoDebugAsync == True: 
                            print("Got valid data in RawReceived from _recv_with_timeout() ==> Keep waiting = False")
                          MyArbo.TimeoutCount=0          # Reset du timeout
                          keep_waiting=False             # Sortir de la boucle
                          if not websocket.closed:       # Relancer la tache (si on est toujours connectés)
                            MyArbo._tasks[0]=asyncio.create_task(_recv_with_timeout(MyArbo,websocket,0))
                        if MyArbo._tasks[1] in done:     # Un message est recu
                          MsgReceived=MyArbo._tasks[1].result()  # Noter le message
                          if DoDebugAsync == True: 
                            print("Got valid data in MsgReceived from _msg_with_timeout() ==> Keep waiting = False")
                          #MyArbo.TimeoutCount=0         # N'impacte pas le timeout
                          keep_waiting=False             # Sortie de la boucle
                          if not websocket.closed:       # Relancer la tache (si on est toujours connectés)
                            MyArbo._tasks[1]=asyncio.create_task(_msg_with_timeout(MyArbo,websocket,1))
                        if len(MyArbo._tasks)>2:         # Si une tache timer existe
                          if MyArbo._tasks[2] in done:   # Un timer est recu
                            TimerReceived=True           # Noter l'évènement
                            if DoDebugAsync == True: 
                              print("Got valid data in TimerReceived from _timer_with_timeout() ==> Keep waiting = False")
                            #MyArbo.TimeoutCount=0        # N'impacte pas le timeout
                            keep_waiting=False            # Sortie de la boucle
                            if not websocket.closed:      # Relancer la tache (si on est toujours connectés)
                              MyArbo._tasks[2]=asyncio.create_task(_timer_with_timeout(MyArbo,websocket,1))
                      else:                               # Aucune tache terminee -> une seconde est passee et on est sorti du wait par timeout
                        TimeOut+=1                        # Une seconde de plus est notée
                        if (TimeOut>=MyArbo.TimeoutLimit) and (MyArbo.TimeoutLimit>0):  # Si le delais de timeout est valide et atteint
                          keep_waiting=False              # Sortie de la boucle
                          if DoDebugAsync == True:        # 
                            print("Got TimeOut ["+str(TimeOut)+"] from _timeout_for_recv()  ==> Keep waiting = False, RawReceived=None, MsgReceived=None, TimerReceived=None")
                            z=asyncio.all_tasks()
                            print("Timeout => all_tasks ="+str(len(z))+".")
                            cnt=0
                            for zz in z:
                              cnt+=1
                              print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                              print(zz.get_stack(limit=3))
                        else:                              # Delais de timeout invalide ou pas atteint
                          if DoDebugAsync == True: 
                            print("Got TimeOut ["+str(TimeOut)+"] from _timeout_for_recv()  ==> Keep waiting = True")
                          keep_waiting=True                # On reste dans la boucle

                  except asyncio.TimeoutError:             # Inucile ?
                      if DoDebugAsync == True: 
                        print("asyncio.TimeoutError : no message in {} seconds".format(MyTimeOut))
                      raise asyncio.TimeoutError
                  except asyncio.CancelledError:
                      if DoDebugAsync == True: 
                        print("asyncio.cancelled error")
                      raise asyncio.CancelledError
                  finally:
                      if DoDebugAsync == True: 
                        print("finally asyncio.wait")
                      #for t in MyArbo.tasks:
                      #    t.cancel()
                      #keep_waiting = False  
                      if str(sys.exc_info()[0])!="None":
                        print ("ERR:await asyncio.wait() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                        err=sys.exc_info()
                        for item in err:
                          print(item)

          except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
            MyArbo.GotLib=True
            if DoDebugAsync == True: 
              print("RawReceived cancelled [ClosedOK or ClosedError]")
            pass
          except Exception as e:
              MyArbo.GotLib=True
              print('ws exception:{}'.format(e))
              #keep_waiting = False          
                       
          #print("Fin de KeepWaiting")
          if RawReceived != None:
            #RawReceived = await websocket.recv()
            # https://stackoverflow.com/questions/45229304/await-only-for-some-time-in-python
            # https://stackoverflow.com/questions/37663560/websocket-recv-never-returns-inside-another-event-loop
            # https://stackoverflow.com/questions/54421029/python-websockets-how-to-setup-connect-timeout
            for item in RawReceived:        # Analyse le paquet reçu
                if item == CHAR_ESC:        # Annonce une sequence ESC
                    GotEsc=True
                else:
                    if GotEsc==True:        # Traitement d'une sequence ESC reçue
                        if item == CHAR_PRO1:   # Annonce une sequence PRO1
                            GotEsc=False
                        if item == CHAR_PRO2:   # Annonce une sequence PRO2
                            GotEsc=False
                        if item == CHAR_PRO3:   # Annonce une sequence PRO3
                            GotEsc=False
                        if GotEsc == False:     # Annonce une sequence protocole
                            GotProSeq = (ord(item) - ord(CHAR_PRO1))+1
                            ProtocolSeq = ""
                            MyArbo.DebugInput += "<PRO{}> ".format(GotProSeq)
                        else:
                            GotEsc=False
                            if item == CHAR_CSI:
                                GotCsi = True
                                GotCsiSeq = ""
                            else:
                                AddItemToBuffer(CHAR_ESC)
                                AddItemToBuffer(item)       # Ici, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                    else:                               # On n'est pas dans le traitement d'une sequence ESC reçue
                        if GotProSeq > 0:               # On est dans le traitement d'une sequence protocole
                            ProtocolSeq += item         # Ici aussi, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                            GotProSeq -=1
                            if GotProSeq == 0:
                                MyArbo.BufferInput+=CHAR_ESC
                                MyArbo.BufferInput+=chr(ord(CHAR_PRO1)+len(ProtocolSeq)-1)
                                for item in ProtocolSeq:
                                    MyArbo.BufferInput+=item
                                    MyArbo.DebugInput += "<0x{:02x}> ".format(ord(item))
                        else:                       # On n'est pas dans le traitement d'une sequence protocole reçue
                            if GotCsi == True:
                                GotCsiSeq += item         # Ici aussi, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                                if ord(item) >= 0x40:
                                    GotCsi = False
                                    MyArbo.BufferInput+=CHAR_ESC
                                    MyArbo.BufferInput+=CHAR_CSI
                                    MyArbo.DebugInput += "[CSI]"
                                    for item in GotCsiSeq:
                                        AddItemToBuffer(item)
                            else:
                                if item == CHAR_SEP:    # Annonce une touche de fonction
                                    GotSep=True
                                else:
                                    if GotSep==True:    # Traitement d'une touche de fonction reçue
                                        if item == CHAR_ENVOI:
                                            GotSep=False
                                            MyArbo.DebugInput += "[ENVOI]"
                                            UpdateCurField()              # Met à jour le champ en cours avec BufferInput puis vide BufferInput 
                                            LoadBufferInputWithCurField() # Charge BufferInput avec le champ en cours
                                            MyArbo.CallModule('envoi',"Comment Envoi")
                                                
    #
    # https://stackoverflow.com/questions/1450275/any-way-to-modify-locals-dictionary
    #
    #    refs    = locals()
    #    def set_pets():
    #        global refs
    #        animals = ('dog', 'cat', 'fish', 'fox', 'monkey')
    #        for i in range(len(animals)):
    #            refs['pet_0%s' % i] = animals[i]   
    #    set_pets()
    #    refs['pet_05']='bird'
    #    print(pet_00, pet_02, pet_04, pet_01, pet_03, pet_05 )
    #    >> dog fish monkey cat fox bird
    #And if you want to test your dict before putting it in locals():
    #
    #def set_pets():
    #    global refs
    #    sandbox = {}
    #    animals = ('dog', 'cat', 'fish', 'fox', 'monkey')
    #    for i in range(len(animals)):
    #        sandbox['pet_0%s' % i] = animals[i]
    #    # Test sandboxed dict here
    #    refs.update( sandbox )
                                        if item == CHAR_SUITE:
                                            GotSep=False
                                            MyArbo.DebugInput += "[SUITE]"
                                            #
                                            # Traitement des séquences de pages
                                            #
                                            if MyArbo.CurFile==MyArbo.LastFile:
                                                if MyArbo.CurFile==MyArbo.FirstFile:
                                                    MyArbo.DebugInput += "$OnlyOnePage$"
                                                else:
                                                    MyArbo.CurFile=MyArbo.FirstFile
                                                    MyArbo.DoSendPage=True
                                            else:
                                                MyArbo.DoSendPage=True
                                                MyArbo.CurFile+=1
                                            #
                                            # Traitement des listes de champs
                                            #
                                            if (MyArbo.CurField+1)>len(MyArbo.FieldList):
                                              MyArbo.DebugInput += "$NoField$"
                                            elif (MyArbo.CurField+1)==len(MyArbo.FieldList):
                                              if len(MyArbo.FieldList)==1:
                                                MyArbo.DebugInput += "$OnlyOneField$"
                                              else:
                                                UpdateCurField()
                                                MyArbo.PrevField=MyArbo.CurField
                                                MyArbo.RefreshCurField=True
                                                MyArbo.CurField=0
                                                LoadBufferInputWithCurField()
                                            else:
                                              UpdateCurField()
                                              MyArbo.PrevField=MyArbo.CurField
                                              MyArbo.RefreshCurField=True
                                              MyArbo.CurField+=1
                                              LoadBufferInputWithCurField()
                                            #
                                            # Traitement des listes
                                            #
                                            if len(MyArbo.DisplayList) :
                                              MyArbo.PageDisplayList += 1
                                            #
                                            # Traiteent des modules
                                            #
                                            MyArbo.CallModule('suite',"Comment Suite")
    
                                             
                                        if item == CHAR_RETOUR:
                                            GotSep=False
                                            MyArbo.DebugInput += "[RETOUR]"
                                            #
                                            # Traitement des séquences de pages
                                            #
                                            if MyArbo.CurFile==MyArbo.FirstFile:
                                                if MyArbo.CurFile==MyArbo.LastFile:
                                                    MyArbo.DebugInput += "$OnlyOnePage$"
                                                else:
                                                    MyArbo.CurFile=MyArbo.LastFile
                                                    MyArbo.DoSendPage=True
                                            else:
                                                MyArbo.DoSendPage=True
                                                MyArbo.CurFile-=1
                                            #
                                            # Traitement des listes de champs
                                            #
                                            if (MyArbo.CurField+1)>len(MyArbo.FieldList):
                                              MyArbo.DebugInput += "$NoField$"
                                            elif len(MyArbo.FieldList)==1:
                                                MyArbo.DebugInput += "$OnlyOneField$"
                                            else:
                                              UpdateCurField()
                                              MyArbo.RefreshCurField=True
                                              MyArbo.PrevField=MyArbo.CurField
                                              if MyArbo.CurField >0:
                                                  MyArbo.CurField-=1
                                                  LoadBufferInputWithCurField()
                                              else:
                                                  MyArbo.CurField=len(MyArbo.FieldList)-1
                                                  LoadBufferInputWithCurField()
                                            #
                                            # Traitement des listes
                                            #
                                            if len(MyArbo.DisplayList) :
                                              MyArbo.PageDisplayList -= 1
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('retour',"Comment Retour")
                                            
                                        if item == CHAR_REPETITION:
                                            GotSep=False
                                            MyArbo.DebugInput += "[REPETITION]"
                                            MyArbo.DoSendPage=True
                                        if item == CHAR_CORRECTION:
                                            GotSep=False
                                            MyArbo.DebugInput += "[CORRECTION]"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(MyArbo.FieldList):
                                              Cont=True
                                              Removed = False
                                              while (Cont == True) :
                                                #print("<0x{:02x}> ".format(ord(BufferInput[-2:-1])))
                                                if (Cont == True) and (len(MyArbo.BufferInput) > 1) and (ord(MyArbo.BufferInput[-2:-1]) == ord(CHAR_SS2.encode('utf-8'))) :
                                                    if chr(ord(MyArbo.BufferInput[-1:])) in CHAR_ACCENT_LIST :
                                                      print("Accent sans caractère retiré silencieusement du buffer - Précédent chr sera aussi à retirer")
                                                      pass        # Accent sans caractère retiré silencieusement du buffer - Précédent chr sera aussi à retirer
                                                    else :
                                                      Cont=False  # Caractère spécial retiré du buffer 
                                                      print ("Caractère spécial retiré du buffer")
                                                      Removed = True
                                                    MyArbo.BufferInput = MyArbo.BufferInput[:-2]
                                                else :
                                                  if (Cont == True) and (len(MyArbo.BufferInput) > 2) and (ord(MyArbo.BufferInput[-3:-2]) == ord(CHAR_SS2.encode('utf-8'))) :
                                                      if chr(ord(MyArbo.BufferInput[-2:-1])) in CHAR_ACCENT_LIST :
                                                        Cont=False  # Caractère accentué retiré du buffer
                                                        print("Caractère accentué retiré du buffer")
                                                        Removed = True
                                                        MyArbo.BufferInput = MyArbo.BufferInput[:-3]
                                                  else :
                                                    if (Cont == True) and (len(MyArbo.BufferInput)>0) :
                                                      Cont=False  # Caractère normal retiré du buffer
                                                      print("Caractère normal retiré du buffer")
                                                      Removed = True
                                                      MyArbo.BufferInput = MyArbo.BufferInput[:-1]
                                                    else :
                                                      print("Aucun caractere retiré")
                                                      Cont = False
                                              if Removed == True :
                                                  try:
                                                    if not websocket.closed:
                                                      await websocket.send(((CHAR_BS + MyArbo.FieldList[MyArbo.CurField][FIELD_FILL] + CHAR_BS).encode('utf-8')).decode('utf-8','strict'))
                                                    else:
                                                      MyArbo.GotLib=True
                                                  except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
                                                    MyArbo.GotLib=True
                                                    if DoDebugAsync == True: 
                                                      print("Backspace cancelled [ClosedOK or ClosedError]")
                                                    pass

                                              else :
                                                MyArbo.DebugInput += "$EmptyBufferInput$"
                                                
                                        if item == CHAR_ANNULATION:
                                            GotSep=False
                                            MyArbo.DebugInput += "[ANNULATION]"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(MyArbo.FieldList):
                                              UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")
                                              ClearBufferInput()
                                              MyArbo.RefreshCurField=True
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('annulation',"Comment Annulation")
                                              
                                        if item == CHAR_GUIDE:
                                            GotSep=False
                                            MyArbo.DebugInput += "[GUIDE]"
                                            if len(MyArbo.GuideLink)>0:
                                                MyArbo.StackList.append(MyArbo.ArboCur)
                                                MyArbo.SetArbo(MyArbo.GuideLink)
                                            else:
                                                MyArbo.DebugInput += "$NoGuideDefined$"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(MyArbo.FieldList) and (MyArbo.DoSendPage==True):
                                              UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")
                                              ClearBufferInput()
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('guide',"Comment Guide")
    
                                        if item == CHAR_SOMMAIRE:
                                            GotSep=False
                                            MyArbo.DebugInput += "[SOMMAIRE]"  
                                            if not MyArbo.StackList :
                                                MyArbo.DebugInput += "$TopLevelReached$"
                                            else :                                       
                                              MyArbo.SetArbo(MyArbo.StackList.pop())
                                            #
                                            # Traitement du champ
                                            #
                                            if len(MyArbo.FieldList) and (MyArbo.DoSendPage==True):
                                              UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")
                                              ClearBufferInput()
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('sommaire',"Comment Sommaire")
                                            
                                        if item == CHAR_CONNECTION:
                                            MyArbo.GotLib=True
                                            GotSep=False
                                            MyArbo.DebugInput += "[CONNECTION]"
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('lib',"Connexion")
                                            break
                                        if item == CHAR_CONNECTION_MODEM:
                                            MyArbo.GotLib=True
                                            GotSep=False
                                            MyArbo.DebugInput += "[CONNECTION_MODEM]"
                                            #
                                            # Traitement des modules
                                            #
                                            MyArbo.CallModule('lib',"Modem")
                                            break
                                        if GotSep==True:
                                            GotSep=False                        
                                            if item > ' ':
                                                MyArbo.DebugInput += "<SEP>"+item
                                            else:
                                                MyArbo.DebugInput += "<SEP><0x{:02x}> ".format(ord(item))
                                    else:
                                        AddItemToBuffer(item)
          if MsgReceived != None :
            print("MsgReceived '" + MsgReceived + "'")
          if TimerReceived != None :
            print("TimerReceived ")
            #
            # Timer
            #
            if (not websocket.closed) and (not MyArbo.GotLib==True):
              MyArbo.TimerCount+=1
              MyArbo.CallModule('timer',"Comment Timer "+str(MyArbo.TimerCount))
              MyArbo.DebugInput += "[TIMER]"
              if len(MyArbo.TimerLink)>0:
                  MyArbo.SetArbo(MyArbo.TimerLink)
              else:
                  MyArbo.DebugInput += "$NoTimerDefined$"
              #
              # Traitement du champ
              #
              if len(MyArbo.FieldList) and (MyArbo.DoSendPage==True):
                UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")
                ClearBufferInput()
          if (MsgReceived == None) and (RawReceived == None) and (TimerReceived == None):
            #
            # Timeout
            #
            if (not websocket.closed) and (not MyArbo.GotLib==True):
              MyArbo.TimeoutCount+=1
              MyArbo.CallModule('timeout',"Comment TimeOut "+str(MyArbo.TimeoutCount))
              MyArbo.DebugInput += "[TIMEOUT]"
              if len(MyArbo.TimeoutLink)>0:
                  MyArbo.SetArbo(MyArbo.TimeoutLink)
              else:
                  MyArbo.DebugInput += "$NoTimeoutDefined$"
              #
              # Traitement du champ
              #
              if len(MyArbo.FieldList) and (MyArbo.DoSendPage==True):
                UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,"")
                ClearBufferInput()

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
            print(f"SERVER GOT '{MyArbo.DebugInput}'")
            MyArbo.DebugInput=""
    print(f"SERVER GOT '{MyArbo.DebugInput}' EXITING")
    #
    # Traitement des modules
    #
    MyArbo.CallModule('lib',"Bye")
    MyArbo.DebugInput=""
  finally:
    if not MyArbo._tasks[0].cancelled():
      print("Cancel 0") 
      MyArbo._tasks[0].cancel()  # Supprimer la tâche Raw
    if not MyArbo._tasks[1].cancelled():
      print("Cancel 1") 
      MyArbo._tasks[1].cancel()  # Supprimer la tâche Msg 
    if len(MyArbo._tasks)>2:
      if not MyArbo._tasks[2].cancelled():
        print("Cancel 2") 
        MyArbo._tasks[2].cancel()  # Supprimer la tâche Timer
    await asyncio.sleep(0.1) 
    if not websocket.closed:
      await websocket.close()
    NumSession=NumSession - 1
    print("FINALLY")
    z=asyncio.all_tasks()
    print("Pending tasks after websocket.close() : ="+str(len(z))+".")
#    if DoDebugAsync == True: 
    cnt=0
    for zz in z:
      cnt+=1
      print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
      print(zz.get_stack(limit=3))
    #
    # Do whatever is necessary to save/close after the session completes
    FreeAllFields()
    #
    SessionId=-1
    SessionCount=0
    try:
      lock.acquire()
      for Session in ListSession :
        if Session[0] == MySession :
          SessionId=SessionCount
        SessionCount += 1
      if SessionId > -1 :
        ListSession.pop(SessionId)
        print ("Deleted session " + str(MySession))
    finally :
        lock.release()
                  
    for Session in ListSession :
      print(Session)
        
try:
  #
  # Main
  #
  asyncio.get_event_loop().set_debug(DoDebugAsync)
  logging.basicConfig(level=logging.DEBUG) #ERROR) #DEBUG)
  #https://pymotw.com/3/asyncio/debugging.html
 
  logger = logging.getLogger('websockets')
  logger.setLevel(logging.ERROR) # DEBUG / ERROR / INFO
  logger.addHandler(logging.StreamHandler())

  loop=asyncio.get_event_loop()
  start_server = websockets.serve(hello, MyIP, MyPort)
  print("MAIN:websockets.serve hello() on @IP "+MyIP+ " and port "+str(MyPort))
  
  if DoDebugAsync == True: 
    z=asyncio.all_tasks(loop)
    print("Pending tasks after websocket.serve() : ="+str(len(z))+".")
    cnt=0
    for zz in z:
      cnt+=1
      print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
      print(zz.get_stack(limit=3))

  loop.run_until_complete(start_server)

  loop.set_exception_handler(handle_exception)
  loop.run_forever()
except:
  print ("ERR:Main() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
  err=sys.exc_info()
  for item in err:
    print(item)
finally:
  #print("Pending tasks at exit: %s" % asyncio.Task.all_tasks(asyncio.get_event_loop()))
  try:
    z=asyncio.all_tasks(asyncio.get_event_loop())
    print("Pending tasks at exit: ="+str(len(z))+".")
    if DoDebugAsync == True: 
      cnt=0
      for zz in z:
        cnt+=1
        print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
        print(zz.get_stack(limit=3))
  except:
    print ("ERR:AfterMain() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
    err=sys.exc_info()
    for item in err:
      print(item)
  finally:
    asyncio.get_event_loop().close()
