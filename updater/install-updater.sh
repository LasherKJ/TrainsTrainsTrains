#!/bin/bash
# One-time installer. Runs as root on the next boot, then removes itself.
# No "set -e" on purpose: a failure partway must not leave the Pi stuck in this boot mode.

BOOT=/boot/firmware
exec > "$BOOT/install-updater.log" 2>&1
echo "Installer started: $(date)"

# 1. Install the updater (root-owned, so the pi user can't break it by accident)
install -m 755 "$BOOT/updater.py" /usr/local/bin/mta-updater.py

# 2. The service that runs the update check
cat > /etc/systemd/system/mta-updater.service <<'EOF'
[Unit]
Description=Check GitHub for MTA display updates
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/mta-updater.py
EOF

# 3. The timer: 3 minutes after every boot, and daily at 4am
cat > /etc/systemd/system/mta-updater.timer <<'EOF'
[Unit]
Description=Daily MTA display update check

[Timer]
OnBootSec=3min
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl enable mta-updater.timer
echo "Timer enabled (exit code $?)"

# 4. Clean up so this never runs again
rm -f "$BOOT/updater.py" "$BOOT/install-updater.sh"
sed -i 's| systemd\.run[^ ]*||g; s| systemd\.unit=[^ ]*||g' "$BOOT/cmdline.txt"
echo "Cleanup done: $(date)"
exit 0