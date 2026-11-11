#!/usr/bin/env python3
"""FORMULA - lanceur d'émulateurs pour Steam Deck.

Petit serveur local (stdlib uniquement) qui :
  - scanne ~/Emulation/roms/<console> et lit les infos des jeux (titre, numéro de série),
  - télécharge les jaquettes officielles en arrière-plan,
  - sert l'interface web (dossier web/),
  - lance le bon émulateur quand on clique sur un jeu.

Pour ajouter un émulateur plus tard : ajouter une entrée dans SYSTEMS
(ou dans ~/.config/formula/systems.json, même format).
"""
import base64
import gzip
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
APP_DIR = Path(__file__).resolve().parent
WEB_DIR = APP_DIR / "web"
IS_WIN = os.name == "nt"
if IS_WIN:
    # Windows : le code (dépôt git) et les données lourdes sont séparés. Le dossier de données
    # (émulateurs, roms, bios, formula-data, python) est donné par FORMULA_BASE ou formula-base.txt.
    _base_file = APP_DIR / "formula-base.txt"
    BASE = Path(os.environ.get("FORMULA_BASE")
                or (_base_file.read_text(encoding="utf-8").strip() if _base_file.exists() else APP_DIR.parent))
    ROMS = BASE / "roms"
    DATA = BASE / "formula-data"
    EMU = BASE / "emulators"
else:
    ROMS = HOME / "Emulation" / "roms"
    DATA = HOME / ".local" / "share" / "formula"
COVERS = DATA / "covers"
LIB_FILE = DATA / "library.json"
PORT = int(os.environ.get("FORMULA_PORT", "47800"))
SYNC_PORT = int(os.environ.get("FORMULA_SYNC_PORT", "47810"))
UA = {"User-Agent": "FORMULA/1.0 (Steam Deck launcher)"}
STARTED = time.time()
# version MAJEUR.MINEUR.CORRECTIF (correctif sur 3 chiffres), propre à chaque plateforme (branche git)
try:
    VERSION = (APP_DIR / "VERSION").read_text(encoding="utf-8").strip()
except OSError:
    VERSION = "dev"
PLATFORM = "Windows" if IS_WIN else "Steam Deck"
NO_WINDOW = 0x08000000 if IS_WIN else 0   # CREATE_NO_WINDOW : pas de console qui clignote (ffmpeg, tar…)
SETTINGS_FILE = DATA / "settings.json"


def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"lang": "en"}

SYSTEMS = {
    "ps2": {
        "name": "PlayStation 2", "short": "PS2", "order": 2,
        "exts": [".iso", ".chd", ".cso", ".bin", ".gz"],
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "net.pcsx2.PCSX2", "-batch", "-nogui", "-fullscreen", "--", "{path}"],
        "libretro": "Sony - PlayStation 2",
    },
    "psp": {
        "name": "PlayStation Portable", "short": "PSP", "order": 3,
        "exts": [".iso", ".cso", ".pbp", ".chd"],
        "cmd": ["flatpak", "run", "--user", "--env=SDL_VIDEO_DRIVER=x11", "org.ppsspp.PPSSPP", "--fullscreen", "{path}"],
        "libretro": "Sony - PlayStation Portable",
        # libretro n'a pas toutes les jaquettes PSP : dépôt GitHub de jaquettes PSP aux noms No-Intro
        "covers_repo": ("dipubadatya/psp-covers-hd", "main", "covers/"),
    },
    "psvita": {
        "name": "PlayStation Vita", "short": "Vita", "order": 3.5,
        # .vpk (archive d'installation), .pkg PSN (avec sa licence, voir vita_license) ou dossier de jeu
        # décompressé (sce_sys/param.sfo + eboot.bin).
        # Vita3K installe le jeu au premier lancement, puis le lance directement par son identifiant.
        "exts": [".vpk", ".pkg"], "folders": True,
        "cmd": [str(HOME / "Emulation/psvita/Vita3K-x86_64.AppImage"), "{path}"],
        "cwd": str(HOME / "Emulation/psvita"),
        # DISABLE_AUTO_UPDATES : l'AppImage propose sinon de télécharger un outil de mise à jour et de se
        # remplacer elle-même (fenêtres au lancement) ; FORMULA gère les versions dans Paramètres
        "env": {"SDL_VIDEO_DRIVER": "x11", "SDL_VIDEODRIVER": "x11", "SDL_JOYSTICK_HIDAPI": "0",
                "DISABLE_AUTO_UPDATES": "1"},
        "libretro": "Sony - PlayStation Vita",
        # libretro n'a qu'une dizaine de jaquettes Vita : base HexFlow, une image par identifiant (PCSF00243…)
        "cover_by_id": "https://raw.githubusercontent.com/Andiweli/HexFlow-Covers/main/Covers/PSVita/{serial}.png",
    },
    "ps3": {
        "name": "PlayStation 3", "short": "PS3", "order": 4,
        "exts": [".iso"], "folders": True,
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "net.rpcs3.RPCS3", "--no-gui", "{path}"],
        "libretro": "Sony - PlayStation 3",
    },
    "ps4": {
        "name": "PlayStation 4", "short": "PS4", "order": 5,
        "exts": [], "folders": True,
        "cmd": [str(HOME / "Emulation/ps4/Shadps4-sdl.AppImage"), "-g", "{path}", "--fullscreen", "true"],
        "cwd": str(HOME / "Emulation/ps4"),
        "env": {"SDL_VIDEO_DRIVER": "x11"},
    },
    "nes": {
        "name": "NES", "short": "NES", "order": 9,
        "exts": [".nes", ".zip", ".7z", ".fds"],
        # SDL_JOYSTICK_HIDAPI=0 : Nestopia ne voit que la manette virtuelle de Steam (port 0, disposition
        # Xbox 360, priorité Steam Input respectée) et pas la manette physique du Deck.
        "cmd": ["flatpak", "run", "--user", "--env=SDL_VIDEO_DRIVER=x11", "--env=GDK_BACKEND=x11",
                "--env=SDL_JOYSTICK_HIDAPI=0", "ca._0ldsk00l.Nestopia", "-f", "{path}"],
        "libretro": "Nintendo - Nintendo Entertainment System",
    },
    "n64": {
        "name": "Nintendo 64", "short": "N64", "order": 9.5,
        "exts": [".z64", ".n64", ".v64", ".zip", ".7z"],
        "cmd": ["flatpak", "run", "--user", "com.github.Rosalie241.RMG",
                "--fullscreen", "--nogui", "--quit-after-emulation", "{path}"],
        "libretro": "Nintendo - Nintendo 64",
    },
    "gba": {
        "name": "Game Boy Advance", "short": "GBA", "order": 10,
        "exts": [".gba", ".gb", ".gbc", ".zip", ".7z"],
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "--env=SDL_JOYSTICK_HIDAPI=0", "io.mgba.mGBA", "-f", "{path}"],
        "libretro": "Nintendo - Game Boy Advance",
    },
    "nds": {
        "name": "Nintendo DS", "short": "DS", "order": 11,
        "exts": [".nds", ".zip", ".7z"],
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "--env=SDL_JOYSTICK_HIDAPI=0", "net.kuribo64.melonDS", "-f", "{path}"],
        "libretro": "Nintendo - Nintendo DS",
    },
    "gc": {
        "name": "GameCube", "short": "GC", "order": 12,
        "exts": [".iso", ".gcm", ".rvz", ".ciso", ".gcz"],
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "org.DolphinEmu.dolphin-emu", "-b", "-e", "{path}"],
        "libretro": "Nintendo - GameCube", "gametdb": True,
    },
    "wii": {
        "name": "Wii", "short": "Wii", "order": 13,
        "exts": [".iso", ".wbfs", ".rvz", ".ciso", ".gcz"],
        "cmd": ["flatpak", "run", "--user", "--env=QT_QPA_PLATFORM=xcb", "org.DolphinEmu.dolphin-emu", "-b", "-e", "{path}"],
        "libretro": "Nintendo - Wii", "gametdb": True,
    },
    "xbox": {
        "name": "Xbox", "short": "Xbox", "order": 14,
        # images XISO (format attendu par xemu)
        "exts": [".iso", ".xiso"],
        # xemu est en SDL2 : SDL_VIDEODRIVER (le flatpak le règle sur wayland,x11 par défaut)
        "cmd": ["flatpak", "run", "--user", "--env=SDL_VIDEODRIVER=x11", "--env=SDL_JOYSTICK_HIDAPI=0",
                "app.xemu.xemu", "-full-screen", "-dvd_path", "{path}"],
        "libretro": "Microsoft - Xbox",
    },
    "x360": {
        "name": "Xbox 360", "short": "360", "order": 15,
        # disque (.iso), jeu extrait (dossier avec default.xex) ou archive .zar
        "exts": [".iso", ".xex", ".zar"],
        # l'AppImage ne peut pas utiliser portable.txt (son dossier est le point de montage) : réglages dans
        # ~/Emulation/x360, contenu et sauvegardes dans kDrive
        "cmd": [str(HOME / "Emulation/x360/xenia_canary.AppImage"), "--storage_root=" + str(HOME / "Emulation/x360"),
                "--content_root=" + str(HOME / "kDrive/Saves/Xbox 360"), "--fullscreen=true", "{path}"],
        "cwd": str(HOME / "Emulation/x360"),
        "env": {"SDL_VIDEODRIVER": "x11", "GDK_BACKEND": "x11", "SDL_JOYSTICK_HIDAPI": "0"},
        "libretro": "Microsoft - Xbox 360",
    },
}

if IS_WIN:
    # mêmes consoles, émulateurs Windows portables dans <BASE>/emulators
    WIN_CMDS = {
        "ps2": ("pcsx2/pcsx2-qt.exe", ["-batch", "-nogui", "-fullscreen", "--", "{path}"]),
        "psp": ("ppsspp/PPSSPPWindows64.exe", ["--fullscreen", "{path}"]),
        "ps3": ("rpcs3/rpcs3.exe", ["--no-gui", "{path}"]),
        "psvita": ("vita3k/Vita3K.exe", ["{path}"]),
        "ps4": ("shadps4/shadPS4.exe", ["-g", "{path}", "--fullscreen", "true"]),
        "nes": ("nestopia/nestopia.exe", ["-f", "{path}"]),
        "n64": ("rmg/RMG.exe", ["--fullscreen", "--nogui", "--quit-after-emulation", "{path}"]),
        "gba": ("mgba/*/mGBA.exe", ["-f", "{path}"]),   # le sous-dossier porte le numéro de version
        "nds": ("melonds/melonDS.exe", ["-f", "{path}"]),
        "gc": ("dolphin/Dolphin-x64/Dolphin.exe", ["-b", "-e", "{path}"]),
        "wii": ("dolphin/Dolphin-x64/Dolphin.exe", ["-b", "-e", "{path}"]),
        "xbox": ("xemu/xemu.exe", ["-full-screen", "-dvd_path", "{path}"]),
        "x360": ("xenia/xenia_canary.exe", ["--fullscreen=true", "{path}"]),
    }
    for _k, (_exe, _args) in WIN_CMDS.items():
        SYSTEMS[_k]["cmd"] = [str(EMU / _exe)] + _args   # motif résolu au lancement (resolve_exe)
        SYSTEMS[_k].pop("env", None)


def resolve_exe(path):
    """Windows : remplace un motif (« mgba/*/mGBA.exe ») par le fichier réellement installé."""
    p = Path(path)
    if "*" not in path:
        return p if p.exists() else None
    found = sorted(EMU.glob(str(p.relative_to(EMU)).replace("\\", "/")))
    return found[-1] if found else None


# ---------------------------------------------------------------- PCSX2 debug
# Certains jeux sont cassés par une régression des PCSX2 récents (Splashdown : la course ne démarre pas,
# pas d'eau). Ils sont listés dans debug-games.json et lancés avec un ancien PCSX2 fixé, installé en même
# temps que le PCSX2 principal (il n'apparaît pas comme émulateur séparé).
PCSX2_DEBUG = {
    "version": "1.7.3780",
    "win": {"dir": "pcsx2-debug", "exe": "pcsx2-qtx64-avx2.exe",
            "url": "https://github.com/PCSX2/pcsx2/releases/download/v1.7.3780/"
                   "pcsx2-v1.7.3780-windows-64bit-AVX2-Qt.7z"},
    "appimage": {"dir": "pcsx2-debug", "file": "pcsx2-debug.AppImage",
                 "url": "https://github.com/PCSX2/pcsx2/releases/download/v1.7.3780/"
                        "pcsx2-v1.7.3780-linux-AppImage-64bit-AVX2-Qt.AppImage"},
}
DEBUG_GAMES_FILE = APP_DIR / "debug-games.json"
GS_RENDERERS = {"auto": -1, "dx11": 3, "opengl": 12, "software": 13, "vulkan": 14, "dx12": 15}
# PCSX2 1.7 nomme les boutons de façade A/B/X/Y (FaceSouth… depuis la 2.0)
PCSX2_DEBUG_PAD = {
    "Type": "DualShock2", "Up": "SDL-0/DPadUp", "Right": "SDL-0/DPadRight", "Down": "SDL-0/DPadDown",
    "Left": "SDL-0/DPadLeft", "Select": "SDL-0/Back", "Start": "SDL-0/Start", "L1": "SDL-0/LeftShoulder",
    "L2": "SDL-0/+LeftTrigger", "R1": "SDL-0/RightShoulder", "R2": "SDL-0/+RightTrigger", "L3": "SDL-0/LeftStick",
    "R3": "SDL-0/RightStick", "LUp": "SDL-0/-LeftY", "LRight": "SDL-0/+LeftX", "LDown": "SDL-0/+LeftY",
    "LLeft": "SDL-0/-LeftX", "RUp": "SDL-0/-RightY", "RRight": "SDL-0/+RightX", "RDown": "SDL-0/+RightY",
    "RLeft": "SDL-0/-RightX", "LargeMotor": "SDL-0/LargeMotor", "SmallMotor": "SDL-0/SmallMotor",
    "Triangle": "SDL-0/Y", "Circle": "SDL-0/B", "Cross": "SDL-0/A", "Square": "SDL-0/X",
}


def pcsx2_debug_dir():
    return EMU / PCSX2_DEBUG["win"]["dir"] if IS_WIN else HOME / "Emulation" / PCSX2_DEBUG["appimage"]["dir"]


def pcsx2_debug_exe():
    if IS_WIN:
        return pcsx2_debug_dir() / PCSX2_DEBUG["win"]["exe"]
    return pcsx2_debug_dir() / PCSX2_DEBUG["appimage"]["file"]


def debug_game(g):
    """Réglages debug d'un jeu (dict) s'il est inscrit dans debug-games.json, sinon None."""
    try:
        games = json.loads(DEBUG_GAMES_FILE.read_text(encoding="utf-8")).get(g["system"], {})
    except Exception:
        return None
    entry = games.get(g.get("serial") or "")
    return entry if isinstance(entry, dict) else None


def ini_update(path, section, values, sep=" = "):
    """Écrit des clés dans une section d'un .ini façon PCSX2 (« clé = valeur »), sans toucher au reste."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    start = next((i for i, l in enumerate(lines) if l.strip() == f"[{section}]"), None)
    if start is None:
        lines += ([""] if lines else []) + [f"[{section}]"]
        start = len(lines) - 1
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("[")), len(lines))
    todo = {k: str(v) for k, v in values.items()}
    for i in range(start + 1, end):
        k = lines[i].split("=", 1)[0].strip()
        if k in todo:
            lines[i] = f"{k}{sep}{todo.pop(k)}"
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    lines[end:end] = [f"{k}{sep}{v}" for k, v in todo.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pcsx2_debug_configure(renderer="software"):
    """Réglages du PCSX2 debug, réécrits à chaque lancement : même BIOS et même manette que le PCSX2
    principal, cartes mémoire séparées (dans kDrive) pour qu'une vieille version n'écrive jamais dans les
    cartes du PCSX2 principal."""
    d = pcsx2_debug_dir()
    saves = PROFILES.saves_dir() / "PS2"      # profil actif (voir Profiles)
    for sub in ("memcards-debug", "sstates-debug"):
        (saves / sub).mkdir(parents=True, exist_ok=True)
    if IS_WIN:
        (d / "portable.ini").write_text("RunWizard=0\n", encoding="utf-8")
        ini, bios = d / "inis" / "PCSX2.ini", BASE / "bios" / "ps2"
    else:
        # l'AppImage ne peut pas être portable : réglages isolés via XDG_CONFIG_HOME (voir pcsx2_debug_cmd)
        ini, bios = d / "config" / "PCSX2" / "inis" / "PCSX2.ini", HOME / "Emulation" / "bios" / "ps2"
    ini_update(ini, "UI", {"SettingsVersion": 1, "SetupWizardIncomplete": "false", "StartFullscreen": "true",
                           "ConfirmShutdown": "false", "HideMouseCursor": "true"})
    ini_update(ini, "Folders", {"Bios": bios, "MemoryCards": saves / "memcards-debug",
                                "Savestates": saves / "sstates-debug"})
    if (bios / "SCPH-70004_BIOS_V12_PAL_200.BIN").exists():   # même BIOS que le PCSX2 principal
        ini_update(ini, "Filenames", {"BIOS": "SCPH-70004_BIOS_V12_PAL_200.BIN"})
    ini_update(ini, "GameList", {"RecursivePaths": ROMS / "ps2"})
    ini_update(ini, "AutoUpdater", {"CheckAtStartup": "false"})
    ini_update(ini, "EmuCore/GS", {"Renderer": GS_RENDERERS.get(str(renderer).lower(), 13)})
    ini_update(ini, "InputSources", {"SDL": "true", "SDLControllerEnhancedMode": "false"})
    ini_update(ini, "Pad1", PCSX2_DEBUG_PAD)
    ini_update(ini, "Hotkeys", {"OpenPauseMenu": "SDL-0/Back & SDL-0/Start",
                                "ToggleFullscreen": "Keyboard/Alt & Keyboard/Return"})


def pcsx2_debug_cmd(path):
    """Commande, dossier et environnement pour lancer un jeu avec le PCSX2 debug."""
    env = {}
    if not IS_WIN:
        env = {"QT_QPA_PLATFORM": "xcb", "XDG_CONFIG_HOME": str(pcsx2_debug_dir() / "config")}
    return [str(pcsx2_debug_exe()), "-batch", "-nogui", "-fullscreen", "--", path], str(pcsx2_debug_dir()), env


_extra = (DATA if IS_WIN else HOME / ".config" / "formula") / "systems.json"
if _extra.exists():
    try:
        SYSTEMS.update(json.loads(_extra.read_text()))
    except Exception as e:  # un fichier mal formé ne doit pas empêcher le lancement
        print("systems.json ignoré :", e, file=sys.stderr)


# ---------------------------------------------------------------- lecture des disques

class Disc:
    """Accès en lecture à un ISO ou un CSO (ISO compressé PSP/PS2)."""

    def __init__(self, path):
        self.f = open(path, "rb")
        self.cso = None
        head = self.f.read(24)
        if head[:4] == b"CISO":
            _, hsz, total, bs, ver, align = struct.unpack("<4sIQIBB2x", head)
            n = (total + bs - 1) // bs
            self.f.seek(24)
            idx = struct.unpack("<%dI" % (n + 1), self.f.read(4 * (n + 1)))
            self.cso = (bs, align, idx)
            self._cache = (-1, b"")

    def _block(self, i):
        if self._cache[0] == i:
            return self._cache[1]
        bs, align, idx = self.cso
        plain = idx[i] & 0x80000000
        a = (idx[i] & 0x7FFFFFFF) << align
        b = (idx[i + 1] & 0x7FFFFFFF) << align
        self.f.seek(a)
        d = self.f.read(b - a)
        d = d[:bs] if plain else zlib.decompress(d, -15)
        self._cache = (i, d)
        return d

    def read(self, off, size):
        if not self.cso:
            self.f.seek(off)
            return self.f.read(size)
        bs = self.cso[0]
        out = bytearray()
        while size > 0:
            blk = self._block(off // bs)
            part = blk[off % bs: off % bs + size]
            if not part:
                break
            out += part
            off += len(part)
            size -= len(part)
        return bytes(out)

    def close(self):
        self.f.close()

    # ISO9660 --------------------------------------------------------------
    def _dir(self, lba, size):
        data = self.read(lba * 2048, size)
        p, out = 0, {}
        while p < len(data):
            ln = data[p]
            if ln == 0:
                p = (p // 2048 + 1) * 2048
                continue
            r = data[p:p + ln]
            name = r[33:33 + r[32]]
            if name not in (b"\0", b"\1"):
                nm = name.decode("latin1").split(";")[0].upper()
                out[nm] = (struct.unpack("<I", r[2:6])[0], struct.unpack("<I", r[10:14])[0], bool(r[25] & 2))
            p += ln
        return out

    def file(self, path, limit=8 * 1024 * 1024):
        pvd = self.read(16 * 2048, 2048)
        if pvd[1:6] != b"CD001":
            return None
        root = pvd[156:190]
        lba, size = struct.unpack("<I", root[2:6])[0], struct.unpack("<I", root[10:14])[0]
        parts = [p for p in path.upper().split("/") if p]
        for i, part in enumerate(parts):
            ent = self._dir(lba, size).get(part)
            if not ent:
                return None
            lba, size, is_dir = ent
            if i == len(parts) - 1:
                return None if is_dir else self.read(lba * 2048, min(size, limit))
        return None


def parse_sfo(data):
    if not data or data[:4] != b"\0PSF":
        return {}
    _, _, kt, dt, n = struct.unpack("<4sIIII", data[:20])
    out = {}
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack("<HHIII", data[20 + i * 16: 36 + i * 16])
        key = data[kt + ko: data.index(b"\0", kt + ko)].decode("latin1")
        raw = data[dt + do: dt + do + ln]
        if fmt == 0x0404:
            out[key] = struct.unpack("<I", raw[:4])[0]
        else:
            out[key] = raw.split(b"\0")[0].decode("utf-8", "replace")
    if isinstance(out.get("TITLE"), str):
        # « God of War®: Ghost of Sparta », « Killzone™: Liberation » : symboles de marque retirés
        out["TITLE"] = re.sub(r"\s*[™®©]", "", out["TITLE"]).strip()
    return out


# ---------------------------------------------------------------- paquets PS Vita (.pkg)
# Seule la couche extérieure du paquet est lue ici (clés publiques des paquets), pour le titre,
# l'identifiant et les images. Le contenu du jeu reste chiffré : Vita3K l'installe avec la licence.

_AES_S = [0] * 256


def _aes_init():
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        r = lambda n: ((q << n) | (q >> (8 - n))) & 0xFF
        _AES_S[p] = q ^ r(1) ^ r(2) ^ r(3) ^ r(4) ^ 0x63
        if p == 1:
            break
    _AES_S[0] = 0x63


_aes_init()


def _xt(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


def aes_expand(key):
    w, rcon = list(key), 1
    for i in range(16, 176, 4):
        t = w[i - 4:i]
        if i % 16 == 0:
            t = [_AES_S[t[1]] ^ rcon, _AES_S[t[2]], _AES_S[t[3]], _AES_S[t[0]]]
            rcon = _xt(rcon)
        w += [w[i - 16 + j] ^ t[j] for j in range(4)]
    return w


def aes_encrypt(rk, blk):
    s = [blk[i] ^ rk[i] for i in range(16)]
    for rnd in range(1, 11):
        s = [_AES_S[b] for b in s]
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]
        if rnd != 10:
            n = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                t = a[0] ^ a[1] ^ a[2] ^ a[3]
                n += [a[j] ^ t ^ _xt(a[j] ^ a[(j + 1) % 4]) for j in range(4)]
            s = n
        s = [s[i] ^ rk[16 * rnd + i] for i in range(16)]
    return bytes(s)


PKG_KEYS = {1: bytes.fromhex("07F2C68290B50D2C33818D709B60E62B"),
            2: bytes.fromhex("E31A70C9CE1DD72BF3C0622963F2ECCB"),
            3: bytes.fromhex("423ACA3A2BD5649F9686ABAD6FD8801F"),
            4: bytes.fromhex("AF07FD59652527BAF13388668CE11C7B")}


class VitaPkg:
    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(0x100)
        if h[:4] != b"\x7fPKG":
            raise ValueError("pas un paquet PKG")
        self.count = struct.unpack(">I", h[0x14:0x18])[0]
        self.doff = struct.unpack(">Q", h[0x20:0x28])[0]
        self.content_id = h[0x30:0x60].split(b"\0")[0].decode("ascii", "replace")
        iv, kt = h[0x70:0x80], h[0xE7] & 7
        key = PKG_KEYS[1] if kt == 1 else aes_encrypt(aes_expand(PKG_KEYS[kt]), iv)
        self.rk, self.iv = aes_expand(key), int.from_bytes(iv, "big")

    def close(self):
        self.f.close()

    def read(self, off, size):
        start = off - off % 16
        self.f.seek(self.doff + start)
        data = self.f.read(size + off % 16)
        out = bytearray()
        for i in range(0, len(data), 16):
            ks = aes_encrypt(self.rk, ((self.iv + (start + i) // 16) % (1 << 128)).to_bytes(16, "big"))
            out += bytes(a ^ b for a, b in zip(data[i:i + 16], ks))
        return bytes(out[off % 16: off % 16 + size])

    def files(self):
        if getattr(self, "_files", None) is not None:
            return self._files
        tbl = self.read(0, 32 * self.count)
        out = {}
        for i in range(self.count):
            no, ns, do, ds = struct.unpack(">IIQQ", tbl[32 * i:32 * i + 24])
            out[self.read(no, ns).decode("utf-8", "replace").lower()] = (do, ds)
        self._files = out
        return out

    def file(self, name, limit=8 << 20):
        ent = self.files().get(name.lower())
        return self.read(ent[0], ent[1]) if ent and 0 < ent[1] <= limit else None


def rif_to_zrif(rif):
    """Licence .rif / work.bin (512 octets) -> zRIF (format attendu par Vita3K --zrif)."""
    c = zlib.compressobj(9, zlib.DEFLATED, 10)
    return base64.b64encode(c.compress(rif) + c.flush()).decode()


def read_pbp(path):
    with open(path, "rb") as f:
        h = f.read(40)
        if h[:4] != b"\0PBP":
            return {}, None, None
        offs = list(struct.unpack("<8I", h[8:40]))
        size = os.path.getsize(path)
        offs.append(size)
        def chunk(i):
            f.seek(offs[i])
            return f.read(max(0, offs[i + 1] - offs[i]))
        return parse_sfo(chunk(0)), chunk(1) or None, chunk(4) or None


def xex_title_id(head):
    """Identifiant de titre (8 chiffres hexa) d'un exécutable Xbox 360 (en-tête XEX2)."""
    if head[:4] != b"XEX2":
        return None
    count = struct.unpack(">I", head[0x14:0x18])[0]
    for i in range(min(count, 64)):
        key, val = struct.unpack(">II", head[0x18 + 8 * i: 0x20 + 8 * i])
        if key == 0x00040006 and val + 16 <= len(head):     # informations d'exécution
            return "%08X" % struct.unpack(">I", head[val + 12: val + 16])[0]
    return None


def xbox360_title_id(path):
    """Lit default.xex dans une image de disque Xbox 360 (système de fichiers XDVDFS) ou un .xex."""
    with open(path, "rb") as f:
        if path.suffix.lower() == ".xex":
            return xex_title_id(f.read(0x10000))
        # la partition de jeu commence à un décalage fixe selon le type de disque (XGD3, XGD2, XGD1, XISO)
        for part in (0x2080000, 0xFD90000, 0x18300000, 0):
            f.seek(part + 32 * 2048)
            vd = f.read(28)
            if vd[:20] != b"MICROSOFT*XBOX*MEDIA":
                continue
            root, rsize = struct.unpack("<II", vd[20:28])
            f.seek(part + root * 2048)
            table = f.read(min(rsize, 1 << 20))
            stack = [0]
            while stack:                 # arbre binaire d'entrées, positions en mots de 4 octets
                p = stack.pop() * 4
                if p + 14 > len(table) or table[p:p + 2] == b"\xff\xff":
                    continue
                left, right, sector, size, _, nlen = struct.unpack("<HHIIBB", table[p:p + 14])
                if table[p + 14:p + 14 + nlen].lower() == b"default.xex":
                    f.seek(part + sector * 2048)
                    return xex_title_id(f.read(min(size, 0x10000)))
                stack += [x for x in (left, right) if x]
    return None


def nintendo_disc_header(path):
    """ID (ex. RMCP01) et titre d'un disque GameCube/Wii : ISO/GCM, WBFS ou RVZ."""
    with open(path, "rb") as f:
        head = f.read(0x400)
    if head[:4] in (b"RVZ\x01", b"WIA\x01"):
        dh = head[0x58:0x58 + 0x80]
    elif head[:4] == b"WBFS":
        dh = head[0x200:0x280]
    elif head[:4] == b"CISO":
        with open(path, "rb") as f:
            f.seek(0x8000)
            dh = f.read(0x80)
    else:
        dh = head[:0x80]
    gid = dh[:6]
    if not re.fullmatch(rb"[A-Z0-9]{6}", gid):
        return None, None
    title = dh[0x20:0x80].split(b"\0")[0].decode("latin1").strip()
    return gid.decode(), title or None


_gameindex = None


def ps2_name(serial):
    """Nom officiel depuis la base de PCSX2 (GameIndex.yaml)."""
    global _gameindex
    if _gameindex is None:
        _gameindex = {}
        base = EMU / "pcsx2" if IS_WIN else HOME / ".local/share/flatpak/app/net.pcsx2.PCSX2"
        for gi in base.glob("**/resources/GameIndex.yaml"):
            cur = None
            for line in gi.read_text("utf-8", "replace").splitlines():
                m = re.match(r"^([A-Z]{4}-\d{5}):", line)
                if m:
                    cur = m.group(1)
                    _gameindex[cur] = {}
                elif cur and line.startswith("  ") and not line.startswith("   "):
                    m = re.match(r'^  (name|name-en|region):\s*"?(.*?)"?\s*$', line)
                    if m:
                        _gameindex[cur][m.group(1)] = m.group(2)
            break
    e = _gameindex.get(serial, {})
    return e.get("name-en") or e.get("name"), e.get("region")


def clean_name(stem):
    s = re.sub(r"[\[(][^\])]*[\])]", "", stem)
    s = re.sub(r"\s+", " ", s.replace("_", " ")).strip(" -.")
    return s or stem


# ---------------------------------------------------------------- scan

def game_id(path):
    return hashlib.sha1(str(path).encode()).hexdigest()[:12]


def save_asset(gid, kind, data, ext=".png"):
    if not data:
        return None
    COVERS.mkdir(parents=True, exist_ok=True)
    p = COVERS / f"{gid}_{kind}{ext}"
    p.write_bytes(data)
    return optimize_image(p.name, kind)


# Taille max à l'affichage (cartes ~150x210, fond flouté) avec de la marge pour la netteté.
IMG_MAX = {"cover": "scale=-2:min(480\\,ih):flags=lanczos", "icon": "scale=-2:min(480\\,ih):flags=lanczos",
           "hero": "scale=min(640\\,iw):-2:flags=lanczos"}


def optimize_image(name, kind):
    """Convertit une image en WebP redimensionné (une jaquette passe de ~1 Mo à ~50 Ko).
    Renvoie le nouveau nom, ou l'ancien si ffmpeg n'est pas disponible ou échoue."""
    if not name or name.endswith(".webp"):
        return name
    src = COVERS / name
    dst = src.with_suffix(".webp")
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                        "-vf", IMG_MAX.get(kind, IMG_MAX["cover"]), "-c:v", "libwebp",
                        "-quality", "82", "-compression_level", "6", str(dst)],
                       check=True, timeout=60, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        if dst.stat().st_size == 0:
            raise OSError("fichier vide")
    except Exception as e:
        print("compression impossible", name, e, file=sys.stderr)
        dst.unlink(missing_ok=True)
        return name
    src.unlink(missing_ok=True)
    return dst.name


def optimize_library(lib):
    """Compresse les images déjà téléchargées avant l'ajout de la compression."""
    for g in list(lib.games.values()):
        changed = False
        for kind in ("cover", "icon", "hero"):
            n = g.get(kind)
            if n and not n.endswith(".webp") and (COVERS / n).exists():
                g[kind] = optimize_image(n, kind)
                changed = changed or g[kind] != n
        if changed:
            with lib.lock:
                lib.save()


def scan_file(sysid, path):
    g = {"system": sysid, "path": str(path), "title": clean_name(path.stem), "serial": None, "region": None}
    if path.stem.lower() == "default":      # jeu Xbox 360 extrait : le nom est celui du dossier
        g["title"] = clean_name(path.parent.name)
    gid = g["id"] = game_id(path)
    ext = path.suffix.lower()
    try:
        if sysid in ("gc", "wii"):
            g["serial"], title = nintendo_disc_header(path)
            g["title"] = title or g["title"]
            g["launch"] = str(path)
            return g
        if sysid == "x360":
            g["serial"] = xbox360_title_id(path)
        if sysid == "psvita" and ext == ".vpk":
            import zipfile
            with zipfile.ZipFile(path) as z:
                names = {n.lower(): n for n in z.namelist()}
                rd = lambda n: z.read(names[n]) if n in names else None
                sfo = parse_sfo(rd("sce_sys/param.sfo"))
                g["title"] = sfo.get("TITLE") or g["title"]
                g["serial"] = sfo.get("TITLE_ID")
                g["icon"] = save_asset(gid, "icon", rd("sce_sys/icon0.png"))
                g["hero"] = save_asset(gid, "hero", rd("sce_sys/pic0.png") or rd("sce_sys/livearea/contents/bg.png"))
        if sysid == "psvita" and ext == ".pkg":
            pkg = VitaPkg(path)
            try:
                files = pkg.files()
                rd = lambda n: pkg.read(*files[n]) if n in files and 0 < files[n][1] <= 8 << 20 else None
                sfo = parse_sfo(rd("sce_sys/param.sfo"))
                g["title"] = sfo.get("TITLE") or g["title"]
                g["serial"] = sfo.get("TITLE_ID") or pkg.content_id[7:16]
                g["content_id"] = pkg.content_id
                # les images sont chiffrées avec la licence (PFS) dans la plupart des paquets :
                # on les prend dans le jeu déjà installé par Vita3K, s'il l'est
                app = vita_root() / "portable" / "fs" / "ux0" / "app" / (g["serial"] or "-") / "sce_sys"
                png = lambda b: b if b and b[:8] == b"\x89PNG\r\n\x1a\n" else None
                img = lambda rel: png(rd("sce_sys/" + rel)) or png((app / rel).read_bytes() if (app / rel).is_file() else None)
                g["icon"] = save_asset(gid, "icon", img("icon0.png"))
                g["hero"] = save_asset(gid, "hero", img("pic0.png") or img("livearea/contents/bg0.png")
                                       or img("livearea/contents/bg.png"))
            finally:
                pkg.close()
        if sysid in ("gba", "nds") and ext in (".gba", ".nds"):
            with open(path, "rb") as f:
                h = f.read(0x200)
            code = h[0xAC:0xB0] if sysid == "gba" else h[0x0C:0x10]
            if re.fullmatch(rb"[A-Z0-9]{4}", code):
                g["serial"] = code.decode()
        if sysid == "psp" and ext == ".pbp":
            sfo, icon, pic1 = read_pbp(path)
            g["title"] = sfo.get("TITLE") or g["title"]
            g["serial"] = sfo.get("DISC_ID")
            g["icon"] = save_asset(gid, "icon", icon)
            g["hero"] = save_asset(gid, "hero", pic1)
        elif ext in (".iso", ".cso"):
            d = Disc(path)
            try:
                if sysid == "ps2":
                    cnf = d.file("SYSTEM.CNF", 4096) or b""
                    m = re.search(rb"BOOT2?\s*=\s*cdrom0?:\\?([A-Z]{4})[_-](\d{3})\.(\d{2})", cnf)
                    if m:
                        g["serial"] = f"{m.group(1).decode()}-{m.group(2).decode()}{m.group(3).decode()}"
                        name, region = ps2_name(g["serial"])
                        g["title"] = name or g["title"]
                        g["region"] = region
                elif sysid == "psp":
                    sfo = parse_sfo(d.file("PSP_GAME/PARAM.SFO"))
                    g["title"] = sfo.get("TITLE") or g["title"]
                    g["serial"] = sfo.get("DISC_ID")
                    g["icon"] = save_asset(gid, "icon", d.file("PSP_GAME/ICON0.PNG"))
                    g["hero"] = save_asset(gid, "hero", d.file("PSP_GAME/PIC1.PNG"))
                elif sysid == "ps3":
                    sfo = parse_sfo(d.file("PS3_GAME/PARAM.SFO"))
                    g["title"] = sfo.get("TITLE") or g["title"]
                    g["serial"] = sfo.get("TITLE_ID")
                    g["icon"] = save_asset(gid, "icon", d.file("PS3_GAME/ICON0.PNG"))
                    g["hero"] = save_asset(gid, "hero", d.file("PS3_GAME/PIC1.PNG"))
            finally:
                d.close()
    except Exception as e:
        print("lecture impossible", path, e, file=sys.stderr)
    g["launch"] = str(path)
    return g


def pkg_content_id(path):
    """Content ID d'un paquet PSN (en clair dans l'en-tête), ex. UP9000-NPUA80145_00-RATCHET550000001."""
    with open(path, "rb") as f:
        h = f.read(0x60)
    return h[0x30:0x60].split(b"\0")[0].decode("ascii", "replace") if h[:4] == b"\x7fPKG" else None


def rpcs3_root():
    return EMU / "rpcs3" if IS_WIN else HOME / ".var/app/net.rpcs3.RPCS3/config/rpcs3"


def scan_psn_folder(g, path):
    """Jeu PSN PS3 : dossier roms/ps3/<Jeu>/ contenant le(s) .pkg (jeu, clé de déblocage…) et les licences
    .rap. Installé dans RPCS3 au premier lancement (ps3_prepare) ; titre et images lus ensuite dans le jeu installé."""
    pkgs = sorted(path.glob("*.pkg"), key=lambda p: -p.stat().st_size)
    if not pkgs:
        return None
    cid = pkg_content_id(pkgs[0])
    if not cid or len(cid) < 16:
        return None
    g["serial"], g["content_id"] = cid[7:16], cid
    inst = rpcs3_root() / "dev_hdd0" / "game" / g["serial"]
    g["launch"] = str(path)
    if (inst / "PARAM.SFO").exists():
        sfo = parse_sfo((inst / "PARAM.SFO").read_bytes())
        g["title"] = sfo.get("TITLE") or g["title"]
        for kind, fn in (("icon", "ICON0.PNG"), ("hero", "PIC1.PNG")):
            if (inst / fn).exists():
                g[kind] = save_asset(g["id"], kind, (inst / fn).read_bytes())
    return g


def ps3_cli(args):
    """Commande RPCS3 sans fenêtre (installation du firmware ou d'un paquet)."""
    if IS_WIN:
        exe = resolve_exe(str(EMU / "rpcs3" / "rpcs3.exe"))
        return [str(exe), "--headless", *args] if exe else None
    return ["flatpak", "run", "--user", "net.rpcs3.RPCS3", "--headless", *args]


def ps3_prepare(cmd, g):
    """Jeu PSN : firmware installé si besoin, paquets installés et licences .rap copiées, puis lancement
    de l'EBOOT installé."""
    root, folder = rpcs3_root(), Path(g["launch"])
    eboot = root / "dev_hdd0" / "game" / g["serial"] / "USRDIR" / "EBOOT.BIN"
    run = lambda args, t: subprocess.run(ps3_cli(args), cwd=str(root) if IS_WIN else None, capture_output=True,
                                         timeout=t, creationflags=NO_WINDOW)
    if not ps3_cli([]):
        return False, "Émulateur non installé"
    if not (root / "dev_flash" / "vsh" / "module").is_dir():
        pup = (BASE if IS_WIN else HOME / "Emulation") / "bios" / "ps3" / "PS3UPDAT.PUP"
        if not pup.exists():
            return False, "Firmware PS3 manquant (bios/ps3/PS3UPDAT.PUP)"
        run(["--installfw", str(pup)], 900)
    if not eboot.exists():
        for pkg in sorted(folder.glob("*.pkg"), key=lambda p: -p.stat().st_size):   # le jeu, puis les clés
            run(["--installpkg", str(pkg)], 3600)
        if not eboot.exists():
            return False, "Installation du paquet PSN impossible"
    exdata = root / "dev_hdd0" / "home" / "00000001" / "exdata"
    for rap in folder.glob("*.rap"):
        exdata.mkdir(parents=True, exist_ok=True)
        if not (exdata / rap.name).exists():
            shutil.copy2(rap, exdata / rap.name)
    cmd[:] = [str(eboot) if c == g["launch"] else c for c in cmd]
    return True, "ok"


def ps3_disc_updates(g):
    """Jeu disque en dossier : les mises à jour posées dans son dossier (« Jeu (Update v1.01).pkg ») sont
    installées une fois dans RPCS3, qui les applique ensuite au lancement du disque."""
    folder = Path(g["path"])
    pkgs = sorted(folder.glob("*.pkg")) if folder.is_dir() else []
    if not pkgs or not ps3_cli([]):
        return
    root = rpcs3_root()
    done_f = root / ".formula-pkgs"
    done = set(done_f.read_text(encoding="utf-8").splitlines()) if done_f.exists() else set()
    sfo = root / "dev_hdd0" / "game" / str(g.get("serial")) / "PARAM.SFO"
    for pkg in pkgs:   # ordre des noms = ordre des versions (v1.01, v1.02…), certaines exigent la précédente
        key = f"{g.get('serial')}/{pkg.name}"
        if key in done:
            continue
        before = sfo.stat().st_mtime if sfo.exists() else None
        subprocess.run(ps3_cli(["--installpkg", str(pkg)]), cwd=str(root) if IS_WIN else None,
                       capture_output=True, timeout=3600, creationflags=NO_WINDOW)
        if not sfo.exists() or sfo.stat().st_mtime == before:
            break      # refusée (ex. version précédente manquante) : retentée au prochain lancement
        done.add(key)
        done_f.write_text("\n".join(sorted(done)), encoding="utf-8")


def scan_folder(sysid, path):
    """Jeux PS3 (PS3_GAME/...) et PS4 (sce_sys/...) décompressés en dossier."""
    gid = game_id(path)
    g = {"system": sysid, "path": str(path), "id": gid, "title": clean_name(path.name), "serial": None, "region": None}
    if sysid == "ps3":
        base = path / "PS3_GAME" if (path / "PS3_GAME").is_dir() else path
        sfo_p, eboot = base / "PARAM.SFO", base / "USRDIR" / "EBOOT.BIN"
        if not sfo_p.exists():
            return scan_psn_folder(g, path)
        sfo = parse_sfo(sfo_p.read_bytes())
        g["serial"] = sfo.get("TITLE_ID")
        g["launch"] = str(eboot if eboot.exists() else path)
        for kind, fn in (("icon", "ICON0.PNG"), ("hero", "PIC1.PNG")):
            if (base / fn).exists():
                g[kind] = save_asset(gid, kind, (base / fn).read_bytes())
    elif sysid == "psvita":
        sfo_p = path / "sce_sys" / "param.sfo"
        if not sfo_p.exists() or not (path / "eboot.bin").exists():
            return None
        sfo = parse_sfo(sfo_p.read_bytes())
        g["serial"] = sfo.get("TITLE_ID")
        g["launch"] = str(path)
        for kind, rel in (("icon", "icon0.png"), ("hero", "pic0.png"), ("hero", "livearea/contents/bg.png")):
            if not g.get(kind) and (path / "sce_sys" / rel).exists():
                g[kind] = save_asset(gid, kind, (path / "sce_sys" / rel).read_bytes())
    elif sysid == "ps4":
        sfo_p = path / "sce_sys" / "param.sfo"
        eboot = path / "eboot.bin"
        if not eboot.exists():
            return None
        sfo = parse_sfo(sfo_p.read_bytes()) if sfo_p.exists() else {}
        g["serial"] = sfo.get("TITLE_ID") or (re.search(r"CUSA\d{5}", path.name) or [None])[0]
        g["launch"] = str(eboot)
        for kind, fn in (("icon", "icon0.png"), ("hero", "pic1.png"), ("hero", "pic0.png")):
            if not g.get(kind) and (path / "sce_sys" / fn).exists():
                g[kind] = save_asset(gid, kind, (path / "sce_sys" / fn).read_bytes())
    else:
        return None
    g["title"] = sfo.get("TITLE") or g["title"]
    return g


class Library:
    def __init__(self):
        self.lock = threading.Lock()
        self.games = {}
        self.scanning = False
        try:
            self.games = json.loads(LIB_FILE.read_text())
        except Exception:
            pass

    def save(self):
        DATA.mkdir(parents=True, exist_ok=True)
        tmp = LIB_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.games, ensure_ascii=False, indent=1))
        tmp.replace(LIB_FILE)

    def candidates(self):
        for sysid, s in SYSTEMS.items():
            root = ROMS / sysid
            if not root.is_dir():
                continue
            exts = set(s.get("exts", []))
            for p in sorted(root.iterdir()):
                if p.name.startswith("."):
                    continue
                if p.is_file() and p.suffix.lower() in exts:
                    if sysid == "psvita" and "(update" in p.name.lower():
                        continue   # mise à jour d'un .pkg Vita, installée avec le jeu (vita_prepare)
                    yield sysid, p, "file"
                elif p.is_dir():
                    if re.search(r"-(UPDATE|patch)$", p.name, re.I) or p.name == "pkg":
                        continue  # mises à jour PS4 (chargées par shadPS4 avec le jeu) et paquets à installer
                    if s.get("folders"):
                        yield sysid, p, "folder"
                    else:  # un niveau de sous-dossier (ex. "Jeu [SLUS-xxxxx]/jeu.iso")
                        for q in sorted(p.iterdir()):
                            if q.is_file() and q.suffix.lower() in exts:
                                yield sysid, q, "file"

    def scan(self):
        if self.scanning:
            return
        self.scanning = True
        try:
            seen = {}
            for sysid, p, kind in self.candidates():
                try:
                    st = p.stat()
                except OSError:
                    continue
                gid = game_id(p)
                old = self.games.get(gid)
                pending_art = old and old.get("content_id") and not old.get("icon")   # .pkg Vita installé depuis ?
                if old and old.get("mtime") == st.st_mtime and old.get("size") == st.st_size and not pending_art:
                    seen[gid] = old
                    continue
                g = scan_file(sysid, p) if kind == "file" else scan_folder(sysid, p)
                if not g:
                    continue
                g.update(mtime=st.st_mtime, size=st.st_size, added=old.get("added") if old else time.time())
                if old:
                    for k in ("cover", "cover_tried", "plays", "last_played", "fav"):
                        if k in old:
                            g.setdefault(k, old[k])
                seen[gid] = g
                with self.lock:
                    self.games[gid] = g
            with self.lock:
                self.games = seen
                self.save()
            optimize_library(self)
            fetch_covers(self)
        finally:
            self.scanning = False


# ---------------------------------------------------------------- jaquettes

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            return None
        return r.read()


def norm(s):
    s = re.sub(r"[\[(][^\])]*[\])]", "", s.lower()).replace("&", " and ")
    s = re.sub(r"\bthe\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


_lr_index = {}


def libretro_index(system):
    if system in _lr_index:
        return _lr_index[system]
    cache = DATA / f"libretro_{norm(system)}.json"
    names = None
    if cache.exists() and time.time() - cache.stat().st_mtime < 14 * 86400:
        names = json.loads(cache.read_text())
    else:
        try:
            raw = http_get(f"https://thumbnails.libretro.com/{urllib.parse.quote(system)}/Named_Boxarts/", 40)
            hrefs = re.findall(r'href="([^"]+\.png)"', (raw or b"").decode("utf-8", "replace"))
            names = sorted({html.unescape(urllib.parse.unquote(h))[:-4] for h in hrefs})
            cache.write_text(json.dumps(names))
        except Exception as e:
            print("index libretro indisponible", system, e, file=sys.stderr)
            names = []
    idx = {}
    for n in names:
        idx.setdefault(norm(n), []).append(n)
    _lr_index[system] = idx
    return idx


def libretro_cover(system, title, region_hint=None):
    cands = libretro_index(system).get(norm(title))
    if not cands:
        return None
    pref = ["France", "Europe", "World", "USA", "Japan"]
    if region_hint == "NTSC-U":
        pref = ["USA", "World", "Europe", "France", "Japan"]
    cands.sort(key=lambda n: next((i for i, r in enumerate(pref) if f"({r}" in n or f", {r}" in n), 99))
    url = f"https://thumbnails.libretro.com/{urllib.parse.quote(system)}/Named_Boxarts/{urllib.parse.quote(cands[0])}.png"
    return http_get(url), ".png"


_repo_index = {}


def repo_cover(repo, title, region_hint=None):
    """Jaquette dans un dépôt GitHub public (fichiers nommés comme No-Intro), index mis en cache 14 jours."""
    name, branch, prefix = repo
    if name not in _repo_index:
        cache = DATA / f"repo_{norm(name)}.json"
        files = None
        if cache.exists() and time.time() - cache.stat().st_mtime < 14 * 86400:
            files = json.loads(cache.read_text())
        else:
            try:
                # ~370 Ko en clair : demandé compressé (la lecture non compressée se coupait en route)
                req = urllib.request.Request(f"https://api.github.com/repos/{name}/git/trees/{branch}?recursive=1",
                                             headers={**UA, "Accept-Encoding": "gzip"})
                with urllib.request.urlopen(req, timeout=40) as r:
                    raw = r.read()
                    if r.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                tree = json.loads(raw or b"{}")
                files = sorted(t["path"] for t in tree.get("tree", [])
                               if t.get("type") == "blob" and t["path"].startswith(prefix)
                               and t["path"].lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
                if files:
                    cache.write_text(json.dumps(files))
            except Exception as e:
                print("index de jaquettes indisponible", name, e, file=sys.stderr)
                files = []
        idx = {}
        for f in files or []:
            idx.setdefault(norm(Path(f).stem), []).append(f)
        _repo_index[name] = idx
    cands = list(_repo_index[name].get(norm(title)) or [])
    if not cands:
        return None
    pref = ["France", "Europe", "World", "USA", "Japan"]
    if region_hint == "NTSC-U":
        pref = ["USA", "World", "Europe", "France", "Japan"]
    cands.sort(key=lambda n: next((i for i, r in enumerate(pref) if f"({r}" in n or f", {r}" in n), 99))
    url = f"https://raw.githubusercontent.com/{name}/{branch}/{urllib.parse.quote(cands[0])}"
    return http_get(url, 40), Path(cands[0]).suffix.lower()


def xboxunity_cover(title_id):
    """Xbox 360 : jaquette par identifiant de titre sur XboxUnity (libretro n'en a qu'une douzaine).
    Les images sont des jaquettes complètes (dos, tranche, face) : on garde la face, à droite."""
    info = json.loads(http_get(f"https://xboxunity.net/Resources/Lib/CoverInfo.php?titleid={title_id}") or b"{}")
    covers = sorted(info.get("Covers") or [], key=lambda c: (c.get("Official") != "1", -int(c.get("Rating") or 0)))
    if not covers:
        return None
    data = http_get(f"https://xboxunity.net/Resources/Lib/Cover.php?size=large&cid={int(covers[0]['CoverID'])}", 40)
    if not data:
        return None
    COVERS.mkdir(parents=True, exist_ok=True)
    src, dst = COVERS / f"x360_{title_id}_full.jpg", COVERS / f"x360_{title_id}_front.png"
    src.write_bytes(data)
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                        "-vf", "crop=trunc(iw*0.469):ih:iw-trunc(iw*0.469):0", str(dst)],
                       check=True, timeout=60, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        return dst.read_bytes(), ".png"
    except Exception as e:
        print("recadrage impossible", title_id, e, file=sys.stderr)
        return data, ".jpg"
    finally:
        src.unlink(missing_ok=True)
        dst.unlink(missing_ok=True)


def find_cover(g):
    sysid, serial = g["system"], g.get("serial")
    tries = []
    if sysid == "ps2" and serial:
        tries.append(lambda: (http_get(f"https://raw.githubusercontent.com/xlenore/ps2-covers/main/covers/default/{serial}.jpg"), ".jpg"))
    if sysid == "ps3" and serial:
        tries.append(lambda: (http_get(f"https://raw.githubusercontent.com/aldostools/Resources/main/COV/{serial}.JPG"), ".jpg"))
    if SYSTEMS.get(sysid, {}).get("gametdb") and serial:
        # GameTDB : jaquettes officielles par ID de disque, en français si elles existent
        for reg in ("FR", "EN", "US", "JA"):
            tries.append(lambda reg=reg: (http_get(f"https://art.gametdb.com/wii/cover/{reg}/{serial}.png"), ".png"))
    if sysid == "x360" and serial:
        tries.append(lambda: xboxunity_cover(serial))
    stem = clean_name(Path(g["path"]).stem)
    names = [g["title"]] + ([stem] if norm(stem) != norm(g["title"]) else [])
    # le titre interne est parfois tronqué (« ACE COMBAT X ») : on retente avec le nom du fichier
    lr = SYSTEMS.get(sysid, {}).get("libretro")
    if lr:
        for n in names:
            tries.append(lambda n=n: libretro_cover(lr, n, g.get("region")))
    repo = SYSTEMS.get(sysid, {}).get("covers_repo")
    if repo:
        for n in names:
            tries.append(lambda n=n: repo_cover(repo, n, g.get("region")))
    by_id = SYSTEMS.get(sysid, {}).get("cover_by_id")
    if by_id and serial and re.fullmatch(r"[A-Z0-9]{4,12}", serial):
        tries.append(lambda: (http_get(by_id.format(serial=serial)), Path(by_id).suffix.lower()))
    for t in tries:
        try:
            res = t()
            if res and res[0] and len(res[0]) > 2000:
                return res
        except Exception:
            continue
    return None


def adopt_local_assets(lib):
    """Rattache les images déjà présentes dans covers/ (par ex. reçues de l'autre appareil) aux jeux."""
    files = {}
    for p in COVERS.iterdir() if COVERS.exists() else []:
        files.setdefault(p.stem, p.name)
    changed = False
    for gid, g in lib.games.items():
        for kind in ("cover", "hero", "icon"):
            name = files.get(f"{gid}_{kind}")
            if name and not g.get(kind):
                g[kind] = optimize_image(name, kind)
                changed = True
    if changed:
        with lib.lock:
            lib.save()


def fetch_covers(lib):
    adopt_local_assets(lib)
    for gid, g in list(lib.games.items()):
        # une jaquette introuvable est retentée à chaque démarrage (pas plus d'une fois par session)
        if g.get("cover") or g.get("cover_tried", 0) > STARTED:
            continue
        res = find_cover(g)
        with lib.lock:
            if res:
                g["cover"] = save_asset(gid, "cover", res[0], res[1])
            g["cover_tried"] = time.time()
            lib.save()


# ---------------------------------------------------------------- profils
#
# Jusqu'à 4 profils (écran « Qui joue ? » au démarrage). Chaque profil a ses propres sauvegardes, rangées
# dans kDrive (donc partagées entre le PC et le Deck) : kDrive/Saves/Profils/<profil>/<console>/…
# La liste des profils (nom, couleur, compte parent + code) est dans kDrive/Saves/Profils/profiles.json.
# Avant chaque lancement, FORMULA fait pointer les dossiers de sauvegarde de l'émulateur vers le profil
# actif : liens (jonctions sous Windows) ou chemins dans ses réglages, voir save_targets().
# Favoris, nombre de parties et dernière partie sont propres à chaque profil et à chaque appareil
# (formula-data/profiles/<id>.json), car les identifiants de jeux diffèrent d'un appareil à l'autre.
# Rien n'est jamais supprimé : un dossier réel trouvé à la place d'un lien est recopié puis mis de côté
# (<nom>.avant-profils-<date>), un profil supprimé part dans Profils/_supprimes.

SAVES_ROOT = HOME / "kDrive" / "Saves"
MAX_PROFILES = 4
PROFILE_COLORS = ["#8b6cff", "#22b8ff", "#2fbf71", "#ff8a3d"]
# dossiers par console dans kDrive/Saves (ceux d'avant les profils, recopiés dans le profil « P.A.D »)
CONSOLE_SAVE_DIRS = ["PS2", "PSP", "PSVita", "PS3", "PS4", "NES", "N64", "GBA", "DS", "GameCube", "Wii",
                     "Xbox", "Xbox 360"]
FIRST_PROFILE = "P.A.D"
XEMU_HDD = "https://github.com/xemu-project/xemu-hdd-image/releases/download/1.0/xbox_hdd.qcow2.zip"


def is_link(p):
    return p.is_symlink() or (IS_WIN and os.path.isjunction(p))


def link_target(p):
    try:
        t = os.readlink(p)
    except OSError:
        return None
    return os.path.normcase(os.path.normpath(t[4:] if t.startswith("\\\\?\\") else t))


def make_link(link, target):
    if IS_WIN:
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True,
                       capture_output=True, creationflags=NO_WINDOW)
    else:
        link.symlink_to(target)


def copy_missing(src, dst):
    """Recopie src dans dst sans rien écraser (fichiers absents seulement), dates conservées."""
    n = 0
    for root, dirs, files in os.walk(src):
        rel = Path(root).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in files:
            d = dst / rel / f
            if not d.exists():
                shutil.copy2(Path(root) / f, d)
                n += 1
    return n


def sha1_file(p):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def point_link(link, target):
    """Fait de « link » (dossier de l'émulateur) un lien vers « target » (dossier du profil)."""
    link, target = Path(link), Path(target)
    target.mkdir(parents=True, exist_ok=True)
    if is_link(link):
        if link_target(link) == os.path.normcase(os.path.normpath(str(target))):
            return
        os.rmdir(link) if IS_WIN else link.unlink()      # retire le lien seul, jamais son contenu
    elif link.is_dir():
        if any(link.iterdir()):
            # vrai dossier (émulateur réinstallé…) : contenu recopié dans le profil puis mis de côté
            copy_missing(link, target)
            link.rename(link.with_name(link.name + ".avant-profils-" + time.strftime("%Y%m%d-%H%M%S")))
        else:
            link.rmdir()
    link.parent.mkdir(parents=True, exist_ok=True)
    make_link(link, target)


def save_targets(sysid):
    """Où chaque émulateur range ses sauvegardes : ("link", dossier de l'émulateur, sous-dossier du profil)
    ou ("ini", fichier, section, {clé: (sous-dossier, format)}, séparateur)."""
    q2 = lambda p: f'"{p.as_posix()}"'
    q1 = lambda p: f"'{p}'"
    raw = str
    if IS_WIN:
        dol = EMU / "dolphin" / "Dolphin-x64" / "User"
        mgba = sorted(EMU.glob("mgba/*/mGBA.exe"))
        t = {
            "ps2": [("ini", EMU / "pcsx2/inis/PCSX2.ini", "Folders",
                     {"MemoryCards": ("PS2/memcards", raw), "Savestates": ("PS2/sstates", raw)}, " = ")],
            "psp": [("link", EMU / "ppsspp/memstick/PSP/SAVEDATA", "PSP/SAVEDATA"),
                    ("link", EMU / "ppsspp/memstick/PSP/PPSSPP_STATE", "PSP/PPSSPP_STATE")],
            "ps3": [("link", EMU / "rpcs3/dev_hdd0/home/00000001/savedata", "PS3/savedata")],
            "ps4": [("link", EMU / "shadps4/user/savedata", "PS4/savedata")],
            "psvita": [("link", EMU / "vita3k/portable/fs/ux0/user/00/savedata", "PSVita")],
            "gba": [("ini", mgba[-1].parent / "config.ini", "ports.qt",
                     {"savegamePath": ("GBA/saves", raw), "savestatePath": ("GBA/states", raw)}, "=")] if mgba else [],
            "nds": [("ini", EMU / "melonds/melonDS.toml", "Instance0",
                     {"SaveFilePath": ("DS/saves", q2), "SavestatePath": ("DS/states", q2)}, " = ")],
            "gc": [("link", dol / "GC", "GameCube"), ("link", dol / "Wii", "Wii")],
            "n64": [("ini", EMU / "rmg/Config/mupen64plus.cfg", "Rosalie's Mupen GUI Core",
                     {"SaveSRAMPath": ("N64/Game", q2), "SaveStatePath": ("N64/State", q2)}, " = ")],
            "xbox": [("ini", EMU / "xemu/xemu.toml", "sys.files",
                      {"eeprom_path": ("Xbox/eeprom.bin", q1), "hdd_path": ("Xbox/xbox_hdd.qcow2", q1)}, " = ")],
            "x360": [("link", EMU / "xenia/content", "Xbox 360")],
        }
    else:
        v = HOME / ".var" / "app"
        dol = v / "org.DolphinEmu.dolphin-emu/data/dolphin-emu"
        t = {
            "ps2": [("ini", v / "net.pcsx2.PCSX2/config/PCSX2/inis/PCSX2.ini", "Folders",
                     {"MemoryCards": ("PS2/memcards", raw), "Savestates": ("PS2/sstates", raw)}, " = ")],
            "psp": [("link", v / "org.ppsspp.PPSSPP/config/ppsspp/PSP/SAVEDATA", "PSP/SAVEDATA"),
                    ("link", v / "org.ppsspp.PPSSPP/config/ppsspp/PSP/PPSSPP_STATE", "PSP/PPSSPP_STATE")],
            "ps3": [("link", v / "net.rpcs3.RPCS3/config/rpcs3/dev_hdd0/home/00000001/savedata", "PS3/savedata")],
            "ps4": [("link", HOME / "Emulation/ps4/user/savedata", "PS4/savedata")],
            "psvita": [("link", HOME / "Emulation/psvita/portable/fs/ux0/user/00/savedata", "PSVita")],
            "gba": [("ini", v / "io.mgba.mGBA/config/mgba/config.ini", "ports.qt",
                     {"savegamePath": ("GBA/saves", raw), "savestatePath": ("GBA/states", raw)}, "=")],
            "nds": [("ini", v / "net.kuribo64.melonDS/config/melonDS/melonDS.toml", "Instance0",
                     {"SaveFilePath": ("DS/saves", q2), "SavestatePath": ("DS/states", q2)}, " = ")],
            "gc": [("link", dol / "GC", "GameCube"), ("link", dol / "Wii", "Wii")],
            # RMG range Game/ et State/ dans data/RMG/Save (chemins de ses réglages)
            "n64": [("link", v / "com.github.Rosalie241.RMG/data/RMG/Save", "N64")],
            "nes": [("link", v / "ca._0ldsk00l.Nestopia/data/nestopia/save", "NES/save"),
                    ("link", v / "ca._0ldsk00l.Nestopia/data/nestopia/state", "NES/state")],
            "xbox": [("ini", v / "app.xemu.xemu/data/xemu/xemu/xemu.toml", "sys.files",
                      {"eeprom_path": ("Xbox/eeprom.bin", q1), "hdd_path": ("Xbox/xbox_hdd.qcow2", q1)}, " = ")],
            # Xbox 360 (Deck) : --content_root sur la ligne de commande, voir Runner.launch
        }
    t["wii"] = t.get("gc", [])          # même Dolphin pour GameCube et Wii
    return t.get(sysid, [])


def flatpak_id(cmd):
    if cmd and cmd[0] == "flatpak":
        return next((c for c in cmd[2:] if not c.startswith("-")), None)
    return None


def write_settings(s):
    DATA.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


class Profiles:
    def __init__(self):
        self.lock = threading.RLock()
        self.current = None          # profil choisi sur l'écran « Qui joue ? » (aucun au démarrage)
        self.fails = {}              # id -> (erreurs de code de suite, bloqué jusqu'à)
        self.root = SAVES_ROOT / "Profils" if SAVES_ROOT.exists() else DATA / "profils"
        self.file = self.root / "profiles.json"
        self.local = DATA / "profiles"

    # ---- liste partagée (kDrive)
    def load(self):
        try:
            d = json.loads(self.file.read_text(encoding="utf-8"))
            return d if isinstance(d.get("profiles"), list) else {"profiles": []}
        except Exception:
            return {"profiles": []}

    def save(self, d):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.file)

    def get(self, pid):
        return next((p for p in self.load()["profiles"] if p["id"] == pid), None)

    def public(self):
        out = [{k: p.get(k) for k in ("id", "name", "color", "parent")} for p in self.load()["profiles"]]
        cur = self.current if any(p["id"] == self.current for p in out) else None
        return {"profiles": out, "current": cur, "last": load_settings().get("profile"),
                "max": MAX_PROFILES, "parents": any(p["parent"] for p in out)}

    # ---- code parent (4 chiffres, jamais stocké en clair)
    @staticmethod
    def hash_pin(pin, salt=None):
        salt = salt or secrets.token_hex(16)
        h = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 200_000).hex()
        return {"salt": salt, "hash": h}

    @staticmethod
    def valid_pin(pin):
        return isinstance(pin, str) and re.fullmatch(r"\d{4}", pin) is not None

    def check_pin(self, p, pin):
        """Vrai si le code est bon ; 5 erreurs de suite bloquent le profil 30 s."""
        n, until = self.fails.get(p["id"], (0, 0))
        if time.time() < until:
            return False
        ok = bool(self.valid_pin(pin) and p.get("pin") and
                  hmac.compare_digest(self.hash_pin(pin, p["pin"]["salt"])["hash"], p["pin"]["hash"]))
        if ok:
            self.fails.pop(p["id"], None)
        else:
            n += 1
            self.fails[p["id"]] = (0, time.time() + 30) if n >= 5 else (n, 0)
        return ok

    def manager_ok(self, pin):
        """Ajouter / modifier / supprimer un profil : code d'un compte parent, dès qu'il en existe un."""
        parents = [p for p in self.load()["profiles"] if p.get("parent")]
        return not parents or any(self.check_pin(p, pin) for p in parents)

    # ---- actions
    def select(self, pid, pin=None):
        p = self.get(pid)
        if not p:
            return False, "unknown"
        if p.get("parent") and not self.check_pin(p, pin):
            return False, "pin"
        self.current = pid
        s = load_settings()
        s["profile"] = pid
        write_settings(s)
        return True, "ok"

    def dir_name(self, name, d):
        base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "Profil"
        used = {p["dir"].lower() for p in d["profiles"]} | {"_supprimes"}
        n, out = 1, base
        while out.lower() in used or (self.root / out).exists() and n < 50:
            n += 1
            out = f"{base} {n}"
        return out

    def create(self, name, parent=False, pin=None, pid=None, reuse_dir=False):
        with self.lock:
            d = self.load()
            name = str(name or "").strip()[:20]
            if not name:
                return False, "name"
            if len(d["profiles"]) >= MAX_PROFILES:
                return False, "full"
            if parent and not self.valid_pin(pin):
                return False, "pin"
            used = {p["color"] for p in d["profiles"]}
            folder = name if reuse_dir else self.dir_name(name, d)
            p = {"id": pid or secrets.token_hex(4), "name": name, "dir": folder,
                 "color": next((c for c in PROFILE_COLORS if c not in used), PROFILE_COLORS[0]),
                 "parent": bool(parent), "pin": self.hash_pin(pin) if parent else None, "created": int(time.time())}
            d["profiles"].append(p)
            (self.root / p["dir"]).mkdir(parents=True, exist_ok=True)
            self.save(d)
            return True, p["id"]

    def update(self, pid, name=None, parent=None, pin=None):
        with self.lock:
            d = self.load()
            p = next((x for x in d["profiles"] if x["id"] == pid), None)
            if not p:
                return False, "unknown"
            if name is not None:
                name = str(name).strip()[:20]
                if not name:
                    return False, "name"
                p["name"] = name       # le dossier garde son nom : les sauvegardes ne bougent pas
            if parent is True:
                if pin is not None and not self.valid_pin(pin):
                    return False, "pin"
                if pin is None and not p.get("pin"):
                    return False, "pin"
                p["parent"] = True
                if pin is not None:
                    p["pin"] = self.hash_pin(pin)
            elif parent is False:
                p["parent"], p["pin"] = False, None
            self.save(d)
            return True, "ok"

    def delete(self, pid):
        with self.lock:
            d = self.load()
            p = next((x for x in d["profiles"] if x["id"] == pid), None)
            if not p:
                return False, "unknown"
            if len(d["profiles"]) <= 1:
                return False, "last"
            src = self.root / p["dir"]
            if src.exists():
                dst = self.root / "_supprimes" / f'{p["dir"]}-{time.strftime("%Y%m%d-%H%M%S")}'
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))     # sauvegardes mises de côté, pas effacées
            d["profiles"].remove(p)
            self.save(d)
            if self.current == pid:
                self.current = None
            return True, "ok"

    # ---- sauvegardes
    def saves_dir(self, pid=None):
        p = self.get(pid or self.current) or (self.load()["profiles"] or [None])[0]
        return self.root / p["dir"] if p else SAVES_ROOT

    def apply(self, sysid, cmd=None):
        """Fait pointer les sauvegardes de l'émulateur de cette console vers le profil actif."""
        base = self.saves_dir()
        for t in save_targets(sysid):
            if t[0] == "link":
                point_link(t[1], base / t[2])
            elif t[1].exists():
                vals = {}
                for k, (sub, fmt) in t[3].items():
                    target = base / sub
                    (target.parent if target.suffix else target).mkdir(parents=True, exist_ok=True)
                    vals[k] = fmt(target)
                ini_update(t[1], t[2], vals, t[4])
        if sysid == "xbox":
            self.xbox_hdd(base / "Xbox" / "xbox_hdd.qcow2")
        app = flatpak_id(cmd)
        if app:
            self.flatpak_access(app)
        return base

    @staticmethod
    def xbox_hdd(hdd):
        """Nouveau profil : disque dur Xbox vierge publié par le projet xemu (sans contenu Microsoft)."""
        if hdd.exists():
            return
        import io
        import zipfile
        hdd.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(io.BytesIO(http_get(XEMU_HDD, timeout=120))) as z:
                tmp = hdd.with_suffix(".part")
                tmp.write_bytes(z.read("xbox_hdd.qcow2"))
                os.replace(tmp, hdd)
        except Exception as e:
            print("disque Xbox vierge indisponible :", e, flush=True)

    def flatpak_access(self, app):
        """Deck : un flatpak n'a accès qu'aux dossiers déclarés ; on lui ouvre Profils/ (une seule fois)."""
        f = HOME / ".local/share/flatpak/overrides" / app
        try:
            if str(self.root) in f.read_text(encoding="utf-8"):
                return
        except OSError:
            pass
        subprocess.run(["flatpak", "override", "--user", f"--filesystem={self.root}", app], capture_output=True)

    # ---- favoris et parties, par profil (sur cet appareil)
    def stats_file(self, pid):
        return self.local / f"{pid}.json"

    def stats(self, pid=None):
        pid = pid or self.current
        if not pid:
            return {}
        try:
            return json.loads(self.stats_file(pid).read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_stats(self, data, pid=None):
        pid = pid or self.current
        self.local.mkdir(parents=True, exist_ok=True)
        tmp = self.stats_file(pid).with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.stats_file(pid))

    def bump(self, gid, played=False, fav=None):
        if not self.current:
            return {}
        with self.lock:
            s = self.stats()
            g = s.setdefault(gid, {})
            if played:
                g["plays"] = g.get("plays", 0) + 1
                g["last_played"] = time.time()
            if fav is not None:
                g["fav"] = fav
            self.save_stats(s)
            return g

    # ---- migration : tout ce qui existait avant les profils va dans « P.A.D »
    def migrate(self, lib):
        marker = DATA / "profiles-migrated.json"
        if marker.exists():
            return
        with self.lock:
            d = self.load()
            p = next((x for x in d["profiles"] if x["id"] == "pad"), None)
            if not p:
                # créé sur l'autre appareil puis synchronisé par kDrive, ou à créer ici
                ok, _ = self.create(FIRST_PROFILE, pid="pad", reuse_dir=True)
                p = self.get("pad")
            dst = self.root / p["dir"]
            report = {"profile": p["id"], "at": time.time(), "copied": {}, "mismatch": []}
            for name in CONSOLE_SAVE_DIRS:
                src = SAVES_ROOT / name
                if src.is_dir() and not is_link(src):
                    report["copied"][name] = copy_missing(src, dst / name)
                    # vérification : chaque fichier d'origine doit se retrouver à l'identique dans le profil
                    for root, _, files in os.walk(src):
                        for f in files:
                            a = Path(root) / f
                            b = dst / name / a.relative_to(src)
                            if not b.exists() or sha1_file(a) != sha1_file(b):
                                report["mismatch"].append(str(a))   # version déjà présente gardée
            with lib.lock:
                stats = {gid: {k: g[k] for k in ("fav", "plays", "last_played") if g.get(k)}
                         for gid, g in lib.games.items() if g.get("fav") or g.get("plays") or g.get("last_played")}
            if stats and not self.stats_file(p["id"]).exists():
                self.save_stats(stats, p["id"])
            DATA.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
            print("profils : données recopiées dans", dst, report["copied"], flush=True)


PROFILES = Profiles()


# ---------------------------------------------------------------- lancement

class Runner:
    def __init__(self):
        self.proc = None
        self.game = None

    def running(self):
        if self.proc and self.proc.poll() is None:
            return self.game
        self.proc = self.game = None
        return None

    def launch(self, lib, gid):
        if self.running():
            return False, "Un jeu est déjà lancé"
        g = lib.games.get(gid)
        if not g:
            return False, "Jeu introuvable"
        if not PROFILES.current:
            return False, "Choisis d'abord un profil"
        s = SYSTEMS[g["system"]]
        cmd = [c.replace("{path}", g["launch"]) for c in s["cmd"]]
        cwd = s.get("cwd")
        dbg = debug_game(g) if g["system"] == "ps2" else None
        if dbg:
            # jeu inscrit dans debug-games.json : ancien PCSX2 (voir PCSX2_DEBUG)
            if not pcsx2_debug_exe().exists():
                return False, "Émulateur non installé"
            pcsx2_debug_configure(dbg.get("renderer", "software"))
            cmd, cwd, extra_env = pcsx2_debug_cmd(g["launch"])
            s = dict(s, env=dict(s.get("env", {}), **extra_env))
        elif IS_WIN:
            exe = resolve_exe(cmd[0])
            if not exe:
                return False, "Émulateur non installé"
            cmd[0], cwd = str(exe), str(exe.parent)
        elif not EMUS.installed(EMUS.for_system(g["system"])):
            return False, "Émulateur non installé"
        # sauvegardes de l'émulateur -> dossier du profil actif
        try:
            saves = PROFILES.apply(g["system"], cmd)
        except Exception as e:
            return False, f"Sauvegardes du profil inaccessibles : {e}"
        cmd = [("--content_root=" + str(saves / "Xbox 360")) if c.startswith("--content_root=") else c for c in cmd]
        if g["system"] == "psvita":
            extra = {}
            ok, msg = vita_prepare(cmd, g, extra)
            if not ok:
                return False, msg
            s = dict(s, env=dict(s.get("env", {}), **extra))
        if g["system"] == "ps3" and g.get("content_id"):
            ok, msg = ps3_prepare(cmd, g)
            if not ok:
                return False, msg
        elif g["system"] == "ps3":
            ps3_disc_updates(g)
        # Fenêtres X11 (XWayland) : en mode Bureau, Steam ne reconnaît pas une fenêtre Wayland native
        # comme le jeu en cours et applique alors la config manette « Bureau » (souris/clavier).
        env = dict(os.environ, **s.get("env", {}))
        log = open(DATA / "last_launch.log", "w")
        self.proc = subprocess.Popen(cmd, cwd=cwd or str(HOME), env=env,
                                     stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     creationflags=NO_WINDOW)
        self.game = gid
        PROFILES.bump(gid, played=True)
        return True, "ok"


# ---------------------------------------------------------------- manette

def win_browser_in_front():
    """Windows : vrai si la fenêtre au premier plan est celle de FORMULA (FORMULA.exe, ou Edge en secours)."""
    import ctypes
    from ctypes import wintypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = u32.GetForegroundWindow()
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = k32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return True
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return True
        return Path(buf.value).name.lower() in ("formula.exe", "msedge.exe")
    finally:
        k32.CloseHandle(h)


# ---------------------------------------------------------------- manette

class PadReader:
    """Lit la manette virtuelle de Steam directement (evdev, côté hôte) et transmet
    les appuis à l'interface. Le navigateur n'est pas fiable pour ça (sandbox flatpak,
    focus sous gamescope).

    Priorité des entrées :
      - un jeu tourne        -> la manette est au jeu, FORMULA ignore tout ;
      - menu Steam ouvert    -> Steam Input coupe la manette virtuelle, rien n'arrive ici ;
      - sinon                -> FORMULA.
    Au retour d'un jeu, les boutons encore enfoncés sont ignorés jusqu'à leur relâchement
    (le « A » qui valide « Quitter » dans l'émulateur ne relance pas un jeu).
    """
    KEYS = {0x130: "a", 0x131: "b", 0x133: "x", 0x134: "y", 0x136: "lb", 0x137: "rb",
            0x13A: "select", 0x13B: "start", 0x13D: "l3", 0x13E: "r3", 0x9E: "select",
            0x220: "up", 0x221: "down", 0x222: "left", 0x223: "right"}
    EVT = struct.Struct("llHHi")

    def __init__(self, runner):
        self.runner = runner
        self.fds = {}            # chemin -> fd
        self.absr = {}           # fd -> {axe: (centre, demi-plage)} lus via EVIOCGABS
        self.held = set()        # boutons logiques enfoncés (sources confondues)
        self.src = {}            # (source, bouton) -> bool, pour combiner croix et stick
        self.muted = set()       # enfoncés pendant le jeu : ignorés jusqu'au relâchement
        self.was_running = False
        self.resume_at = 0.0
        self.clients = []
        self.lock = threading.Lock()

    def subscribe(self):
        import queue
        q = queue.Queue(maxsize=200)
        with self.lock:
            self.clients.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def emit(self, msg):
        with self.lock:
            for q in self.clients:
                try:
                    q.put_nowait(msg)
                except Exception:
                    pass

    def rescan(self):
        try:
            blocks = Path("/proc/bus/input/devices").read_text().split("\n\n")
        except OSError:
            return
        want = set()
        for b in blocks:
            h = re.search(r"^H: Handlers=(.*)$", b, re.M)
            if h and re.search(r"\bjs\d+", h.group(1)):
                ev = re.search(r"\bevent\d+", h.group(1))
                if ev:
                    want.add("/dev/input/" + ev.group(0))
        for p in list(self.fds):
            if p not in want:
                fd = self.fds.pop(p)
                self.absr.pop(fd, None)
                for (s, n) in [k for k in self.src if isinstance(k[0], tuple) and k[0][1] == fd]:
                    self.set_src(s, n, False)
                os.close(fd)
        for p in want - set(self.fds):
            try:
                fd = self.fds[p] = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
                self.absr[fd] = self.axis_ranges(fd)
            except OSError:
                pass

    def set_src(self, source, name, on):
        self.src[(source, name)] = on
        new = any(v for (s, n), v in self.src.items() if n == name)
        old = name in self.held
        if new == old:
            return
        if new:
            self.held.add(name)
        else:
            self.held.discard(name)
            if name in self.muted:
                self.muted.discard(name)
                return
        running = self.runner.running()
        if running or time.time() < self.resume_at:
            if new:
                self.muted.add(name)
            return
        if name in self.muted:
            return
        if IS_WIN and new and not win_browser_in_front():
            return  # une autre fenêtre est au premier plan : elle garde la manette
        self.emit({"b": name, "v": 1 if new else 0})

    @staticmethod
    def axis_ranges(fd):
        """Plage des axes X/Y du stick gauche. La manette virtuelle de Steam va de -32767 à
        32767, mais une manette Xbox en Bluetooth vue en direct va de 0 à 65535 (centre 32768) :
        sans normalisation, son stick paraît toujours poussé en bas à droite."""
        out = {}
        try:
            import fcntl
            for code in (0, 1):
                buf = bytearray(24)
                fcntl.ioctl(fd, 0x80184540 + code, buf)  # EVIOCGABS(code)
                _, lo, hi, _, _, _ = struct.unpack("6i", buf)
                if hi > lo:
                    out[code] = ((lo + hi) / 2, (hi - lo) / 2)
        except (OSError, ImportError):
            pass
        return out

    def handle(self, etype, code, value, fd=None):
        # une source par périphérique : la même manette peut apparaître deux fois
        # (en direct et via Steam), leurs états ne doivent pas s'écraser
        if etype == 1 and code in self.KEYS:
            self.set_src(("btn", fd), self.KEYS[code], value != 0)
        elif etype == 3 and code in (0x10, 0x11):      # croix (hat)
            neg, pos = ("left", "right") if code == 0x10 else ("up", "down")
            self.set_src(("hat", fd), neg, value < 0)
            self.set_src(("hat", fd), pos, value > 0)
        elif etype == 3 and code in (0, 1):            # stick gauche, avec hystérésis
            mid, half = self.absr.get(fd, {}).get(code, (0, 32767))
            value = (value - mid) * 32767 / half
            neg, pos = ("left", "right") if code == 0 else ("up", "down")
            for name, on in ((neg, value < 0), (pos, value > 0)):
                cur = self.src.get((("stick", fd), name), False)
                mag = abs(value)
                self.set_src(("stick", fd), name, on and (mag > 9000 if cur else mag > 16000))

    def check_resume(self):
        running = bool(self.runner.running())
        if self.was_running and not running:
            self.resume_at = time.time() + 0.8
            self.muted |= self.held
            self.emit({"t": "resume"})
        self.was_running = running

    # Windows : XInput (manette virtuelle Steam ou manette Xbox), lu même sans le focus
    XI_BUTTONS = {0x0001: "up", 0x0002: "down", 0x0004: "left", 0x0008: "right", 0x0010: "start",
                  0x0020: "select", 0x0040: "l3", 0x0080: "r3", 0x0100: "lb", 0x0200: "rb", 0x1000: "a", 0x2000: "b", 0x4000: "x", 0x8000: "y"}

    def loop_xinput(self):
        import ctypes

        class XState(ctypes.Structure):
            _fields_ = [("packet", ctypes.c_uint32), ("buttons", ctypes.c_uint16), ("lt", ctypes.c_ubyte),
                        ("rt", ctypes.c_ubyte), ("lx", ctypes.c_short), ("ly", ctypes.c_short),
                        ("rx", ctypes.c_short), ("ry", ctypes.c_short)]
        xi = None
        for dll in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
            try:
                xi = ctypes.windll.LoadLibrary(dll)
                break
            except OSError:
                continue
        if not xi:
            print("XInput introuvable : manette désactivée dans FORMULA", file=sys.stderr)
            return
        st = XState()
        self.fds = {"xinput": 0}   # signale à l'interface qu'une manette est lue côté serveur
        while True:
            self.check_resume()
            buttons, lx, ly, lt, rt = 0, 0, 0, 0, 0
            for user in range(4):
                if xi.XInputGetState(user, ctypes.byref(st)) == 0:
                    buttons |= st.buttons
                    lt, rt = max(lt, st.lt), max(rt, st.rt)
                    lx = lx if abs(lx) > abs(st.lx) else st.lx
                    ly = ly if abs(ly) > abs(st.ly) else st.ly
            for bit, name in self.XI_BUTTONS.items():
                self.set_src("btn", name, bool(buttons & bit))
            # gâchettes (taille des jaquettes), avec hystérésis
            for name, val in (("lt", lt), ("rt", rt)):
                cur = self.src.get(("btn", name), False)
                self.set_src("btn", name, val > 60 if cur else val > 120)
            # stick gauche (axe Y XInput : positif = haut)
            for name, val, sign in (("left", lx, -1), ("right", lx, 1), ("up", ly, 1), ("down", ly, -1)):
                cur = self.src.get(("stick", name), False)
                v = val * sign
                self.set_src("stick", name, v > 9000 if cur else v > 16000)
            time.sleep(0.016)

    def loop(self):
        if IS_WIN:
            return self.loop_xinput()
        import select
        last_scan = 0
        while True:
            now = time.time()
            running = bool(self.runner.running())
            if self.was_running and not running:
                self.resume_at = now + 0.8
                self.muted |= self.held
                self.emit({"t": "resume"})
            self.was_running = running
            if now - last_scan > 2:
                self.rescan()
                last_scan = now
            if not self.fds:
                time.sleep(0.5)
                continue
            try:
                r, _, _ = select.select(list(self.fds.values()), [], [], 0.25)
            except (OSError, ValueError):
                self.rescan()
                continue
            for fd in r:
                try:
                    data = os.read(fd, self.EVT.size * 64)
                except OSError:
                    continue
                for i in range(0, len(data) - self.EVT.size + 1, self.EVT.size):
                    _, _, etype, code, value = self.EVT.unpack_from(data, i)
                    self.handle(etype, code, value, fd)


# ---------------------------------------------------------------- émulateurs (Paramètres)
#
# Liste des émulateurs gérés : installés ou non, version, taille, installation de la dernière
# version et désinstallation. Deck : flatpaks utilisateur (+ AppImage pour shadPS4) ; les réglages
# (~/.var/app) et les sauvegardes (kDrive) sont conservés à la désinstallation.
# Windows : versions portables dans <BASE>/emulators ; les jonctions vers kDrive sont retirées
# avant suppression pour ne jamais toucher aux sauvegardes.

EMULATORS = [
    {"id": "pcsx2", "name": "PCSX2", "systems": ["ps2"], "flatpak": "net.pcsx2.PCSX2",
     "win": {"dir": "pcsx2", "exe": "pcsx2-qt.exe", "repo": "PCSX2/pcsx2", "asset": r"windows-x64-Qt\.7z$"}},
    {"id": "ppsspp", "name": "PPSSPP", "systems": ["psp"], "flatpak": "org.ppsspp.PPSSPP",
     "win": {"dir": "ppsspp", "exe": "PPSSPPWindows64.exe", "repo": "hrydgard/ppsspp", "asset": r"Windows-x64\.zip$"}},
    {"id": "rpcs3", "name": "RPCS3", "systems": ["ps3"], "flatpak": "net.rpcs3.RPCS3",
     "win": {"dir": "rpcs3", "exe": "rpcs3.exe", "repo": "RPCS3/rpcs3-binaries-win", "asset": r"win64.*\.7z$"}},
    {"id": "shadps4", "name": "shadPS4", "systems": ["ps4"],
     "appimage": {"repo": "shadps4-emu/shadPS4", "asset": r"linux-sdl.*\.zip$", "file": "Shadps4-sdl.AppImage"},
     "win": {"dir": "shadps4", "exe": "shadPS4.exe", "repo": "shadps4-emu/shadPS4", "asset": r"win64-sdl.*\.zip$"}},
    {"id": "nestopia", "name": "Nestopia", "systems": ["nes"], "flatpak": "ca._0ldsk00l.Nestopia",
     "win": {"dir": "nestopia", "exe": "nestopia.exe", "repo": "0ldsk00l/nestopia", "asset": r"windows-x86_64\.zip$"}},
    {"id": "rmg", "name": "RMG", "systems": ["n64"], "flatpak": "com.github.Rosalie241.RMG",
     "win": {"dir": "rmg", "exe": "RMG.exe", "repo": "Rosalie241/RMG", "asset": r"Portable-Windows64.*\.zip$"}},
    {"id": "mgba", "name": "mGBA", "systems": ["gba"], "flatpak": "io.mgba.mGBA",
     "win": {"dir": "mgba", "exe": "*/mGBA.exe", "repo": "mgba-emu/mgba", "asset": r"win64\.7z$"}},
    {"id": "melonds", "name": "melonDS", "systems": ["nds"], "flatpak": "net.kuribo64.melonDS",
     "win": {"dir": "melonds", "exe": "melonDS.exe", "repo": "melonDS-emu/melonDS", "asset": r"windows-x86_64\.zip$"}},
    # Dolphin ne publie pas ses binaires Windows sur GitHub : version fixée
    {"id": "dolphin", "name": "Dolphin", "systems": ["gc", "wii"], "flatpak": "org.DolphinEmu.dolphin-emu",
     "win": {"dir": "dolphin", "exe": "Dolphin-x64/Dolphin.exe", "version": "2609a",
             "url": "https://dl.dolphin-emu.org/releases/2609a/dolphin-2609a-x64.7z"}},
    {"id": "xemu", "name": "xemu", "systems": ["xbox"], "flatpak": "app.xemu.xemu",
     "win": {"dir": "xemu", "exe": "xemu.exe", "repo": "xemu-project/xemu", "asset": r"^xemu-[\d.]+-windows-x86_64\.zip$"}},
    # Xenia Canary : versions nommées par commit ; AppImage officielle sous Linux
    # Vita3K : publié en continu (pas de numéro de version, la date de la version sert de repère)
    {"id": "vita3k", "name": "Vita3K", "systems": ["psvita"],
     "appimage": {"repo": "Vita3K/Vita3K", "asset": r"^Vita3K-x86_64\.AppImage$", "file": "Vita3K-x86_64.AppImage",
                  "dir": "psvita"},
     "win": {"dir": "vita3k", "exe": "Vita3K.exe", "repo": "Vita3K/Vita3K", "asset": r"^windows-latest\.zip$"}},
    {"id": "xenia", "name": "Xenia Canary", "systems": ["x360"],
     "appimage": {"repo": "xenia-canary/xenia-canary", "asset": r"linux\.AppImage$", "file": "xenia_canary.AppImage",
                  "dir": "x360"},
     "win": {"dir": "xenia", "exe": "xenia_canary.exe", "repo": "xenia-canary/xenia-canary", "asset": r"windows\.7z$"}},
]
FLATPAK_APPS = HOME / ".local/share/flatpak/app"


# ---------------------------------------------------------------- PS Vita (Vita3K)
# Mode portable : un dossier « portable » à côté de l'exécutable (Windows) ou de l'AppImage (Deck)
# contient tout (firmware installé, jeux installés, réglages). Les sauvegardes vont dans kDrive.
# Le firmware officiel (PSVUPDAT.PUP + PSP2UPDAT.PUP, gratuits chez Sony) se place dans bios/psvita ;
# FORMULA l'installe dans Vita3K automatiquement, sans fenêtre, avant le premier jeu.

def vita_root():
    return EMU / "vita3k" if IS_WIN else HOME / "Emulation" / "psvita"


def vita_bios():
    return (BASE if IS_WIN else HOME / "Emulation") / "bios" / "psvita"


def vita_configure(portable):
    """Réglages de base (ajoutés seulement s'ils manquent) et sauvegardes dans kDrive."""
    portable.mkdir(parents=True, exist_ok=True)
    cfg = portable / "config.yml"
    lines = cfg.read_text(encoding="utf-8").splitlines() if cfg.exists() else []
    keys = {l.split(":", 1)[0].strip() for l in lines if ":" in l and not l.startswith((" ", "#"))}
    wanted = {"sys-lang": "2",                 # français
              "sys-button": "1",               # croix pour valider
              "initial-setup": "true", "show-welcome": "false", "check-for-updates": "false",
              "discord-rich-presence": "false"}
    lines += [f"{k}: {v}" for k, v in wanted.items() if k not in keys]
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # sauvegardes (ux0/user/00/savedata) : lien vers le profil actif, posé par Profiles.apply au lancement


def vita_license(fs, g):
    """Licence d'un .pkg : déjà ajoutée dans Vita3K (ux0/license/<ID>/<content_id>.rif), ou posée à côté
    du paquet (<nom>.rif ou <nom>.work.bin). Celle posée à côté est recopiée dans Vita3K."""
    tid, cid = g.get("serial"), g.get("content_id") or ""
    lic = fs / "ux0" / "license" / tid
    if cid and (lic / f"{cid}.rif").exists():
        return (lic / f"{cid}.rif").read_bytes()
    pkg = Path(g["launch"])
    for cand in (pkg.with_suffix(".rif"), pkg.with_suffix(".work.bin")):
        if not cand.exists():
            continue
        data = cand.read_bytes()
        if len(data) in (512, 1024) and (not cid or cid.encode() in data[:0x60]):
            lic.mkdir(parents=True, exist_ok=True)
            (lic / f"{cid or tid}.rif").write_bytes(data)
            return data
    return None


def vita_prepare(cmd, g, env=None):
    """Complète la commande Vita3K : firmware installé si besoin, puis lancement direct du jeu
    (déjà installé : par son identifiant ; sinon installation puis lancement)."""
    exe = cmd[0]
    portable = Path(exe).parent / "portable"
    vita_configure(portable)
    fs = portable / "fs"
    quiet_env = {**os.environ, "DISABLE_AUTO_UPDATES": "1"}   # pas de fenêtre de mise à jour de l'AppImage
    if not (fs / "vs0").is_dir():
        pups = sorted(vita_bios().glob("*.PUP")) if vita_bios().is_dir() else []
        main = [p for p in pups if p.name.upper() == "PSVUPDAT.PUP"]
        if not main:
            return False, "Firmware PS Vita manquant (bios/psvita/PSVUPDAT.PUP)"
        for pup in main + [p for p in pups if p not in main]:
            subprocess.run([exe, "--firmware", str(pup)], cwd=str(Path(exe).parent), capture_output=True,
                           timeout=600, creationflags=NO_WINDOW, env=quiet_env)
    tid = g.get("serial")
    if g["launch"].lower().endswith(".pkg") and tid and not (fs / "ux0" / "app" / tid / "eboot.bin").exists():
        rif = vita_license(fs, g)
        if not rif:
            return False, f"Licence manquante pour {g.get('content_id') or tid} (fichier .rif ou work.bin)"
        subprocess.run([exe, "--pkg", g["launch"], "--zrif", rif_to_zrif(rif)], cwd=str(Path(exe).parent),
                       capture_output=True, timeout=3600, creationflags=NO_WINDOW, env=quiet_env)
        if not (fs / "ux0" / "app" / tid / "eboot.bin").exists():
            return False, "Installation du paquet impossible (la licence ne correspond peut-être pas au paquet)"
    if g["launch"].lower().endswith(".pkg") and tid and (fs / "ux0" / "app" / tid / "eboot.bin").exists():
        # mises à jour posées à côté : « Jeu (Update v1.04).pkg », installées une fois chacune
        pkg = Path(g["launch"])
        done_f = fs / "ux0" / "app" / tid / ".formula-updates"
        done = set(done_f.read_text(encoding="utf-8").splitlines()) if done_f.exists() else set()
        updates = sorted(p for p in pkg.parent.glob("*.pkg")
                         if p.name.startswith(pkg.stem + " (") and "(update" in p.name.lower() and p.name not in done)
        rif = vita_license(fs, g) if updates else None
        for upd in updates:
            if not rif:
                break
            subprocess.run([exe, "--pkg", str(upd), "--zrif", rif_to_zrif(rif)], cwd=str(Path(exe).parent),
                           capture_output=True, timeout=3600, creationflags=NO_WINDOW, env=quiet_env)
            done.add(upd.name)
            done_f.write_text("\n".join(sorted(done)), encoding="utf-8")
    if tid and (fs / "ux0" / "app" / tid / "eboot.bin").exists():
        cmd[1:] = ["--frontend", "sdl", "-F", "-r", tid]
    else:
        cmd[1:] = ["--frontend", "sdl", "-F", g["launch"]]
    if not IS_WIN and env is not None:
        runner = vita_appdir_runner(Path(exe))
        if runner:
            cmd[0] = str(runner)
            env.update(APPDIR=str(runner.parent), APPIMAGE=str(exe))   # APPIMAGE : dossier portable à côté
    return True, "ok"


def vita_appdir_runner(appimage):
    """Deck : l'AppImage de Vita3K range ses shaders dans share/Vita3K/shaders-builtin alors que Vita3K les
    cherche à côté de son exécutable (bin/) ; il envoie alors un shader vide au pilote, qui plante dès la
    première image. On lance donc une copie extraite de l'AppImage, avec un lien bin/shaders-builtin.
    Ré-extraite quand l'AppImage change (mise à jour depuis Paramètres)."""
    root = appimage.parent / "Vita3K-AppDir"
    st = appimage.stat()
    stamp = f"{st.st_size}:{int(st.st_mtime)}"
    marker = root / ".formula-source"
    if not (marker.exists() and marker.read_text().strip() == stamp and (root / "AppRun").exists()):
        tmp = appimage.parent / ".vita3k-extract"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        try:
            subprocess.run([str(appimage), "--appimage-extract"], cwd=str(tmp), capture_output=True, timeout=600,
                           env={**os.environ, "DISABLE_AUTO_UPDATES": "1"})
            src = next((d for d in tmp.iterdir() if (d / "AppRun").exists()), None)
            if not src:
                return None
            shutil.rmtree(root, ignore_errors=True)
            src.rename(root)
            marker.write_text(stamp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    link, shaders = root / "bin" / "shaders-builtin", root / "share" / "Vita3K" / "shaders-builtin"
    if not link.exists() and shaders.is_dir():
        link.symlink_to(Path("..") / "share" / "Vita3K" / "shaders-builtin")
    return root / "AppRun"


def app_dir(e):
    """Deck : dossier d'un émulateur distribué hors Flathub (AppImage), ~/Emulation/<dir>."""
    return HOME / "Emulation" / e["appimage"].get("dir", "ps4")


def dir_size(path):
    """Taille d'un dossier sans suivre les liens ni les jonctions (sauvegardes kDrive)."""
    total, stack = 0, [Path(path)]
    while stack:
        try:
            with os.scandir(stack.pop()) as it:
                for e in it:
                    try:
                        if e.is_symlink() or (IS_WIN and os.path.isjunction(e.path)):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        pass
        except OSError:
            pass
    return total


class EmuManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs = {}            # id -> {"state": "installing"|"uninstalling"|"error", "progress", "error"}
        self.cache = {}           # résultats coûteux (tailles, versions flatpak, disque)
        self.disk = None
        self.disk_at = 0

    def get(self, eid):
        return next((e for e in EMULATORS if e["id"] == eid), None)

    def for_system(self, sysid):
        return next((e for e in EMULATORS if sysid in e["systems"]), None)

    def root(self, e):
        if IS_WIN:
            return EMU / e["win"]["dir"]
        return app_dir(e) if "appimage" in e else FLATPAK_APPS / e["flatpak"]

    def installed(self, e):
        if not e:
            return True        # console sans émulateur géré ici
        if IS_WIN:
            return bool(list(self.root(e).glob(e["win"]["exe"])))
        if "appimage" in e:
            return (app_dir(e) / e["appimage"]["file"]).exists()
        return (FLATPAK_APPS / e["flatpak"] / "current").exists()

    def version(self, e):
        vf = self.root(e) / ".formula-version"
        if (IS_WIN or "appimage" in e) and vf.exists():
            return vf.read_text(encoding="utf-8").strip()
        if not IS_WIN and "flatpak" in e:
            if "flatpak_versions" not in self.cache:
                try:
                    out = subprocess.run(["flatpak", "list", "--user", "--app", "--columns=application,version"],
                                         capture_output=True, text=True, timeout=20).stdout
                    self.cache["flatpak_versions"] = dict(l.split("\t", 1) for l in out.splitlines() if "\t" in l)
                except Exception:
                    self.cache["flatpak_versions"] = {}
            return self.cache["flatpak_versions"].get(e["flatpak"], "").strip().lstrip("v") or "?"
        return e.get("win", {}).get("version", "?")

    def size(self, e):
        key = "size_" + e["id"]
        if key not in self.cache:
            if not IS_WIN and "appimage" in e:
                f = app_dir(e) / e["appimage"]["file"]
                self.cache[key] = f.stat().st_size if f.exists() else 0
            else:
                self.cache[key] = dir_size(self.root(e))
            if e["id"] == "pcsx2" and pcsx2_debug_dir().exists():   # PCSX2 debug compté avec le principal
                self.cache[key] += dir_size(pcsx2_debug_dir())
        return self.cache[key]

    def listing(self):
        out = []
        for e in EMULATORS:
            inst = self.installed(e)
            job = self.jobs.get(e["id"], {})
            out.append({"id": e["id"], "name": e["name"], "systems": e["systems"], "installed": inst,
                        "version": self.version(e) if inst else None, "size": self.size(e) if inst else 0,
                        "job": job.get("state"), "progress": job.get("progress"), "error": job.get("error")})
        return out

    # ---- disque (barre façon SteamOS)
    def disk_usage(self):
        """Renvoie le dernier calcul connu et relance le calcul en fond s'il date (il parcourt les jeux)."""
        if (not self.disk or time.time() - self.disk_at > 120) and not self.cache.get("disk_busy"):
            self.cache["disk_busy"] = True
            def work():
                try:
                    self._disk_compute()
                finally:
                    self.cache.pop("disk_busy", None)
            threading.Thread(target=work, daemon=True).start()
        return self.disk

    def _disk_compute(self):
        import shutil
        root = BASE if IS_WIN else HOME
        du = shutil.disk_usage(root)
        parts = [ROMS.parent if IS_WIN else HOME / "Emulation", DATA, APP_DIR]
        if not IS_WIN:
            parts += [FLATPAK_APPS / e["flatpak"] for e in EMULATORS if "flatpak" in e]
            parts += [HOME / ".var/app" / e["flatpak"] for e in EMULATORS if "flatpak" in e]
        saves = HOME / "kDrive" / "Saves"
        if saves.exists() and Path(saves.anchor) == Path(Path(root).anchor):
            parts += [saves / c for c in ("PS2", "PSP", "PS3", "PS4", "NES", "N64", "GBA", "DS", "GameCube", "Wii",
                                         "Xbox", "Xbox 360", "PSVita")]
        seen, formula = set(), 0
        for p in parts:
            p = Path(p)
            if p.exists() and str(p) not in seen:
                seen.add(str(p))
                formula += dir_size(p)
        formula = min(formula, du.used)
        self.disk = {"total": du.total, "free": du.free, "formula": formula, "other": du.used - formula,
                     "path": str(root)}
        self.disk_at = time.time()

    # ---- installation / désinstallation (en arrière-plan)
    def start(self, eid, action):
        e = self.get(eid)
        if not e or eid in self.jobs and self.jobs[eid].get("state") in ("installing", "uninstalling"):
            return False
        self.jobs[eid] = {"state": "installing" if action == "install" else "uninstalling", "progress": None}
        threading.Thread(target=self._run, args=(e, action), daemon=True).start()
        return True

    def _run(self, e, action):
        try:
            (self._install if action == "install" else self._uninstall)(e)
            if e["id"] == "pcsx2":     # le PCSX2 debug suit toujours le PCSX2 principal
                (self._install_pcsx2_debug if action == "install" else self._uninstall_pcsx2_debug)(e)
            self.jobs.pop(e["id"], None)
        except Exception as ex:
            self.jobs[e["id"]] = {"state": "error", "error": str(ex)}
        self.cache.clear()
        self.disk = None

    def _latest(self, repo, pattern):
        data = json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest", 30))
        for a in data.get("assets", []):
            if re.search(pattern, a["name"]):
                tag = data.get("tag_name", "?")
                if tag == "continuous":      # version publiée en continu : on retient sa date
                    tag = (data.get("published_at") or "?")[:10]
                return a["browser_download_url"], tag.lstrip("v.")
        raise OSError("aucune version téléchargeable trouvée")

    def _download(self, e, url, dest):
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    self.jobs[e["id"]]["progress"] = int(90 * done / total)

    def _install(self, e):
        if IS_WIN:
            w = e["win"]
            url, ver = (w["url"], w["version"]) if "url" in w else self._latest(w["repo"], w["asset"])
            dl = BASE / "_downloads"
            dl.mkdir(exist_ok=True)
            arc = dl / url.rsplit("/", 1)[-1]
            self._download(e, url, arc)
            target = self.root(e)
            target.mkdir(parents=True, exist_ok=True)
            subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", str(arc), "-C", str(target)], check=True,
                           creationflags=0x08000000)
            arc.unlink(missing_ok=True)
            (target / ".formula-version").write_text(ver, encoding="utf-8")
            setup = APP_DIR / "tools" / "setup_windows.py"
            fn = {"pcsx2": "pcsx2", "ppsspp": "ppsspp", "rpcs3": "rpcs3", "shadps4": "shadps4", "mgba": "mgba",
                  "melonds": "melonds", "dolphin": "dolphin", "rmg": "rmg", "xemu": "xemu", "xenia": "xenia"}.get(e["id"])
            if e["id"] == "vita3k":
                vita_configure(target / "portable")
            if setup.exists() and fn:
                import importlib.util
                spec = importlib.util.spec_from_file_location("setup_windows", setup)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                getattr(mod, fn)()
        elif "appimage" in e:
            a = e["appimage"]
            url, ver = self._latest(a["repo"], a["asset"])
            d = app_dir(e)
            d.mkdir(parents=True, exist_ok=True)
            if url.endswith(".AppImage"):          # AppImage publiée telle quelle (Xenia)
                self._download(e, url, d / a["file"])
            else:                                  # AppImage dans une archive zip (shadPS4)
                arc = d / "_download.zip"
                self._download(e, url, arc)
                import zipfile
                with zipfile.ZipFile(arc) as z:
                    name = next(n for n in z.namelist() if n.endswith(".AppImage"))
                    with z.open(name) as src, open(d / a["file"], "wb") as dst:
                        dst.write(src.read())
                arc.unlink()
            os.chmod(d / a["file"], 0o755)
            (d / ".formula-version").write_text(ver, encoding="utf-8")
            if e["id"] == "vita3k":
                vita_configure(d / "portable")
        else:
            subprocess.run(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", e["flatpak"]],
                           check=True, capture_output=True, timeout=3600)

    def _install_pcsx2_debug(self, e):
        d = pcsx2_debug_dir()
        d.mkdir(parents=True, exist_ok=True)
        if IS_WIN:
            arc = d / "_download.7z"
            self._download(e, PCSX2_DEBUG["win"]["url"], arc)
            subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", str(arc), "-C", str(d)], check=True,
                           creationflags=NO_WINDOW)
            arc.unlink(missing_ok=True)
        else:
            self._download(e, PCSX2_DEBUG["appimage"]["url"], pcsx2_debug_exe())
            os.chmod(pcsx2_debug_exe(), 0o755)
        (d / ".formula-version").write_text(PCSX2_DEBUG["version"], encoding="utf-8")
        pcsx2_debug_configure()

    def _uninstall_pcsx2_debug(self, e):
        import shutil
        # les cartes mémoire et sauvegardes rapides sont dans kDrive : rien à protéger ici
        shutil.rmtree(pcsx2_debug_dir(), ignore_errors=True)

    def _uninstall(self, e):
        if IS_WIN:
            import shutil
            target = self.root(e)
            for root, dirs, _ in os.walk(target):
                for d in list(dirs):
                    p = os.path.join(root, d)
                    if os.path.isjunction(p) or os.path.islink(p):
                        os.rmdir(p)          # retire le lien vers kDrive sans toucher aux sauvegardes
                        dirs.remove(d)
            shutil.rmtree(target)
        elif "appimage" in e:
            (app_dir(e) / e["appimage"]["file"]).unlink(missing_ok=True)
            (app_dir(e) / ".formula-version").unlink(missing_ok=True)
            shutil.rmtree(app_dir(e) / "Vita3K-AppDir", ignore_errors=True)   # copie extraite (vita_appdir_runner)
        else:
            subprocess.run(["flatpak", "uninstall", "--user", "-y", "--noninteractive", e["flatpak"]],
                           check=True, capture_output=True, timeout=600)


EMUS = EmuManager()


# ---------------------------------------------------------------- serveur HTTP

LIB = Library()
RUN = Runner()
PAD = PadReader(RUN)
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "application/javascript",
        ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".json": "application/json",
        ".woff2": "font/woff2"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def static(self, base, rel, cache=False):
        p = (base / rel).resolve()
        if base.resolve() not in p.parents or not p.is_file():
            return self.send(404, {"error": "not found"})
        self.send(200, p.read_bytes(), MIME.get(p.suffix.lower(), "application/octet-stream"), cache)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/library":
            stats = PROFILES.stats()          # favoris et parties du profil actif
            with LIB.lock:
                games = [{k: g.get(k) for k in ("id", "system", "title", "serial", "region", "cover", "icon",
                                                "hero", "added", "size")}
                         for g in LIB.games.values()]
            for g in games:
                st = stats.get(g["id"], {})
                g.update(plays=st.get("plays"), last_played=st.get("last_played"), fav=bool(st.get("fav")))
            systems = [{"id": k, "name": v["name"], "short": v["short"], "order": v.get("order", 99)}
                       for k, v in SYSTEMS.items()]
            return self.send(200, {"games": games, "systems": systems, "scanning": LIB.scanning,
                                   "running": RUN.running(), "version": VERSION, "platform": PLATFORM,
                                   "settings": load_settings(), "profile": PROFILES.current})
        if path == "/api/events":
            return self.events()
        if path == "/api/sync":
            return self.send(200, sync_status_for_ui())
        if path == "/api/emulators":
            return self.send(200, {"emulators": EMUS.listing(), "disk": EMUS.disk_usage()})
        if path == "/api/profiles":
            return self.send(200, PROFILES.public())
        if path.startswith("/covers/"):
            return self.static(COVERS, path[len("/covers/"):], cache=True)
        rel = path.lstrip("/") or "index.html"
        return self.static(WEB_DIR, rel)

    def events(self):
        """Flux SSE des appuis manette (voir PadReader)."""
        import queue
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        q = PAD.subscribe()
        try:
            self.wfile.write(b"data: " + json.dumps({"t": "hello", "pads": len(PAD.fds)}).encode() + b"\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=10)
                    self.wfile.write(b"data: " + json.dumps(msg).encode() + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            PAD.unsubscribe(q)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            body = {}
        if path == "/api/launch":
            ok, msg = RUN.launch(LIB, body.get("id"))
            return self.send(200 if ok else 409, {"ok": ok, "message": msg})
        if path == "/api/rescan":
            threading.Thread(target=LIB.scan, daemon=True).start()
            return self.send(200, {"ok": True})
        if path in ("/api/emulators/install", "/api/emulators/uninstall"):
            if RUN.running():
                return self.send(409, {"ok": False, "message": "game running"})
            ok = EMUS.start(body.get("id"), path.rsplit("/", 1)[-1])
            return self.send(200 if ok else 409, {"ok": ok})
        if path == "/api/settings":
            s = load_settings()
            if body.get("lang") in ("en", "fr"):
                s["lang"] = body["lang"]
            if isinstance(body.get("fullscreen"), bool):   # Windows : lu par FORMULA.exe au démarrage
                s["fullscreen"] = body["fullscreen"]
            write_settings(s)
            return self.send(200, s)
        if path == "/api/fav":
            gid = body.get("id")
            if gid not in LIB.games or not PROFILES.current:
                return self.send(409, {"ok": False})
            st = PROFILES.bump(gid, fav=not PROFILES.stats().get(gid, {}).get("fav"))
            return self.send(200, {"ok": True, "fav": bool(st.get("fav"))})
        if path.startswith("/api/profiles/"):
            return self.profiles(path.rsplit("/", 1)[-1], body)
        if path == "/api/quit":
            self.send(200, {"ok": True})
            def bye():
                time.sleep(0.3)
                os._exit(0)     # FORMULA.exe (Windows) / formula.sh (Deck) ferment la fenêtre en voyant le serveur s'arrêter
            threading.Thread(target=bye, daemon=True).start()
            return
        self.send(404, {"error": "not found"})

    def profiles(self, action, body):
        """Profils : choisir (code si compte parent), ajouter, modifier, supprimer. Dès qu'un compte parent
        existe, ajouter / modifier / supprimer demande le code d'un parent (« auth »)."""
        if RUN.running():
            return self.send(409, {"ok": False, "error": "running"})
        pid = body.get("id")
        if action == "select":
            ok, err = PROFILES.select(pid, body.get("pin"))
        elif action == "logout":
            PROFILES.current, ok, err = None, True, "ok"
        elif action == "auth":           # vérifie le code parent avant d'ouvrir la gestion des profils
            ok, err = PROFILES.manager_ok(body.get("auth")), "auth"
        elif action in ("create", "update", "delete"):
            if not PROFILES.manager_ok(body.get("auth")):
                return self.send(403, {"ok": False, "error": "auth"})
            if action == "create":
                ok, err = PROFILES.create(body.get("name"), bool(body.get("parent")), body.get("pin"))
            elif action == "update":
                parent = body.get("parent")
                ok, err = PROFILES.update(pid, body.get("name"), parent if isinstance(parent, bool) else None,
                                          body.get("pin"))
            else:
                ok, err = PROFILES.delete(pid)
        else:
            return self.send(404, {"error": "not found"})
        return self.send(200 if ok else 409, dict(PROFILES.public(), ok=ok, error=None if ok else err,
                                                  created=err if ok and action == "create" else None))


# ---------------------------------------------------------------- synchro entre appareils
#
# Chaque appareil fait tourner « formula.py --sync » en fond (service systemd sur le Deck,
# démarrage de session sur Windows). Ce service :
#   - publie la liste de ses jeux (roms/) et sert les fichiers aux autres appareils (jeton partagé),
#   - télécharge régulièrement les jeux présents chez l'autre et absents ici,
#   - garde en attente ce qui n'a pas pu être récupéré (appareil éteint) et réessaie plus tard.
# Un jeu supprimé volontairement ici n'est pas re-téléchargé (liste des suppressions).

SYNC_CFG = DATA / "sync.json"
SYNC_STATUS = DATA / "sync_status.json"
SYNC_KNOWN = DATA / "sync_known.json"
WIN_BAD = re.compile(r'[<>:"\\|?*]')
PART = ".formula-part"


def sync_key(rel):
    """Clé de comparaison commune aux deux systèmes (caractères interdits sous Windows remplacés)."""
    return "/".join(WIN_BAD.sub("-", p).rstrip(" .") for p in rel.split("/"))


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(p, data):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def local_manifest(settle=120):
    """Fichiers de roms/ (hors fichiers en cours d'écriture depuis moins de `settle` secondes)."""
    out, now = {}, time.time()
    for root, dirs, files in os.walk(ROMS):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if fn.startswith(".") or fn.endswith(PART):
                continue
            p = Path(root) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            if now - st.st_mtime < settle:
                continue
            rel = p.relative_to(ROMS).as_posix()
            out[sync_key(rel)] = {"rel": rel, "size": st.st_size, "mtime": int(st.st_mtime)}
    return out


def update_known(manifest):
    """Mémorise les jeux vus ici ; ceux qui disparaissent passent dans les suppressions."""
    k = load_json(SYNC_KNOWN, {"known": [], "deleted": []})
    known, deleted, cur = set(k["known"]), set(k["deleted"]), set(manifest)
    deleted = (deleted | (known - cur)) - cur
    save_json(SYNC_KNOWN, {"known": sorted(known | cur), "deleted": sorted(deleted)})
    return deleted


def sync_status_for_ui():
    st = load_json(SYNC_STATUS, {})
    if st and time.time() - st.get("updated", 0) > 900:
        st["state"] = "stopped"   # service de synchro arrêté
    return st


class SyncHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        import hmac
        import ipaddress
        cfg = load_json(SYNC_CFG, {})
        token = cfg.get("token") or ""
        try:
            ip = ipaddress.ip_address(self.client_address[0])
            local = ip.is_private or ip.is_loopback
        except ValueError:
            local = False
        # réseau local uniquement, et jeton partagé obligatoire (refus si aucun jeton n'est configuré)
        if not local or len(token) < 16 or not hmac.compare_digest(self.headers.get("X-Formula-Token", ""), token):
            self.send_response(403)
            self.end_headers()
            return
        u = urllib.parse.urlparse(self.path)
        if u.path == "/manifest":
            body = json.dumps({"device": cfg.get("device"), "files": local_manifest(),
                               "deleted": load_json(SYNC_KNOWN, {}).get("deleted", [])}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/covers":
            # jaquettes connues ici, par jeu (chemin relatif à roms/)
            out = {}
            for g in load_json(LIB_FILE, {}).values():
                try:
                    rel = Path(g["path"]).relative_to(ROMS).as_posix()
                except (KeyError, ValueError):
                    continue
                assets = {k: g.get(k) for k in ("cover", "hero", "icon") if g.get(k)}
                if assets:
                    out[sync_key(rel)] = assets
            body = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/cover":
            name = Path(urllib.parse.parse_qs(u.query).get("name", [""])[0]).name   # nom de fichier seul
            p = COVERS / name
            if not name or not p.is_file():
                self.send_response(404)
                self.end_headers()
                return
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if u.path == "/file":
            rel = urllib.parse.parse_qs(u.query).get("rel", [""])[0]
            p = (ROMS / rel).resolve()
            if ROMS.resolve() not in p.parents or not p.is_file():
                self.send_response(404)
                self.end_headers()
                return
            size = p.stat().st_size
            start = 0
            m = re.match(r"bytes=(\d+)-", self.headers.get("Range", ""))
            if m:
                start = min(int(m.group(1)), size)
            self.send_response(206 if start else 200)
            self.send_header("Content-Length", str(size - start))
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            try:
                with open(p, "rb") as f:
                    f.seek(start)
                    while chunk := f.read(1 << 20):
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            return
        self.send_response(404)
        self.end_headers()


class Syncer:
    def __init__(self):
        self.cfg = load_json(SYNC_CFG, {})
        self.status = {"state": "starting", "device": self.cfg.get("device"), "peers": {}}

    def publish(self, **kw):
        self.status.update(kw, updated=time.time())
        save_json(SYNC_STATUS, self.status)

    def peer_get(self, peer, path, timeout=5, headers=None):
        h = {"X-Formula-Token": self.cfg.get("token", ""), **(headers or {})}
        req = urllib.request.Request(f"http://{peer}{path}", headers=h)
        return urllib.request.urlopen(req, timeout=timeout)

    def download(self, peer, item, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + PART)
        have = part.stat().st_size if part.exists() else 0
        hdr = {"Range": f"bytes={have}-"} if have else {}
        with self.peer_get(peer, "/file?rel=" + urllib.parse.quote(item["rel"]), timeout=30, headers=hdr) as r:
            if have and r.status != 206:
                have = 0
            with open(part, "ab" if have else "wb") as f:
                done, last = have, 0
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if time.time() - last > 2:
                        self.publish(current=item["rel"], current_done=done, current_size=item["size"])
                        last = time.time()
        if part.stat().st_size != item["size"]:
            raise OSError("taille inattendue, nouvel essai plus tard")
        os.utime(part, (item["mtime"], item["mtime"]))
        part.replace(dest)

    def sync_peer(self, peer):
        cache = DATA / f"sync_peer_{re.sub(r'[^0-9A-Za-z]', '_', peer)}.json"
        local = local_manifest(settle=0)
        deleted = update_known(local)
        try:
            with self.peer_get(peer, "/manifest") as r:
                remote = json.loads(r.read())
            save_json(cache, remote)
            online = True
        except Exception:
            remote = load_json(cache, {"files": {}})
            online = False
        # absents ici, ou présents mais différents et plus récents chez l'autre (copie incomplète remplacée)
        todo = [v for k, v in remote.get("files", {}).items() if k not in deleted and (
            k not in local or (local[k]["size"] != v["size"] and v["mtime"] > local[k]["mtime"]))]
        name = remote.get("device") or peer
        info = {"name": name, "online": online, "pending": len(todo),
                "pending_bytes": sum(v["size"] for v in todo), "checked": time.time()}
        self.status["peers"][peer] = info
        self.publish(state="syncing" if (online and todo) else "idle")
        if not online:
            return 0
        got = 0
        for item in sorted(todo, key=lambda v: v["size"]):
            dest = ROMS / sync_key(item["rel"]) if IS_WIN else ROMS / item["rel"]
            try:
                self.publish(current=item["rel"], current_done=0, current_size=item["size"])
                self.download(peer, item, dest)
                got += 1
                info["pending"] -= 1
                info["pending_bytes"] -= item["size"]
            except Exception as e:
                info["online"] = False
                info["error"] = str(e)
                break
        self.publish(state="idle", current=None)
        return got

    def sync_covers(self, peer):
        """Récupère chez l'autre appareil les jaquettes déjà téléchargées et compressées, pour les jeux
        présents ici qui n'en ont pas encore (évite de tout re-télécharger depuis Internet)."""
        with self.peer_get(peer, "/covers", timeout=10) as r:
            remote = json.loads(r.read())
        COVERS.mkdir(parents=True, exist_ok=True)
        have = {p.stem for p in COVERS.iterdir()}
        got = 0
        for key, assets in remote.items():
            local = ROMS / (sync_key(key) if IS_WIN else key)
            if not local.exists():
                continue
            gid = game_id(local)
            for kind, name in assets.items():
                if not name or f"{gid}_{kind}" in have:
                    continue
                try:
                    with self.peer_get(peer, "/cover?name=" + urllib.parse.quote(name), timeout=20) as r:
                        data = r.read()
                    (COVERS / f"{gid}_{kind}{Path(name).suffix}").write_bytes(data)
                    have.add(f"{gid}_{kind}")
                    got += 1
                except Exception:
                    continue
        return 1 if got else 0

    def run(self):
        DATA.mkdir(parents=True, exist_ok=True)
        if len(self.cfg.get("token") or "") < 16 or not self.cfg.get("peers"):
            print("synchro non configurée (sync.json) : rien n'est ouvert sur le réseau", file=sys.stderr)
            return
        srv = ThreadingHTTPServer(("0.0.0.0", SYNC_PORT), SyncHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        while True:
            self.cfg = load_json(SYNC_CFG, {})
            got = 0
            # un appareil = une liste d'adresses possibles (IP, nom réseau) essayées dans l'ordre
            for addrs in self.cfg.get("peers", []):
                addrs = [addrs] if isinstance(addrs, str) else addrs
                for i, peer in enumerate(addrs):
                    try:
                        got += self.sync_peer(peer)
                        if self.status["peers"].get(peer, {}).get("online"):
                            got += self.sync_covers(peer)
                    except Exception as e:
                        print("synchro", peer, e, file=sys.stderr)
                    if self.status["peers"].get(peer, {}).get("online") or i == len(addrs) - 1:
                        for other in addrs:  # n'affiche que l'adresse retenue
                            if other != peer:
                                self.status["peers"].pop(other, None)
                        break
            if got:  # prévient l'interface si elle est ouverte
                try:
                    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/api/rescan",
                                                                  data=b"{}", method="POST"), timeout=3)
                except Exception:
                    pass
            self.publish()
            time.sleep(300 if not got else 5)


def watch_host(pid):
    """Windows : arrête le serveur si la fenêtre FORMULA.exe qui l'a lancé disparaît (plantage, fin de tâche)."""
    import ctypes
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
    if h:
        k32.WaitForSingleObject(h, 0xFFFFFFFF)
    os._exit(0)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    COVERS.mkdir(parents=True, exist_ok=True)
    if "--sync" in sys.argv:
        return Syncer().run()
    if "--window" in sys.argv:
        # ancien mode (raccourcis d'avant la 0.4) : la fenêtre est maintenant FORMULA.exe, qui lance le serveur
        exe = BASE / "FORMULA.exe"
        if not exe.exists():
            sys.exit(f"{exe} introuvable : lancer tools\\install_windows.py")
        return subprocess.run([str(exe)]).returncode
    if "--host" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--host") + 1])
        threading.Thread(target=watch_host, args=(pid,), daemon=True).start()
    try:
        PROFILES.migrate(LIB)      # une seule fois par appareil : données d'avant les profils -> « P.A.D »
    except Exception as e:
        print("profils : migration impossible :", e, flush=True)
    threading.Thread(target=LIB.scan, daemon=True).start()
    threading.Thread(target=PAD.loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"FORMULA sur http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
