"""
ClubMessenger v1.1.0
Application Flet (Android) — Messagerie ciblée pour club de plongée FFESSM
Bundle : fr.csdev.clubmessenger
Auteur  : CS-DEV (Cédric SALVAT)
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
VERSION = "1.1.0"
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
    "RIFA Tir sur cible": "RIFATSC",
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
}


BREVETS_PLONGEUR_ORDRE = [
    "Niveau 3",
    "Plongeur encadré 60 mètres",
    "Plongeur autonome 40 mètres",
    "Niveau 2",
    "Plongeur encadré 40 mètres",
    "Plongeur autonome 20 mètres",
    "Niveau 1",
    "Niveau 1 passerelle SSI"
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
]

BREVETS_JEUNES = [
    "Plongeur Or",
    "Plongeur Argent",
    "Plongeur Bronze",
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

# Filtres transversaux : Handisub & Activités Jeunes (non liés à une commission)
FILTRES_TRANSVERSAUX = [
    ("Handisub",         BREVETS_HANDI),
    ("Activités Jeunes", BREVETS_JEUNES),
]

# Filtres secourisme
FILTRES_SECOURISME = [
    ("Secourisme",       BREVETS_SECOURS),
]

# Sections affichées dans l'UI : (titre_section, liste_des_filtres)
SECTIONS_FILTRES = [
    ("Commissions FFESSM", COMMISSIONS_FFESSM),
    ("Transversaux",       FILTRES_TRANSVERSAUX),
    ("Secourisme",         FILTRES_SECOURISME),
]


def _tous_filtres():
    """Liste fusionnée (nom, brevets) de tous les filtres (commissions +
    transversaux + secourisme). Utilisé pour le lookup par nom."""
    out = []
    for _titre, filtres in SECTIONS_FILTRES:
        out.extend(filtres)
    return out


def brevets_d_une_commission(brevets_brut: str, commission_nom: str) -> list:
    """Retourne les brevets (noms complets) d'un plongeur appartenant à
    une commission/transversal/secourisme donnée, par appartenance exacte
    à la liste de référence.
    """
    liste_ref = next(
        (lst for nom, lst in _tous_filtres() if nom == commission_nom),
        []
    )
    if not liste_ref or not brevets_brut:
        return []
    brevets = [b.strip() for b in brevets_brut.split(",") if b.strip()]
    liste_ref_set = set(liste_ref)
    return [b for b in brevets if b in liste_ref_set]


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
    Retourne (moniteur, encadrant, plongeur, nitrox) — codes courts — à partir
    de la liste brute FFESSM.
    Utilise SIMPLIFICATIONS_TOUS_BREVETS pour matcher les noms complets
    ("E2 - Niveau IV/GP/Directeur de bassin" → "E2"), et reste tolérant aux
    notations courtes éventuellement déjà présentes ("E2" direct).
    """
    t = str(brevets_str) if brevets_str else ""
    elements = [e.strip() for e in t.split(",") if e.strip()]

    # Pour chaque élément FFESSM, on calcule sa version courte (via le dict
    # complet) ; sinon on garde l'élément tel quel.
    elements_courts = set()
    for e in elements:
        elements_courts.add(SIMPLIFICATIONS_TOUS_BREVETS.get(e, e))

    # Moniteur : E1..E4 en code court (priorité décroissante)
    brev_m = ""
    for grad in ["E4", "E3", "E2", "E1"]:
        if grad in elements_courts:
            brev_m = grad
            break

    # Encadrant : GP / N4/GP
    brev_e = ""
    if "GP" in elements_courts or "N4/GP" in elements_courts:
        brev_e = "GP"

    # Plongeur : ordre priorité décroissant (BREVETS_PLONGEUR_ORDRE)
    brev_p = "Débutant"
    for candidat in BREVETS_PLONGEUR_ORDRE:
        if candidat in elements:
            brev_p = SIMPLIFICATIONS_BREVETS.get(candidat, candidat)
            break

    # Nitrox : on cherche par valeur courte (PN / PNC / MNx)
    brev_nx = ""
    for sigle in ["MNx", "PNC", "PN"]:
        if sigle in elements_courts:
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
    data_dir = os.path.join(os.path.expanduser("~"), ".clubmessenger")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DB_NAME)


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


def upsert_plongeurs_batch(plongeurs: list):
    """Upsert d'une liste de plongeurs en une seule transaction.
    Très rapide (~100×) comparé à upsert plongeur par plongeur.
    """
    if not plongeurs:
        return
    conn = get_conn()
    try:
        # Précharger les niveau_prepa existants pour appliquer la règle de vidage
        ids = [p.get("id_licence", "") for p in plongeurs if p.get("id_licence")]
        prepas_existants = {}
        if ids:
            placeholders = ",".join("?" * len(ids))
            for id_lic, prepa in conn.execute(
                f"SELECT id_licence, niveau_prepa FROM plongeurs_club "
                f"WHERE id_licence IN ({placeholders})", ids
            ).fetchall():
                prepas_existants[id_lic] = prepa

        # PRAGMA pour accélérer les inserts en masse
        conn.execute("BEGIN")
        for p in plongeurs:
            prepa_ancien = prepas_existants.get(p.get("id_licence", ""), "")
            _upsert_plongeur_on_conn(conn, p, prepa_ancien)
        conn.commit()
    except Exception:
        conn.rollback()
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
    """Lit un fichier XLSX sans pandas/openpyxl.
    Utilise zipfile + xml.etree (compatible Android).
    Retourne une liste de dict {nom_colonne: valeur_brute}.
    """
    with zipfile.ZipFile(path, 'r') as z:
        # Chaînes partagées
        shared_strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            ss_xml = z.read("xl/sharedStrings.xml")
            root_ss = ET.fromstring(ss_xml)
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root_ss.findall('ns:si', ns):
                # Une cellule peut être texte direct OU rich-text (plusieurs <t>)
                texts = [t.text or "" for t in si.findall('.//ns:t', ns)]
                shared_strings.append("".join(texts))

        # Première feuille
        sheet_xml = z.read("xl/worksheets/sheet1.xml")
        root_sheet = ET.fromstring(sheet_xml)
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

        rows_data = []
        for row in root_sheet.findall('.//ns:row', ns):
            row_cells = []
            for c in row.findall('ns:c', ns):
                t = c.get('t')
                v_elem = c.find('ns:v', ns)
                v = v_elem.text if v_elem is not None else ""
                if t == 's' and v.isdigit():
                    idx = int(v)
                    row_cells.append(shared_strings[idx] if idx < len(shared_strings) else "")
                elif t == 'inlineStr':
                    is_elem = c.find('ns:is', ns)
                    if is_elem is not None:
                        t_elem = is_elem.find('ns:t', ns)
                        row_cells.append(t_elem.text if t_elem is not None else "")
                    else:
                        row_cells.append("")
                else:
                    row_cells.append(v or "")
            if row_cells:
                rows_data.append(row_cells)

    if not rows_data:
        return []

    # Conversion en list[dict]
    headers = [str(h).strip() for h in rows_data[0]]
    records = []
    for row in rows_data[1:]:
        while len(row) < len(headers):
            row.append("")
        record = {headers[i]: row[i] for i in range(len(headers))}
        records.append(record)
    return records


def import_xlsx_ffessm_data(path: str):
    """
    Lit le fichier FFESSM (XLSX ou CSV) et retourne (liste_plongeurs, erreur).
    Parseur natif sans dépendance externe (compatible Android).
    """
    try:
        ext = path.lower()
        if ext.endswith(".xlsx"):
            records = _read_xlsx_native(path)
        elif ext.endswith((".csv", ".txt")):
            # Tente UTF-8 puis latin-1
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
            return None, "Format non supporté (utilisez .xlsx ou .csv)."
    except Exception as e:
        return None, f"Erreur lecture fichier : {e}"

    if not records:
        return None, "Fichier vide ou illisible."

    # Vérification des colonnes obligatoires
    cols_requises = [
        "Identifiant", "Nom", "Prénom",
        "Brevets", "Date Fin Validité CACI", "Date Naissance",
    ]
    first_keys = set(records[0].keys())
    missing = [c for c in cols_requises if c not in first_keys]
    if missing:
        return None, (
            "Colonnes manquantes : " + ", ".join(missing) +
            ". Vérifier qu'il s'agit d'une extraction licenciés FFESSM."
        )

    def opt(row, col):
        v = row.get(col, "")
        if v is None:
            return ""
        v = str(v).strip()
        return "" if v.lower() in ("nan", "nat", "none") else v

    def opt_match(row, keywords):
        """Cherche la 1ère colonne dont le nom (lowercase) contient un des
        keywords. Insensible à la casse, aux espaces et aux accents."""
        def norm(s):
            return (s or "").lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
        keys_norm = [norm(k) for k in keywords]
        for col_name in row.keys():
            col_norm = norm(col_name)
            if any(kw in col_norm for kw in keys_norm):
                v = opt(row, col_name)
                if v:
                    return v
        return ""

    plongeurs = []
    for row in records:
        licence = opt(row, "Identifiant")
        if not licence:
            continue
        nom    = opt(row, "Nom").upper()
        prenom = opt(row, "Prénom").title()
        if not nom:
            continue

        brevets_str = opt(row, "Brevets")
        brev_m, brev_e, brev_p, brev_nx = extract_brevets(brevets_str)
        niveau = brev_m or brev_e or brev_p

        plongeurs.append({
            "id_licence":     licence,
            "nom":            nom,
            "prenom":         prenom,
            "date_naissance": norm_date(opt(row, "Date Naissance")),
            "niveau":         niveau,
            "niveau_prepa":   "",
            "brev_moniteur":  brev_m,
            "brev_encadrant": brev_e,
            "brev_plongeur":  brev_p,
            "brev_nitrox":    brev_nx,
            "brevets_brut":   brevets_str,
            "portable":       opt_match(row, ["portable", "mobile", "gsm"]),
            "email":          opt_match(row, ["email", "courriel", "mail"]),
            "saison":         opt(row, "Saison"),
            "type_licence":   opt(row, "Type de licence") or opt(row, "Type licence"),
            "categorie":      opt(row, "Catégorie") or opt(row, "Categorie") or
                              opt_match(row, ["categorie", "catégorie"]),
            "date_caci":      norm_date(opt(row, "Date Début Validité CACI") or
                                        opt(row, "Date Début CACI")),
            "date_fin_caci":  norm_date(opt(row, "Date Fin Validité CACI")),
            "nom_club":       opt_match(row, ["nomclub", "nomdu club", "club"]),
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


def evaluer_groupes(p: dict, groupes: list) -> bool:
    """Plongeur passe si TOUS les groupes matchent (AND).
    Un groupe matche si AU MOINS UN item matche (OR)."""
    if not groupes:
        return True
    for grp in groupes:
        if not any(evaluer_item(p, it) for it in grp):
            return False
    return True


def appliquer_filtres(plongeurs: list, filtres: dict) -> list:
    """
    filtres = {
        "groupes_filtres": [[item, ...], [item, ...], ...],
        "types_licence": ["Pratiquant", "Aidant"],   # liste de mots-clés à matcher
        "categories":    ["Enfant", "Jeune", "Adulte"],
        "age_min":     None, "age_max": None,
        "statuts_caci": [],
        "avec_email":  bool, "avec_portable": bool,
    }
    Logique :
    - Dans un groupe commission : OU entre items
    - Entre groupes : ET
    - Entre sections (groupes, types licence, catégories, âge, CACI, contact) : ET
    """
    resultat = []
    groupes          = filtres.get("groupes_filtres") or []
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
        # Filtre groupes (OR dans, AND entre)
        if not evaluer_groupes(p, groupes):
            continue

        # Filtre type de licence (OR entre options) - matche par sous-chaîne (case insensitive)
        if types_licence:
            tl = (p.get("type_licence", "") or "").lower()
            if not any(t in tl for t in types_licence_low):
                continue

        # Filtre catégorie (OR entre options)
        if categories:
            cat = (p.get("categorie", "") or "").lower()
            if not any(c in cat for c in categories_low):
                continue

        # Filtre âge (AND)
        if age_min is not None or age_max is not None:
            age = calcul_age(p.get("date_naissance", ""))
            if age is None:
                continue
            if age_min is not None and age < age_min:
                continue
            if age_max is not None and age > age_max:
                continue

        # Filtre CACI (AND)
        if statuts_caci:
            statut, _ = calcul_statut_caci(p.get("date_fin_caci", ""))
            if statut not in statuts_caci:
                continue

        # Filtre contact (AND)
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

class ClubMessengerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = APP_TITLE
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width  = 420
        self.page.window.height = 900
        self.page.padding = 0
        self.page.bgcolor = ft.Colors.GREY_100

        self.plongeurs: list = []
        self.filtres_actifs: dict = {}
        self.destinataires_selectionnes: list = []

        # Référence aux onglets
        self.tab_plongeurs   = None
        self.tab_composer    = None
        self.tab_historique  = None
        self.tab_parametres  = None

        # FilePicker UNIQUE — créé au démarrage et ajouté aux services
        # (sinon timeout sur pick_files en Flet 0.85)
        self.file_picker = ft.FilePicker()
        self.page.services.append(self.file_picker)

        self._build_ui()
        self._load_data()

    # ──────────────────────────────────────────────────────────────────────
    # Construction UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Construction des 4 pages
        self.page_plongeurs  = self._build_tab_plongeurs()
        self.page_composer   = self._build_tab_composer()
        self.page_historique = self._build_tab_historique()
        self.page_parametres = self._build_tab_parametres()

        # Container qui contient la page active
        self.content_area = ft.Container(
            content=self.page_plongeurs,
            expand=True,
        )

        # NavigationBar en bas
        self.nav_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.PEOPLE,   label="Plongeurs"),
                ft.NavigationBarDestination(icon=ft.Icons.SEND,     label="Composer"),
                ft.NavigationBarDestination(icon=ft.Icons.HISTORY,  label="Historique"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Paramètres"),
            ],
        )

        self.page.navigation_bar = self.nav_bar
        self.page.add(self.content_area)

    def _on_nav_change(self, e):
        idx = self.nav_bar.selected_index
        pages = [
            self.page_plongeurs,
            self.page_composer,
            self.page_historique,
            self.page_parametres,
        ]
        self.content_area.content = pages[idx]
        self._safe_update(self.content_area)
        # Rafraîchit les données de l'onglet qui devient visible
        if idx == 0:
            self._refresh_liste_plongeurs(
                self.search_field.value if hasattr(self, "search_field") else ""
            )
        elif idx == 1:
            self._actualiser_destinataires()
        elif idx == 2:
            self._refresh_historique()
        elif idx == 3 and hasattr(self, "params_fields"):
            self._load_params_fields()
        try:
            self.page.update()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # TAB 1 — Plongeurs
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_plongeurs(self):
        self.search_field = ft.TextField(
            hint_text="Rechercher (nom, prénom, licence)…",
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search,
            dense=True,
            border_radius=8,
        )
        # ListView : beaucoup plus efficace qu'une Column scrollable pour
        # des listes longues (rendu paresseux par le moteur Flet)
        self.liste_plongeurs_col = ft.ListView(
            expand=True,
            spacing=4,
            padding=0,
            cache_extent=200,  # pré-rendre ~200px hors viewport
        )
        self.lbl_nb_plongeurs = ft.Text("", size=12, color=ft.Colors.GREY_600)

        btn_import = ft.FilledButton(
            "Importer FFESSM",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._on_import_ffessm,
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        )
        btn_vider = ft.OutlinedButton(
            "Vider la base",
            icon=ft.Icons.DELETE_OUTLINE,
            on_click=self._on_vider_plongeurs,
            style=ft.ButtonStyle(color=ft.Colors.RED_700),
        )

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(
                                "Plongeurs du club",
                                size=18, weight=ft.FontWeight.BOLD,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Actualiser",
                                on_click=lambda _: self._load_data(),
                            ),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        self.search_field,
                        ft.Row([
                            self.lbl_nb_plongeurs,
                            ft.Row([btn_import, btn_vider], spacing=6),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], spacing=8),
                    padding=12,
                    bgcolor=ft.Colors.WHITE,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=self.liste_plongeurs_col,
                    expand=True,
                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                ),
            ], spacing=0),
            expand=True,
        )

    def _build_carte_plongeur(self, p: dict) -> ft.Control:
        """Carte plongeur : ListTile (widget Flet optimisé pour les longues listes).
        Bien plus rapide à rendre que Container+Row+Column custom."""
        statut_caci, coul_caci = calcul_statut_caci(p.get("date_fin_caci", ""))
        age = calcul_age(p.get("date_naissance", ""))
        age_str = f"  •  {age} ans" if (age is not None and age < 18) else ""
        niveau_str = niveau_affiche(p.get("niveau", ""), p.get("brev_nitrox", ""))

        prepa = p.get("niveau_prepa", "")
        subtitle_parts = [niveau_str + age_str]
        if prepa:
            subtitle_parts.append(f"→ {prepa}")
        subtitle = "   ·   ".join(subtitle_parts)

        statut_chip = ft.Container(
            content=ft.Text(statut_caci, size=10, color=ft.Colors.WHITE),
            bgcolor=coul_caci,
            border_radius=4,
            padding=ft.Padding(left=6, right=6, top=2, bottom=2),
        )

        return ft.ListTile(
            title=ft.Text(
                f"{p['nom']} {p['prenom']}",
                weight=ft.FontWeight.BOLD,
                size=14,
            ),
            subtitle=ft.Text(subtitle, size=12, color=ft.Colors.GREY_700),
            trailing=statut_chip,
            on_click=lambda _, plongeur=p: self._show_fiche_plongeur(plongeur),
            dense=True,
            bgcolor=ft.Colors.WHITE,
        )

    def _refresh_liste_plongeurs(self, query=""):
        plongeurs_filtres = self.plongeurs
        if query:
            q = query.lower()
            plongeurs_filtres = [
                p for p in self.plongeurs
                if q in p["nom"].lower()
                or q in p["prenom"].lower()
                or q in (p.get("id_licence") or "").lower()
            ]
        self.liste_plongeurs_col.controls.clear()
        for p in plongeurs_filtres:
            self.liste_plongeurs_col.controls.append(
                self._build_carte_plongeur(p)
            )
        self.lbl_nb_plongeurs.value = f"{len(plongeurs_filtres)} plongeur(s)"
        self._safe_update(self.liste_plongeurs_col)
        self._safe_update(self.lbl_nb_plongeurs)

    def _on_search(self, e):
        self._refresh_liste_plongeurs(e.control.value)

    # ── Fiche détail plongeur ─────────────────────────────────────────────

    def _show_fiche_plongeur(self, p: dict):
        statut_caci, coul_caci = calcul_statut_caci(p.get("date_fin_caci", ""))
        age = calcul_age(p.get("date_naissance", ""))
        # Âge affiché uniquement pour les mineurs
        age_str = f"  ({age} ans)" if (age is not None and age < 18) else ""
        niveau_str = niveau_affiche(p.get("niveau", ""), p.get("brev_nitrox", ""))

        email = (p.get("email", "") or "").strip()
        portable = (p.get("portable", "") or "").strip()
        nom_club = (p.get("nom_club", "") or "").strip()

        def ligne(label, valeur, couleur=None, multi_ligne=False):
            txt = ft.Text(
                valeur or "—",
                size=12,
                color=couleur or ft.Colors.BLACK87,
                no_wrap=not multi_ligne,
            )
            if multi_ligne:
                return ft.Row([
                    ft.Text(label, size=12, color=ft.Colors.GREY_600, width=130),
                    ft.Container(content=txt, expand=True),
                ], vertical_alignment=ft.CrossAxisAlignment.START)
            return ft.Row([
                ft.Text(label, size=12, color=ft.Colors.GREY_600, width=130),
                txt,
            ])

        def ligne_scroll(label, valeur, on_click=None):
            """Ligne avec scroll horizontal pour contenu long (email)."""
            txt = ft.Text(
                valeur or "—",
                size=12,
                color=ft.Colors.BLUE_700 if (on_click and valeur) else ft.Colors.BLACK87,
                no_wrap=True,
            )
            inner = ft.Row([txt], scroll=ft.ScrollMode.AUTO, expand=True)
            return ft.Row([
                ft.Text(label, size=12, color=ft.Colors.GREY_600, width=130),
                ft.Container(
                    content=inner,
                    expand=True,
                    on_click=on_click if valeur else None,
                    ink=bool(on_click and valeur),
                ),
            ])

        prepa = p.get("niveau_prepa", "")
        prepa_row = ligne("Niveau en prépa", prepa) if prepa else ft.Container()
        nom_club_row = ligne("Club ou OD", nom_club, multi_ligne=True) if nom_club else ft.Container()

        def open_mail(_):
            club = get_param("nom_club_court")
            sujet = urllib.parse.quote(f"Message de {club}")
            self.page.launch_url(f"mailto:{email}?subject={sujet}")

        def open_tel(_):
            num = re.sub(r'[^\d+]', '', portable)
            self.page.launch_url(f"tel:{num}")

        contenu = ft.Column([
            ft.Text(
                f"{p['nom']} {p['prenom']}",
                size=18, weight=ft.FontWeight.BOLD,
            ),
            ft.Divider(),
            ligne("N° Licence",      p.get("id_licence", "")),
            ligne("Date naissance",  p.get("date_naissance", "") + age_str),
            ligne("Saison",          p.get("saison", "")),
            ligne("Type licence",    p.get("type_licence", "")),
            nom_club_row,
            ft.Divider(),
            ligne("Niveau",          niveau_str),
            prepa_row,
            ligne("Brevet moniteur",   p.get("brev_moniteur", "")),
            ligne("Brevet encadrant",  p.get("brev_encadrant", "")),
            ligne("Brevet plongeur",   p.get("brev_plongeur", "")),
            ligne("Brevet nitrox",     p.get("brev_nitrox", "")),
            ft.Row([
                ft.Text("Tous les brevets", size=12, color=ft.Colors.GREY_600, width=130),
                ft.TextButton(
                    f"Voir ({len(parse_brevets(p.get('brevets_brut', '')))})",
                    icon=ft.Icons.LIST,
                    on_click=lambda _, plg=p: self._show_tous_brevets(plg),
                ),
            ]),
            ft.Divider(),
            ligne("CACI fin",        p.get("date_fin_caci", "")),
            ft.Row([
                ft.Text("Statut CACI", size=12, color=ft.Colors.GREY_600, width=130),
                ft.Container(
                    content=ft.Text(statut_caci, size=12, color=ft.Colors.WHITE),
                    bgcolor=coul_caci,
                    border_radius=4,
                    padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                ),
            ]),
            ft.Divider(),
            ligne_scroll("Email",    email,    on_click=open_mail if email else None),
            ligne_scroll("Portable", portable, on_click=open_tel  if portable else None),
        ], scroll=ft.ScrollMode.AUTO, spacing=6)

        def fermer(_):
            self.page.pop_dialog()

        actions = []
        if email:
            actions.append(ft.TextButton("Email", icon=ft.Icons.EMAIL, on_click=open_mail))
        if portable:
            actions.append(ft.TextButton("Tél.",  icon=ft.Icons.PHONE, on_click=open_tel))
        actions.append(ft.TextButton("Fermer", on_click=fermer))

        dlg = ft.AlertDialog(
            title=ft.Text("Fiche plongeur"),
            content=ft.Container(content=contenu, width=360, height=500),
            actions=actions,
        )
        self.page.show_dialog(dlg)

    def _show_tous_brevets(self, p: dict):
        """Popup secondaire listant tous les brevets bruts du plongeur."""
        brevets = parse_brevets(p.get("brevets_brut", ""))

        if not brevets:
            self._show_snack("Aucun brevet enregistré pour ce plongeur.")
            return

        lignes = []
        for nom_long, nom_court in brevets:
            # Code court en chip + nom complet à côté
            lignes.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(nom_court, size=11,
                                        color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.BLUE_700,
                        border_radius=4,
                        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                        width=70,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(nom_long, size=12, expand=True),
                ], spacing=8)
            )

        def fermer(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text(f"{p['nom']} {p['prenom']} — {len(brevets)} brevet(s)",
                          size=14),
            content=ft.Container(
                content=ft.Column(lignes, scroll=ft.ScrollMode.AUTO, spacing=4),
                width=380, height=420,
            ),
            actions=[ft.TextButton("Fermer", on_click=fermer)],
        )
        self.page.show_dialog(dlg)

    # ── Import FFESSM ─────────────────────────────────────────────────────

    async def _on_import_ffessm(self, e):
        # Réutilise le FilePicker unique créé au démarrage
        files = await self.file_picker.pick_files(
            dialog_title="Sélectionner le fichier FFESSM (XLSX ou CSV)",
            allowed_extensions=["xlsx", "csv", "txt"],
        )
        if not files:
            return
        path = files[0].path
        self._do_import_ffessm(path)

    def _do_import_ffessm(self, path: str):
        dlg_prog = ft.AlertDialog(
            title=ft.Text("Import en cours…"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Lecture du fichier FFESSM…"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            modal=True,
        )
        self.page.show_dialog(dlg_prog)

        def do():
            plongeurs, err = import_xlsx_ffessm_data(path)
            if err:
                self.page.pop_dialog()
                self._show_snack(f"Erreur : {err}", erreur=True)
                return

            nb_total = len(plongeurs)
            upsert_plongeurs_batch(plongeurs)

            # Recharger UNIQUEMENT ce qui est visible (onglet Plongeurs).
            # Les autres onglets seront rafraîchis automatiquement au switch
            # via _on_nav_change.
            self.plongeurs = load_plongeurs()
            self._refresh_liste_plongeurs(
                self.search_field.value if hasattr(self, "search_field") else ""
            )

            self.page.pop_dialog()
            try:
                self.page.update()
            except Exception:
                pass
            self._show_snack(
                f"Import terminé — {nb_total} plongeur(s) traité(s)."
            )

        threading.Thread(target=do, daemon=True).start()

    # ── Vider la base des membres ─────────────────────────────────────────

    def _on_vider_plongeurs(self, e):
        """Confirmation puis vidage de la table plongeurs (garde messages)."""
        nb = len(self.plongeurs)
        if nb == 0:
            self._show_snack("La base est déjà vide.")
            return

        def confirmer(_):
            self.page.pop_dialog()
            truncate_plongeurs()
            self.plongeurs = []
            self._refresh_liste_plongeurs("")
            try:
                self.page.update()
            except Exception:
                pass
            self._show_snack(f"{nb} plongeur(s) supprimé(s). Historique conservé.")

        def annuler(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("Vider la base des membres"),
            content=ft.Text(
                f"Supprimer définitivement les {nb} plongeur(s) de la base ?\n\n"
                "L'historique des messages envoyés sera conservé."
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Supprimer", on_click=confirmer,
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_suppression_totale(self, e):
        """Double confirmation puis suppression de TOUTES les données."""
        def annuler(_):
            self.page.pop_dialog()

        # 2e confirmation
        def confirmer_2(_):
            self.page.pop_dialog()
            truncate_all_data()
            self.plongeurs = []
            self.groupes_filtres = []
            self.pj_path = ""
            # Refresh tous les onglets
            self._refresh_liste_plongeurs("")
            self._refresh_commissions_chips()
            self._refresh_historique()
            self._load_params_fields()
            try:
                self.page.update()
            except Exception:
                pass
            self._show_snack("Toutes les données ont été supprimées.")

        # 1re confirmation
        def confirmer_1(_):
            self.page.pop_dialog()
            dlg2 = ft.AlertDialog(
                title=ft.Text("⚠ Confirmation finale", color=ft.Colors.RED_700),
                content=ft.Text(
                    "Cette action est IRRÉVERSIBLE.\n\n"
                    "Toutes les données seront supprimées :\n"
                    "  • plongeurs\n"
                    "  • historique des messages\n"
                    "  • paramètres du club\n\n"
                    "Êtes-vous absolument certain(e) ?"
                ),
                actions=[
                    ft.TextButton("Annuler", on_click=annuler),
                    ft.FilledButton("Oui, tout supprimer", on_click=confirmer_2,
                                    bgcolor=ft.Colors.RED_900,
                                    color=ft.Colors.WHITE),
                ],
            )
            self.page.show_dialog(dlg2)

        dlg1 = ft.AlertDialog(
            title=ft.Text("Suppression totale des données"),
            content=ft.Text(
                "Vous êtes sur le point de supprimer TOUTES les données "
                "de l'application : plongeurs, historique des messages et "
                "paramètres du club.\n\n"
                "Cette action est définitive."
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Continuer", on_click=confirmer_1,
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg1)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 2 — Composer un message
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_composer(self):
        # ── Filtres ───────────────────────────────────────────────────────
        # Canal : RadioGroup au lieu de Dropdown (on_change ne fonctionne pas
        # sur Dropdown en Flet 0.85)
        self.dd_canal = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="email", label="Email"),
                ft.Radio(value="sms",   label="SMS  (uniquement pour un club)"),
            ]),
            value="email",
            on_change=self._on_canal_change,
        )

        # Groupes de filtres commission : liste de listes d'items
        # Chaque groupe = OR interne, ET entre groupes
        # item = {"commission": nom, "mode": "tous_avec"|"selection"|"tous_sans",
        #         "brevets": [brevets_exacts] (vide sauf en mode selection)}
        self.groupes_filtres: list = []

        # Règle pour ajouter la PROCHAINE commission ("OU" ou "ET")
        self.regle_courante: str = "OU"

        # Affichage de l'expression logique (chips colorées)
        self.commissions_chips_row = ft.Row(wrap=True, spacing=4,
                                            run_spacing=4,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER)
        # Container avec les 12 boutons des commissions
        self.commissions_grid = ft.Column(spacing=4)
        # Boutons de règle OU/ET
        self.rule_buttons_row = ft.Row(spacing=8)

        self.tf_age_min = ft.TextField(
            label="Âge min", width=90, dense=True, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filtre_change,
        )
        self.tf_age_max = ft.TextField(
            label="Âge max", width=90, dense=True, keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filtre_change,
        )

        self.cb_caci = {}
        for statut in [STATUT_CACI_VALIDE, STATUT_CACI_ALERTE, STATUT_CACI_PERIME]:
            cb = ft.Checkbox(label=statut, value=False, on_change=self._on_filtre_change)
            self.cb_caci[statut] = cb

        # Type de licence
        self.cb_type_licence = {}
        for typ in ["Pratiquant", "Aidant"]:
            cb = ft.Checkbox(label=typ, value=False, on_change=self._on_filtre_change)
            self.cb_type_licence[typ] = cb

        # Catégorie
        self.cb_categorie = {}
        for cat in ["Enfant", "Jeune", "Adulte"]:
            cb = ft.Checkbox(label=cat, value=False, on_change=self._on_filtre_change)
            self.cb_categorie[cat] = cb

        # ── Message ───────────────────────────────────────────────────────
        self.tf_sujet = ft.TextField(
            label="Sujet / objet",
            dense=True,
            visible=True,
        )
        self.tf_corps = ft.TextField(
            label="Corps du message",
            multiline=True,
            min_lines=5,
            max_lines=10,
        )

        self.btn_pj = ft.FilledButton(
            "Pièce jointe",
            icon=ft.Icons.ATTACH_FILE,
            on_click=self._on_choisir_pj,
        )
        self.lbl_pj = ft.Text("", size=11, color=ft.Colors.GREY_600)
        self.pj_path = ""

        # ── Destinataires prévisualisation ────────────────────────────────
        self.lbl_nb_dest = ft.Text("0 destinataire(s)", size=13,
                                   weight=ft.FontWeight.BOLD)
        self.liste_dest_preview = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            height=150,
            spacing=2,
        )

        self.btn_envoyer = ft.FilledButton(
            "Envoyer",
            icon=ft.Icons.SEND,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            on_click=self._on_envoyer,
        )

        # Construit la grille des commissions
        self._build_commissions_grid()
        self._build_rule_buttons()

        filtres_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Filtres", weight=ft.FontWeight.BOLD, size=14),
                    self.dd_canal,
                    ft.Text("Filtres commission actifs", size=12, color=ft.Colors.GREY_700),
                    self.commissions_chips_row,
                    ft.Text("Ajouter une règle", size=12, color=ft.Colors.GREY_700),
                    self.rule_buttons_row,
                    ft.Text("Ajouter une commission", size=12, color=ft.Colors.GREY_700),
                    self.commissions_grid,
                    ft.Text("Type de licence", size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_type_licence["Pratiquant"],
                        self.cb_type_licence["Aidant"],
                    ], spacing=8),
                    ft.Text("Catégorie", size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_categorie["Enfant"],
                        self.cb_categorie["Jeune"],
                        self.cb_categorie["Adulte"],
                    ], spacing=8),
                    ft.Text("Âge", size=12, color=ft.Colors.GREY_700),
                    ft.Row([self.tf_age_min, self.tf_age_max], spacing=8),
                    ft.Text("Statut CACI", size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_caci[STATUT_CACI_VALIDE],
                        self.cb_caci[STATUT_CACI_ALERTE],
                        self.cb_caci[STATUT_CACI_PERIME],
                    ], spacing=8),
                ], spacing=6),
                padding=12,
            ),
        )

        dest_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        self.lbl_nb_dest,
                        ft.Row([
                            ft.TextButton(
                                "Actualiser",
                                icon=ft.Icons.REFRESH,
                                on_click=lambda _: self._actualiser_destinataires(),
                            ),
                            ft.TextButton(
                                "Export CSV",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                on_click=self._export_csv_destinataires,
                            ),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.liste_dest_preview,
                ], spacing=4),
                padding=12,
            ),
        )

        message_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Message", weight=ft.FontWeight.BOLD, size=14),
                    self.tf_sujet,
                    self.tf_corps,
                    ft.Row([self.btn_pj, self.lbl_pj]),
                    ft.Row([self.btn_envoyer],
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=8),
                padding=12,
            ),
        )

        return ft.Container(
            content=ft.Column([
                filtres_section,
                dest_section,
                message_section,
            ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True),
            padding=8,
            expand=True,
        )

    def _on_canal_change(self, e):
        canal = self.dd_canal.value
        self.tf_sujet.visible = (canal == "email")
        self.btn_pj.visible   = (canal == "email")
        self.lbl_pj.visible   = (canal == "email")
        self._safe_update(self.tf_sujet)
        self._safe_update(self.btn_pj)
        self._safe_update(self.lbl_pj)
        self._actualiser_destinataires()

    def _on_filtre_change(self, e):
        self._actualiser_destinataires()

    def _build_filtres(self) -> dict:
        statuts = [s for s, cb in self.cb_caci.items() if cb.value]
        types_licence = [t for t, cb in self.cb_type_licence.items() if cb.value]
        categories    = [c for c, cb in self.cb_categorie.items() if cb.value]

        def to_int(tf):
            try:
                return int(tf.value.strip())
            except Exception:
                return None

        canal = self.dd_canal.value or "email"
        return {
            "groupes_filtres": [list(g) for g in self.groupes_filtres],
            "types_licence": types_licence,
            "categories":    categories,
            "age_min":       to_int(self.tf_age_min),
            "age_max":       to_int(self.tf_age_max),
            "statuts_caci":  statuts,
            "avec_email":    (canal == "email"),
            "avec_portable": (canal == "sms"),
        }

    # ── Groupes de filtres : helpers ──────────────────────────────────────

    def _find_item_in_groupes(self, commission_nom: str):
        """Retourne l'item commission, ou None s'il n'existe pas."""
        for grp in self.groupes_filtres:
            for it in grp:
                if it.get("commission") == commission_nom:
                    return it
        return None

    def _remove_commission_from_groupes(self, commission_nom: str):
        """Retire toutes les occurrences de cette commission, nettoie les groupes vides."""
        for grp in self.groupes_filtres:
            grp[:] = [it for it in grp if it.get("commission") != commission_nom]
        self.groupes_filtres = [g for g in self.groupes_filtres if g]

    def _upsert_commission_in_groupes(self, item: dict):
        """Ajoute (ou met à jour) un item selon self.regle_courante.
        Retire d'abord toute occurrence existante, puis insère :
        - OU : ajoute au dernier groupe (ou crée si aucun)
        - ET : crée un nouveau groupe
        """
        commission_nom = item["commission"]
        self._remove_commission_from_groupes(commission_nom)

        if not self.groupes_filtres:
            self.groupes_filtres = [[item]]
        elif self.regle_courante == "OU":
            self.groupes_filtres[-1].append(item)
        else:  # ET
            self.groupes_filtres.append([item])

    # ── Commissions : grille, popup, chips ────────────────────────────────

    def _build_rule_buttons(self):
        """Construit les 2 boutons 'OU' et 'ET' (l'actif en bleu, l'inactif en gris)."""
        self.rule_buttons_row.controls.clear()
        for op in ("OU", "ET"):
            actif = (self.regle_courante == op)
            bgcolor = ft.Colors.BLUE_700 if actif else ft.Colors.GREY_200
            txtcolor = ft.Colors.WHITE if actif else ft.Colors.GREY_800
            self.rule_buttons_row.controls.append(
                ft.Container(
                    content=ft.Text(op, size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=txtcolor,
                                    text_align=ft.TextAlign.CENTER),
                    bgcolor=bgcolor,
                    border_radius=6,
                    padding=ft.Padding(left=18, right=18, top=6, bottom=6),
                    on_click=lambda _, o=op: self._on_rule_change(o),
                    ink=True,
                )
            )

    def _on_rule_change(self, op: str):
        """Bascule sur la règle 'ET' ou 'OU' pour la prochaine commission ajoutée."""
        self.regle_courante = op
        self._build_rule_buttons()
        self._safe_update(self.rule_buttons_row)

    def _build_commissions_grid(self):
        """Construit les sections de filtres (Commissions / Transversaux / Secourisme).
        Chaque section : titre + grille 2-par-ligne. Les filtres sans liste sont
        affichés en grisé et non cliquables."""
        self.commissions_grid.controls.clear()

        for titre_section, filtres in SECTIONS_FILTRES:
            # Titre de section
            self.commissions_grid.controls.append(
                ft.Text(titre_section, size=11,
                        color=ft.Colors.GREY_700,
                        weight=ft.FontWeight.BOLD)
            )
            # Grille 2-par-ligne
            couples = [filtres[i:i+2] for i in range(0, len(filtres), 2)]
            for couple in couples:
                row_ctrls = []
                for nom, liste in couple:
                    actif = bool(liste)
                    if actif:
                        bgcolor   = ft.Colors.BLUE_50
                        border    = ft.Border.all(1, ft.Colors.BLUE_200)
                        txt_color = ft.Colors.BLACK87
                        handler   = (lambda _, n=nom: self._open_commission_popup(n))
                    else:
                        bgcolor   = ft.Colors.GREY_100
                        border    = ft.Border.all(1, ft.Colors.GREY_300)
                        txt_color = ft.Colors.GREY_500
                        handler   = None
                    row_ctrls.append(
                        ft.Container(
                            content=ft.Text(nom, size=11,
                                            color=txt_color,
                                            text_align=ft.TextAlign.CENTER),
                            bgcolor=bgcolor,
                            border=border,
                            border_radius=6,
                            padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                            expand=True,
                            on_click=handler,
                            ink=actif,
                        )
                    )
                # Si seul élément dans la dernière ligne, ajouter un spacer
                if len(row_ctrls) == 1:
                    row_ctrls.append(ft.Container(expand=True))
                self.commissions_grid.controls.append(
                    ft.Row(row_ctrls, spacing=4)
                )
            # Espace avant la prochaine section
            self.commissions_grid.controls.append(ft.Container(height=4))

    def _brevets_commission_dans_club(self, commission_nom: str) -> list:
        """Retourne la liste triée et dédupliquée des brevets de cette commission
        effectivement présents dans le club. Tri alphabétique par code court."""
        seen = set()
        for p in self.plongeurs:
            brevets = brevets_d_une_commission(p.get("brevets_brut", ""), commission_nom)
            seen.update(brevets)
        return sorted(seen, key=lambda b: (brevet_court(b).lower(), b.lower()))

    def _open_commission_popup(self, commission_nom: str):
        """Popup : choix du mode (tous_avec / selection / tous_sans) + liste des brevets."""
        brevets_dispo = self._brevets_commission_dans_club(commission_nom)
        existing = self._find_item_in_groupes(commission_nom)

        # Mode initial
        if existing is None:
            mode_initial = "tous_avec"
            brevets_pre  = []
        else:
            mode_initial = existing.get("mode", "tous_avec")
            brevets_pre  = list(existing.get("brevets", []))

        # Cas particulier : pas de brevet dans le club pour cette commission.
        # Le mode "tous_sans" reste pertinent (tous les plongeurs sont concernés)
        # mais les autres modes n'ont pas de sens.
        no_brevets = (not brevets_dispo)

        # Checkboxes
        cbs = {}
        cb_rows = []
        for b in brevets_dispo:
            court = brevet_court(b)
            if court != b:
                label = f"{court}  —  {b}"
            else:
                label = b
            valeur_init = (b in brevets_pre)
            cb = ft.Checkbox(value=valeur_init)
            cbs[b] = cb
            cb_rows.append(
                ft.Row([
                    cb,
                    ft.Text(label, size=12, expand=True,
                            no_wrap=False, max_lines=2),
                ], spacing=4,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        cbs_column = ft.Column(cb_rows, spacing=2, scroll=ft.ScrollMode.AUTO)
        cbs_column.visible = (mode_initial == "selection")

        def tout_cocher(_):
            for cb in cbs.values():
                cb.value = True
                self._safe_update(cb)

        def tout_decocher(_):
            for cb in cbs.values():
                cb.value = False
                self._safe_update(cb)

        actions_selection = ft.Row([
            ft.TextButton("Tout cocher",   icon=ft.Icons.CHECK_BOX, on_click=tout_cocher),
            ft.TextButton("Tout décocher", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK, on_click=tout_decocher),
        ], spacing=4)
        actions_selection.visible = (mode_initial == "selection")

        # RadioGroup : 3 modes
        def on_mode_change(e):
            mode = radio_mode.value
            cbs_column.visible        = (mode == "selection")
            actions_selection.visible = (mode == "selection")
            self._safe_update(cbs_column)
            self._safe_update(actions_selection)

        # Construction des Radio (désactiver "tous_avec"/"selection" si pas de brevet)
        radios = []
        radios.append(ft.Radio(
            value="tous_avec",
            label=f"Tous les membres ({len(brevets_dispo)} brevet(s))",
            disabled=no_brevets,
        ))
        radios.append(ft.Radio(
            value="selection",
            label="Sélection précise de brevet(s)",
            disabled=no_brevets,
        ))
        radios.append(ft.Radio(
            value="tous_sans",
            label="Tous les membres SANS brevet",
        ))

        radio_mode = ft.RadioGroup(
            content=ft.Column(radios, spacing=0),
            value=mode_initial if not (no_brevets and mode_initial != "tous_sans") else "tous_sans",
            on_change=on_mode_change,
        )

        def annuler(_):
            self.page.pop_dialog()

        def valider(_):
            mode = radio_mode.value
            if mode == "selection":
                selectes = [b for b, cb in cbs.items() if cb.value]
                if not selectes:
                    # Rien coché → on retire le filtre
                    self._remove_commission_from_groupes(commission_nom)
                    self.page.pop_dialog()
                    self._refresh_commissions_chips()
                    self._actualiser_destinataires()
                    return
                item = {"commission": commission_nom, "mode": "selection",
                        "brevets": selectes}
            elif mode == "tous_sans":
                item = {"commission": commission_nom, "mode": "tous_sans",
                        "brevets": []}
            else:  # tous_avec
                item = {"commission": commission_nom, "mode": "tous_avec",
                        "brevets": []}

            self._upsert_commission_in_groupes(item)
            self.page.pop_dialog()
            self._refresh_commissions_chips()
            self._actualiser_destinataires()

        def retirer(_):
            self._remove_commission_from_groupes(commission_nom)
            self.page.pop_dialog()
            self._refresh_commissions_chips()
            self._actualiser_destinataires()

        boutons = [
            ft.TextButton("Annuler", on_click=annuler),
            ft.FilledButton("Valider", on_click=valider,
                            bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE),
        ]
        if existing is not None:
            boutons.insert(0, ft.TextButton(
                "Retirer le filtre", on_click=retirer,
                style=ft.ButtonStyle(color=ft.Colors.RED),
            ))

        dlg = ft.AlertDialog(
            title=ft.Text(commission_nom, size=14),
            content=ft.Container(
                content=ft.Column([
                    radio_mode,
                    ft.Divider(height=8),
                    actions_selection,
                    cbs_column,
                ], scroll=ft.ScrollMode.AUTO, spacing=4),
                width=360, height=440,
            ),
            actions=boutons,
        )
        self.page.show_dialog(dlg)

    def _chip_for_item(self, item: dict) -> ft.Control:
        """Construit le chip visuel pour un item commission."""
        nom = item["commission"]
        mode = item.get("mode", "tous_avec")
        brevets = item.get("brevets", [])

        # Couleur selon le mode
        if mode == "tous_sans":
            bg = ft.Colors.RED_700
            icon = ft.Icons.BLOCK
        elif mode == "selection":
            bg = ft.Colors.INDIGO_700
            icon = ft.Icons.CHECKLIST
        else:
            bg = ft.Colors.BLUE_700
            icon = ft.Icons.CHECK

        # Label : nom + qualificatif
        if mode == "selection" and brevets:
            label = f"{nom} ({len(brevets)})"
        elif mode == "tous_sans":
            label = f"sans {nom}"
        else:
            label = nom

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=12, color=ft.Colors.WHITE),
                ft.Text(label, size=11, color=ft.Colors.WHITE),
            ], spacing=4, tight=True),
            bgcolor=bg,
            border_radius=12,
            padding=ft.Padding(left=8, right=10, top=4, bottom=4),
            on_click=lambda _, n=nom: self._open_commission_popup(n),
            ink=True,
        )

    def _refresh_commissions_chips(self):
        """Met à jour l'affichage des groupes de filtres avec leurs opérateurs.
        Plusieurs groupes → des parenthèses encadrent les groupes ayant
        plusieurs items, pour rendre la priorité explicite."""
        self.commissions_chips_row.controls.clear()

        if not self.groupes_filtres:
            self.commissions_chips_row.controls.append(
                ft.Text("(aucun — tous les plongeurs)", size=11,
                        italic=True, color=ft.Colors.GREY_500)
            )
        else:
            multi_groupes = len(self.groupes_filtres) > 1
            for idx_g, grp in enumerate(self.groupes_filtres):
                # ET séparateur entre groupes
                if idx_g > 0:
                    self.commissions_chips_row.controls.append(
                        ft.Container(
                            content=ft.Text("ET", size=12,
                                            color=ft.Colors.GREY_800,
                                            weight=ft.FontWeight.BOLD),
                            padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                        )
                    )

                # Parenthèses si plusieurs groupes ET le groupe a plusieurs items
                paren = multi_groupes and len(grp) > 1
                if paren:
                    self.commissions_chips_row.controls.append(
                        ft.Text("(", size=14, color=ft.Colors.GREY_800,
                                weight=ft.FontWeight.BOLD)
                    )
                for idx_i, item in enumerate(grp):
                    if idx_i > 0:
                        self.commissions_chips_row.controls.append(
                            ft.Container(
                                content=ft.Text("OU", size=11,
                                                color=ft.Colors.GREY_700),
                                padding=ft.Padding(left=2, right=2, top=2, bottom=2),
                            )
                        )
                    self.commissions_chips_row.controls.append(self._chip_for_item(item))
                if paren:
                    self.commissions_chips_row.controls.append(
                        ft.Text(")", size=14, color=ft.Colors.GREY_800,
                                weight=ft.FontWeight.BOLD)
                    )

        self._safe_update(self.commissions_chips_row)

    def _actualiser_destinataires(self):
        # S'assurer que les chips reflètent l'état courant
        if hasattr(self, "commissions_chips_row"):
            self._refresh_commissions_chips()
        filtres = self._build_filtres()
        self.filtres_actifs = filtres
        dest = appliquer_filtres(self.plongeurs, filtres)
        self.destinataires_selectionnes = dest

        self.lbl_nb_dest.value = f"{len(dest)} destinataire(s)"
        self.liste_dest_preview.controls.clear()
        for p in dest[:50]:
            statut, coul = calcul_statut_caci(p.get("date_fin_caci", ""))
            self.liste_dest_preview.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(
                            f"{p['nom']} {p['prenom']}",
                            size=12, expand=True,
                        ),
                        ft.Text(
                            p.get("email") or p.get("portable") or "—",
                            size=11, color=ft.Colors.GREY_600,
                        ),
                    ]),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=4,
                    padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                )
            )
        if len(dest) > 50:
            self.liste_dest_preview.controls.append(
                ft.Text(f"…et {len(dest)-50} autre(s)", size=11,
                        color=ft.Colors.GREY_500)
            )
        self._safe_update(self.lbl_nb_dest)
        self._safe_update(self.liste_dest_preview)

    async def _on_choisir_pj(self, e):
        # Réutilise le FilePicker unique créé au démarrage
        files = await self.file_picker.pick_files(
            dialog_title="Sélectionner une pièce jointe"
        )
        if files:
            self.pj_path = files[0].path
            self.lbl_pj.value = os.path.basename(self.pj_path)
            self._safe_update(self.lbl_pj)

    # ── Export CSV ───────────────────────────────────────────────────────

    def _brevets_filtres_du_plongeur(self, p: dict) -> list:
        """Retourne la liste des brevets (codes courts) du plongeur qui ont
        permis de passer les filtres commission.
        - Pour chaque item commission active dans les groupes :
            * mode "tous_avec" : tous les brevets du plongeur dans cette commission
            * mode "selection" : ceux du plongeur ∩ ceux cochés
            * mode "tous_sans" : rien (la commission est une condition de négation)
        - Si aucun groupe : tous les brevets simplifiés du plongeur
        """
        groupes = self.filtres_actifs.get("groupes_filtres") or []
        brevets_brut = p.get("brevets_brut", "")
        brevets_courts = []

        if groupes:
            for grp in groupes:
                for item in grp:
                    mode = item.get("mode", "tous_avec")
                    if mode == "tous_sans":
                        continue
                    nom_com = item.get("commission", "")
                    brevets_dans_com = brevets_d_une_commission(brevets_brut, nom_com)
                    if not brevets_dans_com:
                        continue
                    if mode == "selection":
                        cibles = [b for b in brevets_dans_com
                                  if b in item.get("brevets", [])]
                    else:  # tous_avec
                        cibles = brevets_dans_com
                    brevets_courts.extend(brevet_court(b) for b in cibles)
        else:
            # Aucun filtre commission → tous les brevets du plongeur
            for _, court in parse_brevets(brevets_brut):
                brevets_courts.append(court)

        # Dédupliquer en conservant l'ordre
        return list(dict.fromkeys(brevets_courts))

    async def _export_csv_destinataires(self, e):
        """Exporte la liste filtrée actuelle des destinataires au format CSV."""
        dest = self.destinataires_selectionnes
        if not dest:
            self._show_snack("Aucun destinataire à exporter.", erreur=True)
            return

        # Préparer les données
        rows = []
        for p in dest:
            brevets_filtres = self._brevets_filtres_du_plongeur(p)
            rows.append([
                p.get("nom", ""),
                p.get("prenom", ""),
                ", ".join(brevets_filtres),
                p.get("nom_club", ""),
                p.get("email", ""),
            ])

        # Nom de fichier suggéré
        nom_club_court = get_param("nom_club_court") or "club"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{nom_club_court}_{date_str}.csv"

        # Ouverture du dialogue "save_file" via le FilePicker partagé
        try:
            target = await self.file_picker.save_file(
                dialog_title="Exporter en CSV",
                file_name=filename,
                allowed_extensions=["csv"],
            )
        except Exception as err:
            self._show_snack(f"Erreur ouverture sélecteur : {err}", erreur=True)
            return

        if not target:
            return  # annulé par l'utilisateur

        # Écriture du fichier
        try:
            with open(target, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["Nom", "Prénom", "Brevets", "Club ou OD", "Email"])
                writer.writerows(rows)
            self._show_snack(f"Export terminé : {len(rows)} ligne(s) → {os.path.basename(target)}")
        except Exception as err:
            self._show_snack(f"Erreur écriture fichier : {err}", erreur=True)

    # ── Envoi ─────────────────────────────────────────────────────────────

    def _on_envoyer(self, e):
        dest = self.destinataires_selectionnes
        if not dest:
            self._show_snack("Aucun destinataire correspondant aux filtres.", erreur=True)
            return

        canal  = self.dd_canal.value or "email"
        sujet  = self.tf_sujet.value.strip()
        corps  = self.tf_corps.value.strip()

        if canal == "email" and not sujet:
            self._show_snack("Veuillez saisir un sujet.", erreur=True)
            return
        if not corps:
            self._show_snack("Veuillez saisir le corps du message.", erreur=True)
            return

        nb_email = sum(1 for p in dest if p.get("email"))
        nb_sms   = sum(1 for p in dest if p.get("portable"))

        detail = f"{nb_email} email(s)" if canal == "email" else f"{nb_sms} SMS"
        self._confirm_envoi(
            f"Envoyer {detail} à {len(dest)} destinataire(s) ?",
            canal, sujet, corps,
        )

    def _confirm_envoi(self, message, canal, sujet, corps):
        def on_ok(_):
            self.page.pop_dialog()
            self._executer_envoi(canal, sujet, corps)

        def on_cancel(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmer l'envoi"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("Annuler", on_click=on_cancel),
                ft.FilledButton("Envoyer", on_click=on_ok,
                                  color=ft.Colors.WHITE)
            ],
        )
        self.page.show_dialog(dlg)

    def _executer_envoi(self, canal, sujet, corps):
        prog = ft.AlertDialog(
            title=ft.Text("Envoi en cours…"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Envoi des messages…"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            modal=True,
        )
        self.page.show_dialog(prog)

        def do():
            nb_ok = nb_err = 0
            dest = self.destinataires_selectionnes

            if canal == "email":
                smtp_host = get_param("smtp_host")
                smtp_port = int(get_param("smtp_port") or 587)
                smtp_user = get_param("smtp_user")
                smtp_pwd  = get_param("smtp_password")
                use_tls   = get_param("smtp_tls") == "1"
                expediteur = get_param("email_expediteur") or smtp_user

                for p in dest:
                    email = p.get("email", "").strip()
                    if not email:
                        continue
                    ok, err = envoyer_email(
                        email, sujet, corps, self.pj_path,
                        smtp_host, smtp_port, smtp_user, smtp_pwd,
                        use_tls, expediteur,
                    )
                    if ok:
                        nb_ok += 1
                    else:
                        nb_err += 1
                        print(f"Erreur envoi {email} : {err}")
            else:
                # SMS via l'app native du téléphone (URL sms:)
                # Nettoyage des numéros : retirer espaces, points, tirets, parenthèses
                import re as _re
                import urllib.parse as _urlparse
                numeros = []
                for p in dest:
                    portable = p.get("portable", "").strip()
                    if not portable:
                        continue
                    # Nettoyer : ne garder que chiffres et + initial
                    num_clean = _re.sub(r'[^\d+]', '', portable)
                    if num_clean:
                        numeros.append(num_clean)

                if not numeros:
                    nb_err = len(dest)
                else:
                    nums_str = ",".join(numeros)
                    body_enc = _urlparse.quote(corps)
                    url = f"sms:{nums_str}?body={body_enc}"
                    try:
                        self.page.launch_url(url)
                        nb_ok = len(numeros)
                    except Exception as err:
                        print(f"Erreur lancement SMS : {err}")
                        nb_err = len(numeros)

            dest_ids = [p.get("id_licence", "") for p in dest]
            save_message_historique(
                canal, sujet, corps, self.filtres_actifs, dest_ids, nb_ok, nb_err
            )

            self.page.pop_dialog()
            self._show_snack(
                f"Envoi terminé — {nb_ok} envoyé(s), {nb_err} erreur(s)."
            )

        threading.Thread(target=do, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────
    # TAB 3 — Historique
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_historique(self):
        self.historique_col = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=6,
        )
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("Historique des envois",
                                size=18, weight=ft.FontWeight.BOLD),
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Actualiser",
                            on_click=lambda _: self._refresh_historique(),
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=12,
                    bgcolor=ft.Colors.WHITE,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=self.historique_col,
                    expand=True,
                    padding=8,
                ),
            ], spacing=0),
            expand=True,
        )

    def _refresh_historique(self):
        rows = load_historique()
        self.historique_col.controls.clear()
        if not rows:
            self.historique_col.controls.append(
                ft.Text("Aucun envoi enregistré.", color=ft.Colors.GREY_500)
            )
        for r in rows:
            id_, date_e, canal, sujet, nb_ok, nb_err, filtre_j, dest_j, corps = r
            try:
                nb_dest = len(json.loads(dest_j))
            except Exception:
                nb_dest = 0
            self.historique_col.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(date_e, size=11, color=ft.Colors.GREY_600),
                                ft.Container(
                                    content=ft.Text(canal.upper(), size=10,
                                                    color=ft.Colors.WHITE),
                                    bgcolor=(ft.Colors.BLUE_600
                                             if canal == "email"
                                             else ft.Colors.GREEN_600),
                                    border_radius=4,
                                    padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                ),
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(sujet or corps[:60], size=13,
                                    weight=ft.FontWeight.BOLD),
                            ft.Text(
                                f"{nb_dest} destinataire(s)  •  "
                                f"{nb_ok} envoyé(s)  •  {nb_err} erreur(s)",
                                size=12, color=ft.Colors.GREY_700,
                            ),
                        ], spacing=4),
                        padding=10,
                    ),
                )
            )
        self._safe_update(self.historique_col)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 4 — Paramètres
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_parametres(self):
        params_fields = {
            "nom_club_court":  ft.TextField(label="Nom court du club ou OD",   dense=True),
            "nom_club_long":   ft.TextField(label="Nom complet du club ou OD", dense=True),
            "email_expediteur":ft.TextField(label="Email expéditeur",      dense=True, keyboard_type=ft.KeyboardType.EMAIL),
            "smtp_host":       ft.TextField(label="Serveur SMTP (host)",   dense=True),
            "smtp_port":       ft.TextField(label="Port SMTP",             dense=True, keyboard_type=ft.KeyboardType.NUMBER),
            "smtp_user":       ft.TextField(label="Utilisateur SMTP",      dense=True),
            "smtp_password":   ft.TextField(label="Mot de passe SMTP",     dense=True, password=True, can_reveal_password=True),
        }
        self.params_fields = params_fields

        def sauvegarder(_):
            for cle, tf in params_fields.items():
                set_param(cle, tf.value.strip())
            self._show_snack("Paramètres sauvegardés.")

        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Paramètres",
                                    size=18, weight=ft.FontWeight.BOLD),
                    padding=12,
                    bgcolor=ft.Colors.WHITE,
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Column([
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Club ou OD", weight=ft.FontWeight.BOLD),
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                            color=ft.Colors.BLUE_600),
                                    ft.Text(
                                        "OD = Organe Déconcentré (comité "
                                        "départemental ou régional, par exemple).",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True, no_wrap=False,
                                    ),
                                ], spacing=6),
                                params_fields["nom_club_court"],
                                params_fields["nom_club_long"],
                            ], spacing=8),
                            padding=12,
                        )),
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Email — SMTP", weight=ft.FontWeight.BOLD),
                                params_fields["email_expediteur"],
                                params_fields["smtp_host"],
                                params_fields["smtp_port"],
                                params_fields["smtp_user"],
                                params_fields["smtp_password"],
                            ], spacing=8),
                            padding=12,
                        )),
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("SMS", weight=ft.FontWeight.BOLD),
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                            color=ft.Colors.BLUE_600),
                                    ft.Text(
                                        "L'envoi de SMS utilise l'application "
                                        "SMS native du téléphone. Aucune "
                                        "configuration n'est nécessaire.",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True,
                                    ),
                                ], spacing=6),
                            ], spacing=8),
                            padding=12,
                        )),
                        ft.FilledButton(
                            "Sauvegarder",
                            icon=ft.Icons.SAVE,
                            bgcolor=ft.Colors.BLUE_700,
                            color=ft.Colors.WHITE,
                            on_click=sauvegarder,
                        ),
                        # ── Section Données (vider / supprimer) ───────────
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Données", weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.RED_700),
                                ft.Row([
                                    ft.Icon(ft.Icons.WARNING_AMBER, size=16,
                                            color=ft.Colors.ORANGE_700),
                                    ft.Text(
                                        "Ces actions sont définitives.",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True,
                                    ),
                                ], spacing=6),
                                ft.OutlinedButton(
                                    "Vider la base des membres",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    on_click=self._on_vider_plongeurs,
                                    style=ft.ButtonStyle(color=ft.Colors.RED_700),
                                ),
                                ft.Text(
                                    "Conserve l'historique des messages et "
                                    "les paramètres.",
                                    size=10, color=ft.Colors.GREY_600,
                                ),
                                ft.FilledButton(
                                    "Suppression totale des données",
                                    icon=ft.Icons.DELETE_FOREVER,
                                    on_click=self._on_suppression_totale,
                                    bgcolor=ft.Colors.RED_900,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    "Supprime plongeurs, historique et paramètres.",
                                    size=10, color=ft.Colors.GREY_600,
                                ),
                            ], spacing=8),
                            padding=12,
                        )),
                        ft.Text(
                            f"ClubMessenger v{VERSION}  —  fr.csdev.clubmessenger",
                            size=10, color=ft.Colors.GREY_500,
                        ),
                    ], spacing=10, scroll=ft.ScrollMode.AUTO),
                    padding=8,
                    expand=True,
                ),
            ], spacing=0),
            expand=True,
        )

    def _load_params_fields(self):
        for cle, tf in self.params_fields.items():
            tf.value = get_param(cle)
            self._safe_update(tf)

    # ──────────────────────────────────────────────────────────────────────
    # Chargement données
    # ──────────────────────────────────────────────────────────────────────

    def _load_data(self):
        self.plongeurs = load_plongeurs()
        self._refresh_liste_plongeurs(
            self.search_field.value if hasattr(self, "search_field") else ""
        )
        self._actualiser_destinataires()
        self._refresh_historique()
        if hasattr(self, "params_fields"):
            self._load_params_fields()
        # Rafraîchit la page courante (les autres seront affichées correctement
        # lors du switch via NavigationBar)
        try:
            self.page.update()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────
    # Helpers UI
    # ──────────────────────────────────────────────────────────────────────

    def _safe_update(self, ctrl):
        """Update défensif — ignore si le contrôle n'est pas encore monté."""
        try:
            ctrl.update()
        except (RuntimeError, AssertionError, AttributeError):
            pass

    def _show_snack(self, message, erreur=False):
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_700 if erreur else ft.Colors.GREEN_700,
            duration=3000,
        )
        self.page.show_dialog(snack)


# ──────────────────────────────────────────────────────────────────────────────
# Point d'entrée
# ──────────────────────────────────────────────────────────────────────────────

def main(page: ft.Page):
    init_db()
    ClubMessengerApp(page)


if __name__ == "__main__":
    ft.run(main)