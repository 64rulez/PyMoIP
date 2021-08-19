import sys        # Pour les messages d'erreur
import asyncio    # Pour await/async
import threading  # Necessaire pour asyncio local (il faut une autre thread pour faire une autre boucle asyncio - sinon, la coroutine async n'est jamais executee dans le module [avant la fin])
import requests   # Nécessaire pour faire une requête HTTP
from Server.PyMoIP_global import *    # Définition des constantes

YellowPages=""

def comment():
  #
  # Ceci est une variable locale
  #
  zizi="Variable locale"
  #
  # Variables globales
  #
  global_refs['pet_06']='truc_bar'    # Modification d'une variable globale
  #
  print("Zizi est : " + zizi)
  print("Pet_05 est : " + global_refs['pet_05'])
  #
  # Variables locales à hello (module parent)
  #
  print(local_refs['Blabla'])
  (local_refs['Blabla'])='BarWozHere'  # Modification d'une variable locale au module parent ==> Ne fonctionne pas !!!
  print(local_refs['Blabla'])
  #
  # Objet local à hello (module parent)
  #
  print("Item d'un objet du module parent : " + (local_refs['MyArbo']).ArboCur)
  (local_refs['MyArbo']).ArboCur="BarWazHereToo"    # Modification d'un objet local au module parent

#https://stackoverflow.com/questions/55409641/asyncio-run-cannot-be-called-from-a-running-event-loop
class RunThread(threading.Thread):
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.result = False
        super().__init__()
    def run(self):
        self.result = asyncio.run(self.func(*self.args, **self.kwargs))

def run_async(func, *args, **kwargs):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        if EnableTrace:
          print('Async event loop already running -> New thread')
        thread = RunThread(func, args, kwargs)
        thread.start()
        thread.join()
        return thread.result
    else:
        if EnableTrace:
          print('Starting new event loop')
        return asyncio.run(func(*args, **kwargs))

def HandleError():      # Ici, MyArbo n'est pas nécessairement défini .... On utilise (local_refs['MyArbo']).
    print ("ERR:"+__file__+"() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
    err=sys.exc_info()
    cnt=0
    for item in err:
      cnt+=1
      print("ERROR#"+str(cnt))
      print(item)
    #old await local_refs['websocket'].send("Error".encode('utf-8'))
    #if not (local_refs['MyArbo']).StackList :
    if not (local_refs['self']).StackList :
        print("$TopLevelReached$")
        #(local_refs['MyArbo']).DebugInput += "$TopLevelReached$"
        (local_refs['self']).DebugInput += "$TopLevelReached$"
    else :                                       
      (local_refs['self']).SetArbo((local_refs['self']).StackList.pop())
      #(local_refs['MyArbo']).SetArbo((local_refs['MyArbo']).StackList.pop())
      #old (local_refs['MyArbo']).InsertBytes= (chr(31)+"00"+chr(24)+chr(27)+"T ERR: " + str(sys.exc_info()[0])+chr(10)).encode('utf-8') # Hello
    #(local_refs['MyArbo']).SetMessage("ERR:" + str(sys.exc_info()[0]),False)
    (local_refs['self']).SetMessage("ERR:" + str(sys.exc_info()[0]),False)


def init(global_refs,local_refs,comment):
  global CommentFromInit
  global EnableTrace
  global YellowPages
  #  
  #    init() Est appelee lors de l'initialisation du module (changement de position dans l'arbo)
  #    
  #    Permet d'initialiser des variables qui seront utilisées plus tard dans le traitement des touches, charger des fichiers, etc
  #       
  #
  EnableTrace=False      # N'affiche pas les messages de debuggage si False
  MyArbo=local_refs['self']
  
  if EnableTrace:
    print (__file__ + " INIT (" + comment + ")")
  Success=True # Il n'est pas prévu d'échec sur l'init
  try:
    CommentFromInit=comment
    #print("Getting Minitel yellow pages ...")
    # Voir comment lancer un thread pour avoir la réponse plus tard ....
    if YellowPages=="":
      temp = "Searching Teletel.org ..."
      temp=(MyArbo.SetMessage(temp, False, True)).decode('utf-8','strict') # Présentation du message à envoyer
      Success=run_async(_async_send, MyArbo.websocket,temp)        
  
      MinitelYellowPages='http://teletel.org/minitel-yp.json'
      r=requests.get(MinitelYellowPages)
      if r.status_code==200:
        YellowPages=r.json()
        if EnableTrace:
          for server in YellowPages['servers']:
            print(server.get("name"))
      else:
        if EnableTrace:
          print ("Failled to get Minitel Yellow Pages from '{}' : Error {}".format(MinitelYellowPages,r.status_code))
        
    if True:            #
      Success=True      # Ne jamais toucher au champ en cours sur init reçu
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[init()] Exiting from "+__file__)
    return Success

def message(global_refs,local_refs,comment):
  if EnableTrace:
    print (__file__ + " MESSAGE (" + comment + ")")
  MyArbo=local_refs['self']
  Success=False
  try:
    # Comment = message
    # "GTW:StateRedir=NewState" ==> Nouvel état de la gateway
    #          if Result[0].upper() == "USERREDIRECTING":               print("GatewayLink() UserRedirecting : "+str(Result[4]))               NewState=START_REDIR
    #          if Result[0].upper() == "USERREDIRECTENDED":             print("GatewayLink() UserRedirectEnded : "+str(Result[4]))             NewState=NO_REDIR
    #          if Result[0].upper() == "USERREDIRECTED":                print("GatewayLink() UserRedirected : "+str(Result[4]))                NewState=OK_REDIR
    if (comment.upper()=="GTW:StateRedir=NewState".upper()):
      if MyArbo.StateRedir==NO_REDIR:
        run_async(_async_send,MyArbo.websocket,(chr(31)+"00"+chr(24)+"LIB00"+chr(10)).encode('utf-8'))
        _AddCost(global_refs,local_refs,0.0)    # Rappel du cout (si demande d'affichage)
        MyArbo.DoSendPage=True
        if EnableTrace:
          print("[message() ]GTW:StateRedir==NO_REDIR =>DoSendPage=True")
      if MyArbo.StateRedir==OK_REDIR:
        _AddCost(global_refs,local_refs,0.12)    # 12 centimes par connexion
      if MyArbo.StateRedir==START_REDIR:
        run_async(_async_send,MyArbo.websocket,(chr(31)+"00"+chr(27)+"T "+MyArbo.CurCostName+chr(27)+"P "+MyArbo.SearchLink+chr(24)+chr(10)).encode('utf-8'))
    if True:          #
      Success=True    # Ne jamais toucher au champ en cours sur message reçu
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[message() ]Exiting from "+__file__)
    return Success

  
def lib(global_refs,local_refs,comment):
  print (__file__ + " LIB (" + comment + ")")
  Success=False
  try:
    # Comment =
    # Connexion : Touche Connexion/Fin
    # Modem     : SEP/0x59 ((Dé)connexion modem)
    # Closed    : websocket.closed             (éventuellement, déconnexion déjà traitée)
    # Bye       : Fin de la boucle principale  (éventuellement avec une erreur)
    if False:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[lib() ]Exiting from "+__file__)
    return Success

def _ShowCost(local_refs):
  MyArbo=local_refs['self']

  if MyArbo.ShowCost==True:
    return run_async(_async_send, MyArbo.websocket,(chr(31)+"@]"+chr(27)+"P "+str('{0:,.2f}'.format(MyArbo.CurCost))+"Fr"+chr(24)+chr(10)).encode('utf-8'))
  else:
    return True

def _AddCost(global_refs,local_refs,ToAdd):
    MyArbo=local_refs['self']
    MyList=global_refs['ListSession']
    
    MyArbo.CurCost=MyArbo.CurCost+ToAdd
    if MyArbo.ShowCost==True:
      Found=-1
      Count=0
      Output=False
      for item in MyList:
          if item[LIST_SESSION_SESSION]==MyArbo.MySession:
            Found=Count
            break
          Count+=1
      if Found>-1:
          #if MyList[Found][LIST_SESSION_MYARBO].StateRedir==NO_REDIR:
            Output=True
          #else:
          #  if EnableTrace:
          #    print("No output as redirect")
      else:
        if EnableTrace:
          print("Not found MySession in ListSession")
      if Output==True:
        Success=_ShowCost(local_refs)
      else:
        Success=True        # Ne jamais toucher au champ en cours sur timeout reçu
  
def timer(global_refs,local_refs,comment):
  if EnableTrace:
    print (__file__ + " TIMER (" + comment + ")")
  Success=False
  MyArbo=local_refs['self']
  MyList=global_refs['ListSession']
  
  try:
    _AddCost(global_refs,local_refs,MyArbo.CurCostAdd)    
   
    if True:        #
      Success=True  # Ne jamais toucher au champ en cours sur timer reçu
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[timer()] Exiting from "+__file__)
    return Success

async def _async_send(websocket,temp):
    await websocket.send(temp)
    if EnableTrace:
      print("_async_send done")
    return True
              
def timeout(global_refs,local_refs,comment):
  if EnableTrace:
    print (__file__ + " TIMEOUT (" + comment + ")")
  MyArbo=local_refs['self']
  MyList=global_refs['ListSession']
  
  Success=False
  try:
    temp = "Timeout #"+str(MyArbo.TimeoutCount)
    #MyArbo._RcvQueue.put_nowait(temp) # Pong timeout as message !
    
    Found=-1
    Count=0
    Output=False
    for item in MyList:
        if item[LIST_SESSION_SESSION]==MyArbo.MySession:
          Found=Count
          break
        Count+=1
    if Found>-1:
        if MyList[Found][LIST_SESSION_MYARBO].StateRedir==NO_REDIR:
          Output=True
        else:
          if EnableTrace:
            print("No output as redirect")
    else:
      if EnableTrace:
        print("Not found MySession in ListSession")
    if Output==True:
      temp=(MyArbo.SetMessage(temp, False, True)).decode('utf-8','strict')
      Success=run_async(_async_send, MyArbo.websocket,temp)
    else:
      Success=True        # Ne jamais toucher au champ en cours sur timeout reçu
    if EnableTrace:
      print(Success)
    #Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[timeout()] Exiting from "+__file__)
    return Success

  
def guide(global_refs,local_refs,comment):
  print (__file__ + " GUIDE (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[guide()] Exiting from "+__file__)
    return Success


  
def suite(global_refs,local_refs,comment):
  print (__file__ + " SUITE (" + comment + ")")
  Success=False
  MyArbo=local_refs['self']
  try:
    if EnableTrace:
      print(MyArbo.FieldList)
      print(len(MyArbo.FieldList))
    if len(MyArbo.FieldList)==1 :               # Si seulement un champ est défini
      #
      # Cette technique ne marche pas - les listes de tous les nouveaux objets sont modifiées - Why ????
      #
      temp="Donn"+CHAR_SS2+"Bees compl"+CHAR_SS2+"Bementaires : "
      tempL=18
      tempC=1
      MyArbo.ConstList.append([tempL,tempC,[],temp,0,"."])
      temp=CHAR_US+chr(64+tempL)+chr(64+tempC)+temp
      Success=run_async(_async_send, MyArbo.websocket,temp)        
      #
      # Ajout d'un champ supplémentaire et passage sur ce champ
      #
      MyArbo.FieldList.append([18,26,[],"Text02",15,"."])
      MyArbo.UpdateCurField()
      MyArbo.PrevField=MyArbo.CurField
      MyArbo.RefreshCurField=True
      MyArbo.CurField+=1
      MyArbo.LoadBufferInputWithCurField()
      MyArbo.FieldList=MyArbo.FieldList
      MyArbo.ConstList=MyArbo.ConstList
#    if False:
    Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[suite()] Exiting from "+__file__)
    return Success



def retour(global_refs,local_refs,comment):
  print (__file__ + " RETOUR (" + comment + ")")
  Success=False
  try:
    #if False:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[retour()] Exiting from "+__file__)
    return Success


  
def annulation(global_refs,local_refs,comment):
  print (__file__ + " ANNULATION (" + comment + ")")
  Success=False
  try:
    MyGtw=(local_refs['self']).MyGtw
    MyGtw._outgoing_gateway_link_queue.put_nowait("blabla")
    if False:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[annulation()] Exiting from "+__file__)
    return Success


def sommaire(global_refs,local_refs,comment):
  print (__file__ + " SOMMAIRE (" + comment + ")")
  MyArbo=local_refs['self']
  Success=False
  try:
    MyArbo.ShowCost=True
    Success=_ShowCost(local_refs)
    if False:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[sommaire()] Exiting from "+__file__)
    return Success


def envoi (global_refs,local_refs,comment):
  print (__file__ + " ENVOI (" + comment + ")")
  Success=False
  #MyArbo=local_refs['MyArbo']
  MyArbo=local_refs['self']
  if EnableTrace:
    print(CommentFromInit)

  try:
    if EnableTrace:
      print(MyArbo.FieldList)
      print(len(MyArbo.FieldList))
    if len(MyArbo.FieldList)>0 :               # Si au moins un champ est défini
      #(local_refs['UpdateCurField'])()
      #  UpdateField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession,BufferInput)
      #  ClearBufferInput()
      #
      # ==> Sauvegarde le contenu de BufferInput dans la variable définie pour le champ en cours de saisie, puis supprime le contenu du buffer de saisie
      #     
      #
                #zz    for server in YellowPages['servers']:
                #zz        if server.get("name").upper() == nom:
                #zz            minitel.ConnectionString=server.get("address")
                #zz            print ("Found address")

        KeywordLink = ""
        SearchLink=MyArbo.BufferInput.upper()
        #
        # Recherche des données de connexion dans les "pages jaunes"
        #
        SearchIt=True
        while SearchIt==True:        # On bouclera si on trouve un alias
          SearchIt=False
          for server in YellowPages['servers']:
            if server.get("name").upper() == SearchLink:
              AliasLink=server.get("alias")
              if type(AliasLink) is str:        # On a un alias,
                SearchIt=True                   # Boucler et chercher à quoi ca correspond
                SearchLink=AliasLink
                #print("Found alias '"+AliasLink+"'")
              else:
                #print("Found '"+SearchLink+"'")
                print(server)
                KeywordLink=server.get("address")  # On a une vraie entrée
                KeywordPing=server.get("ping")
                KeywordSub=server.get("subprotocol")
                KeywordTarif=server.get("tarif")
                KeywordCost=server.get("cost")
                if len(KeywordSub)==0:
                  KeywordSub="[]"
                else:
                  KeywordSub=KeywordSub.split("[")[1]
                  KeywordSub=KeywordSub.split("]")[0]
                  temp="["
                  SubList=KeywordSub.split(",")
                  Count=0
                  for Sub in SubList:
                    if Count>0:
                      temp+=","
                    temp+=('"'+Sub+'"')
                    Count+=1
                  KeywordSub=temp+"]"
                  print(KeywordSub)
              break
              
        if KeywordLink == "":
          if EnableTrace:
            print("module_teletel/envoi() : $Server not found --> MyItem=0$")
          MyArbo.DebugInput += "$Server not found --> MyItem=0$"
          MyArbo.SetMessage("Serveur inconnu",False)
          MyItem=0
        else:
          #
          # Recherche de notre PID pour la gateway
          #
          MyList=global_refs['ListSession']
          Found=-1
          Count=0
          for item in MyList:
              if item[LIST_SESSION_SESSION]==MyArbo.MySession:
                Found=Count
              Count+=1
          if Found>-1:
            if EnableTrace:
              print("module_envoi/envoi() : Known server selected '" + MyArbo.BufferInput.upper() + "'  --> MyItem=-1$")
              print("Server address : '" + KeywordLink+"'")
              print(global_refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])
              print ((global_refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])[0]+","+str(MyArbo.MySession)+","+KeywordLink+","+KeywordPing+","+KeywordSub)
            if len(global_refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])>0:
              #
              # Informer l'utilisateur que la redirection est en cours
              #
              #MyArbo.SetMessage("Connexion a '"+SearchLink+"' ...",False)
              #temp=(MyArbo.SetMessage("Connexion a '"+SearchLink+"' ...", False, True)).decode('utf-8','strict')
              #Success=run_async(_async_send, MyArbo.websocket,temp)
              MyArbo.SearchLink=SearchLink
              if KeywordTarif==None:
                KeywordTarif="T?"
              MyArbo.CurCostName=KeywordTarif
              if KeywordCost==None:
                KeywordCost="0.0"
              MyArbo.CurCost=float(KeywordCost)              
              #
              # Ordonner à la gateway de rediriger l'utilisateur
              #
              MyGtw=(local_refs['self']).MyGtw
              #MyGtw=global_refs['MyGtw']
              try:
                MyGtw._outgoing_gateway_link_queue.put_nowait(((global_refs['ListSession'][Found][LIST_SESSION_FROMGATEWAY])[0]+","+str(MyArbo.MySession)+",CONNECT,"+KeywordLink+","+KeywordPing+","+KeywordSub).encode('utf-8'))
                Success=True
                MyItem=-1
              except:
                  err=sys.exc_info()
                  cnt=0
                  for item in err:
                    cnt+=1
                    print("ERROR#"+str(cnt))
                    print(item)
                  raise  
              #MyArbo.StackList.append(MyArbo.ArboCur)
              #MyArbo.SetArbo(KeywordLink)
              #MyArbo.DoSendPage=True
            else:
              MyArbo.SetMessage("Gateway not found",False)
          else:
            MyArbo.SetMessage("PID not found",False)
        

        #if EnableTrace:
        #  print("$NoListOrMenuToValidateWith$")
        #MyArbo.DebugInput += "$NoListOrMenuToValidateWith$"
        #MyArbo.SetMessage("Aucun choix propose",False)
    else:
      if EnableTrace:
        print("$NoFieldIsDefined$")
      MyArbo.DebugInput += "$NoFieldIsDefined$"
      MyArbo.SetMessage("Aucun champ a valider",False)

  except:
    HandleError()
  finally:
    if EnableTrace:
      print("[envoi()] Exiting from "+__file__)
    return Success


def RemovedFromEnvoi():
  def CheckKeyword():
    if EnableTrace:
      print("module_menu/CheckKeyword() : BufferInput after Load()")
      print(MyArbo.BufferInput)
    try:
      MyItem=int(MyArbo.BufferInput)
      MyItem=abs(MyItem)
      if EnableTrace:
        print(int(MyArbo.BufferInput))
    except ValueError:
      if len(MyArbo.KeywordList)>0:
        KeywordLink=""
        if EnableTrace:
          print (MyArbo.KeywordList)
        for Keyword in MyArbo.KeywordList:
          if MyArbo.BufferInput.upper() == Keyword[0].upper():
            KeywordLink=Keyword[1]
        if KeywordLink == "":
          if EnableTrace:
            print("module_menu/CheckKeyword() : $Keyword not found --> MyItem=0$")
          MyArbo.DebugInput += "$Keyword not found --> MyItem=0$"
          MyArbo.SetMessage("Mot cle inconnu",False)
          MyItem=0
        else:
          if EnableTrace:
            print("module_menu/CheckKeyword() : Keyword Selected '" + MyArbo.BufferInput.upper() + "'  --> MyItem=-1$")
          MyArbo.StackList.append(MyArbo.ArboCur)
          MyArbo.SetArbo(KeywordLink)
          MyArbo.DoSendPage=True
          Success=True
          MyItem=-1
      else:
        MyItem=0
        if EnableTrace:
          print("module_menu/CheckKeyword() : Except ValueError and no KeywordList => MyItem==0")
      pass 
    return MyItem

    if EnableTrace:
      if False:
        print("UpdateField")
        print(local_refs['UpdateField'])
        print("FIELD_NAME")
        print(local_refs['FIELD_NAME'])
        print("MyArbo.FieldList[MyArbo.CurField][FIELD_NAME]")
        print((local_refs['MyArbo']).FieldList[(local_refs['MyArbo']).CurField][(local_refs['FIELD_NAME'])])
        print("MySession")
        print((local_refs['MySession']))
        print("BufferInput")
        print((local_refs['BufferInput']))
        (local_refs['UpdateField'])((local_refs['MyArbo']).FieldList[(local_refs['MyArbo']).CurField][(local_refs['FIELD_NAME'])],(local_refs['MySession']),(local_refs['BufferInput']))
        (local_refs['BufferInput'])=""
        print("BufferInput after clear")
        print((local_refs['BufferInput']))
        print("-------------")
        #(local_refs['LoadBufferInputWithCurField'])()
        #BufferInput=GetField(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession).decode('utf-8','strict')
        (local_refs['BufferInput'])=(local_refs['GetField'])((local_refs['MyArbo']).FieldList[(local_refs['MyArbo']).CurField][(local_refs['FIELD_NAME'])],(local_refs['MySession'])).decode('utf-8','strict')
        print("local_refs[BufferInput]")
        print(local_refs['BufferInput'])
    if len (MyArbo.CurrentList) >0:          # Si au moins 1 item existe dans la liste
      if EnableTrace:
        print("TestAvecCurrentList (liste de menu affichee)")
        print (MyArbo.CurrentList)
      #MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],MySession)
      #print(int(MyArbo.FieldList[MyArbo.CurField][FIELD_NAME],base=10))
      MyItem=CheckKeyword()
      if MyItem>-1:
        if (MyItem>0) :
          if (MyItem<=len(MyArbo.CurrentList)):
            if EnableTrace:
              print("Item Selected '" + local_refs['MyArbo'].CurrentList[MyItem-1][0] + "' in " + local_refs['MyArbo'].DisplayList[0])
            #print("MyArbo.ArboCur après bar()" + MyArbo.ArboCur)
            MyArbo.StackList.append(MyArbo.ArboCur)
            MyArbo.SetArbo(MyArbo.CurrentList[MyItem-1][1])
            MyArbo.DoSendPage=True
            Success=True
            if EnableTrace:
              print("ModuleMenu() MyArbo.ArboCur apres envoi [WithList] " + MyArbo.ArboCur)
              print(MyArbo.PrefixFile)
              print(MyArbo.PostfixFile)
              print(MyArbo.PageDir)
              if (False) :
                print("SetArbo() = success")
                MyArbo.BufferInput=""
                print("BufferInput cleared")
                (local_refs['UpdateField'])((local_refs['MyArbo']).FieldList[(local_refs['MyArbo']).CurField][(local_refs['FIELD_NAME'])],(local_refs['MySession']),MyArbo.BufferInput)
          else:
            if EnableTrace:
              print("$Val(MyItem)>len(MyArbo.CurrentList) --> Index selected over len(list)$")
            MyArbo.DebugInput += "$Val(MyItem)>len(MyArbo.CurrentList) --> Index selected over len(list)$"
            MyArbo.SetMessage("Choix non propose (>max)",False)
        else:
          if EnableTrace:
            print("$Val(MyItem)==0 --> No index selected in list$")
          try:
            MyItem=int(MyArbo.BufferInput)
            MyArbo.DebugInput += "$Val(MyItem)==0 --> No index selected in list$"
            MyArbo.SetMessage("Choix non propose (==0)",False)
          except ValueError:
            pass
    elif  len (MyArbo.MenuList) >0:          # Si au moins 1 item existe dans la liste Menu:
      # Aucune liste n'est affichée - Essayer avec MenuList 
      MyItem=CheckKeyword()
      if EnableTrace:
        print("TestAvecMenuList (liste de menu pas affichee)")
      if MyItem>-1:        # Pas de mot clé trouvé
        if (MyItem>0) :    # On a saisi une valeur
          if (MyItem<=len(MyArbo.MenuList)):
            if EnableTrace:
              print("Item Selected '" + local_refs['MyArbo'].MenuList[MyItem-1][0] + "' in MenuList[])")
              print("MyArbo.ArboCur apres bar()" + MyArbo.ArboCur)
            MyArbo.StackList.append(MyArbo.ArboCur)
            MyArbo.SetArbo(MyArbo.MenuList[MyItem-1][1])
            MyArbo.DoSendPage=True
            Success=True
            if EnableTrace:
              print("ModuleMenu() MyArbo.ArboCur apres envoi [NoList] " + MyArbo.ArboCur)
              print(MyArbo.PrefixFile)
              print(MyArbo.PostfixFile)
              print(MyArbo.PageDir)
              if (False) :
                print("SetArbo() = success")
                MyArbo.BufferInput=""
                print("BufferInput cleared")
                (local_refs['UpdateField'])((local_refs['MyArbo']).FieldList[(local_refs['MyArbo']).CurField][(local_refs['FIELD_NAME'])],(local_refs['MySession']),MyArbo.BufferInput)
          else:
            if EnableTrace:
              print("$Val(MyItem)>len(MyArbo.CurrentList) --> Index selected over len(list)$")
            MyArbo.DebugInput += "$Val(MyItem)>len(MyArbo.CurrentList) --> Index selected over len(list)$"
            MyArbo.SetMessage("Choix non propose (>max)",False)
        else:
          if EnableTrace:
            print("$Val(MyItem)==0 --> No index selected in NO list$")
          try:
            MyItem=int(MyArbo.BufferInput)
            MyArbo.DebugInput += "$Val(MyItem)==0 --> No index selected in NO list$"
            MyArbo.SetMessage("Choix non propose (=0)",False)
          except ValueError:
            pass
    #else :