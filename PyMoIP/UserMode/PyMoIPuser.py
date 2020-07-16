#!/usr/bin/env python
# -*- coding: utf-8 -*-

from serial import Serial      # Liaison physique avec le Minitel
from threading import Thread   # Threads pour l’émission/réception
from queue import Queue, Empty # Files de caractères pour l’émission/réception

import time
import sys
from minitel.Minitel import Minitel,Empty
from minitel.ui.Menu import Menu
from minitel.ui.ChampTexte import ChampTexte
from minitel.ui.Label import Label
from minitel.ui.MyClass import MyClass

import requests

print("Getting Minitel yellow pages ...")
MinitelYellowPages='http://teletel.org/minitel-yp.json'
r=requests.get(MinitelYellowPages)
if r.status_code==200:
    YellowPages=r.json()
    for server in YellowPages['servers']:
        print(server.get("name"))
else:
    print ("Failled to get Minitel Yellow Pages from '{}' : Error {}".format(MinitelYellowPages,r.status_code))
    exit()
    

from minitel.constantes import (SS2, SEP, ESC, CSI, PRO1, PRO2, PRO3, MIXTE1,
    MIXTE2, TELINFO, ENQROM, SOH, EOT, TYPE_MINITELS, STATUS_FONCTIONNEMENT,
    LONGUEUR_PRO2, STATUS_TERMINAL, PROG, START, STOP, LONGUEUR_PRO3,
    RCPT_CLAVIER, ETEN, C0, MINUSCULES, RS, US, VT, LF, BS, TAB, CON, COF,
    AIGUILLAGE_ON, AIGUILLAGE_OFF, RCPT_ECRAN, EMET_MODEM, FF, CAN, BEL, CR,
    SO, SI, B300, B1200, B4800, B9600, REP, COULEURS_MINITEL,
    CAPACITES_BASIQUES, CONSTRUCTEURS,
    #Touches de fonction
    ENVOI, RETOUR, REPETITION, GUIDE, ANNULATION, SOMMAIRE, CORRECTION, SUITE, CONNEXION
    )

from unicodedata import normalize
from binascii import unhexlify
#from minitel.Sequence import Sequence # Gestion des séquences de caractères

from ws4py.client.threadedclient import WebSocketClient # Liaison WebSocket avec un serveur

import select
import tty
import termios

def isKeyboardData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

class WsMinitelClient(WebSocketClient):
    def opened(self):
        """def data_provider():
            for i in range(1, 200, 25):
                yield "#" * i
                
        self.send(data_provider())"""
        print ("WebSocket Connected - ESC to close")
        if minitel.DisplayDebug != 0:
            print ("DisplayDebug is ON [d or D to toggle]")
        else:
            print ("DisplayDebug is OFF [d or D to toggle]")
        minitel.ConnectionState = "Connected"
        self.received_messages = 0
        self.PrevWasEsc = False
        self.CharToExtract = 0

    def closed(self, code, reason):
        print(("WebSocket Closed down", code, reason))
        self.debug_message_flush()
        minitel.ConnectionState = "WaitingCall" # "Booting" #"Closed"
    
    def add_debug_char (self, item):
        minitel.DisplayDebugString += item
        if len(minitel.DisplayDebugString) == 16:
            StringToDisplay=""
            for char in minitel.DisplayDebugString:
                StringToDisplay += "{:02x} ".format(ord(char))
            StringToDisplay += " : "
            for char in minitel.DisplayDebugString:
                if char.encode('ascii') >= ' '.encode('ascii'):
                    StringToDisplay += char
                else:
                    StringToDisplay += "."
            print (StringToDisplay)
            minitel.DisplayDebugString=""

    def debug_message (self, MyStr):
        if minitel.DisplayDebug != 0:
            for item in MyStr:
                self.add_debug_char(item)

    def debug_message_flush (self):
        if minitel.DisplayDebug != 0:
            while len(minitel.DisplayDebugString) > 0:
                self.add_debug_char(' ')
            print("DebugFlushed")

    def CheckFilterProtocol(self):
        ProtocolString=chr(0x1b)
        if len(self.BufferProtocol)==0:
            ProtocolString=chr(0x05)
            ProtocolStringToDisplay="Got ENQ"
        if len(self.BufferProtocol)==1:
            ProtocolStringToDisplay="Got ESC 0x61"
        if len(self.BufferProtocol)>1:
            ProtocolStringToDisplay="Got Protocol : PRO{} ".format(len(self.BufferProtocol)-1)
            for char in self.BufferProtocol:
                ProtocolStringToDisplay += "{:02x} ".format(ord(char))
        print("======================")
        print(ProtocolStringToDisplay)
        print("======================")
        ProtocolString += self.BufferProtocol
        if ord(self.BufferProtocol[0]) == 0x3a: #Pro2
            if ord(self.BufferProtocol[1]) == 0x6a: #Stop
                if ord(self.BufferProtocol[2]) == 0x45: #Minus
                    ProtocolString=""
                    print("PRO2/STOP/MINUS Filtered")
        if len(self.StringToSend)>0:
            minitel.envoyer(self.StringToSend)
        if minitel.IsHayes == True: # No filter with Hayes modem
            if len(ProtocolString)>0:
                minitel.envoyer(ProtocolString)
        # else:
        # si Minitel et retourné, interpreter protocole + transparence
        self.StringToSend=""

    def received_message(self, m):
        self.received_messages += 1
        if minitel.DisplayDebug != 0:
            print ("WS_MessagesReçus={}({})".format(self.received_messages,len(m)))
        if minitel.ConnectionState == "Connected":
            #minitel.envoyer(str(m))
            self.debug_message(str(m))
            self.StringToSend=""
            for item in str(m):
                if self.CharToExtract > 0:
                    self.BufferProtocol += item
                    self.CharToExtract -= 1
                    if self.CharToExtract == 0:
                        self.CheckFilterProtocol()
                else:
                    if ord(item) == 0x1b:
                        if self.PrevWasEsc == False:
                            self.PrevWasEsc = True
                            # print("GotEsc=>PrevWasEsc=true")
                        else:
                            self.StringToSend += item
                    else:
                        if self.PrevWasEsc == False:
                            self.StringToSend += item
                        else:
                            # print("NotGotEsc but PrevWasEsc=true")
                            if ord(item) == 0x61 or ord(item) == 0x39 or ord(item) == 0x3a or ord(item) == 0x3b:
                                # print("InitProtocol")
                                self.BufferProtocol=item
                                if ord(item) == 0x39:
                                    self.CharToExtract=1
                                if ord(item) == 0x3a:
                                    self.CharToExtract=2
                                if ord(item) == 0x3b:
                                    self.CharToExtract=3
                                if ord(item) == 0x61:
                                    self.CharToExtract=0
                                    self.CheckFilterProtocol()
                            else:
                                self.StringToSend += chr(0x1b)
                                self.StringToSend += item
                            self.PrevWasEsc = False
            minitel.envoyer(self.StringToSend)
        else:
            self.debug_message_flush()
            self.debug_message(str(m))
            self.debug_message_flush()
            print("MessageReceivedWhileNotConnected:{}".format(str(m)))
#            self.close(reason='Bye bye WebSockey (175 bytes received)')

def HayesCommand(AtString="\r\nAT\r",RetryTimeout=1,attente=1):
    OkString="OK"
    ErrorString="ERROR"
    ConnectString="CONNECT"
    NocarrierString="NO CARRIER"
    retour=minitel.envoyer(AtString)
    if minitel.debug >= DebugInfo:
        print("Minitel.Envoyer AtString [{}]".format(AtString))

    minitel.HayesReplyStr=""
    minitel.HayesGotStr=""
    GotEcho=False
    GotReply=False
    TakeAllUntilEnd=False
    item=0              # Index echo commande
    itemok=0            # Index recu OK
    itemerror=0         # Index recu ERROR
    itemconnect=0       # Index recu CONNECT
    itemnocarrier=0     # Index recu NO CARRIER
    
    while (GotReply == False) and (RetryTimeout >= 0):
        try:
            retour=minitel.recevoir_sequence(attente=attente)
            for element in retour.valeurs:
                if GotEcho == False:                # Here we're waiting for the echo of our command
                    if AtString[item] == str(chr(element)):
                        item+=1
                        if item == len(AtString):   # Here we had the echo of our entire command, wait for timeout to send '\r'
                            GotEcho = True
                            itemok=0
                            itemerror=0
                            itemconnect=0
                            if minitel.IsHayes != True:
                                if minitel.debug >= DebugInfo:
                                    print ("Detected something echoing")
                    else:                           # It was not the echo of our command - retry
                        item=0
                else:                               # Here we're waiting for the result of our command [either OK/ERROR/CONNECT]
                    minitel.HayesReplyStr += str(chr(element))
                    #print(str(chr(element)))
                    if TakeAllUntilEnd==True:       # We already had the result, take also the rest of the line
                        if str(chr(element))=="\r":
                            GotReply = True
                            if minitel.debug >= DebugInfo:
                                print("{}:[{}]".format(minitel.HayesGotStr,minitel.HayesReplyStr))
                            minitel.IsHayesState = HayesOffline
                            if minitel.IsHayes != True:
                                minitel.IsHayes = True
                                if minitel.debug >= DebugInfo:
                                    print ("Detected Hayes modem in command mode")
                    else:
                        if OkString[itemok] == str(chr(element)):
                            itemok+=1
                            if itemok == len(OkString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=OkString
                        else:
                            itemok=0
                        if ErrorString[itemerror] == str(chr(element)):
                            itemerror+=1
                            if itemerror == len(ErrorString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=ErrorString
                        else:
                            itemerror=0
                        if ConnectString[itemconnect] == str(chr(element)):
                            itemconnect+=1
                            if itemconnect == len(ConnectString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=ConnectString
                        else:
                            itemconnect=0
                        if NocarrierString[itemnocarrier] == str(chr(element)):
                            itemnocarrier+=1
                            if itemnocarrier == len(NocarrierString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=NocarrierString
                        else:
                            itemnocarrier=0
        #return GotEcho or GotReply
        except Empty:
            if GotEcho == True:
                RetryTimeout -= 1
                if GotReply == False:
                    minitel.envoyer("\r\n")
                    if minitel.debug >= DebugInfo:
                        print("Timeout when GotReply was False and GotEcho was True =>= Resend CrLf")
                    #print("HayesReplyStr=[{}]".format(minitel.HayesReplyStr))
                else:
                    if minitel.debug >= DebugInfo:
                        print("Timeout when both GotReply and GotEcho was True =>= Should not occur =>= Wait")
            else:
                if minitel.debug >= DebugInfo:
                    print("Timeout when GotReply was False =>= No echo means no modem found")
                RetryTimeout = -1
            pass
        except UnicodeDecodeError:
            if minitel.debug >= DebugWarning:
                print ("Err unicode")
                pass

def HayesToggleDtr():
    minitel._minitel.dtr = not minitel._minitel.dtr
    time.sleep(2)
    minitel._minitel.dtr = not minitel._minitel.dtr                            
    if minitel.debug >= DebugInfo:
        print("Toggled DTR")

DebugVerbose=15
DebugInfo=10
DebugWarning=5
DebugNone=0

HayesOffline=0
HayesOnline=1

MyComDevice = '/dev/ttyUSB0'


minitel = Minitel(MyComDevice)
minitel.debug=DebugInfo    
if minitel.debug >= DebugInfo:
    print ( "Starting on {}".format(MyComDevice) )

minitel.IsHayes=False
minitel.IsHayesState = HayesOffline
vitesse_initiale = minitel.deviner_vitesse()
vitesse_souhaitee = 1200

print ( "Vitesse initiale : {} Bds".format(vitesse_initiale))
if vitesse_initiale == -1:
    print ( "Vitesse non identifiee ou pas de minitel")
    
    minitel._minitel.baudrate = 19200
    minitel._minitel.parity = 'N'
    minitel._minitel.bytesize = 8
    minitel._minitel.rtscts = False
    minitel._minitel.dsrdtr = True
    print("Waiting 1s before reopen()")
    time.sleep(1)
    HayesCommand()
    if minitel.IsHayes == False:
        print("Not found a suitable modem, exiting")
        exit()
if minitel.IsHayes == True:
    print ( "[Modem Hayes]")
    HayesCommand(AtString="ATI3\r",RetryTimeout=1,attente=1)
    HayesCommand(AtString="ATB0X1\r",RetryTimeout=1,attente=1)
    HayesCommand(AtString="ATL0S27=16S32=120\r",RetryTimeout=1,attente=1)
    HayesCommand(AtString="AT+FCLASS?\r",RetryTimeout=1,attente=1)

    #HayesCommand(AtString="AT$\r",RetryTimeout=4,attente=1)
    #HayesCommand(AtString="ATS$",RetryTimeout=4,attente=1)
    #HayesCommand(AtString="ATD$",RetryTimeout=4,attente=1)
    #HayesCommand(AtString="AT&$",RetryTimeout=6,attente=1)
else:   # Identify minitel and set expected speed
    minitel.identifier()
    print ( minitel.capacite['nom'] )
    if vitesse_initiale != vitesse_souhaitee:
        retry_vitesse = 3
        while retry_vitesse > 0:
            if not ( minitel.definir_vitesse(vitesse_souhaitee)):
                retry_vitesse -= 1
                if retry_vitesse == 0:
                    print ( "Echec de définition de la vitesse souhaitee" )
                    exit()
            else:
                print ("Retry vitesse souhaitee" )
                while not minitel.sortie.empty():
                    time.sleep(1)
    else:
        retry_vitesse = 0
        print ( "Vitesse souhaitee : {} Bds".format(vitesse_souhaitee))
        minitel._minitel= Serial(
            MyComDevice,
            baudrate = vitesse_souhaitee, # vitesse à 1200 bps, le standard Minitel
            bytesize = 7,    # taille de caractère à 7 bits
            parity   = 'E',  # parité paire
            stopbits = 1,    # 1 bit d’arrêt
            timeout  = 1,    # 1 bit de timeout
            xonxoff  = 0,    # pas de contrôle logiciel
            rtscts   = 0     # pas de contrôle matériel
        )
        minitel.definir_mode('VIDEOTEX')
        minitel.configurer_clavier(etendu = True, curseur = False, minuscule = True)
        minitel.echo(False)
        minitel.efface()
        minitel.curseur(False)
        print ( minitel.capacite )


print("BeforeTry")
print("[ESC] Close web socket [force disconnect from remote IP]")
print("'sS'  Show complete serial state")
print("'dD'  Toggle debug mode [Monitor any received character]")
if minitel.IsHayes == True:
    print("'hH'  [Hayes only] Send ATH1")
    print("'aA'  [Hayes only] Send ATA")
    print("'tT'  [Hayes only] Togle DTR state")
looped=0
minitel.DisplayDebug=1
minitel.DisplayDebugString=""
minitel.ConnectionState = "WaitingCall"
#minitel.ConnectionString='ws://mntl.joher.com:2018/?echo' #Hacker
#minitel.ConnectionString="ws://3611.re/ws"
#minitel.ConnectionString="ws://minitel.3614teaser.fr:8080/ws"
#minitel.ConnectionString="ws://34.223.255.81:9999/?echo" #SM
#minitel.ConnectionString="wss://3615co.de/ws"

old_settings = termios.tcgetattr(sys.stdin)
try:
    tty.setcbreak(sys.stdin.fileno())
    minitel.QuitMinitel=False
    while minitel.QuitMinitel == False:    #minitel.ConnectionState != "Closed":
        try:
            if isKeyboardData():
                print("Minitel.Entree.QSize()={}".format(minitel.entree.qsize()))
                c = sys.stdin.read(1)
                if c == '\x1b':         # x1b is ESC
                    print ("ESC")
                    if minitel.ConnectionState == "Connected": # !="Closed":
                        ws.close()
                if (c == 'h') or (c == 'H'):        # 'hH'  Send ATH1
                    if minitel.IsHayes == True:
                        if True: #minitel.IsHayesState == HayesOffline:
                            result=HayesCommand(AtString="\r\nATH1\r",RetryTimeout=1,attente=30)
                            print ("HayesCommand ATH1={}".format(result))
                            print ("HayesGotStr[{}]".format(minitel.HayesGotStr))
                            print ("HayesReplyStr[{}]".format(minitel.HayesReplyStr))
                            print ("CarrierDetect={}".format(minitel._minitel.cd))
                        else:
                            print ("Send ATH1 is invalid when a Hayes modem is not in command mode")
                    else:
                        print ("Send ATH1 is invalid without a Hayes modem")
                if (c == 'a') or (c == 'A'):        # 'aA'  Send ATA
                    if minitel.IsHayes == True:
                        if minitel.IsHayesState == HayesOffline:
                            result=HayesCommand(AtString="\r\nATA\r",RetryTimeout=1,attente=30)
                            print ("HayesCommand ATA={}".format(result))
                            print ("HayesGotStr[{}]".format(minitel.HayesGotStr))
                            print ("HayesReplyStr[{}]".format(minitel.HayesReplyStr))
                            print ("CarrierDetect={}".format(minitel._minitel.cd))
                            if minitel._minitel.cd:
                                minitel.ConnectionState="Booting"
                                minitel.IsHayesState = HayesOnline
                                minitel._minitel.parity = 'E'
                                minitel._minitel.bytesize = 7
                            else:
                                HayesToggleDtr()
                        else:
                            print ("Send ATA is invalid when a Hayes modem is not in command mode")
                    else:
                        print ("Send ATA is invalid without a Hayes modem")
                if (c == 'q') or (c == 'Q'):        # 'qQ'  Quit ...
                    minitel.QuitMinitel=True
                    if minitel.ConnectionState == "Connected": #!= "Closed":
                        ws.close()
                if (c == 't') or (c == 'T'):        # 'tT'  DTR state
                        HayesToggleDtr()
                if (c == 's') or (c == 'S'):        # 'sS'  Show complete serial state
                    sys.stderr.write("\n--- Settings: {p.name}  {p.baudrate},{p.bytesize},{p.parity},{p.stopbits}\n".format(p=minitel._minitel))
                    sys.stderr.write('--- RTS: {:8}  DTR: {:8}  BREAK: {:8}\n'.format(
                    ('active' if minitel._minitel.rts else 'inactive'),
                    ('active' if minitel._minitel.dtr else 'inactive'),
                    ('active' if minitel._minitel.break_condition else 'inactive')))
                    try:
                        sys.stderr.write('--- CTS: {:8}  DSR: {:8}  RI: {:8}  CD: {:8}\n'.format(
                            ('active' if minitel._minitel.cts else 'inactive'),
                            ('active' if minitel._minitel.dsr else 'inactive'),
                            ('active' if minitel._minitel.ri else 'inactive'),
                            ('active' if minitel._minitel.cd else 'inactive')))
                    except serial.SerialException:
                        # on RFC 2217 ports, it can happen if no modem state notification was
                        # yet received. ignore this error.
                        pass
                    sys.stderr.write('--- software flow control: {}\n'.format('active' if minitel._minitel.xonxoff else 'inactive'))
                    sys.stderr.write('--- hardware flow control: {}\n'.format('active' if minitel._minitel.rtscts else 'inactive'))
                if (c == 'd') or (c == 'D'):        # 'dD' Activation du mode debug
                    if minitel.DisplayDebug == 0:
                        print("DisplayDebugOn")
                        minitel.DisplayString = ""
                    else:
                        print("DisplayDebugOff")
                        if minitel.ConnectionState == "Connected":
                            ws.debug_message_flush()
                    minitel.DisplayDebug ^= 1
            if minitel.IsHayes == True:     # Monitor carrier with hayes modem
                if minitel.IsHayesState == HayesOnline:
                    if not minitel._minitel.cd:
                        print ("CarrierDetect={}".format(minitel._minitel.cd))
                        print ("Hayes modem has lost Carrier detect")
                        HayesToggleDtr()
                        if minitel.ConnectionState == "Connected":
                            ws.close()
                        minitel.IsHayesState = HayesOffline
                        minitel._minitel.parity = 'N'
                        minitel._minitel.bytesize = 8
                    else:
                        if minitel.ConnectionState == "WaitingCall":
                            minitel.ConnectionState="Booting"
                            print("WS Was disconnected from remote server but Hayes modem remains connected")
                else:
                    if minitel.ConnectionState != "WaitingCall":
                        if minitel.ConnectionState == "Booted":
                            minitel.ConnectionState = "WaitingCall"
                        #minitel.ConnectionState="Booting"
                        else:
                            print("ERR : IsHayesState is 'HayesOffLine' but ConnectionState is not 'WaitingCall' {}".format(minitel.ConnectionState))
                    
            if minitel.IsHayes == False:
                if minitel.ConnectionState == "WaitingCall":
                    minitel.ConnectionState="Booting"

            if minitel.ConnectionState == "Booting":    # Initialise les champs de saisie puis passe à "Booted"
                conteneur = MyClass(minitel, 1, 14, 32, 4, 'jaune', 'bleu',"PageToto.vdt")
                labelNom = Label(minitel, 2, 15, "Nom", 'jaune')
                champNom = ChampTexte(minitel, 10, 15, 20, 60)
                labelPrenom = Label(minitel, 2, 16, "Prénom", 'jaune')
                champPrenom = ChampTexte(minitel, 10, 16, 20, 60)
                conteneur.ajoute(labelNom)
                conteneur.ajoute(champNom)
                IndexChampNom=len(conteneur.elements)-1
                conteneur.elements[IndexChampNom].valeur="Défault"
                conteneur.ajoute(labelPrenom)
                conteneur.ajoute(champPrenom)
                IndexChampPrenom=len(conteneur.elements)-1
                minitel.ConnectionState = "Booted"
            if minitel.ConnectionState == "Booted":     # Gere les touches de fonction
                conteneur.affiche()
                print("Conteneur.executer()={}".format(conteneur.executer()))
                ToucheTraitee=False
                # Touche pas traitée en amont
                if conteneur.sequence.egale(REPETITION):
                    print ("Répétition !")
                    ToucheTraitee=True
                if conteneur.sequence.egale(CONNEXION):
                    print ("Connexion !")
                    if minitel.ConnectionState == "Connected":
                        ws.close()
                    ToucheTraitee=True
                if conteneur.sequence.egale(ENVOI):
                    print ("Envoi !")
                    ToucheTraitee=True
                    minitel.ConnectionState = "Starting"
                if ToucheTraitee == False:
                    print ( "InMain[{}]".format(conteneur.sequence) )
                    print ( "Longueur" )
                    print (conteneur.sequence.longueur )
                    print ( "Valeurs" )
                    for element in conteneur.sequence.valeurs:
                        print ( element )
                    for element in conteneur.elements:
                        if element.activable == True:
                            print(element.valeur)

                
            if minitel.ConnectionState == "Starting":
                print ("Starting connection")
                nom=conteneur.elements[IndexChampNom].valeur.upper()
                minitel.ConnectionString=None
                for server in YellowPages['servers']:
                    if server.get("name").upper() == nom:
                        minitel.ConnectionString=server.get("address")
                        print ("Found address")
                if minitel.ConnectionString == None:
                        if len(conteneur.elements[IndexChampNom].valeur) >0:
                            minitel.ConnectionString=conteneur.elements[IndexChampNom].valeur
                            if len(conteneur.elements[IndexChampPrenom].valeur) >0:
                                minitel.ConnectionString += "/" + conteneur.elements[IndexChampPrenom].valeur
                if minitel.ConnectionString != None:
                    try:
                        ws = WsMinitelClient(minitel.ConnectionString, protocols=['http-only', 'chat'])
                        minitel.ConnectionState = "Started"
                    except:
                        minitel.ConnectionState = "Booted"
                        print("BAD Connection String {}".format(minitel.ConnectionString))
                    if minitel.ConnectionState == "Started":
                        ws.daemon = False
                        ws.connect()
                else:
                    minitel.ConnectionState = "Booted"
            if minitel.ConnectionState == "Connected":
                looped +=1
                try:
                    char=minitel.recevoir()
                    ws.send(char)
                    if minitel.DisplayDebug != 0:
                        print("FromMinitel:",hex(ord(char)))
                except Empty: 
                    time.sleep(0.1)
                    pass
            
        except KeyboardInterrupt:
            print("GotKeyboardInterrupt")
            if minitel.ConnectionState == "Connected":
                ws.close()
            minitel.QuitMinitel = True  #minitel.ConnectionState="Closed"
            #pass
        except :
            print ("Minitel.ConnectionState={}".format(minitel.ConnectionState))
            if minitel.ConnectionState == "Started":
                minitel.ConnectionState="Booting" # "Closed"
                print("Unreachable server:[{}-{}]".format( sys.exc_info()[0],sys.exc_info()[1]))
                pass
            else:
                raise
                if minitel.ConnectionState == "Connected":
                    ws.close()
                    pass
                else:
                    print("Unexpected error:[{}-{}]".format( sys.exc_info()[0],sys.exc_info()[1]))
                    raise
finally:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
print("Continue after Try loop and {} iterations.".format(looped))

exit()
conteneur = MyClass(minitel, 1, 1, 32, 17, 'blanc', 'bleu',"PageToto.vdt")

options = [
  'Nouveau',
  'Ouvrir',
  '-',
  'Enregistrer',
  'Enreg. sous...',
  'Rétablir',
  '-',
  'Aperçu',
  'Imprimer...',
  '-',
  'Fermer',
  'Quitter'
]

labelMenu = Label(minitel, 2, 2, "Menu", 'jaune')
menu = Menu(minitel, options, 9, 1)

labelNom = Label(minitel, 2, 15, "Nom", 'jaune')
champNom = ChampTexte(minitel, 10, 15, 20, 60)

labelPrenom = Label(minitel, 2, 16, "Prénom", 'jaune')
champPrenom = ChampTexte(minitel, 10, 16, 20, 60)

conteneur.ajoute(labelMenu)
conteneur.ajoute(menu)
conteneur.ajoute(labelNom)
conteneur.ajoute(champNom)
conteneur.ajoute(labelPrenom)
conteneur.ajoute(champPrenom)
conteneur.affiche()
conteneur.executer()
print ( "conteneur" )
print ( conteneur )


MyItem=0

#menu = Menu(minitel, options, 15, 3, MyItem, 'bleu')
#menu.affiche()
#menu.executer()




while True:
    try:
        r = minitel.recevoir_sequence(attente=30)
        # r = minitel.entree.get(True , 30)
        # print ( r )
        MyItem += 1
        if MyItem >= len (options):
            MyItem = 0
        while options[MyItem] == '-':
            MyItem += 1
            if MyItem >= len (options):
                MyItem = 0
        print ( "Longueur" )
        print (r.longueur )
        print ( "Valeurs" )
        for element in r.valeurs:
            print ( element )
        menu.change_selection (MyItem)
    except Empty :
        print ( "Rien.." )
        pass


minitel.close()
print ( "Goodbye Minitel" )

