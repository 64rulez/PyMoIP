# Teletel-mgs.py

PageDir="/home/pi/python/PyMoIP/TestPages/Serveur-Teletel/Teletel-mgs/"
FirstFile=1
LastFile=2
PrefixFile="Teletel-mgs"
VarList=[[1,4,['A'],"%GotRom",3,'.'],[1,35,[],"%NumPageDisplayList",2,"/"],[1,37,[],"%NumPagesDisplayList",2," "],[24,2,[],"*ListSession:*:3,2",15,"_"]]
FieldList=[[24,35,[],"Text01",5,"."]]
GuideLink="MGS_guide"
Module="module_menu"
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
MenuList=[]#[["Menu1","TestMenu.Test1"],["Menu2","TestMenu.Test2"],["Menu3","TestMenu.Test3"],["DemoJet7","arbo_demo-jet7"]]
DisplayList=["%MenuList",1,3,12,2,10,[[0,2,1,[]],[1,5,1,['B']]],"#",['B','H'],"_",['A']]
DisplayList=["*ListSession",22,1,2,1,39,[[0,2,1,[]],[1,2,0,[]],[2,15,1,[]],[3,11,1,[]],[4,1,1,[]]],"_",['C','H'],".",['A']]

#DisplayList=["<Nom de la liste globale>",<Nb de lignes>,<Nb de colonnes>,<Premi�re ligne>,<Premi�re colonne>,<TailleColonne>,[<Liste des champs � afficher>],<Caract�re de remplissage pour l'effacement>,<Attributs pour l'effacement>,<Caract�re de remplissage pour l'affichage>,<Attributs pour l'affichage>]
#[<Liste des champs � afficher>]=[<Num�ro du champ dans la liste globale>,<Nb de caract�res dans le champ>,<Nb de caract�res � passer avant>,[<Attributs>]]