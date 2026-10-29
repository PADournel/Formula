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
- Le navigateur (Edge sur PC, Chromium sur le Deck) est lancé sans synchro de compte, sans tâches de fond
  réseau et sans mises à jour de composants (navigation privée sur PC).

**Ce qui est lancé** (toujours sans fenêtre de console)
- L'émulateur du jeu choisi ; `ffmpeg` pour compresser les jaquettes ; `tar` (Windows) ou `flatpak` (Deck)
  quand tu installes ou désinstalles un émulateur ; le navigateur de l'interface ; le service de synchro.

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
- Windows : `<base>\python\pythonw.exe formula.py --window`.
- Synchro : `formula.py --sync` (service systemd `formula-sync` sur le Deck, raccourci « FORMULA synchro » sous Windows).
  Réglages dans `sync.json` du dossier de données : nom de l'appareil, jeton partagé, adresses des autres appareils.

## Installer sous Windows

```
python tools\install_windows.py G:\Jeux\FORMULA
```

Télécharge Python (embarqué) et les émulateurs depuis leurs sites officiels (versions fixées dans le script),
crée l'arborescence, configure les émulateurs et crée le raccourci du bureau. Relançable ; `--update`
réinstalle les émulateurs. Le BIOS PS2 (`bios\ps2`) et le firmware PS3 (`bios\ps3`) ne sont pas fournis :
ce sont des fichiers Sony à extraire de sa propre console. Ils ne doivent pas être ajoutés au dépôt, pas plus que les jeux.

## Outils

- `tools/install_windows.py` : installation complète (voir ci-dessus).
- `tools/setup_windows.py` : configure les émulateurs Windows (mode portable, manettes, français, sauvegardes kDrive),
  à partir des modèles de `tools/templates`.
- `tools/steam_shortcut.py` : ajoute FORMULA aux jeux non-Steam avec ses visuels.

## Ajouter une console

Ajouter une entrée dans `SYSTEMS` (et `WIN_CMDS` pour Windows) dans `formula.py`, ou dans `systems.json`
du dossier de données. Penser à rediriger ses sauvegardes vers `kDrive/Saves/<console>`
et à écrire explicitement ses touches de manette.
