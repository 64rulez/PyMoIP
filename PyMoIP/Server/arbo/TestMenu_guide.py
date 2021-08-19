# TestMenu_Guide.py

PageDir="/home/pi/python/PyMoIP/TestPages/Serveur-PyMoIP/TestMenu/"
FirstFile=1
LastFile=1
PrefixFile="TestGuide"
VarList=[[3,4,['A','H'],"GotRom",3,'.']]
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

#DisplayList=["<Nom de la liste globale>",<Nb de lignes>,<Nb de colonnes>,<Première ligne>,<Première colonne>,<TailleColonne>,[<Liste des champs à afficher>],<Caractère de remplissage pour l'effacement>,<Attributs pour l'effacement>,<Caractère de remplissage pour l'affichage>,<Attributs pour l'affichage>]
#[<Liste des champs à afficher>]=[<Numéro du champ dans la liste globale>,<Nb de caractères dans le champ>,<Nb de caractères à passer avant>,[<Attributs>]]