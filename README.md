# FORMULA

Lanceur d'émulateurs façon bibliothèque Steam, pour Steam Deck et PC Windows.

- Galerie des jeux avec jaquettes officielles (GameTDB, libretro, xlenore, aldostools), compressées en WebP.
- Tri par console (logos officiels), recherche avec clavier à l'écran, favoris, récents.
- Navigation à la manette (la fenêtre au premier plan garde les commandes), souris et tactile.
- Lance le bon émulateur en plein écran, langue française par défaut quand elle existe.
- Synchronisation des jeux entre appareils (service de fond, reprise automatique, file d'attente si l'autre appareil est éteint).
- Sauvegardes de tous les émulateurs dans `kDrive/Saves/<console>`.

Consoles : PS2 (PCSX2), PSP (PPSSPP), PS3 (RPCS3), PS4 (shadPS4), NES (Nestopia), N64 (RMG),
GBA (mGBA), DS (melonDS), GameCube et Wii (Dolphin).

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
