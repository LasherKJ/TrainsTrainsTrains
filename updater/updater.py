#!/usr/bin/env python3
"""Checks GitHub for a newer release of TrainsTrainsTrains and installs it."""
import hashlib, json, shutil, subprocess, tarfile, tempfile, time, urllib.request
from pathlib import Path

REPO = "LasherKJ/TrainsTrainsTrains"
APP_DIR = Path("/home/pi/mta-arrivals")
BACKUP_DIR = Path("/home/pi/mta-arrivals.bak")
VERSION_FILE = APP_DIR / ".version"
SERVICE = "mta-arrivals.service"
MAIN_SCRIPT = "mta_arrivals.py"
OWNER = "pi:pi"
KEEP = {".venv", ".version"}  # never overwritten by an update


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def run(*cmd, check=True):
    return subprocess.run(cmd, check=check)


def service_ok():
    time.sleep(20)  # give it a moment to crash if it's going to
    return subprocess.run(["systemctl", "is-active", "--quiet", SERVICE]).returncode == 0


def copy_tree(src, dst):
    for item in src.iterdir():
        if item.name in KEEP:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(item, target, ignore=shutil.ignore_patterns(".venv"))
        else:
            shutil.copy2(item, target)


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest() if path.exists() else None


def main():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/latest",
        headers={"User-Agent": "pi-updater"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        release = json.load(r)

    latest = release["tag_name"]
    current = VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else None
    if latest == current:
        log(f"Up to date ({current})")
        return

    log(f"Updating {current} -> {latest}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        tarball = tmp / "release.tar.gz"
        urllib.request.urlretrieve(release["tarball_url"], tarball)
        with tarfile.open(tarball) as t:
            t.extractall(tmp / "src")
        new_src = next((tmp / "src").iterdir())

        # Refuse to install a release whose main script has a syntax error
        run("python3", "-m", "py_compile", str(new_src / MAIN_SCRIPT))

        # Back up the current install (without the big .venv folder)
        shutil.rmtree(BACKUP_DIR, ignore_errors=True)
        shutil.copytree(APP_DIR, BACKUP_DIR, ignore=shutil.ignore_patterns(".venv"))

        old_reqs = md5(APP_DIR / "requirements.txt")
        copy_tree(new_src, APP_DIR)

    # Install any new Python dependencies
    if md5(APP_DIR / "requirements.txt") != old_reqs:
        log("requirements.txt changed; installing")
        run(str(APP_DIR / ".venv/bin/pip"), "install", "-r", str(APP_DIR / "requirements.txt"))

    run("chown", "-R", OWNER, str(APP_DIR))
    run("systemctl", "restart", SERVICE)

    if service_ok():
        VERSION_FILE.write_text(latest)
        log(f"Now running {latest}")
    else:
        log("Service failed after update; rolling back")
        copy_tree(BACKUP_DIR, APP_DIR)
        run("chown", "-R", OWNER, str(APP_DIR))
        run("systemctl", "restart", SERVICE, check=False)
        # Version file untouched, so it will retry next run (and fail again until you publish a fix)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"Update check failed: {e}")