# OCI to Umbrella BYOD Transfer Agent

Complete Installation and Configuration Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Credential Setup](#credential-setup)
5. [Configuration](#configuration)
6. [Testing the Installation](#testing-the-installation)
7. [Running in Interactive Mode](#running-in-interactive-mode)
8. [Loading Historical Files](#loading-historical-files)
9. [Running in Production](#running-in-production)
10. [Monitoring and Logs](#monitoring-and-logs)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The OCI to Umbrella BYOD Transfer Agent is an automated daemon that continuously monitors your Oracle Cloud Infrastructure (OCI) Object Storage for FOCUS cost reports and transfers them to your Umbrella BYOD S3 bucket.

**What it does:**
- Polls OCI Object Storage every 10 minutes for new FOCUS reports
- Streams files directly from OCI to S3 (no disk space needed)
- Renames files with date prefixes (YYYY-MM-DD_filename.csv.gz)
- Tracks transferred files to avoid duplicates
- Supports parallel transfers (3 files at once)
- Retries failed transfers with exponential backoff

---

## Prerequisites

### System Requirements

- **Operating System:** Linux (Ubuntu, RHEL, CentOS, Debian, Fedora)
- **Python:** Version 3.8 or higher
- **Memory:** Minimum 512 MB RAM (recommended 1 GB)
- **Network:** Stable internet connection for OCI and AWS access

### Required Access

- **Oracle OCI:** Read access to FOCUS reports in Object Storage
- **AWS S3:** Write access to Umbrella BYOD bucket

### Python Dependencies

The following Python packages are required:
- `boto3` - AWS SDK for Python
- `oci` - Oracle Cloud Infrastructure SDK
- `PyYAML` - YAML configuration parser

---

## Installation

There are three installation methods available:

- **Method A:** Automated Installation (Recommended for Linux servers)
- **Method B:** Manual Installation (For development or custom setups)
- **Method C:** Docker Installation (Recommended for containerized deployments)

### Method A: Automated Installation (Linux Servers) ⭐ RECOMMENDED

Use this method to deploy the agent on production Linux servers. The deployment package includes an automated installer that sets up everything for you.

#### Step 1: Download Deployment Package

```bash
# Download from GitHub releases or build from source
wget https://github.com/pileus-cloud/agent-oci-to-umbrella/releases/download/v1.0.0/agent-oci-to-umbrella-1.0.0.tar.gz

# Or build the package yourself
./package.sh
```

**Package Contents:**
- Python wheel package (ready to install)
- Systemd service file
- Automated installation script
- Configuration template
- Complete documentation

#### Step 2: Transfer to Target Server

```bash
# Copy to your Linux server
scp agent-oci-to-umbrella-1.0.0.tar.gz user@server:/tmp/

# SSH to the server
ssh user@server
```

#### Step 3: Extract Package

```bash
cd /tmp
tar -xzf agent-oci-to-umbrella-1.0.0.tar.gz
cd agent-oci-to-umbrella-1.0.0
```

#### Step 4: Run Automated Installer

```bash
sudo ./install.sh
```

**What the installer does:**
- ✅ Checks Python 3.8+ requirement
- ✅ Installs pip3 if needed (Ubuntu, RHEL, CentOS)
- ✅ Creates dedicated service user (`oci-umbrella-agent`)
- ✅ Creates directories: `/opt`, `/etc`, `/var/log`, `/var/lib`
- ✅ Installs Python package and dependencies
- ✅ Copies configuration template to `/etc/agent-oci-to-umbrella/config.yaml`
- ✅ Installs systemd service
- ✅ Tests the installation

#### Step 5: Configure the Agent

After installation completes, follow the on-screen instructions to configure:

```bash
# Edit main configuration
sudo nano /etc/agent-oci-to-umbrella/config.yaml

# Setup OCI credentials
sudo mkdir -p /root/.oci
sudo nano /root/.oci/config
# Copy your OCI private key
sudo cp /path/to/key.pem /root/.oci/
sudo chmod 600 /root/.oci/oci_api_key.pem

# Setup AWS credentials
sudo mkdir -p /root/.aws
sudo nano /root/.aws/credentials
```

#### Step 6: Test and Start

```bash
# Test configuration
sudo agent-oci-to-umbrella test --config /etc/agent-oci-to-umbrella/config.yaml

# Enable auto-start on boot
sudo systemctl enable agent-oci-to-umbrella

# Start the service
sudo systemctl start agent-oci-to-umbrella

# Check status
sudo systemctl status agent-oci-to-umbrella
```

**Installation Complete!** The agent is now running as a systemd service and will automatically start on boot.

---

### Method B: Manual Installation (Development/Custom Setup)

Use this method for development environments or if you want more control over the installation process.

#### Step 1: Clone or Download the Project

```bash
# If using git
git clone https://github.com/pileus-cloud/agent-oci-to-umbrella.git
cd agent-oci-to-umbrella

# Or download and extract the ZIP file
unzip agent-oci-to-umbrella.zip
cd agent-oci-to-umbrella
```

#### Step 2: Install Python Dependencies

```bash
pip3 install boto3 oci PyYAML
```

**Tip:** Consider using a virtual environment to isolate dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install boto3 oci PyYAML
```

#### Step 3: Install the Agent

```bash
# Development mode (editable install)
pip3 install -e .

# Or install from wheel
pip3 install dist/oracle_focus_agent-1.0.0-py3-none-any.whl
```

#### Step 4: Verify Installation

```bash
agent-oci-to-umbrella --help
```

**Expected Output:** You should see the help message with available commands (start, stop, run, test, sync, status).

---

### Method C: Docker Installation 🐳 CONTAINERIZED

Use this method to run the agent in a Docker container. Perfect for containerized environments, Kubernetes, or isolated deployments.

#### Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose (V1 or V2)
- 512 MB RAM minimum
- Volume mounts for credentials

#### Step 1: Clone or Download the Project

```bash
# Clone from GitHub
git clone https://github.com/pileus-cloud/agent-oci-to-umbrella.git
cd agent-oci-to-umbrella

# Or download and extract
wget https://github.com/pileus-cloud/agent-oci-to-umbrella/archive/main.zip
unzip main.zip
cd agent-oci-to-umbrella-main
```

#### Step 2: Run Docker Setup Script

```bash
./docker-setup.sh
```

**What the setup script does:**
- ✅ Checks Docker and Docker Compose are installed
- ✅ Creates required directories (config/, logs/, state/)
- ✅ Copies configuration template
- ✅ Checks for OCI and AWS credentials
- ✅ Builds the Docker image

#### Step 3: Configure the Agent

```bash
# Edit configuration
nano config/config.yaml
```

**Important:** Update paths for Docker volumes:

```yaml
logging:
  file: "/logs/agent.log"

state:
  file: "/state/state.json"
```

#### Step 4: Set Up Credentials

Ensure your credentials are in place:

```bash
# OCI credentials
ls -la ~/.oci/config
ls -la ~/.oci/oci_api_key.pem

# AWS credentials
ls -la ~/.aws/credentials
```

The Docker container will mount these directories as read-only volumes.

#### Step 5: Test Configuration

```bash
docker compose run --rm agent-oci-to-umbrella test --config /config/config.yaml
```

**Expected Output:**

```
✓ OCI connectivity: OK
✓ S3 connectivity: OK
✓ All tests passed!
```

#### Step 6: Run the Agent

**One-time sync:**

```bash
docker compose run --rm agent-oci-to-umbrella sync --config /config/config.yaml
```

**Start in daemon mode (runs continuously):**

```bash
docker compose up -d
```

**View logs:**

```bash
docker compose logs -f
```

**Check status:**

```bash
docker compose ps
```

**Stop the agent:**

```bash
docker compose down
```

### Docker Commands Reference

| Task | Command |
|------|---------|
| Build image | `docker compose build` |
| Test config | `docker compose run --rm agent-oci-to-umbrella test --config /config/config.yaml` |
| One-time sync | `docker compose run --rm agent-oci-to-umbrella sync --config /config/config.yaml` |
| Force sync | `docker compose run --rm agent-oci-to-umbrella sync --config /config/config.yaml --force` |
| Start daemon | `docker compose up -d` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |
| Stop daemon | `docker compose down` |
| Restart | `docker compose restart` |
| Rebuild | `docker compose build --no-cache` |

### Docker Volume Mounts

The Docker container uses the following volume mounts:

| Host Path | Container Path | Purpose | Mode |
|-----------|----------------|---------|------|
| `./config` | `/config` | Configuration files | Read-only |
| `./logs` | `/logs` | Agent logs | Read-write |
| `./state` | `/state` | State tracking | Read-write |

**Note:** Credentials are provided via environment variables (`.env` file), not volume mounts. This is more secure and portable across environments.

### Secrets Management

The agent supports **two methods** for managing credentials:

#### Method 1: Environment Variables (Recommended) ⭐

**Portable, works everywhere (AWS, Azure, GCP, on-prem)**

1. Copy the template:
   ```bash
   cp .env.template .env
   chmod 600 .env
   ```

2. Edit `.env` with your credentials:
   ```bash
   nano .env
   ```

3. Place your OCI private key:
   ```bash
   cp /path/to/your/oci_key.pem config/oci_private_key.pem
   chmod 600 config/oci_private_key.pem
   ```

4. Run the agent:
   ```bash
   docker compose up -d
   ```

**Pros:**
- ✅ Works in any environment (not cloud-specific)
- ✅ Easy to set up and understand
- ✅ `.env` file excluded from git automatically
- ✅ No volume mounting of credential directories

**`.env` file contains:**
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1

# OCI Credentials
OCI_USER_OCID=ocid1.user...
OCI_FINGERPRINT=aa:bb:cc...
OCI_TENANCY_OCID=ocid1.tenancy...
OCI_REGION=us-ashburn-1
OCI_KEY_FILE=/config/oci_private_key.pem
```

#### Method 2: Docker Secrets (Advanced)

**For Docker Swarm deployments requiring enhanced security**

1. Create Docker secrets:
   ```bash
   echo "AKIA..." | docker secret create aws_access_key_id -
   echo "secret..." | docker secret create aws_secret_access_key -
   cat oci_key.pem | docker secret create oci_private_key -
   # ... (see docker-compose.secrets.yml for full list)
   ```

2. Deploy with Docker Swarm:
   ```bash
   docker stack deploy -c docker-compose.secrets.yml agent-oci-to-umbrella
   ```

**Pros:**
- ✅ Secrets encrypted at rest and in transit
- ✅ Only available to specified services
- ✅ No plain text files
- ⚠️ Requires Docker Swarm mode

**For most users, Method 1 (Environment Variables) is recommended.**

### Docker Best Practices

**Resource Limits:**

The default `docker-compose.yml` includes resource limits:
- CPU: 1.0 max, 0.25 reserved
- Memory: 512 MB max, 128 MB reserved

**Logging:**

Logs are configured with rotation:
- Max size: 10 MB per file
- Max files: 3 files retained

**Health Check:**

The container includes a health check that runs every 60 seconds to ensure the agent is responsive.

**Security:**

- Credentials stored in `.env` file (not checked into git)
- OCI private key stored separately in `config/` directory
- Container runs as root (needed for OCI/AWS SDKs)
- No exposed ports (agent doesn't listen on any ports)
- All credential files have restrictive permissions (600)

---

## Credential Setup

### Oracle OCI Credentials

The agent uses the standard OCI configuration file (`~/.oci/config`).

#### Create OCI Config File

If you don't have an OCI config file yet, create `~/.oci/config`:

```ini
[DEFAULT]
user=ocid1.user.oc1..your-user-ocid
fingerprint=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
tenancy=ocid1.tenancy.oc1..your-tenancy-ocid
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

**Important:** Ensure your private key file (`oci_api_key.pem`) has proper permissions:

```bash
chmod 600 ~/.oci/oci_api_key.pem
```

### AWS S3 Credentials

The agent uses standard AWS credentials from `~/.aws/credentials`.

#### Create AWS Credentials File

```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials <<EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
EOF

chmod 600 ~/.aws/credentials
```

**Finding Your AWS Credentials:**
- **Access Key ID:** Identifies your AWS account (e.g., AKIAIOSFODNN7EXAMPLE)
- **Secret Access Key:** The password for your access key (keep this secure!)
- Both are required for AWS authentication

### Test Credentials

Verify your credentials work:

```bash
# Test OCI
oci os ns get

# Test AWS S3
aws s3 ls s3://your-bucket-name/ --region us-east-1
```

---

## Configuration

### Create Configuration File

Copy the template and customize for your environment:

```bash
cp config.template.yaml config.yaml
```

### Configure OCI Settings

Edit `config.yaml` and update the OCI section:

```yaml
oci:
  # Path to your OCI config file
  config_file: "~/.oci/config"

  # Profile name in config file
  profile: "DEFAULT"

  # Oracle billing namespace (use "bling", NOT your tenancy namespace)
  namespace: "bling"

  # Bucket name (your tenancy OCID)
  bucket: "ocid1.tenancy.oc1..aaaaaaaatjusogdqicpfl5vfvl7q474vm2ao7lzffenavtmwkc4p6olszjoq"

  # Prefix for FOCUS reports
  prefix: "FOCUS Reports/"
```

**Important:**
- Use `namespace: "bling"` (Oracle's billing namespace)
- Use your tenancy OCID as the bucket name

### Configure S3 Settings

```yaml
s3:
  # Full S3 path including your organization's prefix
  bucket_path: "s3://your-umbrella-bucket/your-org-id/0/YourName-id"

  # AWS region
  region: "us-east-1"

  # Leave credentials empty (uses ~/.aws/credentials)
  access_key_id: ""
  secret_access_key: ""
```

### Configure Agent Settings

```yaml
agent:
  # Polling interval in seconds (600 = 10 minutes)
  poll_interval: 600

  # Number of days to look back (1 = yesterday + today)
  lookback_days: 1

  # Maximum concurrent file transfers
  max_concurrent_transfers: 3

  # Enable daemon mode
  daemon_mode: true
```

**Key Settings:**
- `poll_interval`: How often to check for new files (seconds)
- `lookback_days`: Number of past days to scan for files
- `max_concurrent_transfers`: Parallel upload limit (3 recommended)

---

## Testing the Installation

### Step 1: Test Configuration and Connectivity

```bash
agent-oci-to-umbrella test --config config.yaml
```

**Expected Output:**

```
Configuration Test
======================================================================
✓ OCI config file: ~/.oci/config [DEFAULT]
✓ OCI namespace: bling
✓ OCI bucket: ocid1.tenancy.oc1..aaaaaaaatjusogdqicpfl5vfvl7q474vm2ao7lzffenavtmwkc4p6olszjoq
✓ OCI connectivity: OK
✓ S3 bucket path: s3://your-bucket/...
✓ S3 region: us-east-1
✓ S3 connectivity: OK
✓ State file: ./state/state.json
  - Tracked files: 0

✓ All tests passed!
```

### Step 2: Perform Test Sync

Run a one-time sync to verify file transfers work:

```bash
agent-oci-to-umbrella sync --config config.yaml
```

**Expected Output:**

```
======================================================================
Starting sync operation
======================================================================
Processing date range: 2025-11-24 to 2025-11-25 (2 days)
Discovered 6 total files
Files to transfer: 6
Files skipped (already transferred): 0
Starting parallel transfers (max 3 concurrent)
✓ Transferred: 2025-11-24_0001000002711283-00001.csv.gz (124.47 KB)
✓ Transferred: 2025-11-24_0001000002711630-00001.csv.gz (213.04 KB)
✓ Transferred: 2025-11-24_0001000002711992-00001.csv.gz (240.18 KB)
...
======================================================================
Sync operation complete
  Discovered: 6
  Transferred: 6
  Skipped: 0
  Failed: 0
  Data transferred: 989.41 KB
  Duration: 4.0s
======================================================================
```

### Step 3: Verify State Tracking

Run sync again to verify files are skipped:

```bash
agent-oci-to-umbrella sync --config config.yaml
```

**Expected Output:**

```
Discovered: 6 total files
Files to transfer: 0
Files skipped (already transferred): 6
All files already transferred
```

---

## Running in Interactive Mode

Interactive mode runs the agent in the foreground, making it perfect for testing and monitoring real-time behavior. The agent will poll every 10 minutes and display all activity in your terminal.

### Start Interactive Mode

```bash
agent-oci-to-umbrella run --config config.yaml
```

**Interactive Mode Features:**
- Real-time log output directly to your terminal
- Polls every 10 minutes (configurable via `poll_interval`)
- Press `Ctrl+C` to stop gracefully
- Perfect for testing and debugging
- See transfer progress immediately

**Example Output:**

```
2025-11-25 10:00:00 - INFO - Starting agent in foreground mode (Ctrl+C to stop)
2025-11-25 10:00:00 - INFO - Starting sync operation
2025-11-25 10:00:02 - INFO - Discovered 3 total files
2025-11-25 10:00:02 - INFO - Files to transfer: 3
2025-11-25 10:00:05 - INFO - ✓ Transferred: 2025-11-25_0001000002713240-00001.csv.gz
2025-11-25 10:00:06 - INFO - Sync operation complete
2025-11-25 10:00:06 - INFO - Next sync in 600 seconds...
2025-11-25 10:10:00 - INFO - Starting sync operation
...
```

### Stop Interactive Mode

Press `Ctrl+C` to stop the agent gracefully:

```bash
^C
2025-11-25 10:15:30 - INFO - Stopped by user
```

---

## Loading Historical Files

If you need to load historical FOCUS files from the past (e.g., last 10 days, 30 days, etc.), follow these steps:

### Step 1: Configure Lookback Period

Edit `config.yaml` and set `lookback_days` to your desired period:

```yaml
agent:
  # Load last 10 days of historical files
  lookback_days: 10
```

| Lookback Days | Date Range | Use Case |
|---------------|------------|----------|
| 1 | Yesterday + Today | Normal daily operation |
| 7 | Last 7 days | Weekly backfill |
| 10 | Last 10 days | Initial setup / testing |
| 30 | Last 30 days | Monthly historical load |
| 90 | Last 90 days | Quarterly historical load |

### Step 2: Force Sync Historical Files

Use the `--force` flag to transfer all discovered files, ignoring state tracking:

```bash
agent-oci-to-umbrella sync --config config.yaml --force
```

**Force Mode Behavior:**
- Ignores `state.json` completely
- Re-transfers ALL files in the date range
- Overwrites existing files in S3
- Useful when Oracle updates files

**Example: Load Last 10 Days**

```bash
# Step 1: Edit config.yaml
agent:
  lookback_days: 10

# Step 2: Force sync
agent-oci-to-umbrella sync --config config.yaml --force

# Output:
Starting sync operation (FORCED - ignoring state)
Processing date range: 2025-11-15 to 2025-11-25 (10 days)
Discovered 66 total files
Force mode enabled: transferring all files regardless of state
Files to transfer: 66
Files skipped: 0 (force mode: re-transferring all)
✓ Transferred: 2025-11-15_0001000002701234-00001.csv.gz
✓ Transferred: 2025-11-15_0001000002701456-00001.csv.gz
...
Sync operation complete
  Discovered: 66
  Transferred: 66
  Skipped: 0
  Failed: 0
  Data transferred: 11.13 MB
  Duration: 19.7s
```

### Step 3: Reset to Normal Operation

After loading historical files, reset `lookback_days` to normal operation:

```yaml
agent:
  # Back to normal: yesterday + today
  lookback_days: 1
```

### Historical Loading Strategies

| Strategy | Configuration | Command |
|----------|---------------|---------|
| **Initial Setup** | `lookback_days: 10` | `sync --force` |
| **Monthly Backfill** | `lookback_days: 30` | `sync --force` |
| **Re-sync Updated Files** | `lookback_days: 7` | `sync --force` |
| **Daily Operation** | `lookback_days: 1` | `run` (daemon mode) |

---

## Running in Production

### Start as Background Daemon

```bash
agent-oci-to-umbrella start --config config.yaml
```

**Output:**

```
Starting daemon in background...
Daemon started with PID 12345
```

### Check Daemon Status

```bash
agent-oci-to-umbrella status
```

**Output:**

```
Daemon is running with PID 12345
```

### Stop Daemon

```bash
agent-oci-to-umbrella stop
```

**Output:**

```
Stopping daemon (PID 12345)...
Daemon stopped successfully
```

### Production Best Practices

- **Use systemd:** Create a systemd service for auto-start on boot
- **Monitor logs:** Set up log rotation and monitoring
- **Set alerts:** Alert on transfer failures
- **Review state:** Periodically check `state/state.json`
- **Secure credentials:** Use proper file permissions (chmod 600)

---

## Monitoring and Logs

### View Real-Time Logs

```bash
tail -f logs/agent.log
```

### Check Transfer State

```bash
cat state/state.json
```

**State File Contains:**
- All transferred files with timestamps
- File sizes and creation times
- Transfer durations
- Last sync timestamp

### Log Levels

Configure log verbosity in `config.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### Key Metrics to Monitor

| Metric | Where to Find | What to Watch |
|--------|---------------|---------------|
| Files Transferred | Logs: "Transferred: X" | Should match Oracle's file count |
| Files Skipped | Logs: "Skipped: X" | Should increase after initial load |
| Files Failed | Logs: "Failed: X" | Should be 0 |
| Transfer Duration | Logs: "Duration: Xs" | Monitor for slow transfers |
| State File Size | `ls -lh state/state.json` | Grows over time |

---

## Troubleshooting

### Problem: OCI Connectivity Test Fails

**Error:** `✗ OCI connectivity: FAILED - Invalid credentials`

**Solutions:**
- Verify `~/.oci/config` exists and is properly formatted
- Check private key path is correct: `key_file=~/.oci/oci_api_key.pem`
- Ensure private key has correct permissions: `chmod 600 ~/.oci/oci_api_key.pem`
- Test OCI CLI: `oci os ns get`

### Problem: S3 Connectivity Test Fails

**Error:** `✗ S3 connectivity: FAILED - Access Denied`

**Solutions:**
- Verify `~/.aws/credentials` contains valid credentials
- Check AWS credentials permissions: `chmod 600 ~/.aws/credentials`
- Verify S3 bucket path is correct in `config.yaml`
- Test AWS CLI: `aws s3 ls s3://your-bucket/ --region us-east-1`
- Ensure IAM user has `s3:PutObject` permission

### Problem: No Files Discovered

**Output:** `Discovered 0 total files`

**Solutions:**
- Verify OCI namespace is `"bling"` (not your tenancy namespace)
- Check bucket name is your tenancy OCID
- Verify prefix: `"FOCUS Reports/"` (with trailing slash)
- Increase `lookback_days` to search more days
- Check if Oracle has generated FOCUS reports yet

### Problem: Files Not Transferring (All Skipped)

**Output:** `Files to transfer: 0, Skipped: 10`

**Solutions:**
- Files were already transferred (check `state/state.json`)
- To re-transfer, use `--force` flag: `agent-oci-to-umbrella sync --config config.yaml --force`
- Or delete state file to start fresh: `rm state/state.json`

### Problem: Daemon Won't Start

**Error:** `Error: Daemon already running with PID 12345`

**Solutions:**
- Check if daemon is actually running: `agent-oci-to-umbrella status`
- Stop existing daemon: `agent-oci-to-umbrella stop`
- If stuck, kill process manually: `kill $(cat /tmp/agent-oci-to-umbrella.pid)`
- Remove stale PID file: `rm /tmp/agent-oci-to-umbrella.pid`

### Problem: Transfer Failures

**Output:** `Failed: 3, Errors: [...]`

**Solutions:**
- Check logs for specific error messages: `tail -100 logs/agent.log`
- Verify network connectivity to both OCI and AWS
- Check file sizes aren't exceeding limits (default: 5 GB)
- Retry with: `agent-oci-to-umbrella sync --config config.yaml --force`
- Increase retry settings in `config.yaml`

### Problem: Slow Transfers

**Symptom:** Transfers taking much longer than expected

**Solutions:**
- Check network bandwidth and latency
- Increase concurrent transfers (max 5): `max_concurrent_transfers: 5`
- Adjust chunk size (default 8MB): `chunk_size_bytes: 16777216`
- Run from a server closer to OCI/AWS regions

### Getting Help

**Support Resources:**
- **Documentation:** Check INSTALLATION_GUIDE.html
- **Logs:** Review `logs/agent.log` for detailed errors
- **State:** Inspect `state/state.json` for transfer history
- **Test Mode:** Run `agent-oci-to-umbrella test --config config.yaml`
- **Verbose Logs:** Set `level: "DEBUG"` in config for more detail

---

## Quick Reference Commands

| Task | Command |
|------|---------|
| Test configuration | `agent-oci-to-umbrella test --config config.yaml` |
| One-time sync | `agent-oci-to-umbrella sync --config config.yaml` |
| Force re-transfer all | `agent-oci-to-umbrella sync --config config.yaml --force` |
| Run interactively | `agent-oci-to-umbrella run --config config.yaml` |
| Start daemon | `agent-oci-to-umbrella start --config config.yaml` |
| Check status | `agent-oci-to-umbrella status` |
| Stop daemon | `agent-oci-to-umbrella stop` |
| View logs | `tail -f logs/agent.log` |
| Check state | `cat state/state.json` |

---

## Installation Locations (Automated Install)

After automated installation, files are located at:

| Component | Location |
|-----------|----------|
| Binary | `/usr/local/bin/agent-oci-to-umbrella` |
| Configuration | `/etc/agent-oci-to-umbrella/config.yaml` |
| OCI Credentials | `/root/.oci/config` |
| AWS Credentials | `/root/.aws/credentials` |
| Logs | `/var/log/agent-oci-to-umbrella/agent.log` |
| State | `/var/lib/agent-oci-to-umbrella/state.json` |
| Systemd Service | `/etc/systemd/system/agent-oci-to-umbrella.service` |
| PID File | `/tmp/agent-oci-to-umbrella.pid` |

---

## Service Management (Systemd)

```bash
# Start/Stop/Restart
sudo systemctl start agent-oci-to-umbrella
sudo systemctl stop agent-oci-to-umbrella
sudo systemctl restart agent-oci-to-umbrella

# Enable/Disable Auto-Start
sudo systemctl enable agent-oci-to-umbrella   # Start on boot
sudo systemctl disable agent-oci-to-umbrella  # Don't start on boot

# View Logs
sudo journalctl -u agent-oci-to-umbrella -f

# View last 100 lines
sudo journalctl -u agent-oci-to-umbrella -n 100
```

---

**Installation Complete!** Your OCI to Umbrella BYOD Transfer Agent is ready to use. Start with:

```bash
agent-oci-to-umbrella test --config config.yaml
```

---

OCI to Umbrella BYOD Transfer Agent v1.0.0 | Last Updated: November 25, 2025
