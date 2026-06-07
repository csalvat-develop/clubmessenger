# Politique de confidentialité — ClubMessenger

**Dernière mise à jour : 7 juin 2026**
**Éditeur :** CS-DEV (Cédric SALVAT)
**Application :** ClubMessenger
**Identifiant Android :** `fr.csdev.clubmessenger`
**Contact :** [adresse@email à compléter]

---

## En résumé

ClubMessenger est une application **100 % locale**. Toutes les données importées et saisies dans l'application sont stockées **uniquement sur votre appareil** et ne sont transmises à aucun serveur de l'éditeur, à aucun service tiers, à aucune entreprise.

- ❌ Aucun compte utilisateur, aucune inscription, aucun mot de passe à créer
- ❌ Aucune télémétrie, aucun mouchard analytique, aucune publicité
- ❌ Aucune transmission de données vers le développeur ou un tiers
- ❌ Aucun accès à votre carnet d'adresses, votre géolocalisation, vos photos
- ✅ Les données restent dans le stockage privé de l'application sur l'appareil
- ✅ Vous pouvez supprimer toutes les données à tout moment depuis l'application

---

## 1. Données traitées

ClubMessenger permet aux responsables d'un **club ou organe déconcentré (OD) affilié à la FFESSM** de gérer les contacts de leurs licenciés afin de leur adresser des messages ciblés. À ce titre, l'application traite les catégories de données suivantes, **importées par vous depuis l'export officiel FFESSM** :

- Identité : nom, prénom, identifiant de licence, date de naissance, catégorie (enfant / jeune / adulte)
- Coordonnées : adresse email, numéro de téléphone portable
- Vie sportive : brevets et qualifications FFESSM, niveau, club ou OD d'appartenance, saison, type de licence (pratiquant / aidant)
- Santé : date de fin de validité du CACI (Certificat d'Absence de Contre-Indication à la pratique). **Aucune autre donnée médicale n'est traitée** — l'application n'enregistre que la date d'expiration, jamais le contenu du certificat.

Aucune donnée personnelle complémentaire n'est collectée à votre insu.

---

## 2. Lieu de stockage

Toutes les données sont stockées **localement** sur votre appareil dans une base SQLite située dans le **dossier privé de l'application** :

- **Android** : répertoire `data/data/fr.csdev.clubmessenger/files/` (accessible uniquement par l'application, conformément au sandbox Android)
- **Windows / macOS / Linux** : dossier `~/.clubmessenger/` dans votre répertoire personnel

Cette base **n'est pas synchronisée avec le cloud**, **n'est pas sauvegardée par l'éditeur**, et n'est accessible qu'à vous depuis votre appareil.

---

## 3. Connexions réseau de l'application

L'application établit des connexions réseau **uniquement dans les cas suivants**, et **uniquement à votre initiative explicite** :

### a) Envoi d'emails (SMTP)

Si vous configurez un serveur SMTP (Gmail, votre fournisseur de messagerie, etc.) dans les paramètres de l'application, l'envoi d'un message déclenche une connexion **directe** entre votre appareil et **ce serveur SMTP que vous avez choisi**. L'éditeur ne reçoit ni vos identifiants SMTP, ni le contenu des messages, ni la liste des destinataires.

Le fournisseur SMTP que vous utilisez (par exemple Google pour Gmail) traite alors les emails selon **sa propre politique de confidentialité**, qui s'applique indépendamment.

### b) Ouverture d'applications externes

L'application peut déclencher l'ouverture :
- de votre **client mail** par défaut (lien `mailto:`)
- de votre **application téléphone** par défaut (lien `tel:`)
- de votre **application SMS** native (lien `sms:`)

Ces ouvertures se font via les **intents standards** du système d'exploitation. ClubMessenger n'a aucun contrôle ni visibilité sur les traitements effectués par ces applications externes.

### c) Aucune autre connexion

L'application **n'envoie aucune donnée vers le développeur**, ne télécharge aucune mise à jour automatique de données, ne consulte aucun service externe.

---

## 4. Permissions Android demandées

| Permission                       | Pourquoi                                                                |
| -------------------------------- | ----------------------------------------------------------------------- |
| `INTERNET`                       | Envoi d'emails via le serveur SMTP que vous configurez                  |
| `READ_EXTERNAL_STORAGE`          | Importer le fichier FFESSM (.xlsx ou .csv) depuis votre stockage        |
| `READ_MEDIA_DOCUMENTS`           | Idem, version Android 13+                                               |
| `READ_MEDIA_IMAGES`              | Sélectionner une pièce jointe image pour un email                       |
| `SEND_SMS`                       | Ouvrir l'application SMS native pré-remplie (déclaration de capacité, l'envoi reste manuel via votre app SMS) |

Aucune permission n'est demandée pour : carnet d'adresses, géolocalisation, micro, caméra, calendrier, capteurs.

---

## 5. Pas de tracking, pas de publicité

ClubMessenger ne contient :

- ❌ aucun SDK publicitaire
- ❌ aucun service d'analyse (Google Analytics, Firebase Analytics, Crashlytics, etc.)
- ❌ aucun cookie ni identifiant publicitaire
- ❌ aucune intégration de réseau social
- ❌ aucun pixel de tracking

Aucune donnée comportementale, technique ou de diagnostic n'est transmise au développeur ou à un tiers.

---

## 6. Partage de données

L'éditeur **ne partage aucune donnée**, puisqu'**il n'en reçoit aucune**. Aucun transfert vers des tiers ne peut avoir lieu côté éditeur.

Vous restez le seul à pouvoir :
- envoyer des emails via votre serveur SMTP (le contenu transite alors par votre fournisseur de messagerie)
- ouvrir votre application SMS native (le SMS transite alors via votre opérateur mobile)
- exporter manuellement les destinataires filtrés en CSV depuis l'application

---

## 7. Durée de conservation

Les données sont conservées **tant que vous le souhaitez**, sur votre appareil. L'application met à votre disposition deux fonctions de suppression dans **Paramètres → Données** :

- **Vider la base des membres** : supprime tous les plongeurs importés (conserve l'historique des messages et les paramètres SMTP)
- **Suppression totale des données** : supprime plongeurs, historique des messages et paramètres du club (double confirmation requise)

La désinstallation de l'application supprime également l'intégralité des données.

---

## 8. Responsabilités RGPD

Dans le cadre du Règlement Général sur la Protection des Données (RGPD) :

- L'éditeur (CS-DEV) **n'est pas responsable de traitement** au sens du RGPD, car il ne collecte, ne stocke ni ne traite aucune donnée personnelle.
- **Le responsable de traitement est l'utilisateur du club** (président, secrétaire, responsable de commission, etc.), qui détient les données FFESSM et les utilise pour ses besoins associatifs internes.
- À ce titre, le club doit informer ses licenciés des traitements effectués et respecter les principes du RGPD (finalité, minimisation, durée de conservation, droits des personnes).

Les données FFESSM utilisées dans l'application proviennent de l'export licenciés mis à disposition par la FFESSM aux clubs et OD. Les conditions d'utilisation de ces données sont définies par la FFESSM.

---

## 9. Droits des personnes

Les licenciés dont les données figurent dans l'application disposent, conformément au RGPD, des droits suivants : accès, rectification, effacement, limitation, opposition, portabilité.

**Ces droits doivent être exercés auprès du club ou OD** qui utilise l'application (le responsable de traitement), et non auprès de l'éditeur de l'application.

L'éditeur n'a aucun moyen technique d'accéder aux données traitées dans l'application.

---

## 10. Sécurité

- Les données sont stockées dans le sandbox privé de l'application Android, isolé des autres apps.
- Les paramètres SMTP (y compris le mot de passe) sont stockés en local dans la base SQLite sans chiffrement supplémentaire. Pour Gmail, l'usage d'un **mot de passe d'application** (au lieu du mot de passe principal du compte) est recommandé et documenté dans l'application.
- L'éditeur recommande de protéger l'accès à l'appareil par un verrouillage (code PIN, empreinte, etc.).

---

## 11. Mineurs

L'application est destinée à un usage **par les responsables adultes** d'un club ou d'un OD. Les fiches plongeurs peuvent contenir des données de licenciés mineurs (catégories "Enfant" / "Jeune") dans la mesure où ceux-ci sont membres du club. La gestion du consentement parental relève du **club responsable**.

---

## 12. Modifications de cette politique

Cette politique peut être mise à jour pour refléter les évolutions de l'application ou de la législation. La date en haut du document indique la dernière révision. Pour les modifications significatives, une notification pourra apparaître au lancement de l'application.

---

## 13. Contact

Pour toute question concernant cette politique de confidentialité :

**CS-DEV** — Cédric SALVAT
Email : [adresse@email à compléter]

Pour toute question concernant **vos données personnelles** présentes dans l'application (droits d'accès, rectification, effacement) : **adressez-vous au club ou OD** qui utilise ClubMessenger.

---

*ClubMessenger est un logiciel propriétaire édité par CS-DEV. Sa diffusion est limitée aux clubs et organes déconcentrés affiliés à la FFESSM. Voir le fichier LICENSE pour plus de détails.*
