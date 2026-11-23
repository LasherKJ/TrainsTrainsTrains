# Pi Auto-Updater

Keeps the MTA arrivals display up to date without needing to reach the Pi. Once a day (and a few minutes after every boot), the Pi checks this repo's latest GitHub release and installs it if it's newer than what's running.

## Files

| File | Purpose |
|---|---|
| `updater.py` | Checks for a new release, installs it, restarts the service, and rolls back if the service fails to start |
| `install-updater.sh` | One-time installer. Runs as root on the Pi's next boot, sets up the update timer, then deletes itself |

## How it works

1. The `mta-updater.timer` systemd timer fires 3 minutes after boot and daily at 4:00 AM.
2. `updater.py` asks the GitHub API for the latest release tag and compares it to `/home/pi/mta-arrivals/.version`.
3. If the tag is new, it downloads the release, syntax-checks `mta_arrivals.py`, and backs up the current install to `/home/pi/mta-arrivals.bak`.
4. It copies the new files over the install, leaving `.venv` and `.version` alone, and runs `pip install` if `requirements.txt` changed.
5. It restarts `mta-arrivals.service`. If the service isn't running 20 seconds later, it restores the backup and tries again at the next check.
6. Any failure (no Wi-Fi, no release yet, GitHub down) is logged and the current version keeps running.

## Installing without SSH (SD card from a Mac)

This is how it was installed on a Pi that was already gifted away. It assumes Raspberry Pi OS Bookworm or newer, where the FAT partition mounts at `/boot/firmware` (older versions use `/boot`, so change `BOOT` in the script and the path below).

1. Insert the SD card. Click **Ignore** on any "disk not readable" prompt, never Initialize.
2. Save a copy of the original: `cp /Volumes/bootfs/cmdline.txt ~/cmdline.txt.original`
3. Copy both files onto the card: `cp updater.py install-updater.sh /Volumes/bootfs/`
4. Append the boot instruction to `cmdline.txt`, keeping it a single line:

   ```bash
   line=$(cat /Volumes/bootfs/cmdline.txt)
   printf '%s systemd.run=/boot/firmware/install-updater.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target' "$line" > /Volumes/bootfs/cmdline.txt
   ```

5. Eject the card, put it in the Pi, and power on. The first boot runs the installer and reboots once by itself.

If something goes wrong, restore the original with `cp ~/cmdline.txt.original /Volumes/bootfs/cmdline.txt`.

## Publishing an update

1. Push your changes to `main`.
2. On GitHub, go to **Releases > Draft a new release**, create a new tag (e.g. `v1.0.1`), and publish.
3. The Pi picks it up at its next check, so within a day, or sooner if it reboots.

Tags only need to differ from the previous one; they don't have to follow any numbering scheme. Test changes on your own machine first, because a broken release can only be rolled back automatically if the service fails to start (not if it starts but displays the wrong thing).

## Checking that it worked

With the Pi online and the card in a Mac:

- `install-updater.log` on the boot partition shows whether the one-time installer ran and finished.

With SSH or a keyboard on the Pi:

```bash
systemctl list-timers mta-updater.timer     # confirms the timer is scheduled
sudo journalctl -u mta-updater.service      # update check history and errors
cat /home/pi/mta-arrivals/.version          # currently installed release tag
sudo systemctl start mta-updater.service    # run a check right now
```

## Notes

- The update replaces everything in the repo except `.venv` and `.version`. Local files that aren't in the repo (like a hand-edited config) are left alone, but any repo file edited on the Pi will be overwritten.
- The repo must stay public, since the updater makes unauthenticated GitHub API requests. (GitHub allows 60 per hour per IP address, far more than needed.)
- If this folder is committed to the repo, it will be copied to the Pi along with everything else. That's harmless.
