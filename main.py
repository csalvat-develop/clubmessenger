"""
ClubMessenger v1.3.3 — Version Android
Application Flet (Android) — Messagerie ciblée pour club de plongée FFESSM
Bundle : fr.csdev.clubmessenger
Auteur  : CS-DEV (Cédric SALVAT)

Ce fichier ne contient QUE l'UI Android (NavigationBar en bas, SafeArea,
fenêtre étroite). Toute la logique métier (DB, parsing XLSX, filtres, SMTP)
est dans clubmessenger_core.py et importée via `from clubmessenger_core import *`.
"""

import os
import re
import json
import urllib.parse
import threading
from datetime import datetime

import flet as ft

# Toute la logique métier (constantes FFESSM, DB, parsing, filtres, SMTP…)
from clubmessenger_core import *  # noqa: F401,F403


class ClubMessengerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = APP_TITLE
        self.page.safe_area = True
        self.page.theme_mode = ft.ThemeMode.LIGHT
        # Dimensions fenêtre uniquement sur desktop (mobile = plein écran)
        try:
            plat = getattr(page, "platform", None)
            is_mobile = plat in (
                getattr(ft.PagePlatform, "ANDROID", None),
                getattr(ft.PagePlatform, "IOS",     None),
            )
            if not is_mobile and hasattr(page, "window"):
                self.page.window.width  = 420
                self.page.window.height = 900
        except Exception:
            pass
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
        try:
            self.page.services.append(self.file_picker)
        except Exception:
            # Fallback ancienne API : overlay
            try:
                self.page.overlay.append(self.file_picker)
            except Exception:
                pass

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
        # SafeArea : évite la superposition avec la status bar et le notch
        # sur Android/iOS. Sur desktop, c'est transparent.
        self.page.add(ft.SafeArea(content=self.content_area, expand=True))

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
                            btn_import,
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Row([btn_vider],
                               alignment=ft.MainAxisAlignment.END),
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

    def _launch_url(self, url: str):
        """Lance une URL externe (mailto:, tel:, sms:, http:).
        En Flet 0.85, page.launch_url est une COROUTINE : il faut la planifier
        via run_task, qui exige une fonction coroutine (async def). On enveloppe
        donc l'appel dans un wrapper async."""
        page = self.page
        async def _do_launch():
            try:
                await page.launch_url(url)
            except Exception as exc:
                # Affichage différé pour ne pas bloquer le launch
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
        nom_club_row = ligne("Club", nom_club, multi_ligne=True) if nom_club else ft.Container()

        def open_mail(_):
            club = get_param("nom_club_court")
            mode = get_param("mode_redaction") or "structure"
            if mode == "commission":
                commission = get_param("commission_redaction") or ""
                if commission:
                    sujet_str = f"Message de la commission {commission} du {club}"
                else:
                    sujet_str = f"Message du {club}"
            else:
                sujet_str = f"Message du {club}"
            sujet = urllib.parse.quote(sujet_str)
            self._launch_url(f"mailto:{email}?subject={sujet}")

        def open_tel(_):
            num = re.sub(r'[^\d+]', '', portable)
            self._launch_url(f"tel:{num}")

        def open_sms(_):
            num = re.sub(r'[^\d+]', '', portable)
            self._launch_url(f"sms:{num}")

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

        # Boutons d'action contact — icônes seules avec tooltip au survol
        # pour que les 3 boutons tiennent confortablement sur une ligne
        action_buttons = []
        if email:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.EMAIL,
                    tooltip="Envoyer un email",
                    on_click=open_mail,
                    bgcolor=ft.Colors.BLUE_700,
                    icon_color=ft.Colors.WHITE,
                )
            )
        if portable:
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.PHONE,
                    tooltip="Appeler",
                    on_click=open_tel,
                    bgcolor=ft.Colors.GREEN_700,
                    icon_color=ft.Colors.WHITE,
                )
            )
            action_buttons.append(
                ft.IconButton(
                    icon=ft.Icons.SMS,
                    tooltip="Envoyer un SMS",
                    on_click=open_sms,
                    bgcolor=ft.Colors.ORANGE_700,
                    icon_color=ft.Colors.WHITE,
                )
            )
        if action_buttons:
            contenu.controls.append(ft.Divider())
            contenu.controls.append(
                ft.Row(action_buttons, spacing=8,
                       alignment=ft.MainAxisAlignment.CENTER)
            )

        dlg = ft.AlertDialog(
            title=ft.Text("Fiche plongeur"),
            content=ft.Container(content=contenu, width=360, height=520),
            actions=[ft.TextButton("Fermer", on_click=fermer)],
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
            self.filtre_tokens = []
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

        # Expression booléenne de filtres commission, sous forme de liste de
        # tokens : items + opérateurs (OU/ET/NON) + parenthèses.
        # L'utilisateur compose l'expression dans l'ordre via les boutons.
        self.filtre_tokens: list = []

        # Affichage de l'expression logique (chips colorées)
        self.commissions_chips_row = ft.Row(wrap=True, spacing=4,
                                            run_spacing=4,
                                            vertical_alignment=ft.CrossAxisAlignment.CENTER)
        # Container avec les 12 boutons des commissions
        self.commissions_grid = ft.Column(spacing=4)
        # Boutons d'opérateurs : OU / ET / NON / ( / )  + Annuler le dernier
        self.rule_buttons_row = ft.Row(spacing=8, wrap=True)

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
            expand=True,
        )
        self.tf_corps = ft.TextField(
            label="Corps du message",
            multiline=True,
            min_lines=5,
            max_lines=10,
            expand=True,
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
                    ft.Row([
                        ft.Text("Filtres", weight=ft.FontWeight.BOLD, size=14),
                        ft.TextButton(
                            "Effacer les filtres",
                            icon=ft.Icons.FILTER_ALT_OFF,
                            on_click=self._on_effacer_filtres,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
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
                    ft.Row([self.tf_sujet], spacing=0),
                    ft.Row([self.tf_corps], spacing=0),
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

    def _on_effacer_filtres(self, e):
        """Réinitialise tous les filtres de l'onglet Composer."""
        self.filtre_tokens = []
        for cb in self.cb_type_licence.values():
            cb.value = False
            self._safe_update(cb)
        for cb in self.cb_categorie.values():
            cb.value = False
            self._safe_update(cb)
        self.tf_age_min.value = ""
        self.tf_age_max.value = ""
        self._safe_update(self.tf_age_min)
        self._safe_update(self.tf_age_max)
        for cb in self.cb_caci.values():
            cb.value = False
            self._safe_update(cb)
        self._refresh_commissions_chips()
        self._actualiser_destinataires()
        try:
            self.page.update()
        except Exception:
            pass
        self._show_snack("Filtres effacés.")

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
            "filtre_tokens": list(self.filtre_tokens),
            "types_licence": types_licence,
            "categories":    categories,
            "age_min":       to_int(self.tf_age_min),
            "age_max":       to_int(self.tf_age_max),
            "statuts_caci":  statuts,
            "avec_email":    (canal == "email"),
            "avec_portable": (canal == "sms"),
        }

    # ── Tokens de filtre : helpers ────────────────────────────────────────

    def _new_token_id(self) -> str:
        """Génère un identifiant unique pour un token item."""
        import uuid
        return uuid.uuid4().hex[:12]

    def _find_item_token(self, item_id: str):
        """Retourne le token item correspondant à l'ID, ou None."""
        for t in self.filtre_tokens:
            if t.get("type") == "item" and t.get("id") == item_id:
                return t
        return None

    def _add_token(self, token: dict):
        """Ajoute un token à la fin de l'expression et rafraîchit l'UI."""
        self.filtre_tokens.append(token)
        self._refresh_commissions_chips()
        self._actualiser_destinataires()

    def _add_op(self, op: str):
        """Ajoute un opérateur (OU / ET / NON)."""
        self._add_token({"type": "op", "value": op})

    def _add_paren_open(self):
        """Ajoute une parenthèse ouvrante."""
        self._add_token({"type": "paren_open"})

    def _add_paren_close(self):
        """Ajoute une parenthèse fermante après vérification : il doit y avoir
        une parenthèse ouverte non encore fermée."""
        nb_open  = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_open")
        nb_close = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_close")
        if nb_close >= nb_open:
            self._show_snack("Aucune parenthèse à fermer.", erreur=True)
            return
        self._add_token({"type": "paren_close"})

    def _undo_last_token(self):
        """Retire le dernier token de l'expression."""
        if not self.filtre_tokens:
            return
        self.filtre_tokens.pop()
        self._refresh_commissions_chips()
        self._actualiser_destinataires()

    # ── Commissions : grille, popup, chips ────────────────────────────────

    def _build_rule_buttons(self):
        """Construit les boutons d'opérateurs : OU / ET / NON / ( / )
        + un bouton 'Annuler le dernier' pour défaire."""
        self.rule_buttons_row.controls.clear()

        def chip_btn(label, color, handler, tooltip=None, width=None):
            return ft.Container(
                content=ft.Text(label, size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                text_align=ft.TextAlign.CENTER),
                bgcolor=color,
                border_radius=6,
                padding=ft.Padding(left=12, right=12, top=6, bottom=6),
                on_click=lambda _: handler(),
                ink=True,
                tooltip=tooltip,
                width=width,
            )

        self.rule_buttons_row.controls.extend([
            chip_btn("OU",  ft.Colors.BLUE_700,   lambda: self._add_op("OU"),  "Opérateur OU"),
            chip_btn("ET",  ft.Colors.BLUE_700,   lambda: self._add_op("ET"),  "Opérateur ET"),
            chip_btn("NON", ft.Colors.RED_700,    lambda: self._add_op("NON"), "Négation logique"),
            chip_btn("(",   ft.Colors.GREY_700,   self._add_paren_open,  "Parenthèse ouvrante", 50),
            chip_btn(")",   ft.Colors.GREY_700,   self._add_paren_close, "Parenthèse fermante", 50),
            chip_btn("⌫",   ft.Colors.GREY_500,   self._undo_last_token, "Annuler le dernier", 50),
        ])

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

    def _open_commission_popup(self, commission_nom: str, item_id: str = None):
        """Popup : choix du mode (tous_avec / selection / tous_sans) + liste des brevets.

        Si item_id est fourni : édition de cet item existant (modification sur place).
        Sinon : création d'un NOUVEL item ajouté à la fin de l'expression.

        Cela permet d'avoir plusieurs filtres sur la même commission (ex.
        Niveau 2 ET NON Niveau 3).
        """
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
            ft.Radio(value="tous_sans",
                     label="Tous les membres SANS brevet"),
        ]

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
                    self._show_snack("Aucun brevet sélectionné.", erreur=True)
                    return
                brevets = selectes
            else:
                brevets = []

            if existing is not None:
                # Édition sur place
                existing["mode"] = mode
                existing["brevets"] = brevets
            else:
                # Création d'un nouvel item ajouté à la fin de l'expression
                new_item = {
                    "type": "item",
                    "id": self._new_token_id(),
                    "commission": commission_nom,
                    "mode": mode,
                    "brevets": brevets,
                }
                self.filtre_tokens.append(new_item)
            self.page.pop_dialog()
            self._refresh_commissions_chips()
            self._actualiser_destinataires()

        def retirer(_):
            """Supprime ce token item de l'expression (édition uniquement)."""
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

        titre = commission_nom
        if existing is not None:
            titre += "   (modification)"

        dlg = ft.AlertDialog(
            title=ft.Text(titre, size=14),
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
        """Construit le chip visuel pour un item commission.
        Le clic ouvre la popup en mode édition (via item_id)."""
        nom = item.get("commission", "")
        mode = item.get("mode", "tous_avec")
        brevets = item.get("brevets", [])
        item_id = item.get("id", "")

        if mode == "tous_sans":
            bg = ft.Colors.RED_700
            icon = ft.Icons.BLOCK
        elif mode == "selection":
            bg = ft.Colors.INDIGO_700
            icon = ft.Icons.CHECKLIST
        else:
            bg = ft.Colors.BLUE_700
            icon = ft.Icons.CHECK

        if mode == "selection" and brevets:
            # Affichage compact : "Apnée: A1, A2" si peu de brevets, sinon "Apnée (n)"
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
                ft.Icon(icon, size=12, color=ft.Colors.WHITE),
                ft.Text(label, size=11, color=ft.Colors.WHITE),
            ], spacing=4, tight=True),
            bgcolor=bg,
            border_radius=12,
            padding=ft.Padding(left=8, right=10, top=4, bottom=4),
            on_click=lambda _, n=nom, iid=item_id:
                self._open_commission_popup(n, item_id=iid),
            ink=True,
        )

    def _refresh_commissions_chips(self):
        """Met à jour l'affichage de l'expression de filtres : tokens dans
        l'ordre, opérateurs en couleur, parenthèses, items en chips."""
        self.commissions_chips_row.controls.clear()

        if not self.filtre_tokens:
            self.commissions_chips_row.controls.append(
                ft.Text("(aucun filtre — tous les plongeurs)", size=11,
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
                        content=ft.Text(op, size=11,
                                        color=couleur,
                                        weight=ft.FontWeight.BOLD),
                        padding=ft.Padding(left=2, right=2, top=2, bottom=2),
                    )
                )
            elif ttype == "paren_open":
                self.commissions_chips_row.controls.append(
                    ft.Text("(", size=18, color=ft.Colors.GREY_900,
                            weight=ft.FontWeight.BOLD)
                )
            elif ttype == "paren_close":
                self.commissions_chips_row.controls.append(
                    ft.Text(")", size=18, color=ft.Colors.GREY_900,
                            weight=ft.FontWeight.BOLD)
                )

        # Indicateur visuel si parenthèses non fermées (sera auto-fermé à l'éval)
        nb_open  = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_open")
        nb_close = sum(1 for t in self.filtre_tokens if t.get("type") == "paren_close")
        if nb_open > nb_close:
            self.commissions_chips_row.controls.append(
                ft.Text(f" + {nb_open - nb_close} «)» auto-fermée(s)",
                        size=10, italic=True, color=ft.Colors.ORANGE_700)
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
        contribué à le faire passer les filtres commission.
        Parcourt les tokens 'item' de l'expression :
            * mode "tous_avec" : tous les brevets du plongeur dans cette commission
            * mode "selection" : ceux du plongeur ∩ ceux cochés
            * mode "tous_sans" : ignoré (condition de négation, pas de contribution)
        Si aucun token item : tous les brevets simplifiés du plongeur.
        """
        tokens = self.filtres_actifs.get("filtre_tokens") or []
        brevets_brut = p.get("brevets_brut", "")
        brevets_courts = []

        items = [t for t in tokens if t.get("type") == "item"]
        if items:
            for item in items:
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
                else:
                    cibles = brevets_dans_com
                brevets_courts.extend(brevet_court(b) for b in cibles)
        else:
            for _, court in parse_brevets(brevets_brut):
                brevets_courts.append(court)

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
        dest = self.destinataires_selectionnes

        # ── Mode SMS : ouverture directe de l'app SMS native (instantané) ──
        if canal == "sms":
            numeros = []
            for p in dest:
                portable = (p.get("portable", "") or "").strip()
                if not portable:
                    continue
                num_clean = re.sub(r'[^\d+]', '', portable)
                if num_clean:
                    numeros.append(num_clean)

            if not numeros:
                self._show_snack("Aucun destinataire avec un numéro de portable.",
                                 erreur=True)
                return

            # Historique AVANT le launch (opération DB, pas d'UI)
            # On consigne l'ouverture de l'app, pas l'envoi (non vérifiable).
            dest_ids = [p.get("id_licence", "") for p in dest]
            save_message_historique(
                canal, sujet, corps, self.filtres_actifs, dest_ids,
                nb_ok=0, nb_err=0,
            )

            # launch_url EN DERNIER : aucune action UI après, sinon Android
            # ramène le focus sur l'app et annule l'ouverture de l'app SMS.
            nums_str = ",".join(numeros)
            body_enc = urllib.parse.quote(corps)
            url = f"sms:{nums_str}?body={body_enc}"
            self._launch_url(url)
            return

        # ── Mode Email : envoi SMTP en arrière-plan avec progression ──
        prog = ft.AlertDialog(
            title=ft.Text("Envoi en cours…"),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Envoi des emails…"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
               tight=True),
            modal=True,
        )
        self.page.show_dialog(prog)

        def fermer_progress():
            """Ferme la dialog de progression de manière robuste depuis un thread."""
            try:
                prog.open = False
            except Exception:
                pass
            try:
                self.page.pop_dialog()
            except Exception:
                pass
            try:
                self.page.update()
            except Exception:
                pass

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

                dest_ids = [p.get("id_licence", "") for p in dest]
                save_message_historique(
                    canal, sujet, corps, self.filtres_actifs, dest_ids,
                    nb_ok, nb_err,
                )
            finally:
                # Fermeture systématique de la dialog même en cas d'exception
                fermer_progress()
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
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Historique des envois",
                                    size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    tooltip="Actualiser",
                                    on_click=lambda _: self._refresh_historique(),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_SWEEP,
                                    tooltip="Vider l'historique",
                                    icon_color=ft.Colors.RED_700,
                                    on_click=self._on_vider_historique,
                                ),
                            ], spacing=0),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], spacing=0),
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

    def _on_vider_historique(self, e):
        """Vide l'historique avec confirmation."""
        rows = load_historique(limit=1)
        if not rows:
            self._show_snack("L'historique est déjà vide.")
            return

        def annuler(_):
            self.page.pop_dialog()

        def confirmer(_):
            self.page.pop_dialog()
            truncate_historique()
            self._refresh_historique()
            try:
                self.page.update()
            except Exception:
                pass
            self._show_snack("Historique vidé.")

        dlg = ft.AlertDialog(
            title=ft.Text("Vider l'historique"),
            content=ft.Text(
                "Supprimer définitivement tout l'historique des envois ?"
            ),
            actions=[
                ft.TextButton("Annuler", on_click=annuler),
                ft.FilledButton("Vider", on_click=confirmer,
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE),
            ],
        )
        self.page.show_dialog(dlg)

    def _on_supprimer_message(self, id_msg: int):
        """Supprime un message de l'historique (sans confirmation)."""
        delete_historique(id_msg)
        self._refresh_historique()
        try:
            self.page.update()
        except Exception:
            pass

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
                                ft.Row([
                                    ft.Container(
                                        content=ft.Text(canal.upper(), size=10,
                                                        color=ft.Colors.WHITE),
                                        bgcolor=(ft.Colors.BLUE_600
                                                 if canal == "email"
                                                 else ft.Colors.GREEN_600),
                                        border_radius=4,
                                        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_size=18,
                                        tooltip="Supprimer ce message",
                                        icon_color=ft.Colors.RED_600,
                                        on_click=lambda _, mid=id_:
                                            self._on_supprimer_message(mid),
                                    ),
                                ], spacing=4,
                                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
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

        # ── Mode de rédaction : Switch + Dropdown ──
        # Switch ON  = "Écrire en tant que commission" (utilisera dropdown)
        # Switch OFF = "Écrire en tant que structure"  (utilisera nom_court_club)
        mode_actuel = get_param("mode_redaction") or "structure"
        commission_actuelle = get_param("commission_redaction") or ""

        # Dropdown : commissions FFESSM + activités transversales
        _all_dropdown_options = (
            [ft.DropdownOption(text=nom) for nom, _ in COMMISSIONS_FFESSM]
            + [ft.DropdownOption(key="_separator_", text="─" * 24, disabled=True)]
            + [ft.DropdownOption(text=nom) for nom, _ in FILTRES_TRANSVERSAUX]
        )
        dd_commission = ft.Dropdown(
            label="Commission ou activité transversale",
            dense=True,
            options=_all_dropdown_options,
            value=commission_actuelle if commission_actuelle else None,
            visible=(mode_actuel == "commission"),
        )

        # Label dynamique du switch
        lbl_switch_mode = ft.Text(
            "Écrire en tant que commission" if mode_actuel == "commission"
            else "Écrire en tant que structure",
            size=12, weight=ft.FontWeight.BOLD,
            expand=True,
        )

        def on_switch_change(e):
            mode = "commission" if e.control.value else "structure"
            lbl_switch_mode.value = ("Écrire en tant que commission"
                                     if mode == "commission"
                                     else "Écrire en tant que structure")
            dd_commission.visible = (mode == "commission")
            self._safe_update(lbl_switch_mode)
            self._safe_update(dd_commission)

        switch_mode = ft.Switch(
            value=(mode_actuel == "commission"),
            on_change=on_switch_change,
            active_color=ft.Colors.BLUE_700,
        )

        # Conserver les références pour la sauvegarde + reload
        self.switch_mode_redaction = switch_mode
        self.dd_commission_redaction = dd_commission
        self.lbl_switch_mode = lbl_switch_mode

        def sauvegarder(_):
            # Champs texte standards
            for cle, tf in params_fields.items():
                set_param(cle, tf.value.strip())
            # Mode de rédaction + commission éventuelle
            mode = "commission" if switch_mode.value else "structure"
            set_param("mode_redaction", mode)
            if mode == "commission":
                set_param("commission_redaction", dd_commission.value or "")
            else:
                set_param("commission_redaction", "")
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
                                        "départemental ou régional).",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True, no_wrap=False,
                                    ),
                                ], spacing=6),
                                params_fields["nom_club_court"],
                                params_fields["nom_club_long"],
                            ], spacing=8),
                            padding=12,
                        )),
                        # ── Section Mode de rédaction ──
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Mode de rédaction",
                                        weight=ft.FontWeight.BOLD),
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                            color=ft.Colors.BLUE_600),
                                    ft.Text(
                                        "Détermine la formulation des sujets de mails. "
                                        "« Structure » utilise le nom court du club/OD. "
                                        "« Commission » ajoute la commission choisie.",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True, no_wrap=False,
                                    ),
                                ], spacing=6),
                                ft.Row([
                                    lbl_switch_mode,
                                    switch_mode,
                                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                dd_commission,
                            ], spacing=8),
                            padding=12,
                        )),
                        ft.Card(content=ft.Container(
                            content=ft.Column([
                                ft.Text("Email — SMTP", weight=ft.FontWeight.BOLD),
                                ft.Row([
                                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16,
                                            color=ft.Colors.BLUE_600),
                                    ft.Text(
                                        "Pour un compte Gmail, utilisez un "
                                        "« mot de passe d'application » "
                                        "(la validation en 2 étapes doit être activée). "
                                        "Voir : myaccount.google.com → Sécurité → "
                                        "Mots de passe des applications.",
                                        size=11, color=ft.Colors.GREY_700,
                                        expand=True, no_wrap=False,
                                    ),
                                ], spacing=6),
                                params_fields["email_expediteur"],
                                params_fields["smtp_host"],
                                params_fields["smtp_port"],
                                params_fields["smtp_user"],
                                params_fields["smtp_password"],
                            ], spacing=8),
                            padding=12,
                            expand=True,
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
        # Mode de rédaction (switch + dropdown commission)
        if hasattr(self, "switch_mode_redaction"):
            mode = get_param("mode_redaction") or "structure"
            is_commission = (mode == "commission")
            self.switch_mode_redaction.value = is_commission
            self.lbl_switch_mode.value = ("Écrire en tant que commission"
                                          if is_commission
                                          else "Écrire en tant que structure")
            self.dd_commission_redaction.value = get_param("commission_redaction") or None
            self.dd_commission_redaction.visible = is_commission
            self._safe_update(self.switch_mode_redaction)
            self._safe_update(self.lbl_switch_mode)
            self._safe_update(self.dd_commission_redaction)

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
    """Point d'entrée Flet. Tout est encapsulé dans un try/except pour
    afficher l'erreur à l'écran en cas de plantage au démarrage (sinon
    écran noir invisible sur Android)."""
    try:
        init_db()
        ClubMessengerApp(page)
    except Exception as exc:
        import traceback
        tb = traceback.format_exc()
        try:
            page.bgcolor = "#FFE5E5"
            page.padding = 16
            page.safe_area = True
            page.add(
                ft.Column([
                    ft.Text("⚠ Erreur au démarrage",
                            size=20, weight=ft.FontWeight.BOLD,
                            color="#B00020"),
                    ft.Divider(),
                    ft.Text(f"{type(exc).__name__}: {exc}",
                            size=14, selectable=True),
                    ft.Container(
                        content=ft.Text(tb, size=10, selectable=True,
                                        color="#444444"),
                        bgcolor="#FFFFFF",
                        padding=8,
                        border_radius=4,
                    ),
                    ft.Text(
                        "Merci de signaler cette erreur au développeur.",
                        size=11, italic=True, color="#666666",
                    ),
                ], scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
            )
            page.update()
        except Exception:
            # Si même l'affichage de l'erreur échoue, on log au moins
            print(f"[FATAL] {exc}\n{tb}")


# Flet appelle main(page) automatiquement. Sur Android, le module est exécuté
# au démarrage, sans passer par __main__.
ft.run(main)
