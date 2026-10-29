"""Configure les émulateurs Windows de FORMULA (mode portable, manettes, langue FR, sauvegardes kDrive).

Relançable sans risque : ne remplace que les réglages qu'il gère.
Usage : python setup_windows.py
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("FORMULA_BASE") or (_REPO / "formula-base.txt").read_text(encoding="utf-8").strip())
EMU = BASE / "emulators"
ROMS = BASE / "roms"
BIOS = BASE / "bios"
REF = _REPO / "tools" / "templates"                  # réglages de référence (repris du Deck)
SAVES = Path.home() / "kDrive" / "Saves"             # mêmes dossiers que sur le Deck


def junction(link, target):
    """Remplace un dossier de sauvegarde par une jonction vers kDrive (contenu existant recopié)."""
    link, target = Path(link), Path(target)
    target.mkdir(parents=True, exist_ok=True)
    if link.exists() and os.path.isjunction(link):
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists():
        for p in link.iterdir():
            dst = target / p.name
            if not dst.exists():
                shutil.move(str(p), str(dst))
        shutil.rmtree(link)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True,
                   creationflags=0x08000000)   # pas de console visible quand FORMULA l'appelle
    print("jonction", link, "->", target)


def ini_set(path, section, values, sep=" = "):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
    out, cur, done = [], None, set()
    def flush():
        if cur == section:
            for k, v in values.items():
                if k not in done:
                    out.append(f"{k}{sep}{v}")
                    done.add(k)
    for l in lines:
        m = re.match(r"^\[(.+)\]\s*$", l)
        if m:
            flush()
            cur = m.group(1)
        elif cur == section:
            k = re.split(r"\s*=\s*", l, maxsplit=1)[0]
            if k in values:
                l = f"{k}{sep}{values[k]}"
                done.add(k)
        out.append(l)
    flush()
    if len(done) < len(values):
        out += ["", f"[{section}]"] + [f"{k}{sep}{v}" for k, v in values.items() if k not in done]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def pcsx2():
    d = EMU / "pcsx2"
    (d / "portable.ini").touch()
    ini = d / "inis" / "PCSX2.ini"
    if not ini.exists():
        ini.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REF / "PCSX2.ini", ini)   # manette SDL, assistant passé, BIOS PAL v2.0
    ini_set(ini, "Folders", {"Bios": BIOS / "ps2", "MemoryCards": SAVES / "PS2" / "memcards",
                             "Savestates": SAVES / "PS2" / "sstates"})
    ini_set(ini, "GameList", {"RecursivePaths": ROMS / "ps2"})


def ppsspp():
    d = EMU / "ppsspp"
    sysdir = d / "memstick" / "PSP" / "SYSTEM"
    ini = sysdir / "ppsspp.ini"
    ini_set(ini, "General", {"FirstRun": "False", "CurrentDirectory": str(ROMS / "psp").replace("\\", "/"),
                             "Language": "fr_FR", "CheckForNewVersion": "False"})
    ini_set(ini, "Graphics", {"InternalResolution": "2", "FullScreen": "True"})
    ini_set(ini, "SystemParam", {"GameLanguage": "2"})
    junction(d / "memstick" / "PSP" / "SAVEDATA", SAVES / "PSP" / "SAVEDATA")
    junction(d / "memstick" / "PSP" / "PPSSPP_STATE", SAVES / "PSP" / "PPSSPP_STATE")


def rpcs3():
    d = EMU / "rpcs3"
    (d / "input_configs" / "global").mkdir(parents=True, exist_ok=True)
    (d / "input_configs" / "global" / "Default.yml").write_text(
        "Player 1 Input:\n  Handler: XInput\n  Device: XInput Pad #0\n", encoding="utf-8")
    junction(d / "dev_hdd0" / "home" / "00000001" / "savedata", SAVES / "PS3" / "savedata")
    cfg = d / "config.yml"
    if cfg.exists():
        cfg.write_text(re.sub(r"(\n  Language: ).*", r"\1French", cfg.read_text(encoding="utf-8"), count=1),
                       encoding="utf-8")


def shadps4():
    d = EMU / "shadps4"
    (d / "user").mkdir(exist_ok=True)
    conf = d / "user" / "config.toml"
    if not conf.exists():
        conf.write_text("[Settings]\nconsoleLanguage = 2\n\n[General]\nFullscreen = true\n", encoding="utf-8")
    junction(d / "user" / "savedata", SAVES / "PS4" / "savedata")


def mgba():
    d = sorted((EMU / "mgba").glob("*/mGBA.exe"))[-1].parent   # sous-dossier nommé d'après la version
    (d / "portable.ini").touch()
    cfg = d / "config.ini"
    s = SAVES / "GBA"
    (s / "saves").mkdir(parents=True, exist_ok=True)
    (s / "states").mkdir(parents=True, exist_ok=True)
    ini_set(cfg, "ports.qt", {"savegamePath": s / "saves", "savestatePath": s / "states", "fullscreen": "1"}, sep="=")
    # manette XInput vue par SDL : A=0 B=1 X=2 Y=3 LB=4 RB=5 Back=6 Start=7, croix sur le chapeau 0
    keys = {"keyA": 1, "keyB": 0, "keyL": 4, "keyR": 5, "keySelect": 6, "keyStart": 7,
            "hat0Up": 6, "hat0Right": 4, "hat0Down": 7, "hat0Left": 5,
            "axisLeftAxis": "-0", "axisLeftValue": -16384, "axisRightAxis": "+0", "axisRightValue": 16384,
            "axisUpAxis": "-1", "axisUpValue": -16384, "axisDownAxis": "+1", "axisDownValue": 16384}
    ini_set(cfg, "gba.input.SDLB", keys, sep="=")


def melonds():
    d = EMU / "melonds"
    t = d / "melonDS.toml"
    if not t.exists():
        shutil.copy(REF / "melonDS.toml", t)
    s = t.read_text(encoding="utf-8")
    s = re.sub(r'(?m)^SaveFilePath = .*$', f'SaveFilePath = "{(SAVES / "DS" / "saves").as_posix()}"', s)
    s = re.sub(r'(?m)^SavestatePath = .*$', f'SavestatePath = "{(SAVES / "DS" / "states").as_posix()}"', s)
    t.write_text(s, encoding="utf-8")
    (SAVES / "DS" / "saves").mkdir(parents=True, exist_ok=True)


def dolphin():
    d = EMU / "dolphin" / "Dolphin-x64"
    (d / "portable.txt").touch()
    u = d / "User"
    junction(u / "GC", SAVES / "GameCube")
    junction(u / "Wii", SAVES / "Wii")
    cfg = u / "Config"
    ini_set(cfg / "Dolphin.ini", "Interface", {"ConfirmStop": "False", "UsePanicHandlers": "False"})
    ini_set(cfg / "Dolphin.ini", "Display", {"Fullscreen": "True"})
    ini_set(cfg / "Dolphin.ini", "Core", {"SelectedLanguage": "2", "SIDevice0": "6"})
    ini_set(cfg / "Dolphin.ini", "General", {"ISOPath0": ROMS / "wii", "ISOPath1": ROMS / "gc", "ISOPaths": "2"})
    ini_set(cfg / "Dolphin.ini", "Analytics", {"PermissionAsked": "True", "Enabled": "False"})
    dev = "XInput/0/Gamepad"
    gc = {"Device": dev, "Buttons/A": "`Button A`", "Buttons/B": "`Button X`", "Buttons/X": "`Button B`",
          "Buttons/Y": "`Button Y`", "Buttons/Z": "`Shoulder R`", "Buttons/Start": "`Start`",
          "Main Stick/Up": "`Left Y+`", "Main Stick/Down": "`Left Y-`", "Main Stick/Left": "`Left X-`",
          "Main Stick/Right": "`Left X+`", "C-Stick/Up": "`Right Y+`", "C-Stick/Down": "`Right Y-`",
          "C-Stick/Left": "`Right X-`", "C-Stick/Right": "`Right X+`", "Triggers/L": "`Trigger L`",
          "Triggers/R": "`Trigger R`", "Triggers/L-Analog": "`Trigger L`", "Triggers/R-Analog": "`Trigger R`",
          "D-Pad/Up": "`Pad N`", "D-Pad/Down": "`Pad S`", "D-Pad/Left": "`Pad W`", "D-Pad/Right": "`Pad E`"}
    ini_set(cfg / "GCPadNew.ini", "GCPad1", gc)
    wm = {"Source": "1", "Device": dev, "Buttons/A": "`Button A`", "Buttons/B": "`Trigger R`",
          "Buttons/1": "`Button X`", "Buttons/2": "`Button Y`", "Buttons/-": "`Back`", "Buttons/+": "`Start`",
          "D-Pad/Up": "`Pad N`", "D-Pad/Down": "`Pad S`", "D-Pad/Left": "`Pad W`", "D-Pad/Right": "`Pad E`",
          "IR/Up": "`Right Y+`", "IR/Down": "`Right Y-`", "IR/Left": "`Right X-`", "IR/Right": "`Right X+`",
          "Shake/X": "`Button B`", "Shake/Y": "`Button B`", "Shake/Z": "`Button B`", "Extension": "Nunchuk",
          "Nunchuk/Buttons/C": "`Shoulder L`", "Nunchuk/Buttons/Z": "`Trigger L`",
          "Nunchuk/Stick/Up": "`Left Y+`", "Nunchuk/Stick/Down": "`Left Y-`",
          "Nunchuk/Stick/Left": "`Left X-`", "Nunchuk/Stick/Right": "`Left X+`"}
    ini_set(cfg / "WiimoteNew.ini", "Wiimote1", wm)
    ini_set(cfg / "Hotkeys.ini", "Hotkeys", {"Device": dev, "General/Stop": "`Back`&`Start`"})


def rmg():
    d = EMU / "rmg"
    cfg = d / "Config" / "mupen64plus.cfg"
    (SAVES / "N64" / "Game").mkdir(parents=True, exist_ok=True)
    (SAVES / "N64" / "State").mkdir(parents=True, exist_ok=True)
    ini_set(cfg, "Rosalie's Mupen GUI Core", {"SaveSRAMPath": f'"{(SAVES / "N64" / "Game").as_posix()}"',
                                              "SaveStatePath": f'"{(SAVES / "N64" / "State").as_posix()}"'})
    # même profil manette que sur le Deck (SDL3 : A=Sud, B=Ouest, Z=LT, R=RT, L=LB, C=stick droit)
    B, AX = 0, 1
    m = {"A": ("A", B, 0, 0), "B": ("X", B, 2, 0), "Start": ("Start", B, 6, 0),
         "DpadUp": ("DPad Up", B, 11, 0), "DpadDown": ("DPad Down", B, 12, 0),
         "DpadLeft": ("DPad Left", B, 13, 0), "DpadRight": ("DPad Right", B, 14, 0),
         "CButtonUp": ("RightY-", AX, 3, 0), "CButtonDown": ("RightY+", AX, 3, 1),
         "CButtonLeft": ("RightX-", AX, 2, 0), "CButtonRight": ("RightX+", AX, 2, 1),
         "LeftShoulder": ("LB", B, 9, 0), "RightShoulder": ("RT", AX, 5, 1), "ZTrigger": ("LT", AX, 4, 1),
         "AnalogStickUp": ("LeftY-", AX, 1, 0), "AnalogStickDown": ("LeftY+", AX, 1, 1),
         "AnalogStickLeft": ("LeftX-", AX, 0, 0), "AnalogStickRight": ("LeftX+", AX, 0, 1)}
    prof = {"PluggedIn": "True", "DeviceType": "2", "DeviceName": '"Automatic"', "DeviceNum": "-1",
            "Deadzone": "9", "Sensitivity": "100", "Pak": "0"}
    for k, (n, t, dd, e) in m.items():
        prof.update({f"{k}_Name": f'"{n}"', f"{k}_InputType": f'"{t}"', f"{k}_Data": f'"{dd}"',
                     f"{k}_ExtraData": f'"{e}"'})
    ini_set(cfg, "Rosalie's Mupen GUI - Input Plugin Profile 0", prof)


XEMU_HDD = "https://github.com/xemu-project/xemu-hdd-image/releases/download/1.0/xbox_hdd.qcow2.zip"


def xemu():
    """xemu (Xbox) : mode portable (xemu.toml à côté de l'exe), BIOS dans bios/xbox, disque dur et EEPROM
    dans kDrive (les sauvegardes Xbox sont dans le disque dur virtuel)."""
    d = EMU / "xemu"
    s = SAVES / "Xbox"
    s.mkdir(parents=True, exist_ok=True)
    hdd = s / "xbox_hdd.qcow2"
    if not hdd.exists():
        # disque dur vierge publié par le projet xemu, sans contenu Microsoft
        import io
        import urllib.request
        import zipfile
        req = urllib.request.Request(XEMU_HDD, headers={"User-Agent": "FORMULA-setup/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, zipfile.ZipFile(io.BytesIO(r.read())) as z:
            hdd.write_bytes(z.read("xbox_hdd.qcow2"))
    bios = BIOS / "xbox"
    bios.mkdir(parents=True, exist_ok=True)
    # fichiers à fournir soi-même : boot ROM MCPX et BIOS (flash) ; on prend ceux présents, sinon les noms usuels
    bins = sorted(bios.glob("*.bin"))
    mcpx = next((p for p in bins if "mcpx" in p.name.lower()), bios / "mcpx_1.0.bin")
    flash = next((p for p in bins if p != mcpx and "eeprom" not in p.name.lower()), bios / "Complex_4627.bin")
    q = lambda p: "'" + str(p) + "'"
    toml = d / "xemu.toml"
    ini_set(toml, "general", {"show_welcome": "false", "skip_boot_anim": "true"})
    ini_set(toml, "general.updates", {"check": "false"})
    ini_set(toml, "input", {"auto_bind": "true"})
    ini_set(toml, "sys.files", {"bootrom_path": q(mcpx), "flashrom_path": q(flash),
                                "eeprom_path": q(s / "eeprom.bin"), "hdd_path": q(hdd)})


def xenia():
    """Xenia Canary (Xbox 360) : mode portable (portable.txt), contenu et sauvegardes dans kDrive,
    sans Discord."""
    d = EMU / "xenia"
    (d / "portable.txt").touch()
    junction(d / "content", SAVES / "Xbox 360")
    ini_set(d / "xenia-canary.config.toml", "General", {"discord": "false"})
    ini_set(d / "xenia-canary.config.toml", "Display", {"fullscreen": "true"})


if __name__ == "__main__":
    for f in (pcsx2, ppsspp, rpcs3, shadps4, mgba, melonds, dolphin, rmg, xemu, xenia):
        try:
            f()
            print("ok", f.__name__)
        except Exception as e:
            print("ERREUR", f.__name__, e)
