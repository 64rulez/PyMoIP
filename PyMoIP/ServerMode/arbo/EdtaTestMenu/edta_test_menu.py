# %arbo%/EdtaTestMenu/edta_test_menu.py

PageDir="/home/pi/python/PyMoIP/TestPages/Serveur-PyMoIP/TestEdta/"
FirstFile=1
LastFile=2
PrefixFile="EDTA_MenuMT"
VarList=[[3,4,['A','H'],"%GotRom",3,'.'],[1,35,[],"%NumPageDisplayList",2,"/"],[1,37,[],"%NumPagesDisplayList",2," "]]
FieldList=[[22,38,[],"Text01",2,"."]]
GuideLink="TestMenu_guide"
Module="module_menu"
#
# VarList = Affiche une liste de variables après l'affichage d'une page (rafraichissement dynamique des variables avant chargement de la page)
#
# Liste vide = [] (valeur par défaut)
# Liste avec un seul item = [[PosY,PosX,[Attrib],"VarName",Size,'Char']]
# Liste avec plusieurs items = [[PosY,PosX,[Attrib],"VarName",Size,'Char'],[PosY,PosX,[Attrib],"VarName",Size,'Char']]
#
# - PosY = Ligne où devra être affichée la variable
# - PosX = Colonne où devra être positionnée la variable
# - Attrib = Liste des attributs pour l'affichage de la variable - ex : [] pour liste vide, ou ['A'] pour caractère bleu ou ['A','H'] caractère bleu et clignottant
# - "VarName" = Nom de la variable à afficher (peut être INT, STR, ou bin (utf-8))
# - Size = Préremplissage du champ avec Size caractères (si 0, pas de préremplissage)
# - 'Char' = Caractère de préremplissage (sans objet si size=0 mais doit être présent)
#
MenuList=[["Tests simples","EdtaTestMenu.Test1Simple"],["Tests compliques","EdtaTestMenu.Test2Complique"],["Differences M1b","EdtaTestMenu.Test3Difference"],["Bugs Minitel","EdtaTestMenu.Test4Bug"],["Tables ASCII","EdtaTestMenu.Test5Ascii"],["DoodlePaves","EdtaTestMenu.DoodlePaves"],["DoodleDRCS","EdtaTestMenu.DoodleDRCS"],["DoodlePhoto","EdtaTestMenu.DoodlePhoto"],["DoodleHaMinitel","EdtaTestMenu.DoodleHaMinitel"]]
DisplayList=["%MenuList",3,2,12,5,15,[],"",[],"",[]]
# [0,2,1,[]],[1,5,1,['B']] - Liste des champs � afficher
# "#" - Caract�re de remplissage pour effacement
# 'B','H' - Liste des attributs pour effacement
# "_" - Caract�re de remplissage pour affichage
# 'A' - Liste des attributs pour affichage

#DisplayList=["<Nom de la liste globale>",<Nb de lignes>,<Nb de colonnes>,<Première ligne>,<Première colonne>,<TailleColonne>,[<Liste des champs à afficher>],<Caractère de remplissage pour l'effacement>,<Attributs pour l'effacement>,<Caractère de remplissage pour l'affichage>,<Attributs pour l'affichage>]
#[<Liste des champs à afficher>]=[<Numéro du champ dans la liste globale>,<Nb de caractères dans le champ>,<Nb de caractères à passer avant>,[<Attributs>]]