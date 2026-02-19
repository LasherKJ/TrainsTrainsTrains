# Running MTA Arrivals on Raspberry Pi

This guide shows different ways to run the MTA arrivals script automatically every N seconds on a Raspberry Pi.

## Setup Instructions

### 1. Transfer Files to Raspberry Pi
```bash
# From your Mac/PC, copy your project to the Pi
# Replace "raspberrypi.local" with your Pi's IP address if needed
scp -r "/Users/kevinlasher/Desktop/untitled folder"/* pi@raspberrypi.local:/home/pi/mta-arrivals/
```

### 2. Install Dependencies on Pi
```bash
# SSH into your Raspberry Pi (one-time setup)
ssh pi@raspberrypi.local
cd /home/pi/mta-arrivals

# Install Python dependencies

# Step 1: Check Python versions available
python3 --version    # Should show Python 3.x
python --version     # Might show Python 2.7 (ignore this)

# Step 2: If Python 3 is too old (< 3.7), upgrade the system
sudo apt update
sudo apt upgrade -y

# Step 3: Install Python 3 development tools
sudo apt install python3-dev python3-venv python3-pip

# Step 4: Create virtual environment using Python 3
python3 -m venv .venv

# Step 5: Activate virtual environment and install packages
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** You only need SSH for the initial setup. Once configured, the Pi runs independently and will automatically start the MTA monitoring service on boot (if using systemd method).

## Method 1: Built-in Monitoring (Easiest)

The script now has continuous monitoring enabled by default. Just run:

```bash
python mta_arrivals.py
```

**Pros:** Simple, handles errors gracefully, clears screen between updates  
**Cons:** Stops if SSH session ends

To run in background:
```bash
nohup python mta_arrivals.py > arrivals.log 2>&1 &
```

## Method 2: Systemd Service (Recommended)

This runs the script as a system service that starts automatically on boot.

### Setup:
```bash
# Copy the service file
sudo cp mta-arrivals.service /etc/systemd/system/

# Edit paths in the service file if needed
sudo nano /etc/systemd/system/mta-arrivals.service

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable mta-arrivals.service
sudo systemctl start mta-arrivals.service
```

### Management:
```bash
# Check status
sudo systemctl status mta-arrivals.service

# View logs
sudo journalctl -u mta-arrivals.service -f

# Stop service
sudo systemctl stop mta-arrivals.service

# Restart service
sudo systemctl restart mta-arrivals.service
```

**Pros:** Automatic startup, restarts on failure, proper logging  
**Cons:** Requires sudo to manage

## Method 3: Cron Job

Runs the script at regular intervals using cron.

### Setup:
```bash
# Make the cron script executable
chmod +x run_arrivals_cron.sh

# Edit your crontab
crontab -e

# Add one of these lines:

# Every minute:
* * * * * /home/pi/mta-arrivals/run_arrivals_cron.sh

# Every 2 minutes:
*/2 * * * * /home/pi/mta-arrivals/run_arrivals_cron.sh

# Every 5 minutes:
*/5 * * * * /home/pi/mta-arrivals/run_arrivals_cron.sh
```

**Pros:** Simple, reliable, good for less frequent updates  
**Cons:** Minimum 1-minute intervals, separate processes each time

## Method 4: Simple Loop Script

Runs a bash loop that executes the script every N seconds.

### Setup:
```bash
# Make executable
chmod +x run_loop.sh

# Run with default 30-second interval
./run_loop.sh

# Run with custom interval (60 seconds)
./run_loop.sh 60

# Run in background
nohup ./run_loop.sh 30 > arrivals.log 2>&1 &
```

**Pros:** Very flexible timing, simple to understand  
**Cons:** Stops if SSH session ends (unless using nohup)

## Method 5: Screen/Tmux Session

Run in a persistent terminal session:

```bash
# Install screen or tmux
sudo apt update
sudo apt install screen

# Start a screen session
screen -S mta-arrivals

# Run your script
python mta_arrivals.py

# Detach: Ctrl+A, then D
# Reattach: screen -r mta-arrivals
```

**Pros:** Easy to monitor, can reconnect to see output  
**Cons:** Manual management

## Recommendations

- **For continuous monitoring**: Use **Method 2 (Systemd)** - most reliable
- **For periodic checks**: Use **Method 3 (Cron)** - every 5+ minutes
- **For development/testing**: Use **Method 1 (Built-in)** or **Method 5 (Screen)**

## Customizing Update Frequency

Edit the interval in:
- **Built-in monitoring**: Change `mta.monitor_arrivals(30)` → `mta.monitor_arrivals(60)`
- **Loop script**: Run `./run_loop.sh 60` 
- **Cron job**: Modify crontab timing
- **Systemd**: The service runs continuously with built-in timing

## Viewing Logs

```bash
# Method 1 & 4: Check log files
tail -f arrivals.log

# Method 2: Systemd logs
sudo journalctl -u mta-arrivals.service -f

# Method 3: Cron logs (if logging enabled)
grep CRON /var/log/syslog
```

## Auto-start on Boot

- **Systemd service**: Automatically starts on boot
- **Cron**: Automatically runs on schedule
- **Others**: Add to `/etc/rc.local` or create systemd service

## Upgrading Old Raspberry Pi OS

If you're getting 404 errors or have Python 2.7, your Pi is running an outdated OS. Here are your options:

### **Option A: Fresh Install (Recommended)**

**Best approach for old systems:**

1. **Backup your data** (if any important files exist)
2. **Download latest Raspberry Pi OS** from [rpi.org/software](https://www.raspberrypi.org/software/)
3. **Flash to SD card** using Raspberry Pi Imager
4. **Boot fresh system** and transfer your MTA files

**Benefits:** Clean system, latest Python 3.9+, all modern packages

### **Option B: In-Place Upgrade (Advanced)**

**Only if you have important data to preserve:**

```bash
# 1. Fix repositories for old Stretch
sudo sed -i 's|stretch|buster|g' /etc/apt/sources.list
sudo sed -i 's|stretch|buster|g' /etc/apt/sources.list.d/raspi.list

# 2. Update package lists
sudo apt update

# 3. Upgrade to Buster (may take 1-2 hours)
sudo apt full-upgrade -y

# 4. Reboot
sudo reboot

# 5. After reboot, upgrade to Bullseye
sudo sed -i 's|buster|bullseye|g' /etc/apt/sources.list
sudo sed -i 's|buster|bullseye|g' /etc/apt/sources.list.d/raspi.list
sudo apt update && sudo apt full-upgrade -y
sudo reboot
```

**Risks:** May break, requires multiple reboots, time-consuming

### **Option C: Quick Fix for Old OS**

**If you just want to run the MTA script now:**

```bash
# Fix archive repositories
sudo sed -i 's|http://raspbian.raspberrypi.org/raspbian|http://archive.raspbian.org/raspbian|g' /etc/apt/sources.list

# Update with archive
sudo apt update

# Install packages globally (skip virtual env)
sudo apt install python3-pip
sudo pip3 install requests gtfs-realtime-bindings protobuf

# Run script directly
python3 mta_arrivals.py
```

### **Recommendation:**

**Fresh install (Option A)** is cleanest and fastest. Takes ~30 minutes total vs. hours for in-place upgrade.