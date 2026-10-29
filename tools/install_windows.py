"""Installation complète de FORMULA sous Windows, à partir de ce dépôt.

Télécharge Python (version embarquée) et les émulateurs depuis leurs sites officiels, crée l'arborescence
de données, configure les émulateurs (tools/setup_windows.py) et crée le raccourci du bureau.
Ce qui ne peut pas être téléchargé : le BIOS PS2 (bios/ps2) et le firmware PS3 (bios/ps3), à fournir soi-même.

Usage (avec n'importe quel Python 3.10+) :
    python tools\\install_windows.py G:\\Jeux\\FORMULA
Relançable : ce qui est déjà installé est sauté. --update réinstalle les émulateurs (versions ci-dessous).
"""
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TAR = r"C:\Windows\System32\tar.exe"     # sait ouvrir .zip et .7z
UA = {"User-Agent": "FORMULA-installer/1.0"}

PYTHON_EMBED = "https://www.python.org/ftp/python/3.15.2/python-3.15.2-embed-amd64.zip"

# dossier dans emulators/ -> (archive officielle, exécutable attendu)
EMULATORS = {
    "pcsx2": ("https://github.com/PCSX2/pcsx2/releases/download/v2.8.2/pcsx2-v2.8.2-windows-x64-Qt.7z",
              "pcsx2-qt.exe"),
    "ppsspp": ("https://github.com/hrydgard/ppsspp/releases/download/v1.20.4/PPSSPP-v1.20.4-Windows-x64.zip",
               "PPSSPPWindows64.exe"),
    "rpcs3": ("https://github.com/RPCS3/rpcs3-binaries-win/releases/download/"
              "build-6c44fff7549e941389a4ce072a95c5ff9db7237c/rpcs3-v0.0.43-20415-6c44fff7_win64_msvc.7z",
              "rpcs3.exe"),
    "shadps4": ("https://github.com/shadps4-emu/shadPS4/releases/download/v.0.20.0/shadps4-win64-sdl-2026-0.20.0.zip",
                "shadPS4.exe"),
    "mgba": ("https://github.com/mgba-emu/mgba/releases/download/0.10.5/mGBA-0.10.5-win64.7z",
             "*/mGBA.exe"),
    "melonds": ("https://github.com/melonDS-emu/melonDS/releases/download/1.1/melonDS-1.1-windows-x86_64.zip",
                "melonDS.exe"),
    "rmg": ("https://github.com/Rosalie241/RMG/releases/download/v0.9.0/RMG-Portable-Windows64-v0.9.0.zip",
            "RMG.exe"),
    "nestopia": ("https://github.com/0ldsk00l/nestopia/releases/download/2.0.0/nestopia-2.0.0-windows-x86_64.zip",
                 "nestopia.exe"),
    "dolphin": ("https://dl.dolphin-emu.org/releases/2609a/dolphin-2609a-x64.7z", "Dolphin-x64/Dolphin.exe"),
}
CONSOLES = ["ps2", "psp", "ps3", "ps4", "nes", "n64", "gba", "nds", "gc", "wii"]

# fenêtre FORMULA.exe : bibliothèques WebView2 officielles (NuGet Microsoft), compilées avec csc.exe de Windows
WEBVIEW2 = "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/1.0.4314.35"
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"


def build_host(base, update=False):
    """Compile tools/winhost/FormulaHost.cs en <base>/FORMULA.exe (DLL WebView2 dans <base>/host)."""
    exe, host = base / "FORMULA.exe", base / "host"
    src = REPO / "tools" / "winhost" / "FormulaHost.cs"
    (base / "formula-data" / "code-dir.txt").write_text(str(REPO) + "\n", encoding="utf-8")
    if exe.exists() and exe.stat().st_mtime > src.stat().st_mtime and not update:
        print("déjà compilé : FORMULA.exe")
        return
    pkg = base / "_build" / "webview2"
    lib = pkg / "lib" / "net462"
    if not (lib / "Microsoft.Web.WebView2.WinForms.dll").exists():
        (base / "_build").mkdir(exist_ok=True)
        z = base / "_downloads" / "webview2.zip"
        download(WEBVIEW2, z)
        extract(z, pkg)
    host.mkdir(exist_ok=True)
    for f in (lib / "Microsoft.Web.WebView2.Core.dll", lib / "Microsoft.Web.WebView2.WinForms.dll",
              pkg / "runtimes" / "win-x64" / "native" / "WebView2Loader.dll"):
        (host / f.name).write_bytes(f.read_bytes())
    subprocess.run([CSC, "/nologo", "/target:winexe", "/platform:x64", "/optimize+",
                    f"/out:{exe}", f"/win32icon:{REPO / 'icon.ico'}",
                    "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll",
                    f"/r:{host / 'Microsoft.Web.WebView2.Core.dll'}",
                    f"/r:{host / 'Microsoft.Web.WebView2.WinForms.dll'}", str(src)], check=True)
    print("compilé :", exe)


def desktop_shortcut(base):
    """Raccourci du bureau vers FORMULA.exe (les manettes XInput marchent sans Steam)."""
    ps = (f'$ws=New-Object -ComObject WScript.Shell; $d=[Environment]::GetFolderPath("Desktop"); '
          f'$l=$ws.CreateShortcut("$d\\FORMULA.lnk"); $l.TargetPath="{base}\\FORMULA.exe"; '
          f'$l.Arguments=""; $l.WorkingDirectory="{base}"; '
          f'$l.IconLocation="{base}\\FORMULA.exe,0"; $l.Save()')
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def download(url, dest):
    print("téléchargement", url.rsplit("/", 1)[-1])
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def extract(archive, dest):
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([TAR, "-xf", str(archive), "-C", str(dest)], check=True)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    base = Path(sys.argv[1]).resolve()
    update = "--update" in sys.argv
    if "--host-only" in sys.argv:          # recompile seulement FORMULA.exe (+ raccourci du bureau)
        (base / "_downloads").mkdir(parents=True, exist_ok=True)
        build_host(base, True)
        desktop_shortcut(base)
        return
    dl = base / "_downloads"
    for d in ["emulators", "formula-data", "bios/ps2", "bios/ps3", "_downloads"] + [f"roms/{c}" for c in CONSOLES]:
        (base / d).mkdir(parents=True, exist_ok=True)
    (REPO / "formula-base.txt").write_text(str(base) + "\n", encoding="utf-8")

    py = base / "python"
    if not (py / "pythonw.exe").exists():
        z = dl / "python-embed.zip"
        download(PYTHON_EMBED, z)
        extract(z, py)

    for name, (url, exe) in EMULATORS.items():
        target = base / "emulators" / name
        if list(target.glob(exe)) and not update:
            print("déjà installé :", name)
            continue
        archive = dl / url.rsplit("/", 1)[-1]
        download(url, archive)
        extract(archive, target)
        if not list(target.glob(exe)):
            print(f"ATTENTION : {exe} introuvable après extraction de {name}")
        # version lue dans l'adresse de téléchargement (affichée dans Paramètres > Emulators)
        m = re.search(r"(\d+\.\d+(?:\.\d+)*(?:-\d+)?|\d{4}[a-z]?)(?=[^/]*$)", url.rsplit("/", 1)[-1])
        (target / ".formula-version").write_text(m.group(1) if m else "?", encoding="utf-8")

    subprocess.run([sys.executable, str(REPO / "tools" / "setup_windows.py")], check=True)
    build_host(base, update)
    desktop_shortcut(base)

    for f in dl.iterdir():
        f.unlink()
    print("\nInstallation terminée.")
    if not any((base / "bios" / "ps2").iterdir()):
        print(f"- Le BIOS PS2 est à placer dans {base / 'bios' / 'ps2'}")
    print(f"- Jeux : {base / 'roms'}\\<console>")
    print("- Raccourci Steam (facultatif) : python tools\\steam_shortcut.py "
          '"C:\\Program Files (x86)\\Steam\\userdata\\<id>"  (Steam fermé)')
    print("- Synchro avec le Deck : renseigner formula-data\\sync.json puis lancer formula.py --sync")


if __name__ == "__main__":
    main()
