# arbo_start.py

PageDir="/home/pi/python/PyMoIP/TestPages/Serveur-PyMoIP/"
FirstFile=1
LastFile=1
PrefixFile="Start_"
GuideLink="arbo_demo-jet7"
TimeoutLink=""    #"arbo_demo-jet7"
TimerLink=""      #"arbo_demo-jet7"
VarList=[[3,4,['A','H'],"%GotRom",3,'.'],[4,4,['B'],"%GotRam1",16,'#'],[5,4,[],"%GotRam2",2,"="],[7,20,[],"*ListSession:*:3",18,"*"],[8,2,[],"#DoDebugSetArbo",18,"*"],[8,30,[],"%NumPageDisplayList",5,"#"]]
FieldList=[[21,4,[],"Text01",20,"."],[22,4,[],"Text02",20,"."]]
BypassList = [["*ListSession:*:3","Cond1","Val1","Pos1"],["Text01","Cond2","Val2","Pos2"],["%MenuList","Cond3","Val3","Pos3"],["%GotRom","==","Bv9","arbo_main"],["%GotRom","=*","Cp","arbo_timtel"],["%GotRom","=*","Pv","arbo_timtel"],["%GotRom","=*","C","arbo_alcatel"]]
TimeoutLimit=10      # Nombre de secondes depuis SetArbo() avant declanchement 
TimerDelay=30        # Nombre de secondes d'inactivite avant declanchement

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
MenuList=[["TestMenu","arbo_test_menu"],["Menu2","PageMenu2"],["Menu3","PageMenu3"],["Menu4","arbo_demo-jet7"]]
DisplayList=["*ListSession",3,2,12,3,12,[[0,2,1,[]],[1,5,1,[]],[2,5,1,[]]],"=",['B','H'],"_",['A']]
DisplayList=["TestList",7,2,12,2,15,[[0,2,1,[]],[1,5,1,['B']],[2,5,1,['C','H']]],"",['B','H'],"_",['A']]
DisplayList=["*TestList",7,2,12,2,15,[[0,2,1,[]],[1,5,1,['B']],[2,5,1,['C','H']]],"",['B','H'],"_",['A']]
DisplayList=["%MenuList",7,2,12,2,15,[[0,2,1,[]],[1,10,1,['B']],[2,20,1,['C','H']]],"",['B','H'],"_",['A']]

#DisplayList=["<Nom de la liste globale>",<Nb de lignes>,<Nb de colonnes>,<Première ligne>,<Première colonne>,<TailleColonne>,[<Liste des champs à afficher>],<Caractère de remplissage pour l'effacement>,<Attributs pour l'effacement>,<Caractère de remplissage pour l'affichage>,<Attributs pour l'affichage>]
#[<Liste des champs à afficher>]=[<Numéro du champ dans la liste globale>,<Nb de caractères dans le champ>,<Nb de caractères à passer avant>,[<Attributs>]]