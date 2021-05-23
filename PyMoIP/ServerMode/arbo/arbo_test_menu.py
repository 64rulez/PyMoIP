# arbo_test_menu.py

PageDir="/home/pi/python/PyMoIP/TestPages/Serveur-PyMoIP/TestMenu/"
FirstFile=1
LastFile=1
PrefixFile="TestMenu0"
VarList=[[3,4,['A','H'],"%GotRom",3,'.'],[2,14,[],"%ArboCur",15,'.'],[3,8,[],"Text02",0,'']]
FieldList=[[23,30,[],"Text01",5,"."]]
GuideLink="TestMenu_guide"
Module="module_menu"
TimerDelay=3      # Nombre de secondes d'inactivite avant declanchement dans le module

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
MenuList=[["TestMenu1","TestMenu_Test1"],["TestMenu2","TestMenu_Test2"],["TestMenu3","TestMenu_Test3"],["DemoJet7","arbo_demo-jet7"]]
DisplayList=["%MenuList",7,1,12,2,33,[[0,2,1,[]],[1,9,1,['B']],[2,18,1,['C','H']]],"#",['B','H'],":",['A']]

#DisplayList=["<Nom de la liste globale>",<Nb de lignes>,<Nb de colonnes>,<Première ligne>,<Première colonne>,<TailleColonne>,[<Liste des champs à afficher>],<Caractère de remplissage pour l'effacement>,<Attributs pour l'effacement>,<Caractère de remplissage pour l'affichage>,<Attributs pour l'affichage>]
#[<Liste des champs à afficher>]=[<Numéro du champ dans la liste globale>,<Nb de caractères dans le champ>,<Nb de caractères à passer avant>,[<Attributs>]]