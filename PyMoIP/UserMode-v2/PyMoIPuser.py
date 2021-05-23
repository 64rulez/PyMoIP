#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
#from serial import Serial      # Liaison physique avec le Minitel
from serial.serialutil import *
from serial.tools.list_ports import comports # Pour ask_for_port()
from threading import Thread   # Threads pour l’émission/réception
from queue import Queue, Empty # Files de caractères pour l’émission/réception

import time
import sys
import requests

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

try:
    raw_input
except NameError:
    # pylint: disable=redefined-builtin,invalid-name
    raw_input = input   # in python3 it's "raw"
    #unichr = chr

SERIAL_DEFAULT_SPEED=9600
SERIAL_DEFAULT_BITS=8
SERIAL_DEFAULT_PARITY='N'




class MyMinitel:
    def __init__(self, peripherique = '/dev/ttyUSB0', spy = False):
        print("MyMinitel.__init__() started")

        assert isinstance(peripherique, str)

        self.capacite = CAPACITES_BASIQUES

        # Crée les deux files d’attente entrée/sortie
        self.entree = Queue()
        self.sortie = Queue()

        # Initialise la connexion avec le Minitel
        self._minitel = serial.Serial(
            peripherique,
            baudrate = SERIAL_DEFAULT_SPEED, # vitesse à 1200 bps, le standard Minitel
            bytesize = SERIAL_DEFAULT_BITS,    # taille de caractère à 7 bits
            parity   = SERIAL_DEFAULT_PARITY,  # parité paire
            stopbits = 1,    # 1 bit d’arrêt
            timeout  = 1,    # 1 bit de timeout
            xonxoff  = 0,    # pas de contrôle logiciel
            rtscts   = 0     # pas de contrôle matériel
        )
        self._XOFF=False
        self._continuer = True
        self.spy=False
        self._spy_allowed = spy
        if self._spy_allowed:
          self._spy=serial.serial_for_url('spy://'+ peripherique + '?file=/tmp/spy_py.txt', timeout=1)
          self._spy.write(bytearray('<<<START>>>','latin1'))
        
        # Crée les deux threads de lecture/écriture
        self._threads = []
        self._threads.append(Thread(None, self._gestion_entree, None, ()))
        self._threads.append(Thread(None, self._gestion_sortie, None, ()))

        # Démarre les deux threads de lecture/écriture
        for thread in self._threads:
            # Configure chaque thread en mode daemon
            thread.setDaemon(True)
            try:
                # Lance le thread
                thread.start()
            except (KeyboardInterrupt, SystemExit):
                self.close()
        print("MyMinitel.__init__() done")

    def close(self):
        print("MyMinitel.close() start")
        self._continuer = False

        # Attend que tous les threads aient fini
        for thread in self._threads:
            thread.join()

        if self._spy_allowed:
          self._spy.write(bytearray('<<<END>>>','latin1'))
          self._spy.close()
        #with open('/tmp/spy_py.txt') as f:
        #  print(f.read())
        self._minitel.close()
        print("MyMinitel.close() done")

    def _gestion_entree(self):
        print("MyMinitel._gestion_entree() start")
        GotSep=False
        while self._continuer:
          try:
            if self._spy_allowed and self.spy:
              caractere = self._spy.read()
            else:
              caractere = self._minitel.read()
            for c in caractere:
              if c==0x13:
                GotSep=True
              else:
                if GotSep==True:
                  if c==0x15:
                    print("_gestion_entree():XOFF")
                    self._XOFF=True
                  elif c==0x11:
                    print("_gestion_entree():XON")
                    self._XOFF=False
                else:
                  GotSep=False
          except serial.serialutil.SerialException:
              print ("ERR:_gestion_entree() "+str(sys.exc_info()[0])+" "+str(sys.exc_info()[1])+" "+str(sys.exc_info()[2]))
              err=sys.exc_info()
              for item in err:
                print(item)
              self.entree.task_done()
              self.close()
              raise

          if len(caractere) > 0:
              self.entree.put(caractere)
          else:
            #print("_gestion_entree() timeout")
            pass
        print("MyMinitel._gestion_entree() done")

    def _CheckForPhoto(self, datas, Filter):      # Ref : ETS 300 177
      # Analyse la présence d'une éventuelle photo
      # Retourne les éventuels offset de filtrage des données 8 bits
      #
      DebugCheckForPhoto=False
      GotEsc=False
      GotPD =False  # Si vrai, on a eu un identifiagnt 'Picture Delimiter' qui sera suivi d'un CMI
      GotCMI=False  # Si vrai, on a eu un CMI (photo ou audio) , qui sera suivi d'un identifiant de codage
      GotJPEG=False  # Si vrai, on a eu un identifiant de codage 'JPEG', prendre la taille des parametres (plusieurs octets - le dernier a le bit#5 à 0)
      GotLI=False    # Si vrai, on a la taille des parametres dans LI, il faudra les extraire
      LI=0
      LIcount=0
      Param=[]
      Return=[]
      ByteCount=0
      StartPhoto=0
      for Byte in datas:
        if GotLI==False:
          if GotJPEG==False:
            if GotCMI==False:
              if GotPD==False:
                if GotEsc==False:
                  if Byte==0x1b:
                    GotEsc=True
                else:
                  GotEsc=False
                  if Byte==0x70:                  # P17 - Switch to ISO 2022 - Data syntax 2 - PD (Picture Delimiter)
                    GotPD=True
                    StartPhoto=ByteCount-1
                    if DebugCheckForPhoto==True:
                      print("Found PD at byte "+str(ByteCount)+" {:04x}".format(ByteCount))
              else:
                GotPD=False
                if Byte==0x23:
                  GotCMI=True
                  if DebugCheckForPhoto==True:
                    print("Found CMI at byte "+str(ByteCount)+" {:04x}".format(ByteCount))
            else:
              GotCMI=False
              if Byte==0x40:
                GotJPEG=True
                if DebugCheckForPhoto==True:
                  print("Found JPEG at byte "+str(ByteCount)+" {:04x}".format(ByteCount))
                LIcount=0
          else:
            LIcount+=1
            if LIcount>1:
              if DebugCheckForPhoto==True:
                print("LI byte {:02x}".format(Byte))
              if Byte>= 0x60:
                LI=LI * 32 + (Byte-0x60)
              else:
                LI=LI * 32 + (Byte-0x40)
                GotJPEG=False
                GotLI=True
                Param=[]
                if DebugCheckForPhoto==True:
                  print("LI count = "+str(LI)+"({:04x})".format(LI))
            else:
              pass # Skip 0x7F ??? ISO 9281-1/11 5.2.7
        else:
          if len(Param)==0:
            if LI>1:
              start=ByteCount+1
              end=ByteCount+LI-1
              print("_CheckForPhoto() : Should force 8 bit operation from byte {:04x} to byte {:04x}".format(start,end))
              if Filter==True:
                Return.append(StartPhoto)   # Permet le filtrage depuis \x1b\x70 de toutes données 8 bits         
              else:
                Return.append(start)        # Permet de détecter les données nécessairement 8 bits  
              Return.append(end+1)            
          Param.append(Byte)
          LI-=1
          if LI==0:
            GotLI=False
            if DebugCheckForPhoto==True:
              print("Len(Param)="+str(len(Param))+" PDE[0]={:02x} ByteCount={:04x}".format(Param[0],ByteCount))
            if Param[0]==0x50:
              if DebugCheckForPhoto==True:
                print("Header (TBC)")
            elif Param[0]==0x51:
              if DebugCheckForPhoto==True:
                print("Header (Last)")
            elif Param[0]==0x52:
              if DebugCheckForPhoto==True:
                print("Data (TBC)")
            elif Param[0]==0x53:
              if DebugCheckForPhoto==True:
                print("Data (Last)")
            else:
              if DebugCheckForPhoto==True:
                print("Illegal header")
            if Param[0]==0x50 or Param[0]==0x51:
              i=1
              while i<len(Param):
                AC=Param[i]
                i+=1
                if AC==0x20:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Parameter Status Attribute'")
                  LastParamCode=0x30
                elif AC==0x21:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Picture Display Attribute'")
                  LastParamCode=0x35
                elif AC==0x22:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Source Picture Attribute'")
                  LastParamCode=0x34
                elif AC==0x23:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Source Signal Attribute'")
                  LastParamCode=0x33
                elif AC==0x24:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Source Coding Algorithm Attribute'")
                  LastParamCode=0x32
                elif AC==0x25:
                  if DebugCheckForPhoto==True:
                    print("Attribute='Transmission Channel Attribute'")
                  LastParamCode=0x30
                else:
                  if DebugCheckForPhoto==True:
                    print("Attribute='unknown'")
                  LastParamCode=0x00
                # Get Parameter code
                PC=Param[i]
                i+=1
                if DebugCheckForPhoto==True:
                  print("ParameterCode={:02x}".format(PC))
                if PC<0x30 or PC>LastParamCode:
                  if DebugCheckForPhoto==True:
                    print("Illegal parameter code")
                  NbSub=-1
                else:
                  if AC==0x20:
                    NbSub=1
                    if DebugCheckForPhoto==True:
                      print("Reset to default")
                  elif AC==0x21:
                    if PC==0x30:
                      NbSub=1
                    elif PC==0x31:
                      NbSub=2
                    elif PC==0x32:
                      NbSub=2
                      if DebugCheckForPhoto==True:
                        print("Photo Area Location")
                    elif PC==0x33:
                      NbSub=2
                      if DebugCheckForPhoto==True:
                        print("Photo Area Size")
                    elif PC==0x34:
                      NbSub=4
                      if DebugCheckForPhoto==True:
                        print("Photo Picture Placement")
                    elif PC==0x35:
                      NbSub=1
                  elif AC==0x22:
                    if PC==0x30:
                      NbSub=2
                    elif PC==0x31:
                      NbSub=2
                    elif PC==0x32:
                      NbSub=5  # ou 1 !?
                    elif PC==0x33:
                      NbSub=2
                    elif PC==0x34:
                      NbSub=1
                  elif AC==0x23:
                    if PC==0x30:
                      NbSub=1
                      if DebugCheckForPhoto==True:
                        print("Source Component Description")
                    elif PC==0x31:
                      NbSub=1
                    elif PC==0x32:
                      NbSub=1
                    elif PC==0x33:
                      NbSub=1  # ou 2 !?
                  elif AC==0x24:
                    if PC==0x30:
                      NbSub=1
                    elif PC==0x31:
                      NbSub=3
                    elif PC==0x32:
                      NbSub=1                
                for NumParam in range (0 , NbSub):
                  # Get FieldType (FT)
                    if DebugCheckForPhoto==True:
                      print("SubParam#"+str(NumParam))
                    FT=Param[i]
                    i+=1
                    if FT==0x40:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Integer'")
                    elif FT==0x41:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Real'")
                    elif FT==0x42:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Normalised'")
                    elif FT==0x43:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Decimal'")
                    elif FT==0x44:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Enum'")
                    elif FT==0x45:
                      if DebugCheckForPhoto==True:
                        print("FieldType='Bool'")
                    elif FT==0x46:
                      if DebugCheckForPhoto==True:
                        print("FieldType='String'")
                    #  Get FieldLen
                    FieldLen=0
                    FL=Param[i]
                    i+=1
                    while FL>0x40:
                      FL-=0x40
                      FieldLen=FieldLen*0x40+FL
                      FL=Param[i]
                      i+=1
                    FieldLen=FieldLen*0x40+FL
                    #  Get SubParam
                    SubParam=[]
                    SubParamCount=0
                    while SubParamCount<FieldLen:
                      SubParam.append(Param[i])
                      i+=1
                      SubParamCount+=1
                    if DebugCheckForPhoto==True:
                      print(SubParam)
            #  
            Param=[]
        ByteCount+=1
      return Return    # Liste de tuples {start/end} pour passage à 8 bits et retour en 7 bits - Attention, ils sont parfois inversés !
      
    def _gestion_sortie(self):
        print("MyMinitel._gestion_sortie() start")
        DoFilter=True  # Filtrer les données photo si 7 bits
                       # NB : Non implémenté dans _gestion_sortie() mais prêt dans _CheckForPhoto() le cas False où l'on forcerait le format 8 bits pendant la transmission photo [cas d'un modem Hayes par ex] 
        while self._continuer or not self.sortie.empty():
            # Attend un caractère pendant 1 seconde
            try:
                a=self.sortie.get(block = True, timeout = 1)
                StartStop=self._CheckForPhoto(a,Filter=DoFilter)
                #print(StartStop)
                if len(StartStop) :
                  IndexStartStop=0
                else:
                  IndexStartStop=-1
                Sent=0
                DontSend8Bits=False
                
                while len(a)>0:                  
                  if self._XOFF:
                    print("_gestion_sortie():XOFF")
                    count_XOFF=10
                    while (self._XOFF) and (count_XOFF>0):
                      time.sleep(1)           
                      count_XOFF-=1         
                    print("_gestion_sortie():XON"+str(count_XOFF))
                  if len(a)>16:
                    b=a[:16]
                    a=a[16:]
                  else:
                    b=a
                    a=bytearray()
                  
                  if IndexStartStop>=0 and IndexStartStop<len(StartStop):
                    while Sent+len(b)>=StartStop[IndexStartStop]:
                      #print("-------------------- Sent="+str(Sent)+" StartStop[Index]="+str(StartStop[IndexStartStop]))
                      #print("B avant "+str(StartStop[IndexStartStop]-Sent))
                      #print(b)
                      c=b[:StartStop[IndexStartStop]-Sent]
                      b=b[StartStop[IndexStartStop]-Sent:]
                      if DontSend8Bits!=True:
                        if self._spy_allowed and self.spy:
                          self._spy.write(c)
                        else:
                          self._minitel.write(c)
                        self._minitel.flush()
                      Sent+=len(c)
                      #print(c)
                      #print(len(c))
                      if not IndexStartStop & 1:
                        if self._minitel.bytesize!=8:
                          if DoFilter==True:
                            DontSend8Bits=True
                            print("DontSend8Bits=True")
                        print("Pass to 8 bits from byte {:02x}".format(Sent))
                      else:
                        if DoFilter==True:
                          print("DontSend8Bits=False")
                          DontSend8Bits=False
                        print("Pass to 7 bits from byte {:02x}".format(Sent))
                      #print(b)
                      #print(len(b))
                      IndexStartStop+=1
                      if IndexStartStop==len(StartStop):
                        break
                    Sent+=len(b)
                  if DontSend8Bits!=True:
                    if self._spy_allowed and self.spy:
                      self._spy.write(b)
                    else:
                      self._minitel.write(b)
                    self._minitel.flush()

                # Attend que le caractère envoyé au minitel ait bien été envoyé
                # car la sortie est bufferisée

                # Permet à la méthode join de la file de fonctionner
                self.sortie.task_done()
            except Empty:
                continue
        print("MyMinitel._gestion_sortie() done")

    def envoyer(self, contenu):
      #print("MyMinitel.Envoyer()")
      if type(contenu) is str:
        #print("MyMinitel.EnvoyerSTR("+str(len(contenu))+")")
        self.sortie.put(bytearray(contenu,'latin1'))
      elif type(contenu) == bytes:
        #print("MyMinitel.EnvoyerBYTES("+str(len(contenu))+")")
        self.sortie.put(contenu)
      elif type(contenu) is int:
        #print("MyMinitel.EnvoyerINT(0x"+format(contenu, '02X')+")")
        self.sortie.put(chr(contenu).encode())
      elif type(contenu) is list:
        #print("MyMinitel.EnvoyerLIST")
        for item in contenu:
          if type(item) is list:
            self.envoyer(item)
          else:
            self.sortie.put(chr(item).encode())
      else:
        print("MyMinitel.Envoyer(type inconnu)")
        print(str(type(contenu))+ "("+ str(len(contenu))+")")
        print(contenu)
      #print("MyMinitel.Envoyer()done")

    def recevoir(self, bloque = False, attente = None):
        assert bloque in [True, False]
        assert isinstance(attente, (int,float)) or attente == None

        return self.entree.get(bloque, attente).decode('iso-8859-1')

    def appeler(self, contenu, attente):
        print("MyMinitel.Appeler("+str(contenu)+","+str(attente)+")")
        assert isinstance(attente, int)

        # Vide la file d’attente en réception
        self.entree = Queue()

        # Envoie la séquence
        self.envoyer(contenu)
        #print("Envoyé")

        # Attend que toute la séquence ait été envoyée
        self.sortie.join()
        #print("Envoyé fini")

        # Tente de recevoir le nombre de caractères indiqué par le paramètre
        # attente avec un délai d’1 seconde.
        retour = bytearray()
        for _ in range(0, attente):
            try:
                # Attend un caractère
                entree_bytes = self.recevoir(bloque = True, attente = 1) #.entree.get(block = True, timeout = 1)
                #print("Appeler():"+str(len(entree_bytes))+"-"+str(len(retour))+"-"+str(entree_bytes))
                retour+=(entree_bytes.encode())
            except Empty:
                # Si un caractère n’a pas été envoyé en moins d’une seconde,
                # on abandonne
                break
        a=""
        for item in retour:
          if len(a)>0:
            a+=" "
          a+=format(item, '02X')
        print("MyMinitel.Appeler():retour="+a)
        return retour

    def definir_mode(self, mode = 'VIDEOTEX'):
        """Définit le mode de fonctionnement du Minitel.

        Le Minitel peut fonctionner selon 3 modes : VideoTex (le mode standard
        du Minitel, celui lors de l’allumage), Mixte ou TéléInformatique (un
        mode 80 colonnes).

        La méthode definir_mode prend en compte le mode courant du Minitel pour
        émettre la bonne commande.

        :param mode:
            une valeur parmi les suivantes : VIDEOTEX,
            MIXTE ou TELEINFORMATIQUE (la casse est importante).
        :type mode:
            une chaîne de caractères

        :returns:
            False si le changement de mode n’a pu avoir lieu, True sinon.
        """
        assert isinstance(mode, str)

        # 3 modes sont possibles
        if mode not in ['VIDEOTEX', 'MIXTE', 'TELEINFORMATIQUE']:
            return False

        # Si le mode demandé est déjà actif, ne fait rien
        if self.mode == mode:
            return True

        resultat = False

        # Il y a 9 cas possibles, mais seulement 6 sont pertinents. Les cas
        # demandant de passer de VIDEOTEX à VIDEOTEX, par exemple, ne donnent
        # lieu à aucune transaction avec le Minitel
        if self.mode == 'TELEINFORMATIQUE' and mode == 'VIDEOTEX':
            retour = self.appeler([CSI, 0x3f, 0x7b], 2)
            resultat = retour.egale([SEP, 0x5e])
        elif self.mode == 'TELEINFORMATIQUE' and mode == 'MIXTE':
            # Il n’existe pas de commande permettant de passer directement du
            # mode TéléInformatique au mode Mixte. On effectue donc la
            # transition en deux étapes en passant par le mode Videotex
            retour = self.appeler([CSI, 0x3f, 0x7b], 2)
            resultat = retour.egale([SEP, 0x5e])

            if not resultat:
                return False

            retour = self.appeler([PRO2, MIXTE1], 2)
            resultat = retour.egale([SEP, 0x70])
        elif self.mode == 'VIDEOTEX' and mode == 'MIXTE':
            retour = self.appeler([PRO2, MIXTE1], 2)
            resultat = retour.egale([SEP, 0x70])
        elif self.mode == 'VIDEOTEX' and mode == 'TELEINFORMATIQUE':
            retour = self.appeler([PRO2, TELINFO], 4)
            resultat = retour.egale([CSI, 0x3f, 0x7a])
        elif self.mode == 'MIXTE' and mode == 'VIDEOTEX':
            retour = self.appeler([PRO2, MIXTE2], 2)
            resultat = retour.egale([SEP, 0x71])
        elif self.mode == 'MIXTE' and mode == 'TELEINFORMATIQUE':
            retour = self.appeler([PRO2, TELINFO], 4)
            resultat = retour.egale([CSI, 0x3f, 0x7a])

        # Si le changement a eu lieu, on garde le nouveau mode en mémoire
        if resultat:
            self.mode = mode

        return resultat

    def identifier(self):
        print("MyMinitel.Identifier()")
        self.capacite = CAPACITES_BASIQUES

        # Émet la commande d’identification
        retour = self.appeler(b'\x1b\x39\x7b', 5)        #retour = self.appeler([PRO1, ENQROM], 5)

        # Teste la validité de la réponse
        if (len(retour) != 5):
            print("Identifier():RomNotFound<>5")
            return
        if( retour[0] != 1 or #SOH or
            retour[4] != 4): #EOT):
            print("Identifier():RomNotFound<SOH>="+str(retour[0])+"<EOT>="+str(retour[4]))
            return

        # Extrait les caractères d’identification
        constructeur_minitel = chr(retour[1])
        type_minitel         = chr(retour[2])
        version_logiciel     = chr(retour[3])

        # Types de Minitel
        if type_minitel in TYPE_MINITELS:
            self.capacite = TYPE_MINITELS[type_minitel]

        if constructeur_minitel in CONSTRUCTEURS:
            self.capacite['constructeur'] = CONSTRUCTEURS[constructeur_minitel]

        self.capacite['version'] = version_logiciel
        self.capacite['type_minitel'] = type_minitel

        # Correction du constructeur
        if constructeur_minitel == 'B' and type_minitel == 'v':
            self.capacite['constructeur'] = 'Philips'
        elif constructeur_minitel == 'P' and type_minitel == 'v':
            self.capacite['nom']="Minitel 2 Photo"
        elif constructeur_minitel == 'C':
            if version_logiciel == ['4', '5', ';', '<']:
                self.capacite['constructeur'] = 'Telic ou Matra'

        # Détermine le mode écran dans lequel se trouve le Minitel
        retour=self.appeler(b'\x1b\x39\x70', LONGUEUR_PRO2)      # retour = self.appeler([PRO1, STATUS_FONCTIONNEMENT], LONGUEUR_PRO2)

        if len(retour) != LONGUEUR_PRO2:
            # Le Minitel est en mode Téléinformatique car il ne répond pas
            # à une commande protocole
            self.mode = 'TELEINFORMATIQUE'
        elif retour[3] & 1 == 1:
            # Le bit 1 du status fonctionnement indique le mode 80 colonnes
            self.mode = 'MIXTE'
        else:
            # Par défaut, on considère qu’on est en mode Vidéotex
            self.mode = 'VIDEOTEX'
        #print("Capacité:")
        print(str(self.capacite))
        print("MyMinitel.Identifier():Done")
        

    def deviner_vitesse(self):
        print("MyMinitel.DevinerVitesse()")

        # Vitesses possibles jusqu’au Minitel 2
        params = [[19200,8,PARITY_NONE], [19200,7,PARITY_EVEN], [9600,8,PARITY_NONE],[9600,7,PARITY_EVEN], [4800,8,PARITY_NONE], [4800,7,PARITY_EVEN], [1200,7,PARITY_EVEN], [1200,8,PARITY_NONE], [300,8,PARITY_NONE], [300,7,PARITY_EVEN], [75,7,PARITY_EVEN]]

        for param in params:
          print ("Trying with "+str(param[0])+"/"+str(param[1])+"/"+str(param[2]))
          # Configure le port série à la vitesse à tester
          self._minitel.baudrate = param[0]
          self._minitel.bytesize = param[1]
          self._minitel.parity = param[2]
          
          retry=3
          while retry>0:

            # Envoie une demande de statut terminal
            retour = self.appeler(b'\x1b\x39\x70', LONGUEUR_PRO2)

            # Le Minitel doit renvoyer un acquittement PRO2
            print("DevinerVitesse():Got "+str(len(retour))+" bytes")
            if len(retour) == LONGUEUR_PRO2:
                if (retour[0]== 0x1b) and (retour[1]==0x3a) and (retour[2]==0x71): 
                  self.vitesse = self._minitel.baudrate
                  print("MyMinitel.DevinerVitesse("+str(self.vitesse)+"):Done")
                  return self.vitesse
                else:
                  print("MyMinitel.DevinerVitesse():Must retry")
                  retry-=1
            else:
              retry=0

        # La vitesse n’a pas été trouvée
        print("MyMinitel.DevinerVitesse(-1):Done")
        return -1

    def definir_vitesse(self, vitesse,bits=7):
        assert isinstance(vitesse, int)
        assert isinstance(bits, int)

        print("MyMinitel.DefinirVitesse("+str(vitesse)+","+str(bits)+")")

        # Vitesses possibles jusqu’au Minitel 2
        vitesses = {300: B300, 1200: B1200, 4800: B4800, 9600: B9600, 19200: 0x47}

        # Teste la validité de la vitesse demandée
        if vitesse not in vitesses or vitesse > self.capacite['vitesse']:
            print("definir_vitesse():"+str(vitesse)+">max")
            return False
        if (bits==8) and not ((self.capacite['nom'] == "Minitel MagisClub")or(self.capacite['nom'] == "Minitel 2 Photo")):
            print("definir_vitesse():8Bits illegal <> MagisClub/Minitel2Photo")
            return False
# Codes PRO2+PROG
#B9600  = 0x7f  - 01111111
#B4800  = 0x76  - 01110110
#B19200 = 0x6d  m- 01101101
#B1200  = 0x64  - 01100100 - 100
#B300   = 0x52  - 01010010
#B19200 = 0x47  G- 01000111 ==> C3/A3/24
#B75    = 0x49  - 01001001


        self.envoyer("<<PROG"+str(vitesse)+"/"+str(bits)+">>")
        # Envoie une commande protocole de programmation de vitesse
        if (bits==7):
          print("7Bits")
          retour = self.appeler([PRO2, PROG, vitesses[vitesse]], LONGUEUR_PRO2)
        else:
          print("8Bits")
          retour = self.appeler([PRO2, PROG, vitesses[vitesse]], LONGUEUR_PRO2)

        # Le Minitel doit renvoyer un acquittement PRO2
        if len(retour) == LONGUEUR_PRO2:
            # Si on peut lire un acquittement PRO2 avant d’avoir régler la
            # vitesse du port série, c’est que le Minitel ne peut pas utiliser
            # la vitesse demandée      
            if self._minitel.baudrate == vitesse:
              print("MyMinitel.DefinirVitesse():Vitesse inchangee")
            else:
              print("MyMinitel.DefinirVitesse():Failed")
              print(retour)
              return False
            #print("Demande Status prise")
            #print(self.appeler([PRO2, 118,91], LONGUEUR_PRO3)) # ==>0x
            #print("Demande Status terminal")
            #print(self.appeler([PRO1, 112], LONGUEUR_PRO3))  # ==> 0x46
            #print("TestVitesses")
            #for i in range(0x40,0xff):
            #if i not in [0x47,0x49,0x52,0x64,0x6d,0x76,0x7f]:
            #    print(self.appeler([PRO3, PROG, 0x47 , i], LONGUEUR_PRO2))

        # Configure le port série à la nouvelle vitesse
        self._minitel.baudrate = vitesse
        if self._minitel.bytesize != bits:
          print("Bits ancien:"+str(self._minitel.bytesize))
          print("Bits nouveau:"+str(bits))
        else:
          print("Bits inchangés:"+str(bits))
        self._minitel.bytesize = bits
        self.vitesse = vitesse
        print("MyMinitel.DefinirVitesse():OK")

        return True





#print("Getting Minitel yellow pages ...")
#MinitelYellowPages='http://teletel.org/minitel-yp.json'
#r=requests.get(MinitelYellowPages)
#if r.status_code==200:
#    YellowPages=r.json()
#    for server in YellowPages['servers']:
#        print(server.get("name"))
#else:
#    print ("Failled to get Minitel Yellow Pages from '{}' : Error {}".format(MinitelYellowPages,r.status_code))
#    exit()
    #
    # Exit because we can't reach internet !
    #
    


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
        print("ws.opened(MainLoop()): passe à 'Connected'")
        self.received_messages = 0
        self.PrevWasEsc = False
        self.CharToExtract = 0

    def closed(self, code, reason):
        print(("WebSocket Closed down", code, reason))
        #print("Closed1()={}".format(minitel.ConnectionState))
        self.debug_message_flush()
        minitel.ConnectionState = "WaitingCall" # "Booting" #"Closed"
        print("ws.closed(MainLoop()): passe à 'WaitingCall'")
        #print("Closed2()={}".format(minitel.ConnectionState))
    
    def add_debug_char (self, item):
        minitel.DisplayDebugString += item
        if len(minitel.DisplayDebugString) == 16:
            StringToDisplay=""
            for char in minitel.DisplayDebugString:
                StringToDisplay += "{:02x} ".format(ord(char))
            StringToDisplay += " : "
            for char in minitel.DisplayDebugString:
              try:
                if char.encode('ascii') >= ' '.encode('ascii'):
                    StringToDisplay += char
                else:
                    StringToDisplay += "."
              except:
                #print("Except")
                StringToDisplay += "_"
                pass
            print (StringToDisplay)
            minitel.DisplayDebugString=""

    def debug_message (self, MyStr):
        print("debug_message()")
        if minitel.DisplayDebug != 0 and MyStr != None:
            for item in MyStr:
                self.add_debug_char(item)

    def debug_message_flush (self):
        print("debug_message_flush()")
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
        if len(self.BufferProtocol) != 0:
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
        else:
            print("not filtered while being minitel")
            if len(ProtocolString)>0:
                minitel.envoyer(ProtocolString)
            # si Minitel et retourné, interpreter protocole + et forcer en transparence
        self.StringToSend=""
        self.BufferProtocol=""

    def received_message(self, m):
        self.received_messages += 1
        if minitel.DisplayDebug != 0:
            print ("WS_MessagesReçus={}({})".format(self.received_messages,len(m)))
        if len(m)>0:
            if minitel.ConnectionState == "Connected":
                #print("ReceivedMessage1()={}".format(minitel.ConnectionState))
                #minitel.envoyer(str(m))
                try:
                    self.debug_message(str(m))
                except:
                    if str(sys.exc_info()[0]) == "<class 'TypeError'>":
                        temp=""
                        for item in m.data:
                            temp+=chr(item)
                        m=temp
                        self.debug_message(str(m))
                        pass
                    else:
                        print("ReceivedMessage():Unexpected error:", sys.exc_info()[0])
                        #
                    #for attr in dir(self):
                    #    print("obj.%s = %r" % (attr, getattr(self, attr)))
                    #for attr in dir(m):
                    #    print("m.obj.%s = %r" % (attr, getattr(m, attr)))
                #finally:
                    #print("ReceivedMessage2()={}".format(minitel.ConnectionState))
                    
                self.StringToSend=str(m)

                if len(m)!=len(self.StringToSend):
                  print("len(m)"+str(len(m)))
                  print("len(m.data.decode('iso-8859-1'))"+str(len(m.data.decode('iso-8859-1'))))
                  print("len(self.StringToSend)"+str(len(self.StringToSend)))
                  raise ValueError('m<>StringToSend')
                  

                if False: #for item in str(m):
                    if self.CharToExtract > 0:
                        self.BufferProtocol += item
                        self.CharToExtract -= 1
                        if self.CharToExtract == 0:
                            self.CheckFilterProtocol()
                    else:
                        if ord(item) == 0x05:
                            self.CheckFilterProtocol()
                            print("GOT 0X05!!!!!!!")
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
            retour=minitel.recevoir(attente=attente, bloque=True)
            for element in retour:
                if GotEcho == False:                # Here we're waiting for the echo of our command
                    if AtString[item] == element: #str(chr(element)):
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
                    minitel.HayesReplyStr += element #str(chr(element))
                    #print(str(chr(element)))
                    if TakeAllUntilEnd==True:       # We already had the result, take also the rest of the line
                        if "\r"==element: #str(chr(element))==
                            GotReply = True
                            if minitel.debug >= DebugInfo:
                                print("{}:[{}]".format(minitel.HayesGotStr,minitel.HayesReplyStr))
                            minitel.IsHayesState = HayesOffline
                            if minitel.IsHayes != True:
                                minitel.IsHayes = True
                                if minitel.debug >= DebugInfo:
                                    print ("Detected Hayes modem in command mode")
                    else:
                        if OkString[itemok] == element: #str(chr(element)):
                            itemok+=1
                            if itemok == len(OkString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=OkString
                        else:
                            itemok=0
                        if ErrorString[itemerror] == element: #str(chr(element)):
                            itemerror+=1
                            if itemerror == len(ErrorString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=ErrorString
                        else:
                            itemerror=0
                        if ConnectString[itemconnect] == element: #str(chr(element)):
                            itemconnect+=1
                            if itemconnect == len(ConnectString):
                                TakeAllUntilEnd=True
                                minitel.HayesGotStr=ConnectString
                        else:
                            itemconnect=0
                        if NocarrierString[itemnocarrier] == element: #str(chr(element)):
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

def ask_for_port():
    """\
    Show a list of ports and ask the user for a choice. To make selection
    easier on systems with long device names, also allow the input of an
    index.
    """
    sys.stderr.write('\n--- Available ports:\n')
    ports = []
    for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
        sys.stderr.write('--- {:2}: {:20} {!r}\n'.format(n, port, desc))
        ports.append(port)
    while True:
        port = raw_input('--- Enter port index or full name: ')
        try:
            index = int(port) - 1
            if not 0 <= index < len(ports):
                sys.stderr.write('--- Invalid index!\n')
                continue
        except ValueError:
            pass
        else:
            port = ports[index]
        return port

DebugVerbose=15
DebugInfo=10
DebugWarning=5
DebugNone=0

HayesOffline=0
HayesOnline=1

MyComDevice = ask_for_port()    # '/dev/ttyUSB0'


minitel = MyMinitel(MyComDevice,spy=True)
minitel.debug=DebugInfo    
minitel.spy=True
if minitel.debug >= DebugInfo:
    print ( "Starting on {}".format(MyComDevice) )

minitel.IsHayes=False
minitel.IsHayesState = HayesOffline
vitesse_initiale = minitel.deviner_vitesse()

print ( "Vitesse initiale : {} Bds {}bits {}".format(vitesse_initiale,minitel._minitel.bytesize,minitel._minitel.parity))

if vitesse_initiale == -1:
    print ( "Vitesse non identifiee ou pas de minitel -> Essaye Hayes")
    
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
    if (minitel.capacite['nom'] == "Minitel MagisClub") :
        vitesse_souhaitee = 9600  #  Plante à 19200 sur photos 
        bits_souhaites = 8
    elif (minitel.capacite['nom']=="Minitel 2 Photo"):
        vitesse_souhaitee = 9600  # Plante (moins fort) à 9600 sur photos
        bits_souhaites = 8
    elif minitel.capacite['nom'] == "Minitel 2":
        vitesse_souhaitee = 4800
        bits_souhaites = 7
    else:
        bits_souhaites = 7
        vitesse_souhaitee = 1200
    if (vitesse_initiale != vitesse_souhaitee) or (bits_souhaites != minitel._minitel.bytesize):
        retry_vitesse = 3
        while retry_vitesse > 0:
            if ( minitel.definir_vitesse(vitesse_souhaitee,bits_souhaites)):
                if minitel.deviner_vitesse() == vitesse_souhaitee:
                  if (bits_souhaites != minitel._minitel.bytesize):
                    print("ERR format souhaité (8 bits) <> Format détecté (7 bits) (et vitesse OK).")
                    print("Configurer le M2-photo ou le MagisClub pour accepter le bon format [FNCT-P puis 8 ou menu clé]")
                    exit()
                  else:
                    retry_vitesse = 0
                    print("Changed to {} {}".format(vitesse_souhaitee,bits_souhaites))
                else:
                    retry_vitesse -= 1
                    if retry_vitesse == 0:
                        print ( "Echec de définition de la vitesse souhaitee" )
                        exit()
                    else:
                        print ("Retry {} vitesse souhaitee".format(retry_vitesse))                    
                        time.sleep(2)
            else:
                print ("Retry vitesse souhaitee definir_vitesse() failed" )
                while not minitel.sortie.empty():
                    time.sleep(2)
                    retry_vitesse -= 1
                if retry_vitesse == 0:
                    print ( "Echec de définition de la vitesse souhaitee" )
                    exit()
    else:
        retry_vitesse = 0
    print ( "Vitesse actuelle : {} Bds {}bits".format(vitesse_souhaitee,bits_souhaites))
    print(minitel.appeler(b'\x1b\x3b\x60\x51\x5a', 5))        #retour = self.appeler([PRO1, ENQROM], 5)
    print(minitel.appeler(b'\x1b\x3b\x60\x52\x58', 5))        #retour = self.appeler([PRO1, ENQROM], 5)
    #minitel._minitel= serial.Serial(
    #    MyComDevice,
    #    baudrate = vitesse_souhaitee, # vitesse à 1200 bps, le standard Minitel
    #    #bytesize = 7,    # taille de caractère à 7 bits
    #    #parity   = 'E',  # parité paire
    #    bytesize = 8,    # taille de caractère à 7 bits
    #    parity   = 'N',  # parité paire
    #    stopbits = 1,    # 1 bit d’arrêt
    #    timeout  = 1,    # 1 bit de timeout
    #    xonxoff  = 0,    # pas de contrôle logiciel
    #    rtscts   = 0     # pas de contrôle matériel
    #)
    #zzminitel.definir_mode('VIDEOTEX')
    #zzminitel.configurer_clavier(etendu = True, curseur = False, minuscule = True)
    #zzminitel.echo(False)
    #zzminitel.efface()
    #zzminitel.curseur(False)
    #zzprint ( minitel.capacite )


print("BeforeTry")
print("[ESC] Close web socket [force disconnect from remote IP]")
print("'sS'  Show complete serial state")
print("'dD'  Toggle debug mode [Monitor any received character]")
if minitel.IsHayes == True:
    print("'hH'  [Hayes only] Send ATH1")
    print("'aA'  [Hayes only] Send ATA")
    print("'tT'  [Hayes only] Togle DTR state")
looped=0
DefaultServer="Default"
DefaultConnectionString="ws://localhost:9001"
minitel.DisplayDebug=1
minitel.DisplayDebugString=""
minitel.ConnectionState = "WaitingCall"
print("MainLoop():[INIT] ConnectionState=WaitingCall")
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
                        print("MainLoop():[Connected et ESC] ws.close()")
                        ws.close()
                if ((c=='l') or (c=='L')) and minitel.ConnectionState == "Booted":
                  minitel.ConnectionState = "Starting" 
                  print("MainLoop():[Key 'l'] minitel.ConnectionState = 'Booted' passe à 'Starting'")
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
                                print("MainLoop():[ATA] minitel.IsHayes==True et minitel.IsHayesState=HayesOffline et CD présent passe à 'Booting' et IsHayesState à HayesOnline, E/7")
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
                            print("MainLoop():[Connected] minitel.IsHayes==True et minitel.IsHayesState=HayesOnline et CD absent ws.close()")
                            ws.close()
                        minitel.IsHayesState = HayesOffline
                        minitel._minitel.parity = 'N'
                        minitel._minitel.bytesize = 8
                    else:
                        if minitel.ConnectionState == "WaitingCall":
                            print("MainLoop():[WaitingCall] minitel.IsHayes==True et CD présent passe à 'Booting'")
                            minitel.ConnectionState="Booting"
                            print("WS Was disconnected from remote server but Hayes modem remains connected")
                else:
                    if minitel.ConnectionState != "WaitingCall":
                        if minitel.ConnectionState == "Booted":
                            print("MainLoop():[Booted] minitel.IsHayes==True et minitel.IsHayesState<>HayesOnline passe à 'WaitingCall'")
                            minitel.ConnectionState = "WaitingCall"
                        #minitel.ConnectionState="Booting"
                        else:
                            print("ERR : IsHayesState is 'HayesOffLine' but ConnectionState is not 'WaitingCall' {}".format(minitel.ConnectionState))
                    
            if minitel.ConnectionState == "WaitingCall":
                if minitel.IsHayes == False:
                    print("MainLoop():[WaitingCall] minitel.IsHayes==False passe à 'Booting'")
                    minitel.ConnectionState="Booting"
                else:
                    # Avoid eating all CPU while waiting to start a call
                    time.sleep(0.1)

            if minitel.ConnectionState == "Booting":    # Initialise les champs de saisie puis passe à "Booted"
                print("MainLoop():[Booting] Initialise les champs de saisie puis passe à 'Booted'")                
                print("Press 'l' to call local gateway")
                minitel.envoyer("\r\nPress 'l' to call local gateway\r\n")
                #zzconteneur = MyClass(minitel, 1, 14, 32, 4, 'jaune', 'bleu',"PageToto.vdt")
                #zzlabelNom = Label(minitel, 2, 15, "Nom", 'jaune')
                #zzchampNom = ChampTexte(minitel, 10, 15, 20, 60)
                #zzlabelPrenom = Label(minitel, 2, 16, "Prénom", 'jaune')
                #zzchampPrenom = ChampTexte(minitel, 10, 16, 20, 60)
                #zzconteneur.ajoute(labelNom)
                #zzconteneur.ajoute(champNom)
                #zzIndexChampNom=len(conteneur.elements)-1
                #zzconteneur.elements[IndexChampNom].valeur=DefaultServer
                #zzconteneur.ajoute(labelPrenom)
                #zzconteneur.ajoute(champPrenom)
                #zzIndexChampPrenom=len(conteneur.elements)-1
                minitel.ConnectionState = "Booted"
            if minitel.ConnectionState == "Booted":     # Gere les touches de fonction
                #print("MainLoop():[Booted] Gere les touches de fonction Suite/Retour/Repetition")
                #print("MainLoop():[Booted] Si Envoi, passe à 'Starting'")
                #print("MainLoop():[Booted] Si Connexion et minitel.ConnectionState=='Connected', ws.close()")
                #print("MainLoop():[Booted] Si touche non traitée, affiche la touche")
                
                #zzconteneur.affiche()
                #zzprint("Conteneur.executer()={}".format(conteneur.executer()))
                ToucheTraitee=False
                # Touche pas traitée en amont
                #zzif conteneur.sequence.egale(REPETITION):
                #zz    print ("Répétition !")
                #zz    ToucheTraitee=True
                #zzif conteneur.sequence.egale(CONNEXION):
                #zz    print ("Connexion !")
                #zz    if minitel.ConnectionState == "Connected":
                #zz        ws.close()
                #zz    ToucheTraitee=True
                #zzif conteneur.sequence.egale(ENVOI):
                #zz    print ("Envoi !")
                try:
                  # Avoid eating all CPU while waiting to start a call
                  time.sleep(0.1)
                  char=minitel.recevoir(attente=0.1)
                except Empty:
                  char=""
                  pass
                if (char=='l') or (char=='L'):
                  print("MainLoop():[Key 'l'] minitel.ConnectionState = 'Booted' passe à 'Starting'")
                  ToucheTraitee=True
                  minitel.ConnectionState = "Starting"
                #zzif ToucheTraitee == False:
                #zz    print ( "InMain[{}]".format(conteneur.sequence) )
                #zz    print ( "Longueur" )
                #zz    print (conteneur.sequence.longueur )
                #zz    print ( "Valeurs" )
                #zz    for element in conteneur.sequence.valeurs:
                #zz        print ( element )
                #zz    for element in conteneur.elements:
                #zz        if element.activable == True:
                #zz            print(element.valeur)                
            if minitel.ConnectionState == "Starting":
                print ("Starting connection")
                print("MainLoop():[Starting] Ouvre la session WS - Si succès, passe à 'Started', Si échec, passe à 'Booted'")
                #zznom=conteneur.elements[IndexChampNom].valeur.upper()
                #zzminitel.ConnectionString=None
                #zzif DefaultServer.upper() == nom:
                minitel.ConnectionString = DefaultConnectionString
                #zz    print ("Default address")
                #zzif minitel.ConnectionString == None:
                #zz    for server in YellowPages['servers']:
                #zz        if server.get("name").upper() == nom:
                #zz            minitel.ConnectionString=server.get("address")
                #zz            print ("Found address")
                #zzif minitel.ConnectionString == None:
                #zz        print("Pas de chaine de connexion => Prise en compte des données brutes saisies")
                #zz        if len(conteneur.elements[IndexChampNom].valeur) >0:
                #zz            minitel.ConnectionString=conteneur.elements[IndexChampNom].valeur
                #zz            if len(conteneur.elements[IndexChampPrenom].valeur) >0:
                #zz                minitel.ConnectionString += "/" + conteneur.elements[IndexChampPrenom].valeur
                if minitel.ConnectionString != None:
                    try:
                        #ws = WsMinitelClient(minitel.ConnectionString, protocols=['http-only', 'chat'])
                        print (minitel.ConnectionString)
                        ws = WsMinitelClient(minitel.ConnectionString, protocols=['https','http-only', 'chat'])
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
                print("MainLoop():[Connected et Ctrl+C] ws.close()")
                ws.close()
            minitel.QuitMinitel = True  #minitel.ConnectionState="Closed"
            #pass
        except :
            print ("Minitel.ConnectionState={}".format(minitel.ConnectionState))
            if minitel.ConnectionState == "Started":
                print("MainLoop():[Started et EXCEPTION] passe à 'Booting'")
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


minitel.close()
print ( "Goodbye Minitel" )




