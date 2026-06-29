"""
ClubMessenger Desktop v1.3.3
Variante Desktop (PC) de l'application Android ClubMessenger.

Cette version importe toute la logique métier de clubmessenger_core.py
(constantes FFESSM, DB SQLite, parseur XLSX, filtres, SMTP) et redéfinit
uniquement l'UI pour un écran de PC :
- NavigationRail à gauche (au lieu de NavigationBar en bas)
- Fenêtre 1280×800 par défaut, redimensionnable
- AlertDialog plus larges (700×720 pour la fiche plongeur)
- Pas de SafeArea (inutile sur desktop)
- Canal SMS désactivé (pas d'app SMS native sur PC)
- Layout 2 colonnes pour le Composer

Lancement : python main_desktop.py
"""

import os
import re
import sys
import json
import urllib.parse
import threading
import csv
from datetime import datetime

import flet as ft

# Toute la logique métier (constantes FFESSM, DB, parsing, filtres, SMTP…)
from clubmessenger_core import *  # noqa: F401,F403


def _resource_path(relative_path: str) -> str:
    """Résout le chemin d'une ressource embarquée.
    Compatible avec PyInstaller --onefile (les fichiers sont extraits dans
    un dossier temporaire référencé par sys._MEIPASS).
    En mode développement (.py lancé directement), utilise le dossier du script.
    """
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class ClubMessengerDesktopApp:
    """Variante Desktop de ClubMessengerApp.

    Différences principales avec la version Android :
    - NavigationRail à gauche au lieu de NavigationBar en bas
    - Fenêtre 1280×800 par défaut
    - Dialogues 1.6× plus larges
    - Canal SMS désactivé (pas d'app SMS native PC)
    - Pas de SafeArea
    """

    # Constantes UI desktop
    WIN_WIDTH       = 1280
    WIN_HEIGHT      = 800
    WIN_MIN_WIDTH   = 900
    WIN_MIN_HEIGHT  = 600
    CONTENT_MAX_W   = 1100   # largeur max du contenu (centré au-delà)
    DIALOG_W        = 600    # AlertDialog standard
    DIALOG_H        = 600
    DIALOG_W_LARGE  = 700    # AlertDialog fiche plongeur
    DIALOG_H_LARGE  = 720

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = f"{APP_TITLE} Desktop"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = ft.Colors.GREY_100
        self.page.padding = 0
        # Pas de SafeArea sur desktop (inutile : pas de notch)

        # Dimensions fenêtre
        try:
            if hasattr(page, "window"):
                self.page.window.width      = self.WIN_WIDTH
                self.page.window.height     = self.WIN_HEIGHT
                self.page.window.min_width  = self.WIN_MIN_WIDTH
                self.page.window.min_height = self.WIN_MIN_HEIGHT
                # Icône de la fenêtre (barre de titre + barre des tâches Windows)
                try:
                    icon_path = _resource_path("assets/ClubMessenger.ico")
                    if os.path.exists(icon_path):
                        self.page.window.icon = icon_path
                except Exception:
                    pass
                # window.center() est une coroutine en Flet 0.85, planifier via run_task
                _win = self.page.window
                async def _do_center():
                    try:
                        await _win.center()
                    except Exception:
                        pass
                try:
                    self.page.run_task(_do_center)
                except Exception:
                    pass
        except Exception:
            pass

        self.plongeurs: list = []
        self.filtres_actifs: dict = {}
        self.destinataires_selectionnes: list = []
        self.pj_path = ""

        # FilePicker unique
        self.file_picker = ft.FilePicker()
        try:
            self.page.services.append(self.file_picker)
        except Exception:
            try:
                self.page.overlay.append(self.file_picker)
            except Exception:
                pass

        self._build_ui()
        self._load_data()

    # ──────────────────────────────────────────────────────────────────────
    # Construction UI : NavigationRail à gauche + contenu à droite
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Construction des 4 pages
        self.page_plongeurs  = self._build_tab_plongeurs()
        self.page_composer   = self._build_tab_composer()
        self.page_historique = self._build_tab_historique()
        self.page_parametres = self._build_tab_parametres()

        # Container du contenu actif (centré avec largeur max)
        self.content_area = ft.Container(
            content=self.page_plongeurs,
            expand=True,
        )
        content_wrapper = ft.Container(
            content=self.content_area,
            expand=True,
            padding=ft.Padding(left=16, right=16, top=8, bottom=8),
        )

        # NavigationRail à gauche
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            extended=True,
            group_alignment=-0.9,  # vers le haut
            on_change=self._on_nav_change,
            leading=self._build_club_leading(),
            trailing=self._build_logo_trailing(),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE, label="Plongeurs"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEND, label="Composer"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY, label="Historique"),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS, label="Paramètres"),
            ],
        )

        # Layout principal : Row [NavRail | Divider | content]
        self.page.add(
            ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1),
                content_wrapper,
            ], expand=True, spacing=0)
        )

    def _build_club_leading(self):
        """Bouton 'leading' du NavigationRail : affiche le nom court du club
        configuré et ouvre un popup d'édition. Si le club n'est pas configuré,
        affiche un placeholder discret invitant à le faire.

        Renvoie une Column contenant deux boutons : identité du club + mode
        de rédaction (les deux gérés via popups)."""
        # ── Bouton identité club ──
        nom_court = (get_param("nom_club_court") or "").strip()
        label = nom_court if nom_court else "Configurer le club"

        self.lbl_club_leading = ft.Text(
            label,
            size=11,
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.BLUE_900 if nom_court else ft.Colors.GREY_600,
            weight=ft.FontWeight.BOLD if nom_court else ft.FontWeight.NORMAL,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        btn_club = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.APARTMENT, size=30, color=ft.Colors.BLUE_700),
                self.lbl_club_leading,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.Padding(left=8, right=8, top=14, bottom=14),
            margin=ft.Padding(left=8, right=8, top=8, bottom=4),
            border_radius=8,
            width=164,
            alignment=ft.Alignment.CENTER,
            on_click=lambda _: self._open_club_popup(),
            ink=True,
            tooltip="Modifier l'identité du club ou OD",
            bgcolor=ft.Colors.BLUE_100,
            border=ft.Border.all(1, ft.Colors.BLUE_300),
        )

        # ── Bouton mode de rédaction ──
        mode = get_param("mode_redaction") or "structure"
        if mode == "commission":
            commission = (get_param("commission_redaction") or "").strip()
            label_red = commission if commission else "Commission"
            color_red = ft.Colors.INDIGO_900 if commission else ft.Colors.GREY_600
            weight_red = ft.FontWeight.BOLD if commission else ft.FontWeight.NORMAL
        else:
            label_red = "Structure"
            color_red = ft.Colors.INDIGO_900
            weight_red = ft.FontWeight.BOLD

        self.lbl_redaction_leading = ft.Text(
            label_red,
            size=11,
            text_align=ft.TextAlign.CENTER,
            color=color_red,
            weight=weight_red,
            max_lines=2,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        btn_redaction = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.EDIT_NOTE, size=30,
                        color=ft.Colors.INDIGO_700),
                self.lbl_redaction_leading,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            padding=ft.Padding(left=8, right=8, top=14, bottom=14),
            margin=ft.Padding(left=8, right=8, top=4, bottom=8),
            border_radius=8,
            width=164,
            alignment=ft.Alignment.CENTER,
            on_click=lambda _: self._open_redaction_popup(),
            ink=True,
            tooltip="Mode de rédaction (sujet des mails)",
            bgcolor=ft.Colors.INDIGO_100,
            border=ft.Border.all(1, ft.Colors.INDIGO_300),
        )

        return ft.Column([btn_club, btn_redaction], spacing=0, tight=True)

    def _refresh_club_leading(self):
        """Met à jour le label sous l'icône du leading après modification."""
        if not hasattr(self, "lbl_club_leading"):
            return
        nom_court = (get_param("nom_club_court") or "").strip()
        self.lbl_club_leading.value = nom_court if nom_court else "Configurer le club"
        self.lbl_club_leading.color = (ft.Colors.BLUE_900 if nom_court
                                       else ft.Colors.GREY_600)
        self.lbl_club_leading.weight = (ft.FontWeight.BOLD if nom_court
                                        else ft.FontWeight.NORMAL)
        self._safe_update(self.lbl_club_leading)

    def _build_logo_trailing(self):
        """Pied de NavigationRail : logo de l'application + version.

        Cherche un fichier image dans plusieurs emplacements/noms candidats.
        Si aucun n'est trouvé, affiche seulement la version (pas d'erreur).
        """
        # Candidats par ordre de préférence (PNG d'abord, ICO en dernier recours)
        candidates = [
            "assets/clubmessenger_logo.png",
            "assets/ClubMessenger.png",
            "assets/logo.png",
            "assets/ClubMessenger.ico",
        ]

        logo_path = None
        for c in candidates:
            full = _resource_path(c)
            if os.path.exists(full):
                logo_path = full
                break

        children = []
        if logo_path:
            # Wrapper Container avec border_radius + clip_behavior pour
            # arrondir les coins de l'image (ft.Image n'a pas border_radius
            # directement).
            children.append(
                ft.Container(
                    content=ft.Image(
                        src=logo_path,
                        width=140,
                        height=140,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    width=140,
                    height=140,
                    border_radius=30,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                )
            )
        children.append(
            ft.Text(f"v{VERSION}",
                    size=10,
                    color=ft.Colors.GREY_500,
                    text_align=ft.TextAlign.CENTER)
        )
        # Texte cliquable « À propos » → ouvre le popup
        children.append(
            ft.TextButton(
                "À propos",
                icon=ft.Icons.INFO_OUTLINE,
                on_click=lambda _: self._open_about_popup(),
                style=ft.ButtonStyle(
                    color=ft.Colors.BLUE_700,
                    padding=ft.Padding(left=4, right=4, top=2, bottom=2),
                ),
            )
        )

        return ft.Container(
            content=ft.Column(
                children,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.Padding(left=8, right=8, top=12, bottom=16),
            width=164,
            alignment=ft.Alignment.CENTER,
        )

    def _open_about_popup(self):
        """Popup « À propos » : logo, nom, version, auteur, contact."""
        # Recherche du logo (mêmes candidats que _build_logo_trailing)
        candidates = [
            "assets/clubmessenger_logo.png",
            "assets/ClubMessenger.png",
            "assets/logo.png",
            "assets/ClubMessenger.ico",
        ]
        logo_path = None
        for c in candidates:
            full = _resource_path(c)
            if os.path.exists(full):
                logo_path = full
                break

        contenu = []
        if logo_path:
            contenu.append(
                ft.Container(
                    content=ft.Image(
                        src=logo_path,
                        width=140,
                        height=140,
                        fit=ft.BoxFit.CONTAIN,
                    ),
                    width=140,
                    height=140,
                    border_radius=30,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                )
            )
        contenu += [
            ft.Text(APP_TITLE, size=22, weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER),
            ft.Text(f"Version {VERSION}", size=14,
                    color=ft.Colors.GREY_700,
                    text_align=ft.TextAlign.CENTER),
            ft.Divider(height=12),
            ft.Text(
                "Messagerie ciblée pour clubs de plongée FFESSM.\n"
                "Envoyez emails et SMS à vos licenciés filtrés "
                "par expression booléenne (commissions, brevets, "
                "type de licence, âge, CACI…).",
                size=12, color=ft.Colors.GREY_800,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Divider(height=12),
            ft.Row([
                ft.Text("Auteur :", size=12, color=ft.Colors.GREY_600, width=80),
                ft.Text("CS-DEV (Cédric SALVAT)", size=12,
                        selectable=True, expand=True),
            ]),
            ft.Row([
                ft.Text("Bundle :", size=12, color=ft.Colors.GREY_600, width=80),
                ft.Text("fr.csdev.clubmessenger", size=12,
                        selectable=True, expand=True),
            ]),
            ft.Row([
                ft.Text("Licence :", size=12, color=ft.Colors.GREY_600, width=80),
                ft.Text("Propriétaire — Tous droits réservés",
                        size=12, selectable=True, expand=True),
            ]),
            ft.Container(height=8),
            ft.Text(
                "© 2026 — Application 100 % locale, aucune donnée "
                "transmise au développeur.",
                size=10, italic=True, color=ft.Colors.GREY_500,
                text_align=ft.TextAlign.CENTER,
            ),
        ]

        def fermer(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("À propos", size=16),
            content=ft.Container(
                content=ft.Column(
                    contenu,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=8,
                    tight=True,
                ),
                width=460,
                height=520,
            ),
            actions=[ft.TextButton("Fermer", on_click=fermer)],
        )
        self.page.show_dialog(dlg)

    def _refresh_redaction_leading(self):
        """Met à jour le label du bouton mode de rédaction après modification."""
        if not hasattr(self, "lbl_redaction_leading"):
            return
        mode = get_param("mode_redaction") or "structure"
        if mode == "commission":
            commission = (get_param("commission_redaction") or "").strip()
            if commission:
                self.lbl_redaction_leading.value = commission
                self.lbl_redaction_leading.color = ft.Colors.INDIGO_900
                self.lbl_redaction_leading.weight = ft.FontWeight.BOLD
            else:
                self.lbl_redaction_leading.value = "Commission"
                self.lbl_redaction_leading.color = ft.Colors.GREY_600
                self.lbl_redaction_leading.weight = ft.FontWeight.NORMAL
        else:
            self.lbl_redaction_leading.value = "Structure"
            self.lbl_redaction_leading.color = ft.Colors.INDIGO_900
            self.lbl_redaction_leading.weight = ft.FontWeight.BOLD
        self._safe_update(self.lbl_redaction_leading)

    def _open_club_popup(self):
        """Popup d'édition de l'identité du club ou OD (nom court + nom long)."""
        tf_court = ft.TextField(
            label="Nom court du club ou OD",
            dense=True,
            value=get_param("nom_club_court") or "",
            autofocus=True,
        )
        tf_long = ft.TextField(
            label="Nom complet du club ou OD",
            dense=True,
            value=get_param("nom_club_long") or "",
        )

        def annuler(_):
            self.page.pop_dialog()

        def sauvegarder(_):
            set_param("nom_club_court", (tf_court.value or "").strip())
            set_param("nom_club_long",  (tf_long.value or "").strip())
            self.page.pop_dialog()
            self._refresh_club_leading()
            self._show_snack("Identité du club enregistrée.")

        dlg = ft.AlertDialog(
            title=ft.Text("Identité du club ou OD"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                color=ft.Colors.BLUE_600),
                        ft.Text(
                            "OD = Organe Déconcentré (comité départemental "
                            "ou régional).",
                            size=12, color=ft.Colors.GREY_700,
                            expand=True, no_wrap=False),
                    ], spacing=6),
                    tf_court,
                    tf_long,
                ], spacing=14, tight=True),
                width=500,
                height=240,
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Enregistrer", on_click=sauvegarder,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _open_redaction_popup(self):
        """Popup d'édition du mode de rédaction : Switch structure/commission
        + Dropdown des commissions (visible uniquement en mode commission)."""
        mode_actuel = get_param("mode_redaction") or "structure"
        commission_actuelle = get_param("commission_redaction") or ""

        # Dropdown : commissions FFESSM + activités transversales
        all_options = (
            [ft.DropdownOption(text=nom) for nom, _ in COMMISSIONS_FFESSM]
            + [ft.DropdownOption(key="_separator_",
                                 text="─" * 24, disabled=True)]
            + [ft.DropdownOption(text=nom) for nom, _ in FILTRES_TRANSVERSAUX]
        )
        dd_commission = ft.Dropdown(
            label="Commission ou activité transversale",
            dense=True,
            options=all_options,
            value=commission_actuelle if commission_actuelle else None,
            visible=(mode_actuel == "commission"),
        )

        lbl_switch_mode = ft.Text(
            "Écrire en tant que commission" if mode_actuel == "commission"
            else "Écrire en tant que structure",
            size=13, weight=ft.FontWeight.BOLD, expand=True,
        )

        def on_switch_change(e):
            is_com = bool(e.control.value)
            lbl_switch_mode.value = ("Écrire en tant que commission" if is_com
                                     else "Écrire en tant que structure")
            dd_commission.visible = is_com
            self._safe_update(lbl_switch_mode)
            self._safe_update(dd_commission)

        switch_mode = ft.Switch(
            value=(mode_actuel == "commission"),
            on_change=on_switch_change,
            active_color=ft.Colors.INDIGO_700,
        )

        def annuler(_):
            self.page.pop_dialog()

        def sauvegarder(_):
            mode = "commission" if switch_mode.value else "structure"
            set_param("mode_redaction", mode)
            if mode == "commission":
                set_param("commission_redaction", dd_commission.value or "")
            else:
                set_param("commission_redaction", "")
            self.page.pop_dialog()
            self._refresh_redaction_leading()
            self._show_snack("Mode de rédaction enregistré.")

        dlg = ft.AlertDialog(
            title=ft.Text("Mode de rédaction"),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                color=ft.Colors.BLUE_600),
                        ft.Text(
                            "Détermine la formulation des sujets de mails. "
                            "« Structure » utilise le nom court du club/OD. "
                            "« Commission » ajoute la commission choisie.",
                            size=12, color=ft.Colors.GREY_700,
                            expand=True, no_wrap=False),
                    ], spacing=6),
                    ft.Row([lbl_switch_mode, switch_mode],
                           vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    dd_commission,
                ], spacing=14, tight=True),
                width=500,
                height=260,
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Enregistrer", on_click=sauvegarder,
                                bgcolor=ft.Colors.INDIGO_700,
                                color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_nav_change(self, e):
        idx = self.nav_rail.selected_index
        pages = [
            self.page_plongeurs,
            self.page_composer,
            self.page_historique,
            self.page_parametres,
        ]
        self.content_area.content = pages[idx]
        self._safe_update(self.content_area)
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
            expand=True,
        )
        self.liste_plongeurs_col = ft.ListView(
            expand=True,
            spacing=4,
            padding=0,
            cache_extent=400,
        )
        self.lbl_nb_plongeurs = ft.Text("", size=13, color=ft.Colors.GREY_600)

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
                # Header
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Plongeurs du club",
                                    size=20, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                btn_import,
                                btn_vider,
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    tooltip="Actualiser",
                                    on_click=lambda _: self._load_data(),
                                ),
                            ], spacing=8),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([
                            self.search_field,
                            ft.Container(width=12),
                            self.lbl_nb_plongeurs,
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ], spacing=12),
                    padding=16,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=8,
                ),
                ft.Container(height=8),
                # En-tête de tableau (mêmes largeurs que les lignes ci-dessous)
                ft.Container(
                    content=ft.Row([
                        ft.Text("Nom Prénom", size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700, expand=2),
                        ft.Text("Niveau", size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700, width=180),
                        ft.Text("Saison", size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700, width=110),
                        ft.Text("Club", size=11,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.GREY_700, expand=2),
                        ft.Container(
                            content=ft.Text("CACI", size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.GREY_700,
                                            text_align=ft.TextAlign.CENTER),
                            width=80,
                            alignment=ft.Alignment.CENTER,
                        ),
                    ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                    bgcolor=ft.Colors.GREY_200,
                    border_radius=8,
                ),
                ft.Container(height=4),
                # Liste
                ft.Container(
                    content=self.liste_plongeurs_col,
                    expand=True,
                    padding=ft.Padding(left=4, right=4, top=0, bottom=4),
                    bgcolor=ft.Colors.WHITE,
                    border_radius=8,
                ),
            ], spacing=0),
            expand=True,
        )

    def _build_carte_plongeur(self, p: dict) -> ft.Control:
        """Carte plongeur en LIGNE UNIQUE (style tableau) — version desktop.
        Colonnes : Nom (+ âge si mineur)  |  Niveau (+ prépa)  |  Saison  |  Club  |  Statut CACI
        """
        statut_caci, coul_caci = calcul_statut_caci(p.get("date_fin_caci", ""))
        age = calcul_age(p.get("date_naissance", ""))
        age_suffix = f"  ({age} ans)" if (age is not None and age < 18) else ""
        niveau_str = niveau_affiche(p.get("niveau", ""), p.get("brev_nitrox", ""))
        prepa = (p.get("niveau_prepa", "") or "").strip()
        niveau_full = f"{niveau_str} → {prepa}" if prepa else niveau_str

        saison   = (p.get("saison", "")   or "").strip() or "—"
        nom_club = (p.get("nom_club", "") or "").strip() or "—"

        statut_chip = ft.Container(
            content=ft.Text(statut_caci, size=11, color=ft.Colors.WHITE,
                            text_align=ft.TextAlign.CENTER),
            bgcolor=coul_caci,
            border_radius=4,
            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
            width=80,
            alignment=ft.Alignment.CENTER,
        )

        return ft.Container(
            content=ft.Row([
                # Nom Prénom (+ âge si mineur)
                ft.Text(
                    f"{p['nom']} {p['prenom']}{age_suffix}",
                    weight=ft.FontWeight.BOLD, size=14,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    expand=2,
                ),
                # Niveau (+ prépa éventuelle)
                ft.Text(
                    niveau_full,
                    size=13, color=ft.Colors.GREY_800,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    width=180,
                ),
                # Saison
                ft.Text(
                    saison,
                    size=12, color=ft.Colors.GREY_600,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    width=110,
                ),
                # Club
                ft.Text(
                    nom_club,
                    size=12, color=ft.Colors.GREY_600,
                    no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS,
                    expand=2,
                ),
                # Statut CACI
                statut_chip,
            ], spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(left=14, right=14, top=10, bottom=10),
            bgcolor=ft.Colors.WHITE,
            border_radius=4,
            on_click=lambda _, plongeur=p: self._show_fiche_plongeur(plongeur),
            ink=True,
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

    def _launch_url(self, url: str):
        """Lance une URL externe. Sur desktop, page.launch_url ouvre via le
        navigateur ou l'app système enregistrée pour le schéma (mailto:, tel:).
        En Flet 0.85 c'est une coroutine, on la planifie via run_task."""
        page = self.page
        async def _do_launch():
            try:
                await page.launch_url(url)
            except Exception as exc:
                try:
                    self._show_snack(f"Impossible d'ouvrir : {exc}", erreur=True)
                except Exception:
                    print(f"Erreur launch_url : {exc}")
        try:
            self.page.run_task(_do_launch)
        except Exception as exc:
            self._show_snack(f"Impossible d'ouvrir : {exc}", erreur=True)

    def _show_fiche_plongeur(self, p: dict):
        statut_caci, coul_caci = calcul_statut_caci(p.get("date_fin_caci", ""))
        age = calcul_age(p.get("date_naissance", ""))
        age_str = f"  ({age} ans)" if (age is not None and age < 18) else ""
        niveau_str = niveau_affiche(p.get("niveau", ""), p.get("brev_nitrox", ""))

        email = (p.get("email", "") or "").strip()
        portable = (p.get("portable", "") or "").strip()
        nom_club = (p.get("nom_club", "") or "").strip()

        def ligne(label, valeur, couleur=None, multi_ligne=False):
            txt = ft.Text(
                valeur or "—",
                size=13,
                color=couleur or ft.Colors.BLACK87,
                no_wrap=not multi_ligne,
                selectable=True,
            )
            if multi_ligne:
                return ft.Row([
                    ft.Text(label, size=13, color=ft.Colors.GREY_600, width=160),
                    ft.Container(content=txt, expand=True),
                ], vertical_alignment=ft.CrossAxisAlignment.START)
            return ft.Row([
                ft.Text(label, size=13, color=ft.Colors.GREY_600, width=160),
                txt,
            ])

        def ligne_scroll(label, valeur, on_click=None):
            txt = ft.Text(
                valeur or "—",
                size=13,
                color=ft.Colors.BLUE_700 if (on_click and valeur) else ft.Colors.BLACK87,
                no_wrap=True,
                selectable=True,
            )
            inner = ft.Row([txt], scroll=ft.ScrollMode.AUTO, expand=True)
            return ft.Row([
                ft.Text(label, size=13, color=ft.Colors.GREY_600, width=160),
                ft.Container(
                    content=inner,
                    expand=True,
                    on_click=on_click if valeur else None,
                    ink=bool(on_click and valeur),
                ),
            ])

        prepa = p.get("niveau_prepa", "")
        prepa_row = ligne("Niveau en prépa", prepa) if prepa else ft.Container()
        nom_club_row = ligne("Club", nom_club, multi_ligne=True) if nom_club else ft.Container()

        def open_mail(_):
            club = get_param("nom_club_court")
            mode = get_param("mode_redaction") or "structure"
            if mode == "commission":
                commission = get_param("commission_redaction") or ""
                sujet_str = (f"Message de la commission {commission} du {club}"
                             if commission else f"Message du {club}")
            else:
                sujet_str = f"Message du {club}"
            sujet = urllib.parse.quote(sujet_str)
            self._launch_url(f"mailto:{email}?subject={sujet}")

        def open_tel(_):
            num = re.sub(r'[^\d+]', '', portable)
            self._launch_url(f"tel:{num}")

        def open_sms(_):
            # Sur desktop, sms: ouvre rarement quelque chose (sauf macOS Messages),
            # mais on tente quand même
            num = re.sub(r'[^\d+]', '', portable)
            self._launch_url(f"sms:{num}")

        contenu = ft.Column([
            ft.Text(f"{p['nom']} {p['prenom']}",
                    size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ligne("N° Licence",     p.get("id_licence", "")),
            ligne("Date naissance", p.get("date_naissance", "") + age_str),
            ligne("Saison",         p.get("saison", "")),
            ligne("Type licence",   p.get("type_licence", "")),
            nom_club_row,
            ft.Divider(),
            ligne("Niveau",            niveau_str),
            prepa_row,
            ligne("Brevet moniteur",   p.get("brev_moniteur", "")),
            ligne("Brevet encadrant",  p.get("brev_encadrant", "")),
            ligne("Brevet plongeur",   p.get("brev_plongeur", "")),
            ligne("Brevet nitrox",     p.get("brev_nitrox", "")),
            ft.Row([
                ft.Text("Tous les brevets", size=13,
                        color=ft.Colors.GREY_600, width=160),
                ft.TextButton(
                    f"Voir ({len(parse_brevets(p.get('brevets_brut', '')))})",
                    icon=ft.Icons.LIST,
                    on_click=lambda _, plg=p: self._show_tous_brevets(plg),
                ),
            ]),
            ft.Divider(),
            ligne("CACI fin", p.get("date_fin_caci", "")),
            ft.Row([
                ft.Text("Statut CACI", size=13,
                        color=ft.Colors.GREY_600, width=160),
                ft.Container(
                    content=ft.Text(statut_caci, size=13, color=ft.Colors.WHITE),
                    bgcolor=coul_caci,
                    border_radius=4,
                    padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                ),
            ]),
            ft.Divider(),
            ligne_scroll("Email",    email,    on_click=open_mail if email else None),
            ligne_scroll("Portable", portable, on_click=open_tel  if portable else None),
        ], scroll=ft.ScrollMode.AUTO, spacing=8)

        # Boutons d'action contact en bas — icônes seules + tooltip
        action_buttons = []
        if email:
            action_buttons.append(ft.IconButton(
                icon=ft.Icons.EMAIL, tooltip="Envoyer un email",
                on_click=open_mail,
                bgcolor=ft.Colors.BLUE_700, icon_color=ft.Colors.WHITE,
            ))
        if portable:
            action_buttons.append(ft.IconButton(
                icon=ft.Icons.PHONE, tooltip="Appeler",
                on_click=open_tel,
                bgcolor=ft.Colors.GREEN_700, icon_color=ft.Colors.WHITE,
            ))
            action_buttons.append(ft.IconButton(
                icon=ft.Icons.SMS, tooltip="Envoyer un SMS",
                on_click=open_sms,
                bgcolor=ft.Colors.ORANGE_700, icon_color=ft.Colors.WHITE,
            ))
        if action_buttons:
            contenu.controls.append(ft.Divider())
            contenu.controls.append(
                ft.Row(action_buttons, spacing=12,
                       alignment=ft.MainAxisAlignment.CENTER)
            )

        def fermer(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text("Fiche plongeur"),
            content=ft.Container(
                content=contenu,
                width=self.DIALOG_W_LARGE,
                height=self.DIALOG_H_LARGE,
            ),
            actions=[ft.TextButton("Fermer", on_click=fermer)],
        )
        self.page.show_dialog(dlg)

    def _show_tous_brevets(self, p: dict):
        brevets = parse_brevets(p.get("brevets_brut", ""))
        if not brevets:
            self._show_snack("Aucun brevet enregistré pour ce plongeur.")
            return

        lignes = []
        for nom_long, nom_court in brevets:
            lignes.append(
                ft.Row([
                    ft.Container(
                        content=ft.Text(nom_court, size=12,
                                        color=ft.Colors.WHITE,
                                        weight=ft.FontWeight.BOLD),
                        bgcolor=ft.Colors.BLUE_700,
                        border_radius=4,
                        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                        width=90,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(nom_long, size=13, expand=True, selectable=True),
                ], spacing=12)
            )

        def fermer(_):
            self.page.pop_dialog()

        dlg = ft.AlertDialog(
            title=ft.Text(f"{p['nom']} {p['prenom']} — {len(brevets)} brevet(s)",
                          size=15),
            content=ft.Container(
                content=ft.Column(lignes, scroll=ft.ScrollMode.AUTO, spacing=6),
                width=self.DIALOG_W, height=self.DIALOG_H,
            ),
            actions=[ft.TextButton("Fermer", on_click=fermer)],
        )
        self.page.show_dialog(dlg)

    # ── Import FFESSM ─────────────────────────────────────────────────────

    async def _on_import_ffessm(self, e):
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
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
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
            self.plongeurs = load_plongeurs()
            self._refresh_liste_plongeurs(
                self.search_field.value if hasattr(self, "search_field") else ""
            )

            self.page.pop_dialog()
            try:
                self.page.update()
            except Exception:
                pass
            self._show_snack(f"Import terminé — {nb_total} plongeur(s) traité(s).")

        threading.Thread(target=do, daemon=True).start()

    # ── Vider la base ─────────────────────────────────────────────────────

    def _on_vider_plongeurs(self, e):
        nb = len(self.plongeurs)
        if nb == 0:
            self._show_snack("La base est déjà vide.")
            return

        def confirmer(_):
            self.page.pop_dialog()
            truncate_plongeurs()
            self.plongeurs = []
            self._refresh_liste_plongeurs("")
            try: self.page.update()
            except Exception: pass
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
                                bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_suppression_totale(self, e):
        def annuler(_):
            self.page.pop_dialog()

        def confirmer_2(_):
            self.page.pop_dialog()
            truncate_all_data()
            self.plongeurs = []
            self.filtre_tokens = []
            self.pj_path = ""
            self._refresh_liste_plongeurs("")
            self._refresh_commissions_chips()
            self._refresh_historique()
            self._load_params_fields()
            try: self.page.update()
            except Exception: pass
            self._show_snack("Toutes les données ont été supprimées.")

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
                                    bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE),
                ],
            )
            self.page.show_dialog(dlg2)

        dlg1 = ft.AlertDialog(
            title=ft.Text("Suppression totale des données"),
            content=ft.Text(
                "Vous êtes sur le point de supprimer TOUTES les données "
                "de l'application : plongeurs, historique des messages et "
                "paramètres du club.\n\nCette action est définitive."
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Continuer", on_click=confirmer_1,
                                bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg1)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 2 — Composer
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_composer(self):
        # Canal : SMS désactivé sur desktop
        self.dd_canal = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="email", label="Email"),
                ft.Radio(value="sms",   label="SMS  (indisponible sur desktop)",
                         disabled=True),
            ]),
            value="email",
            on_change=self._on_canal_change,
        )

        self.filtre_tokens: list = []
        self.commissions_chips_row = ft.Row(
            wrap=True, spacing=4, run_spacing=4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        self.commissions_grid = ft.Column(spacing=4)
        self.rule_buttons_row = ft.Row(spacing=8, wrap=True)

        self.tf_age_min = ft.TextField(
            label="Âge min", width=110, dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filtre_change,
        )
        self.tf_age_max = ft.TextField(
            label="Âge max", width=110, dense=True,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._on_filtre_change,
        )

        self.cb_caci = {}
        for statut in [STATUT_CACI_VALIDE, STATUT_CACI_ALERTE, STATUT_CACI_PERIME]:
            self.cb_caci[statut] = ft.Checkbox(
                label=statut, value=False, on_change=self._on_filtre_change)

        self.cb_type_licence = {}
        for typ in ["Pratiquant", "Aidant"]:
            self.cb_type_licence[typ] = ft.Checkbox(
                label=typ, value=False, on_change=self._on_filtre_change)

        self.cb_categorie = {}
        for cat in ["Enfant", "Jeune", "Adulte"]:
            self.cb_categorie[cat] = ft.Checkbox(
                label=cat, value=False, on_change=self._on_filtre_change)

        self.tf_sujet = ft.TextField(
            label="Sujet / objet", dense=True, visible=True, expand=True)
        self.tf_corps = ft.TextField(
            label="Corps du message", multiline=True,
            min_lines=8, max_lines=20, expand=True)

        self.btn_pj = ft.FilledButton(
            "Pièce jointe", icon=ft.Icons.ATTACH_FILE,
            on_click=self._on_choisir_pj)
        self.lbl_pj = ft.Text("", size=12, color=ft.Colors.GREY_600)

        self.lbl_nb_dest = ft.Text("0 destinataire(s)", size=14,
                                   weight=ft.FontWeight.BOLD)
        self.liste_dest_preview = ft.Column(
            scroll=ft.ScrollMode.AUTO, height=220, spacing=2)

        self.btn_envoyer = ft.FilledButton(
            "Envoyer", icon=ft.Icons.SEND,
            bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE,
            on_click=self._on_envoyer)

        self._build_commissions_grid()
        self._build_rule_buttons()

        # Layout 2 colonnes sur desktop : Filtres à gauche | Message + Dest à droite
        filtres_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("Filtres", weight=ft.FontWeight.BOLD, size=15),
                        ft.TextButton(
                            "Effacer les filtres",
                            icon=ft.Icons.FILTER_ALT_OFF,
                            on_click=self._on_effacer_filtres,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.dd_canal,
                    ft.Text("Filtres commission actifs", size=12,
                            color=ft.Colors.GREY_700),
                    self.commissions_chips_row,
                    ft.Text("Ajouter une règle", size=12,
                            color=ft.Colors.GREY_700),
                    self.rule_buttons_row,
                    ft.Text("Ajouter une commission", size=12,
                            color=ft.Colors.GREY_700),
                    self.commissions_grid,
                    ft.Text("Type de licence", size=12,
                            color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_type_licence["Pratiquant"],
                        self.cb_type_licence["Aidant"],
                    ], spacing=12),
                    ft.Text("Catégorie", size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_categorie["Enfant"],
                        self.cb_categorie["Jeune"],
                        self.cb_categorie["Adulte"],
                    ], spacing=12),
                    ft.Text("Âge", size=12, color=ft.Colors.GREY_700),
                    ft.Row([self.tf_age_min, self.tf_age_max], spacing=12),
                    ft.Text("Statut CACI", size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        self.cb_caci[STATUT_CACI_VALIDE],
                        self.cb_caci[STATUT_CACI_ALERTE],
                        self.cb_caci[STATUT_CACI_PERIME],
                    ], spacing=12),
                ], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=16,
                expand=True,
            ),
        )

        dest_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        self.lbl_nb_dest,
                        ft.Row([
                            ft.TextButton(
                                "Actualiser", icon=ft.Icons.REFRESH,
                                on_click=lambda _: self._actualiser_destinataires(),
                            ),
                            ft.TextButton(
                                "Export CSV", icon=ft.Icons.FILE_DOWNLOAD,
                                on_click=self._export_csv_destinataires,
                            ),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.liste_dest_preview,
                ], spacing=4),
                padding=16,
            ),
        )

        message_section = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Message", weight=ft.FontWeight.BOLD, size=15),
                    ft.Row([self.tf_sujet], spacing=0),
                    ft.Row([self.tf_corps], spacing=0, expand=True),
                    ft.Row([self.btn_pj, self.lbl_pj], spacing=12),
                    ft.Row([self.btn_envoyer],
                           alignment=ft.MainAxisAlignment.END),
                ], spacing=12, expand=True),
                padding=16,
                expand=True,
            ),
            expand=True,
        )

        # Layout 2 colonnes
        return ft.Container(
            content=ft.Row([
                # Colonne gauche : Filtres (largeur fixe)
                ft.Container(
                    content=filtres_section,
                    width=440,
                ),
                ft.Container(width=12),
                # Colonne droite : Destinataires en haut + Message en bas
                ft.Container(
                    content=ft.Column([
                        dest_section,
                        message_section,
                    ], spacing=12, expand=True),
                    expand=True,
                ),
            ], spacing=0, expand=True,
               vertical_alignment=ft.CrossAxisAlignment.START),
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

    def _on_effacer_filtres(self, e):
        self.filtre_tokens = []
        for cb in self.cb_type_licence.values():
            cb.value = False; self._safe_update(cb)
        for cb in self.cb_categorie.values():
            cb.value = False; self._safe_update(cb)
        self.tf_age_min.value = ""; self.tf_age_max.value = ""
        self._safe_update(self.tf_age_min); self._safe_update(self.tf_age_max)
        for cb in self.cb_caci.values():
            cb.value = False; self._safe_update(cb)
        self._refresh_commissions_chips()
        self._actualiser_destinataires()
        try: self.page.update()
        except Exception: pass
        self._show_snack("Filtres effacés.")

    def _build_filtres(self) -> dict:
        statuts = [s for s, cb in self.cb_caci.items() if cb.value]
        types_licence = [t for t, cb in self.cb_type_licence.items() if cb.value]
        categories    = [c for c, cb in self.cb_categorie.items() if cb.value]

        def to_int(tf):
            try: return int(tf.value.strip())
            except Exception: return None

        canal = self.dd_canal.value or "email"
        return {
            "filtre_tokens": list(self.filtre_tokens),
            "types_licence": types_licence,
            "categories":    categories,
            "age_min":       to_int(self.tf_age_min),
            "age_max":       to_int(self.tf_age_max),
            "statuts_caci":  statuts,
            "avec_email":    (canal == "email"),
            "avec_portable": (canal == "sms"),
        }

    # ── Tokens helpers ────────────────────────────────────────────────────

    def _new_token_id(self) -> str:
        import uuid
        return uuid.uuid4().hex[:12]

    def _find_item_token(self, item_id: str):
        for t in self.filtre_tokens:
            if t.get("type") == "item" and t.get("id") == item_id:
                return t
        return None

    def _add_token(self, token: dict):
        self.filtre_tokens.append(token)
        self._refresh_commissions_chips()
        self._actualiser_destinataires()

    def _add_op(self, op: str):
        self._add_token({"type": "op", "value": op})

    def _add_paren_open(self):
        self._add_token({"type": "paren_open"})

    def _add_paren_close(self):
        nb_open  = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_open")
        nb_close = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_close")
        if nb_close >= nb_open:
            self._show_snack("Aucune parenthèse à fermer.", erreur=True)
            return
        self._add_token({"type": "paren_close"})

    def _undo_last_token(self):
        if not self.filtre_tokens:
            return
        self.filtre_tokens.pop()
        self._refresh_commissions_chips()
        self._actualiser_destinataires()

    def _build_rule_buttons(self):
        self.rule_buttons_row.controls.clear()

        def chip_btn(label, color, handler, tooltip=None, width=None):
            return ft.Container(
                content=ft.Text(label, size=13, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                text_align=ft.TextAlign.CENTER),
                bgcolor=color, border_radius=6,
                padding=ft.Padding(left=14, right=14, top=8, bottom=8),
                on_click=lambda _: handler(),
                ink=True, tooltip=tooltip, width=width,
            )

        self.rule_buttons_row.controls.extend([
            chip_btn("OU",  ft.Colors.BLUE_700, lambda: self._add_op("OU"),  "Opérateur OU"),
            chip_btn("ET",  ft.Colors.BLUE_700, lambda: self._add_op("ET"),  "Opérateur ET"),
            chip_btn("NON", ft.Colors.RED_700,  lambda: self._add_op("NON"), "Négation logique"),
            chip_btn("(",   ft.Colors.GREY_700, self._add_paren_open,  "Parenthèse ouvrante", 55),
            chip_btn(")",   ft.Colors.GREY_700, self._add_paren_close, "Parenthèse fermante", 55),
            chip_btn("⌫",   ft.Colors.GREY_500, self._undo_last_token, "Annuler le dernier", 55),
        ])

    def _build_commissions_grid(self):
        self.commissions_grid.controls.clear()
        for titre_section, filtres in SECTIONS_FILTRES:
            self.commissions_grid.controls.append(
                ft.Text(titre_section, size=12,
                        color=ft.Colors.GREY_700,
                        weight=ft.FontWeight.BOLD)
            )
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
                            content=ft.Text(nom, size=12, color=txt_color,
                                            text_align=ft.TextAlign.CENTER),
                            bgcolor=bgcolor, border=border, border_radius=6,
                            padding=ft.Padding(left=8, right=8, top=8, bottom=8),
                            expand=True, on_click=handler, ink=actif,
                        )
                    )
                if len(row_ctrls) == 1:
                    row_ctrls.append(ft.Container(expand=True))
                self.commissions_grid.controls.append(ft.Row(row_ctrls, spacing=4))
            self.commissions_grid.controls.append(ft.Container(height=4))

    def _brevets_commission_dans_club(self, commission_nom: str) -> list:
        seen = set()
        for p in self.plongeurs:
            seen.update(brevets_d_une_commission(p.get("brevets_brut", ""), commission_nom))
        return sorted(seen, key=lambda b: (brevet_court(b).lower(), b.lower()))

    def _open_commission_popup(self, commission_nom: str, item_id: str = None):
        brevets_dispo = self._brevets_commission_dans_club(commission_nom)
        existing = self._find_item_token(item_id) if item_id else None

        if existing is None:
            mode_initial = "tous_avec"
            brevets_pre  = []
        else:
            mode_initial = existing.get("mode", "tous_avec")
            brevets_pre  = list(existing.get("brevets", []))

        no_brevets = (not brevets_dispo)

        cbs = {}
        cb_rows = []
        for b in brevets_dispo:
            court = brevet_court(b)
            label = f"{court}  —  {b}" if court != b else b
            cb = ft.Checkbox(value=(b in brevets_pre))
            cbs[b] = cb
            cb_rows.append(ft.Row([
                cb,
                ft.Text(label, size=13, expand=True, no_wrap=False, max_lines=2),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        cbs_column = ft.Column(cb_rows, spacing=2, scroll=ft.ScrollMode.AUTO)
        cbs_column.visible = (mode_initial == "selection")

        def tout_cocher(_):
            for cb in cbs.values(): cb.value = True; self._safe_update(cb)
        def tout_decocher(_):
            for cb in cbs.values(): cb.value = False; self._safe_update(cb)

        actions_selection = ft.Row([
            ft.TextButton("Tout cocher", icon=ft.Icons.CHECK_BOX, on_click=tout_cocher),
            ft.TextButton("Tout décocher", icon=ft.Icons.CHECK_BOX_OUTLINE_BLANK,
                          on_click=tout_decocher),
        ], spacing=4)
        actions_selection.visible = (mode_initial == "selection")

        def on_mode_change(e):
            mode = radio_mode.value
            cbs_column.visible        = (mode == "selection")
            actions_selection.visible = (mode == "selection")
            self._safe_update(cbs_column)
            self._safe_update(actions_selection)

        radios = [
            ft.Radio(value="tous_avec",
                     label=f"Tous les membres ({len(brevets_dispo)} brevet(s))",
                     disabled=no_brevets),
            ft.Radio(value="selection",
                     label="Sélection précise de brevet(s)",
                     disabled=no_brevets),
            ft.Radio(value="tous_sans", label="Tous les membres SANS brevet"),
        ]
        radio_mode = ft.RadioGroup(
            content=ft.Column(radios, spacing=0),
            value=mode_initial if not (no_brevets and mode_initial != "tous_sans") else "tous_sans",
            on_change=on_mode_change,
        )

        def annuler(_): self.page.pop_dialog()

        def valider(_):
            mode = radio_mode.value
            if mode == "selection":
                selectes = [b for b, cb in cbs.items() if cb.value]
                if not selectes:
                    self._show_snack("Aucun brevet sélectionné.", erreur=True)
                    return
                brevets = selectes
            else:
                brevets = []
            if existing is not None:
                existing["mode"] = mode
                existing["brevets"] = brevets
            else:
                self.filtre_tokens.append({
                    "type": "item", "id": self._new_token_id(),
                    "commission": commission_nom,
                    "mode": mode, "brevets": brevets,
                })
            self.page.pop_dialog()
            self._refresh_commissions_chips()
            self._actualiser_destinataires()

        def retirer(_):
            if existing is not None:
                self.filtre_tokens = [t for t in self.filtre_tokens
                                      if not (t.get("type") == "item"
                                              and t.get("id") == existing.get("id"))]
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
                "Retirer", on_click=retirer,
                style=ft.ButtonStyle(color=ft.Colors.RED),
            ))

        titre = commission_nom + ("   (modification)" if existing is not None else "")
        dlg = ft.AlertDialog(
            title=ft.Text(titre, size=15),
            content=ft.Container(
                content=ft.Column([
                    radio_mode,
                    ft.Divider(height=8),
                    actions_selection,
                    cbs_column,
                ], scroll=ft.ScrollMode.AUTO, spacing=4),
                width=self.DIALOG_W, height=self.DIALOG_H,
            ),
            actions=boutons,
        )
        self.page.show_dialog(dlg)

    def _chip_for_item(self, item: dict) -> ft.Control:
        nom = item.get("commission", "")
        mode = item.get("mode", "tous_avec")
        brevets = item.get("brevets", [])
        item_id = item.get("id", "")

        if mode == "tous_sans":
            bg = ft.Colors.RED_700; icon = ft.Icons.BLOCK
        elif mode == "selection":
            bg = ft.Colors.INDIGO_700; icon = ft.Icons.CHECKLIST
        else:
            bg = ft.Colors.BLUE_700; icon = ft.Icons.CHECK

        if mode == "selection" and brevets:
            if len(brevets) <= 2:
                codes = ", ".join(brevet_court(b) for b in brevets)
                label = f"{nom} : {codes}"
            else:
                label = f"{nom} ({len(brevets)})"
        elif mode == "tous_sans":
            label = f"sans {nom}"
        else:
            label = nom

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=13, color=ft.Colors.WHITE),
                ft.Text(label, size=12, color=ft.Colors.WHITE),
            ], spacing=4, tight=True),
            bgcolor=bg, border_radius=12,
            padding=ft.Padding(left=9, right=11, top=5, bottom=5),
            on_click=lambda _, n=nom, iid=item_id:
                self._open_commission_popup(n, item_id=iid),
            ink=True,
        )

    def _refresh_commissions_chips(self):
        self.commissions_chips_row.controls.clear()
        if not self.filtre_tokens:
            self.commissions_chips_row.controls.append(
                ft.Text("(aucun filtre — tous les plongeurs)", size=12,
                        italic=True, color=ft.Colors.GREY_500)
            )
            self._safe_update(self.commissions_chips_row)
            return

        for t in self.filtre_tokens:
            ttype = t.get("type")
            if ttype == "item":
                self.commissions_chips_row.controls.append(self._chip_for_item(t))
            elif ttype == "op":
                op = t.get("value", "")
                couleur = ft.Colors.RED_700 if op == "NON" else ft.Colors.BLUE_800
                self.commissions_chips_row.controls.append(
                    ft.Container(
                        content=ft.Text(op, size=12, color=couleur,
                                        weight=ft.FontWeight.BOLD),
                        padding=ft.Padding(left=2, right=2, top=2, bottom=2),
                    )
                )
            elif ttype == "paren_open":
                self.commissions_chips_row.controls.append(
                    ft.Text("(", size=18, color=ft.Colors.GREY_900,
                            weight=ft.FontWeight.BOLD))
            elif ttype == "paren_close":
                self.commissions_chips_row.controls.append(
                    ft.Text(")", size=18, color=ft.Colors.GREY_900,
                            weight=ft.FontWeight.BOLD))

        nb_open  = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_open")
        nb_close = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_close")
        if nb_open > nb_close:
            self.commissions_chips_row.controls.append(
                ft.Text(f" + {nb_open - nb_close} «)» auto-fermée(s)",
                        size=11, italic=True, color=ft.Colors.ORANGE_700))

        self._safe_update(self.commissions_chips_row)

    def _actualiser_destinataires(self):
        if hasattr(self, "commissions_chips_row"):
            self._refresh_commissions_chips()
        filtres = self._build_filtres()
        self.filtres_actifs = filtres
        dest = appliquer_filtres(self.plongeurs, filtres)
        self.destinataires_selectionnes = dest

        self.lbl_nb_dest.value = f"{len(dest)} destinataire(s)"
        self.liste_dest_preview.controls.clear()
        for p in dest[:200]:  # plus large sur desktop
            self.liste_dest_preview.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"{p['nom']} {p['prenom']}",
                                size=13, expand=True),
                        ft.Text(
                            p.get("email") or p.get("portable") or "—",
                            size=12, color=ft.Colors.GREY_600,
                        ),
                    ]),
                    bgcolor=ft.Colors.WHITE, border_radius=4,
                    padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                )
            )
        if len(dest) > 200:
            self.liste_dest_preview.controls.append(
                ft.Text(f"…et {len(dest)-200} autre(s)", size=12,
                        color=ft.Colors.GREY_500))
        self._safe_update(self.lbl_nb_dest)
        self._safe_update(self.liste_dest_preview)

    async def _on_choisir_pj(self, e):
        files = await self.file_picker.pick_files(
            dialog_title="Sélectionner une pièce jointe")
        if files:
            self.pj_path = files[0].path
            self.lbl_pj.value = os.path.basename(self.pj_path)
            self._safe_update(self.lbl_pj)

    def _brevets_filtres_du_plongeur(self, p: dict) -> list:
        tokens = self.filtres_actifs.get("filtre_tokens") or []
        brevets_brut = p.get("brevets_brut", "")
        brevets_courts = []
        items = [t for t in tokens if t.get("type") == "item"]
        if items:
            for item in items:
                mode = item.get("mode", "tous_avec")
                if mode == "tous_sans": continue
                nom_com = item.get("commission", "")
                brevets_dans_com = brevets_d_une_commission(brevets_brut, nom_com)
                if not brevets_dans_com: continue
                if mode == "selection":
                    cibles = [b for b in brevets_dans_com
                              if b in item.get("brevets", [])]
                else:
                    cibles = brevets_dans_com
                brevets_courts.extend(brevet_court(b) for b in cibles)
        else:
            for _, court in parse_brevets(brevets_brut):
                brevets_courts.append(court)
        return list(dict.fromkeys(brevets_courts))

    async def _export_csv_destinataires(self, e):
        dest = self.destinataires_selectionnes
        if not dest:
            self._show_snack("Aucun destinataire à exporter.", erreur=True)
            return
        rows = []
        for p in dest:
            brevets_filtres = self._brevets_filtres_du_plongeur(p)
            rows.append([p.get("nom", ""), p.get("prenom", ""),
                         ", ".join(brevets_filtres),
                         p.get("nom_club", ""), p.get("email", "")])
        nom_club_court = get_param("nom_club_court") or "club"
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{nom_club_court}_{date_str}.csv"
        try:
            target = await self.file_picker.save_file(
                dialog_title="Exporter en CSV",
                file_name=filename,
                allowed_extensions=["csv"])
        except Exception as err:
            self._show_snack(f"Erreur ouverture sélecteur : {err}", erreur=True)
            return
        if not target:
            return
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
        detail = f"{nb_email} email(s)"
        self._confirm_envoi(
            f"Envoyer {detail} à {len(dest)} destinataire(s) ?",
            canal, sujet, corps)

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
                ft.FilledButton("Envoyer", on_click=on_ok, color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _executer_envoi(self, canal, sujet, corps):
        # Sur desktop on n'a que le canal email (SMS désactivé)
        dest = self.destinataires_selectionnes
        prog = ft.AlertDialog(
            title=ft.Text("Envoi en cours…"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Envoi des emails…"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
            modal=True,
        )
        self.page.show_dialog(prog)

        def fermer_progress():
            try: prog.open = False
            except Exception: pass
            try: self.page.pop_dialog()
            except Exception: pass
            try: self.page.update()
            except Exception: pass

        def do():
            nb_ok = nb_err = 0
            try:
                smtp_host = get_param("smtp_host")
                smtp_port = int(get_param("smtp_port") or 587)
                smtp_user = get_param("smtp_user")
                smtp_pwd  = get_param("smtp_password")
                use_tls   = get_param("smtp_tls") == "1"
                expediteur = get_param("email_expediteur") or smtp_user
                for p in dest:
                    email = (p.get("email", "") or "").strip()
                    if not email: continue
                    ok, err = envoyer_email(
                        email, sujet, corps, self.pj_path,
                        smtp_host, smtp_port, smtp_user, smtp_pwd,
                        use_tls, expediteur)
                    if ok: nb_ok += 1
                    else:
                        nb_err += 1
                        print(f"Erreur envoi {email} : {err}")
                dest_ids = [p.get("id_licence", "") for p in dest]
                save_message_historique(
                    canal, sujet, corps, self.filtres_actifs, dest_ids,
                    nb_ok, nb_err)
            finally:
                fermer_progress()
                self._show_snack(
                    f"Envoi terminé — {nb_ok} envoyé(s), {nb_err} erreur(s).")

        threading.Thread(target=do, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────
    # TAB 3 — Historique
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_historique(self):
        self.historique_col = ft.Column(
            scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("Historique des envois",
                                size=20, weight=ft.FontWeight.BOLD),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.REFRESH, tooltip="Actualiser",
                                on_click=lambda _: self._refresh_historique()),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_SWEEP,
                                tooltip="Vider l'historique",
                                icon_color=ft.Colors.RED_700,
                                on_click=self._on_vider_historique),
                        ], spacing=0),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=16, bgcolor=ft.Colors.WHITE, border_radius=8),
                ft.Container(height=8),
                ft.Container(content=self.historique_col, expand=True,
                             padding=8),
            ], spacing=0),
            expand=True,
        )

    def _on_vider_historique(self, e):
        rows = load_historique(limit=1)
        if not rows:
            self._show_snack("L'historique est déjà vide.")
            return
        def annuler(_): self.page.pop_dialog()
        def confirmer(_):
            self.page.pop_dialog()
            truncate_historique()
            self._refresh_historique()
            try: self.page.update()
            except Exception: pass
            self._show_snack("Historique vidé.")
        dlg = ft.AlertDialog(
            title=ft.Text("Vider l'historique"),
            content=ft.Text("Supprimer définitivement tout l'historique des envois ?"),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Vider", on_click=confirmer,
                                bgcolor=ft.Colors.RED_700, color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_supprimer_message(self, id_msg: int):
        delete_historique(id_msg)
        self._refresh_historique()
        try: self.page.update()
        except Exception: pass

    def _refresh_historique(self):
        rows = load_historique()
        self.historique_col.controls.clear()
        if not rows:
            self.historique_col.controls.append(
                ft.Text("Aucun envoi enregistré.", color=ft.Colors.GREY_500))
        for r in rows:
            id_, date_e, canal, sujet, nb_ok, nb_err, filtre_j, dest_j, corps = r
            try: nb_dest = len(json.loads(dest_j))
            except Exception: nb_dest = 0
            self.historique_col.controls.append(
                ft.Card(content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(date_e, size=12, color=ft.Colors.GREY_600),
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(canal.upper(), size=11,
                                                    color=ft.Colors.WHITE),
                                    bgcolor=(ft.Colors.BLUE_600
                                             if canal == "email"
                                             else ft.Colors.GREEN_600),
                                    border_radius=4,
                                    padding=ft.Padding(left=7, right=7, top=2, bottom=2)),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_size=20, tooltip="Supprimer ce message",
                                    icon_color=ft.Colors.RED_600,
                                    on_click=lambda _, mid=id_:
                                        self._on_supprimer_message(mid)),
                            ], spacing=4,
                               vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Text(sujet or corps[:80], size=14,
                                weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{nb_dest} destinataire(s)  •  "
                            f"{nb_ok} envoyé(s)  •  {nb_err} erreur(s)",
                            size=13, color=ft.Colors.GREY_700),
                    ], spacing=4),
                    padding=12)))
        self._safe_update(self.historique_col)

    # ──────────────────────────────────────────────────────────────────────
    # TAB 4 — Paramètres
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_parametres(self):
        # Note : nom_club_court et nom_club_long ne sont PLUS dans cet onglet
        # mais accessibles via le bouton "Identité du club" en haut du
        # NavigationRail (cf. _build_club_leading + _open_club_popup).
        params_fields = {
            "email_expediteur":ft.TextField(label="Email expéditeur", dense=True,
                                           keyboard_type=ft.KeyboardType.EMAIL),
            "smtp_host":       ft.TextField(label="Serveur SMTP (host)", dense=True),
            "smtp_port":       ft.TextField(label="Port SMTP", dense=True,
                                           keyboard_type=ft.KeyboardType.NUMBER),
            "smtp_user":       ft.TextField(label="Utilisateur SMTP", dense=True),
            "smtp_password":   ft.TextField(label="Mot de passe SMTP", dense=True,
                                           password=True, can_reveal_password=True),
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
                                    size=20, weight=ft.FontWeight.BOLD),
                    padding=16, bgcolor=ft.Colors.WHITE, border_radius=8),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Column([
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Email — SMTP", weight=ft.FontWeight.BOLD,
                                        size=14),
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                            color=ft.Colors.BLUE_600),
                                    ft.Text(
                                        "Pour un compte Gmail, utilisez un "
                                        "« mot de passe d'application » "
                                        "(la validation en 2 étapes doit être activée). "
                                        "Voir : myaccount.google.com → Sécurité → "
                                        "Mots de passe des applications.",
                                        size=12, color=ft.Colors.GREY_700,
                                        expand=True, no_wrap=False),
                                ], spacing=6),
                                params_fields["email_expediteur"],
                                params_fields["smtp_host"],
                                params_fields["smtp_port"],
                                params_fields["smtp_user"],
                                params_fields["smtp_password"],
                            ], spacing=10),
                            padding=16, expand=True)),
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("SMS", weight=ft.FontWeight.BOLD, size=14),
                                ft.Row([
                                    ft.Icon(ft.Icons.WARNING_AMBER, size=16,
                                            color=ft.Colors.ORANGE_700),
                                    ft.Text(
                                        "L'envoi de SMS est désactivé sur cette "
                                        "version Desktop (pas d'app SMS native sur PC). "
                                        "Pour envoyer des SMS, utilisez la version "
                                        "Android de ClubMessenger.",
                                        size=12, color=ft.Colors.GREY_700,
                                        expand=True),
                                ], spacing=6),
                            ], spacing=10),
                            padding=16, expand=True)),
                        ft.FilledButton(
                            "Sauvegarder", icon=ft.Icons.SAVE,
                            bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE,
                            on_click=sauvegarder),
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Données", weight=ft.FontWeight.BOLD,
                                        size=14, color=ft.Colors.RED_700),
                                ft.Row([
                                    ft.Icon(ft.Icons.WARNING_AMBER, size=16,
                                            color=ft.Colors.ORANGE_700),
                                    ft.Text("Ces actions sont définitives.",
                                            size=12, color=ft.Colors.GREY_700,
                                            expand=True),
                                ], spacing=6),
                                ft.OutlinedButton(
                                    "Vider la base des membres",
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    on_click=self._on_vider_plongeurs,
                                    style=ft.ButtonStyle(color=ft.Colors.RED_700)),
                                ft.Text(
                                    "Conserve l'historique des messages et "
                                    "les paramètres.",
                                    size=11, color=ft.Colors.GREY_600),
                                ft.FilledButton(
                                    "Suppression totale des données",
                                    icon=ft.Icons.DELETE_FOREVER,
                                    on_click=self._on_suppression_totale,
                                    bgcolor=ft.Colors.RED_900, color=ft.Colors.WHITE),
                                ft.Text(
                                    "Supprime plongeurs, historique et paramètres.",
                                    size=11, color=ft.Colors.GREY_600),
                            ], spacing=10),
                            padding=16, expand=True)),
                        ft.Text(
                            f"ClubMessenger Desktop v{VERSION}  —  "
                            f"fr.csdev.clubmessenger",
                            size=11, color=ft.Colors.GREY_500),
                    ], spacing=12, scroll=ft.ScrollMode.AUTO),
                    padding=8, expand=True),
            ], spacing=0),
            expand=True,
        )

    def _load_params_fields(self):
        for cle, tf in self.params_fields.items():
            tf.value = get_param(cle)
            self._safe_update(tf)
        # Identité du club et mode de rédaction sont gérés via les boutons
        # du NavigationRail (popups), pas dans cet onglet. Mais on rafraîchit
        # les labels du NavRail au cas où d'autres écrans les auraient modifiés.
        self._refresh_club_leading()
        self._refresh_redaction_leading()

    # ──────────────────────────────────────────────────────────────────────
    # Chargement données & helpers
    # ──────────────────────────────────────────────────────────────────────

    def _load_data(self):
        self.plongeurs = load_plongeurs()
        self._refresh_liste_plongeurs(
            self.search_field.value if hasattr(self, "search_field") else "")
        self._actualiser_destinataires()
        self._refresh_historique()
        if hasattr(self, "params_fields"):
            self._load_params_fields()
        try: self.page.update()
        except Exception: pass

    def _safe_update(self, ctrl):
        try: ctrl.update()
        except (RuntimeError, AssertionError, AttributeError): pass

    def _show_snack(self, message, erreur=False):
        snack = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.RED_700 if erreur else ft.Colors.GREEN_700,
            duration=3000,
        )
        self.page.show_dialog(snack)


# ──────────────────────────────────────────────────────────────────────────────
# Point d'entrée Desktop
# ──────────────────────────────────────────────────────────────────────────────

def main_desktop(page: ft.Page):
    """Point d'entrée Desktop. Affiche l'erreur à l'écran en cas de crash
    au démarrage plutôt qu'un écran noir."""
    try:
        init_db()
        ClubMessengerDesktopApp(page)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        try:
            page.bgcolor = "#FFE5E5"
            page.padding = 24
            page.add(
                ft.Column([
                    ft.Text("⚠ Erreur au démarrage",
                            size=22, weight=ft.FontWeight.BOLD,
                            color="#B00020"),
                    ft.Divider(),
                    ft.Text(f"{type(exc).__name__}: {exc}",
                            size=15, selectable=True),
                    ft.Container(
                        content=ft.Text(tb, size=11, selectable=True,
                                        color="#444444"),
                        bgcolor="#FFFFFF", padding=12, border_radius=4),
                ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=10))
            page.update()
        except Exception:
            print(f"[FATAL] {exc}\n{tb}")


if __name__ == "__main__":
    ft.run(main_desktop)