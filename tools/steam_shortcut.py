"""Ajoute FORMULA aux jeux non-Steam (shortcuts.vdf binaire) avec ses visuels. Idempotent.

Steam ne relit ce fichier qu'au démarrage : à lancer Steam fermé, ou redémarrer Steam après.
Usage : python steam_shortcut.py <dossier userdata\\<id>>
"""
import shutil
import struct
import sys
import zlib
from pathlib import Path

F = Path(__file__).resolve().parents[1]                     # dépôt FORMULA (code)
BASE = Path((F / "formula-base.txt").read_text(encoding="utf-8").strip())   # données (python, émulateurs…)
EXE = f'"{BASE / "FORMULA.exe"}"'            # fenêtre WebView2 (lance elle-même le serveur)
OPTS = ""
NAME = "FORMULA"


def parse(b, i=0):
    out = {}
    while True:
        t = b[i]; i += 1
        if t == 8:
            return out, i
        j = b.index(0, i); key = b[i:j].decode("utf-8", "replace"); i = j + 1
        if t == 0:
            out[key], i = parse(b, i)
        elif t == 1:
            j = b.index(0, i); out[key] = b[i:j].decode("utf-8", "replace"); i = j + 1
        elif t == 2:
            out[key] = struct.unpack_from("<I", b, i)[0]; i += 4
        else:
            raise ValueError(f"type VDF inconnu {t}")


def dump(d):
    b = bytearray()
    for k, v in d.items():
        kb = k.encode() + b"\0"
        if isinstance(v, dict):
            b += b"\0" + kb + dump(v)
        elif isinstance(v, int):
            b += b"\2" + kb + struct.pack("<I", v)
        else:
            b += b"\1" + kb + str(v).encode() + b"\0"
    return bytes(b + b"\x08")


def main(userdir):
    cfg = Path(userdir) / "config"
    vdf = cfg / "shortcuts.vdf"
    data = parse(vdf.read_bytes())[0] if vdf.exists() else {"shortcuts": {}}
    sc = data.setdefault("shortcuts", {})
    appid = (zlib.crc32((EXE + NAME).encode()) & 0xFFFFFFFF) | 0x80000000
    fields = {"Exe": EXE, "StartDir": f'"{BASE}"', "icon": str(F / "icon.ico"), "LaunchOptions": OPTS}
    if vdf.exists():
        shutil.copy(vdf, vdf.with_suffix(".vdf.avant-formula"))
    for k, v in sc.items():
        if v.get("AppName") == NAME or v.get("appname") == NAME:
            v.update(fields)          # met à jour les chemins, garde l'appid (et donc les visuels)
            appid = v.get("appid", appid)
            print("mis à jour", k)
            break
    else:
        sc[str(len(sc))] = {"appid": appid, "AppName": NAME, **fields, "ShortcutPath": "",
                            "IsHidden": 0, "AllowDesktopConfig": 1, "AllowOverlay": 1, "OpenVR": 0,
                            "Devkit": 0, "DevkitGameID": "", "DevkitOverrideAppID": 0, "LastPlayTime": 0,
                            "FlatpakAppID": "", "tags": {}}
        print("ajouté, appid", appid)
    vdf.write_bytes(dump(data))
    grid = cfg / "grid"
    grid.mkdir(exist_ok=True)
    art = F / "art"
    for src, dst in (("portrait.png", f"{appid}p.png"), ("wide.png", f"{appid}.png"),
                     ("hero.png", f"{appid}_hero.png"), ("logo.png", f"{appid}_logo.png")):
        if (art / src).exists():
            shutil.copy(art / src, grid / dst)
    print("rungameid", (appid << 32) | 0x02000000)


if __name__ == "__main__":
    main(sys.argv[1])
