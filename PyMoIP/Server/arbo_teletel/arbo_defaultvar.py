# Définition des variables arbo par défaut (afin de ne pas repeter toutes les définitions dans tous les fichiers)


PageDir="/home/pi/python/PyMoIP/TestPages/"
FirstFile=0
LastFile=0
PrefixFile=""
PostfixFile=".vdt"
GuideLink=""
TimeoutLink=""
TimerLink=""
ConstList=[]
VarList=[]
FieldList=[]
BypassList=[]
TimeoutLimit=0      # Nombre de secondes d'inactivite avant declanchement
TimerDelay  =0      # Nombre de secondes d'inactivite avant declanchement

Module="<None>"

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
DisplayList=[]
MenuList=[]
KeywordList=[["jet1","arbo_demo-jet7"],["start","arbo_start"]]