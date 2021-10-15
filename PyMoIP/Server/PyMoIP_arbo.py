#!/usr/bin/envh python
# -*- coding: utf-8 -*-
# PyMoIP_arbo class for PyMoIP_server

# 23/08/2021 - Augmentation des traces pour Unknown BUG100% CPU [désactivé 08/09/21]


import sys
import asyncio
import websockets
import importlib
from Server.PyMoIP_global import *

DoEchoBufferInput  = True      # Effectue l'écho des caractères bufferisés
DoRefreshPrevField = False     # Lors d'un changement de champ, réaffiche le champ qui vient d'être quitté avant d'afficher le nouveau champ en cours de saisie  
DoDebugList    = False         # Affiche les infos de trace pour les listes
DoDebugSetArbo = False         # Affiche les infos de trace pour l'arborescence
DoDebugGetVarInArboClass=False # Affiche les infos de trace pour l'évaluation des variables de l'arbo
DoDebugCallModule=False
DoDebugField    = False        # Affiche les infos de trace pour les champs
DoDebugTimer   = False         # Affiche les infos de trace pour le timer
DoDebugAsync   = False         # Affiche les infos de trace pour l'async
DoDebugUpdateDisplay = False   # Affiche les infos de trace pour UpdateDisplay()
DoDebugInsertBytes = True     # Affiche les infos pour InsertBytes
DoDebugRomRam=False            # Affiche les infos de décodage RomRam (dans AddItemToBuffer()) Unknown BUG100% CPU
DoDebugMainLoop=False          # Unknown BUG100% CPU
DoDebugSetMessage=True        # Affiche les infos de SetMessage() 
DoDebugImport=False            # Mise en évidence du pb 'suite' sur module teletel - l'import retrouve toujours l'état de la variable - IE : liste avec append 
DoDebugFastForward=False        # Avance rapide (N + SUITE)


class Arbo:
    def __init__(self,ArboRoot,path_modules,MyGtw,loop,MySession,websocket,refs):
        if DoDebugMainLoop==True:
          print("Arbo() __init__")
        self.ArboRoot    = ArboRoot   # + "."
        self.path_modules=path_modules      # Pour le moment, laisser à "" (ne marche pas)
        self.MyGtw       = MyGtw            # Pour retrouver la queue de sortie vers Gateway
        self.ArboCur     = "<None>"         # Position actuelle dans l'arborescence - "<None>" avant d'entrer 
        self.FirstFile   = 0                # Numéro de la première page (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [accessibles par SUITE/RETOUR]  
        self.LastFile    = 0                # Numéro de la dernière page (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [accessibles par SUITE/RETOUR]
        self.CurFile     = ""               # Numéro de la page actuelle - commence par la première (utile lorsqu'une séquence de plusieurs pages existe à cet emplacement de l'arbo) [modifié par SUITE/RETOUR]
        self.PrefixFile  = ""               # Préfixe du nom des pages de la séquence (ex : MENU_ pour une page qui serait nommée MENU_1_TEST.VDT)
        self.PostfixFile = ""               # Postfixe du nom des pages de la séquence (ex : _TEST.vdt pour une page qui serait nommée MENU_1_TEST.VDT)
        self.PageDir     = ""               # Répertoire où se trouve la séquence de pages pour cet emplacement de l'arborescence
        self.GuideLink   = ""
        self.RetourLink  = ""
        self.TimeoutLink = ""
        self.TimerLink   = ""
        self.ConstList   = list()           # Ceci contient la liste des constantes à évaluer dynamiquement dans self.InsertPostBytes
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
        #
        self.CrsrOnSent=True                # Envoyer Curseur OFF avant la page 
        #
        self.ArboLoop = 0                   # Boucler sur TimerLink ou RetourLink autant de fois que noté
        #
        # Parse input bytes - Used only in EventRawReceived()
        #
        self.GotSep=False
        self.GotSS2=False
        self.GotEsc=False
        self.GotCsi=False
        self.GotProSeq = 0
        self.ProtocolSeq = ""
        self.GotCsiSeq=""
        self.MsgReceived=""                 # Evènement : Messages recus ou None - Cleared/Updated in WaitEvent()
        self.TimerReceived=False            # Evènement : Timer reçu - Cleared/Updated in WaitEvent()
        #
        # Input of data 
        #
        self.RawReceived = ""               # Evènement : Caractères recus ou None - Buffer d'entrée en cours de traitement - Cleared/Updated in WaitEvent() - Used in EventRawReceived()  
        self.BufferInput = ""               # Buffer d'entrée (saisie en cours) - Cleared in CallModule()/ClearBufferInput() - Used+Cleared in UpdateCurField()
                                            #      Updated in AddItemToBufferNoRomRamNoLog() + LoadBufferInputWithCurField() + EventRawReceived()
        self.BufferEcho = ""                # Buffer d'écho (saisie en cours, filtrée)
        #
        self.DebugInput = ""
        self.DebugOutput = ""
        self.refs=refs
        self.GotLib      = False
        #
        #
        #
        self.GotRom      = bytearray()            # Contenu ROM recu
        self.GotRam1     = bytearray()            # Contenu RAM1 recu
        self.GotRam2     = bytearray()            # Contenu RAM2 recu
        self.ReplyRomRamExpect  = 0               # Nb ROM/RAM attendu (0 = aucun)
        self.ReplyRomRamIndex   = 0               # Nb caractères recus dans ROM/RAM en cours
        self.ReplyRomRam        = 0               # Item ROM/RAM en attente (0=ROM, 1=RAM1, 2=RAM2)
        self.ReplyRomRamPending = False           # ROM/RAM en cours de réception (SOH reçu)
        #
        self.ReplyRomRamGateway = False           # Précisions en cours de réception depuis la gateway
        self.ReplyRomRamGatewayValue=bytearray()  # Valeur des précisions reçues de la gateway
        #
        #
        #
        self.NumPageVdt  = bytearray()            # Numéro affichable de la page dans la séquence 
        self.NumPagesVdt = bytearray()            # Nombre total affichable de pages dans la séquence 
        self._tasks       = []                    # Liste des taches async
        self._RcvQueue    = asyncio.Queue()       # Queue de reception des messages
        self.TimeoutCount = 0                     # Nombre de timeout declanches depuis caractere recu par await websocket.recev
        self.TimerCount   = 0                     # Nombre de timer declanches - RAZ en début de session
        self.TimerChanged = False                 # Passe à True à chaque passage dans SetArbo - La tâche Timer est mise à jour dans Hello() afin d'éviter les pbs de boucle lorsque SetArbo() est mis à jour depuis un module 
        self.websocket    = websocket             # Au cas où .... permet websocket.send depuis un module (avec un thread distinct)
        self.loop         = loop                  # S'assure qu'on lance bien les tâches dans la bouche asyncio de départ (au cas où)
        self.MySession    = MySession             # Numéro de la session courante
        self.StateRedir   = NO_REDIR              # Passe True lorsque redirigé
        self.CurCost      = 0.0                   # Cout de la connexion
        self.CurCostAdd   = 0.74
        self.CurCostName  = "T30"
        self.SearchLink   = ""
        self.ShowCost     = False                 # Affichage en cours du cout
    
        #MyArbo._tasks = []
        #task = asyncio.create_task(foo())
        #              DataToWsServer = await (self.players[pid]).keysforward.get()
        #self._tasks.append(asyncio.ensure_future(_recv_with_timeout(self,websocket,0)))
        #MyArbo._tasks.append(asyncio.ensure_future(_timeout_for_recv (MyArbo,websocket,1)))
        ###self._tasks.append(asyncio.create_task(_timer_with_timeout(self,websocket,2)))
        #self._tasks.append(_recv_with_timeout(self,websocket,0))
        #MyArbo._tasks.append(asyncio.create_task(foo()))
        
        #print("Arbo() __init__ tasks")
        #self._tasks.append(self.loop.create_task(_recv_with_timeout(self,websocket,0)))
        #self._tasks.append(self.loop.create_task(_msg_with_timeout(self,websocket,1)))
        if DoDebugMainLoop==True:
          print("Arbo() __init__ done")
        
    def SetArbo (self,ArboCur):           
        MoveArbo=True            # Boucle dans l'arborescence - si fichier arbo_xxxxxx.py manquant ou Bypass
        PrevArbo=self.ArboCur    # Emplacement actuel dans l'arbo, pour y revenir au cas d'erreur à destination (fichier arbo manquant)
        ErrorInArbo = False      # Passe à Vrai en cas d'erreur sur l'arbo 
        _temp_Module_Args="Uninitialized"
                    
        while MoveArbo==True:
          MoveArbo=False
          print(f"SetArbo() SERVER ARBO MOVE from '{self.ArboCur}' to '{ArboCur}'")
          if self.ArboCur == "<None>":
            #self.InsertBytes= (chr(31)+"00"+chr(24)+chr(27)+"T Arriving"+chr(10)).encode('utf-8') # Hello
            self.InsertBytes= (chr(31)+"00"+chr(24)+chr(12)).encode('utf-8') # Hello
            if DoDebugInsertBytes == True:
              print(f"InsertBytes = ARRIVING")
            
          self.ArboCur=ArboCur
          # Chargement des valeurs d'arbo par défaut (pour ne pas devoir définir chaque variable dans chaque fichier <arbo>.py)
          if (DoDebugSetArbo==True):
            print("SetArbo() : __IMPORT__" + self.ArboRoot+"arbo_defaultvar")
          try:
            _tempDef = __import__(self.ArboRoot+"arbo_defaultvar", globals(), locals(), ['FirstFile', 'LastFile', 'PrefixFile', 'PostfiFile', 'PageDir', 
                                        'GuideLink', 'RetourLink', 'TimeoutLink', 'TimertLink', 'ConstList', 'VarList', 'FieldList', 'DisplayList', 'MenuList', 'Module', 'BypassList', 'KeywordList', 'TimeoutLimit'], 0)
            if (DoDebugSetArbo==True):
              print("$Success arbo_defaultvar.py$")
          except:
            print ("ERR:SetArbo(ArboDef,"+ self.ArboRoot + "arbo_defaultvar) "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
            err=sys.exc_info()
            for item in err:
              print(item)
            print("$import '" + self.ArboRoot + "arbo_defaultvar' error$")
            self.DebugInput+="$import '" + self.ArboRoot + "arbo_defaultvar' error$"
            pass

          self.FirstFile   = _tempDef.FirstFile
          self.LastFile    = _tempDef.LastFile
          self.PrefixFile  = _tempDef.PrefixFile
          self.PostfixFile = _tempDef.PostfixFile
          self.PageDir     = _tempDef.PageDir
          self.GuideLink   = _tempDef.GuideLink
          self.RetourLink  = _tempDef.RetourLink
          self.TimeoutLink = _tempDef.TimeoutLink
          self.TimerLink   = _tempDef.TimerLink
          if DoDebugImport==True:
            print("SetArbo() ConstList avant import defaut")
            print(self.ConstList)
          self.ConstList   = _tempDef.ConstList
          if DoDebugImport==True:
            print("SetArbo() ConstList apres import defaut")
            print(self.ConstList)                    
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
                                          'GuideLink', 'RetourLink', 'TimeoutLink', 'TimerLink', 'ConstList', 'VarList', 'FieldList', 'DisplayList', 'MenuList', 'Module', 'BypassList', 'KeywordList', 'TimeoutLimit', 'TimerDelay'], 0)
            if (DoDebugSetArbo==True):
              print("$Success " + self.ArboCur + ".py $")
            del sys.modules[self.ArboRoot+self.ArboCur]  # Corrige le bug d'import
          except:
            if (DoDebugSetArbo==True):
              print ("ERR:SetArbo(ArboCur," + self.ArboRoot+self.ArboCur + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
              print("$import '" + self.ArboRoot+self.ArboCur + "' error$")
            self.DebugInput+="$import '" + self.ArboRoot+self.ArboCur + "' error$"
            self.SetMessage("Arbo:'"+self.ArboCur+"'missing",False)
            if ErrorInArbo ==False:
              ErrorInArbo = True      # Passe à Vrai en cas d'erreur sur l'arbo
              MoveArbo=True           # Essayer de revenir à l'emplacement de départ
              self.ArboLoop = 0       # Annule toute boucle possible
              ArboCur=PrevArbo 
              if not self.StackList :
                self.DebugInput += "$TopLevelReachedInSetArbo()$"
              else :                                       
                ArboCur=self.StackList.pop()

              if (DoDebugSetArbo==True):
                print("SetArbo() : Trying to loop back once after first error")
            else:
              self.DebugInput+="$import '" + self.ArboRoot+self.ArboCur + "' double error$"
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
            self.RetourLink   = _temp.RetourLink
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
          if DoDebugImport==True:
            print("SetArbo() ConstList avant import arbo")
            print(self.ConstList)
          try:
            self.ConstList     = _temp.ConstList
          except:
            pass
          if DoDebugImport==True:
            print("SetArbo() ConstList apres import arbo")
            print(self.ConstList)
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

          if MoveArbo==False: # N'essaye pas de deplacement dans l'arbo un module si l'arbo est KO
            if (self.ArboLoop != 0):
              if DoDebugFastForward==True:
                print("ArboLoop="+str(self.ArboLoop))
              if (self.ArboLoop > 0) :
                if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                  if DoDebugFastForward==True:
                    print("Avancer")
                  self.CurFile  = self.CurFile + self.ArboLoop - 1    # Premiere page (dans une sequence de pages)
                  if (self.CurFile > self.LastFile ):
                    if DoDebugFastForward==True:
                      print ("Passer au noeud suivant")
                    self.ArboLoop = self.CurFile - (self.LastFile )
                    if (len(self.TimerLink)>0):
                        ArboCur = self.TimerLink
                        MoveArbo=True
                    else:
                      if DoDebugFastForward==True:
                        print("Impossible car pas de noeud suivant")
                      self.ArboLoop=0
                  else:
                    self.ArboLoop=0
                    if DoDebugFastForward==True:
                      print("On est arrives") 
                else:
                  if DoDebugFastForward==True:
                    print("ArboLoop >0 mais Liste ou Champ sur la page --> REFUSE")
                  self.ArboLoop=0
              else:
                if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                  if DoDebugFastForward==True:
                    print("Reculer")
                  self.CurFile  = self.LastFile    # Derniere page (dans une sequence de pages) 
                  self.CurFile  = self.CurFile + self.ArboLoop    # Premiere page (dans une sequence de pages)
                  if (self.CurFile < self.FirstFile ):
                    if DoDebugFastForward==True:
                      print ("Passer au noeud precedent")
                    self.ArboLoop = self.CurFile + (self.FirstFile )
                    if (len(self.RetourLink)>0):
                        ArboCur = self.RetourLink
                        MoveArbo=True
                    else:
                      if DoDebugFastForward==True:
                        print("Impossible car pas de noeud suivant")
                      self.ArboLoop=0
                  else:
                    self.ArboLoop=0
                    if DoDebugFastForward==True:
                      print("On est arrives") 
                else:
                  if DoDebugFastForward==True:
                    print("ArboLoop <0 mais Liste ou Champ sur la page --> REFUSE")
                  self.ArboLoop=0
          
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
                if len(_temp.Module.split(",",2))>1:
                  _temp_Module_Args=_temp.Module.split(",",2)[1]
                else:
                  _temp_Module_Args="NoArg"
                _temp.Module=_temp.Module.split(",",2)[0]
                if (DoDebugSetArbo==True):
                  print("__IMPORT__ trying to import _temp.Module '" + self.path_modules+_temp.Module + "' ....")
                #self.Module      = __import__ (self.path_modules+_temp.Module)      # Old
                self.Module      = importlib.import_module(self.path_modules+_temp.Module) # New
                self.ModuleName=_temp.Module
                if (DoDebugSetArbo==True):
                  print("__IMPORT__ '" + self.path_modules+_temp.Module + "' done.")
                  print(type(self.Module))
                  print(dir(self.Module))
              else:
                if hasattr(_tempDef, 'Module') and hasattr(_tempDef, 'ModuleName'): # and (_temp.ModuleName != "<None>"):
                  if (DoDebugSetArbo==True):
                    print("HASATTR")
                    print("__IMPORT__ no module defined in '" + self.ArboCur + "' - Trying with _tempDef.Module " + _tempDef.ModuleName + " .")                    
                  if len(_tempDef.Module.split(",",2))>1:
                    _temp_Module_Args=_tempDef.Module.split(",",2)[1]
                  else:
                    _temp_Module_Args="NoArgDef"
                  _tempDef.Module=_tempDef.Module.split(",",2)[0]
                  self.Module=_tempDef.Module
                  self.ModuleName=_tempDef.Module
                  #
                  # N'essaye jamais d'importer le module 'par defaut' ... A revoir
                  #
                  if (DoDebugSetArbo==True):
                    print("__IMPORT__ no module defined in '" + self.ArboCur + "'.")
                else:
                  if (DoDebugSetArbo==True):
                    print("NO HASATTR")
                    print("__IMPORT__ no module defined in '" + self.ArboCur + "' and in '" + self.ArboRoot+"arbo_defaultvar'.")                    
                    print(type(self.Module))
                    print(dir(self.Module))
                  
            except AttributeError :
              print ("ERR:SetArbo(LoadModule," + _temp.Module + ") "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
              print("$Module import '" + _temp.Module + "' error$")
              self.DebugInput+="$Module import '" + _temp.Module + "' error$"
              pass
        self.TimerChanged = True                # Sera pris en compte dans Hello()
        self.CallModule('init',_temp_Module_Args+",Initialized "+ str(self.MySession))
        
#            except:
#              self.InsertBytes = (chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1])).encode('utf-8')  #+chr(10)+chr(13)+str(sys.exc_info()[2])
#              print ("ERR:SetArbo "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
#              pass

    def CallModule(self,Touche,Comment):
      if type(self.Module) is str:
        if (DoDebugCallModule==True):
          print("CallModule("+Touche+","+Comment+") module="+self.ModuleName+" is STR, not module")
      else:
        if (DoDebugCallModule==True):
          print("CallModule("+Touche+","+Comment+") module="+self.ModuleName)
        if hasattr(self.Module,Touche) :
          try:
            if (DoDebugCallModule==True):
              print("PyMoIP_arbo->CallModule("+Touche+")")
              print("-----")
            Return=(getattr(self.Module, Touche))(self.refs,locals(),Comment)
            if Return == True:
              if (DoDebugCallModule==True):
                print("$Success received from module with '" + Touche + "'$")
              if len(self.FieldList) and (Touche != 'init') and (Touche != 'timeout') and (Touche != 'timer') and (Touche != 'message'):
                self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")  # Vide le champ en cours
                self.ClearBufferInput()      # Vide BufferInput
                self.SetMessage(CHAR_COFF,False)
                #MyArbo.DoSendPage=True
            else: 
              #MyArbo.DoSendPage=True
              self.UpdateCurField()              # Met à jour le champ en cours avec BufferInput puis vide BufferInput 
              self.LoadBufferInputWithCurField() # Charge BufferInput avec le champ en cours
              # self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")  # Vide le champ en cours ==> Pourquoi si BufferInput n'est pas vidé ?
              self.RefreshCurField=True
              if (DoDebugCallModule==True):
                print("$Called module failled with '" + Touche + "'$")
          except:
            print ("ERR CallModule():"+ self.ModuleName +"('" + Touche + "') "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
            err=sys.exc_info()
            for item in err:
              print(item)
        else:
          print("CallModule("+Touche+","+Comment+") fonction not found in module "+self.ModuleName)
          print ("PathModules="+self.path_modules)
          print ("ModuleName="+self.ModuleName)
          print ("dir(self.Module):")
          print (dir(self.Module))
          print ("self.Module:")
          print (self.Module)

          

    def GetVarInArboClass(self,MyVarToGet,DontManageList=False):
      #print("GetVarInArboClass("+MyVar+")")
      if False:
        print(vars(self).get("MenuList"))
        #print((vars().get("self")).get("MenuList"))
        print(vars().get("self.MenuList"))
        print ("GotRom")
        #print (GotRom)
      #if DoDebugGetVarInArboClass == True:
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
        print("-=-=-=-=-=-=-")
        print("PyMoIP_arbo->GetVarInArboClass()")
        print("MyVarToFetch ='"+MyVarToFetch+"'")     # Premier item de MyVarToGet dans, par ex <MyVarToGet>=<MyVarToFetch>,<Param1>,<ParamN>
        print("MyVar='"+MyVar+"'")                    # Nom de la variable extrait de MyVarToFetch dans, par ex <MyVarToFetch>=<MyVar>:<SubParam1>:<SubParamN>
        print("refs_prefix='"+self.refs["refs_prefix"]+"'")
        print("DontManageList='"+str(DontManageList)+"'")
        #try:
        #  print("refs[]")
        #  print(self.refs)
        #except:
        #  err=sys.exc_info()
        #  for item in err:
        #    print(item)
        print("----")
      try:   
        if (MyVar[:1]=="*") :                                                                    # (*) = Valeur 'globale', définies dans PyMoIP_server.py telles que NumSession, TotalSession, ListSession[], refs_prefix
                                                                                                 # Inclus la classe 'Server', la classe 'Arbo', les imports globaux, =les modules sys, asyncio, websockets
          if DoDebugGetVarInArboClass == True:
            print("Search var in global :'"+MyVar[1:]+"'")
          #print(self.refs)
          if MyVar[1:] in self.refs:
            MyTempVal = self.refs[MyVar[1:]]
          else:
            MyTempVal = "Udef:"+MyVar[1:]
            if DoDebugGetVarInArboClass == True:
              print("Var not found in global :'"+MyVar[1:]+"'")
            #
          #  
        elif (MyVar[:1]=="#") :                                                                 # (#) = Valeur locale [Qui doit être définie en dur, quelque part =>  MyVar, MyVarToGet, MyVarToFetch, ParamLen 
          if DoDebugGetVarInArboClass == True:
            print("Search var in local :'"+MyVar[1:]+"'")
          #print(vars())
          MyTempVal=vars().get(MyVar[1:],"Udef#:"+MyVar)
        elif (MyVar[:1]=="%") :                                                                 # (%) = Valeur dans l'objet arbo (self)
          if DoDebugGetVarInArboClass == True:
            print("Search var in self :'"+MyVar[1:]+"'")
          #print(vars(self))
          MyTempVal=(vars(self).get(MyVar[1:],"Udef%:"+MyVar))
        else:                                                                                      # Valeur globale indexée sur session => 'Locale'
          if DoDebugGetVarInArboClass == True:
            print("Search var in global with <refs_prefix>_<MyVar>_<MySession> :'"+MyVar+"'")  # Variables accessibles depuis toutes les sessions
          #print(self.refs)
          if self.refs["refs_prefix"] + MyVar + "_" + str(self.MySession) in self.refs:
            MyTempVal = self.refs[self.refs["refs_prefix"] + MyVar + "_" + str(self.MySession)]
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
      except:
          err=sys.exc_info()
          for item in err:
            print(item)

      if DoDebugGetVarInArboClass == True:
        print("GetVarInArboClass found")
        print(MyTempVal)

      while (type(MyTempVal) is list) and (DontManageList==False):
        if DoDebugGetVarInArboClass == True:
          print("MyTempVal is a list ... Needs to select an item")
          print(MyTempVal)
        if (len(MyTempVal)>0):
          if DoDebugGetVarInArboClass == True:
            print("Au moins 1 item dans la liste")
          if (len(MyVarToFetch.split(":"))>1):
            if DoDebugGetVarInArboClass == True:
              print("Un element est selectionne")
            if (MyVarToFetch.split(":"))[1]=="*":
              if DoDebugGetVarInArboClass == True:
                print("Select item = '*' ==> Selected MySession")
              FoundVal=-1  # -1 = NotFound
              CurVal=0
              for Val in MyTempVal:
                if DoDebugGetVarInArboClass == True:
                  print("Val in MyTempVal")
                  print(Val[LIST_SESSION_SESSION])
                if int(Val[LIST_SESSION_SESSION])==self.MySession:
                  if DoDebugGetVarInArboClass == True:
                    print("FoundVal=CurVal")
                  FoundVal=CurVal
                CurVal+=1
              if FoundVal>-1:
                MyTempVal=MyTempVal[FoundVal]
                if DoDebugGetVarInArboClass == True:
                  print("Un item == MySession dans la liste ==> MyTempVal=MyTempVal[FoundVal]")
                if (len(MyVarToFetch.split(":"))>2):
                  if DoDebugGetVarInArboClass == True:
                    print("Un sous-element est selectionne")
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
                  print("Un sous-element est selectionne")
                MyTempVal=MyTempVal[(MyVarToFetch.split(":"))[2]-1]
          else:
            if DoDebugGetVarInArboClass == True:
              print("Aucun element de la liste n'est selectionne ==> MyTempVal = MyTempVal[0]")
            MyTempVal = MyTempVal[0]
        else:
          MyTempVal=""
          if DoDebugGetVarInArboClass == True:
            print("Aucun item dans la liste => MyVal = ''")
      if DoDebugGetVarInArboClass == True:
        print("MyTempVal retourne : ")
        print(MyTempVal)
      return MyTempVal
      
      
    def SetMessage(self,MyMessage, MyBeep, Immediate=False):
      if Immediate==True:
        if DoDebugSetMessage==True:
          print("SetMessage("+MyMessage+",Immediate)")
        return ((CHAR_US+"00"+ CHAR_CAN + CHAR_ESC + "T " + MyMessage + CHAR_VTAB).encode('utf-8')) # Hello
        # _RcvQueue
      else:
        if MyMessage == CHAR_COFF or MyMessage == CHAR_CON:
          if MyMessage == CHAR_COFF :
            self.CrsrOnSent=False 
            if DoDebugSetMessage==True:
              print("SetMessage(COFF)")
          elif MyMessage == CHAR_CON :
            self.CrsrOnSent=True 
            if DoDebugSetMessage==True:
              print("SetMessage(CON)")
          self.InsertBytes += MyMessage.encode('utf-8') 
          if DoDebugInsertBytes == True:
            print("SetMessage() : InsertBytes CON/COFF CrsrOnSent="+str(self.CrsrOnSent))
        else:
          if DoDebugSetMessage==True:
            print("SetMessage("+MyMessage+")")
          self.InsertBytes += (CHAR_US+"00"+ CHAR_CAN + CHAR_ESC + "T " + MyMessage + CHAR_VTAB).encode('utf-8') # Hello
          if DoDebugInsertBytes == True:
            print("SetMessage() : InsertBytes "+MyMessage)
        if (MyBeep==True):
          self.InsertBytes += (CHAR_BEEP).encode('utf-8')

    def GetPage(self,fichier):
        # "Envoi du contenu d'un fichier"
        f = open(fichier, 'rb')
        contents=f.read()
        f.close()
        return (contents)
    

    #"""
    #    CalcPostBytes : Prepare les donnees a afficher (rafraichir) apres l'affichage de la page - CalcDisplayList traite similairement la liste specifiee dans DisplayList 
    #                    - Ces données sont specifiees dans la liste ConstList et VarList
    #                    - Pour chaque donnee, sont precises (*=optionellement)
    #                        - Une variable (obtenue avec GetVarInArboClass)
    #                        - Une position (YX)
    #                        - (*) Une serie d'attributs
    #                        - (*) Un nombre de caracteres
    #                        - (*) Un caractère de remplissage 
    #"""
    def CalcPostBytes(self):                        
        for MyVar in self.ConstList :
          MyTempStr=CHAR_US + chr(64+MyVar[VAR_POSV])+chr(64+MyVar[VAR_POSH])    # Positionnement au début
          for Attrib in MyVar[VAR_ATTRIBS]:                                      # Ajout de chaque attribut défini
            MyTempStr += CHAR_ESC
            MyTempStr += Attrib
          MyTempVal=MyVar[VAR_NAME]      # Ici, c'est une constante, pas une variable !
          if type (MyTempVal) is str:
            MyTempVal=MyTempVal.encode('utf-8')
          # Optimisations possibles si len(MyTempVal = 0)
          self.InsertPostBytes.extend (MyTempStr.encode('utf-8'))
          if (MyVar[VAR_SIZE]>0) or (len(MyVar[VAR_FILL])>0):
            self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            if MyVar[VAR_SIZE]>3:
              Repet=MyVar[VAR_SIZE]-1
              while Repet > 0:
                self.InsertPostBytes.extend (CHAR_REP.encode('utf-8'))
                if Repet < 64 :
                  self.InsertPostBytes.extend (chr(64+Repet).encode('utf-8'))
                  Repet = 0
                else :
                  self.InsertPostBytes.extend (chr(64+63).encode('utf-8'))
                  Repet -= 63
            else:
              if MyVar[VAR_SIZE]==3:
                self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
              self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            self.InsertPostBytes.extend (MyTempStr.encode('utf-8'))                
          self.InsertPostBytes.extend (MyTempVal)
        for MyVar in self.VarList :
          MyTempStr=CHAR_US + chr(64+MyVar[VAR_POSV])+chr(64+MyVar[VAR_POSH])    # Positionnement au début
          for Attrib in MyVar[VAR_ATTRIBS]:                                      # Ajout de chaque attribut défini
            MyTempStr += CHAR_ESC
            MyTempStr += Attrib
          MyTempVal=self.GetVarInArboClass(MyVar[VAR_NAME])
          if type (MyTempVal) is str:
            MyTempVal=MyTempVal.encode('utf-8')
          # Optimisations possibles si len(MyTempVal = 0)
          self.InsertPostBytes.extend (MyTempStr.encode('utf-8'))
          if (MyVar[VAR_SIZE]>0) or (len(MyVar[VAR_FILL])>0):
            self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            if MyVar[VAR_SIZE]>3:
              Repet=MyVar[VAR_SIZE]-1
              while Repet > 0:
                self.InsertPostBytes.extend (CHAR_REP.encode('utf-8'))
                if Repet < 64 :
                  self.InsertPostBytes.extend (chr(64+Repet).encode('utf-8'))
                  Repet = 0
                else :
                  self.InsertPostBytes.extend (chr(64+63).encode('utf-8'))
                  Repet -= 63
            else:
              if MyVar[VAR_SIZE]==3:
                self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
              self.InsertPostBytes.extend (MyVar[VAR_FILL].encode('utf-8'))
            self.InsertPostBytes.extend (MyTempStr.encode('utf-8'))                
          self.InsertPostBytes.extend (MyTempVal)

    def CalcDisplayList(self):
      if len(self.DisplayList) :
        MyList=self.GetVarInArboClass(self.DisplayList[LIST_NAME],True)
        MyNbLin=self.DisplayList[LIST_NB_LIN]          # Définition des champs de la liste
        MyNbCol=self.DisplayList[LIST_NB_COL]          # Définition des champs de la liste
        MyFirstLin=self.DisplayList[LIST_FIRST_LIN]    # Définition des champs de la liste
        MyFirstCol=self.DisplayList[LIST_FIRST_COL]    # Définition des champs de la liste
        MySizeCol=self.DisplayList[LIST_SIZE_COL]      # Définition des champs de la liste
        MyDefs=self.DisplayList[LIST_DEFS]             # Définition des champs de la liste
        MyFill1=self.DisplayList[LIST_FILL_1]          # Définition des champs de la liste
        MyAttr1=self.DisplayList[LIST_ATTR_1]          # Définition des champs de la liste
        MyFill2=self.DisplayList[LIST_FILL_2]          # Définition des champs de la liste
        MyAttr2=self.DisplayList[LIST_ATTR_2]          # Définition des champs de la liste
        
        MyItemsPerPage=MyNbLin*MyNbCol
        if MyItemsPerPage>0:
          MyNbPage=len(MyList)//MyItemsPerPage
          if MyNbPage*MyItemsPerPage!=len(MyList):
            MyNbPage=MyNbPage+1
        else:
          MyNbPage=1    # La liste n'est pas affichée - Il n'y a pas de nombre de pages mais il y en a forcément une quand même 
          
        if self.PageDisplayList < 0:
          self.PageDisplayList = 0
        if self.PageDisplayList > MyNbPage:
          self.PageDisplayList=MyNbPage
        self.NumPageDisplayList = (str(self.PageDisplayList+1)).encode('utf-8')
        self.NumPagesDisplayList= (str(MyNbPage)).encode('utf-8')
        if DoDebugList == True:
          print("Values in '" + self.DisplayList[LIST_NAME] + "'=")
          print(MyList)
          print("NbLin:" + str(MyNbLin) + " NbCol:" + str(MyNbCol) + " FirstLin:" + str(MyFirstLin) + " FirtstCol:" + str(MyFirstCol) + " SizeCol:" + str(MySizeCol))
          print("NbPage:" + str(MyNbPage) + " CurPage:" + str(self.PageDisplayList) + " ItemPerPage:" + str(MyItemsPerPage))
        if len(MyFill1) >0 :
          for ItemLin in range (0,MyNbLin):
            self.InsertPostBytes.extend ((CHAR_US + chr(64+MyFirstLin+ItemLin)+chr(64+MyFirstCol)).encode('utf-8'))
            for Attrib in MyAttr1:                                # Ajout de chaque attribut défini
              self.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
            if ItemLin == 0:
              self.InsertPostBytes.extend (MyFill1.encode('utf-8'))
            self.InsertPostBytes.extend (CHAR_REP.encode('utf-8'))
            if ItemLin == 0:
              self.InsertPostBytes.extend (chr(64+MySizeCol*MyNbCol-1).encode('utf-8'))
            else:
              self.InsertPostBytes.extend (chr(64+MySizeCol*MyNbCol).encode('utf-8'))
        MyCountItem = 0
        self.CurrentListDefs=MyDefs
        self.CurrentList=[]
        SizeItem=0
        for MyDef in MyDefs :
          if DoDebugList == True:
            print(MyDef)
          SizeItem += MyDef[LIST_DEF_COLS]
        for ItemCol in range(0,MyNbCol):
          for ItemLin in range (0,MyNbLin):
            CurItem=((self.PageDisplayList*MyItemsPerPage)+(ItemCol*MyNbLin)+ItemLin)
            if len (MyList)>CurItem and len(MyDefs)>0 :
              self.CurrentList.append (MyList[CurItem])
              if SizeItem ==0 :
                if DoDebugList == True:
                  print("NoItemToDisplay")
                # Aucun champ n'est à afficher
                #pass
              else:
                self.InsertPostBytes.extend ((CHAR_US + chr(64+MyFirstLin+ItemLin) + chr(64+MyFirstCol+MySizeCol*ItemCol)).encode('utf-8'))
                for Attrib in MyAttr2:                                # Ajout de chaque attribut défini
                  self.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
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
                    self.InsertPostBytes.extend (chr(9).encode('utf-8'))
                    MyInsert -= 1
                  for Attrib in MyDef[LIST_DEF_ATTR]:                                # Ajout de chaque attribut défini
                    self.InsertPostBytes.extend ((CHAR_ESC + Attrib).encode('utf-8'))
                  self.InsertPostBytes.extend (MyValue.encode('utf-8'))
                  if MyDef[LIST_DEF_COLS]>len(MyValue):
                    self.InsertPostBytes.extend (MyFill2.encode('utf-8'))
                    if (MyDef[LIST_DEF_COLS]-len(MyValue)) > 2:
                      self.InsertPostBytes.extend ((CHAR_REP+chr(64+MyDef[1]-len(MyValue)-1)).encode('utf-8'))
                    elif (MyDef[LIST_DEF_COLS]-len(MyValue)) == 2:
                      self.InsertPostBytes.extend (MyFill2.encode('utf-8'))
            MyCountItem += 1                    
        if DoDebugList == True:
          print(MyDefs)
          print(self.CurrentList)
          print(self.CurrentListDefs)
      #pass


    #
    # Gestion des champs
    #
    #  
    #


    def GetField(self,MyVar,MySession):
      try:                 
        try:                                  # Valeur globale
          MyTempVal = self.refs[self.refs["refs_prefix"] + MyVar + "_" + str(MySession)]
        except KeyError:
          print ("KeyError-> '"+ MyVar + "_" + str(MySession) + "' not found")
          MyTempVal = ""
          pass
        if type (MyTempVal) is int:
          MyTempVal = str(MyTempVal)
        if type (MyTempVal) is str:
          MyTempVal = MyTempVal.encode('utf-8')
        if DoDebugField == True:
          print ("GetField(" + MyVar + ")=" + (MyTempVal.decode('utf8', 'strict')))
        return MyTempVal
      except:
        print("ERR GetField()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
    
    def DeclareField(self,MyField):
      try:
        if DoDebugList == True:
          print("DeclareField(" + MyField + ")")
        self.refs[self.refs["refs_prefix"] + MyField + "_" + str(self.MySession)] = ""
      except:
        print("ERR DeclareField()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise

    def FreeAllFields(self):
      if DoDebugField == True:
        print("FreeAllFields()")
      try:
        for key in [*self.refs]:    # Pour toutes les variables 'globales'
          if key[:len(self.refs["refs_prefix"])] == self.refs["refs_prefix"]:  # si le début du nom de la variable est notre préfixe  
              if key[len(key)-(len(str(self.MySession))+1):] == "_" + str(self.MySession) :  # si la fin du nom de la variable est notre session
                if DoDebugField == True:
                  print(key + " deleted")
                self.refs.pop(key)
              else :
                if DoDebugField == True:
                  print(key + " kept")
      except:
        print("ERR FreeAllFields()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise

    def LoadBufferInputWithCurField(self):
      try:
        self.BufferInput=self.GetField(self.FieldList[self.CurField][FIELD_NAME],self.MySession).decode('utf-8','strict')
        print("LoadBufferInputWithCurField(" + self.FieldList[self.CurField][FIELD_NAME]+ ")")
      except IndexError:
        print("ERR : LoadBufferInputWithCurField():IndexError")
        print("Len(self.FieldList[])="+str(len(self.FieldList)))
        print("self.CurField)="+str(self.CurField))        
        pass
      
    def SetField(self,MyVar,MySession,MyBuffer):
      print("SetField("  + MyVar + "," + str(MySession) + ",' MyBuffer ')")
      self.refs[self.refs["refs_prefix"] + MyVar + "_" + str(MySession)] = MyBuffer
      #print(refs[refs_prefix + MyVar + "_" + str(MySession)])

    def UpdateField(self,MyVar,MySession,MyBuffer):
      print("UpdateField("  + MyVar + "," + str(MySession) + ",'" + MyBuffer + "')")
      self.SetField(MyVar,MySession,MyBuffer.encode('utf-8'))
      #self.refs[self.refs["refs_prefix"] + MyVar + "_" + str(MySession)] = MyBuffer.encode('utf-8')
      #print(refs[refs_prefix + MyVar + "_" + str(MySession)])
    
    def UpdateCurField(self):
      #nonlocal MySession
      
      print("UpdateCurField("  + str(self.MySession) + ",'" + self.BufferInput + "')")
      if len(self.FieldList) :
        self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,self.BufferInput)
        self.ClearBufferInput()

    def PresentFieldValue (self, MyVar):
      InsertPostField = bytearray()
      
      MyTempStr=CHAR_US + chr(64+MyVar[FIELD_POSV])+chr(64+MyVar[FIELD_POSH])    # Positionnement au début
      for Attrib in MyVar[FIELD_ATTRIBS]:                                        # Ajout de chaque attribut défini
        MyTempStr += CHAR_ESC
        MyTempStr += Attrib
      MyTempVal=self.GetField(MyVar[FIELD_NAME],self.MySession)                   # Valeur globale
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
    #
    # Traitement du buffer d'entrée
    #
    #
    def ClearBufferInput(self):
      print("ClearBufferInput()")
      self.BufferInput = ""
                
    def AddItemToBufferNoRomRamNoLog(self, item):
        #nonlocal BufferEcho

      try:
        if len(self.BufferInput)>2:
          if (ord(self.BufferInput[-1:])==ord(CHAR_SS2.encode('utf-8'))) and (chr(ord(item)) in CHAR_ACCENT_LIST) :
            if (ord(self.BufferInput[-3:-2])==ord(CHAR_SS2.encode('utf-8'))) and (chr(ord(self.BufferInput[-2:-1])) in CHAR_ACCENT_LIST) :
              self.BufferInput=self.BufferInput[:-2]
        self.BufferInput+=item
        if DoEchoBufferInput == True:
          self.BufferEcho += item
      except:
        print("ERR AddItemToBufferNoRomRamNoLog()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
    
    def AddItemToBufferNoRomRam(self, item):
        #
        # Ici, le traitement ROM/RAM a déjà été effectué - Ne bufferise pas [RC] ni [ESC] (mais accepte les autres codes de contrôle)
        #
      try:
        if type(item)==int:
          print("WARN : AddItemToBufferNoRomRam() got INT type --> CHR()") # "+str(item)+"
          item=chr(item)
        #self.DebugInput += "<0x{:02x}> ".format(ord(item)) # A supprimer, affichage en double du caractère reçu : Unknown BUG100% CPU
        if (item >= ' ') and (item <chr(0x80)):
            self.DebugInput += item
            self.AddItemToBufferNoRomRamNoLog(item)
        else:
            if item == CHAR_RC:
                self.DebugInput += "[RC]"
                # Prevoir traitement de [RC] comme [ENVOI]
            elif item == CHAR_ESC:
              self.DebugInput += "[ESC]"
            else:
                self.AddItemToBufferNoRomRamNoLog(item)
                self.DebugInput += "<0x{:02x}> ".format(ord(item))
      except:
        print("ERR AddItemToBufferNoRomRam()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
    
    def AddItemToBuffer(self, item):
        #nonlocal MyArbo
        #zznonlocal ReplyRomRamIndex,ReplyRomRam,ReplyRomRamPending
        #nonlocal ReplyRomRamExpect,GotRom,GotRam1,GotRam2
        #
        # Filter bytes received before buffering --> Will extract expected Rom/Ram and gateway replies
        # Called only from EventRawReceived() once ESC+Protocol, ESC+CSI, SEP/xx have been filtered
        #
      try:
        if type(item)==int:
          item=chr(item)
          if DoDebugRomRam==True:
            print("WARN : AddItemToBuffer() got int type --> CHR()") # "+str(item)+"
        if self.ReplyRomRamExpect > 0 :      # Si on prévoit de recevoir ROM/RAM
           if item == CHAR_SOH :                            # On se prépare à recevoir des éléments de ROM/RAM
             self.DebugInput += "[SOH]"
             self.ReplyRomRamPending = True                      # Les prochains caractères reçus seront des éléments de ROM/RAM
             self.ReplyRomRamIndex = 0                           # On n'en a encore reçus aucun
             if self.ReplyRomRam == 0 :                          # On attends ROM
               self.GotRom = bytearray()
             elif self.ReplyRomRam == 1 :                        # On attends RAM1
               self.GotRam1 = bytearray()
             elif self.ReplyRomRam == 2 :                        # On attends RAM2
               self.GotRam2 = bytearray()
           elif self.ReplyRomRamGateway==True:              # Reception en cours d'infos de la gateway
             if DoDebugRomRam==True:
               print("AddItemToBuffer() GotMessageFromGateway")
             if (item == chr(10)):
               self.ReplyRomRamGateway=False
               if DoDebugRomRam==True:
                 print("AddItemToBuffer() GotRom:MessageFromGateway-Complete '")
                 print(self.ReplyRomRamGatewayValue) #.decode('utf-8','strict')+"'")
               MyList=self.refs['ListSession']
               Found=-1
               Count=0
               for item in MyList:
                  if item[LIST_SESSION_SESSION]==self.MySession:
                    Found=Count
                  Count+=1
               if Found>-1:
                    #print(MyList[Found])
                    if MyList[Found][LIST_SESSION_FROMGATEWAY]==bytearray() and len(self.ReplyRomRamGatewayValue)>0:
                      if DoDebugRomRam==True:
                        print(self.refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])
                      self.refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY]=(self.ReplyRomRamGatewayValue.decode('utf-8','strict')).split(',')
                      if DoDebugRomRam==True:
                        print(self.refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])
                        print("ListSession changed")
             else:
               self.ReplyRomRamGatewayValue.extend(item.encode('utf-8'))
           elif self.ReplyRomRamPending == True :                # Si on est en cours de réception d'éléments de ROM/RAM
               self.ReplyRomRamIndex = self.ReplyRomRamIndex + 1      # Noter qu'un de plus est reçu
               if (item == CHAR_EOT) or (self.ReplyRomRamIndex == 16):             # fin de ROM/RAM ou Taille maximale reçue
                 self.DebugInput += "[EOT/EndOfRomRam]"
                 self.ReplyRomRamPending = False                 # On ne reçoit plus RAM/ROM
                 self.ReplyRomRamExpect = self.ReplyRomRamExpect - 1  # Une ROM/RAM attendue en moins
                 self.ReplyRomRam = self.ReplyRomRam + 1              # Au cas où, on se prépare pour attendre le prochain ROM/RAM
               if item != CHAR_EOT :                        # Ne pas stocker EOT
                 # Mémoriser le caractère reçu
                 self.DebugInput += item
                 if self.ReplyRomRam == 0 :                      # Attends ROM
                   self.GotRom += item.encode('utf-8')
                 elif self.ReplyRomRam == 1 :                    # Attends RAM1
                   self.GotRam1 += item.encode('utf-8')
                 elif self.ReplyRomRam == 2 :                    # Attends RAM2
                   self.GotRam2 += item.encode('utf-8')
               if self.ReplyRomRamPending == False :
                 # Juste pour débugage
                 if self.ReplyRomRam == 1 :                      # Attendait ROM
                   if self.GotRom[0]==self.GotRom[1]==self.GotRom[2]==127:
                     if DoDebugRomRam==True:
                       print("AddItemToBuffer() GotRom:MessageFromGateway-Start")
                     #print(type(self.GotRom[0]))
                     #print(self.GotRom[0])
                     self.ReplyRomRamGateway=True
                     self.ReplyRomRamGatewayValue=bytearray()
                     self.ReplyRomRamExpect = self.ReplyRomRamExpect + 1  # Une ROM/RAM attendue en moins -> en plus
                     self.ReplyRomRam = self.ReplyRomRam - 1              # Au cas où, on se prépare pour attendre le prochain ROM/RAM -> Le même
                   else:
                     if DoDebugRomRam==True:
                       print("Updated ROM {}".format(self.GotRom))
                 elif self.ReplyRomRam == 2 :                    # Attendait RAM1
                   if DoDebugRomRam==True:
                     print("Updated RAM1 {}".format(self.GotRam1))
                 elif self.ReplyRomRam == 3 :                    # Attendait RAM2
                   if DoDebugRomRam==True:
                     print("Updated RAM2 {}".format(self.GotRam2))
           else :                                           # On n'est pas en cours de réception d'éléments de ROM/RAM
             self.AddItemToBufferNoRomRam(item)
        else :              # On ne s'attend pas à reçevoir ROM/RAM
          self.AddItemToBufferNoRomRam(item)
      except:
        print("ERR AddItemToBuffer()")
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
        
    #
    #  Async stuff
    #
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
    #  
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
    #
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

    async def UpdateDisplay(self):
        if DoDebugMainLoop==True or DoDebugUpdateDisplay == True:
          print("PyMoIP_arbo->UpdateDisplay()")
        #
        # 1ere étape de la boucle principale
        #
        # Si demandé [DoSendPage=True], recalcule puis affiche la page complète
        # Sinon,  si demandé [RefreshCurField=True seulementg], recalcule puis affiche le champ actuel seulement
        # Dans tous les cas, assure l'écho des caractères traités au passage précédent de la boucle principale dans AddItemToBufferNoRomRamNoLog() 
        #
        if self.DoSendPage==True:
            if len(self.BufferEcho) :          # Envoyer l'echo avant la page (Si X + Fnct reçus dans le meme paquet)
              self.InsertBytes.extend (self.BufferEcho.encode('utf-8'))
              self.BufferEcho=""          
            if (self.CrsrOnSent==True):
              self.CrsrOnSent=False
              self.InsertPostField.extend (CHAR_CON.encode('utf-8')) # Curseur ON
              if DoDebugSetMessage==True:
                print("UpdateDisplay(COFF,DoSendPage)")
            
            #
            # La page complete est a envoyer
            #
            # Rafraichissement et mise en forme de tous les types de variables à afficher, tel que défini dans l'arborescence 
            #
            self.InsertPostBytes=bytearray()        # Vider avant de recalculer la liste, les variables, et les champs qui seront a afficher apres la page
            self.CalcDisplayList()                  # Preparer en premier la partie de liste a afficher
            self.NumPageVdt  = str(self.CurFile-self.FirstFile + 1).encode('utf-8')            # Numéro affichable de la page dans la séquence (MAJ de la variable avant son éventuel affichage !)
            self.CalcPostBytes()                     # Preparer ensuite les variables a afficher                 
            #
            # Rafraichissement et mise en forme des champs à afficher, le champ en cours de saisie en dernier, tel que défini dans l'arborescence 
            #
            self.InsertPostField=bytearray()
            # Commencer par les champs qui ne sont pas en cours de saisie
            CountField = 0
            for MyVar in self.FieldList :
              if CountField != self.CurField :
                self.InsertPostField.extend (self.PresentFieldValue(MyVar))
              CountField = CountField + 1
            # Puis le champ en cours de saisie
            if len(self.FieldList) >0 :    # Si au moins 1 champ 
              self.InsertPostField.extend (self.PresentFieldValue(self.FieldList[self.CurField]))
              self.InsertPostField.extend (CHAR_CON.encode('utf-8')) # Curseur ON
              self.CrsrOnSent=True 
              if DoDebugSetMessage==True:
                print("UpdateDisplay(CON,DoSendPage)")
            else:
              self.CrsrOnSent=False
            # Enfin, charger la page    
            try:
                page=self.GetPage(self.PageDir + self.PrefixFile + str(self.CurFile) + self.PostfixFile)
                if DoDebugUpdateDisplay == True:
                  print(f"UpdateDisplay() SERVER SENT FILE '{self.PrefixFile+str(self.CurFile)+self.PostfixFile}'")
                  print(type(page))
            except:
                page=bytearray(chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1]),'utf-8')     #+chr(10)+chr(13)+str(sys.exc_info()[2])
                #page=(chr(12)+str(sys.exc_info()[0])+chr(10)+chr(13)+str(sys.exc_info()[1])).encode('utf-8')  #+chr(10)+chr(13)+str(sys.exc_info()[2])
                print ("ERR:Hello().GetPage() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
                self.CurFile=self.FirstFile
                pass
            #
            # Envoi de la page
            #
            try:
              if not self.websocket.closed:
                # await websocket.send(MyArbo.InsertBytes) # + page)
                #await websocket.send((MyArbo.InsertBytes + page + MyArbo.InsertPostBytes + MyArbo.InsertPostField).decode('utf-8','strict'))
                await self.websocket.send((self.InsertBytes + page + self.InsertPostBytes + self.InsertPostField))
                self.DebugOutput += (self.InsertBytes + page + self.InsertPostBytes + self.InsertPostField).decode('utf-8','strict')
              else:
                self.GotLib=True
            except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
              if DoDebugAsync == True: 
                print("DoSendPage cancelled [ClosedOK or ClosedError]")
              self.GotLib=True
              pass
            self.InsertBytes = bytearray()                   # Clear possible previous page content prefix
            if DoDebugInsertBytes == True:
              print("UpdateDisplay() self.InsertBytes cleared [DoSendPage]")
            self.DoSendPage=False                            # La page a ete envoyee, pas besoin de la re-afficher au prochain passage de la boucle, sauf si demande
            self.RefreshCurField=False                       # Le champ en cours ete envoye, pas besoin de le re-afficher au prochain passage de la boucle, sauf si demande

        if self.RefreshCurField==True :
          if len(self.BufferEcho) :          # Envoyer l'echo avant la page (Si X + Fnct reçus dans le meme paquet)
              self.InsertBytes.extend (self.BufferEcho.encode('utf-8'))
              self.BufferEcho=""          
          #
          # La page complete n'est pas a envoyer, seulement le champ en cours
          #
          self.RefreshCurField=False                         # Le champ en cours ete envoye, pas besoin de le re-afficher au prochain passage de la boucle, sauf si demande
          if len(self.FieldList) >0 :                        # Si au moins 1 champ est defini 
            #
            # Rafraichissement et mise en forme des champs à afficher, le champ précédent puis le champs en cours de saisie, tel que défini dans l'arborescence 
            #                                                              
            self.InsertPostField=bytearray()                 # Recalculer le(s) champ(s) à afficher
            # Champ précédement en cours de saisie
            if DoRefreshPrevField == True :                    # Optionnellement, ré-afficher le champ dont on vient de partir 
              if self.PrevField >= 0:                        # Si le "champ précédent" est défini
                self.InsertPostField.extend (self.PresentFieldValue(self.FieldList[self.PrevField]))
              self.PrevField = -1                            # Ne pas ré-afficher le champ precedent au prochain passage, sauf si demande
            # Champ en cours de saisie
            self.InsertPostField.extend (self.PresentFieldValue(self.FieldList[self.CurField]))
            self.InsertPostField.extend (CHAR_CON.encode('utf-8')) # Curseur ON           
            if DoDebugSetMessage==True:
              print("UpdateDisplay(CON,RefreshCurField)")
            self.CrsrOnSent=True
            #
            # Envoi du champ seul
            #
            try:
              if not self.websocket.closed:
                await self.websocket.send((self.InsertBytes + self.InsertPostField).decode('utf-8','strict'))
                self.DebugOutput += (self.InsertBytes + self.InsertPostField).decode('utf-8','strict')
              else:
                self.GotLib=True
            except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
              self.GotLib=True
              if DoDebugAsync == True: 
                print("RefreshCurField cancelled [ClosedOK or ClosedError]")
              pass
          else:
            self.CrsrOnSent=False

            self.InsertBytes = bytearray()                 # Clear possible previous page content prefix
            if DoDebugInsertBytes == True:
              print("UpdateDisplay() self.InsertBytes cleared [RefreshCurField]")
        #
        #      Echo des caractères saisis - Ca marche parce qu'une page ou un champ seul ne peuvent être (ré)affichés que sur demande (touche de fonction reçue)
        #      --> Le buffer a donc été envoyé en echo au pécédent passage et pris en compte
        #      --> Seuls cas douteux : action de (ré)affichage sur évènements Timeout, Timer ou Msg
        #      --> L'écho pourrait facilement être masqué au besoin (attention aux accents) 
        #
        if len(self.BufferEcho) :
          try:
            if not self.websocket.closed:
              await self.websocket.send((self.BufferEcho.encode('utf-8')).decode('utf-8','strict'))
              self.DebugOutput += (self.BufferEcho)
            else:
              self.GotLib=True
          except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
            self.GotLib=True
            if DoDebugAsync == True: 
              print("BufferEcho cancelled [ClosedOK or ClosedError]")
            pass
          self.BufferEcho=""          
        if DoDebugMainLoop==True or DoDebugUpdateDisplay == True:
          print("PyMoIP_arbo->UpdateDisplay() done")
      
    async def UpdateTimer(self) :
        #
        # 2eme étape de la boucle principale
        #
        # Prends en compte les changements de timer dans SetArbo()
        #
        if DoDebugMainLoop==True or DoDebugTimer == True:
          print("PyMoIP_arbo->UpdateTimer()")
        try:
          if self.TimerChanged==True:
            self.TimerChanged=False
            if len(self._tasks) >2:    # Mais il y avait un timer actif avant SetArbo
              self._tasks[2].cancel()  # Supprimer la tâche Timer 
              del self._tasks[2]
              if DoDebugTimer==True:
                print("SetArbo() Timer cancelled for "+str(self.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
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
                print("SetArbo() No timer to cancel for "+str(self.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
              pass          
            #
            # Mets un nouveau timer 
            #
            if self.TimerDelay>0:      # Il y a maintenant un Timer actif
              result=self._tasks.append(self.loop.create_task(self._timer_with_timeout(self.websocket,2)))
              if DoDebugTimer==True:
                print("SetArbo() Timer created for "+str(self.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")
                z=asyncio.all_tasks()
                print("Timer => all_tasks ="+str(len(z))+".")
                cnt=0
                for zz in z:
                  cnt+=1
                  print("Task #"+str(cnt)+" done="+str(zz.done())+", cancelled="+str(zz.cancelled()))
                  print(zz.get_stack(limit=3))
            else:
              if DoDebugTimer==True:
                print("SetArbo() No timer to create for "+str(self.TimerDelay)+"secs  --- all_tasks ="+str(len(asyncio.all_tasks()))+".")          
        except:
          err=sys.exc_info()
          for item in err:
            print(item)
          raise
        finally:
          if DoDebugMainLoop==True or DoDebugTimer == True:
            print("PyMoIP_arbo->UpdateTimer() done")

    async def WaitEvent(self):
        #
        # 3eme étape de la boucle principale
        #
        # Attends un évènement - Retourne RawReceived, MsgReceived, TimerReceived, ou Timeout
        #
          if DoDebugMainLoop==True:
            print("WaitEvent() start")
          keep_waiting: bool = True
          TimeOut=0         
          self.RawReceived=None
          self.MsgReceived=None
          self.TimerReceived=None

          if DoDebugTimer==True:
              print("SetArbo() Timer keepwaiting for "+str(self.TimerDelay)+"secs  --- Before all_tasks ="+str(len(asyncio.all_tasks()))+".")
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
              while keep_waiting and (not self.websocket.closed):
                  try:
                      if DoDebugAsync == True: 
                        print("asyncio.wait started "+str(len(self._tasks)) + " tasks - all_tasks = ("+str(len(asyncio.all_tasks()))+")")
                      done, pending = await asyncio.wait(self._tasks, timeout=1, return_when=asyncio.FIRST_COMPLETED)
                      if DoDebugAsync == True: 
                        print("asyncio.wait done")
                      if len(done)>0:                    # Au moins une tache terminee -> C'est pas un timeout
                        if self._tasks[0] in done:     # Un caractere est recu (au moins)
                          self.RawReceived=self._tasks[0].result()  # Noter le(s) caractere(s) recu(s)
                          if DoDebugAsync == True: 
                            print("Got valid data in RawReceived from _recv_with_timeout() ==> Keep waiting = False")
                          self.TimeoutCount=0          # Reset du timeout
                          keep_waiting=False             # Sortir de la boucle
                          if not self.websocket.closed:       # Relancer la tache (si on est toujours connectés)
                            self._tasks[0]=asyncio.create_task(self._recv_with_timeout(self.websocket,0))
                        if self._tasks[1] in done:     # Un message est recu
                          self.MsgReceived=self._tasks[1].result()  # Noter le message
                          if DoDebugAsync == True: 
                            print("Got valid data in MsgReceived from _msg_with_timeout() ==> Keep waiting = False")
                          #MyArbo.TimeoutCount=0         # N'impacte pas le timeout
                          keep_waiting=False             # Sortie de la boucle
                          if not self.websocket.closed:       # Relancer la tache (si on est toujours connectés)
                            self._tasks[1]=asyncio.create_task(self._msg_with_timeout(self.websocket,1))
                        if len(self._tasks)>2:         # Si une tache timer existe
                          if self._tasks[2] in done:   # Un timer est recu
                            self.TimerReceived=True           # Noter l'évènement
                            if DoDebugAsync == True: 
                              print("Got valid data in TimerReceived from _timer_with_timeout() ==> Keep waiting = False")
                            #MyArbo.TimeoutCount=0        # N'impacte pas le timeout
                            keep_waiting=False            # Sortie de la boucle
                            if not self.websocket.closed:      # Relancer la tache (si on est toujours connectés)
                              self._tasks[2]=asyncio.create_task(self._timer_with_timeout(self.websocket,1))
                      else:                               # Aucune tache terminee -> une seconde est passee et on est sorti du wait par timeout
                        TimeOut+=1                        # Une seconde de plus est notée
                        if (TimeOut>=self.TimeoutLimit) and (self.TimeoutLimit>0):  # Si le delais de timeout est valide et atteint
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
            self.GotLib=True
            if DoDebugAsync == True: 
              print("RawReceived cancelled [ClosedOK or ClosedError]")
            pass
          except Exception as e:
              self.GotLib=True
              print('ws exception:{}'.format(e))
              #keep_waiting = False
          finally:          
            if DoDebugMainLoop==True:
              print("WaitEvent() end")
                       
          #print("Fin de KeepWaiting")

    async def EventRawReceived(self) :
          def PRO2_CodeFonctionnement_to_strings(argument):
            switcher = {
                0x42: "80 colonnes",
                0x43: "rouleau",
                0x44: "PCE",
                0x45: "minuscules",
                0x46: "loupe haut",
                0x47: "loupe bas"
            }
          def PROx_Aig_E_to_strings(argument):
            switcher = {
                0x50: "ecran emeteur",
                0x51: "clavier emeteur",
                0x52: "modem emeteur",
                0x53: "prise emeteur",
                0x54: "telephone emeteur",
                0x55: "logiciel emeteur"
            }
            return switcher.get(argument, "")
          def PROx_Aig_R_to_strings(argument):
            switcher = {
                0x58: "ecran recepteur",
                0x59: "clavier recepteur",
                0x5A: "modem recepteur",
                0x5B: "prise recepteur",
                0x5C: "telephone recepteur",
                0x5D: "logiciel recepteur"
            }
            return switcher.get(argument, "")
          def PRO3_MfClavier_to_strings(argument):
            switcher = {
                0x41: "clavier etendu",
                0x42: "clavier normal"
            }
            return switcher.get(argument, "")
          def PRO1_to_strings(argument):
            switcher = {
                0x50: "PRO1 Bis",
                0x53: "PRO1 Decrochage",
                0x54: "PRO1 Commutation donnees phonie",
                0x57: "PRO1 Racrochage",
                0x58: "PRO1 Coupure calibree",
                0x59: "PRO1 Remise a zero",
                0x5A: "PRO1 Demande status telephonique",
                0x67: "PRO1 Deconnexion modem",
                0x68: "PRO1 Connexion modem",
                0x6C: "PRO1 Retournement modem",
                0x6D: "PRO1 Retournement inverse",
                0x6E: "PRO1 Acquitement retournement",
                0x6F: "PRO1 Mode maitre retournement",
                0x70: "PRO1 Demande status terminal",
                0x72: "PRO1 Demande status fonctionnement",
                0x74: "PRO1 Demande status vitesse",
                0x76: "PRO1 Demande status protocole",
                0x78: "PRO1 Telechargement RAM1",
                0x79: "PRO1 Telechargement RAM2",
                0x7A: "PRO1 Identification RAM1",
                0x7B: "PRO1 Identification terminal",
                0x7F: "PRO1 Reset videotext"
            }
            return switcher.get(argument, "PRO1 inconnu")


          def PRO2_to_strings(argument1,argument2):
            if argument1==0x31:
              if argument2==0x7D:
                return "PRO2 Mode teleinformatique"
              else:
                return "PRO2 Mode teleinformatique invalide"
            elif argument1==0x32:
              if argument2==0x7D:
                return "PRO2 Mode videotext a mixte"
              elif argument2==0x7E:
                return "PRO2 Mode mixte a videotext"
              else:
                return "PRO2 Mode teleinformatique invalide"
            elif argument1==0x55:
              if argument2==0x4E:
                return "PRO2 Commutation donnees phonie"
              else:
                return "PRO2 Commutation donnees phonie invalide"
            elif argument1==0x5B:
                return "PRO2 Reponse status telephonique <octet>"
            elif argument1==0x62:
                module=PROx_Aig_R_to_strings(argument2)
                if module=="":
                  module=PROx_Aig_E_to_strings(argument2)
                  if module=="":
                    return "PRO2 Demande status module invalide"
                  else:
                    return "PRO2 Demande status module emeteur "+module
                else:
                    return "PRO2 Demande status module recepteur "+module
            elif argument1==0x64:
                module=PROx_Aig_R_to_strings(argument2)
                if module=="":
                  module=PROx_Aig_E_to_strings(argument2)
                  if module=="":
                    return "PRO2 Non diffusion acquitements module invalide"
                  else:
                    return "PRO2 Non diffusion acquitements module emeteur "+module
                else:
                    return "PRO2 Non diffusion acquitements module recepteur "+module
            elif argument1==0x65:
                module=PROx_Aig_R_to_strings(argument2)
                if module=="":
                  module=PROx_Aig_E_to_strings(argument2)
                  if module=="":
                    return "PRO2 Diffusion acquitements module invalide"
                  else:
                    return "PRO2 Diffusion acquitements module emeteur "+module
                else:
                    return "PRO2 Diffusion acquitements module recepteur "+module
            elif argument1==0x66:
                return "PRO2 Transparence "+str(argument2)
            elif argument1==0x69:
                return "PRO2 Debut mode fonctionnement "+PRO2_CodeFonctionnement_to_strings(argument2)
            elif argument1==0x6A:
                return "PRO2 Debut mode fonctionnement "+PRO2_CodeFonctionnement_to_strings(argument2)
            elif argument1==0x6B:
                return "PRO2 Vitesse prise <CodeVitesse>"
            elif argument1==0x6F:
              if argument2==0x31:
                return "PRO2 Mode esclave"
              else:
                return "PRO2 Mode esclave invalide"
            elif argument1==0x71:
              if argument2 & 0x01:
                mode="oppose, "
              else:
                mode="non oppose, "
              if argument2 & 0x02:
                mode=mode+"reception 1200, "
              else:
                mode=mode+"reception 75, "
              if argument2 & 0x04:
                mode=mode+"module telephonique on, "
              else:
                mode=mode+"module telephonique off, "
              if argument2 & 0x08:
                mode=mode+"porteuse presente, "
              else:
                mode=mode+"porteuse absente, "
              if argument2 & 0x10:
                mode=mode+"fil PT actif, "
              else:
                mode=mode+"fil PT inactif, "
              if argument2 & 0x20:
                mode=mode+"module logiciel actif, "
              else:
                mode=mode+"module logiciel inactif, "
              
              return "PRO2 Reponse status terminal "+mode
            elif argument1==0x72:
              if argument2==0x59:
                return "PRO2 Demande status clavier"
              else:
                return "PRO2 Demande status invalide"
            elif argument1==0x73:
              if (argument2 & 0x01)==0x01:
                mode="80 colonnes, "
              else:
                mode="40 colonnes, "
              if (argument2 & 0x02)==0x02:
                mode=mode+"page, "
              else:
                mode=mode+"rouleau, "
              if (argument2 & 0x04)==0x04:
                mode=mode+"PCE, "
              else:
                mode=mode+"non PCE, "
              if (argument2 & 0x08)==0x08:
                mode=mode+"minuscules"
              else:
                mode=mode+"majuscules"
              if (argument2 & 0x10)==0x10:
                mode=mode+", loupe haute"
              else:
                mode=mode+", loupe basse"
              if (argument2 & 0x20)==0x20:
                mode=mode+", loupe active"
              else:
                mode=mode+", loupe inactive"
              return "PRO2 Reponse status fonctionnement "+mode
            elif argument1==0x75:
              return "PRO2 Reponse status vitesse <octet>"
            elif argument1==0x77:
              return "PRO2 Reponse status protocole <octet>"
            elif argument1==0x7C:
              if argument2==0x6A:
                return "PRO2 Copie ecran en jeu Francais"
              elif argument2==0x6B:
                return "PRO2 Copie ecran en jeu Americain"
              else:
                return "PRO2 Copie ecran invalide"
            else:
              return "PRO2 inconnu"


          def PRO3_to_strings(argument1,argument2,argument3):
            if argument1==0x52:
              return "PRO3 Numerotation a partir de l'ecran ????"
            elif argument1==0x60:
              # PRO3 OFF <R> <E>
              module_R=PROx_Aig_R_to_strings(argument2)
              module_E=PROx_Aig_E_to_strings(argument3)
              if module_R=="":
                if module_E=="":
                  return "PRO3 OFF <recepteur invalide> <emeteur invalide>" 
              elif module_E=="":
                  return "PRO3 OFF "+ module_R +" <emeteur invalide>" 
              else:
                  return "PRO3 OFF "+ module_R + module_E 
            elif argument1==0x61:
              # PRO3 ON <R> <E>
              module_R=PROx_Aig_R_to_strings(argument2)
              module_E=PROx_Aig_E_to_strings(argument3)
              if module_R=="":
                if module_E=="":
                  return "PRO3 ON <recepteur invalide> <emeteur invalide>" 
              elif module_E=="":
                  return "PRO3 ON "+ module_R +" <emeteur invalide>" 
              else:
                  return "PRO3 ON "+ module_R + module_E 
            elif argument1==0x63:
              # PRO3 STATUS <R ou E> <octet>
              module=PROx_Aig_R_to_strings(argument2)
              if module!="":
                return "PRO3 STATUS "+ module +" (reception) <octet>" 
              else:
                module=PROx_Aig_E_to_strings(argument2)
                if module!="":
                  return "PRO3 STATUS "+ module +" (emission) <octet>" 
                else:
                  return "PRO3 STATUS module invalide <octet>" 
            elif argument1==0x69:
              if argument2==0x59:
                mode=PRO3_MfClavier_to_strings(argument3)
                if mode=="":
                  return "PRO3 Activation mode fonctionnement clavier invalide"
                else:
                  return "PRO3 Activation mode fonctionnement clavier "+mode
              else:
                return "PRO3 Activation mode fonctionnement invalide"
            elif argument1==0x6A:
              if argument2==0x59:
                mode=PRO3_MfClavier_to_strings(argument3)
                if mode=="":
                  return "PRO3 Desactivation mode fonctionnement clavier invalide"
                else:
                  return "PRO3 Desactivation mode fonctionnement clavier "+mode
              else:
                return "PRO3 Desactivation mode fonctionnement invalide"
            elif argument1==0x73:
              if argument2==0x59:
                mode=PRO3_MfClavier_to_strings(argument3)
                if mode=="":
                  return "PRO3 Reponse status fonctionnement clavier invalide"
                else:
                  return "PRO3 Reponse status fonctionnement clavier "+mode
              else:
                return "PRO3 Reponse status fonctionnement invalide"
            else:
              return "PRO3 inconnu"



          if self.RawReceived != None:
            if DoDebugMainLoop==True:
              print("EventRawReceived() Start")
            # https://stackoverflow.com/questions/45229304/await-only-for-some-time-in-python
            # https://stackoverflow.com/questions/37663560/websocket-recv-never-returns-inside-another-event-loop
            # https://stackoverflow.com/questions/54421029/python-websockets-how-to-setup-connect-timeout
            for item in self.RawReceived:        # Analyse le paquet reçu
                
                if type(item)==int:                                    # A supprimer, affichage en double du caractère reçu : Unknown BUG100% CPU
                  print("WARN : EventRawReceived() got INT type --> CHR()") # "+str(item)+"
                  itemdebug=chr(item)
                else:
                  itemdebug=item
                # self.DebugInput += "<<0x{:02x}>> ".format(ord(itemdebug)) # A supprimer, affichage en double du caractère reçu : Unknown BUG100% CPU



                if item == CHAR_ESC:        # Annonce une sequence ESC
                    self.GotEsc=True
                else:
                    if self.GotEsc==True:        # Traitement d'une sequence ESC reçue
                        if item == CHAR_PRO1:   # Annonce une sequence PRO1
                            self.GotEsc=False
                        if item == CHAR_PRO2:   # Annonce une sequence PRO2
                            self.GotEsc=False
                        if item == CHAR_PRO3:   # Annonce une sequence PRO3
                            self.GotEsc=False
                        if self.GotEsc == False:     # Annonce une sequence protocole
                            self.GotProSeq = (ord(item) - ord(CHAR_PRO1))+1
                            self.ProtocolSeq = ""
                            self.DebugInput += "<PRO{}> ".format(self.GotProSeq)
                        else:
                            self.GotEsc=False
                            if item == CHAR_CSI:
                                self.GotCsi = True
                                self.GotCsiSeq = ""
                            else:
                                self.AddItemToBuffer(CHAR_ESC)
                                self.AddItemToBuffer(item)       # Ici, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                    else:                               # On n'est pas dans le traitement d'une sequence ESC reçue
                        if self.GotProSeq > 0:               # On est dans le traitement d'une sequence protocole
                            self.ProtocolSeq += item         # Ici aussi, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                            self.GotProSeq -=1
                            if self.GotProSeq == 0:
                                #self.BufferInput+=CHAR_ESC
                                #self.BufferInput+=chr(ord(CHAR_PRO1)+len(self.ProtocolSeq)-1)
                                for item in self.ProtocolSeq:
                                    #self.BufferInput+=item
                                    self.DebugInput += "<0x{:02x}> ".format(ord(item))
                                if len(self.ProtocolSeq)==1:
                                  self.DebugInput += PRO1_to_strings(ord(self.ProtocolSeq[0]))
                                if len(self.ProtocolSeq)==2:
                                  self.DebugInput += PRO2_to_strings(ord(self.ProtocolSeq[0]),ord(self.ProtocolSeq[1]))
                                if len(self.ProtocolSeq)==3:
                                  self.DebugInput += PRO3_to_strings(ord(self.ProtocolSeq[0]),ord(self.ProtocolSeq[1]),ord(self.ProtocolSeq[2]))
                        else:                       # On n'est pas dans le traitement d'une sequence protocole reçue
                            if self.GotCsi == True:
                                self.GotCsiSeq += item         # Ici aussi, il faudrait pouvoir traiter directement un code de contrôle [BUG!]
                                if ord(item) >= 0x40:
                                    self.GotCsi = False
                                    self.BufferInput+=CHAR_ESC
                                    self.BufferInput+=CHAR_CSI
                                    self.DebugInput += "[CSI]"
                                    for item in self.GotCsiSeq:
                                        self.AddItemToBuffer(item)
                            else:
                                if item == CHAR_SEP:    # Annonce une touche de fonction
                                    self.GotSep=True
                                    self.DebugInput += "[SEP]"
                                else:
                                    if self.GotSep==True:    # Traitement d'une touche de fonction reçue
                                        if item == CHAR_ENVOI:
                                            self.GotSep=False
                                            self.DebugInput += "[ENVOI]"
                                            self.UpdateCurField()              # Met à jour le champ en cours avec BufferInput puis vide BufferInput 
                                            self.LoadBufferInputWithCurField() # Charge BufferInput avec le champ en cours
                                            self.CallModule('envoi',"Comment Envoi")
                                                
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
                                            self.GotSep=False
                                            self.DebugInput += "[SUITE]"
                                            #
                                            # Traitement des séquences de pages
                                            #
                                            if self.CurFile==self.LastFile:                          # Sur la derniere page
                                                if self.CurFile==self.FirstFile:                     # Sur la premiere page ==> Une seule page
                                                    self.DebugInput += "$OnlyOnePage$"
                                                    if (len(self.FieldList)<2) and (len(self.DisplayList)==0):  # On a au plus 1 seul champ et pas de liste
                                                      self.ArboLoop = 0
                                                      if (self.BufferInput.isdecimal()):                  # BufferInput contient une valeur decimale
                                                        if (int(self.BufferInput) < ARBO_MAXFASTFORWARD):                 # qui reste acceptable
                                                          if (len(self.TimerLink)>0) :
                                                            self.ArboLoop = int(self.BufferInput)
                                                          else:
                                                            if DoDebugFastForward==True:
                                                              print("SUITE depuis seule page sans TimerLink --> REFUSE")
                                                        else:
                                                          if (len(self.TimerLink)>0) :
                                                            self.ArboLoop = 1
                                                          else:
                                                            if DoDebugFastForward==True:
                                                              print("SUITE depuis seule page sans TimerLink --> REFUSE")
                                                          if DoDebugFastForward==True:
                                                            print("BufferInput contains too big value")
                                                      else:
                                                        if (len(self.TimerLink)>0) :
                                                          self.ArboLoop = 1
                                                        else:
                                                          if DoDebugFastForward==True:
                                                            print("SUITE depuis seule page sans TimerLink --> REFUSE")
                                                        if DoDebugFastForward==True:
                                                          print("BufferInput does not contains decimal value")
                                                      if (self.ArboLoop != 0):
                                                        self.SetArbo(self.TimerLink)
                                                      self.CurFile=self.FirstFile
                                                      self.DoSendPage=True
                                                    else:
                                                      if DoDebugFastForward==True:
                                                        print("SUITE depuis seule page mais Liste ou Champ sur la page --> REFUSE")
                                                else:                                                # Pas sur la premiere page ==> Il y a plusieurs pages
                                                    if len(self.FieldList) >0 :    # Si au moins 1 champ 
                                                      self.SetMessage(CHAR_COFF,False)

                                                    if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                                                      self.ArboLoop = 0
                                                      if (self.BufferInput.isdecimal()):                  # BufferInput contient une valeur decimale
                                                        if (int(self.BufferInput) < ARBO_MAXFASTFORWARD):                 # qui reste acceptable
                                                          if (len(self.TimerLink)>0) :
                                                            self.ArboLoop = int(self.BufferInput)
                                                          else:
                                                            if DoDebugFastForward==True:
                                                              print("SUITE depuis derniere page sans TimerLink --> REFUSE")
                                                        else:
                                                          if (len(self.TimerLink)>0) :
                                                            self.ArboLoop = 1
                                                          else:
                                                            if DoDebugFastForward==True:
                                                              print("SUITE depuis derniere page sans TimerLink --> REFUSE")
                                                          if DoDebugFastForward==True:
                                                            print("BufferInput contains too big value")
                                                      else:
                                                        if (len(self.TimerLink)>0) :
                                                          self.ArboLoop = 1
                                                        else:
                                                          if DoDebugFastForward==True:
                                                            print("SUITE depuis derniere page sans TimerLink --> REFUSE")
                                                        if DoDebugFastForward==True:
                                                          print("BufferInput does not contains decimal value")
                                                      if (self.ArboLoop != 0):
                                                        self.SetArbo(self.TimerLink)                                                          
                                                        if DoDebugFastForward==True:
                                                          print("SUITE sur derniere page - On a changes de noeud - ArboLoop="+str(self.ArboLoop)+" CurFile="+str(self.CurFile))
                                                      else:
                                                        self.CurFile=self.FirstFile
                                                        self.DoSendPage=True
                                                    else:
                                                      self.CurFile=self.FirstFile
                                                      self.DoSendPage=True
                                                      if DoDebugFastForward==True:
                                                        print("SUITE depuis derniere page mais Liste ou Champ sur la page --> REFUSE")
                                            else:                                                  # Pas sur la derniere page ==> Il y a plusieurs pages
                                                if len(self.FieldList) >0 :    # Si au moins 1 champ 
                                                  self.SetMessage(CHAR_COFF,False)
                                                if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                                                  if (self.BufferInput.isdecimal()):                  # BufferInput contient une valeur decimale
                                                    if (int(self.BufferInput) < ARBO_MAXFASTFORWARD):                 # qui reste acceptable
                                                      #
                                                      # Avancer dans la sequence avant de changer de noeud d'arbo (ToDo)
                                                      #                                           
                                                      self.ArboLoop = int(self.BufferInput)
                                                      self.CurFile += self.ArboLoop
                                                      self.ArboLoop -= self.ArboLoop - (self.CurFile - self.LastFile)
                                                      if (self.CurFile > self.LastFile):
                                                        if (len(self.TimerLink)>0) :
                                                          self.SetArbo(self.TimerLink)
                                                          self.CurFile -= 1
                                                          if DoDebugFastForward==True:
                                                            print("SUITE pas sur derniere page - On a changes de noeud - ArboLoop="+str(self.ArboLoop)+" CurFile="+str(self.CurFile))
                                                        else:
                                                          if DoDebugFastForward==True:
                                                            print("SUITE depuis page quelconque sans TimerLink --> REFUSE")
                                                          while (self.ArboLoop > 0) and (self.CurFile > self.LastFile):
                                                            self.CurFile  = self.FirstFile + self.ArboLoop
                                                            self.ArboLoop -= self.ArboLoop - (self.CurFile - self.LastFile)                                                                                                                      
                                                            if DoDebugFastForward==True:
                                                              print("SUITE pas sur derniere page - On boucle sur le noeud - ArboLoop="+str(self.ArboLoop)+" CurFile="+str(self.CurFile))
                                                          self.ArboLoop = 0
                                                          self.CurFile -= 1
                                                      else:
                                                        self.ArboLoop = 0
                                                        self.CurFile -= 1
                                                        if DoDebugFastForward==True:
                                                          print("SUITE pas sur derniere page - On reste sur le noeud - ArboLoop="+str(self.ArboLoop)+" CurFile="+str(self.CurFile))
                                                    else:
                                                      if DoDebugFastForward==True:
                                                        print("BufferInput contains too big value")
                                                  else:
                                                    if DoDebugFastForward==True:
                                                      print("BufferInput does not contains decimal value")
                                                else:
                                                  if DoDebugFastForward==True:
                                                    print("SUITE depuis une page quelconque mais Liste ou Champ sur la page --> REFUSE")
                                                self.DoSendPage=True
                                                self.CurFile+=1
                                            #
                                            # Traitement des listes de champs
                                            #
                                            if (self.CurField+1)>len(self.FieldList):
                                              self.DebugInput += "$NoField$"
                                            elif (self.CurField+1)==len(self.FieldList):
                                              if len(self.FieldList)==1:
                                                self.DebugInput += "$OnlyOneField$"
                                              else:
                                                self.UpdateCurField()
                                                self.PrevField=self.CurField
                                                self.RefreshCurField=True
                                                self.CurField=0
                                                self.LoadBufferInputWithCurField()
                                            else:
                                              self.UpdateCurField()
                                              self.PrevField=self.CurField
                                              self.RefreshCurField=True
                                              self.CurField+=1
                                              self.LoadBufferInputWithCurField()
                                            #
                                            # Traitement des listes
                                            #
                                            if len(self.DisplayList) :
                                              self.PageDisplayList += 1

                                              MyList=self.GetVarInArboClass(self.DisplayList[LIST_NAME],True)
                                              MyNbLin=self.DisplayList[LIST_NB_LIN]          # Définition des champs de la liste
                                              MyNbCol=self.DisplayList[LIST_NB_COL]          # Définition des champs de la liste      
                                              MyItemsPerPage=MyNbLin*MyNbCol
                                              if MyItemsPerPage>0:
                                                MyNbPage=len(MyList)//MyItemsPerPage
                                                if MyNbPage*MyItemsPerPage!=len(MyList):
                                                  MyNbPage=MyNbPage+1
                                              else:
                                                MyNbPage=1    # La liste n'est pas affichée - Il n'y a pas de nombre de pages mais il y en a forcément une quand même 
                                              if self.PageDisplayList >= MyNbPage:
                                                self.PageDisplayList=MyNbPage
                                              else:
                                                self.DoSendPage=True




                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('suite',"Comment Suite")
    
                                             
                                        if item == CHAR_RETOUR:
                                            self.GotSep=False
                                            self.DebugInput += "[RETOUR]"
                                            #
                                            # Traitement des séquences de pages
                                            #
                                            if self.CurFile==self.FirstFile:
                                                if self.CurFile==self.LastFile:
                                                    self.DebugInput += "$OnlyOnePage$"
                                                    if (len(self.RetourLink)>0) :
                                                      if len(self.FieldList) >0 :    # Si au moins 1 champ 
                                                        self.SetMessage(CHAR_COFF,False)
                                                      if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                                                        self.SetArbo(self.RetourLink)
                                                        self.CurFile=self.LastFile
                                                        self.DoSendPage=True
                                                      else:
                                                        print("RETOUR depuis seule page avec RetourLink mais Liste ou Champ sur la page --> REFUSE")
                                                else:
                                                    if (len(self.RetourLink)>0) :
                                                      if len(self.FieldList) >0 :    # Si au moins 1 champ 
                                                        self.SetMessage(CHAR_COFF,False)
                                                      if (len(self.FieldList)<2) and (len(self.DisplayList)==0):
                                                        self.SetArbo(self.RetourLink)
                                                      else:
                                                        print("RETOUR depuis premiere page avec RetourLink mais Liste ou Champ sur la page --> REFUSE")
                                                    self.CurFile=self.LastFile
                                                    self.DoSendPage=True
                                            else:
                                                if len(self.FieldList) >0 :    # Si au moins 1 champ 
                                                  self.SetMessage(CHAR_COFF,False)
                                                self.DoSendPage=True
                                                self.CurFile-=1
                                            #
                                            # Traitement des listes de champs
                                            #
                                            if (self.CurField+1)>len(self.FieldList):
                                              self.DebugInput += "$NoField$"
                                            elif len(self.FieldList)==1:
                                                self.DebugInput += "$OnlyOneField$"
                                            else:
                                              self.UpdateCurField()
                                              self.RefreshCurField=True
                                              self.PrevField=self.CurField
                                              if self.CurField >0:
                                                  self.CurField-=1
                                                  self.LoadBufferInputWithCurField()
                                              else:
                                                  self.CurField=len(self.FieldList)-1
                                                  self.LoadBufferInputWithCurField()
                                            #
                                            # Traitement des listes
                                            #
                                            if len(self.DisplayList) :
                                              self.PageDisplayList -= 1
                                              if self.PageDisplayList <= 0:
                                                self.PageDisplayList = 0
                                              else:
                                                self.DoSendPage=True
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('retour',"Comment Retour")
                                            
                                        if item == CHAR_REPETITION:
                                            self.GotSep=False
                                            self.DebugInput += "[REPETITION]"
                                            self.DoSendPage=True
                                        if item == CHAR_CORRECTION:
                                            self.GotSep=False
                                            self.DebugInput += "[CORRECTION]"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(self.FieldList):
                                              Cont=True
                                              Removed = False
                                              while (Cont == True) :
                                                #print("<0x{:02x}> ".format(ord(BufferInput[-2:-1])))
                                                if (Cont == True) and (len(self.BufferInput) > 1) and (ord(self.BufferInput[-2:-1]) == ord(CHAR_SS2.encode('utf-8'))) :
                                                    if chr(ord(self.BufferInput[-1:])) in CHAR_ACCENT_LIST :
                                                      print("Accent sans caractere retire silencieusement du buffer - Precedent chr sera aussi a retirer")
                                                      pass        # Accent sans caractère retiré silencieusement du buffer - Précédent chr sera aussi à retirer
                                                    else :
                                                      Cont=False  # Caractère spécial retiré du buffer 
                                                      print ("Caractere special retire du buffer")
                                                      Removed = True
                                                    self.BufferInput = self.BufferInput[:-2]
                                                else :
                                                  if (Cont == True) and (len(self.BufferInput) > 2) and (ord(self.BufferInput[-3:-2]) == ord(CHAR_SS2.encode('utf-8'))) :
                                                      if chr(ord(self.BufferInput[-2:-1])) in CHAR_ACCENT_LIST :
                                                        Cont=False  # Caractère accentué retiré du buffer
                                                        print("Caractere accentue retire du buffer")
                                                        Removed = True
                                                        self.BufferInput = self.BufferInput[:-3]
                                                  else :
                                                    if (Cont == True) and (len(self.BufferInput)>0) :
                                                      Cont=False  # Caractère normal retiré du buffer
                                                      print("Caractere normal retire du buffer")
                                                      Removed = True
                                                      self.BufferInput = self.BufferInput[:-1]
                                                    else :
                                                      print("Aucun caractere retire")
                                                      Cont = False
                                              if Removed == True :
                                                  try:
                                                    if not self.websocket.closed:
                                                      await self.websocket.send(((CHAR_BS + self.FieldList[self.CurField][FIELD_FILL] + CHAR_BS).encode('utf-8')).decode('utf-8','strict'))
                                                    else:
                                                      self.GotLib=True
                                                  except (websockets.exceptions.ConnectionClosedOK , websockets.exceptions.ConnectionClosedError) :
                                                    self.GotLib=True
                                                    if DoDebugAsync == True: 
                                                      print("Backspace cancelled [ClosedOK or ClosedError]")
                                                    pass

                                              else :
                                                self.DebugInput += "$EmptyBufferInput$"
                                                
                                        if item == CHAR_ANNULATION:
                                            self.GotSep=False
                                            self.DebugInput += "[ANNULATION]"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(self.FieldList):
                                              self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
                                              self.ClearBufferInput()
                                              self.RefreshCurField=True
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('annulation',"Comment Annulation")
                                              
                                        if item == CHAR_GUIDE:
                                            self.GotSep=False
                                            self.DebugInput += "[GUIDE]"
                                            if len(self.GuideLink)>0:
                                                self.StackList.append(self.ArboCur)
                                                self.SetArbo(self.GuideLink)
                                            else:
                                                self.DebugInput += "$NoGuideDefined$"
                                            #
                                            # Traitement du champ
                                            #
                                            if len(self.FieldList) and (self.DoSendPage==True):
                                              self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
                                              self.ClearBufferInput()
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('guide',"Comment Guide")
    
                                        if item == CHAR_SOMMAIRE:
                                            self.GotSep=False
                                            self.DebugInput += "[SOMMAIRE]"  
                                            if not self.StackList :
                                                self.DebugInput += "$TopLevelReached$"
                                            else :                                       
                                              self.SetArbo(self.StackList.pop())
                                            #
                                            # Traitement du champ
                                            #
                                            if len(self.FieldList) and (self.DoSendPage==True):
                                              self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
                                              self.ClearBufferInput()
                                              self.DebugInput += "$BufferCleared$"
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('sommaire',"Comment Sommaire")
                                            
                                        if item == CHAR_CONNECTION:
                                            self.GotLib=True
                                            self.GotSep=False
                                            self.DebugInput += "[CONNECTION]"
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('lib',"Connexion")
                                            break
                                        if item == CHAR_CONNECTION_MODEM:
                                            self.GotLib=True
                                            self.GotSep=False
                                            self.DebugInput += "[CONNECTION_MODEM]"
                                            #
                                            # Traitement des modules
                                            #
                                            self.CallModule('lib',"Modem")
                                            break
                                        if self.GotSep==True:
                                            self.GotSep=False                        
                                            if item > ' ':
                                                self.DebugInput += "<SEP>"+item
                                            else:
                                                self.DebugInput += "<SEP><0x{:02x}> ".format(ord(item))
                                    else:
                                        self.AddItemToBuffer(item)
            if DoDebugMainLoop==True:
              print("EventRawReceived() done")

    def EventMsg(self):
          if self.MsgReceived != None :
            if DoDebugMainLoop==True:
                print("MsgReceived '" + self.MsgReceived + "'")
            #
            # Message reçu
            #
            if (not self.websocket.closed) and (not self.GotLib==True):
              #self.TimerCount+=1
              self.CallModule('message',self.MsgReceived)
              self.DebugInput += "[MESSAGE]"
              #
              # Traitement du lien
              #
              #if len(self.TimerLink)>0:
              #    self.SetArbo(self.TimerLink)
              #else:
              #    self.DebugInput += "$NoTimerDefined$"
              #
              # Traitement du champ
              #
              #if len(self.FieldList) and (self.DoSendPage==True):
              #  self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
              #  self.ClearBufferInput()


    def EventTimer(self) :
          if self.TimerReceived != None :
            if DoDebugMainLoop==True:
              print("EventTimer() Received ")
            #
            # Timer
            #
            if (not self.websocket.closed) and (not self.GotLib==True):
              #
              # Traitement des séquences de pages
              #
              if self.CurFile < self.LastFile:
                  self.DoSendPage=True
                  self.CurFile+=1
              self.TimerCount+=1
              self.CallModule('timer',"Comment Timer "+str(self.TimerCount))
              self.DebugInput += "[TIMER]"
              if self.DoSendPage!=True:
                if len(self.TimerLink)>0:
                  self.SetArbo(self.TimerLink)
                else:
                  self.DebugInput += "$NoTimerDefined$"
              #
              # Traitement du champ
              #
              if len(self.FieldList) and (self.DoSendPage==True):
                self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
                self.ClearBufferInput()

    def EventTimeout(self):
          if (self.MsgReceived == None) and (self.RawReceived == None) and (self.TimerReceived == None):
            if DoDebugMainLoop==True:
              print("EventTimeout() Received ")
            #
            # Timeout
            #
            if (not self.websocket.closed) and (not self.GotLib==True):
              self.TimeoutCount+=1
              self.CallModule('timeout',"Comment TimeOut "+str(self.TimeoutCount))
              self.DebugInput += "[TIMEOUT]"
              if len(self.TimeoutLink)>0:
                  self.SetArbo(self.TimeoutLink)
              else:
                  self.DebugInput += "$NoTimeoutDefined$"
              #
              # Traitement du champ
              #
              if len(self.FieldList) and (self.DoSendPage==True):
                self.UpdateField(self.FieldList[self.CurField][FIELD_NAME],self.MySession,"")
                self.ClearBufferInput()

    async def ArboStart(self,ArboStart,path):
      #
      # Arrivée sur la première page de l'arborescence
      #
      try:
        self.SetArbo(ArboStart)
      except:
        err=sys.exc_info()
        for item in err:
          print(item)
        raise
      self.DeclareField("Text01")
      #
      # Demande le détail du contenu ROM/RAM et prépare leur réception
      #
      self.InsertBytes += (CHAR_ESC + CHAR_PRO1 + "{"+ CHAR_ENQ + CHAR_ESC + CHAR_PRO1 + "z").encode('utf-8') # ENQROM + ENQ RAM1 + ENQ RAM2
      self.ReplyRomRamExpect = 3 # Attends 3 items ROM/RAM
      self.ReplyRomRam = 0       # Attends ROM
      self.ReplyRomRamIndex = 0  # Aucun caractère reçu
      
      CHAR_BEEP=b'\x07\x00\x81\xff'    # Test 8 bits
      await self.websocket.send(CHAR_BEEP)
      await self.websocket.send(f"Connected * to {path} !")

    async def KillAllTasks(self):
      print("PyMoIPserver->KillAllTasks()")
      if not self._tasks[0].cancelled():
        print("Cancel 0") 
        self._tasks[0].cancel()  # Supprimer la tâche Raw
      if not self._tasks[1].cancelled():
        print("Cancel 1") 
        self._tasks[1].cancel()  # Supprimer la tâche Msg 
      if len(self._tasks)>2:
        if not self._tasks[2].cancelled():
          print("Cancel 2") 
          self._tasks[2].cancel()  # Supprimer la tâche Timer
      await asyncio.sleep(0.1) 
      if not self.websocket.closed:
        await self.websocket.close()
      self.FreeAllFields()
