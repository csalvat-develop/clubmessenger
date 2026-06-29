# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — ClubMessenger Desktop v1.3.3

Compilation :
    pyinstaller build_desktop.spec

Sortie : dist/ClubMessenger.exe (Windows), dist/ClubMessenger (Linux/macOS)

Ce spec embarque tous les data files et submodules de Flet (notamment
flet/controls/material/icons.json qui est chargé en lazy par Flet et donc
non détecté par l'analyse statique de PyInstaller).
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

# ── Collecte exhaustive des dépendances Flet ─────────────────────────────
# flet : framework UI (contient icons.json, fonts, assets…)
# flet_desktop : runtime natif desktop (binaire Flutter embarqué)
datas = []
binaries = []
hiddenimports = []

for pkg in ("flet", "flet_desktop", "flet_runtime"):
    try:
        datas        += collect_data_files(pkg)
        binaries     += collect_dynamic_libs(pkg)
        hiddenimports += collect_submodules(pkg)
    except Exception:
        # flet_runtime n'existe plus dans Flet 0.85+, on l'ignore
        pass

# Inclure le core métier (au cas où PyInstaller le manquerait)
hiddenimports.append("clubmessenger_core")

# Embarquer l'icône dans le bundle pour pouvoir la lire au runtime
# (page.window.icon = chemin vers le fichier extrait dans _MEIPASS)
datas += [("assets/ClubMessenger.ico", "assets")]


# ── Analyse ──────────────────────────────────────────────────────────────
a = Analysis(
    ["main_desktop.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

# ── Build exécutable unique ──────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ClubMessenger",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # UPX casse parfois les binaires natifs Flet
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                # mode fenêtré (pas de console noire)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/ClubMessenger.ico",
)
