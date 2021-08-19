#!/usr/bin/envh python
# -*- coding: utf-8 -*-
# PyMoIP_global for PyMoIP_server

DoDebugAsync   = False     # Affiche les infos de trace pour l'async
DoDebugInput   = True     # Affiche les infos de trace pour l'async


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
    # Constantes pour les variables (et les constantes)
    #
    VAR_POSV = 0
    VAR_POSH = 1
    VAR_ATTRIBS = 2
    VAR_NAME = 3
    VAR_SIZE = 4
    VAR_FILL = 5
    #
    # Constantes pour les champs
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
    LIST_SESSION_FROMGATEWAY  = 4
    LIST_SESSION_MYARBO  = 5
    #
    # Constantes pour Arbo/StateRedir
    #
    NO_REDIR = 0       # Pas de redirection
    START_REDIR = 1    # Début de redirection (connecting) 
    OK_REDIR = 2       # Redirection en cours (connected)
    

