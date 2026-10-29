# FORMULA

Lanceur d'émulateurs façon bibliothèque Steam, pour Steam Deck et PC Windows.

- Galerie des jeux avec jaquettes officielles (GameTDB, libretro, xlenore, aldostools), compressées en WebP.
- Tri par console (logos officiels), recherche avec clavier à l'écran, favoris, récents.
- Navigation à la manette (la fenêtre au premier plan garde les commandes), souris et tactile.
- Lance le bon émulateur en plein écran, langue française par défaut quand elle existe.
- Synchronisation des jeux entre appareils (service de fond, reprise automatique, file d'attente si l'autre appareil est éteint).
- Sauvegardes de tous les émulateurs dans `kDrive/Saves/<console>`.
- Interface en anglais par défaut, français disponible dans les Paramètres.

## Versions

Une version par plateforme, chacune sur sa branche : `master` = Windows, `linux` = Steam Deck.
Numérotation `MAJEUR.MINEUR.CORRECTIF`, correctif sur 3 chiffres (ex. `0.2.000`) :
- MAJEUR : changement profond (format des données, refonte) ;
- MINEUR : nouvelle fonctionnalité ;
- CORRECTIF : correction ou petit ajustement, sans nouvelle fonctionnalité.

La version est dans le fichier `VERSION`, affichée en bas à gauche de l'application,
et chaque publication reçoit une étiquette `windows-vX.Y.ZZZ` ou `linux-vX.Y.ZZZ`.

Consoles : PS2 (PCSX2), PSP (PPSSPP), PS3 (RPCS3), PS4 (shadPS4), NES (Nestopia), N64 (RMG),
GBA (mGBA), DS (melonDS), GameCube et Wii (Dolphin).

## Sécurité et transparence

FORMULA ne fait rien en douce. Liste exhaustive de ce qu'il fait :

**Ce qui écoute sur le réseau**
- L'interface : `127.0.0.1:47800`, accessible uniquement depuis l'appareil lui-même.
- La synchro (`formula.py --sync`) : port `47810`. Elle n'écoute que si `sync.json` contient un jeton
  d'au moins 16 caractères et au moins un appareil. Elle refuse toute demande qui ne vient pas
  du réseau local (adresses privées) ou qui n'a pas le jeton. Elle ne sert que les fichiers du dossier `roms` et les jaquettes déjà téléchargées.

**Ce qui sort sur Internet** (rien d'autre, aucune télémétrie, aucune statistique)
- Jaquettes : `art.gametdb.com`, `thumbnails.libretro.com`, `raw.githubusercontent.com` (dépôts xlenore/ps2-covers et
  aldostools/Resources), une seule fois par jeu, stockées ensuite en local.
- Installation d'un émulateur depuis Paramètres, uniquement quand tu coches la case : `api.github.com` et
  `github.com` (version officielle de l'émulateur), `dl.dolphin-emu.org`, ou Flathub sur le Deck.
- La page elle-même est verrouillée par une politique de sécurité (CSP) : elle ne peut charger ou contacter
  que FORMULA. Les polices sont fournies avec l'application.
- Sur PC, la fenêtre est `FORMULA.exe` (WebView2, le moteur web fourni avec Windows), pas un navigateur.
  Elle n'affiche que `http://127.0.0.1:47800/` : toute autre adresse, nouvelle fenêtre, téléchargement ou
  permission (caméra, micro, notifications…) est refusée, et les outils de développement, menus, zoom,
  remplissage automatique et SmartScreen sont désactivés. Lancée sans synchro de compte, sans tâches de fond
  réseau et sans mises à jour de composants. Si WebView2 ne démarre pas, FORMULA demande (Oui/Non) avant
  d'ouvrir Edge en mode application et navigation privée à la place.
- Sur le Deck, la fenêtre est Chromium en mode application, avec les mêmes restrictions de lancement.

**Ce qui est lancé** (toujours sans fenêtre de console)
- L'émulateur du jeu choisi ; `ffmpeg` pour compresser les jaquettes ; `tar` (Windows) ou `flatpak` (Deck)
  quand tu installes ou désinstalles un émulateur ; la fenêtre de l'interface (sur PC, `FORMULA.exe` lance le
  serveur `pythonw formula.py --host` et l'arrête en se fermant) ; le service de synchro.

**Ce qui est écrit sur le disque**
- Le dossier de données (`<base>` sous Windows, `~/Emulation` et `~/.local/share/formula` sur le Deck),
  les réglages des émulateurs, et les sauvegardes dans `kDrive/Saves/<console>`. Rien d'autre :
  pas de registre, pas de démarrage automatique ajouté à ton insu.

## Organisation

Le dépôt ne contient que le code. Les données lourdes vivent ailleurs :

| | Steam Deck | Windows |
|---|---|---|
| Code | `~/Applications/Formula` | ce dépôt (`G:\FORMULA`) |
| Jeux | `~/Emulation/roms/<console>` | `<base>\roms\<console>` |
| Émulateurs | flatpaks utilisateur + `~/Emulation/ps4` | `<base>\emulators` (versions portables) |
| Données FORMULA | `~/.local/share/formula` | `<base>\formula-data` |
| Python | système | `<base>\python` (embarqué) |

`<base>` est lu dans `formula-base.txt` (non suivi par git), par exemple `G:\Jeux\FORMULA`.

## Lancer

- Deck : `formula.sh` (raccourci Steam « FORMULA », qui donne la manette Steam Input aux émulateurs).
- Windows : `<base>\FORMULA.exe` (raccourci du bureau et raccourci Steam « FORMULA »). F11 bascule entre
  plein écran et fenêtre. `formula.py --window` reste accepté et ouvre `FORMULA.exe`.
- Synchro : `formula.py --sync` (service systemd `formula-sync` sur le Deck, raccourci « FORMULA synchro » sous Windows).
  Réglages dans `sync.json` du dossier de données : nom de l'appareil, jeton partagé, adresses des autres appareils.

## Installer sous Windows

```
python tools\install_windows.py G:\Jeux\FORMULA
```

Télécharge Python (embarqué) et les émulateurs depuis leurs sites officiels (versions fixées dans le script),
crée l'arborescence, configure les émulateurs, compile `FORMULA.exe` et crée le raccourci du bureau.
Relançable ; `--update` réinstalle les émulateurs ; `--host-only` recompile seulement `FORMULA.exe`.

`FORMULA.exe` est compilé sur place à partir de `tools/winhost/FormulaHost.cs` avec le compilateur C# fourni avec
Windows (`csc.exe`, .NET Framework 4) et les bibliothèques WebView2 officielles de Microsoft (paquet NuGet
`Microsoft.Web.WebView2`, version fixée dans le script). Ses DLL sont dans `<base>\host`, son profil web dans
`<base>\formula-data\webview2`, et il lit le dossier du code dans `<base>\formula-data\code-dir.txt`. Le BIOS PS2 (`bios\ps2`) et le firmware PS3 (`bios\ps3`) ne sont pas fournis :
ce sont des fichiers Sony à extraire de sa propre console. Ils ne doivent pas être ajoutés au dépôt, pas plus que les jeux.

## Outils

- `tools/install_windows.py` : installation complète (voir ci-dessus).
- `tools/setup_windows.py` : configure les émulateurs Windows (mode portable, manettes, français, sauvegardes kDrive),
  à partir des modèles de `tools/templates`.
- `tools/steam_shortcut.py` : ajoute FORMULA (`FORMULA.exe`) aux jeux non-Steam avec ses visuels.
- `tools/winhost/` : source de la fenêtre Windows `FORMULA.exe`.

## Ajouter une console

Ajouter une entrée dans `SYSTEMS` (et `WIN_CMDS` pour Windows) dans `formula.py`, ou dans `systems.json`
du dossier de données. Penser à rediriger ses sauvegardes vers `kDrive/Saves/<console>`
et à écrire explicitement ses touches de manette.
