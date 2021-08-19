# D�finition des variables arbo par d�faut (afin de ne pas repeter toutes les d�finitions dans tous les fichiers)


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
# VarList = Affiche une liste de variables apr�s l'affichage d'une page (rafraichissement dynamique des variables avant chargement de la page)
#
# Liste vide = [] (valeur par d�faut)
# Liste avec un seul item = [[PosY,PosX,[Attrib],"VarName",Size,'Char']]
# Liste avec plusieurs items = [[PosY,PosX,[Attrib],"VarName",Size,'Char'],[PosY,PosX,[Attrib],"VarName",Size,'Char']]
#
# - PosY = Ligne o� devra �tre affich�e la variable
# - PosX = Colonne o� devra �tre positionn�e la variable
# - Attrib = Liste des attributs pour l'affichage de la variable - ex : [] pour liste vide, ou ['A'] pour caract�re bleu ou ['A','H'] caract�re bleu et clignottant
# - "VarName" = Nom de la variable � afficher (peut �tre INT, STR, ou bin (utf-8))
# - Size = Pr�remplissage du champ avec Size caract�res (si 0, pas de pr�remplissage)
# - 'Char' = Caract�re de pr�remplissage (sans objet si size=0 mais doit �tre pr�sent)
#
DisplayList=[]
MenuList=[]
KeywordList=[["jet1","arbo_demo-jet7"],["start","arbo_start"]]