# FORMULA : référence (état au 12/11/2026, Windows 0.9.021 / Linux 0.7.023)

À lire en premier par tout nouveau fil. Dense exprès : il remplace la passation. Vérifier `git log` et les étiquettes
avant de se fier aux numéros (d'autres fils publient en parallèle dans le même dépôt). Détail fonctionnel complet,
liste réseau et disque : `README.md`.

## 1. Règles de l'utilisateur (P.A.D, GitHub `PADournel`)

- Français, ton factuel et neutre : pas d'injonctions ni de leçons ; proposer plutôt qu'ordonner.
- Sécurité et transparence : rien de visible en douce (pas de console qui clignote : `CREATE_NO_WINDOW` partout sous
  Windows), pas de navigateur ouvert tout seul (sinon Oui/Non expliqué d'abord), pas de télémétrie, aucun appel réseau
  inutile, pas de démarrage automatique ajouté. Tout appel réseau, processus ou dossier écrit est listé dans le README.
- Jeux : ne copier sur le Deck **que** les jeux nommés ; si ambigu, demander. Ne jamais piocher dans Téléchargements.
- PS3 : tout jeu disque déchiffré sur PC remplace aussi sa copie sur le Deck si elle y est. Pas de recherche de clés
  (.dkey, zRIF) ni de torrents : les clés viennent de l'utilisateur.
- Les émulateurs peuvent se mettre à jour seuls ; les **jeux** non (FORMULA installe seulement les paquets de mise à
  jour que l'utilisateur dépose). Vita3K : auto-update coupé (`DISABLE_AUTO_UPDATES=1`, il plantait).
- Rien n'est effacé sans accord explicite : corbeille, `gio trash`, dossiers `*.avant-…`, `_backups`.
- `G:\Jeux\Bloodborne` ne fait pas partie de FORMULA : n'y rien lire ni écrire. Travailler dans `G:\FORMULA` (code)
  et `G:\Jeux\FORMULA` (données). Ne pas toucher à Bloodborne ni à kDrive sur le Deck sans demande.
- Git : commits en anglais, auteur `PADournel <paulalexandre.dournel@gmail.com>` + `Co-Authored-By: Claude …`.
  Push autorisé en permanence ; pas de force-push. Jamais d'émulateurs, BIOS, firmwares, jeux ni Python dans git.
- Versionnage (Claude en est responsable) : `MAJEUR.MINEUR.CORRECTIF` (correctif sur 3 chiffres), une version par
  branche, fichier `VERSION`, étiquettes `windows-vX.Y.ZZZ` / `linux-vX.Y.ZZZ`. Changement concluant → commit sur
  chaque branche concernée, version montée, étiquette, push. Toujours `git fetch --tags` avant de choisir un numéro.
- La passation lisible par l'utilisateur : `D:\OneDrive 26-09-26\Desktop\FORMULA - passation.md` (copie de ce
  fichier), à remettre à jour après chaque travail terminé.

## 2. Machines et accès

- **PC THEMIS** (Windows 11) : Ethernet 192.168.1.97, Wi-Fi .151. kDrive `C:\Users\iridi\kDrive`. Pas de Python
  système : `G:\Jeux\FORMULA\python\pythonw.exe` (embarqué 3.15). Outils : `C:\Windows\System32\tar.exe` (zip/7z/rar),
  `C:\Program Files\7-Zip\7z.exe`, ffmpeg, git, gh, `csc.exe` Framework64 (C# 5).
  Lancer un programme détaché : `explorer.exe "…\raccourci.lnk"` (jamais `Start-Process` de Steam).
- **Portable HG_laptop1** : FORMULA dans `C:\Users\iridi\FORMULA`.
- **Steam Deck** : `ssh -i ~/.ssh/bloodborne_deck deck@192.168.1.89` (`steamdeck.local`). **Pas de sudo** (mot de
  passe perdu par l'utilisateur ; polkit refuse en SSH) → flatpaks `--user` (remote flathub `--user`).
  Veille = SSH coupé : tâches longues en `systemd-run --user --unit=X --collect systemd-inhibit --what=sleep:idle …`.
  `pgrep -f`/`pkill -f` attrapent la commande SSH : `pgrep -x` ou motifs ancrés `^…`. Ne jamais définir `DISPLAY`
  globalement (gamescope boucle), ne jamais lancer Steam ou un jeu comme enfant de Claude.
  kDrive Deck : `kdrive.service` (user) avec `Restart=always` ; si profils/sauvegardes divergent, vérifier d'abord
  `systemctl --user status kdrive.service`. Synchro sélective : seuls `Saves` et `Formula` en local
  (liste noire = table `sync_node` de `~/.config/kDrive/.sync_*.db`, à éditer service arrêté).
- Mode auto de Claude bloque : binaires téléchargés exécutés en SSH, démarrage automatique, force-push, `rm -rf` large.

## 3. Architecture

`formula.py` (stdlib seule) = tout le serveur : bibliothèque, jaquettes, lancement, manette, profils, synchro,
gestionnaire d'émulateurs et de jeux. `web/` = interface (index.html, app.js, app.css, logos/, emulogos/, fonts/,
brand/ontrack.webp). CSP : la page ne contacte que FORMULA ; polices locales.

- Modes : sans option = UI sur `127.0.0.1:47800` (`FORMULA_PORT`) ; `--host <pid>` (lancé par FORMULA.exe, meurt avec
  lui) ; `--window` = ouvre FORMULA.exe ; `--sync` = service de synchro port 47810.
- **Windows** : `<base>\FORMULA.exe` (WinForms + WebView2, source `tools/winhost/FormulaHost.cs`, compilé par
  `install_windows.py <base> --host-only` ; DLL dans `<base>\host`, profil `formula-data\webview2`). Il lit le dossier du
  code dans `formula-data\code-dir.txt`, lance `pythonw formula.py --host`, n'affiche que `http://127.0.0.1:47800/`.
  Fenêtré 2/3 centré ; plein écran via Paramètres > Affichage ou F11 (géré dans la page, message `fullscreen:1/0`,
  gardé dans `settings.json`). Edge seulement en secours après Oui/Non.
- **Deck** : `formula.sh` = serveur + `flatpak run --user org.chromium.Chromium --app --kiosk --ozone-platform=x11`.
  formula.sh doit rester 100755 dans git (sinon Steam le ferme aussitôt).
- `<base>` Windows lu dans `formula-base.txt` (non suivi) = `G:\Jeux\FORMULA`.
- Démarrage : splash logo OnTrack Software ~1,4 s sur noir (entrées ignorées), puis « Qui joue ? » en fondu 0,35 s.

## 4. Chemins

| | Windows | Deck |
|---|---|---|
| Code | `G:\FORMULA` (branche **master**, ne pas en changer : raccourcis et synchro tournent depuis là) | `~/Applications/Formula` |
| Données | `G:\Jeux\FORMULA\formula-data` | `~/.local/share/formula` |
| Jeux | `<base>\roms\<id>` | `~/Emulation/roms/<id>` |
| BIOS/firmwares | `<base>\bios\{ps2,ps3,psvita,xbox}` | `~/Emulation/bios/…` |
| Émulateurs | `<base>\emulators\<nom>` portables (`.formula-version`) | flatpaks `--user` + AppImages dans `~/Emulation/{ps4,x360,psvita,pcsx2-debug}` |
| Corbeille FORMULA | `<base>\_corbeille` | `~/Emulation/_corbeille` |
| Sauvegardes | `C:\Users\iridi\kDrive\Saves` | `~/kDrive/Saves` |

Données : `library.json`, `covers/` (WebP), `settings.json`, `sync.json` (jeton : ne jamais le recopier),
`sync_status.json`, `sync_known.json`, `profiles/<id>.json`, `profiles-shared.json`, `last_launch.log`.
Raccourcis : bureau PC `D:\OneDrive 26-09-26\Desktop\FORMULA.lnk` → FORMULA.exe ; Steam PC (userdata 99696636,
compte newgodii) par `tools/steam_shortcut.py` (Steam doit redémarrer) ; Deck Steam appid 2408588416, bureau
`~/Desktop/FORMULA.desktop` → `steam steam://rungameid/10344808476277997568` (pour Steam Input). Steam Input Deck :
`Steam Controller Configs/99696636/config/formula/controller_neptune.vdf` (L4 = touche Windows, R4 = T = tactile Vita).

## 5. Branches et déploiement

- `master` = Windows (a `tools/`, `icon.ico`), `linux` = Deck. `web/` et `formula.py` divergent un peu
  (fonctions propres à chaque plateforme) : reporter commit par commit (`git cherry-pick`), jamais `checkout master -- web`.
- Committer sur `linux` sans quitter master : plomberie (`GIT_INDEX_FILE` temporaire, `read-tree linux`,
  `update-index`, `write-tree`, `commit-tree -p linux`, `update-ref`) ou cherry-pick dans un clone temporaire.
- Déployer sur le Deck **tout l'arbre** linux : `git archive linux | ssh … 'tar -x -C ~/Applications/Formula'`, puis
  `sed -i 's/\r$//'` sur VERSION/README/.sh si besoin, puis comparer les md5 avec la branche. (Déployer un seul fichier
  web a déjà cassé l'UI.) FORMULA en cours d'exécution ne prend le nouveau code qu'au redémarrage.
- Test sans gêner l'utilisateur : serveur de test `FORMULA_PORT=47899` (+ `FORMULA_BASE` vers une base jetable),
  `POST /api/quit` pour fermer ; aperçu Deck via tunnel `ssh -L 47801` + navigateur intégré.

## 6. Consoles et émulateurs (id → émulateur)

ps2 PCSX2 2.8.2 · psp PPSSPP 1.20.4 · psvita Vita3K (build continu, version = date) · ps3 RPCS3 0.0.43+ ·
ps4 shadPS4 0.20 · nes Nestopia (1.53.2 Deck, 2.0.0 PC) · n64 RMG 0.9 · gba mGBA 0.10.5 · nds melonDS 1.1 ·
gc/wii Dolphin 2609a · xbox xemu 0.8.13x · x360 Xenia Canary (commit 48b318a). Pas de Xbox One (aucun émulateur public).
Paramètres > Emulators : installe (GitHub / flatpak --user / AppImage), désinstalle en gardant sauvegardes et réglages.

Leçon : chaque émulateur neuf avait des touches vides ou clavier → toujours écrire les touches explicitement, et
n'éditer RMG/Nestopia que fermés (ils réécrivent leur config en quittant). Deck : fenêtres X11 forcées **par processus**
(`QT_QPA_PLATFORM=xcb` PCSX2/RPCS3/mGBA/melonDS/Dolphin, `SDL_VIDEO_DRIVER=x11` PPSSPP/shadPS4/Nestopia,
`SDL_VIDEODRIVER=x11` xemu/Xenia), `SDL_JOYSTICK_HIDAPI=0` pour Nestopia/mGBA/melonDS/xemu/Xenia. Langue FR partout
où une clé existe (PS2 : dans la NVM du BIOS).

- **PCSX2** : `[Pad1]` SDL-0, pause = Back+Start, BIOS SCPH-70004 (PAL v2.0). **PCSX2 debug** 1.7.3780 pour les jeux de
  `debug-games.json` (série → `{title, renderer}`, software par défaut ; aujourd'hui Splashdown SLES-50486 / SLUS-20223) :
  installé avec PCSX2, réglages réécrits à chaque lancement, cartes à part `Saves/…/PS2/memcards-debug`, `sstates-debug`.
- **RPCS3** : Windows lit `emulators\rpcs3\config\` ; manette `Device: "XInput Pad #1"` (guillemets obligatoires, `#` =
  commentaire YAML). Deck : RPCS3 (SDL3) hors Steam Input voit les manettes physiques ; `rpcs3_set_pad()` réécrit le
  Device du joueur 1 à chaque lancement (manette externe sinon « Steam Deck Controller 1 ») et migre A/B/X/Y vers
  South/East/West/North. Firmware 4.93 installé PC et Deck (`--headless --installfw`). Jeux PSN : dossier par jeu avec
  `.pkg` + `.rap` (installés au 1er lancement, `.rap` → `dev_hdd0/home/00000001/exdata`). Mises à jour disque : `.pkg`
  dans le dossier du jeu, marqué fait seulement si `PARAM.SFO` a changé.
- **Caches shaders (Deck)** : chaque `flatpak run` reçoit `MESA_SHADER_CACHE_DIR=~/.var/app/<app>/cache`
  (`flatpak_shader_cache()`) : le dossier shadercache de Steam est en lecture seule dans les flatpaks.
- **Vita3K** : portable, FR, firmware `PSVUPDAT.PUP` + `PSP2UPDAT.PUP` installé sans fenêtre au 1er jeu. `.vpk`, dossier,
  ou `.pkg` + licence `.rif`/`.work.bin` de même Content ID ; mise à jour `Jeu (Update vX).pkg`. Deck : lancé depuis
  `~/Emulation/psvita/Vita3K-AppDir` (AppImage extraite + lien `bin/shaders-builtin`, sinon segfault RADV),
  `memory-mapping: disabled`.
- **Dolphin** : SDL/0/Steam Virtual Gamepad (Deck), XInput/0/Gamepad (PC), Wiimote + Nunchuk, IR stick droit.
- **xemu** : BIOS `mcpx_1.0.bin` + `Complex_4627.bin` à fournir (absents), HDD vierge xemu-hdd-image dans les saves.
  **Xenia** Deck : AppImage, `--storage_root=~/Emulation/x360 --content_root=<profil>/Xbox 360`.
- Non testés en jeu : Dolphin, xemu, Xenia, Nestopia 2.0 PC (ni manette ni sauvegardes par profil sur PC).

## 7. Profils, sauvegardes, kDrive

- « Qui joue ? », 4 profils max ; compte parent = code 4 chiffres (PBKDF2 salé, 5 erreurs = 30 s). Dès qu'un parent
  existe, ajouter/modifier/supprimer un profil demande le code. Le Deck fait référence ; P.A.D (id `pad`) n'a plus de code.
- Liste commune : `kDrive/Saves/Profils/profiles.json`, copie locale `profiles-shared.json` (reconstruite si absente,
  fusion par nom ; `profiles_conflict_*.json` de kDrive fusionnés puis rangés dans `Profils/_conflits`).
- Avatar : `Profils/<profil>/_avatar.jpeg` (JPEG carré 1000 px, choisi dans l'explorateur, WebP accepté).
- Sauvegardes : `kDrive/Saves/Profils/<profil>/<console>`. Avant chaque lancement `Profiles.apply()` repointe liens /
  jonctions / chemins d'ini (`save_targets()`) ; Deck : `flatpak override --filesystem=~/kDrive/Saves/Profils`.
  Nouvel émulateur → déclarer ses dossiers dans `save_targets()`. Favoris/récents par profil et par appareil.
- Profil supprimé → `Profils/_supprimes`. Sauvegarde d'avant profils : `G:\Jeux\FORMULA\_backups\saves-avant-profils-20261107`.
- Plainte « sauvegarde pas à jour » : chercher des `*_conflict_*` dans `kDrive/Saves` (cas Splashdown 07/11).

## 8. Jaquettes

Une fois par jeu, puis WebP via ffmpeg (480 px de haut, fond 640 px), URL avec date du fichier. Ordre : PS2
xlenore/ps2-covers (série) ; PS3 aldostools/Resources ; GC/Wii art.gametdb.com ; Vita Andiweli/HexFlow-Covers (ID) ;
X360 xboxunity.net (title ID de default.xex, face avant découpée) ; sinon libretro Named_Boxarts (titre puis nom de
fichier) ; PSP dipubadatya/psp-covers-hd. Jamais la jaquette d'une autre console. Ratio réel de boîtier par console
(`BOX_RATIO` dans app.js). Les jaquettes voyagent aussi par la synchro.

## 9. Interface et manette

- Manette : Deck = evdev lu par le serveur (`PadReader`, axes normalisés par appareil), envoyé en SSE `/api/events` ;
  PC = XInput seulement si FORMULA.exe est au premier plan. Jeu lancé → FORMULA ignore la manette ; au retour, boutons
  tenus ignorés jusqu'au relâchement + 0,8 s. API Gamepad = secours.
- Touches : A jouer, B retour (2e B dans la colonne de gauche → Quitter), X recherche (clavier à l'écran sur le Deck
  seulement), Y favori, LB/RB console, Start tri, Select Paramètres, LT/RT taille des jaquettes (50-200 %), L3/R3
  « Qui joue ? », touche G gestionnaire de jeux.
- **Stick droit** : saut entre 5 sections (1 Bibliothèque/Récents/Favoris, 2 consoles, 3 Actualiser→Quitter,
  4 catalogue, 5 barre du haut), seuil 60 % / relâché 35 %, angles par 30° (0° = droite, antihoraire) : 60-120 haut,
  240-300 bas, 300-30 → 4 ; depuis 4 : 120-150 → 1, 150-210 → 2, 210-240 → 3 ; depuis 1 : 30-60 → 5 ; depuis 5 :
  210-240 → 1. Message serveur `{"b":"rs","v":1,"a":angle}`. Testé par appels JS, pas avec une vraie manette.
- **Gestionnaire de jeux** (colonne de gauche) : tailles relatives au disque entier, réservé aux profils parents dès
  qu'un parent existe, confirmation en maintenant A/Entrée/clic 2 s, **déplace** dans la corbeille FORMULA (+ copie
  installée PS3 PSN / Vita), journal `_corbeille/corbeille.json`, ne vide jamais la corbeille, ne touche pas aux
  sauvegardes, vaut pour cet appareil seulement.
- Barre de stockage façon SteamOS (cache 120 s). Interface anglais par défaut, français dans Paramètres.

## 10. Synchro des jeux (`--sync`, port 47810)

`sync.json` : `device`, `token` (≥16 car., secret), `peers` (PC → `192.168.1.89`/`steamdeck.local` ; Deck →
`192.168.1.97`/`THEMIS.local`/`.151`). LAN privé + jeton (`hmac.compare_digest`), sert seulement `roms/` et les
jaquettes. Retente toutes les 5 min, fichiers modifiés depuis <120 s exclus, reprise `*.formula-part`.
Suppressions non propagées : tombstone dans `sync_known.json` (pour faire revenir un fichier : service arrêté, retirer
le chemin de `known` **et** `deleted`). Deck : `formula-sync.service` ; PC : `G:\Jeux\FORMULA\FORMULA synchro.lnk`
(démarrage auto à la main de l'utilisateur). Gros transferts vers le Deck : un seul flux tar par SSH (scratchpad
`resume_copy.py`), pas de scp fichier par fichier.

## 11. PS3 : état des jeux

Disques Redump **chiffrés** : déchiffrés sur PC avec l'outil C# du scratchpad (`Ps3Dec.exe in.iso out.iso <clé 32 hex>`,
secteur 0 = nombre de régions **en clair** puis paires début/fin incluses), puis extraits en dossier
`PS3_GAME` + `PS3_DISC.SFB` (créer le dossier cible avant `Move-Item`). Vérif : EBOOT.BIN commence par `SCE\0`.

| Jeu | PC | Deck |
|---|---|---|
| R&C Quest for Booty, Beyond Good & Evil HD, Killzone HD (PSN) | OK | OK |
| Heavenly Sword (maj 1.10) | OK | OK |
| MotorStorm Apocalypse (maj 1.06 refusée : il faut la chaîne jusqu'à 1.05) | OK | OK |
| R&C Tools of Destruction | OK | OK |
| R&C Collection | OK | OK |
| R&C A Crack in Time, Into the Nexus | OK | non (copie Ratchet en pause par l'utilisateur ; ACiT partiel possible) |
| Sly Collection, Asura's Wrath | OK | non (refusés par l'utilisateur) |
| Killzone 2 / Killzone 3 | en attente : re-téléchargement par l'utilisateur dans `G:\Downloads`, clés reçues, ne pas toucher avant qu'il dise fini | supprimé (chiffré) |

Autres : Dante's Inferno PS3 corrompu (non ajouté, l'utilisateur a la version 360). WipEout 2048 retiré (licence ≠ jeu).
Vita : Gravity Rush, Killzone Mercenary (PC et Deck). Licences Vita inutilisées dans `C:\Users\iridi\Downloads`.

## 12. Pistes ouvertes

Nestopia 2.0 PC (manette, sauvegardes par profil) ; tests en jeu Dolphin/xemu/Xenia ; BIOS Xbox à fournir ;
MotorStorm maj 1.05 ; Killzone 2/3 quand téléchargés (puis Deck selon la règle) ; manette Xbox Series BT sur RPCS3 Deck
(nom supposé) ; stick droit à valider avec une vraie manette.
