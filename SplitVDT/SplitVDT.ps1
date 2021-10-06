$ErrorActionPreference = 'Stop' # Abort, if something unexpectedly goes wrong.
$trace=$false
try {
    Import-Module PsIni
}                       # Chargement du module PsIni (cf : https://github.com/lipkau/PsIni)
catch {
    Install-Module -Scope CurrentUser PsIni
    Import-Module PsIni                             # https://github.com/lipkau/PsIni
}
#
# Concerne le fichier de configuration
#
$ConfigFile="config_SplitVDT.ini"
$ConfigSection="Default"
$ConfigFound=$false
$conf=[ordered]@{}

#
# Valeurs par défaut en dur au cas où le fichier de configuration ne contiendrait pas de section [Default]
#
$SkipComment=$false                            # Si $True => Insère une page d'info avant la page extraite
$EffacerFichiersAvant=$true                    # Si $True => Supprime tous les fichiers dans les répertoires destination avant de débuter l'extraction
$SourceDir=".\mta\teaser.tlt.vdt"              # Source VDT sur la machine source (répertoire (avec wildcard possible) ou fichier)
$DestDir="TestMta"                             # Répertoire destination VDT sur la machine source [pages converties, pages commentaires]
$DestArboDir="TestMtaArbo"                     # Répertoire destination des noeuds arbos sur la machine source - ATTENTION, les points sont interdits
$SkipWarn127=$true                             # Saute les pages qui contiennent des char >127 (pages photo ?)
#
$CommentPageName="Cust_MPV.vdt"                 # Page VDT source commentaire sur la machine source
$CommentSourceDeLaPage="goto10.fr Amitel210b"
$CommentAuteurDeLaPage="LDFA"
$CommentText="Pages extraites de l'archive|'Amitel210b.lha' puis decoupees|automatiquement"
$CommentStartX=10                                 # Colonne de début des commentaires
$CommentTextStartX=2                              # Colonne de début des commentaires (pour $CommentText seulement)
$CommentStartY=9                                  # Ligne de début des commentaires
$CommentAttribs="A"
#
$TargetGuideLink=""                                                # Destiné au fichier Arbo
$PostFix=".vdt"                                                    # Post-fix des pages constituées (aussi destiné au fichier arbo)
$FieldList='[0,30,[],"Text01",2,"."]'                              # Position et attributs du champ de saisie
$TimerDelay=5
$DisplaySpeed=960    # en CPS
#
$TargetPageDir="/home/pi/python/PyMoIP/TestPages/Mta/"
$TargetArboDir="Mta"                                        # Emplacement des fichiers arbo sur le serveur - ATTENTION, les points sont interdits
#
$LineOffset=30
$LineHeigth=40
$PosButton=182
$LineWidth=@(550,400)
$ColPos=@(810,850)
$GUI_Groups=@(3,$ColPos[0],10,($LineWidth[0]+24),(3*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Répetroires locaux"),
            @(3,$ColPos[0],170,($LineWidth[0]+24),(3*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Mode de conversion"),
            @(8,$ColPos[0],320,($LineWidth[0]+24),(8*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Définition des pages d'infos/commentaires"),
            @(2,($ColPos[1]+$LineWidth[0]),10 ,($LineWidth[1]+24),(2*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Répertoire effectif sur la machine serveur PyMoIP"),
            @(5,($ColPos[1]+$LineWidth[0]),320,($LineWidth[1]+24),(5*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Constantes des noeuds d'arbo générés"),
            @(1,($ColPos[1]+$LineWidth[0]),170,($LineWidth[1]+24),(2.5*$LineHeigth+$LineOffset-$LineHeigth/2+5),"Chaines détectées pour la séparation des pages"),
            @(1,10,10,($ColPos[0]-20),(1*$LineHeigth+$LineOffset-$LineHeigth/2+8),"Fichier de configuration")

$Button_Click_Select_SourceDir       = { Select_SourceDir }
$Button_Click_Select_DestDir         = { Select_DestDir }
$Button_Click_Select_DestArboDir     = { Select_DestArboDir }
$Button_Click_Select_CommentPageName = { Select_CommentPageName }
$Button_Click_Select_NewConf         = { Select_NewConf  }
$Button_Click_Select_DelConf         = { Select_DelConf  }
$Button_Click_Select_SaveConf        = { Select_SaveConf }

$Event_TextChanged = {
    #[System.Windows.Forms.MessageBox]::Show("Event_TextChanged" , "Will update GUI")
    if ($trace -eq $true) { write-host("EventTextChanged()") }
    $TextValue=GUI_GetTextValue
    if ($trace -eq $true) { write-host("Test si valeur ComboBox GUI (`$Control.Text=" + $TextValue +") est different de la section en cours `$ConfigSection="+$ConfigSection) }
    if ($TextValue -ne $ConfigSection) {
        if ($trace -eq $true) { write-host("***********`r`n***********") }
       if ($trace -eq $true) {  write-host("Section changée") }
        if ($trace -eq $true) { write-host("***********`r`n***********") }
        SaveConfFromGUI
        UpdateConfigSection $TextValue
        #UpdateGUI_FromVars
        UpdateVarsFromConf
        UpdateGUI_NewSectionSelected
        UpdateGUI_FromVars
        if ($trace -eq $true) { write-host("***********`r`n") }
    }
    if ($trace -eq $true) { write-host("EventTextChanged() done") }
}

$GUI_Var=$data = @(
    [pscustomobject]@{Grp=0;VarName='SourceDir';              PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[0]; SizY=18; Fileselect=$true; Callback = "Button_Click_Select_SourceDir"}
    [pscustomobject]@{Grp=0;VarName='DestDir';                PosX=10; PosY=($LineHeigth * 1)+$LineOffset;SizX=$LineWidth[0]; SizY=18; Fileselect=$true; Callback = "Button_Click_Select_DestDir"}
    [pscustomobject]@{Grp=0;VarName='DestArboDir';            PosX=10; PosY=($LineHeigth * 2)+$LineOffset;SizX=$LineWidth[0]; SizY=18; Fileselect=$true; Callback = "Button_Click_Select_DestArboDir"}

    [pscustomobject]@{Grp=1;VarName='SkipComment';            PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[0]; SizY=18; OnOffSelect=$true}
    [pscustomobject]@{Grp=1;VarName='EffacerFichiersAvant';   PosX=10; PosY=($LineHeigth * 1)+$LineOffset;SizX=$LineWidth[0]; SizY=18; OnOffSelect=$true}
    [pscustomobject]@{Grp=1;VarName='SkipWarn127';            PosX=10; PosY=($LineHeigth * 2)+$LineOffset;SizX=$LineWidth[0]; SizY=18; OnOffSelect=$true}

    [pscustomobject]@{Grp=2;VarName='CommentPageName';        PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[0]; SizY=18; Fileselect=$true; Callback = "Button_Click_Select_CommentPageName"}
    [pscustomobject]@{Grp=2;VarName='CommentSourceDeLaPage';  PosX=10; PosY=($LineHeigth * 1)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=2;VarName='CommentAuteurDeLaPage';  PosX=10; PosY=($LineHeigth * 2)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=2;VarName='CommentText';            PosX=10; PosY=($LineHeigth * 3)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=2;VarName='CommentStartX';          PosX=10; PosY=($LineHeigth * 4)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true; IsInt=$true; MaxVal=39 ; MinVal=1}
    [pscustomobject]@{Grp=2;VarName='CommentTextStartX';      PosX=10; PosY=($LineHeigth * 5)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true; IsInt=$true; MaxVal=39 ; MinVal=1}
    [pscustomobject]@{Grp=2;VarName='CommentStartY';          PosX=10; PosY=($LineHeigth * 6)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true; IsInt=$true; MaxVal=24 ; MinVal=0}
    [pscustomobject]@{Grp=2;VarName='CommentAttribs';         PosX=10; PosY=($LineHeigth * 7)+$LineOffset;SizX=$LineWidth[0]; SizY=18; TextSelect=$true}

    [pscustomobject]@{Grp=3;VarName='TargetPageDir';          PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=3;VarName='TargetArboDir';          PosX=10; PosY=($LineHeigth * 1)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true}

    [pscustomobject]@{Grp=4;VarName='TargetGuideLink';        PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=4;VarName='PostFix';                PosX=10; PosY=($LineHeigth * 1)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=4;VarName='FieldList';              PosX=10; PosY=($LineHeigth * 2)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true}
    [pscustomobject]@{Grp=4;VarName='TimerDelay';             PosX=10; PosY=($LineHeigth * 3)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true; IsFloat=$true; MaxVal=60 ; MinVal=0.01}
    [pscustomobject]@{Grp=4;VarName='DisplaySpeed';           PosX=10; PosY=($LineHeigth * 4)+$LineOffset;SizX=$LineWidth[1]; SizY=18; TextSelect=$true; IsInt=$true; MaxVal=1920 ; MinVal=120}

    [pscustomobject]@{Grp=5;VarName='SplitList';              PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=$LineWidth[1]; SizY=(18*4); SplitSelect=$true}

    [pscustomobject]@{Grp=6;VarName='ConfigSection';          PosX=10; PosY=($LineHeigth * 0)+$LineOffset;SizX=210; SizY=21; ConfSelect=$true ;
                                                                CallbackNew = "Button_Click_Select_NewConf";
                                                                CallbackDel = "Button_Click_Select_DelConf";
                                                                CallbackSave = "Button_Click_Select_SaveConf";
                                                                CallbackText = "Event_TextChanged"}
)

$GUI_Desc=@( "Source VDT sur la machine source (répertoire (avec wildcard possible) ou fichier)",
            "Destination VDT sur la machine source [pages converties et pages commentaires]",
            "Destination des noeuds arbos sur la machine source - ATTENTION, les points sont interdits",

            "Si True => N'insère pas de page d'info/commentaires avant la page extraite",
            "Si True => Supprime tous les fichiers dans les répertoires destination avant de débuter l'extraction",
            "Si True => Saute les pages qui contiennent des char >127 (pages photo ?)",

            "Page VDT source 'infos/commentaire' sur la machine source",
            "Origine de la (série de) page(s) <40 caractères",
            "Auteur de l'origine <40 caractères",
            "Commentaire libre (x lignes <40 caractères) séparées de '|'",
            "Colonne de début (1 à 39)",
            "Colonne de début pour le commentaire libre (1 à 39)",
            "Ligne de début (0 à 24)",
            "Attributs @=Noir, A=Rouge, B=Vert, C=Jaune, D=Bleu, E=Magenta, F=Cyan, G=Blanc ...",

            "Pages VDT - ATTENTION, '\' => '/' sous Linux !",
            "Noeuds arbo - ATTENTION, '\' => '.' pour module python !",

            "Noeud d'arbo pour la touche [GUIDE] (ou '' ou vide)",
            "PostFix des pages VDT (.vdt)",
            "Définition du champ de saisie (ou [] si vide)",
            "Temps de pause nominal (>0 !)",
            "Vitesse de transmission théorique en CPS pour correction tempo (120 ou 960)",

            "[1 chaine par ligne - valeurs séparées par des ','] (ex 12 ou x1F,x40,x41 )",

            "Choix de la section"
            )
#

function UpdateVarsFromConf () {
    if ($trace -eq $true) { write-host("UpdateVarsFromConf() - Mise à jour des variables globales depuis `$conf[$ConfigSection]") }

    #if ($conf[$ConfigSection]["SkipComment"]) {           $SkipComment=[bool] (($conf[$ConfigSection]["SkipComment"]).toupper() -eq $true)    }
    if ($conf[$ConfigSection]["SkipComment"]) {           set-variable -name "SkipComment" -scope script -value ([bool] (($conf[$ConfigSection]["SkipComment"]).toupper() -eq $true))    }
    if ($conf[$ConfigSection]["EffacerFichiersAvant"]) {  set-variable -name "EffacerFichiersAvant" -scope script -value ([bool] (($conf[$ConfigSection]["EffacerFichiersAvant"]).toupper() -eq $true))    }
    if ($conf[$ConfigSection]["SourceDir"]) {             set-variable -name "SourceDir" -scope script -value ([string]$conf[$ConfigSection]["SourceDir"])    }
    if ($conf[$ConfigSection]["DestDir"]) {               set-variable -name "DestDir" -scope script -value ([string]$conf[$ConfigSection]["DestDir"])    }
    if ($conf[$ConfigSection]["DestArboDir"]) {           set-variable -name "DestArboDir" -scope script -value ([string]$conf[$ConfigSection]["DestArboDir"])    }
    if ($conf[$ConfigSection]["SkipWarn127"]) {           set-variable -name "SkipWarn127" -scope script -value ([bool] (($conf[$ConfigSection]["SkipWarn127"]).toupper() -eq $true))    }
    #
    if ($conf[$ConfigSection]["CommentPageName"]) {       set-variable -name "CommentPageName" -scope script -value ([string]$conf[$ConfigSection]["CommentPageName"])    }
    if ($conf[$ConfigSection]["CommentSourceDeLaPage"]) { set-variable -name "CommentSourceDeLaPage" -scope script -value ([string]$conf[$ConfigSection]["CommentSourceDeLaPage"])    }
    if ($conf[$ConfigSection]["CommentAuteurDeLaPage"]) { set-variable -name "CommentAuteurDeLaPage" -scope script -value ([string]$conf[$ConfigSection]["CommentAuteurDeLaPage"])    }
    if ($conf[$ConfigSection]["CommentText"]) {           set-variable -name "CommentText" -scope script -value ([string]$conf[$ConfigSection]["CommentText"])    }
    if ($conf[$ConfigSection]["CommentStartX"]) {         set-variable -name "CommentStartX" -scope script -value ([int]$conf[$ConfigSection]["CommentStartX"])    }
    if ($conf[$ConfigSection]["CommentTextStartX"]) {     set-variable -name "CommentTextStartX" -scope script -value ([int]$conf[$ConfigSection]["CommentTextStartX"])    }
    if ($conf[$ConfigSection]["CommentStartY"]) {         set-variable -name "CommentStartY" -scope script -value ([int]$conf[$ConfigSection]["CommentStartY"])    }
    if ($conf[$ConfigSection]["CommentAttribs"]) {        set-variable -name "CommentAttribs" -scope script -value ([string]$conf[$ConfigSection]["CommentAttribs"])    }
    #
    if ($conf[$ConfigSection]["TargetGuideLink"]) {       set-variable -name "TargetGuideLink" -scope script -value ([string]$conf[$ConfigSection]["TargetGuideLink"])    }
    if ($conf[$ConfigSection]["PostFix"]) {               set-variable -name "PostFix" -scope script -value ([string]$conf[$ConfigSection]["PostFix"])    }
    if ($conf[$ConfigSection]["FieldList"]) {             set-variable -name "FieldList" -scope script -value ([string]$conf[$ConfigSection]["FieldList"])    }
    if ($conf[$ConfigSection]["TimerDelay"]) {            set-variable -name "TimerDelay" -scope script -value ([float]$conf[$ConfigSection]["TimerDelay"])    }
    if ($conf[$ConfigSection]["DisplaySpeed"]) {          set-variable -name "DisplaySpeed" -scope script -value ([int]$conf[$ConfigSection]["DisplaySpeed"])    }
    #
    if ($conf[$ConfigSection]["SplitList"]) {             $SplitList=[string]$conf[$ConfigSection]["SplitList"]
        if ($trace -eq $true) { $SplitList }
        $SplitTabList=@()
        $SplitList=$SplitList.Split("[")
        foreach ($z in $SplitList) {
            if ($z.Length) {
                $SplitTabList+=($z.split("]"))[0]
            }
            else {
                if ($trace -eq $true) { write-host("Empty line found in `$SplitList (skipped)") }
            }
        }
        set-variable -name "SplitTabList" -scope script -value ($SplitTabList)
        $SplitTab=[byte[]]@()                                                                                # Création (effacement) du tableau binaire correspondant
        ConvertSplitTabList ([ref]$SplitTab)                                                                 # Remplissage du tableau binaire à partir du tableau de chaines
        set-variable -name "SplitTab" -scope script -value ($SplitTab)                                       # Création (effacement) du tableau binaire correspondant
        for (($i = 0),($IndexSplitTab=[int[]]@()); $i -lt $SplitTab.count; $i++) { $IndexSplitTab+=0}        # Création (effacement) du tableau d'index correspondant
        set-variable -name "IndexSplitTab" -scope script -value ($IndexSplitTab)                             # Création (effacement) du tableau binaire correspondant
    }         # Maj de $SplitTab et $IndexSplitTab à partir de $SplitList
    #
    if ($conf[$ConfigSection]["TargetPageDir"]) {         set-variable -name "TargetPageDir" -scope script -value ([string]$conf[$ConfigSection]["TargetPageDir"])    }
    if ($conf[$ConfigSection]["TargetArboDir"]) {         set-variable -name "TargetArboDir" -scope script -value ([string]$conf[$ConfigSection]["TargetArboDir"])    }
    
    if ($trace -eq $true) { write-host("UpdateVarsFromConf() done") }
}                                # Mise à jour des variables globales depuis $conf[$ConfigSection]
function ConvertSplitTabList ([ref]$SplitTab) {
    if ($SplitTab.value.count -gt 0) {    write-host("[ref]SplitTab should have been cleared before ConvertSplitTabList call !")}
    foreach ($elem in $SplitTabList) {
        #write-host ("ConvertSplitTabList "+$elem)
        $ToBytes=@()
        foreach ($byte in ($elem.split(","))) {
            #$byte
            $byte=$byte.trim()
            if (($byte.split('x').length) -gt 1) {
                $byte=$byte.split('x')[$byte.split('x').length - 1]
            } else {
                $byte=[Convert]::ToString($byte, 16)
            }
            $ToBytes+=[system.convert]::ToByte($byte,16)
        }
        $splittab.value+=""
        $SplitTab.value[($SplitTab.value.count)-1]=$ToBytes
    }
    if ($trace -eq $true) { write-host("ConvertSplitTabList() Converted "+$splitTab.value.count+" elements from SplitTabList") }
    #$SplitTab
}
#
# Construction de la liste de split [$SplitTab] par défaut
#
$SplitTabList=@()                # Création d'un tableau de chaines
#$SplitTabList+="12"             # Ajout d'une chaine par défaut (x12 = Effacement d'écran) pour séparation des pages
$SplitTabList+="xff,x00,x12"     # Ajout d'une chaine par défaut (x12 = Effacement d'écran) pour séparation des pages
$SplitTabList+="1,2,3"           # Ajout d'une chaine par défaut (x12 = Effacement d'écran) pour séparation des pages
$SplitTab=[byte[]]@()            # Création (effacement) du tableau binaire correspondant
ConvertSplitTabList ([ref]$SplitTab) # Remplissage du tableau binaire à partir du tableau de chaines
for (($i = 0),($IndexSplitTab=[int[]]@()); $i -lt $SplitTab.count; $i++) { $IndexSplitTab+=0}        # Création (effacement) du tableau d'index correspondant

if (Test-Path -Path $ConfigFile -PathType Leaf) {
    $conf = Get-IniContent $ConfigFile
    if ($trace -eq $true) { Write-Host "$ConfigFile loaded" }
    foreach ($key in $conf.keys) { 
        if ($Key -match $ConfigSection) {
            $ConfigFound=$true
            if ($trace -eq $true) { write-host ("`$ConfigSection '"+ $key+"' found in "+$ConfigFile) }
            #if ($trace -eq $true) { $conf[$ConfigSection] }
            #
            UpdateVarsFromConf
        }
    }
}   # Charger la configuration dans $conf[] depuis le fichier $ConfigFile - Si $ConfigSection trouvée, MAJ des variables à partir de $conf[]
else {
    if ($trace -eq $true) { Write-Host "$ConfigFile not found - Left empty !" }
}
if ($ConfigFound -ne $true) {
    $ConfigFound=$true
    if ($trace -eq $true) { Write-Host ("Section ["+ $ConfigSection + "] not found - defaults used !") }
    $conf+=[ordered] @{$ConfigSection={}}
    #$conf[$ConfigSection]+=@{"Bla"="Blu"}
    $conf[$ConfigSection]=@{}
    #$conf[$ConfigSection]+=@{"zaz"="hjgfjhfjg"}

    $conf[$ConfigSection]+=@{"SkipComment"=           $SkipComment }
    $conf[$ConfigSection]+=@{"EffacerFichiersAvant"=  $EffacerFichiersAvant }
    $conf[$ConfigSection]+=@{"SourceDir"=             $SourceDir }
    $conf[$ConfigSection]+=@{"DestDir"=               $DestDir }
    $conf[$ConfigSection]+=@{"DestArboDir"=           $DestArboDir }
    $conf[$ConfigSection]+=@{"SkipWarn127"=           $SkipWarn127 }
    #
    $conf[$ConfigSection]+=@{"CommentPageName"=       $CommentPageName }
    $conf[$ConfigSection]+=@{"CommentSourceDeLaPage"= $CommentSourceDeLaPage }
    $conf[$ConfigSection]+=@{"CommentAuteurDeLaPage"= $CommentAuteurDeLaPage }
    $conf[$ConfigSection]+=@{"CommentText"=           $CommentText }
    $conf[$ConfigSection]+=@{"CommentStartX"=         $CommentStartX }
    $conf[$ConfigSection]+=@{"CommentTextStartX"=     $CommentTextStartX }
    $conf[$ConfigSection]+=@{"CommentStartY"=         $CommentStartY }
    $conf[$ConfigSection]+=@{"CommentAttribs"=        $CommentAttrib }
            #
    $conf[$ConfigSection]+=@{"TargetGuideLink"=       $TargetGuideLink }
    $conf[$ConfigSection]+=@{"PostFix"=               $PostFix }
    $conf[$ConfigSection]+=@{"FieldList"=             $FieldList }
    $conf[$ConfigSection]+=@{"TimerDelay"=            $TimerDelay }
    $conf[$ConfigSection]+=@{"DisplaySpeed"=          $DisplaySpeed }
            #
    $SplittedList=""
    $NbElem=0
    foreach ($elem in $SplitTab) {
        $NbByte=0
        $ResultElem="["
        foreach ($byte in $elem) {
            $ResultElem+=$byte
            $NbByte+=1
            if ($NbByte -ne $elem.length) {
                $ResultElem+=","
            }
        }
        $ResultElem+="]"
        $NbElem+=1
        if ($NbElem -ne $SplitTab.Count) {
            $ResultElem+=","
        }
        $SplittedList+=$ResultElem
    }                         
    $conf[$ConfigSection]+=@{"SplitList"=             $SplittedList }
            #
    $conf[$ConfigSection]+=@{"TargetPageDir"=         $TargetPageDir }
    $conf[$ConfigSection]+=@{"TargetArboDir"=         $TargetArboDir }
}                       # Si $ConfigSection n'a pas été trouvée, l'ajouter à $conf[] à partir des variables définies par défaut


function AddSearchValue {
    param ( $ValueToAdd )

    $z=$IndexSplitTab.length
    $IndexSplitTab+=0
    $SplitTab+=""
    #$SplitTab[1]=[byte]255
    $SplitTab[$z]=$ValueToAdd
    return $SplitTab, $IndexSplitTab
}
function PositionTextAttribs {
    Param
    (    $PosX, $PosY, $Text, $Attribs
    )
    $enc = [system.Text.Encoding]::UTF8
    $data1 = ""
    foreach ($Attrib in $Attribs.ToCharArray()) {
        if ($data1 -eq "") {
            $data1= $enc.GetBytes([char]27)
        } else {
            $data1= $data1 + $enc.GetBytes([char]27)
        }
        $data1=$data1 + $enc.GetBytes($Attrib)
    }
    $data1=$data1 + $enc.GetBytes($Text) 
    return [byte]31,[byte]($PosY+64),[byte]($PosX+64), $data1
}

function NewPage {
    Param ( $CountPage, # Numéro de la page courante
            $PrevIndex, # Début de la page courante
            $CountByte, # Fin de la page courante
            $PageComment, # Contenu initial VDT de la page commantaire
            $PageBase,    # Répertoire destination des pages VDT sur cette machine
            $ArboBase     # Répertoire destination des noeuds arbo sur cette machine
             )

    [hashtable]$return = @{}
    $CountPage=$CountPage+1
    #
    # Get page contents
    #
    $Size=$CountByte - $PrevIndex
    $PageContent = new-object byte[] $Size
    $index=0
    $warned127=$false
    foreach ($byte in $PageContent) {
        $PageContent[$index]=$MyContent[$index+$Previndex]
        #write-host ($PageContent[$index])
        if (($PageContent[$index] -gt 127) -and ($warned127 -eq $false))  {
            $outputBox.lines += ("WARN : Byte>127 at index "+$index)
            $warned127=$true
        }
        $index+=1
    }
    #
    # Construction de la page commentaires
    #
    # Nom du fichier source
    $MyFile=$SourceFile.name
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+0) ($MyFile) $CommentAttribs
    # Date de la dernière modif du fichier source
    $LastWrite=$FileDesc.LastWriteTime.ToShortDateString()
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+1) $LastWrite $CommentAttribs
    # Numéro de page dans le fichier source
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+2) ([string]$Countpage) $CommentAttribs
    # Début de la page dans le fichier source
    $StartOffset=[System.Convert]::ToString($PrevIndex,16)
    while ($StartOffset.length -lt 4) {
        $StartOffset = "0"+$StartOffset
    }
    $StartOffset = "0x"+$StartOffset
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+3) $StartOffset $CommentAttribs
    # Fin de la page dans le fichier source
    $EndOffset=[System.Convert]::ToString($CountByte,16)
    while ($EndOffset.length -lt 4) {
        $EndOffset = "0"+$EndOffset
    }
    $EndOffset = "0x"+$EndOffset
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+4) $EndOffset $CommentAttribs
    # Source de la page
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+5) $CommentSourceDeLaPage $CommentAttribs
    # Auteur de la page
    $PageComment+= PositionTextAttribs $CommentStartX ($CommentStartY+6) $CommentAuteurDeLaPage $CommentAttribs
    # Commentaires dans les commentaires
    $CountLine=0
    foreach ($CommentLine in $CommentText.Split("|")) {
        $PageComment+= PositionTextAttribs $CommentTextStartX ($CommentStartY+8+$CountLine) $CommentLine $CommentAttribs        
        $CountLine=$CountLine+1
    }
    if (($warned127 -eq $false) -or ($SkipWarn127 -eq $false)){
        #
        # Ecriture des fichiers [noeud précédent, noeud actuel, page commentaire, page VDT]
        #
        $ArboName=$ArboBase+"-"+[string]$CountPage                                  # ATTENTION le .py ne doit pas figurer dans le lien
        $JustFile=$ArboName.Split("\")
        $JustFile=$JustFile[$JustFile.length-1]
        if ($UpdatePrevNode -ne "") {                                               # Si une précédente page a été générée
            $temp=get-content -Path ($UpdatePrevNode+".py") -Encoding UTF8          # Lire le noeud arbo correspondant pour mettre à jour son lien
            $temp.Split("`r")
            $newtemp=""
            foreach ($templine in $temp) {
                if ($templine.split("=")[0] -eq "TimerLink") {
                    $newtemp=$newtemp+"TimerLink="+'"'+$TargetArboDir+"."+$JustFile+'"'+"`r"
                    #$newtemp=$newtemp+"TimerLink="+'"'+$ArboName+'"'+"`r"
                }
                else {
                    $newtemp=$newtemp+$templine+"`r"
                }
            }
            $newtemp|Set-Content -Path ($UpdatePrevNode+".py") -Encoding UTF8
        }
        #
        # Sauvegarde du noeud arbo
        #
        $JustFile=$PageBase.Split("\")
        $JustFile=$JustFile[$JustFile.length-1]
        $NodeContent="# "+$ArboName+".py`r"
        $NodeContent=$NodeContent+"# Autogenere le "+ (get-date) +"`r"
        $NodeContent=$NodeContent+"# `r"
        $NodeContent=$NodeContent+"PageDir="+'"'+$TargetPageDir+'"'+"`r"
        $NodeContent=$NodeContent+"FirstFile=1`r"
        if ($SkipComment) {
            $NodeContent=$NodeContent+"LastFile=1`r"
        } else
        {   $NodeContent=$NodeContent+"LastFile=2`r"
        }
        $NodeContent=$NodeContent+"PrefixFile="+'"'+($JustFile+"-"+[string]$CountPage+"-")+'"'+"`r"
        $NodeContent=$NodeContent+"PostfixFile="+'"'+$PostFix+'"'+"`r"
        $NodeContent=$NodeContent+"GuideLink="+'"'+$TargetGuideLink+'"'+"`r"
        $NodeContent=$NodeContent+"TimeoutLink="+'""'+"`r"
        $NodeContent=$NodeContent+"TimerLink="+'""'+"`r"
        $NodeContent=$NodeContent+"ConstList=[]`r"
        $NodeContent=$NodeContent+"VarList=[]`r"
        $NodeContent=$NodeContent+"FieldList=["+$FieldList+"]`r"
        $NodeContent=$NodeContent+"TimeoutLimit=240`r"
        $temp=[Math]::Round([Math]::Ceiling($Size/$DisplaySpeed * 100) / 100, 2)+$TimerDelay
        $temp=ReplaceChar ([string]$temp) "," "."
        $NodeContent=$NodeContent+"TimerDelay="+$temp+"`r"
        $NodeContent=$NodeContent+"Module="+'"module_menu"'+"`r"

        $NodeContent|Set-Content -Path ($ArboName+".py") -Encoding UTF8
        $UpdatePrevNode=$ArboName
        #
        # Sauvegarde de la page commentaire
        #
        if (!$SkipComment) {
            $PageName=$PageBase+"-"+[string]$CountPage+"-1"+$PostFix
            $PageComment | Set-Content -Path $PageName -Encoding byte
            #Write-Host("Page:"+[string]$CountPage+" Size:"+[string]$Size+" Offset="+[System.Convert]::ToString($CountByte,16)+"    "+$PageName)
        }
        #
        # Sauvegarde de la page
        #
        if ($SkipComment) {
            $PageName=$PageBase+"-"+[string]$CountPage+"-1"+$PostFix
        }
        else
        {   $PageName=$PageBase+"-"+[string]$CountPage+"-2"+$PostFix
        }
        $PageContent | Set-Content -Path $PageName -Encoding byte
        $outputBox.lines += ("Page:"+[string]$CountPage+" Size:"+[string]$Size+" Offset="+[System.Convert]::ToString($CountByte,16)+"    "+$PageName)
        #
        #
    }
    else
    {   $outputBox.lines += ("WARN127 : Skipped page "+[string]$Countpage+" starting at offset "+$StartOffset)
        $CountPage=$CountPage-1
    }
    $outputBox.SelectionStart = $outputBox.Text.Length;
    $outputBox.ScrollToCaret()
    $outputBox.Refresh()

    $PrevIndex=$CountByte

    $return.PrevNode = $UpdatePrevNode
    $return.CountPage = $CountPage
    $return.PrevIndex = $PrevIndex
    $return.skipped = [bool]($warned127 -and $SkipWarn127)
    return $return
}

function ClearAllSplit {
    $Tab=0
    #$IndexSplit=0
    #Set-Variable -scope 1 -Name "IndexSplit" -Value (0)
    while ($tab -lt $IndexSplitTab.Count) {
        #Set-Variable -scope 1 -Name "IndexSplitTab[$Tab]" -Value (0)
        $IndexSplitTab[$Tab]=0
        $tab=$Tab+1
    }
}
function TestInSplitTab {
    param ( $byte )
    [hashtable]$return = @{}

    $Tab=0
    $RetVal=$false

    while (($tab -lt $IndexSplitTab.Count) -and ($RetVal -eq $false)){
        #$RetVal=$byte -eq $SplitChar[$IndexSplit]
        #$RetVal=$byte -eq $SplitTab[0][$IndexSplit]
        #foreach ($t in $SplitTab) {Write-Host $t}
        #foreach ($t in $indexSplitTab) {Write-Host $t}
        #write-host $SplitTab[$Tab]
        #write-host $SplitTab[$Tab][$IndexSplitTab[$Tab]]
        #write-host $IndexSplitTab[$Tab]
        $RetVal=$byte -eq $SplitTab[$Tab][$IndexSplitTab[$Tab]]

        if ($RetVal) {
            #$IndexSplit+=1
            #Set-Variable -scope 1 -Name "IndexSplit" -Value ($IndexSplit + 1)
            $z=$IndexSplitTab[$Tab]+1
            #Set-Variable -scope 1 -Name "IndexSplitTab[$Tab]" -Value ($IndexSplitTab[$tab] + 1)
            $IndexSplitTab[$Tab]=$IndexSplitTab[$Tab]+1
            #write-host $IndexSplitTab[$Tab]
        }
        else
        {
            #$IndexSplit=0
            #Set-Variable -scope 1 -Name "IndexSplitTab[$tab]" -Value (0)
            $IndexSplitTab[$Tab]=0
        }
        $tab=$Tab+1
    }
    $return.Found = [bool]($RetVal)
    #$return.SearchIndex = $IndexSplit
    $return.SearchIndex = $IndexSplitTab[($Tab-1)]
    #$return.SearchLen = $SplitChar.length
    #$return.SearchLen = $SplitTab[0].length
    $return.SearchLen = $SplitTab[($Tab-1)].length
    return $return
}

function ReplaceChar {
    param ($ArboBase, $Search, $Replace)
    $temp=($arbobase.Split($Search))
    $ArboBase=[system.String]::Join($Replace, $temp)
    return $arbobase
}

function CreateDestDir { param ( $DestDir )
    if (Test-Path -Path $DestDir -PathType Container) {
        $outputBox.lines +="Le dossier '$DestDir' existe."
        return $true
    } else {
        if (Test-Path -Path $DestDir) {
            $outputBox.lines += "'$DestDir' est un fichier !"
            return $false
        } else {
            if (New-Item -ItemType "directory" -Path $DestDir) {
                $outputBox += "Le dossier '$DestDir' a été créé"
                return $true
            } else {
                return $false
            }
        }
    }
}
function CheckDestDir { param ()
    $Result=$false
    if (CreateDestDir($DestDir)) {
        if (CreateDestDir($DestArboDir)) {
            $Result=$true
        }
    }
    return $Result
}


function SplitVDT { param ($outputBox)
    # Init - Charger page commentaire (sans commentaires !)
    if (!$SkipComment) {
        if (Test-Path -Path $CommentPageName -PathType leaf) {
            $MyCommentContent=get-content ($CommentPageName) -Encoding Byte -Raw
        }
        else {
            $MyCommentContent=[byte]""
            $outputBox.lines += "Problème avec '$CommentPageName' : n'est pas un fichier !"
        }
    }
    # Tester / Créer DestDir + DestArboDir
    if ((CheckDestDir) -eq $false) {
        $outputBox.lines += "Problème avec '$DestDir' ou '$DestArboDir' !"
    }
    else {
        # Effacer DestDir + DestArboDir
        if ($EffacerFichiersAvant) {
            Get-ChildItem $DestDir | Remove-Item
            Get-ChildItem $DestArboDir | Remove-Item
            $outputBox.lines += "'$DestDir' et '$DestArboDir' on été vidés"
        }
        # Balayer le dossier '$Sourcedir'

        $outputBox.lines += ("Traitement de '$SourceDir' ...")

        $SourceFiles=Get-ChildItem $SourceDir
        $CountFiles=0
        $TotalCountPages=0
        $TotalCountSkipped=0
        $UpdatePrevNode=""
        foreach ($SourceFile in $SourceFiles) {
            if (Test-Path -Path $ConfigFile -PathType Leaf) {
                $CountFiles=$CountFiles+1
                $PageBase=$DestDir+"\"+$SourceFile.Name
                $ArboBase=$DestArboDir+"\"+$SourceFile.Name
                $ArboBase=ReplaceChar $ArboBase "." "_"

                $outputBox.lines += ("Découpage de la page '"+$SourceFile+"'")

                $MyContent=get-content ($SourceFile) -Encoding Byte -Raw
                $FileDesc=Get-Childitem ($SourceFile)
    
                [int]$CountByte=0
                [int]$CountPage=0
                [int]$PrevIndex=0
                [int]$CountSkipped=0
                ClearAllSplit

                foreach ($byte in $MyContent) {
                    #if ($byte -eq $SplitChar) {
                    $return=TestInSplitTab($byte)
                    if ($return.found) {
                        if ($return.SearchIndex -eq $return.SearchLen) {
                            $return =NewPage $CountPage $PrevIndex ($CountByte-$return.SearchLen+1) $MyCommentContent $PageBase $ArboBase
                            $UpdatePrevNode = $return.PrevNode
                            $CountPage = $return.CountPage
                            $PrevIndex = $return.PrevIndex
                            if ($return.skipped) {
                                $CountSkipped=$CountSkipped+1
                            }
                        }
                    }
                    $CountByte=$CountByte+1
                }
                if ($CountByte -ne $PrevIndex){
                    $return =NewPage $CountPage $PrevIndex $CountByte $MyCommentContent $PageBase $ArboBase
                    $UpdatePrevNode = $return.PrevNode
                    $CountPage = $return.CountPage
                    $PrevIndex = $return.PrevIndex
                    if ($return.skipped) {
                        $CountSkipped=$CountSkipped+1
                    }
                }
                $outputBoxlines += ( "Fichier '"+$SourceFile+"' découpé en "+[string]$CountPage+" pages (et "+$CountSkipped+" pages sautées).")
                $TotalCountPages=$TotalCountPages+$CountPage
                $TotalCountSkipped=$TotalCountSkipped+$CountSkipped
            }
        }
    }
    $outputBox.lines += ""
    $outputBox.lines += ([string]$CountFiles+" fichiers traité(s) dans '"+$SourceDir+"'")
    $outputBox.lines += ("... produisant "+[string]$TotalCountpages+" page(s) (et "+$TotalCountSkipped+" pages sautées).")
    $outputBox.SelectionStart = $outputBox.Text.Length;
    $outputBox.ScrollToCaret()
    $outputBox.Refresh()
}


############################################## Start GUI functions
function StartButton { 
    if ($trace -eq $true) { write-host "StartButton()" }
    if ($outputBox.lines.Count -gt 1) {
        $outputBox.lines += ""
        $outputBox.SelectionStart = $outputBox.Text.Length;
        $outputBox.ScrollToCaret()
        $outputBox.Refresh()
    }
    $Button.Text = "Traitement en cours" 
    $Button.Refresh()
    SaveConfFromGUI
    UpdateVarsFromConf
    SplitVDT ($outputBox)
    $Button.Text = "Démarrer" 
    if ($trace -eq $true) { write-host "StartButton() done" }
} #end pingInfo
function GUI_getValues($formTitle, $textTitle){
    [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Drawing") 
    [void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") 
    $Script:userInput=""

    $objForm = New-Object System.Windows.Forms.Form
    $objForm.Text = $formTitle
    $objForm.Size = New-Object System.Drawing.Size(300,200)
    $objForm.StartPosition = "CenterScreen"

    $objForm.KeyPreview = $True
    $objForm.Add_KeyDown({if ($_.KeyCode -eq "Enter") {$Script:userInput=$objTextBox.Text;$objForm.Close()}})
    $objForm.Add_KeyDown({if ($_.KeyCode -eq "Escape") {$objForm.Close()}})

    $OKButton = New-Object System.Windows.Forms.Button
    $OKButton.Location = New-Object System.Drawing.Size(75,120)
    $OKButton.Size = New-Object System.Drawing.Size(75,23)
    $OKButton.Text = "OK"
    $OKButton.Add_Click({$Script:userInput=$objTextBox.Text;$objForm.Close()})
    $objForm.Controls.Add($OKButton)

    $CANCELButton = New-Object System.Windows.Forms.Button
    $CANCELButton.Location = New-Object System.Drawing.Size(150,120)
    $CANCELButton.Size = New-Object System.Drawing.Size(75,23)
    $CANCELButton.Text = "CANCEL"
    $CANCELButton.Add_Click({$objForm.Close()})
    $objForm.Controls.Add($CANCELButton)

    $objLabel = New-Object System.Windows.Forms.Label
    $objLabel.Location = New-Object System.Drawing.Size(10,20)
    $objLabel.Size = New-Object System.Drawing.Size(280,30)
    $objLabel.Text = $textTitle
    $objForm.Controls.Add($objLabel)

    $objTextBox = New-Object System.Windows.Forms.TextBox
    $objTextBox.Location = New-Object System.Drawing.Size(10,50)
    $objTextBox.Size = New-Object System.Drawing.Size(260,20)
    $objForm.Controls.Add($objTextBox)

    $objForm.Topmost = $True

    $objForm.Add_Shown({$objForm.Activate()})

    [void] $objForm.ShowDialog()

    return $userInput
}
function GUI_popUp($text,$title) {
    $a = new-object -comobject wscript.shell
    $b = $a.popup($text,0,$title,0)
}

function Select_SourceDir {
    if ($trace -eq $true) { write-host "Select_SourceDir"}
    $FileBrowser = New-Object System.Windows.Forms.OpenFileDialog -Property @{ InitialDirectory = $SourceDir}#[Environment]::GetFolderPath('Desktop') }
    $fileBrowser.Title = "Select_SourceDir"
    $result = $FileBrowser.ShowDialog()
    if ($result -eq [Windows.Forms.DialogResult]::OK){
        #write-host("File="+$FileBrowser.FileName)
        set-variable -name "SourceDir" -value ($FileBrowser.FileName) -scope script
        UpdateGUI_FromVars
    }
    if ($trace -eq $true) { write-host "Select_SourceDir done"}
}
function Select_DestDir {
    if ($trace -eq $true) { write-host "Select_DestDir" }
    $FolderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
    $FolderBrowser.selectedpath = "."
    $FolderBrowser.Description = "Select_DestDir"

    $result = $FolderBrowser.ShowDialog((New-Object System.Windows.Forms.Form -Property @{TopMost = $true }))
    if ($result -eq [Windows.Forms.DialogResult]::OK){
        #write-host("Folder="+$FolderBrowser.SelectedPath)
        set-variable -name "DestDir" -value ($FolderBrowser.SelectedPath) -scope script
        UpdateGUI_FromVars
    }
    if ($trace -eq $true) { write-host "Select_DestDir done" }
}
function Select_DestArboDir {
    if ($trace -eq $true) { write-host "Select_DestArboDir" }
    $FolderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
    $FolderBrowser.selectedpath = "."
    $FolderBrowser.Description = "Select_DestArboDir"

    $result = $FolderBrowser.ShowDialog((New-Object System.Windows.Forms.Form -Property @{TopMost = $true }))
    if ($result -eq [Windows.Forms.DialogResult]::OK){
        #write-host("Folder="+$FolderBrowser.SelectedPath)
        set-variable -name "DestArboDir" -value ($FolderBrowser.SelectedPath) -scope script
        UpdateGUI_FromVars
    }
    if ($trace -eq $true) { write-host "Select_DestArboDir done" }
}
function Select_CommentPageName {
    if ($trace -eq $true) { write-host "Select_CommentPageName" }
    $FileBrowser = New-Object System.Windows.Forms.OpenFileDialog -Property @{ InitialDirectory = $SourceDir}#[Environment]::GetFolderPath('Desktop') }
    $fileBrowser.Title = "Select_CommentPageName"
    $result = $FileBrowser.ShowDialog()
    Write-Host("--")
    if ($result -eq [Windows.Forms.DialogResult]::OK){
        #write-host("File="+$FileBrowser.FileName)
        set-variable -name "CommentPageName" -value ($FileBrowser.FileName) -scope script
        UpdateGUI_FromVars
    }
    if ($trace -eq $true) { write-host "Select_DestArboDir done" }
}

function Select_NewConf {
    if ($trace -eq $true) { write-host "Select_NewConf()" }
    $NewConf = GUI_getValues "Nouvelle configuration" "Entrer un nouveau nom de section"
    $NewConf=$NewConf.trim()
    if ($NewConf.length -gt 0) {
        $NewConfExist=$false
        foreach ($cnf in $Conf.Keys) {
            if (($cnf.ToUpper()) -eq ($NewConf.ToUpper())) {
                $NewConfExist=$true
            }
        }
        if ($NewConfExist -eq $true) {
            GUI_popUp "Cette section existe déjà." "ERREUR" 
        }
        else {
            #$Conf+=[ordered] @{$NewConf=$Conf[$ConfigSection]}
            if ($trace -eq $true) { write-host("***********`r`n***********")
                                    write-host("NewConf")
                                    write-host("***********`r`n***********") }
            SaveConfFromGUI
            $Conf+=[ordered] @{$NewConf=[ordered]@{}}
            foreach ($key in ($conf[$ConfigSection].keys)) {
                $conf[$NewConf]+= @{$key=$conf[$ConfigSection][$key]}
            }
            if ($trace -eq $true) { write-host ("Select_NewConf() : Added `$conf[" + $NewConf + "]") }
            UpdateConfTab $Conf # Nécessaire même si déjà fait par SaveConfFromGUI()
            UpdateConfigSection $NewConf
            #UpdateGUI_FromVars
            UpdateVarsFromConf
            UpdateGUI_NewSectionSelected
            if ($trace -eq $true) { write-host("***********`r`n") }
        }
    }
    else {
        #GUI_popUp  "Nom de section vide." "ERREUR"
    }
    if ($trace -eq $true) { write-host "Select_NewConf() done" }
}
function Select_DelConf {
    if ($trace -eq $true) { write-host "Select_DelConf()" }
    if (($ConfigSection.ToUpper()) -ne "DEFAULT") {
        $temp=[ordered]@{}
        foreach ($z in $conf.keys) {
            if (($z.toupper()) -ne ($ConfigSection.ToUpper())) {
                $temp+=[ordered] @{$z=$conf[$z]}
            }
        }
        if ($trace -eq $true) { write-host("***********`r`n***********")
                                write-host ("Select_DelConf() : Removed `$conf[" + $ConfigSection + "]")
                                write-host("***********`r`n***********") }
        UpdateConfTab $temp
        UpdateConfigSection "Default"
        #UpdateGUI_FromVars
        UpdateVarsFromConf
        UpdateGUI_NewSectionSelected
        if ($trace -eq $true) { write-host("***********`r`n") }
    }
    else {
        GUI_popUp  "Suppression impossible de la configuration par défaut." "ERREUR"
    }
    if ($trace -eq $true) { write-host "Select_DelConf() done" }
}
function Select_SaveConf {
    if ($trace -eq $true) { write-host "Select_SaveConf" }
    SaveConfFromGUI
    # UpdateConfTab $Conf # Pas nécessaire car déjà fait dans SaveConfFromGUI()
    #
    # Sauvegarde de la conf
    #
    $z=Out-IniFile -InputObject $conf -FilePath $Configfile -Force #"test_settings.ini"
    GUI_popUp("Sauvegarde de '"+$ConfigFile+"' effectuée") "Information"
    if ($trace -eq $true) { write-host("***********`r`n") }
}

function UpdateConfTab { param ($NewConfTab)
    if ($trace -eq $true) { write-host "UpdateConfTab() `$conf updated" }
    set-variable -name "Conf" -scope script -value $NewConfTab
    if ($trace -eq $true) { write-host "UpdateConfTab() done" }
}
function UpdateConfigSection { param ($NewSection)
    if ($trace -eq $true) { write-host ("UpdateConfigSection() `$ConfigSection updated (now = '"+ $NewSection+"')") }
    set-variable -name "ConfigSection" -scope script -value $NewSection
    if ($trace -eq $true) { write-host "UpdateConfigSection() done" }
}
function UpdateGUITextFromSplitTabList {
    $RetText=""
    foreach ($list in $SplitTabList) {
        if ($RetText -ne "") {
            $RetText = $RetText + "`r`n"
        }
        $RetText = $RetText + $list
    }
    return $RetText
}
function IsInt { param ($Control_text)
    $control_text=$control_text.trim()
    return ($control_text -match "^[0-9]?[0-9]*$")
}
function IsFloat { param ($Control_text)
    $control_text=$control_text.trim()
    return ($control_text -match "^[0-9]+[.]?[0-9]*$")
}

function NewOnOffGroupBox { param ($PosX , $PosY, $SizX, $SizY, $Text, $Name, $IsOn)
    $groupBox = New-Object System.Windows.Forms.GroupBox
    $groupBox.Location = New-Object System.Drawing.Size($PosX,$PosY) 
    $groupBox.size = New-Object System.Drawing.Size($SizX,$SizY) 
    $groupBox.text = $Text
    $groupBox.name = $Name
    $Form.Controls.Add($groupBox)
     
    $RadioButton1 = New-Object System.Windows.Forms.RadioButton 
    $RadioButton1.Location = new-object System.Drawing.Point(5,15) 
    $RadioButton1.size = New-Object System.Drawing.Size(39,20) 
    if ($IsOn) {
        $RadioButton1.Checked = $true 
    } else {
        $RadioButton1.Checked = $false
    } 
    $RadioButton1.Text = "On" 
    $groupBox.Controls.Add($RadioButton1) 

    $RadioButton2 = New-Object System.Windows.Forms.RadioButton
    $RadioButton2.Location = new-object System.Drawing.Point(44,15)
    $RadioButton2.size = New-Object System.Drawing.Size(38,20)
    if ($IsOn) {
        $RadioButton2.Checked = $false 
    } else {
        $RadioButton2.Checked = $true
    } 
    $RadioButton2.Text = "Off"
    $groupBox.Controls.Add($RadioButton2)
<#
$RadioButton3 = New-Object System.Windows.Forms.RadioButton
$RadioButton3.Location = new-object System.Drawing.Point(15,75)
$RadioButton3.size = New-Object System.Drawing.Size(80,20)
$RadioButton3.Text = "Ping thrice"
$groupBox02.Controls.Add($RadioButton3)
#>
    #return $groupBox
} # param ($PosX , $PosY, $SizX, $SizY, $Text, $Name, $IsOn)
function NewDesc {  param ($PosX , $PosY, $SizX, $SizY, $Name, $Desc, $Obj)
    $descBox = New-Object System.Windows.Forms.Label
    $descBox.Location = New-Object System.Drawing.Point($PosX,($PosY)) ### Location of the text box
    $descBox.Size = New-Object System.Drawing.Size($SizX,$SizY) ### Size of the text box
    $descBox.Name = ("Desc-"+$Name)
    $descBox.Text = $Desc
    #$form.Controls.Add($descBox)
    $obj.Controls.Add($descBox)
}          # param ($PosX , $PosY, $SizX, $SizY, $Name, $Desc, $Obj)
function NewTextBox {  param ($PosX , $PosY, $SizX, $SizY, $Text, $Name, $Desc, $Obj)
    $textBox = New-Object System.Windows.Forms.TextBox
    $textBox.Location = New-Object System.Drawing.Point($PosX,$PosY) ### Location of the text box
    $textBox.Size = New-Object System.Drawing.Size($SizX,$SizY) ### Size of the text box
    $textBox.Name = $Name
    $textBox.Text = $Text
    $textBox.Multiline = $false ### Allows multiple lines of data
    $textbox.AcceptsReturn = $true ### By hitting enter it creates a new line
    $textBox.ScrollBars = "Vertical" ### Allows for a vertical scroll bar if the list of text is too big for the window
    #$form.Controls.Add($textBox)
    $obj.Controls.Add($textBox)

    NewDesc ($PosX) ($PosY-15) ($SizX) ($SizY) ($Name) ($Desc) ($Obj)
}       # param ($PosX , $PosY, $SizX, $SizY, $Text, $Name, $Desc, $Obj)
function InitGui {
    $j=0
    for ($i=0 ;$i -lt ($GUI_Groups.Count); $i+=1) {
        $y=$Gui_Groups[$i]
        $groupBox = New-Object System.Windows.Forms.GroupBox
        $groupBox.Location = New-Object System.Drawing.Size($y[1],$y[2]) 
        $groupBox.size = New-Object System.Drawing.Size($y[3],$y[4]) 
        $groupBox.text = $y[5]
        $groupBox.name = "Group_"+[string]$i
        $Form.Controls.Add($groupBox)

        #for ($a=0;$a -lt $y[0];$a++) {
        for ($j=0;$j -lt ($GUI_Var.Count);$j++) {
            if ($GUI_var[$j].Grp -eq $i) {
                if ($trace -eq $true) { write-host("InitGUI() for Group_"+[string]$i+", item #"+[string]$j) }
                $b=$GUI_var[$j]
                #NewTextBox ($GUI_StartX + $GUI_StartX + 5) ($GUI_StartY + (20 + 5 +20) * $a) 55             20 ($a)                    ("IntTextBox_"+[string]$a) ("Val "+[string]$a) $groupBox
                #write-host("PosY="+($GUI_var[$j]).PosY)
                if ($GUI_var[$j].FileSelect -eq $True) {
                    NewTextBox ($GUI_var[$j].PosX + 80) ($GUI_var[$j].PosY) ($GUI_var[$j].SizX - 80) ($GUI_var[$j].SizY)  ((get-variable -name $GUI_var[$j].VarName).value)  ("IntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                    $Button = New-Object System.Windows.Forms.Button 
                    $Button.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX), ($GUI_var[$j].PosY-10)) 
                    $Button.Size = New-Object System.Drawing.Size((70), ($GUI_var[$j].SizY+10)) 
                    $Button.Text = "Select" 
                    #$Button.Add_Click( $GUI_var[$j].Callback) 
                    $Button.Add_Click( (get-variable -name ($GUI_Var[$j].Callback)).Value)
                    #$Button.Add_Click({Select_SourceDir}) 
                    $groupBox.Controls.Add($Button) 
                }
                elseif ($GUI_var[$j].OnOffSelect -eq $True) { 
                    $DropDownBox = New-Object System.Windows.Forms.ComboBox
                    $DropDownBox.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX), ($GUI_var[$j].PosY)) 
                    $DropDownBox.Size = New-Object System.Drawing.Size(100, ($GUI_var[$j].SizY)) 
                    $DropDownBox.Text = ((get-variable -name $GUI_var[$j].VarName).value)
                    $DropDownBox.Name= ("OnOffDropDownBox_"+[string]$j)
                    $DropDownBox.DropDownHeight = 80 
                    $groupBox.Controls.Add($DropDownBox) 

                    $wksList=@("True","False")

                    foreach ($wks in $wksList) {
                        [void]  $DropDownBox.Items.Add($wks)
                    } #end foreach
                    NewDesc ($GUI_var[$j].PosX) ($GUI_var[$j].PosY - 15) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ("IntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                }
                elseif ($GUI_var[$j].SplitSelect -eq $True) { 
                    $outputBox = New-Object System.Windows.Forms.TextBox 
                    $outputBox.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX),($GUI_var[$j].PosY)) 
                    $outputBox.Size = New-Object System.Drawing.Size(($GUI_var[$j].SizX),($GUI_var[$j].SizY)) 
                    $outputBox.MultiLine = $True
                    $outputBox.ScrollBars = "Vertical"
                    $outputBox.Text = UpdateGUITextFromSplitTabList
                    $groupBox.Controls.Add($outputBox) 
                    $outputBox.Name= ("SplitTabBox_"+[string]$j)

                    NewDesc ($GUI_var[$j].PosX) ($GUI_var[$j].PosY - 15) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ("IntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                }
                elseif ($GUI_var[$j].ConfSelect -eq $True) { 
                    $DropDownBox = New-Object System.Windows.Forms.ComboBox
                    $DropDownBox.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX), ($GUI_var[$j].PosY)) 
                    $DropDownBox.Size = New-Object System.Drawing.Size(($GUI_var[$j].SizX), ($GUI_var[$j].SizY)) 
                    $DropDownBox.Text = ((get-variable -name $GUI_var[$j].VarName).value)
                    $DropDownBox.Name= ("ConfDropDownBox_"+[string]$j)
                    $DropDownBox.DropDownHeight = 80 
                    $DropDownBox.add_textchanged((get-variable -name ($GUI_Var[$j].CallbackText)).Value)
                    $groupBox.Controls.Add($DropDownBox) 
                    foreach ($key in $conf.Keys) {
                        if ($key -ne "_") {
                            [void]  $DropDownBox.Items.Add($key)
                        }
                    } #end foreach
                    NewDesc ($GUI_var[$j].PosX) ($GUI_var[$j].PosY - 15) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ("IntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                    
                    $Button = New-Object System.Windows.Forms.Button 
                    $Button.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX+$GUI_var[$j].SizX+20+$PosButton*0), ($GUI_var[$j].PosY-10)) 
                    $Button.Size = New-Object System.Drawing.Size(($PosButton-10), ($GUI_var[$j].SizY+10)) 
                    $Button.Text = "Dupliquer" 
                    $Button.Add_Click( (get-variable -name ($GUI_Var[$j].CallbackNew)).Value)
                    $groupBox.Controls.Add($Button) 

                    $Button = New-Object System.Windows.Forms.Button 
                    $Button.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX+$GUI_var[$j].SizX+20+$PosButton*1), ($GUI_var[$j].PosY-10)) 
                    $Button.Size = New-Object System.Drawing.Size(($PosButton-10), ($GUI_var[$j].SizY+10)) 
                    $Button.Text = "Supprimer" 
                    $Button.Add_Click( (get-variable -name ($GUI_Var[$j].CallbackDel)).Value)
                    $groupBox.Controls.Add($Button) 

                    $Button = New-Object System.Windows.Forms.Button 
                    $Button.Location = New-Object System.Drawing.Size(($GUI_var[$j].PosX+$GUI_var[$j].SizX+20+$PosButton*2), ($GUI_var[$j].PosY-10)) 
                    $Button.Size = New-Object System.Drawing.Size(($PosButton-10), ($GUI_var[$j].SizY+10)) 
                    $Button.Text = "Sauver" 
                    $Button.Add_Click( (get-variable -name ($GUI_Var[$j].CallbackSave)).Value)
                    $groupBox.Controls.Add($Button) 
                }
                elseif ($GUI_var[$j].TextSelect -eq $True) {
                    if ($GUI_var[$j].IsInt -eq $True) {
                        NewTextBox ($GUI_var[$j].PosX) ($GUI_var[$j].PosY) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ((get-variable -name $GUI_var[$j].VarName).value)  ("IntIntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                    }
                    elseif ($GUI_var[$j].IsFloat -eq $True) {
                        NewTextBox ($GUI_var[$j].PosX) ($GUI_var[$j].PosY) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ((get-variable -name $GUI_var[$j].VarName).value)  ("IntFloatTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                    }
                    else {
                        NewTextBox ($GUI_var[$j].PosX) ($GUI_var[$j].PosY) ($GUI_var[$j].SizX) ($GUI_var[$j].SizY)  ((get-variable -name $GUI_var[$j].VarName).value)  ("IntTextBox_"+[string]$j) ($GUI_Desc[$j]) $groupBox
                    }
                }
                #$j++
            }
        }
    }
    <#
    ############################################## Start drop down boxes
    $DropDownBox = New-Object System.Windows.Forms.ComboBox
    $DropDownBox.Location = New-Object System.Drawing.Size(10,220) 
    $DropDownBox.Size = New-Object System.Drawing.Size(180,20) 
    $DropDownBox.Text = "blabla"
    $DropDownBox.DropDownHeight = 200 
    $Form.Controls.Add($DropDownBox) 

    $wksList=@("hrcomputer1","hrcomputer2","hrcomputer3","workstation1","workstation2","computer5","localhost")

    foreach ($wks in $wksList) {
        [void]  $DropDownBox.Items.Add($wks)
    } #end foreach

    ############################################## end drop down boxes
    #>
    ############################################## Start text fields

    $outputBox = New-Object System.Windows.Forms.TextBox 
    $outputBox.Location = New-Object System.Drawing.Size(10,(1.5*$LineHeigth+$LineOffset-$LineHeigth/2+60)) 
    $outputBox.Size = New-Object System.Drawing.Size(($ColPos[0]-20),(13*$LineHeigth))  # ($LineWidth[2]+24)
    $outputBox.MultiLine = $True 

    $outputBox.ScrollBars = "Vertical" 
    $Form.Controls.Add($outputBox) 

    ############################################## end text fields
    return $outputBox
}

function GUI_GetTextValue{
    $RetVal=""
    if ($trace -eq $true) { write-host("GUI_GetTextValue() start - Retourne la valeur de la combo box - Force 'Default' si le texte est invalide") }
    foreach ($Control in $form.Controls) {
        if ($control.name.split("_").length -gt 1) {
            $Index=$control.name.split("_")[$control.name.split("_").length -1]
            $Key=$control.name.split("_")[0]
            #write-host ("UpdateGUI() Index ="+[string]$Index+" Key="+$Key)
            if (($Key.toupper()) -eq "GROUP") {
                foreach ($Control in $Control.controls) {
                    if ($control.name.split("_").length -gt 1) {
                        $Index=$control.name.split("_")[$control.name.split("_").length -1]
                        $Key=$control.name.split("_")[0]
                        if ($Key -eq "ConfDropDownBox") {
                            if ($trace -eq $true) { write-host ("GUI_GetTextValue() Text="+$Control.Text +" Var="+((get-variable -name $GUI_var[$index].VarName).value)) }
                            #
                            $IsValid=$false
                            foreach ($key in $conf.Keys) {
                                if (($key -ne "_") -and ($key -ne $Control.Text)) {
                                    #
                                }
                                elseif ($key -eq "_") {
                                    #
                                }
                                else {
                                    $IsValid=$true
                                }
                            } #end foreach
                            if ($IsValid -eq $false) {
                                $Control.text="Default"
                                write-host("UpdateGUI_FromVars() Invalid text value found -> Default")
                            }
                            $RetVal=$Control.text
                        }
                    }
                }
            }
        }
    }
    if ($trace -eq $true) { write-host("GUI_GetTextValue() done") }
    return $RetVal
}                                     # Retourne la valeur de la combo box - Force 'Default' si le texte est invalide
function SaveConfFromGUI{
    if ($trace -eq $true) { write-host("SaveConfFromGUI() start - Mise à jour de `$conf[$ConfigSection][] en fonction du contenu du GUI") }
    foreach ($Control in $form.Controls) {
        if ($control.name.split("_").length -gt 1) {
            $Index=$control.name.split("_")[$control.name.split("_").length -1]
            $Key=$control.name.split("_")[0]
            #write-host ("SaveConfFromGUI() Index ="+[string]$Index+" Key="+$Key)
            if (($Key.toupper()) -eq "GROUP") {
                foreach ($Control in $Control.controls) {
                    #write-host $conf[$ConfigSection][($GUI_var[20].VarName)]
                    if ($control.name.split("_").length -gt 1) {
                        $Index=$control.name.split("_")[$control.name.split("_").length -1]
                        $Key=$control.name.split("_")[0]
                        if ($Key -eq "ConfDropDownBox") {
                            #write-host ("Found SaveConfFromGUI() ConfDropDownBox_"+[string]$Index)
                            #if (($Control.Text) -ne ((get-variable -name $GUI_var[$index].VarName).value)) {
                            #    $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                            #    $Control.Items.clear()
                            #    foreach ($key in $conf.Keys) {
                            #        if ($key -ne "_") {
                            #            [void]  $Control.Items.Add($key)
                            #        }
                            #    } #end foreach
                            #}
                        }
                        elseif ($key -eq "OnOffDropDownBox") {
                            $conf[$ConfigSection][($GUI_var[$index].VarName)]=$control.text
                        }
                        elseif ($key -eq "SplitTabBox") { #$GUI_var[$j].SplitSelect -eq $True) { 
                            $res=""
                            foreach ($line in ($Control.text.split())) {
                                $line=$line.trim()
                                if ($line.length -gt 0) {
                                    $line="["+[string]$line+"]"
                                    if ($res.length -eq 0) {
                                        $res=$line
                                    }
                                    else {
                                        $res=$res + "," + $line
                                    }
                                }
                            }
                            $conf[$ConfigSection][($GUI_var[$index].VarName)]=$res
                        }
                        elseif ($key -eq "IntTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            $conf[$ConfigSection][($GUI_var[$index].VarName)]=$control.text
                        }
                        elseif ($key -eq "IntIntTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            if (IsInt($Control.text)) {                         #   [int]$Control.text -is [int] ) {
                                if (([int]$Control.text -ge ($GUI_Var[$control.name.split("_")[1]].MinVal)) -and ([int]$Control.text -le ($GUI_Var[$control.name.split("_")[1]].MaxVal) ) ) {
                                    $temp = ("Int (GUI="+[string]$Control.text+") `$conf[$ConfigSection][$index] AVANT = "+ $conf[$ConfigSection][($GUI_var[$index].VarName)])
                                    $conf[$ConfigSection][($GUI_var[$index].VarName)]=[int]$control.text
                                    if ($trace -eq $true) { write-host($temp + " APRES = "+ $conf[$ConfigSection][($GUI_var[$index].VarName)]) }
                                }
                                else {
                                    if ($trace -eq $true) { write-host("Int ("+[string]$Control.text+") out of bounds ["+[string]($GUI_Var[$control.name.split("_")[1]].MinVal)+"<->"+[string]($GUI_Var[$control.name.split("_")[1]].MaxVal)+"]") }
                                    GUI_popUp  (    "Int (" + [string]$Control.text + ") hors des bornes [" + 
                                                      [string]($GUI_Var[$control.name.split("_")[1]].MinVal) + "<->" + 
                                                      [string]($GUI_Var[$control.name.split("_")[1]].MaxVal) + "] est invalide"
                                                ) "Saisie ignorée."
                                    $conf[$ConfigSection][($GUI_var[$index].VarName)]=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                    $Control.text=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                }
                            }
                            else {
                                if ($trace -eq $true) { write-host ("Int ("+[string]$Control.text+") is invalid") }
                                GUI_popUp  ("Int ("+[string]$Control.text+") est invalide") "Saisie ignorée."
                                $conf[$ConfigSection][($GUI_var[$index].VarName)]=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                $Control.text=($GUI_Var[$control.name.split("_")[1]].MinVal)
                            }
                        }
                        elseif ($key -eq "IntFloatTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            if (IsFloat($Control.text)) {                                     #  [float]$Control.text -is [float] ) {
                                if (([float]$Control.text -ge ($GUI_Var[$control.name.split("_")[1]].MinVal)) -and ([float]$Control.text -le ($GUI_Var[$control.name.split("_")[1]].MaxVal))){
                                    $temp = ("Float (GUI="+[string]$Control.text+") `$conf[$ConfigSection][$index] AVANT = "+ $conf[$ConfigSection][($GUI_var[$index].VarName)])
                                    $conf[$ConfigSection][($GUI_var[$index].VarName)]=[float]$control.text
                                    if ($trace -eq $true) { write-host($temp + " APRES = "+ $conf[$ConfigSection][($GUI_var[$index].VarName)]) }
                                }
                                else {
                                    if ($trace -eq $true) { write-host("Float ("+[string]$Control.text+") out of bounds ["+[string]($GUI_Var[$control.name.split("_")[1]].MinVal)+"<->"+[string]($GUI_Var[$control.name.split("_")[1]].MaxVal)+"]") }
                                    GUI_popUp  (    "Float (" + [string]$Control.text + ") hors des bornes [" + 
                                                      [string]($GUI_Var[$control.name.split("_")[1]].MinVal) + "<->" + 
                                                      [string]($GUI_Var[$control.name.split("_")[1]].MaxVal) + "] est invalide"
                                                ) "Saisie ignorée."
                                    $conf[$ConfigSection][($GUI_var[$index].VarName)]=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                    $Control.text=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                }
                            }
                            else {
                                if ($trace -eq $true) { write-host ("Float ("+[string]$Control.text+") is invalid") }
                                GUI_popUp  ("Float ("+[string]$Control.text+") est invalide") "Saisie ignorée."
                                $conf[$ConfigSection][($GUI_var[$index].VarName)]=($GUI_Var[$control.name.split("_")[1]].MinVal)
                                $Control.text=($GUI_Var[$control.name.split("_")[1]].MinVal)
                            }
                        }
                        elseif ($key -eq "Desc-IntTextBox") {
                            # Description - pas d'update
                        }
                        else {
                            #write-host("SaveConfFromGUI() unknown key="+[string]$key)
                        }
                        #write-host $key $index $Control.name
                    }
                }
            }
        }
    }
    UpdateConfTab $Conf

    if ($trace -eq $true) { write-host("SaveConfFromGUI() done") }
}                                      # Mise à jour de $conf[$ConfigSection][] en fonction du contenu du GUI
function UpdateGUI_NewSectionSelected {
    if ($trace -eq $true) { write-host("UpdateGUI_NewSectionSelected() start - Mise à jour du texte de la combo box en fonction de `$ConfigSection(=$ConfigSection)") }
    foreach ($Control in $form.Controls) {
        if ($control.name.split("_").length -gt 1) {
            $Index=$control.name.split("_")[$control.name.split("_").length -1]
            $Key=$control.name.split("_")[0]
            #if ($trace -eq $true) { write-host ("UpdateGUI_NewSectionSelected() Index ="+[string]$Index+" Key="+$Key) }
            if (($Key.toupper()) -eq "GROUP") {
                foreach ($Control in $Control.controls) {
                    if ($control.name.split("_").length -gt 1) {
                        $Index=$control.name.split("_")[$control.name.split("_").length -1]
                        $Key=$control.name.split("_")[0]
                        if ($Key -eq "ConfDropDownBox") {
                            if (($Control.Text) -ne ((get-variable -name $GUI_var[$index].VarName).value)) {
                                if ($trace -eq $true) { write-host ("UpdateGUI_NewSectionSelected($" +
                                         ((get-variable -name $GUI_var[$index].VarName).Name) + "=" + 
                                         ((get-variable -name $GUI_var[$index].VarName).value) +")") }
                                $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                                $Control.Items.clear()
                                foreach ($key in $conf.Keys) {
                                    if ($key -ne "_") {
                                        [void]  $Control.Items.Add($key)
                                    }
                                } #end foreach
                            }
                        }
                    }
                }
            }
        }
    }
    if ($trace -eq $true) { write-host("UpdateGUI_NewSectionSelected() done") }
}                        # Mise à jour de la combo box en fonction de $ConfigSection

function UpdateGUI_FromVars {
    if ($trace -eq $true) { write-host("UpdateGUI_FromVars() start -  Mise à jour de l'ensemble du GUI depuis les variables globales") }
    foreach ($Control in $form.Controls) {
        if ($control.name.split("_").length -gt 1) {
            $Index=$control.name.split("_")[$control.name.split("_").length -1]
            $Key=$control.name.split("_")[0]
            #write-host ("UpdateGUI_FromVars() Index ="+[string]$Index+" Key="+$Key)
            if (($Key.toupper()) -eq "GROUP") {
                foreach ($Control in $Control.controls) {
                    if ($control.name.split("_").length -gt 1) {
                        $Index=$control.name.split("_")[$control.name.split("_").length -1]
                        $Key=$control.name.split("_")[0]
                        if ($Key -eq "ConfDropDownBox") {
                            #write-host ("Found UpdateGUI_FromVars() ConfDropDownBox_"+[string]$Index)
                            #if (($Control.Text) -ne ((get-variable -name $GUI_var[$index].VarName).value)) {
                            #    $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                            #    $Control.Items.clear()
                            #    foreach ($key in $conf.Keys) {
                            #        if ($key -ne "_") {
                            #            [void]  $Control.Items.Add($key)
                            #        }
                            #    } #end foreach
                            #}
                        }
                        elseif ($key -eq "OnOffDropDownBox") {
                            #write-host ("UpdateGUI_FromVars() UpdateGUI() OnOffDropDownBox_"+[string]$Index)
                            $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                        }
                        elseif ($key -eq "SplitTabBox") { #$GUI_var[$j].SplitSelect -eq $True) { 
                            #write-host ("UpdateGUI_FromVars() SplitSelect_"+[string]$Index)
                            $control.text=UpdateGUITextFromSplitTabList
                        }
                        elseif ($key -eq "IntIntTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            #write-host ("[old] UpdateGUI_FromVars(IntIntTextBox) TextSelect_"+[string]$Index+" = "+$Control.text)
                            $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                            #write-host ("[new] UpdateGUI_FromVars(IntIntTextBox) TextSelect_"+[string]$Index+" = "+$Control.text)
                        }
                        elseif ($key -eq "IntFloatTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            #write-host ("[old] UpdateGUI_FromVarsIntFloatTextBox() TextSelect_"+[string]$Index+" = "+$Control.text)
                            $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                            #write-host ("[new] UpdateGUI_FromVarsIntFloatTextBox() TextSelect_"+[string]$Index+" = "+$Control.text)
                        }
                        elseif ($key -eq "IntTextBox") { #$GUI_var[$j].TextSelect -eq $True) { 
                            #write-host ("UpdateGUI_FromVars(IntTextBox) TextSelect_"+[string]$Index+" = "+$Control.text)
                            $Control.Text = ((get-variable -name $GUI_var[$index].VarName).value)
                        }
                        elseif ($key -eq "Desc-IntTextBox") {
                            # Description - pas d'update
                        }
                        else {
                            #write-host("UpdateGUI_FromVars() unknown key="+[string]$key)
                        }
                        #write-host $key $index $Control.name
                    }
                }
            }
        }
    }
    if ($trace -eq $true) { write-host("UpdateGUI_FromVars() done") }
}                                  # Mise à jour de l'ensemble du GUI depuis les variables globales
############################################## end GUI functions

[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Drawing") 
[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms")  
# https://sysadminemporium.wordpress.com/2012/12/07/powershell-gui-for-your-scripts-episode-3/


if ($trace -eq $true) { write-host($conf.keys) }

$Form = New-Object System.Windows.Forms.Form    
$Form.Size = New-Object System.Drawing.Size(($ColPos[0] + $LineWidth[0]+$LineWidth[1] + 28*3),(18*$LineHeigth)) # 10*3*2 + 18*3*2 +
$Form.AutoScroll=$true
$Form.Text="SplitVDT.ps1" 

$Form.Add_Shown({$Form.Activate()})

$outputBox=InitGUI
############################################## Start buttons
$Button = New-Object System.Windows.Forms.Button 
$Button.Location = New-Object System.Drawing.Size(10,(1.5*$LineHeigth+$LineOffset-$LineHeigth/2+5)) 
$Button.Size = New-Object System.Drawing.Size(($ColPos[0]-20),50) 
$Button.Text = "Démarrer" 
$Button.Add_Click({StartButton}) 
$Form.Controls.Add($Button) 
############################################## end buttons

$z=$Form.ShowDialog()
