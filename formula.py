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
import hashlib
import html
import json
import os
import re
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
    return out


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


def scan_folder(sysid, path):
    """Jeux PS3 (PS3_GAME/...) et PS4 (sce_sys/...) décompressés en dossier."""
    gid = game_id(path)
    g = {"system": sysid, "path": str(path), "id": gid, "title": clean_name(path.name), "serial": None, "region": None}
    if sysid == "ps3":
        base = path / "PS3_GAME" if (path / "PS3_GAME").is_dir() else path
        sfo_p, eboot = base / "PARAM.SFO", base / "USRDIR" / "EBOOT.BIN"
        if not sfo_p.exists():
            return None
        sfo = parse_sfo(sfo_p.read_bytes())
        g["serial"] = sfo.get("TITLE_ID")
        g["launch"] = str(eboot if eboot.exists() else path)
        for kind, fn in (("icon", "ICON0.PNG"), ("hero", "PIC1.PNG")):
            if (base / fn).exists():
                g[kind] = save_asset(gid, kind, (base / fn).read_bytes())
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
                if old and old.get("mtime") == st.st_mtime and old.get("size") == st.st_size:
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
    lr = SYSTEMS.get(sysid, {}).get("libretro")
    if lr:
        tries.append(lambda: libretro_cover(lr, g["title"], g.get("region")))
        # le titre interne est parfois tronqué (« ACE COMBAT X ») : on retente avec le nom du fichier
        stem = clean_name(Path(g["path"]).stem)
        if norm(stem) != norm(g["title"]):
            tries.append(lambda: libretro_cover(lr, stem, g.get("region")))
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
        s = SYSTEMS[g["system"]]
        cmd = [c.replace("{path}", g["launch"]) for c in s["cmd"]]
        cwd = s.get("cwd")
        if IS_WIN:
            exe = resolve_exe(cmd[0])
            if not exe:
                return False, "Émulateur non installé"
            cmd[0], cwd = str(exe), str(exe.parent)
        elif not EMUS.installed(EMUS.for_system(g["system"])):
            return False, "Émulateur non installé"
        # Fenêtres X11 (XWayland) : en mode Bureau, Steam ne reconnaît pas une fenêtre Wayland native
        # comme le jeu en cours et applique alors la config manette « Bureau » (souris/clavier).
        env = dict(os.environ, **s.get("env", {}))
        log = open(DATA / "last_launch.log", "w")
        self.proc = subprocess.Popen(cmd, cwd=cwd or str(HOME), env=env,
                                     stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                     creationflags=NO_WINDOW)
        self.game = gid
        with lib.lock:
            g["plays"] = g.get("plays", 0) + 1
            g["last_played"] = time.time()
            lib.save()
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
            0x13A: "select", 0x13B: "start", 0x220: "up", 0x221: "down", 0x222: "left", 0x223: "right"}
    EVT = struct.Struct("llHHi")

    def __init__(self, runner):
        self.runner = runner
        self.fds = {}            # chemin -> fd
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
                os.close(self.fds.pop(p))
        for p in want - set(self.fds):
            try:
                self.fds[p] = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
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

    def handle(self, etype, code, value):
        if etype == 1 and code in self.KEYS:
            self.set_src("btn", self.KEYS[code], value != 0)
        elif etype == 3 and code in (0x10, 0x11):      # croix (hat)
            neg, pos = ("left", "right") if code == 0x10 else ("up", "down")
            self.set_src("hat", neg, value < 0)
            self.set_src("hat", pos, value > 0)
        elif etype == 3 and code in (0, 1):            # stick gauche, avec hystérésis
            neg, pos = ("left", "right") if code == 0 else ("up", "down")
            for name, on in ((neg, value < 0), (pos, value > 0)):
                cur = self.src.get(("stick", name), False)
                mag = abs(value)
                self.set_src("stick", name, on and (mag > 9000 if cur else mag > 16000))

    def check_resume(self):
        running = bool(self.runner.running())
        if self.was_running and not running:
            self.resume_at = time.time() + 0.8
            self.muted |= self.held
            self.emit({"t": "resume"})
        self.was_running = running

    # Windows : XInput (manette virtuelle Steam ou manette Xbox), lu même sans le focus
    XI_BUTTONS = {0x0001: "up", 0x0002: "down", 0x0004: "left", 0x0008: "right", 0x0010: "start",
                  0x0020: "select", 0x0100: "lb", 0x0200: "rb", 0x1000: "a", 0x2000: "b", 0x4000: "x", 0x8000: "y"}

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
                    self.handle(etype, code, value)


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
    {"id": "xenia", "name": "Xenia Canary", "systems": ["x360"],
     "appimage": {"repo": "xenia-canary/xenia-canary", "asset": r"linux\.AppImage$", "file": "xenia_canary.AppImage",
                  "dir": "x360"},
     "win": {"dir": "xenia", "exe": "xenia_canary.exe", "repo": "xenia-canary/xenia-canary", "asset": r"windows\.7z$"}},
]
FLATPAK_APPS = HOME / ".local/share/flatpak/app"


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
                                         "Xbox", "Xbox 360")]
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
            self.jobs.pop(e["id"], None)
        except Exception as ex:
            self.jobs[e["id"]] = {"state": "error", "error": str(ex)}
        self.cache.clear()
        self.disk = None

    def _latest(self, repo, pattern):
        data = json.loads(http_get(f"https://api.github.com/repos/{repo}/releases/latest", 30))
        for a in data.get("assets", []):
            if re.search(pattern, a["name"]):
                return a["browser_download_url"], data.get("tag_name", "?").lstrip("v.")
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
        else:
            subprocess.run(["flatpak", "install", "--user", "-y", "--noninteractive", "flathub", e["flatpak"]],
                           check=True, capture_output=True, timeout=3600)

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
            with LIB.lock:
                games = [{k: g.get(k) for k in ("id", "system", "title", "serial", "region", "cover", "icon",
                                                "hero", "added", "plays", "last_played", "fav", "size")}
                         for g in LIB.games.values()]
            systems = [{"id": k, "name": v["name"], "short": v["short"], "order": v.get("order", 99)}
                       for k, v in SYSTEMS.items()]
            return self.send(200, {"games": games, "systems": systems, "scanning": LIB.scanning,
                                   "running": RUN.running(), "version": VERSION, "platform": PLATFORM,
                                   "settings": load_settings()})
        if path == "/api/events":
            return self.events()
        if path == "/api/sync":
            return self.send(200, sync_status_for_ui())
        if path == "/api/emulators":
            return self.send(200, {"emulators": EMUS.listing(), "disk": EMUS.disk_usage()})
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
            DATA.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
            return self.send(200, s)
        if path == "/api/fav":
            with LIB.lock:
                g = LIB.games.get(body.get("id"))
                if g:
                    g["fav"] = not g.get("fav")
                    LIB.save()
            return self.send(200, {"ok": bool(g), "fav": bool(g and g.get("fav"))})
        if path == "/api/quit":
            self.send(200, {"ok": True})
            def bye():
                time.sleep(0.3)
                os._exit(0)     # FORMULA.exe (Windows) / formula.sh (Deck) ferment la fenêtre en voyant le serveur s'arrêter
            threading.Thread(target=bye, daemon=True).start()
            return
        self.send(404, {"error": "not found"})


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
    threading.Thread(target=LIB.scan, daemon=True).start()
    threading.Thread(target=PAD.loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"FORMULA sur http://127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
