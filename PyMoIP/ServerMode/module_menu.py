import sys        # Pour les messages d'erreur
import asyncio    # Pour await/async
import threading  # Necessaire pour asyncio local (il faut une autre thread pour faire une autre boucle asyncio - sinon, la coroutine async n'est jamais executee dans le module [avant la fin])

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
    #await local_refs['websocket'].send("Error".encode('utf-8'))
    if not (local_refs['MyArbo']).StackList :
        print("$TopLevelReached$")
        (local_refs['MyArbo']).DebugInput += "$TopLevelReached$"
    else :                                       
      (local_refs['MyArbo']).SetArbo((local_refs['MyArbo']).StackList.pop())
      #(local_refs['MyArbo']).InsertBytes= (chr(31)+"00"+chr(24)+chr(27)+"T ERR: " + str(sys.exc_info()[0])+chr(10)).encode('utf-8') # Hello
    (local_refs['MyArbo']).SetMessage("ERR:" + str(sys.exc_info()[0]),False)


def init(global_refs,local_refs,comment):
  global CommentFromInit
  global EnableTrace
  #  
  #    init() Est appelee lors de l'initialisation du module (changement de position dans l'arbo)
  #    
  #    Permet d'initialiser des variables qui seront utilisées plus tard dans le traitement des touches, charger des fichiers, etc
  #       
  #
  EnableTrace=True      # N'affiche pas les messages de debuggage si False
  
  print (__file__ + " INIT (" + comment + ")")
  Success=True
  try:
    CommentFromInit=comment
    if True:
      Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("Exiting from "+__file__)
    return Success

  
def lib(global_refs,local_refs,comment):
  print (__file__ + " LIB (" + comment + ")")
  Success=False
  try:
    # Comment =
    # Connexion
    # Modem
    # Closed
    # Bye
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success

def timer(global_refs,local_refs,comment):
  print (__file__ + " TIMER (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success

async def _timeout(websocket,temp):
    await websocket.send(temp)
    if EnableTrace:
      print("_timeout done")
    return True
              
def timeout(global_refs,local_refs,comment):
  if EnableTrace:
    print (__file__ + " TIMEOUT (" + comment + ")")
  MyArbo=local_refs['MyArbo']
  Success=False
  try:
    temp = "Timeout #"+str(MyArbo.TimeoutCount)
    MyArbo._RcvQueue.put_nowait(temp)
    temp=(MyArbo.SetMessage(temp, False, True)).decode('utf-8','strict')
    Success=run_async(_timeout, MyArbo.websocket,temp)        
    if EnableTrace:
      print(Success)
    #Success=True
  except:
    HandleError()
  finally:
    if EnableTrace:
      print("Exiting from "+__file__)
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
    print("Exiting from "+__file__)
    return Success


  
def suite(global_refs,local_refs,comment):
  print (__file__ + " SUITE (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success



def retour(global_refs,local_refs,comment):
  print (__file__ + " RETOUR (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success


  
def annulation(global_refs,local_refs,comment):
  print (__file__ + " ANNULATION (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success


def sommaire(global_refs,local_refs,comment):
  print (__file__ + " SOMMAIRE (" + comment + ")")
  Success=False
  try:
    if False:
      Success=True
  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success


def envoi (global_refs,local_refs,comment):
  print (__file__ + " ENVOI (" + comment + ")")
  Success=False
  MyArbo=local_refs['MyArbo']
  if EnableTrace:
    print(CommentFromInit)


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
      else :
        if EnableTrace:
          print("$NoListOrMenuToValidateWith$")
        MyArbo.DebugInput += "$NoListOrMenuToValidateWith$"
        MyArbo.SetMessage("Aucun choix propose",False)
    else:
      if EnableTrace:
        print("$NoFieldIsDefined$")
      MyArbo.DebugInput += "$NoFieldIsDefined$"
      MyArbo.SetMessage("Aucun champ a valider",False)

  except:
    HandleError()
  finally:
    print("Exiting from "+__file__)
    return Success


