"""
ClubMessenger — Core (logique métier partagée)
Pas d'UI ici. Toute la logique commune entre la version Android (main.py)
et la version Desktop (main_desktop.py) est centralisée dans ce module.

Contenu :
- Constantes FFESSM (commissions, brevets, simplifications)
- Helpers (norm_date, parse_brevets, calcul_statut_caci, calcul_age, etc.)
- Accès base SQLite (init_db, get_param, load_plongeurs, upsert…)
- Parseur XLSX natif + import FFESSM
- Filtres + évaluation booléenne (OU/ET/NON/parens)
- Envoi email SMTP

Aucun appel à ft.run() ici — ce module est importable sans déclencher
l'ouverture d'une fenêtre Flet.
"""


import flet as ft
import sqlite3
import os
import json
import re
import smtplib
import threading
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import csv
import zipfile
import urllib.parse
import xml.etree.ElementTree as ET

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
VERSION = "1.3.3"
APP_TITLE = "ClubMessenger"
DB_NAME = "club_messenger.db"

NIVEAUX_ORDRE = [
    "Débutant", "Baptême",
    "PE12", "Plongeur Bronze", "Plongeur Argent", "Plongeur Or",
    "PA12", "N1", "Niveau 1",
    "PE40", "N2", "Niveau 2",
    "PA40", "N3", "Niveau 3",
    "PE60",
    "GP",
    "E1", "E2", "E3", "E4",
]

SIMPLIFICATIONS_BREVETS = {
    "Niveau 3": "N3",
    "Plongeur encadré 60 mètres": "PE60",
    "Plongeur autonome 40 mètres": "PA40",
    "Niveau 2": "N2",
    "Plongeur encadré 40 mètres": "PE40",
    "Plongeur autonome 20 mètres": "PA20",
    "Niveau 1": "N1",
    "Plongeur autonome 12 mètres": "PA12",
    "Plongeur encadré 12 mètres": "PE12",
    "Plongeur Or": "Or",
    "Plongeur Argent": "Argent",
    "Plongeur Bronze": "Bronze",
}

SIMPLIFICATIONS_NITROX = {
    "Moniteur Nitrox Confirmé": "MNx",
    "Plongeur Nitrox confirmé": "PNC",
    "Plongeur Nitrox": "PN",
}

SIMPLIFICATIONS_TOUS_BREVETS = {
    "Plongeur Niveau 5": "N5",
    "Niveau IV-GP": "N4/GP",
    "Niveau IV-GP ANMP/Directeur de bassin": "N4/GP",
    "Niveau 3": "N3",
    "Plongeur encadré 60 mètres": "PE60",
    "Plongeur autonome 40 mètres": "PA40",
    "Niveau 2": "N2",
    "Plongeur encadré 40 mètres": "PE40",
    "Plongeur autonome 20 mètres": "PA20",
    "Niveau 1": "N1",
    "Niveau 1 passerelle PADI": "N1",
    "Niveau 1 passerelle SSI": "N1",
    "Plongeur autonome 12 mètres": "PA12",
    "Plongeur encadré 12 mètres": "PE12",
    "Plongeur Or": "Or",
    "Plongeur Argent": "Argent",
    "Plongeur Bronze": "Bronze",
    "E1 - Initiateur-Directeur de bassin": "E1",
    "E2 - Niveau IV/GP/Directeur de bassin": "E2",
    "E3 - M.F.1.": "E3",
    "E3 - B.E.E.S. 1er degré": "E3",
    "E4 - M.F.2.": "E4",
    "DE - JEPS / E4": "E4",
    "E4 - B.E.E.S. 2ème degré": "E4",
    "Tuteur de stage initiateur": "TSI",
    "Moniteur Nitrox Confirmé": "MNx",
    "Plongeur Nitrox confirmé": "PNC",
    "Plongeur Nitrox": "PN",
    "Plongeur Trimix élémentaire": "PT70",
    "E3 - Moniteur Trimix": "E3-MTX",
    "Technicien Inspection Visuelle": "TIV",
    "Technicien Inspection Visuelle - Recyclage": "TIV",
    "Technicien Inspection Visuelle - Réactivation": "TIV",
    "Formateur de T.I.V.": "F-TIV",
    "Combinaison étanche": "CE",
    "Side Mount": "SM",
    "Plongeur Biologiste Niveau 1": "PB1",
    "Plongeur Biologiste Niveau 2": "PB2",
    "Formateur Biologie 1er degré": "FB1",
    "Formateur Biologie 1er degré – Aptitude Formateur PB2": "FB1+",
    "Formateur Biologie 2e degré": "FB2",
    "Formateur Biologie 3e degré": "FB3",
    "Plongeur souterrain Niveau 1": "PS1",
    "Plongeur souterrain Niveau 2": "PS2",
    "Plongeur souterrain Niveau 3": "PS3",
    "Formateur de plongée souterraine Niveau1": "FPS1",
    "FORMATEUR DE PLONGEE SOUTERRAINE N3": "FPS3",
    "Nageur en eau vive Niveau 1": "NEV1",
    "Nageur en eau vive Niveau 2": "NEV2",
    "Nageur en eau vive Niveau 3": "NEV3",
    "Initiateur entraîneur en eau vive": "IE1NEV",
    "Moniteur entraîneur Fédéral Nage en eau vive 1er degré": "MEF1NEV",
    "Juge Fédéral Nage 1er degré Slalom": "JFN1S",
    "Apnéiste Niveau 1": "A1",
    "Apnéiste Niveau 2": "A2", 
    "Apnéiste / Indoor Freediver 1 CMAS": "A-IF1",
    "Apnéiste confirmé / Indoor Freediver 2 CMAS": "AC-IF2",
    "Apnéiste confirmé en eau Libre / Outdoor Freediver 2 CMAS": "AC-OF2",
    "Apnéiste expert en eau Libre / Outdoor Freediver 3 CMAS": "AE-OF3",
    "Initiateur-Entraîneur Apnée Niveau 1": "IE1",
    "Initiateur-Entraîneur Apnée Niveau 2": "IE2",
    "Initiateur-Entraîneur Apnée N2 / 1* Star Freediving Instructor": "IE2",
    "Moniteur entraîneur Fédéral Apnée 1er degré": "MEF1",
    "Moniteur entraîneur Fédéral Apnée 2e degré": "MEF2",
    "Pêcheur Sous-Marin - Niveau 1": "PSM1",
    "Pêcheur Sous-Marin - Niveau 2": "PSM2",
    "Pêcheur Sous-Marin - Niveau 3": "PSM3",
    "Initiateur entraîneur Pêche Sous-Marine": "IEPSM",
    "Moniteur entraîneur Fédéral Pêche Sous-Marine - 1er degré": "MEF1PSM",
    "Antéor": "ANTEOR",
    "RIFA Plongée": "RIFAP",
    "RIFA Apnée": "RIFAA",
    "RIFA Nage en eau vive": "RIFANEV",
    "RIFA Nage avec palmes": "RIFAPNAP",
    "RIFA Tir sur cible": "RIFAT",
    "RIFA Pêche Sous-Marine": "RIFAPSM",
    "RIFA Hockey Subaquatique": "RIFAHS",
    "Initiateur entraîneur Nage avec palmes": "IE1NAP",
    "P.E.S.H.1 - 6 mètres": "PESH1",
    "P.E.S.H.2 12 mètres": "PESH2",
    "P.E.S.H.3 - 20 mètres": "PESH3",
    "P.E.S.H.4 - 40 mètres": "PESH4",
    "P.E.S.H.A - Horizontal 1": "PESHA H1",
    "P.E.S.H.A - Horizontal 2": "PESHA H2",
    "P.E.S.H.A - Horizontal 3": "PESHA H3",
    "P.E.S.H.A - STATIQUE 1": "PESHA S1",
    "P.E.S.H.A - STATIQUE 2": "PESHA S2",
    "P.E.S.H.A - Vertical 1": "PESHA V1",
    "P.E.S.H.A - Vertical 2": "PESHA V2",
    "P.E.S.H.T.S.C 1 - Initiation":         "PESH-TSC1",
    "P.E.S.H.T.S.C 2 - Perfectionnement":   "PESH-TSC2",
    "P.E.S.H.T.S.C 3 - Confirmé":           "PESH-TSC3",
    "EH1 - Scaphandre": "EH1-S",
    "EH2 - Scaphandre": "EH2-S",
    "EH1 - Apnée": "EH1-A",
    "EH2 - Apnée": "EH2-A",
    "EH1 - Tir sur cible": "EH1-TSC",
    "EH2 - Tir sur cible": "EH2-TSC",
    "MHPC - Module complémentaire Handi-Psychique Cognitif": "MHPC",
    "Moniteur Fédéral E.H.1 Scaphandre": "MEFEH1",
    "Moniteur Fédéral E.H.2 Scaphandre": "MEFEH2",
    "MEFEH - Tir sur cible": "MEFEH - Tir sur cible",
    "Tireur - Niveau 1": "TN1",
    "Tireur - Niveau 2": "TN2",
    "Initiateur entraîneur Tir sur Cible": "IE1TSC",
    "Juge Fédéral Tir sur Cible - 1er degré": "JF1-TSC",
    "Moniteur entraîneur Fédéral Tir sur Cible 1er degré": "MEF1TSC",
    "Arbitre Plongée Sportive Piscine":  "APSP",
    "Plongeur Recycleur Circuit Fermé AP-Diving Inspiration Trimix Avancé": "PRCFTA APD",
    "Moniteur Recycleur Circuit Fermé Diluant Air AP-Diving Inspiration": "MRCFA APD",
    "Moniteur Recycleur Circuit Fermé Trimix Léger  AP-Diving Inspiration": "MRCFTL APD",
    "Plongeur photographe Niveau 1": "PP1",
    "Plongeur vidéaste Niveau 1": "PV1",
    "Pass animateur Photo-Vidéo": "PA PV",  
    "Pass animateur Archéo": "PA Archéo",     
    "Pass animateur Nage en eau vive": "PA NEV",
    "Initiateur entraîneur Hockey Subaquatique": "IE1 HS",
    "Arbitre Hockey Subaquatique 1er degré": "Arb. HS",
    "Dauphin - Apnée jeunes N3": "Dauphin",
    "Poulpe - Apnée jeunes N2": "Poulpe",
    "Crevette - Apnée jeunes N1": "Crevette",
    "Cursus jeune": "Jeune PB",
    "AFH PSP - Assistant formateur": "AFH PSP",
    "AFH Scaphandre - Assistant formateur": "AFH S",
    "AFH TSC - Assistant formateur": "AFH TSC",
    "AH - Aidant accompagnant": "AH",
    "APH PSP - Accompagnant pratiquant": "APH PSP",
    "APH Scaphandre - Accompagnant pratiquant": "APH S",
    "APH TSC - Accompagnant pratiquant": "APH TSC",
}


BREVETS_PLONGEUR_ORDRE = [
    "Niveau 3",
    "Plongeur encadré 60 mètres",
    "Plongeur autonome 40 mètres",
    "Niveau 2",
    "Plongeur encadré 40 mètres",
    "Plongeur autonome 20 mètres",
    "Niveau 1",
    "Niveau 1 passerelle SSI",
    "Niveau 1 passerelle PADI",
    "Plongeur autonome 12 mètres",
    "Plongeur encadré 12 mètres",
    "Plongeur Or",
    "Plongeur Argent",
    "Plongeur Bronze",
]

BREVETS_TECHNIQUES = [
    "Plongeur Niveau 5",
    "Niveau IV-GP",
    "Niveau IV-GP ANMP/Directeur de bassin",
    "Niveau 3",
    "Plongeur encadré 60 mètres",
    "Plongeur autonome 40 mètres",
    "Niveau 2",
    "Plongeur encadré 40 mètres",
    "Plongeur autonome 20 mètres",
    "Niveau 1",
    "Niveau 1 passerelle PADI",
    "Niveau 1 passerelle SSI",
    "Plongeur autonome 12 mètres",
    "Plongeur encadré 12 mètres",
    "Plongeur Or",
    "Plongeur Argent",
    "Plongeur Bronze",
    "E1 - Initiateur-Directeur de bassin",
    "E2 - Niveau IV/GP/Directeur de bassin",
    "E3 - M.F.1.",
    "E3 - B.E.E.S. 1er degré",
    "E4 - M.F.2.",
    "DE - JEPS / E4",
    "E4 - B.E.E.S. 2ème degré",
    "Tuteur de stage initiateur",
    "Moniteur Nitrox Confirmé", 
    "E3 - Moniteur Trimix",
    "Plongeur Nitrox confirmé",
    "Plongeur Nitrox",
    "Plongeur Trimix élémentaire",
    "Technicien Inspection Visuelle",
    "Technicien Inspection Visuelle - Recyclage",
    "Technicien Inspection Visuelle - Réactivation",
    "Formateur de T.I.V.",
    "Combinaison étanche",
    "Side Mount",
    "Plongeur Recycleur Circuit Fermé AP-Diving Inspiration Trimix Avancé",
    "Moniteur Recycleur Circuit Fermé Diluant Air AP-Diving Inspiration",
    "Moniteur Recycleur Circuit Fermé Trimix Léger  AP-Diving Inspiration",
]


BREVETS_SECOURS = [
    "Antéor",
    "RIFA Plongée",
    "RIFA Apnée",
    "RIFA Nage en eau vive",
    "RIFA Nage avec palmes",
    "RIFA Pêche Sous-Marine",
    "RIFA Tir sur cible",
    "RIFA Hockey Subaquatique",
]


BREVETS_NEV = [
    "Nageur en eau vive Niveau 1",
    "Nageur en eau vive Niveau 2",
    "Nageur en eau vive Niveau 3",
    "Initiateur entraîneur en eau vive",
    "Moniteur entraîneur Fédéral Nage en eau vive 1er degré",
    "Juge Fédéral Nage 1er degré Slalom",
    "Pass animateur Nage en eau vive",
]

BREVETS_BIO = [
    "Plongeur Biologiste Niveau 1",
    "Plongeur Biologiste Niveau 2",
    "Formateur Biologie 1er degré",
    "Formateur Biologie 1er degré – Aptitude Formateur PB2",
    "Formateur Biologie 2e degré",
    "Formateur Biologie 3e degré",
    "Cursus jeune",
]

BREVETS_PS = [
    "Plongeur souterrain Niveau 1",
    "Plongeur souterrain Niveau 2",
    "Plongeur souterrain Niveau 3",
    "Formateur de plongée souterraine Niveau1",
    "FORMATEUR DE PLONGEE SOUTERRAINE N3",
]

BREVETS_APNEE = [
    "Apnéiste Niveau 1",
    "Apnéiste Niveau 2",
    "Apnéiste / Indoor Freediver 1 CMAS",
    "Apnéiste confirmé / Indoor Freediver 2 CMAS",
    "Apnéiste confirmé en eau Libre / Outdoor Freediver 2 CMAS",
    "Apnéiste expert en eau Libre / Outdoor Freediver 3 CMAS",
    "Initiateur-Entraîneur Apnée Niveau 1",
    "Initiateur-Entraîneur Apnée Niveau 2",
    "Initiateur-Entraîneur Apnée N2 / 1* Star Freediving Instructor",
    "Moniteur entraîneur Fédéral Apnée 1er degré",
    "Moniteur entraîneur Fédéral Apnée 2e degré",
    "Dauphin - Apnée jeunes N3",
    "Poulpe - Apnée jeunes N2",
    "Crevette - Apnée jeunes N1",
]

BREVETS_PSP = [
    "Arbitre Plongée Sportive Piscine",      
]

BREVETS_TSC = [
    "Tireur - Niveau 1",
    "Tireur - Niveau 2",
    "Initiateur entraîneur Tir sur Cible",
    "Juge Fédéral Tir sur Cible - 1er degré",
    "Moniteur entraîneur Fédéral Tir sur Cible 1er degré",
]

BREVETS_PV = [
    "Plongeur photographe Niveau 1",
    "Plongeur vidéaste Niveau 1",
    "Pass animateur Photo-Vidéo",     
]

BREVETS_AS = [
    "Pass animateur Archéo",       
]

BREVETS_HS = [
    "Initiateur entraîneur Hockey Subaquatique",
    "Arbitre Hockey Subaquatique 1er degré",
]

BREVETS_PSM = [
    "Pêcheur Sous-Marin - Niveau 1",
    "Pêcheur Sous-Marin - Niveau 2",
    "Pêcheur Sous-Marin - Niveau 3",
    "Initiateur entraîneur Pêche Sous-Marine",
    "Moniteur entraîneur Fédéral Pêche Sous-Marine - 1er degré",
]

BREVETS_NAP = [
    "Initiateur entraîneur Nage avec palmes",
]

BREVETS_HANDI = [
    "P.E.S.H.1 - 6 mètres",
    "P.E.S.H.2 12 mètres",
    "P.E.S.H.3 - 20 mètres",
    "P.E.S.H.4 - 40 mètres",
    "P.E.S.H.A - Horizontal 1",
    "P.E.S.H.A - Horizontal 2",
    "P.E.S.H.A - Horizontal 3",
    "P.E.S.H.A - STATIQUE 1",
    "P.E.S.H.A - STATIQUE 2",
    "P.E.S.H.A - Vertical 1",
    "P.E.S.H.A - Vertical 2",
    "P.E.S.H.T.S.C 1 - Initiation",
    "P.E.S.H.T.S.C 2 - Perfectionnement",
    "P.E.S.H.T.S.C 3 - Confirmé",
    "EH1 - Scaphandre",
    "EH2 - Scaphandre",
    "EH1 - Apnée",
    "EH2 - Apnée",
    "EH1 - Tir sur cible",
    "EH2 - Tir sur cible",
    "MHPC - Module complémentaire Handi-Psychique Cognitif",
    "Moniteur Fédéral E.H.1 Scaphandre",
    "Moniteur Fédéral E.H.2 Scaphandre",
    "MEFEH - Tir sur cible",
    "AFH PSP - Assistant formateur",
    "AFH Scaphandre - Assistant formateur",
    "AFH TSC - Assistant formateur",
    "AH - Aidant accompagnant",
    "APH PSP - Accompagnant pratiquant",
    "APH Scaphandre - Accompagnant pratiquant",
    "APH TSC - Accompagnant pratiquant",
]

BREVETS_JEUNES = [
    "Plongeur Or",
    "Plongeur Argent",
    "Plongeur Bronze",
    "Dauphin - Apnée jeunes N3",
    "Poulpe - Apnée jeunes N2",
    "Crevette - Apnée jeunes N1",
    "Cursus jeune",
]

BREVETS_CADRES = [
    "E1 - Initiateur-Directeur de bassin",
    "E2 - Niveau IV/GP/Directeur de bassin",
    "E3 - M.F.1.",
    "E4 - M.F.2.",
    "DE - JEPS / E4",
    "Tuteur de stage initiateur",
    "Moniteur Nitrox Confirmé", 
    "E3 - Moniteur Trimix",
    "Formateur Biologie 1er degré - Aptitude Formateur PB2",
    "Formateur Biologie 2e degré",
    "Formateur Biologie 3e degré",
    "Initiateur entraîneur en eau vive",
    "Moniteur entraîneur Fédéral Nage en eau vive 1er degré",
    "Juge Fédéral Nage 1er degré Slalom",
    "FORMATEUR DE PLONGEE SOUTERRAINE N3",
    "Initiateur-Entraîneur Apnée Niveau 1",
    "Initiateur-Entraîneur Apnée Niveau 2",
    "Initiateur-Entraîneur Apnée N2 / 1* Star Freediving Instructor",
    "Moniteur entraîneur Fédéral Apnée 1er degré",
    "Moniteur entraîneur Fédéral Apnée 2e degré",
    "Initiateur entraîneur Pêche Sous-Marine",
    "Moniteur entraîneur Fédéral Pêche Sous-Marine - 1er degré",
    "Initiateur entraîneur Nage avec palmes",
    "EH1 - Scaphandre",
    "EH1 - Apnée",
]


STATUT_CACI_VALIDE  = "VALIDE"
STATUT_CACI_ALERTE  = "ALERTE"
STATUT_CACI_PERIME  = "PÉRIMÉ"
STATUT_CACI_ABSENT  = "ABSENT"

# ──────────────────────────────────────────────────────────────────────────────
# Commissions FFESSM — chaque commission a sa liste explicite de brevets.
# La détection se fait par appartenance exacte (pas de mots-clés), donc pas de
# faux positifs possibles. Une liste vide signifie que la commission n'a pas
# encore été renseignée — elle sera ignorée à l'affichage.
# ──────────────────────────────────────────────────────────────────────────────
COMMISSIONS_FFESSM = [
    ("Apnée",                       BREVETS_APNEE),
    ("Archéologie Subaquatique",    BREVETS_AS),
    ("Biologie et Environnement",   BREVETS_BIO),
    ("Photo Vidéo",                 BREVETS_PV),
    ("Hockey Subaquatique",         BREVETS_HS),
    ("Nage avec Palmes",            BREVETS_NAP),
    ("Nage En Eau Vive",            BREVETS_NEV),
    ("Plongée technique",           BREVETS_TECHNIQUES),
    ("Pêche sous-Marine",           BREVETS_PSM),
    ("Plongée souterraine",         BREVETS_PS),
    ("Plongée Sportive en Piscine", BREVETS_PSP),
    ("Tir sur cible subaquatique",  BREVETS_TSC),
]

# Brevets Sport Santé
BREVETS_SS = ["Module Sport Santé"]

# Filtres transversaux : Handisub, Activités Jeunes, Secourisme, Sport Santé
FILTRES_TRANSVERSAUX = [
    ("Handisub",         BREVETS_HANDI),
    ("Activités Jeunes", BREVETS_JEUNES),
    ("Secourisme",       BREVETS_SECOURS),
    ("Sport Santé",      BREVETS_SS),
]

# Sections affichées dans l'UI : (titre_section, liste_des_filtres)
SECTIONS_FILTRES = [
    ("Commissions FFESSM",     COMMISSIONS_FFESSM),
    ("Activités transversales", FILTRES_TRANSVERSAUX),
]


def _tous_filtres():
    """Liste fusionnée (nom, brevets) de tous les filtres (commissions +
    transversaux + secourisme). Utilisé pour le lookup par nom."""
    out = []
    for _titre, filtres in SECTIONS_FILTRES:
        out.extend(filtres)
    return out

# Cache simple pour éviter de reparser 1000× les mêmes chaînes de brevets
_BREVETS_CACHE = {}

def _parse_brevets_lists(brevets_str: str):
    """Retourne (liste_brevets_complets, set_brevets_courts) avec cache."""
    key = brevets_str or ""
    if key in _BREVETS_CACHE:
        return _BREVETS_CACHE[key]

    if not key:
        res = ([], set())
        _BREVETS_CACHE[key] = res
        return res

    lst = [b.strip() for b in key.split(",") if b.strip()]
    courts = {SIMPLIFICATIONS_TOUS_BREVETS.get(b, b) for b in lst}
    res = (lst, courts)

    # cache borné simple
    if len(_BREVETS_CACHE) < 2000:
        _BREVETS_CACHE[key] = res

    return res


# Pré‑compilation des sets de référence pour les commissions / filtres
_COMMISSIONS_FFESSM_SETS = {
    nom: set(lst) for nom, lst in _tous_filtres()
}


def brevets_d_une_commission(brevets_brut: str, commission_nom: str) -> list:
    """
    Retourne les brevets (noms complets) d'un plongeur appartenant à
    une commission/transversal/secourisme donnée, en utilisant :
    - sets pré‑compilés pour la commission
    - parsing unique + cache pour la chaîne de brevets.
    """
    liste_ref_set = _COMMISSIONS_FFESSM_SETS.get(commission_nom)
    if not liste_ref_set or not brevets_brut:
        return []

    brevets_list, _ = _parse_brevets_lists(brevets_brut)
    return [b for b in brevets_list if b in liste_ref_set]


def brevet_court(nom_long: str) -> str:
    """Retourne la version abrégée d'un brevet (ex. 'Niveau 2' → 'N2').
    Si pas de mapping connu, retourne le nom long inchangé."""
    return SIMPLIFICATIONS_TOUS_BREVETS.get(nom_long, nom_long)


def parse_brevets(brevets_brut: str) -> list:
    """Transforme la chaîne 'Brevets' FFESSM en liste de tuples
    (nom_complet, nom_court). Espaces de début/fin supprimés, doublons retirés.
    Conserve l'ordre d'apparition. Le nom_court vient de SIMPLIFICATIONS_TOUS_BREVETS
    ou retombe sur le nom complet si pas de mapping.
    """
    if not brevets_brut:
        return []
    seen = set()
    result = []
    for b in brevets_brut.split(","):
        b = b.strip()
        if not b or b in seen:
            continue
        seen.add(b)
        result.append((b, brevet_court(b)))
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Helpers FFESSM (identiques SecuManager)
# ──────────────────────────────────────────────────────────────────────────────

def norm_date(v):
    """Normalise une valeur date quelconque en 'jj/mm/aaaa' ou ''.
    Gère :
    - objets datetime/date
    - chaînes texte (formats variés)
    - numéros de série Excel (ex. 46258 = 14/08/2026)
    """
    if v is None:
        return ""
    # datetime/date natif
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%d/%m/%Y")
        except Exception:
            pass
    s = str(v).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return ""
    # Numéro de série Excel (entier ou float pur)
    try:
        f = float(s)
        # plage raisonnable : 1900-01-01 (1) à 2100-01-01 (~73050)
        if 1 < f < 100000 and "." not in s and "/" not in s and "-" not in s:
            n = int(f)
            offset = n if n < 60 else n - 1
            dt = datetime(1899, 12, 30) + timedelta(days=offset)
            return dt.strftime("%d/%m/%Y")
        # float avec partie décimale (timestamp avec heure)
        if 1 < f < 100000 and "." in s:
            n = int(f)
            offset = n if n < 60 else n - 1
            dt = datetime(1899, 12, 30) + timedelta(days=offset)
            return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        pass
    # Format texte
    s_short = s.split(" ")[0]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s_short, fmt).strftime("%d/%m/%Y")
        except Exception:
            pass
    return s

def extract_brevets(brevets_str):
    """
    Retourne (moniteur, encadrant, plongeur, nitrox) — codes courts —
    à partir de la liste brute FFESSM, en utilisant un parsing
    unique + cache.
    """
    brevets_list, brevets_courts = _parse_brevets_lists(brevets_str)

    # Moniteur : E1..E4
    brev_m = ""
    for grad in ("E4", "E3", "E2", "E1"):
        if grad in brevets_courts:
            brev_m = grad
            break

    # Encadrant : GP / N4/GP
    brev_e = "GP" if ("GP" in brevets_courts or "N4/GP" in brevets_courts) else ""

    # Plongeur : ordre de priorité
    brev_p = "Débutant"
    for candidat in BREVETS_PLONGEUR_ORDRE:
        if candidat in brevets_list:
            brev_p = SIMPLIFICATIONS_BREVETS.get(candidat, candidat)
            break

    # Nitrox : MNx / PNC / PN
    brev_nx = ""
    for sigle in ("MNx", "PNC", "PN"):
        if sigle in brevets_courts:
            brev_nx = sigle
            break

    return brev_m, brev_e, brev_p, brev_nx


def calcul_statut_caci(date_fin_str, date_ref=None):
    """
    Retourne (statut, couleur) pour un CACI.
    date_ref = date de référence (défaut = aujourd'hui).
    VALIDE  : date_fin >= date_ref + 1 mois de marge
    ALERTE  : date_fin >= date_ref mais dans moins d'1 mois
    PÉRIMÉ  : date_fin < date_ref
    ABSENT  : date_fin vide
    """
    if not date_fin_str:
        return STATUT_CACI_ABSENT, ft.Colors.GREY
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            df = datetime.strptime(date_fin_str.strip(), fmt).date()
            ref = date_ref or date.today()
            delta = (df - ref).days
            if delta < 0:
                return STATUT_CACI_PERIME, ft.Colors.RED
            elif delta <= 30:
                return STATUT_CACI_ALERTE, ft.Colors.ORANGE
            else:
                return STATUT_CACI_VALIDE, ft.Colors.GREEN
        except Exception:
            pass
    return STATUT_CACI_ABSENT, ft.Colors.GREY


def calcul_age(date_naissance_str):
    """Retourne l'âge en années entières, ou None si date invalide."""
    if not date_naissance_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dn = datetime.strptime(date_naissance_str.strip(), fmt).date()
            today = date.today()
            age = today.year - dn.year - (
                (today.month, today.day) < (dn.month, dn.day)
            )
            return age
        except Exception:
            pass
    return None


def niveau_affiche(niveau, brev_nx=""):
    """Retourne la chaîne d'affichage 'niveau' ou 'niveau - nitrox'."""
    if brev_nx:
        return f"{niveau} - {brev_nx}"
    return niveau


# ──────────────────────────────────────────────────────────────────────────────
# Base de données
# ──────────────────────────────────────────────────────────────────────────────

def get_db_path():
    """Retourne le chemin de la DB SQLite, multi-plateforme.

    - Android (Flet) : utilise FLET_APP_STORAGE_DATA, dossier privé de l'app.
    - Desktop / autres : ~/.clubmessenger/ ou fallback tempfile.
    """
    # 1. Variable d'environnement Flet (définie sur Android/iOS)
    base = os.environ.get("FLET_APP_STORAGE_DATA")
    if base and os.path.isdir(base):
        # Sur mobile, on écrit directement dans ce dossier privé
        try:
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, DB_NAME)
        except Exception:
            pass

    # 2. Desktop : ~/.clubmessenger/
    candidates = []
    try:
        home = os.path.expanduser("~")
        if home and home != "~" and os.path.isdir(home):
            candidates.append(os.path.join(home, ".clubmessenger"))
    except Exception:
        pass

    # 3. Fallback : dossier temporaire (toujours accessible en écriture)
    import tempfile
    candidates.append(os.path.join(tempfile.gettempdir(), "clubmessenger"))

    for data_dir in candidates:
        try:
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, DB_NAME)
        except Exception:
            continue

    # Dernier recours : juste le nom de fichier (dossier courant)
    return DB_NAME


def get_conn():
    return sqlite3.connect(get_db_path())


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Plongeurs du club
    c.execute("""
        CREATE TABLE IF NOT EXISTS plongeurs_club (
            id_licence      TEXT PRIMARY KEY,
            nom             TEXT NOT NULL,
            prenom          TEXT NOT NULL,
            date_naissance  TEXT DEFAULT '',
            niveau          TEXT DEFAULT '',
            niveau_prepa    TEXT DEFAULT '',
            brev_moniteur   TEXT DEFAULT '',
            brev_encadrant  TEXT DEFAULT '',
            brev_plongeur   TEXT DEFAULT '',
            brev_nitrox     TEXT DEFAULT '',
            brevets_brut    TEXT DEFAULT '',
            portable        TEXT DEFAULT '',
            email           TEXT DEFAULT '',
            saison          TEXT DEFAULT '',
            type_licence    TEXT DEFAULT '',
            categorie       TEXT DEFAULT '',
            date_caci       TEXT DEFAULT '',
            date_fin_caci   TEXT DEFAULT '',
            nom_club        TEXT DEFAULT ''
        )
    """)
    # Migration douce : ajouter colonnes si DB existante
    for col in ("brevets_brut", "nom_club", "categorie"):
        try:
            c.execute(f"ALTER TABLE plongeurs_club ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

    # Paramètres club
    c.execute("""
        CREATE TABLE IF NOT EXISTS parametres_club (
            cle     TEXT PRIMARY KEY,
            valeur  TEXT DEFAULT ''
        )
    """)

    # Paramètres par défaut
    defaults = [
        ("nom_club_court", "CSSA"),
        ("nom_club_long",  "Club Sportif de Plongée"),
        ("email_expediteur", ""),
        ("smtp_host",      "smtp.gmail.com"),
        ("smtp_port",      "587"),
        ("smtp_user",      ""),
        ("smtp_password",  ""),
        ("smtp_tls",       "1"),
        ("sms_api_key",    ""),
        ("sms_expediteur", ""),
    ]
    for cle, val in defaults:
        c.execute(
            "INSERT OR IGNORE INTO parametres_club (cle, valeur) VALUES (?, ?)",
            (cle, val)
        )

    # Historique messages
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages_envoyes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date_envoi          TEXT,
            canal               TEXT,
            sujet               TEXT,
            corps               TEXT,
            filtre_json         TEXT,
            destinataires_json  TEXT,
            nb_envoyes          INTEGER DEFAULT 0,
            nb_erreurs          INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def get_param(cle):
    conn = get_conn()
    r = conn.execute(
        "SELECT valeur FROM parametres_club WHERE cle=?", (cle,)
    ).fetchone()
    conn.close()
    return r[0] if r else ""


def set_param(cle, valeur):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO parametres_club (cle, valeur) VALUES (?, ?)",
        (cle, valeur)
    )
    conn.commit()
    conn.close()


def load_plongeurs():
    """Charge tous les plongeurs depuis la DB."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT id_licence, nom, prenom, date_naissance,
               niveau, niveau_prepa, brev_moniteur, brev_encadrant,
               brev_plongeur, brev_nitrox, brevets_brut, portable, email,
               saison, type_licence, categorie, date_caci, date_fin_caci, nom_club
        FROM plongeurs_club
        ORDER BY nom, prenom
    """).fetchall()
    conn.close()
    keys = [
        "id_licence", "nom", "prenom", "date_naissance",
        "niveau", "niveau_prepa", "brev_moniteur", "brev_encadrant",
        "brev_plongeur", "brev_nitrox", "brevets_brut", "portable", "email",
        "saison", "type_licence", "categorie", "date_caci", "date_fin_caci", "nom_club"
    ]
    return [dict(zip(keys, r)) for r in rows]


def _upsert_plongeur_on_conn(conn, p: dict, niveau_prepa_ancien=""):
    """Insertion/MAJ via une connexion ouverte (pour le batch).
    Ne commit pas — le caller s'en occupe."""
    prepa = niveau_prepa_ancien
    if prepa and prepa == p.get("niveau", ""):
        prepa = ""

    conn.execute("""
        INSERT INTO plongeurs_club
            (id_licence, nom, prenom, date_naissance,
             niveau, niveau_prepa, brev_moniteur, brev_encadrant,
             brev_plongeur, brev_nitrox, brevets_brut, portable, email,
             saison, type_licence, categorie, date_caci, date_fin_caci, nom_club)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id_licence) DO UPDATE SET
            nom            = excluded.nom,
            prenom         = excluded.prenom,
            date_naissance = excluded.date_naissance,
            niveau         = excluded.niveau,
            niveau_prepa   = CASE
                WHEN excluded.niveau != '' AND excluded.niveau = plongeurs_club.niveau_prepa
                THEN ''
                ELSE plongeurs_club.niveau_prepa
            END,
            brev_moniteur  = excluded.brev_moniteur,
            brev_encadrant = excluded.brev_encadrant,
            brev_plongeur  = excluded.brev_plongeur,
            brev_nitrox    = excluded.brev_nitrox,
            brevets_brut   = excluded.brevets_brut,
            portable       = excluded.portable,
            email          = excluded.email,
            saison         = excluded.saison,
            type_licence   = excluded.type_licence,
            categorie      = excluded.categorie,
            date_caci      = excluded.date_caci,
            date_fin_caci  = excluded.date_fin_caci,
            nom_club       = excluded.nom_club
    """, (
        p.get("id_licence", ""),
        p.get("nom", ""),
        p.get("prenom", ""),
        p.get("date_naissance", ""),
        p.get("niveau", ""),
        prepa,
        p.get("brev_moniteur", ""),
        p.get("brev_encadrant", ""),
        p.get("brev_plongeur", ""),
        p.get("brev_nitrox", ""),
        p.get("brevets_brut", ""),
        p.get("portable", ""),
        p.get("email", ""),
        p.get("saison", ""),
        p.get("type_licence", ""),
        p.get("categorie", ""),
        p.get("date_caci", ""),
        p.get("date_fin_caci", ""),
        p.get("nom_club", ""),
    ))


def upsert_plongeur(p: dict, niveau_prepa_ancien=""):
    """Upsert d'un seul plongeur (ouvre/ferme la connexion).
    Pour import en masse, préférer upsert_plongeurs_batch."""
    conn = get_conn()
    _upsert_plongeur_on_conn(conn, p, niveau_prepa_ancien)
    conn.commit()
    conn.close()


# SQL constant — sorti de la fonction pour éviter la re-compilation à chaque appel
_UPSERT_PLONGEUR_SQL = """
INSERT INTO plongeurs_club
    (id_licence, nom, prenom, date_naissance,
     niveau, niveau_prepa, brev_moniteur, brev_encadrant,
     brev_plongeur, brev_nitrox, brevets_brut, portable, email,
     saison, type_licence, categorie, date_caci, date_fin_caci, nom_club)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(id_licence) DO UPDATE SET
    nom            = excluded.nom,
    prenom         = excluded.prenom,
    date_naissance = excluded.date_naissance,
    niveau         = excluded.niveau,
    niveau_prepa   = CASE
        WHEN excluded.niveau != '' AND excluded.niveau = plongeurs_club.niveau_prepa
        THEN ''
        ELSE plongeurs_club.niveau_prepa
    END,
    brev_moniteur  = excluded.brev_moniteur,
    brev_encadrant = excluded.brev_encadrant,
    brev_plongeur  = excluded.brev_plongeur,
    brev_nitrox    = excluded.brev_nitrox,
    brevets_brut   = excluded.brevets_brut,
    portable       = excluded.portable,
    email          = excluded.email,
    saison         = excluded.saison,
    type_licence   = excluded.type_licence,
    categorie      = excluded.categorie,
    date_caci      = excluded.date_caci,
    date_fin_caci  = excluded.date_fin_caci,
    nom_club       = excluded.nom_club
"""


def upsert_plongeurs_batch(plongeurs: list):
    """Import en masse optimisé pour plusieurs milliers de plongeurs.

    Optimisations :
    - executemany() : 1 seul aller-retour C pour toute la liste
    - PRAGMA tuning (journal_mode=MEMORY, synchronous=NORMAL, cache_size=32Mo)
    - Préfetch des niveau_prepa CHUNKÉ par 900 IDs (limite SQLite ~999 paramètres,
      sinon crash sur les gros imports)
    """
    if not plongeurs:
        return
    conn = get_conn()
    try:
        # ── Pragmas de performance (transitoires sur cette connexion) ──
        # journal_mode=MEMORY : pas de write-ahead log sur disque
        # synchronous=NORMAL  : moins de fsync (FULL → NORMAL ≈ 2-3× plus rapide)
        # cache_size=-32000   : 32 Mo de cache pages
        try:
            conn.execute("PRAGMA journal_mode = MEMORY")
            conn.execute("PRAGMA synchronous  = NORMAL")
            conn.execute("PRAGMA temp_store   = MEMORY")
            conn.execute("PRAGMA cache_size   = -32000")
        except Exception:
            pass  # best-effort, certains drivers/builds ignorent

        # ── Préfetch des niveau_prepa existants (chunké par 900) ──
        ids = [p.get("id_licence", "") for p in plongeurs if p.get("id_licence")]
        prepas_existants = {}
        CHUNK = 900  # < limite SQLite 999 paramètres
        for i in range(0, len(ids), CHUNK):
            sub = ids[i:i + CHUNK]
            placeholders = ",".join("?" * len(sub))
            cur = conn.execute(
                f"SELECT id_licence, niveau_prepa FROM plongeurs_club "
                f"WHERE id_licence IN ({placeholders})", sub
            )
            for id_lic, prepa in cur.fetchall():
                prepas_existants[id_lic] = prepa

        # ── Construction des tuples paramètres pour executemany ──
        params = []
        params_append = params.append
        for p in plongeurs:
            id_lic = p.get("id_licence", "")
            prepa = prepas_existants.get(id_lic, "")
            if prepa and prepa == p.get("niveau", ""):
                prepa = ""
            params_append((
                id_lic,
                p.get("nom", ""),
                p.get("prenom", ""),
                p.get("date_naissance", ""),
                p.get("niveau", ""),
                prepa,
                p.get("brev_moniteur", ""),
                p.get("brev_encadrant", ""),
                p.get("brev_plongeur", ""),
                p.get("brev_nitrox", ""),
                p.get("brevets_brut", ""),
                p.get("portable", ""),
                p.get("email", ""),
                p.get("saison", ""),
                p.get("type_licence", ""),
                p.get("categorie", ""),
                p.get("date_caci", ""),
                p.get("date_fin_caci", ""),
                p.get("nom_club", ""),
            ))

        # ── Insert en bulk dans une seule transaction ──
        conn.execute("BEGIN")
        conn.executemany(_UPSERT_PLONGEUR_SQL, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def save_message_historique(canal, sujet, corps, filtre, destinataires,
                             nb_ok, nb_err):
    conn = get_conn()
    conn.execute("""
        INSERT INTO messages_envoyes
            (date_envoi, canal, sujet, corps, filtre_json,
             destinataires_json, nb_envoyes, nb_erreurs)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        datetime.now().strftime("%d/%m/%Y %H:%M"),
        canal,
        sujet,
        corps,
        json.dumps(filtre, ensure_ascii=False),
        json.dumps(destinataires, ensure_ascii=False),
        nb_ok,
        nb_err,
    ))
    conn.commit()
    conn.close()


def load_historique(limit=100):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, date_envoi, canal, sujet, nb_envoyes, nb_erreurs,
               filtre_json, destinataires_json, corps
        FROM messages_envoyes
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def delete_historique(id_msg: int):
    """Supprime un message de l'historique."""
    conn = get_conn()
    conn.execute("DELETE FROM messages_envoyes WHERE id = ?", (id_msg,))
    conn.commit()
    conn.close()


def truncate_historique():
    """Vide la table de l'historique des messages."""
    conn = get_conn()
    conn.execute("DELETE FROM messages_envoyes")
    conn.commit()
    conn.close()


def truncate_plongeurs():
    """Vide la table plongeurs_club. Conserve messages et paramètres."""
    conn = get_conn()
    conn.execute("DELETE FROM plongeurs_club")
    conn.commit()
    conn.close()


def truncate_all_data():
    """Supprime tout : plongeurs, messages, paramètres.
    Les paramètres par défaut seront recréés au prochain init_db."""
    conn = get_conn()
    conn.execute("DELETE FROM plongeurs_club")
    conn.execute("DELETE FROM messages_envoyes")
    conn.execute("DELETE FROM parametres_club")
    conn.commit()
    conn.close()
    # Recréer les paramètres par défaut
    init_db()


# ──────────────────────────────────────────────────────────────────────────────
# Import FFESSM (identique SecuManager)
# ──────────────────────────────────────────────────────────────────────────────

def _read_xlsx_native(path: str):
    """Lecture XLSX optimisée en STREAMING (iterparse) — compatible Android.

    Optimisations vs. version DOM :
    - iterparse() + clear() : ne garde jamais l'arbre complet en mémoire
    - Tags XML qualifiés en chaînes pré-construites (pas de résolution NS)
    - Itération directe sur les enfants (pas de XPath findtext)
    - dict(zip(...)) à la place de dict comprehension

    Retourne list[dict] (compatible avec l'API existante).
    """
    NS      = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    SI_TAG  = NS + 'si'
    T_TAG   = NS + 't'
    ROW_TAG = NS + 'row'
    C_TAG   = NS + 'c'
    V_TAG   = NS + 'v'
    IS_TAG  = NS + 'is'

    with zipfile.ZipFile(path, 'r') as z:
        names = z.namelist()

        # ── Shared strings (streaming) ─────────────────────────────────
        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            with z.open("xl/sharedStrings.xml") as f:
                for event, elem in ET.iterparse(f, events=("end",)):
                    if elem.tag == SI_TAG:
                        # Concaténer tous les <t> descendants (gère le rich text <r>)
                        parts = []
                        for t in elem.iter(T_TAG):
                            if t.text:
                                parts.append(t.text)
                        shared_strings.append("".join(parts))
                        elem.clear()

        # ── Sheet1 (streaming row-par-row) ─────────────────────────────
        if "xl/worksheets/sheet1.xml" not in names:
            return []

        rows = []
        current_row = None
        with z.open("xl/worksheets/sheet1.xml") as f:
            for event, elem in ET.iterparse(f, events=("start", "end")):
                if event == "start":
                    if elem.tag == ROW_TAG:
                        current_row = []
                    continue
                # event == "end"
                tag = elem.tag
                if tag == C_TAG and current_row is not None:
                    t_attr = elem.get('t')
                    if t_attr == 's':
                        v_elem = elem.find(V_TAG)
                        v = v_elem.text if v_elem is not None else None
                        if v and v.isdigit():
                            idx = int(v)
                            if 0 <= idx < len(shared_strings):
                                current_row.append(shared_strings[idx])
                            else:
                                current_row.append("")
                        else:
                            current_row.append("")
                    elif t_attr == 'inlineStr':
                        is_elem = elem.find(IS_TAG)
                        if is_elem is not None:
                            parts = []
                            for te in is_elem.iter(T_TAG):
                                if te.text:
                                    parts.append(te.text)
                            current_row.append("".join(parts))
                        else:
                            current_row.append("")
                    else:
                        v_elem = elem.find(V_TAG)
                        current_row.append(v_elem.text if v_elem is not None else "")
                    elem.clear()
                elif tag == ROW_TAG:
                    rows.append(current_row)
                    current_row = None
                    elem.clear()

    if not rows:
        return []

    headers = [(h or "").strip() for h in rows[0]]
    n_hdr = len(headers)
    out = []
    out_append = out.append
    for r in rows[1:]:
        if len(r) < n_hdr:
            r = r + [""] * (n_hdr - len(r))
        out_append(dict(zip(headers, r)))

    return out



def import_xlsx_ffessm_data(path: str):
    """Import FFESSM optimisé pour gros volumes (plusieurs milliers de licenciés).

    Optimisations :
    - Pré-résolution UNE SEULE FOIS des colonnes opt_match (au lieu d'O(n_cols × n_kw)
      par plongeur)
    - Lookup des brevets via set au lieu de list (O(1) vs O(n))
    - Court-circuit norm_date quand la valeur est vide (évite l'appel)
    - Constantes globales liées en local dans la boucle (micro-opt CPython)
    - plongeurs.append bound en local
    """
    # --- Lecture fichier ---
    try:
        ext = path.lower()
        if ext.endswith(".xlsx"):
            records = _read_xlsx_native(path)
        elif ext.endswith((".csv", ".txt")):
            for enc in ("utf-8-sig", "utf-8", "latin1"):
                try:
                    with open(path, "r", encoding=enc) as f:
                        reader = csv.DictReader(f, delimiter=";")
                        records = list(reader)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return None, "Encodage CSV non reconnu."
        else:
            return None, "Format non supporté."
    except Exception as e:
        return None, f"Erreur lecture fichier : {e}"

    if not records:
        return None, "Fichier vide ou illisible."

    # --- Vérification colonnes ---
    cols_requises = [
        "Identifiant", "Nom", "Prénom",
        "Brevets", "Date Fin Validité CACI", "Date Naissance",
    ]
    first_keys = set(records[0].keys())
    missing = [c for c in cols_requises if c not in first_keys]
    if missing:
        return None, "Colonnes manquantes : " + ", ".join(missing)

    # --- Pré-résolution des correspondances de colonnes (1 seule fois) ---
    def norm(s):
        return (s or "").lower().replace(" ", "").replace(".", "")\
                                .replace("-", "").replace("_", "")

    colmap_items = [(norm(c), c) for c in records[0].keys()]

    def resolve_col(*keywords):
        """Trouve LE nom de colonne original qui matche un des keywords (par sous-chaîne)."""
        keys_norm = [norm(k) for k in keywords]
        for col_norm, col_orig in colmap_items:
            for kw in keys_norm:
                if kw in col_norm:
                    return col_orig
        return None

    col_portable  = resolve_col("portable", "mobile", "gsm")
    col_email     = resolve_col("email", "courriel", "mail")
    col_club      = resolve_col("nomclub", "nomduclub", "club")
    col_cat_extra = resolve_col("categorie", "catégorie")

    INVALID_STR = {"nan", "nat", "none"}

    def opt(row, col):
        if not col:
            return ""
        v = row.get(col, "")
        if not v:
            return ""
        v = str(v).strip()
        return "" if v.lower() in INVALID_STR else v

    # --- Constantes locales (lookup local plus rapide que global en CPython) ---
    SIMPL_TOUS   = SIMPLIFICATIONS_TOUS_BREVETS
    SIMPL_NIVEAU = SIMPLIFICATIONS_BREVETS
    BPLO         = BREVETS_PLONGEUR_ORDRE
    _norm_date   = norm_date

    plongeurs = []
    append    = plongeurs.append

    # --- Boucle principale optimisée ---
    for row in records:
        licence = opt(row, "Identifiant")
        if not licence:
            continue

        nom = opt(row, "Nom").upper()
        if not nom:
            continue
        prenom = opt(row, "Prénom").title()

        # --- Brevets : split + set pour lookups O(1) ---
        brevets_str = opt(row, "Brevets")
        if brevets_str:
            brevets_list = [b.strip() for b in brevets_str.split(",") if b.strip()]
            brevets_set    = set(brevets_list)
            brevets_courts = {SIMPL_TOUS.get(b, b) for b in brevets_list}
        else:
            brevets_set    = set()
            brevets_courts = set()

        # Moniteur
        brev_m = ""
        for g in ("E4", "E3", "E2", "E1"):
            if g in brevets_courts:
                brev_m = g
                break

        # Encadrant
        brev_e = "GP" if ("GP" in brevets_courts or "N4/GP" in brevets_courts) else ""

        # Plongeur (lookup O(1) dans brevets_set)
        brev_p = "Débutant"
        for candidat in BPLO:
            if candidat in brevets_set:
                brev_p = SIMPL_NIVEAU.get(candidat, candidat)
                break

        # Nitrox
        brev_nx = ""
        for nx in ("MNx", "PNC", "PN"):
            if nx in brevets_courts:
                brev_nx = nx
                break

        niveau = brev_m or brev_e or brev_p

        # --- Dates : on évite l'appel norm_date(...) si la valeur est vide ---
        dn = opt(row, "Date Naissance")
        date_naiss = _norm_date(dn) if dn else ""

        dc = opt(row, "Date Début Validité CACI") or opt(row, "Date Début CACI")
        date_caci = _norm_date(dc) if dc else ""

        dfc = opt(row, "Date Fin Validité CACI")
        date_fin_caci = _norm_date(dfc) if dfc else ""

        # Catégorie : double tentative directe + fallback fuzzy
        categorie = opt(row, "Catégorie") or opt(row, "Categorie")
        if not categorie and col_cat_extra:
            categorie = opt(row, col_cat_extra)

        append({
            "id_licence": licence,
            "nom": nom,
            "prenom": prenom,
            "date_naissance": date_naiss,
            "niveau": niveau,
            "niveau_prepa": "",
            "brev_moniteur": brev_m,
            "brev_encadrant": brev_e,
            "brev_plongeur": brev_p,
            "brev_nitrox": brev_nx,
            "brevets_brut": brevets_str,
            "portable": opt(row, col_portable),
            "email": opt(row, col_email),
            "saison": opt(row, "Saison"),
            "type_licence": opt(row, "Type de licence") or opt(row, "Type licence"),
            "categorie": categorie,
            "date_caci": date_caci,
            "date_fin_caci": date_fin_caci,
            "nom_club": opt(row, col_club),
        })

    return plongeurs, None


# ──────────────────────────────────────────────────────────────────────────────
# Filtres destinataires
# ──────────────────────────────────────────────────────────────────────────────

def evaluer_item(p: dict, item: dict) -> bool:
    """Évalue un item de filtre commission pour un plongeur.
    Modes : "tous_avec" / "selection" / "tous_sans"."""
    nom_com = item.get("commission", "")
    mode    = item.get("mode", "tous_avec")
    brevets_dans_com = brevets_d_une_commission(p.get("brevets_brut", "") or "", nom_com)
    if mode == "tous_avec":
        return bool(brevets_dans_com)
    if mode == "tous_sans":
        return not brevets_dans_com
    if mode == "selection":
        brevets_exacts = item.get("brevets", [])
        if not brevets_exacts:
            return bool(brevets_dans_com)
        return any(b in brevets_dans_com for b in brevets_exacts)
    return False


def evaluer_expression(p: dict, tokens: list) -> bool:
    """Évalue l'expression booléenne définie par la liste de tokens pour un plongeur.

    Tokens :
      - {"type": "item",        "commission": ..., "mode": ..., "brevets": [...]}
      - {"type": "op",          "value": "OU" | "ET" | "NON"}
      - {"type": "paren_open"}  ( "("
      - {"type": "paren_close"} ( ")"

    Règles :
      - Auto-fermeture : si des "(" ne sont pas refermées, on ajoute autant de ")".
      - Opérateur implicite entre deux items côte à côte : "ET".
      - Précédence Python : not > and > or.
      - Expression vide  → True (aucun filtre).
      - Expression invalide → True (on n'exclut personne plutôt que tout).
    """
    if not tokens:
        return True

    tokens = list(tokens)
    nb_open  = sum(1 for t in tokens if t["type"] == "paren_open")
    nb_close = sum(1 for t in tokens if t["type"] == "paren_close")
    if nb_open > nb_close:
        tokens += [{"type": "paren_close"}] * (nb_open - nb_close)

    parts = []
    prev_kind = None  # "value" | "op" | None
    for t in tokens:
        ttype = t["type"]
        if ttype == "paren_open":
            if prev_kind == "value":
                parts.append("and")
            parts.append("(")
            prev_kind = "op"
        elif ttype == "paren_close":
            parts.append(")")
            prev_kind = "value"
        elif ttype == "op":
            op = t.get("value", "")
            if op == "OU":
                parts.append("or"); prev_kind = "op"
            elif op == "ET":
                parts.append("and"); prev_kind = "op"
            elif op == "NON":
                if prev_kind == "value":
                    parts.append("and")
                parts.append("not"); prev_kind = "op"
        elif ttype == "item":
            if prev_kind == "value":
                parts.append("and")
            parts.append("True" if evaluer_item(p, t) else "False")
            prev_kind = "value"

    expr = " ".join(parts)
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return True


def appliquer_filtres(plongeurs: list, filtres: dict) -> list:
    """
    filtres = {
        "filtre_tokens": [...],            # expression booléenne à tokens
        "types_licence": ["Pratiquant"],
        "categories":    ["Adulte"],
        "age_min": None, "age_max": None,
        "statuts_caci": [],
        "avec_email":  bool, "avec_portable": bool,
    }
    Logique :
    - Section commission : évaluation de l'expression booléenne (avec ET/OU/NON/parens)
    - Entre sections : ET
    """
    resultat = []
    tokens           = filtres.get("filtre_tokens") or []
    types_licence    = filtres.get("types_licence") or []
    categories       = filtres.get("categories") or []
    age_min          = filtres.get("age_min")
    age_max          = filtres.get("age_max")
    statuts_caci     = filtres.get("statuts_caci", [])
    avec_email       = filtres.get("avec_email", False)
    avec_portable    = filtres.get("avec_portable", False)

    types_licence_low = [t.lower() for t in types_licence]
    categories_low    = [c.lower() for c in categories]

    for p in plongeurs:
        # Filtre expression commission
        if tokens and not evaluer_expression(p, tokens):
            continue

        # Type de licence (OR interne)
        if types_licence:
            tl = (p.get("type_licence", "") or "").lower()
            if not any(t in tl for t in types_licence_low):
                continue

        # Catégorie (OR interne)
        if categories:
            cat = (p.get("categorie", "") or "").lower()
            if not any(c in cat for c in categories_low):
                continue

        # Âge
        if age_min is not None or age_max is not None:
            age = calcul_age(p.get("date_naissance", ""))
            if age is None:
                continue
            if age_min is not None and age < age_min:
                continue
            if age_max is not None and age > age_max:
                continue

        # CACI
        if statuts_caci:
            statut, _ = calcul_statut_caci(p.get("date_fin_caci", ""))
            if statut not in statuts_caci:
                continue

        # Contact
        if avec_email and not p.get("email", "").strip():
            continue
        if avec_portable and not p.get("portable", "").strip():
            continue

        resultat.append(p)

    return resultat


# ──────────────────────────────────────────────────────────────────────────────
# Envoi Email
# ──────────────────────────────────────────────────────────────────────────────

def envoyer_email(destinataire_email, sujet, corps, piece_jointe_path=None,
                  smtp_host="", smtp_port=587, smtp_user="",
                  smtp_password="", use_tls=True, expediteur=""):
    """Envoie un email via SMTP. Retourne (ok, message_erreur)."""
    try:
        msg = MIMEMultipart()
        msg["From"]    = expediteur or smtp_user
        msg["To"]      = destinataire_email
        msg["Subject"] = sujet
        msg.attach(MIMEText(corps, "plain", "utf-8"))

        if piece_jointe_path and os.path.isfile(piece_jointe_path):
            fname = os.path.basename(piece_jointe_path)
            with open(piece_jointe_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=\"{fname}\""
            )
            msg.attach(part)

        server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=15)
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [destinataire_email], msg.as_string())
        server.quit()
        return True, ""
    except Exception as e:
        return False, str(e)


# ──────────────────────────────────────────────────────────────────────────────
# Application principale
# ──────────────────────────────────────────────────────────────────────────────

