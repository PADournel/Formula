# FORMULA : document de référence complet

État au **12/11/2026** : **Windows 0.9.023** (branche `master`), **Linux / Steam Deck 0.7.025** (branche `linux`).
Dépôt : `G:\FORMULA` → https://github.com/PADournel/Formula (`docs/REFERENCE.md` sur les deux branches).
Copie pour l'utilisateur : `D:\OneDrive 26-09-26\Desktop\FORMULA - passation.md`.

Ce fichier remplace toutes les passations précédentes : un nouveau fil doit pouvoir démarrer en lisant ce seul
document. D'autres fils publient en parallèle dans le même dépôt : avant d'agir, faire `git fetch --tags`,
regarder `git log` et les étiquettes. Le `README.md` reste la documentation officielle pour l'utilisateur (liste
exhaustive du réseau, des processus et des fichiers écrits) : toute nouveauté doit y être reportée aussi.

Sommaire : 1 Présentation · 2 Règles de l'utilisateur · 3 Machines et accès · 4 Architecture · 5 Chemins ·
6 Branches, versions, déploiement · 7 formula.py en détail · 8 Émulateurs et configs · 9 Profils, sauvegardes,
kDrive · 10 Jaquettes · 11 Interface et manette · 12 Gestionnaire de jeux · 13 Synchro · 14 Bibliothèque de jeux ·
15 PS3 et Vita : chiffrement, clés, état · 16 Leçons et pièges · 17 Pistes ouvertes · 18 Historique des versions.

---

## 1. Présentation

**FORMULA** est un lanceur d'émulateurs façon bibliothèque Steam, développé pour l'utilisateur (P.A.D, GitHub
`PADournel`). Même interface web sur **Steam Deck (Linux)** et **PC Windows** :
- galerie avec jaquettes officielles (WebP), tri par console avec logos officiels, recherche, favoris, récents ;
- navigation complète à la manette (la fenêtre au premier plan garde les commandes), souris, tactile ;
- lance le bon émulateur en plein écran, en français quand c'est possible ;
- profils façon Netflix (« Qui joue ? », 4 max, compte parent à code) avec sauvegardes par profil dans kDrive,
  communes au PC et au Deck ;
- synchronisation des jeux entre appareils (service de fond, reprise, file d'attente) ;
- gestion des émulateurs (installer / désinstaller) et des jeux (gestionnaire avec corbeille) ;
- écran de démarrage : logo **OnTrack Software** ~1,4 s puis « Qui joue ? » en fondu ;
- interface en anglais par défaut, français dans Paramètres. Version affichée en bas à gauche (« v0.9.023 · Windows »).

Consoles : PS2, PSP, PS Vita, PS3, PS4, NES, N64, GBA, DS, GameCube, Wii, Xbox, Xbox 360. Pas de Xbox One
(aucun émulateur public jouable ; XWine1 annoncé mais pas téléchargeable).

---

## 2. Règles de l'utilisateur (à respecter absolument)

- **Ton** : français, simple, factuel et neutre. Pas d'injonctions ni de leçons (« la prochaine fois, ferme… » a été
  mal vécu). Formuler les contraintes comme des faits, proposer plutôt qu'ordonner.
- **Sécurité et transparence avant tout** : FORMULA ne doit jamais ressembler à un logiciel espion (le premier
  lancement PC avait fait clignoter des dizaines de consoles ffmpeg + une invite de synchro Edge : « on aurait vraiment
  dit un logiciel espion »). Donc :
  - `CREATE_NO_WINDOW` pour tout sous-processus sous Windows ;
  - aucun appel réseau inutile, aucune télémétrie, polices embarquées, CSP ;
  - services réseau restreints (UI sur 127.0.0.1, synchro LAN + jeton) ;
  - pas de démarrage automatique ajouté sans accord ;
  - pas de navigateur qui s'ouvre seul : si vraiment indispensable, fenêtre explicative Oui/Non d'abord ;
  - tout ce qui touche au réseau, aux processus ou au disque est documenté dans le README (« Sécurité et transparence ») ;
  - tester un vrai premier lancement avant de dire à l'utilisateur d'essayer.
- **Copie de jeux** : ne copier sur le Deck **que** les jeux nommés par l'utilisateur. Si la demande est ambiguë,
  demander lequel (une ligne). Ne jamais piocher dans Téléchargements de sa propre initiative (il y a des
  téléchargements en cours ou d'autres versions). Proposer, oui ; copier sans demande, non.
- **PS3 déchiffrés** : tout jeu PS3 disque déchiffré sur PC doit aussi remplacer sa copie sur le Deck si elle y est
  (ou quand l'utilisateur valide la copie vers le Deck), puis ses paquets de mise à jour y sont installés.
- **Clés et sources** : pas de recherche de clés (.dkey, zRIF, licences) ni de torrents par Claude. Les clés viennent
  de l'utilisateur.
- **Mises à jour** : les émulateurs peuvent se mettre à jour seuls ; les **jeux** ne doivent pas se mettre à jour
  automatiquement (FORMULA installe seulement les paquets de mise à jour que l'utilisateur dépose à côté du jeu).
  Exception côté émulateur : l'auto-update de l'AppImage Vita3K est coupé (popups au lancement).
- **Suppression** : rien n'est effacé définitivement sans accord explicite et sans avoir regardé le contenu.
  Préférer la corbeille (Windows), `gio trash` / corbeille FORMULA (Deck), dossiers `*.avant-…`, `_backups`.
- **`G:\Jeux\Bloodborne`** ne fait pas partie de FORMULA et est précieux tel quel : n'y rien lire ni écrire.
  Travailler uniquement dans `G:\FORMULA` (code) et `G:\Jeux\FORMULA` (données). (Le dossier mémoire de Claude
  `C:\Users\iridi\.claude\projects\G--Jeux-Bloodborne\memory` et la clé `~/.ssh/bloodborne_deck` portent ce nom mais
  sont ailleurs.) Sur le Deck : ne pas toucher à l'installation de Bloodborne ni à kDrive sans demande.
- **Git** :
  - commits **en anglais** (les 4 premiers sont en français, l'historique reste tel quel) ;
  - auteur `PADournel <paulalexandre.dournel@gmail.com>` + ligne `Co-Authored-By: Claude …` ;
  - **accord permanent pour pousser** sur GitHub ; pas de force-push ;
  - jamais dans git : émulateurs, BIOS / firmwares (fichiers Sony/Microsoft protégés), jeux, Python
    (droits d'auteur + limite GitHub de 100 Mo).
- **Versionnage : Claude en est responsable** (voir §6).
- **Passation** : remettre à jour ce document (et sa copie sur le bureau) après chaque travail terminé.

---

## 3. Machines et accès

### PC principal THEMIS (Windows 11)
- IP Ethernet `192.168.1.97`, Wi-Fi `192.168.1.151`, nom `THEMIS` / `THEMIS.local`.
- kDrive : `C:\Users\iridi\kDrive`. Bureau : `D:\OneDrive 26-09-26\Desktop`.
- Disques : C: a été plein (collection PS2 dans `C:\Users\iridi\Downloads`, déplacée vers `G:\Downloads`).
  La corbeille de G: fait ~97 Go : au-delà Windows supprime définitivement (déjà arrivé le 12/11).
- **Pas de Python système** : utiliser `G:\Jeux\FORMULA\python\pythonw.exe` / `python.exe` (embarqué 3.15).
- Outils : `C:\Windows\System32\tar.exe` (ouvre zip, 7z, rar ; le tar de Git Bash non), `C:\Program Files\7-Zip\7z.exe`
  (rar multi-volumes), ffmpeg (winget), git, `gh`, compilateur C# `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`
  (C# 5, .NET 4.x).
- Lancer un programme détaché depuis Claude : `explorer.exe "chemin\raccourci.lnk"`. Ne jamais lancer Steam avec
  `Start-Process` (il mourrait avec Claude).
- Fermer FORMULA : `Invoke-RestMethod -Method Post http://127.0.0.1:47800/api/quit`.

### Portable HG_laptop1
- FORMULA dans `C:\Users\iridi\FORMULA`.

### Steam Deck
- `ssh -i ~/.ssh/bloodborne_deck deck@192.168.1.89` (clé autorisée), nom `steamdeck.local`.
- **Pas de sudo** : l'utilisateur a perdu le mot de passe sudo du Deck (Claude ne tape jamais de mot de passe), et
  polkit refuse les opérations système en SSH. Donc flatpaks en `--user` (remote flathub `--user`), aucune modif système.
- Le Deck se met en veille et coupe le SSH : tâches longues en
  `systemd-run --user --unit=X --collect systemd-inhibit --what=sleep:idle --why=… <commande>`
  (un `systemd-inhibit` mis en fond simple meurt avec la session SSH). Arrêter l'inhibiteur ensuite.
- Le Deck redémarre parfois en pleine copie : prévoir la reprise (voir §13).
- `pgrep -f` / `pkill -f` en SSH attrapent la commande SSH elle-même : utiliser `pgrep -x` ou des motifs ancrés `^…`.
  Fermer FORMULA à distance : tuer `pgrep -f "^python3 /home/deck/Applications/Formula/formula.py"` (formula.sh tue
  alors Chromium) et l'émulateur (`pgrep -x pcsx2-qt`…).
- Ne **jamais** définir de variable d'affichage globale (`DISPLAY` dans `environment.d`) : gamescope a bouclé (écran noir).
  Ne jamais lancer Steam ou un jeu comme processus enfant de Claude.
- Écran noir en mode Jeu (seul le menu de gauche visible), déjà vu 28/10 et 08/11 : Steam > Alimentation > Redémarrer
  Steam, ou redémarrer le Deck ; ce n'est pas causé par les émulateurs.
- `gio trash --empty` ne marche pas en SSH (pas de gvfs) : vider = supprimer `~/.local/share/Trash/{files,info}/*`
  (seulement avec accord).
- kDrive Deck : client 3.8.8.1, `kdrive.service` (systemd user) réglé en **`Restart=always`** (il était mort du 09/11
  au 11/11 : crash à la perte de X11, relance « Server already running » code 0, et `Restart=on-failure` ne relançait
  pas). Si profils ou sauvegardes divergent entre PC et Deck : d'abord `systemctl --user status kdrive.service`.
  Synchro sélective : seuls `Saves` et `Formula` en local, le reste (Streaming, Images, Solfegia, ENSEIGNEMENT…) en
  ligne seulement. Liste noire = table `sync_node(nodeId, type=1)` de `~/.config/kDrive/.sync_373831376164.db`,
  à modifier **service arrêté** (sauvegarde `~/.config/kDrive.bak-20261111`).
- Espace : `/home` 464 Go, ~57 Go libres au 12/11.
- Autres flatpaks utilisateur hors FORMULA : qBittorrent 5.3.0, VLC 3.0.24, GNOME Network Displays 0.99.
  Claude Code installé dans `~/.local/bin/claude` (pas dans le PATH).

### Ce que le mode automatique de Claude bloque
Exécuter des binaires téléchargés (en SSH notamment), ajouter un démarrage automatique (dossier Startup, unités
systemd persistantes), force-push, `rm -rf` sur de gros dossiers, ouvrir certains émulateurs pour « vérifier ».
Dans ces cas, expliquer et laisser l'utilisateur décider.

---

## 4. Architecture

```
formula.py          serveur (bibliothèque standard Python uniquement) : bibliothèque, jaquettes, lancement,
                    manette, profils, synchro, gestionnaire d'émulateurs, gestionnaire de jeux
formula.sh          lanceur Deck (serveur + Chromium flatpak en mode appli) ; doit être 100755 dans git
VERSION             version de la branche
debug-games.json    jeux PS2 lancés avec PCSX2 debug (§8)
web/                index.html, app.js, app.css, logos/ (consoles), emulogos/ (émulateurs),
                    fonts/ (Inter, Outfit, licence OFL), brand/ontrack.webp (logo du splash, 900 px)
art/                icône, visuels Steam (portrait, wide, hero, logo), logos-src/ (SVG Wikimedia)
tools/              (master seulement) install_windows.py, setup_windows.py, steam_shortcut.py,
                    templates/ (PCSX2.ini, melonDS.toml…), winhost/FormulaHost.cs
docs/               REFERENCE.md (ce fichier), captures
icon.png, icon.ico  (icon.ico : master seulement)
formula-base.txt    non suivi : chemin des données Windows (G:\Jeux\FORMULA)
.gitattributes      fins de ligne LF (le Deck en a besoin)
```

### Modes de `formula.py`
- **sans option** : serveur d'interface sur `127.0.0.1:47800` (`FORMULA_PORT` pour changer).
- **`--host <pid>`** (Windows) : lancé par FORMULA.exe, s'arrête si l'exe meurt.
- **`--window`** (Windows) : ouvre simplement FORMULA.exe (compatibilité).
- **`--sync`** : service de synchro sur le port 47810 (§13).
- Variables utiles en test : `FORMULA_BASE` (base de données jetable), `FORMULA_PORT`.

### Fenêtre Windows : `FORMULA.exe`
- WinForms + WebView2 (moteur web de Windows), source `tools/winhost/FormulaHost.cs`, compilé par
  `install_windows.py <base> --host-only` avec csc.exe Framework64 et le NuGet officiel `Microsoft.Web.WebView2`
  (version fixée dans le script ; DLL dans `<base>\host`, profil web `<base>\formula-data\webview2`).
- Lit le dossier du code dans **`<base>\formula-data\code-dir.txt`**, lance `pythonw formula.py --host <pid>` sans
  fenêtre, attend le port, affiche **uniquement** `http://127.0.0.1:47800/`. Se ferme quand le serveur s'arrête
  (`/api/quit`), et arrête le serveur s'il est fermé.
- Refuse toute autre adresse, nouvelle fenêtre, téléchargement, permission ; outils de dev, menus, zoom, remplissage
  auto, SmartScreen désactivés ; pas de synchro de compte, pas de tâches réseau de fond.
- La page ne peut lui envoyer que `fullscreen:1` / `fullscreen:0` (le reste est ignoré).
- Ouvre en fenêtre redimensionnable (2/3 de la zone de travail, centrée, min 640×420). Plein écran par Paramètres >
  Affichage (affiché seulement si `window.chrome.webview` existe) ou F11 (géré **dans la page**, car WebView2 avale les
  touches), choix gardé dans `settings.json` (`fullscreen`), lu au démarrage. `web.Focus()` à la navigation et à
  l'activation (sinon la première touche est perdue).
- Si WebView2 ne démarre pas : question Oui/Non avant d'ouvrir Edge en mode application + InPrivate.

### Fenêtre Deck
- `formula.sh` lance le serveur puis `flatpak run --user org.chromium.Chromium --app --kiosk --ozone-platform=x11`
  (profil `~/.var/app/org.chromium.Chromium/formula-profile`), avec les mêmes restrictions de lancement.
- Le raccourci Steam exécute formula.sh directement : s'il perd son bit exécutable, Steam ferme FORMULA aussitôt
  (voir `~/.local/share/Steam/logs/console_log.txt`, « Game process removed »).

### Démarrage (splash et transition, 0.9.021-0.9.023 / 0.7.023-0.7.025)
- Fond noir opaque dès le démarrage ; logo OnTrack Software (`web/brand/ontrack.webp`, 900 px) dont seul le contenu
  apparaît en fondu. Le splash reste affiché tant que « Qui joue ? » n'est pas prêt (1,35 s minimum, 8 s maximum :
  évite le flash de la bibliothèque), entrées manette/clavier ignorées pendant le logo (`splashHandle`), puis
  « Qui joue ? » en fondu 0,35 s.
- Transition profil → bibliothèque (0.9.023 / 0.7.025) : le sélecteur s'agrandit, se floute et s'efface en 0,4 s ;
  la colonne des consoles glisse depuis la gauche, le contenu apparaît en fondu, les jaquettes en cascade.

---

## 5. Chemins

| | Windows (THEMIS) | Steam Deck |
|---|---|---|
| Code | `G:\FORMULA` (branche **master** ; ne pas changer de branche : raccourcis et synchro tournent depuis là) | `~/Applications/Formula` |
| Données FORMULA | `G:\Jeux\FORMULA\formula-data` | `~/.local/share/formula` |
| Jeux | `G:\Jeux\FORMULA\roms\<id>` | `~/Emulation/roms/<id>` |
| BIOS / firmwares | `G:\Jeux\FORMULA\bios\{ps2,ps3,psvita,xbox}` | `~/Emulation/bios/{ps2,ps3,psvita,xbox}` |
| Émulateurs | `G:\Jeux\FORMULA\emulators\<nom>` (portables, fichier `.formula-version`) | flatpaks `--user` + `~/Emulation/{ps4,x360,psvita,pcsx2-debug}` |
| Python | `G:\Jeux\FORMULA\python` (embarqué 3.15) | système |
| Sauvegardes | `C:\Users\iridi\kDrive\Saves` | `/home/deck/kDrive/Saves` |
| Corbeille FORMULA | `G:\Jeux\FORMULA\_corbeille` | `~/Emulation/_corbeille` |
| Sauvegardes de sécurité | `G:\Jeux\FORMULA\_backups` | `~/Emulation/_backups` |

Ids de consoles (dossiers `roms/<id>`) : `ps2 psp psvita ps3 ps4 nes n64 gba nds gc wii xbox x360`.

Contenu du dossier de données : `library.json`, `covers/` (WebP), `settings.json` (langue, plein écran),
`sync.json` (jeton : **ne jamais le recopier dans un message ni dans git**), `sync_status.json`, `sync_known.json`,
`profiles/<id>.json`, `profiles-shared.json`, `profiles-migrated.json`, `repo_<nom>.json` (index de dépôts de
jaquettes, 14 jours), `last_launch.log`, `code-dir.txt` (Windows), `webview2/` (Windows).

Autres éléments Windows hors git : `G:\Jeux\FORMULA\FORMULA.exe`, `host\` (DLL WebView2),
`FORMULA synchro.lnk` (lance `formula.py --sync`), `_build\` (NuGet WebView2), `_staging_new\` (extractions Vita).

Autres éléments Deck : lanceurs individuels `~/Emulation/launchers/*.sh`, `~/.config/systemd/user/formula-sync.service`
(activé, `Nice=10`, IO idle), `~/.config/formula/systems.json` possible pour ajouter des consoles.

### Raccourcis
- **Bureau PC** : `D:\OneDrive 26-09-26\Desktop\FORMULA.lnk` → `G:\Jeux\FORMULA\FORMULA.exe`.
- **Steam PC** (compte `newgodii`, userdata `99696636`) : créé par `tools/steam_shortcut.py` (met à jour l'entrée si
  elle existe, visuels dans `config\grid`). Appid actuel 2340346718 (l'ancien 2452206040 avait disparu de
  shortcuts.vdf). **Steam doit redémarrer** pour voir le changement.
- **Steam Deck** : « FORMULA » appid 2408588416, rungameid 10344808476277997568, visuels dans
  `userdata/99696636/config/grid`. Un raccourci par émulateur aussi (PS2, PSP, PS3, PS4, NES, N64, GBA, DS,
  Wii/GameCube) via `steamos-add-to-steam` sur des `.desktop` de `~/.local/share/applications`.
- **Bureau Deck** : `~/Desktop/FORMULA.desktop` → `steam steam://rungameid/…` (passe par Steam pour que Steam Input
  donne une manette en mode Bureau ; lancé directement, on aurait la config souris/clavier du bureau).
- **Steam Input Deck** pour FORMULA : `Steam Controller Configs/99696636/config/formula/controller_neptune.vdf`
  (clé `"formula"` `autosave 1` dans `configset_controller_neptune.vdf`) : **L4 = touche Windows**, **R4 = touche T**
  (bascule tactile avant/arrière de Vita3K). Sauvegardes `.bak-formula`, `.bak-20261107`, `.bak-avant-R4`. Redémarrer
  Steam pour recharger. Un `\"binding\"` mal échappé avait fait ignorer la config le 07/11.

---

## 6. Branches, versions, déploiement

### Versions
- Format `MAJEUR.MINEUR.CORRECTIF`, correctif sur 3 chiffres (`0.9.021`) : MAJEUR = changement profond (format des
  données, refonte), MINEUR = nouvelle fonctionnalité, CORRECTIF = correction ou petit ajustement.
- Une version **par plateforme**, chacune sur sa branche : `master` = Windows, `linux` = Steam Deck. Fichier `VERSION`
  à la racine, affiché en bas à gauche. Étiquettes `windows-vX.Y.ZZZ` / `linux-vX.Y.ZZZ` (anciennes `windows-v0.1`,
  `linux-v0.1` gardées). Un changement qui ne concerne qu'une plateforme ne monte que sa version.
- Flux : changement concluant → commit sur chaque branche concernée → `VERSION` monté → étiquette → push.
  Toujours `git fetch --tags` avant de choisir un numéro (fils parallèles).
- `windows-v0.3.001` / `linux-v0.3.001` ne contiennent qu'un changement de numéro (correction oubliée, vraie correction
  en 0.3.002).
- Un changement purement documentaire (comme ce fichier) ne monte pas de version.

### Branches
- `G:\FORMULA` reste sur **master**.
- `linux` n'a pas `tools/` ni `icon.ico`. Depuis la 0.5, `web/` et `formula.py` de master ont des fonctions propres à
  Windows (et linux a des correctifs propres au Deck : caches shaders, manette RPCS3 SDL…). Donc **jamais**
  `git checkout master -- web` en bloc sur linux : reporter commit par commit (`git cherry-pick`, en retirant `tools/`).
- Committer sur linux sans quitter master : par plomberie
  ```
  export GIT_INDEX_FILE=$(mktemp); git read-tree linux
  git update-index --add --cacheinfo 100644,<blob>,<chemin>   # blob = git hash-object -w <fichier>
  T=$(git write-tree); C=$(git commit-tree $T -p linux -m "…"); git update-ref refs/heads/linux $C
  unset GIT_INDEX_FILE
  ```
  ou cherry-pick dans un clone temporaire (scratchpad), puis push de la branche.

### Déployer sur le Deck
- Toujours **tout l'arbre linux** :
  `git archive linux | ssh -i ~/.ssh/bloodborne_deck deck@192.168.1.89 'tar -x -C ~/Applications/Formula'`,
  puis comparer les md5 des fichiers avec la branche. (Déployer seulement `app.js` avait cassé l'UI : index.html et
  app.css du Deck étaient plus vieux.)
- `git archive` sous Windows peut convertir VERSION/README en CRLF (autocrlf) : `sed -i 's/\r$//'` sur le Deck si besoin
  (surtout pour `.sh` et `.py`).
- Vérifier que `formula.sh` reste exécutable.
- FORMULA déjà ouvert ne prend le nouveau code qu'au prochain démarrage.

### Tester
- Serveur de test sur un autre port : `FORMULA_PORT=47899 python3 formula.py` (Deck) ou avec `FORMULA_BASE` vers une
  base jetable + patch de `fetch_covers`, `PROFILES.migrate`, `PROFILES.root` ; fermer par `POST /api/quit`.
  Scripts SSH longs : heredoc via `ssh … 'bash -s'`.
- Après un démarrage, la récupération des jaquettes peut prendre >45 s (index libretro) : interroger `/api/library`
  plutôt qu'attendre un délai fixe. `/api/library` n'a pas de champ `path` : faire la correspondance par titre.
- Aperçu de l'UI du Deck : tunnel `ssh -L 47801:127.0.0.1:47800` + navigateur intégré (Chromium headless
  `--screenshot` ne se termine plus à cause du SSE).
- PC : tests par FORMULA.exe + SendKeys + captures (scripts dans le scratchpad).

### Installer sous Windows (machine neuve)
```
python tools\install_windows.py G:\Jeux\FORMULA
```
Télécharge Python embarqué (python.org 3.15.2) et les émulateurs aux versions fixées, crée l'arborescence, lance
`setup_windows.py` (configure portable, manettes, français, sauvegardes, à partir de `tools/templates`), compile
FORMULA.exe, crée le raccourci du bureau. Relançable ; `--update` réinstalle les émulateurs ; `--host-only` recompile
seulement FORMULA.exe. BIOS/firmwares non fournis.

---

## 7. `formula.py` en détail

### Plateforme
`IS_WIN` choisit les chemins. Sous Windows `BASE` vient de `formula-base.txt` ou `FORMULA_BASE`. `SYSTEMS` liste les
consoles (commandes flatpak sur le Deck, `WIN_CMDS` sous Windows, motifs comme `mgba/*/mGBA.exe` résolus au
lancement). Ajouter une console : entrée dans `SYSTEMS` (+ `WIN_CMDS`) ou dans `systems.json`, déclarer ses dossiers
de sauvegarde dans `save_targets()`, écrire explicitement ses touches de manette, lui donner les overrides flatpak.

### Lecture des jeux (`scan_file`)
- PS2 : `SYSTEM.CNF` + `GameIndex.yaml` de PCSX2 (série, titre).
- PSP : `PARAM.SFO` dans ISO / CSO / PBP, avec ICON0 et PIC1. Symboles ™®© retirés des titres.
- PS3 : dossier disque (`PS3_GAME/PARAM.SFO`) ou dossier PSN avec `.pkg` + `.rap` (titre et images pris du jeu installé).
- PS4 : `PARAM.SFO` en dossier (CUSAxxxxx déchiffrés).
- PS Vita : `.vpk`, dossier (`sce_sys/param.sfo` + `eboot.bin`) ou `.pkg` : param.sfo lu dans la couche externe du PKG
  (AES pur Python, `VitaPkg`, clés publiques) sans déchiffrer le jeu ; icône/fond pris du jeu installé
  (`ux0/app/<TID>/sce_sys`) car chiffrés PFS dans le paquet.
- GC/Wii : en-tête ISO / WBFS / RVZ / CISO. GBA et DS : code dans l'en-tête.
- Xbox 360 : identifiant de titre lu dans `default.xex` de l'ISO XGD (partitions XDVDFS 0x2080000 / 0xFD90000 /
  0x18300000 / 0).
- Ignorés : dossiers `-UPDATE`, `pkg/`, fichiers `(Update vX).pkg`.

### Lancement (`Runner`, `launch()`)
- Windows : `CREATE_NO_WINDOW`, chemins résolus. Deck : variables X11 par processus (§8), `MESA_SHADER_CACHE_DIR`
  par flatpak (§8).
- Commandes de base : PCSX2 `-batch -nogui -fullscreen -- <jeu>`, PPSSPP `--fullscreen`, RPCS3 `--no-gui`,
  shadPS4 `-g <eboot> --fullscreen true` (cwd `~/Emulation/ps4`), mGBA `-f`, melonDS `-f`, Dolphin `-b -e`,
  RMG `--fullscreen --nogui --quit-after-emulation`, Vita3K `--frontend sdl -F -r <TITLEID>`.
- Avant chaque lancement : `Profiles.apply()` (sauvegardes du profil actif), préparation propre à la console
  (`ps3_prepare`, `vita_prepare`, `rpcs3_set_pad`, PCSX2 debug…). Journal : `last_launch.log`.

### Gestionnaire d'émulateurs (Paramètres > Emulators, `EMULATORS` + `EmuManager`)
- Affiche installé / version / taille, logos `web/emulogos/*.webp`.
- Installer : dernière version GitHub sous Windows (Dolphin Windows en version fixée), `flatpak install --user` sur le
  Deck, AppImage pour shadPS4, Xenia, Vita3K, PCSX2 debug (entrée `appimage` avec `dir` → `~/Emulation/<dir>`, AppImage
  directe ou dans un zip). Installer PCSX2 installe aussi PCSX2 debug.
- Désinstaller garde sauvegardes et réglages ; sous Windows les jonctions kDrive sont retirées avant suppression ;
  Vita3K Deck : `Vita3K-AppDir` supprimé aussi.
- Confirmation Oui (A) / Non (B). Testé pour de vrai sur PC (Nestopia désinstallé/réinstallé ; GitHub lent ici).
- Barre de stockage façon SteamOS (FORMULA / Autres / Libre), calculée en fond, cache 120 s.

### API principales
`/api/library`, `/api/rescan` (POST), `/api/launch`, `/api/events` (SSE manette), `/api/settings`, `/api/emulators`,
`/api/sync`, `/api/games`, `/api/games/preview`, `/api/games/remove`, `/api/quit`, routes de profils.

---

## 8. Émulateurs et configurations

### Versions installées

| Console | Émulateur | Windows (`emulators\…`) | Deck |
|---|---|---|---|
| PS2 | PCSX2 | 2.8.2 | flatpak `net.pcsx2.PCSX2` 2.8.2 |
| PS2 (jeux cassés) | PCSX2 debug | 1.7.3780 (`pcsx2-debug`, Qt AVX2) | AppImage `~/Emulation/pcsx2-debug/pcsx2-debug.AppImage` |
| PSP | PPSSPP | 1.20.4 | `org.ppsspp.PPSSPP` 1.20.4 |
| PS Vita | Vita3K | build continu (2026-11-06) | AppImage extraite `~/Emulation/psvita/Vita3K-AppDir` |
| PS3 | RPCS3 | 0.0.43-20415 (se met à jour seul) | `net.rpcs3.RPCS3` 0.0.43-20376 |
| PS4 | shadPS4 | 0.20.0 | `~/Emulation/ps4` (Shadps4-sdl.AppImage 0.20.0 + QtLauncher, `user/` portable) |
| NES | Nestopia | 2.0.0 | `ca._0ldsk00l.Nestopia` 1.53.2 |
| N64 | RMG | 0.9.0 | `com.github.Rosalie241.RMG` 0.9.0 (x11 seulement) |
| GBA | mGBA | 0.10.5 | `io.mgba.mGBA` 0.10.5 |
| DS | melonDS | 1.1 | `net.kuribo64.melonDS` 1.1 |
| GC / Wii | Dolphin | 2609a | `org.DolphinEmu.dolphin-emu` 2609a |
| Xbox | xemu | 0.8.139 | `app.xemu.xemu` 0.8.136 |
| Xbox 360 | Xenia Canary | commit 48b318a | AppImage officielle `~/Emulation/x360/xenia_canary.AppImage` (expérimentale, Vulkan) |
| (fenêtre) | Chromium | — | `org.chromium.Chromium` 156 |

### Règles communes
- **Chaque émulateur fraîchement installé avait des touches vides ou réglées sur le clavier** (Nestopia, RMG, mGBA,
  RPCS3) : toujours écrire les correspondances explicitement.
- RMG et Nestopia réécrivent leur config en quittant : ne les modifier que fermés (sauvegarde `.bak`).
- **Deck, X11 par processus, jamais globalement** (sinon fenêtre Wayland native → Steam applique la config manette
  « Bureau », bug SSX 3 du 28/10) : `QT_QPA_PLATFORM=xcb` pour PCSX2, RPCS3, mGBA, melonDS, Dolphin ;
  `SDL_VIDEO_DRIVER=x11` pour PPSSPP, shadPS4, Nestopia ; `SDL_VIDEODRIVER=x11` pour xemu (SDL2) et Xenia
  (+ `GDK_BACKEND=x11`). `flatpak override --user --socket=x11` pour PCSX2, RPCS3, xemu.
- `SDL_JOYSTICK_HIDAPI=0` pour Nestopia, mGBA, melonDS, xemu, Xenia : ils voient alors la manette virtuelle Steam
  (port 0) et pas la manette physique via HIDAPI (autre ordre de boutons, contourne Steam Input).
- Overrides flatpak : `--filesystem` sur `~/Emulation` et `~/kDrive/Saves/Profils` (et anciens `Saves/<console>`).
- **Caches shaders (Deck, Linux 0.7.017-0.7.018)** : Steam fait pointer `MESA_SHADER_CACHE_DIR` vers
  `~/.local/share/Steam/steamapps/shadercache/<appid>`, en lecture seule dans les flatpaks à accès home en lecture
  seule (PCSX2, RMG, Nestopia, RPCS3) → tous les shaders recompilés à chaque lancement. Chaque `flatpak run` reçoit
  désormais `--env=MESA_SHADER_CACHE_DIR=~/.var/app/<app>/cache` (`flatpak_shader_cache()`), sauf s'il est déjà fourni.
- **Langue** : français partout où une clé existe. PPSSPP `[SystemParam] GameLanguage=2` + UI fr_FR ; RPCS3 System
  Language French ; shadPS4 `consoleLanguage = 2` ; melonDS firmware Language=2 ; Dolphin GC français ; Vita3K
  `sys-lang 2`. PCSX2 n'a pas de clé : la langue PS2 vit dans la NVM du BIOS (à régler une fois via PCSX2 « Démarrer
  le BIOS » > Configuration système). Xenia : pas de clé trouvée.

### PCSX2 (PS2)
- `[Pad1]` liaisons `SDL-0/…` (A = Croix…), menu pause = Back+Start. BIOS `SCPH-70004_BIOS_V12_PAL_200.BIN`
  (PAL v2.0) parmi 39 BIOS dans `bios/ps2`. Windows : `portable.ini` + `inis\PCSX2.ini`.
- Sauvegardes : `PCSX2.ini [Folders] MemoryCards / Savestates` → profil.
- Testé en jeu (SSX 3). PCSX2 réécrit les deux cartes mémoire au démarrage.
- **PCSX2 debug** : certains jeux ne marchent plus avec les PCSX2 récents (Splashdown : la course ne démarre pas, pas
  d'eau ; OK en 1.7.3780 Software). Liste par numéro de série dans `debug-games.json` :
  `"SLUS-12345": {"title": "…", "renderer": "software"}` (software par défaut, auto, vulkan, opengl, dx11, dx12).
  Actuellement Splashdown SLES-50486 (Europe v2.00) et SLUS-20223 (USA v2.01). À chaque lancement FORMULA réécrit ses
  réglages (même BIOS, manette avec noms 1.7 A/B/X/Y, plein écran, renderer). Cartes à part
  `Saves/Profils/<profil>/PS2/memcards-debug` et `sstates-debug` pour qu'une vieille version n'écrive jamais dans les
  cartes du PCSX2 principal. Deck : `XDG_CONFIG_HOME=~/Emulation/pcsx2-debug/config`. Pas d'entrée séparée dans
  la liste des émulateurs.

### PPSSPP (PSP)
Valeurs par défaut correctes + L/R ajoutés (`10-192`, `10-193`) dans `controls.ini`. Vulkan, 2×. Sauvegardes :
liens (Deck) / jonctions (PC, `memstick\PSP`) `PSP/SAVEDATA` et `PSP/PPSSPP_STATE`.

### Vita3K (PS Vita)
- Mode portable (dossier `portable` à côté de l'exe / de l'AppImage), console en français, Discord et recherche de
  mises à jour coupés, `DISABLE_AUTO_UPDATES=1`. Version repérée par sa date de publication.
- Firmware officiel `PSVUPDAT.PUP` + `PSP2UPDAT.PUP` (gratuits chez Sony) dans `bios/psvita` : `vita_prepare()` l'installe
  sans fenêtre (`Vita3K --firmware`) avant le premier jeu (fait sur PC le 07/11).
- Formats : `.vpk`, dossier décompressé, ou `.pkg` + licence posée à côté sous le même nom (`Jeu.rif` ou
  `Jeu.work.bin`) ou déjà dans `ux0/license/<TID>/<CONTENT_ID>.rif`. Installation `Vita3K --pkg X --zrif <clé>`
  (zRIF = zlib wbits 10 + base64 ; Vita3K affiche « Invalid zRIF key » mais installe si la licence est dans ux0/license).
  **La licence doit avoir exactement le même Content ID que le paquet**, sinon l'installation ne fait rien.
  Mise à jour : `Jeu (Update v1.04).pkg` à côté, installée une fois (marqueur `ux0/app/<TID>/.formula-updates`).
- Vita3K installe au premier lancement puis lance directement.
- Sauvegardes : lien `savedata` → profil (`…/PSVita`).
- **Deck** : l'AppImage range ses shaders dans `share/Vita3K/shaders-builtin` mais Vita3K les cherche dans `bin/` →
  shader vide → segfault RADV (`libvulkan_radeon`) dès la première image. `vita_appdir_runner()` extrait l'AppImage dans
  `~/Emulation/psvita/Vita3K-AppDir` (marqueur `.formula-source` = taille:date, réextraite si l'AppImage change),
  crée le lien `bin/shaders-builtin`, lance `AppRun` avec `APPDIR` + `APPIMAGE`. Config Deck : `memory-mapping:
  disabled`, `validation-layer: false`. Des rafales de « Unhandled SIGSEGV at rip » dans le journal sont normales.
- Tactile Deck : écran = tactile avant, clic gauche = avant, clic droit = arrière, R4 = T bascule. Touches identité SDL.

### RPCS3 (PS3)
- **Windows** : RPCS3 0.0.43+ lit ses réglages dans `emulators\rpcs3\config\` (`config.yml`,
  `input_configs\global\Default.yml`). Manette XInput : `Device: "XInput Pad #1"` (numérotation à partir de #1,
  **guillemets obligatoires** : `#` sans guillemets = commentaire YAML).
- **Deck** : `~/.var/app/net.rpcs3.RPCS3/config/rpcs3/input_configs`, handler SDL. RPCS3 (SDL3) tourne hors Steam Input
  et voit les manettes **physiques** (« Steam Deck Controller 1 »), jamais « Steam Virtual Gamepad ».
  `rpcs3_set_pad()` réécrit le Device du joueur 1 à chaque lancement PS3 (manette externe si présente, noms appris dans
  RPCS3.log « Found game pad » ; Xbox Series BT supposée « Xbox Series X Controller », non vérifiée) et migre les noms
  de boutons A/B/X/Y vers South/East/West/North (sinon seul le D-pad marchait). Sauvegarde
  `~/Emulation/_backups/rpcs3-input-avant-20261111`.
- Firmware 4.93 installé sur PC et Deck (`rpcs3 --headless --installfw bios/ps3/PS3UPDAT.PUP` ; sans `--headless` il
  attend une boîte de dialogue). `config/rpcs3/games` (Deck) est un lien vers `~/Emulation/roms/ps3`.
- **Jeux PSN** : dossier par jeu dans `roms/ps3` avec le ou les `.pkg` (jeu, clé de déblocage) + licences `.rap`.
  `ps3_prepare` installe le firmware s'il manque, les paquets (`--headless --installpkg`), copie les `.rap` dans
  `dev_hdd0/home/00000001/exdata`, puis lance `dev_hdd0/game/<ID>/USRDIR/EBOOT.BIN`.
- **Jeux disque** : dossier `PS3_GAME` + `PS3_DISC.SFB` (déchiffré, voir §15). Mises à jour : `.pkg` posé dans le dossier
  du jeu (`Jeu (USA) (Update v1.01).pkg`), installé une fois (`ps3_disc_updates()`, marqueur
  `rpcs3_root/.formula-pkgs`), marqué fait **seulement si** `dev_hdd0/game/<ID>/PARAM.SFO` a changé (RPCS3 refuse les
  mises à jour hors chaîne).
- Sauvegardes : lien/jonction `dev_hdd0/home/00000001/savedata` → profil. Fenêtre de bienvenue désactivée.
- RPCS3 0.0.43 plantait (0xC0000409) en ouvrant l'ISO Killzone Trilogy → extraire les jeux en dossier.
- Si l'utilisateur a la GUI RPCS3 ouverte, le journal est verrouillé (pas de vérification par log possible).

### shadPS4 (PS4)
Manette SDL3 par défaut, `consoleLanguage = 2`. Sauvegardes : lien/jonction `user/savedata`. Jeux = dossiers
CUSAxxxxx déchiffrés ; l'installation de `.pkg` passe par le QtLauncher (interface graphique). Indépendant du shadPS4
du pack Bloodborne. Aucun jeu PS4 actuellement.

### Nestopia (NES)
- Deck (1.53.2) : `input.conf [nespad1j]`, format `jPbN` (bouton), `jPhN` (chapeau 0..3 = haut, bas, gauche, droite),
  `jPaN` (axe×2 + positif) : b=j0b0, a=j0b1, select=j0b6, start=j0b7, turbo sur X et Y. Il était livré sans aucune
  touche (Start mort). Sauvegardes : liens `data/nestopia/{save,state}`.
- **Windows (2.0.0) : manette et sauvegardes par profil pas encore faites** (emplacement des sauvegardes inconnu,
  jamais lancé sur PC).

### RMG (N64)
Section `[Rosalie's Mupen GUI - Input Plugin Profile 0]` de `mupen64plus.cfg`, `DeviceType=2` (Automatic), valeurs en
chaînes `<Touche>_InputType/_Data/_ExtraData` (listes séparées par `;` ; type 0 = bouton SDL3, 1 = axe ; ExtraData 1 =
positif) : A = Sud, B = Ouest, Start, Z = LT, L = LB, R = RT, C = stick droit, analogique = stick gauche, D-pad.
Livré sans profil (manette morte). Sauvegardes : lien `data/RMG/Save` (Deck), `SaveSRAMPath` / `SaveStatePath` (PC).

### mGBA (GBA)
`[gba.input.SDLB]` + `[gba.input-profile.Steam Deck Controller]` (SDL nomme ainsi la manette virtuelle) :
keyA=1 keyB=0 keyL=4 keyR=5 keySelect=6 keyStart=7 (livré à -1). Sauvegardes `config.ini [ports.qt] savegamePath /
savestatePath` (+ `portable.ini` sur PC). Testé en jeu (Sonic Pinball Party).

### melonDS (DS)
`[Instance0.Joystick]` A=1 B=0 X=3 Y=2 L=4 R=5 Select=6 Start=7, chapeau 257/258/260/264. Sauvegardes
`SaveFilePath` / `SavestatePath` **sous `[Instance0]`** (à la racine du toml elles sont ignorées : le premier essai
sauvait à côté de la ROM, corrigé le 29/10).

### Dolphin (GameCube / Wii)
Deck : Device `SDL/0/Steam Virtual Gamepad` ; Windows : `XInput/0/Gamepad` (`portable.txt`). Wiimote + Nunchuk,
pointeur IR sur le stick droit, Arrêt = Back&Start, `Dolphin.ini` plein écran. Sauvegardes : liens/jonctions `GC` et
`Wii` (`User\GC`, `User\Wii`). **Non testé en jeu** (aucun jeu GC/Wii).

### xemu (Xbox)
- Jeux XISO `.iso` (conversion possible avec extract-xiso) dans `roms/xbox`.
- BIOS à extraire de sa propre console, dans `bios/xbox` : boot ROM MCPX `mcpx_1.0.bin` + BIOS `Complex_4627.bin` (ou
  autre `.bin`). **Absents pour l'instant.**
- Disque dur virtuel vierge (projet xemu-hdd-image, sans contenu Microsoft) + EEPROM dans les sauvegardes du profil
  (`…/Xbox/xbox_hdd.qcow2`) : les sauvegardes Xbox sont **dans ce disque**. Téléchargé au premier jeu Xbox d'un nouveau
  profil. kDrive peut créer un doublon en conflit : n'en garder qu'un.
- PC : `xemu.toml` à côté de l'exe (mode portable), pas de recherche de mises à jour. Deck :
  `~/.var/app/app.xemu.xemu/data/xemu/xemu/xemu.toml`. `auto_bind = true`.
- **Non testé** (ni jeu ni BIOS).

### Xenia Canary (Xbox 360)
- `.iso`, `.zar`, ou dossier contenant `default.xex`, dans `roms/x360`. Aucun fichier système.
- PC : `portable.txt`, jonction `content` → profil (`…/Xbox 360`), Discord désactivé.
- Deck : l'AppImage ne peut pas utiliser `portable.txt` (son dossier est le point de montage) → FORMULA passe
  `--storage_root=~/Emulation/x360` et `--content_root=<profil>/Xbox 360` (remplacé à chaque lancement). Réglages
  `~/Emulation/x360/xenia-canary.config.toml` (Discord coupé). `input_system` par défaut.
- **Non testé en jeu.**

---

## 9. Profils, sauvegardes, kDrive

### Profils (depuis Windows 0.9.000 / Linux 0.7.000, 07/11)
- Écran « Qui joue ? » au démarrage, **4 profils max**. L3 / R3 rouvre « Qui joue ? » depuis la bibliothèque ; menu
  profil dans la barre du haut.
- **Compte parent** : code à 4 chiffres, stocké seulement en empreinte PBKDF2 salée ; 5 erreurs = 30 s de blocage.
  Dès qu'un compte parent existe, ajouter / modifier / supprimer un profil demande un code parent, et le gestionnaire de
  jeux est réservé aux profils parents.
- Le **Deck fait référence** pour les profils (choix de l'utilisateur). « P.A.D » (id `pad`) n'a plus de code parent
  (ancienne empreinte du PC gardée dans `_backups/profils-avant-synchro-20261111`).
- **Liste commune** : `kDrive/Saves/Profils/profiles.json` (nom, couleur, compte parent), synchronisée par kDrive entre
  PC et Deck. Copie locale `profiles-shared.json` (reconstruit le fichier commun s'il manque, fusion par nom) ; les
  `profiles_conflict_*.json` créés par kDrive sont fusionnés puis rangés dans `Profils/_conflits`.
- **Avatar** : choisi dans l'explorateur de fichiers du système (JPEG, PNG, WebP…), converti en JPEG carré 1000×1000,
  enregistré `kDrive/Saves/Profils/<profil>/_avatar.jpeg` (synchronisé par kDrive). Ancien emplacement
  `Profils/_avatars/<nom>` (0.7.012) repris. Sans image : avatar simple par défaut.
- Favoris, nombre de parties, dernière partie : **par profil et par appareil** (`<données>/profiles/<id>.json`,
  superposés à `/api/library`).
- Profil supprimé : déplacé dans `Profils/_supprimes`, jamais effacé.

### Sauvegardes
- Toutes dans `kDrive/Saves/Profils/<profil>/<console>` (Deck `/home/deck/kDrive/Saves`, PC
  `C:\Users\iridi\kDrive\Saves`), donc communes PC et Deck. Dossier `kDrive/Saves/Bloodborne` existant : ne pas toucher.
- Avant chaque lancement `Profiles.apply()` refait pointer liens (Deck), jonctions (Windows) ou chemins d'ini vers le
  profil actif (`save_targets()`). Un vrai dossier trouvé à la place d'un lien est recopié dans le profil puis renommé
  `<nom>.avant-profils-<date>`. Rien n'est effacé.

| Émulateur | Deck | Windows |
|---|---|---|
| PCSX2 | `PCSX2.ini [Folders] MemoryCards / Savestates` | idem |
| PCSX2 debug | `memcards-debug`, `sstates-debug` | idem |
| PPSSPP | liens `PSP/SAVEDATA`, `PSP/PPSSPP_STATE` | jonctions `memstick\PSP\…` |
| Vita3K | lien `savedata` (PSVita) | idem (jonction) |
| RPCS3 | lien `dev_hdd0/home/00000001/savedata` | jonction |
| shadPS4 | lien `~/Emulation/ps4/user/savedata` | jonction `user\savedata` |
| Nestopia | liens `data/nestopia/{save,state}` | **pas fait** |
| RMG | lien `data/RMG/Save` | `SaveSRAMPath` / `SaveStatePath` |
| mGBA | `savegamePath` / `savestatePath` | idem |
| melonDS | `SaveFilePath` / `SavestatePath` sous `[Instance0]` | idem |
| Dolphin | liens `GC`, `Wii` | jonctions `User\GC`, `User\Wii` |
| xemu | `hdd_path`, `eeprom_path` (Xbox) | idem |
| Xenia | `--content_root` | jonction `content` |

- Deck : chaque flatpak a `flatpak override --user --filesystem=~/kDrive/Saves/Profils`.
- **Migration** (une fois par appareil, compte rendu `profiles-migrated.json`) : anciens `kDrive/Saves/<console>`
  recopiés sans écrasement dans « P.A.D » puis vérifiés par empreinte (PC 33 fichiers, 0 écart). Les anciens dossiers
  restent en place, inutilisés. Sauvegarde complète d'avant migration : `G:\Jeux\FORMULA\_backups\saves-avant-profils-20261107`
  (PC + copie du Deck) et `~/Emulation/_backups/saves-avant-profils-20261107`. Anciens dossiers d'avant kDrive sur le
  Deck : `*.avant-kdrive-20261028`.
- **Plainte « sauvegarde pas à jour »** : chercher des fichiers `*_conflict_*` dans `kDrive/Saves`. Cas Splashdown du
  08/11 : PC et Deck avaient écrit `memcards-debug/Mcd001.ps2` presque en même temps, kDrive avait gardé l'ancienne et
  renommé la plus récente en `Mcd001_conflict_20261107_163225_*.ps2` ; corrigé en recopiant le conflit par-dessus
  (sauvegarde `_backups/splashdown-20261108`). Outil scratchpad `mcd.py` : liste les sauvegardes d'une carte .ps2 et
  leurs dates (heure JST).
- Sauvegardes vérifiées le 28/10 : GBA (Rayman 3, Rayman Advance, Sonic Advance 3, Sonic Pinball Party), N64 (Super
  Mario 64), NES (Zelda), DS (Battles of Prince of Persia), cartes PS2.

---

## 10. Jaquettes

- Cherchées **une fois par jeu** (les manquantes retentées à chaque démarrage du serveur), puis stockées en local.
  L'URL d'image porte la date du fichier pour qu'une jaquette remplacée apparaisse après Actualiser.
- Toutes converties en **WebP par ffmpeg** (jaquettes 480 px de haut, fonds 640 px de large, q82) dans `save_asset` ;
  `optimize_library()` convertit les anciennes PNG/JPG à chaque scan. ~900 Ko → ~55 Ko par jaquette.
- Sources dans l'ordre :
  1. PS2 : `xlenore/ps2-covers` par numéro de série ;
  2. PS3 : `aldostools/Resources` `COV/<TITLEID>.JPG` ;
  3. GC / Wii : `art.gametdb.com/wii/cover/{FR,EN,US,JA}/<ID>.png` ;
  4. PS Vita : `Andiweli/HexFlow-Covers` `Covers/PSVita/<serial>.png` (`cover_by_id`) ;
  5. Xbox 360 : `xboxunity.net` (`CoverInfo.php?titleid=` puis `Cover.php?size=large&cid=`, jaquette complète 900×600
     dont ffmpeg découpe la face avant, 46,9 % à droite) ;
  6. sinon `thumbnails.libretro.com` Named_Boxarts par titre normalisé, puis par nom de fichier nettoyé si le titre
     interne est tronqué (« ACE COMBAT X ») ;
  7. PSP en dernier recours : `dipubadatya/psp-covers-hd` (noms No-Intro, `covers_repo`, index par `api.github.com`
     lu compressé en gzip et mis en cache 14 jours dans `repo_<nom>.json`).
- **Jamais la jaquette d'une autre console** en secours (l'utilisateur a refusé la boîte PS2 pour un jeu PSP).
- `adopt_local_assets` rattache les images déjà présentes (reçues de l'autre appareil par la synchro) avant toute
  recherche Internet.
- Ratio réel des boîtiers par console (`BOX_RATIO` dans app.js, largeur/hauteur) : DVD 0,711 (PS2, Wii, X360),
  GC 0,725, Xbox 0,72, Blu-ray 0,787 (PS3, PS4), PSP 0,578, Vita 0,778, DS 0,912, NES 0,714, N64 1,4 (paysage),
  GBA 0,9. Variable CSS `--ar` ; dans une vue à une seule console `--card-f = min(1.5, ratio/0.714)`.
- Badge de console en bas à droite des jaquettes. Jaquette sélectionnée en haut (`#hero-cover`) à 195 px.
- Logos du rail : SVG officiels Wikimedia (`art/logos-src`), convertis en WebP sans perte de 48 px
  (`web/logos/<id>.webp`), affichés en silhouettes blanches dans une boîte 100×20 « contain », sauf NES et GBA en
  couleur (`COLOR_LOGOS`). Logos PS2/PS3/PSP recadrés sur le lettrage principal.

---

## 11. Interface et manette

### Lecture de la manette
- **Deck** : `PadReader` lit en evdev, côté serveur, les périphériques de type js (manette virtuelle Steam
  « Microsoft X-Box 360 pad N », Deck = event10 ±32767) et envoie les appuis en SSE `/api/events`. L'API Gamepad du
  navigateur (peu fiable dans Chromium flatpak sous gamescope) ne sert que de secours. Axes normalisés par appareil
  avec `EVIOCGABS` (une manette Xbox BT brute va de 0 à 65535, ce qui faisait défiler toute la bibliothèque) ; une
  source par appareil. Gâchettes LT/RT lues aussi.
- **Windows** : XInput par ctypes, uniquement si FORMULA.exe est la fenêtre au premier plan.
- **Priorité** (« la fenêtre affichée garde les commandes ») : un jeu tourne → FORMULA ignore tout ; menu Steam ouvert
  → Steam coupe la manette ; au retour d'un jeu, les boutons encore enfoncés sont ignorés jusqu'au relâchement, puis
  0,8 s de délai. Pendant le splash : entrées ignorées.

### Touches
- A jouer / valider, B retour (un 2e B dans la colonne de gauche présélectionne Quitter), X recherche, Y favori,
  LB / RB console précédente / suivante, Start trier, View / Select Paramètres, LT / RT taille des jaquettes,
  L3 / R3 « Qui joue ? », clavier : G gestionnaire de jeux, `-` / `+` zoom, F11 plein écran (PC).
- Barre du haut accessible à la manette : recherche, tri, journal de la bibliothèque, menu profil.
- **Taille des jaquettes** : curseur −/+ en bas à droite, LT/RT ou `-`/`+`, pas de 10 %, de 50 à 200 %
  (`localStorage formula.zoom`).
- **Clavier à l'écran** (AZERTY/QWERTY, Espace / ⌫ / Tout effacer / OK) : sur le Deck seulement (X ou toucher le champ
  de recherche ; A tape, B efface/ferme, Y espace, X/Start ferme). Sur PC le champ reçoit directement le focus.
- La colonne des consoles défile pour suivre la sélection (`scrollIntoView`).

### Stick droit : saut entre sections (Windows 0.9.019-0.9.020 / Linux 0.7.021-0.7.022)
- 5 sections : **1** Bibliothèque / Récents / Favoris, **2** consoles, **3** Actualiser → Quitter, **4** catalogue,
  **5** barre du haut.
- Déclenché au-delà de 60 % de la course, réarmé sous 35 %. Message serveur `{"b":"rs","v":1,"a":angle}`
  (`PadReader.set_rs` ; XInput rx/ry, evdev ABS_RX/RY ou Z/RZ pour une Xbox BT) ; côté page `stickDir()` +
  `SECTION_JUMPS`.
- Angles par tranches de 30° (0° = droite, sens antihoraire) : 60-120° haut et 240-300° bas (section voisine à
  l'écran) ; 300-30° → catalogue (4) ; depuis 4 : 120-150° → 1, 150-210° → 2, 210-240° → 3 ; depuis 1 : 30-60° → 5 ;
  depuis 5 : 210-240° → 1.
- Testé par appels JS sur un serveur de test et test unitaire de `PadReader`, **pas avec une vraie manette**.

### Paramètres
Langue (anglais par défaut, français ; `/api/settings`, `settings.json`), Affichage (fenêtré / plein écran, PC),
Emulators (§7), barre de stockage. Page en `notranslate`.

---

## 12. Gestionnaire de jeux (Windows 0.9.016-0.9.018 / Linux 0.7.018-0.7.020)

- Entrée « Gestionnaire de jeux » dans la colonne de gauche (touche G). Classe `GameManager`, API `/api/games`,
  `/api/games/preview`, `/api/games/remove`.
- Liste les jeux de cet appareil par taille, barres relatives au **disque entier**, bouton retour en haut.
- Dès qu'un compte parent existe, écran et API réservés aux profils parents (`GameManager.allowed`) ; pas de code à
  la suppression.
- Suppression : confirmation en **maintenant A (ou Entrée, ou le clic) 2 s** (`openConfirm(text, onYes, holdMs)`),
  ligne grisée puis retirée en direct.
- La poubelle **déplace** le jeu dans la corbeille FORMULA (`<base>\_corbeille` / `~/Emulation/_corbeille`), avec la
  copie installée par l'émulateur pour les jeux PS3 PSN (`dev_hdd0/game/<serial>`) et PS Vita (`ux0/app/<serial>`).
  Journal `_corbeille/corbeille.json` (d'où, vers où). FORMULA ne vide **jamais** cette corbeille (c'est l'utilisateur
  qui la vide pour libérer la place). Les sauvegardes ne sont jamais concernées.
- Vaut pour cet appareil seulement : la synchro marque le jeu supprimé et ne le recopie pas ici ; l'autre appareil
  garde le sien. Une option de suppression définitive sur le Deck a été proposée à l'utilisateur, sans réponse.

---

## 13. Synchronisation des jeux (`formula.py --sync`, port 47810)

- `sync.json` dans le dossier de données : `device`, `token` (secret partagé, identique des deux côtés, **ne jamais le
  recopier**), `peers` (liste d'adresses de remplacement) :
  PC `[["192.168.1.89:47810","steamdeck.local:47810"]]` ; Deck `[["192.168.1.97:47810","THEMIS.local:47810","192.168.1.151:47810"]]`.
- Sécurité : n'écoute que si le jeton fait au moins 16 caractères et qu'il y a au moins un appareil ; refuse les
  adresses non privées ; jeton vérifié par `hmac.compare_digest` (vérifié : sans jeton → 403). Sert seulement `roms/`
  (`/manifest`, `/file` avec Range) et les jaquettes (`/covers`, `/cover`). Pare-feu Windows déjà OK pour pythonw.
- Fonctionnement : manifeste de `roms/` (fichiers modifiés depuis moins de 120 s exclus) ; téléchargement vers
  `*.formula-part` avec reprise ; re-téléchargé si absent ici, ou si l'autre copie a une taille différente **et** est
  plus récente ; nouvelle tentative toutes les 5 min ; si l'autre appareil est éteint, jeux « en attente » (pastille,
  `/api/sync`). Caractères interdits sous Windows remplacés (`sync_key`). Jaquettes partagées aussi.
- **Suppressions non propagées** : un jeu supprimé est mémorisé dans `sync_known.json` → `deleted` et n'est plus
  re-téléchargé ; l'autre appareil garde le sien. Penser à supprimer des deux côtés si l'utilisateur veut le retirer
  partout. Pour faire revenir un fichier : arrêter la synchro, retirer son chemin de `known` **et** de `deleted`
  (seulement de `deleted` → re-marqué, car known − actuel = deleted).
- Deck : `formula-sync.service` (systemd user, activé). PC : `G:\Jeux\FORMULA\FORMULA synchro.lnk`, lancé par
  `explorer.exe` ; le démarrage automatique (copie dans `shell:startup`) est laissé à l'utilisateur.
- **Gros transferts PC → Deck** (Wi-Fi ~2-3 Mo/s) : ne pas faire de scp fichier par fichier (milliers de petits
  fichiers PS3). Outil scratchpad `resume_copy.py` : liste les tailles distantes par SSH puis envoie seulement les
  fichiers manquants/différents en un seul flux `tar -cf - -T liste | ssh '… tar -xpf - -C Emulation/roms'`. scp/SFTP
  veut des chemins distants non quotés. Toujours sous inhibiteur de veille, vérifier tailles (et SHA-1 si possible).
- Archives : `tar.exe -xOf` de Windows peut extraire et envoyer directement dans ssh.

---

## 14. Bibliothèque de jeux (12/11/2026)

| Console | PC | Deck | Détail |
|---|---|---|---|
| NES | 275 | 275 | zips No-Intro |
| N64 | 100 | 100 | zips |
| GBA | 157 | 157 | dont Le Seigneur des Anneaux : Le Retour du Roi |
| DS | 6 | 6 | Battles of Prince of Persia, Brain Training, GoldenEye 007, Les Sims 2, Star Wars III, WarioWare Touched! |
| PS2 | 70 | 63 | collection « My Sony PlayStation 2 (USA) Collection » (64 archives) + SSX 3 + Splashdown ; Ratchet = versions de la collection (R&C 1 En/Fr/De/Es/It, Going Commando, Up Your Arsenal En/Fr/Es, Size Matters, Deadlocked). Retirés du Deck seulement à la demande : RE4, Playboy Mansion, Le Monde de Nemo, Harry Potter Azkaban, Metal Slug 4&5 ×2 |
| PSP | 10 | 9 | Ace Combat X, Crisis Core (FR), God of War Chains of Olympus + Ghost of Sparta, Great Battles of Rome (PC seulement), Killzone Liberation, MediEvil Resurrection, Monster Hunter Freedom Unite, Les Sims 2, Warhammer 40,000 Squad Command |
| PS Vita | 2 | 2 | Gravity Rush, Killzone Mercenary (`.pkg` + `.rif`, installés dans Vita3K) |
| PS3 | 12 | 7 | voir §15 |
| Xbox 360 | 4 | 4 | Dante's Inferno, Halo Reach, Halo 4 (disque 1 seulement), Metal Gear Rising |
| PS4, GC, Wii, Xbox | 0 | 0 | |

Supprimés à la demande : Crash of the Titans et MediEvil russes, ancien Deadlocked russe, Jak X PS4, WipEout 2048
(licence EU ≠ jeu USA), anciens Ratchet. La collection PS2 source (108 Go, `G:\Downloads`) était à supprimer par
l'utilisateur (trop grosse pour la corbeille).

---

## 15. PS3 et Vita : chiffrement, clés, état

### Disques PS3
- Les ISO PS3 de la source de l'utilisateur sont des dumps Redump **chiffrés** (EBOOT.BIN sans `SCE\0` ; RPCS3 :
  « Invalid or unsupported file format … Not an ELF »). Il faut la clé du disque (`.dkey`, 32 hex) fournie par
  l'utilisateur.
- Outil : portage C# de ps3dec écrit par Claude, dans le scratchpad (`ps3decnet/Ps3Dec.cs`, compilé avec csc
  Framework64) : `Ps3Dec.exe in.iso out.iso <clé>`. Format correct : secteur 0 = u32 nombre de régions **en clair**,
  u32 inutilisé, puis paires (début, fin incluse) des régions en clair ; tout le reste est chiffré (AES-128-CBC,
  IV = numéro de secteur big-endian ; secteurs entièrement nuls ignorés). ~24 Go en ~60 s. Le dépôt Rust d'origine
  analysait ce secteur autrement. Scripts d'extraction scratchpad `ps3extract*.ps1`, `ps3decrypt_*.ps1`.
- Puis extraction en dossier `roms/ps3/<Jeu (Région)>/` avec `PS3_GAME` + `PS3_DISC.SFB` (créer le dossier cible avant
  `Move-Item`, sinon PS3_GAME est renommé), mise à jour `.pkg` copiée sous `<Nom> (Update vX.YY).pkg`. Vérification :
  EBOOT.BIN commence par `SCE\0`, tailles identiques.
- Ensuite règle utilisateur : remplacer la copie du Deck si elle existe.

| Jeu | Type | PC | Deck |
|---|---|---|---|
| R&C Future : Quest for Booty | PSN | OK | OK |
| Beyond Good & Evil HD | PSN | OK | OK |
| Killzone HD (NPUA80856, tiré de PS3_EXTRA de la Trilogy, licence gratuite) | PSN | OK | OK |
| Heavenly Sword (BCUS98132, maj 1.10) | disque | OK | OK (maj installée) |
| MotorStorm Apocalypse (maj 1.06 refusée : « 01.05 requise », il faut la chaîne de mises à jour) | disque | OK | OK |
| R&C Future : Tools of Destruction (v02.00) | disque | OK | OK |
| R&C Collection | disque | OK | OK |
| R&C Future : A Crack in Time (BCUS98124, maj 1.20) | disque | OK | non (copies Ratchet mises en pause par l'utilisateur) |
| R&C Into the Nexus | disque | OK | non (pause Ratchet) |
| Sly Collection | disque | OK | non (refusé par l'utilisateur) |
| Asura's Wrath | disque | OK | non (refusé, copie chiffrée supprimée) |
| Killzone 2 (USA) | disque | **encore chiffré** : l'utilisateur re-télécharge « Killzone Trilogy (USA) » dans `G:\Downloads` (dkey déjà dans `C:\Users\iridi\Downloads`) | supprimé (chiffré) |
| Killzone 3 (USA, Brazil) | disque | en téléchargement dans `G:\Downloads` (clé reçue, maj v1.14 à copier) | — |

Ne pas toucher aux téléchargements Killzone tant que l'utilisateur n'a pas dit qu'ils sont terminés (un script
d'attente de l'ancien fil devait lancer `ps3decrypt_killzone.ps1` une fois les 7z stables 15 min ; il s'arrête avec
son fil : à relancer si besoin). Dante's Inferno PS3 : 7z corrompu, non ajouté (l'utilisateur a la version 360).
Les dossiers sources PS3 de `G:\Downloads` ont été mis à la corbeille (Windows en a purgé une partie, faute de place).

### PS Vita
- La couche externe d'un PKG Vita se lit avec des clés publiques (outil scratchpad `pkgtool.py`, AES-128 CTR, type de
  clé `header[0xE7] & 7`). Le `sce_sys/package/temp.bin` de 512 octets nuls n'est **pas** une licence.
- Gravity Rush (PCSF00024) et Killzone Mercenary (PCSF00243, licence KZV0000000000000) : installés dans Vita3K sur PC ;
  sur le Deck `.pkg` + `.rif` dans `roms/psvita`, Killzone installé (3,4 Go) et lancé avec succès ; Gravity Rush
  s'installe au premier lancement. Licences inutilisées (`work*.bin` dans `C:\Users\iridi\Downloads` : autres Killzone
  Mercenary, WipEout EU) supprimables.

---

## 16. Leçons et pièges

- Toujours écrire les touches de manette d'un nouvel émulateur ; ne pas croire les valeurs par défaut.
- Forcer X11 par processus sur le Deck, jamais globalement.
- Déployer tout l'arbre linux, vérifier md5 et bit exécutable de formula.sh.
- `git fetch --tags` avant de numéroter : plusieurs fils travaillent dans le même `G:\FORMULA`.
- Ne pas recopier `web/` en bloc d'une branche à l'autre.
- Fichier supprimé une fois (copie partielle) = tombstone permanent dans la synchro (voir §13).
- Conflits kDrive : fichiers `*_conflict_*` ; kdrive.service du Deck à vérifier en premier.
- La corbeille de G: (~97 Go) purge définitivement au-delà : prévenir l'utilisateur avant de gros envois à la corbeille.
- Archives : `.zip` qui est en fait un 7z, rar dans rar, préfixes « 1055 - » de scène dans les noms : vérifier.
- Vita : la licence doit avoir le même Content ID ; PS3 : clé par disque, mises à jour en chaîne.
- Edge/Chromium headless `--screenshot` bloqué par le SSE : utiliser un tunnel + navigateur intégré.
- Cover fetch lent après démarrage : interroger l'API.
- Ne pas lancer soi-même d'émulateur en GUI si l'utilisateur joue ; le journal RPCS3 est verrouillé quand la GUI est ouverte.

---

## 17. Pistes ouvertes

1. Killzone 2 et Killzone 3 : déchiffrer quand l'utilisateur dit que les téléchargements sont finis, puis Deck selon la règle.
2. Copie vers le Deck de A Crack in Time et Into the Nexus : en pause, attendre l'utilisateur.
3. MotorStorm Apocalypse : mise à jour 1.05 manquante pour appliquer la 1.06.
4. Nestopia 2.0 sous Windows : manette et sauvegardes par profil.
5. Tests en jeu : Dolphin (aucun jeu GC/Wii), xemu (BIOS Xbox à fournir par l'utilisateur), Xenia (PC et Deck),
   manette Xbox Series BT sur RPCS3 Deck (nom supposé), stick droit avec une vraie manette.
6. Option de suppression définitive dans le gestionnaire de jeux (Deck) : proposée, sans réponse.
7. Démarrage automatique de la synchro PC : à l'initiative de l'utilisateur (`shell:startup`).
8. Xbox One : rien tant qu'aucun émulateur public n'existe.

---

## 18. Historique des versions (Windows / Linux)

- **28/10** : PSP/PS2 sur le Deck (flatpaks user), PS4 (shadPS4), PS3 (RPCS3) ; création de FORMULA (Deck) :
  galerie, jaquettes, manette evdev, X11 forcé, L4 = Windows ; DS, GBA, Wii/GC, NES, N64 ; sauvegardes vers kDrive ;
  WebP, logos de consoles, clavier à l'écran.
- **29/10** : collection PS2 ; FORMULA Windows (émulateurs portables, XInput) ; synchro ; dépôt git par plateforme.
  0.2.000 i18n en/fr ; 0.3.000 Paramètres > Emulators + stockage ; 0.3.002 synchro taille+date ; 0.3.003 pas de clavier
  à l'écran sur PC ; 0.3.004 `CREATE_NO_WINDOW` ; 0.3.005 / L0.3.003 passe sécurité (synchro LAN + jeton, polices
  locales, CSP) ; 0.3.006 / L0.3.004 jaquettes par la synchro ; **0.4.000** FORMULA.exe WebView2 ; 0.5.000 fenêtré /
  plein écran + zoom des jaquettes ; 0.5.003-0.5.006 / L0.3.005-0.3.008 badges et logos du rail ;
  **0.6.000 / L0.4.000** Xbox (xemu) et Xbox 360 (Xenia).
- **31/10** : 0.6.001 / L0.4.001 jaquettes Xbox 360 XboxUnity.
- **01/11** : **0.7.000 / L0.5.000** PCSX2 debug (Splashdown).
- **06-07/11** : **0.8.000 / L0.6.000** PS Vita ; 0.8.001 titres sans ™ ; 0.8.003 jaquettes PSP HD ; 0.8.004 axes
  normalisés ; 0.8.005-0.8.007 Vita .pkg + jaquettes HexFlow ; 0.8.008 rail qui défile ; 0.8.009 ratio des boîtiers ;
  0.8.010 auto-update Vita3K coupé ; 0.8.011 / L0.6.012 Vita3K AppDir (shaders) ; L0.6.003 formula.sh exécutable.
  **0.9.000 / L0.7.000** profils façon Netflix ; 0.9.001 / L0.7.001 PS3 PSN (.pkg + .rap) et mises à jour Vita.
- **08/11** : 0.9.002-0.9.003 mises à jour des disques PS3 ; 0.9.004 puis 0.9.005 (annulation) des mises à jour auto
  des émulateurs.
- **09-11/11** : L3/R3 « Qui joue ? », 2e B → Quitter, barre du haut à la manette ; 0.9.009 / L0.7.009 copie locale et
  fusion des profils ; LT/RT sous Linux ; date dans l'URL des jaquettes ; 0.9.013 / L0.7.014 manettes RPCS3 ;
  avatars (0.9.014-0.9.015) ; L0.7.016-0.7.017 caches shaders Mesa ; RPCS3 Linux noms SDL3.
- **11-12/11** : 0.9.016-0.9.018 / L0.7.018-0.7.020 gestionnaire de jeux ; 0.9.019-0.9.020 / L0.7.021-0.7.022 stick
  droit ; **0.9.021 / L0.7.023** écran de démarrage OnTrack Software ; 0.9.022 / L0.7.024 splash maintenu jusqu'à
  ce que « Qui joue ? » soit prêt ; **0.9.023 / L0.7.025** transition animée profil → bibliothèque.

Les numéros intermédiaires exacts sont dans `git log` / `git tag`.
