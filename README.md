# ClubMessenger

Application mobile **Android** (et desktop via Flet) pour envoyer des messages ciblés aux membres d'un club ou d'un organe déconcetré de plongée **FFESSM** suivant leurs brevets.

> Version actuelle : **1.3.0**
> Bundle Android : `fr.csdev.clubmessenger`

## Fonctionnalités

- **Import FFESSM** (.xlsx ou .csv) avec parseur natif (sans pandas, compatible Android)
- **Fiche détaillée** de chaque plongeur (brevets, CACI, contact, etc.)
- **Composer** un message ciblé par :
  - Combinaisons logiques de filtres commission (Apnée, Bio, Tech, etc.) avec **OU / ET / parenthèses**
  - **Filtres transversaux** : Handisub, Activités Jeunes, Secourisme
  - 3 modes par commission : *tous les membres ayant un brevet*, *sélection précise*, *tous SANS brevet*
  - Type de licence : Pratiquant / Aidant
  - Catégorie : Enfant / Jeune / Adulte
  - Tranche d'âge
  - Statut CACI : Valide / Alerte / Périmé
- **Envoi via Email** (SMTP configurable) ou **SMS natif** (app SMS du téléphone)
- **Export CSV** des destinataires filtrés
- **Historique** des messages envoyés
- **Mode hors ligne** : toutes les données sont stockées localement en SQLite

## Prérequis

- Python 3.9 ou plus récent
- Flet 0.85.2


## Structure du projet

```
clubmessenger/
├── main.py                     # Point d'entrée Flet
├── pyproject.toml              # Config build (Flet, Android, iOS)
├── requirements.txt            # Dépendances Python
├── README.md                   # Ce fichier
├── LICENSE                     # Licence
├── .gitignore                  # Fichiers à exclure du dépôt
└── assets/
    ├── icon.png                # Icône 1024×1024 PNG
    └── icon.ico                # Icône Windows
```

## Build Android

### Prérequis (à installer une fois)

- **Flutter SDK** : <https://docs.flutter.dev/get-started/install>
- **Android Studio** + Android SDK (cmdline-tools)
- **Java JDK** 17

Configurer :

```bash
flutter doctor
flutter doctor --android-licenses
```

### APK (test direct sur appareil)

```bash
flet build apk
```

Sortie : `build/apk/app-release.apk` → copier sur le téléphone, ouvrir pour installer.


## Licence

Propriétaire — CS-DEV (Cédric SALVAT), 2026.

## Crédits

- Flet — <https://flet.dev>
- FFESSM — <https://ffessm.fr>
