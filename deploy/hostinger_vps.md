# Deploying Super Agents to Hostinger VPS

## Prerequisites

- Hostinger VPS (KVM plan recommended, minimum 2GB RAM)
- SSH access to your VPS
- Domain name (optional but recommended)

## 1. Initial VPS Setup

```bash
# SSH into your VPS
ssh root@YOUR_VPS_IP

# Update system
apt update && apt upgrade -y

# Install Python 3.11+, Node.js 18+, Git, SQLite
apt install -y python3.11 python3.11-venv python3-pip nodejs npm git sqlite3

# Verify versions
python3.11 --version  # 3.11+
node --version         # 18+
npm --version
```

## 2. Create deploy user (don't run as root)

```bash
adduser superagents
usermod -aG sudo superagents
su - superagents
```

## 3. Clone and install Super Agents

```bash
cd /home/superagents
git clone https://github.com/YOUR_REPO/Super_Agents.git
cd Super_Agents

# Create Python virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
# or if using pyproject.toml:
pip install -e .
```

## 4. Install Crucix (data hub)

```bash
# Clone Crucix as sidecar
python -m super_agents crucix setup

# Configure API keys
cp crucix/.env.example crucix/.env
nano crucix/.env
# Fill in your API keys: FRED_API_KEY, OPENSKY_USER, etc.
```

## 5. Environment variables

```bash
# Create project .env
cat > .env << 'EOF'
# Super Agents Configuration
SUPER_AGENTS_HTTP_TIMEOUT=30
SUPER_AGENTS_HTTP_MAX_RETRIES=3

# Crucix
CRUCIX_DIR=/home/superagents/Super_Agents/crucix
CRUCIX_PORT=3117

# API Keys (add your own)
FRED_API_KEY=your_key_here
OPENSKY_USERNAME=your_user
OPENSKY_PASSWORD=your_pass
EOF
```

## 6. Systemd services

### Crucix sidecar (auto-sweep every 15 min)

```bash
sudo cat > /etc/systemd/system/crucix-sidecar.service << 'EOF'
[Unit]
Description=Crucix Intelligence Sidecar
After=network.target

[Service]
Type=simple
User=superagents
WorkingDirectory=/home/superagents/Super_Agents/crucix
Environment=PORT=3117
ExecStart=/usr/bin/node server.mjs
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Crucix sweep timer (scheduled sweeps)

```bash
sudo cat > /etc/systemd/system/crucix-sweep.service << 'EOF'
[Unit]
Description=Crucix Intelligence Sweep
After=network.target

[Service]
Type=oneshot
User=superagents
WorkingDirectory=/home/superagents/Super_Agents
ExecStart=/home/superagents/Super_Agents/.venv/bin/python -m super_agents crucix sweep --store

[Install]
WantedBy=multi-user.target
EOF

sudo cat > /etc/systemd/system/crucix-sweep.timer << 'EOF'
[Unit]
Description=Run Crucix sweep every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min

[Install]
WantedBy=timers.target
EOF
```

### Streamlit dashboard

```bash
sudo cat > /etc/systemd/system/superagents-dashboard.service << 'EOF'
[Unit]
Description=Super Agents Streamlit Dashboard
After=network.target

[Service]
Type=simple
User=superagents
WorkingDirectory=/home/superagents/Super_Agents
ExecStart=/home/superagents/Super_Agents/.venv/bin/python -m streamlit run dashboards/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10
Environment=PYTHONPATH=/home/superagents/Super_Agents/src

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and start all services

```bash
sudo systemctl daemon-reload
sudo systemctl enable crucix-sidecar crucix-sweep.timer superagents-dashboard
sudo systemctl start crucix-sidecar crucix-sweep.timer superagents-dashboard

# Check status
sudo systemctl status crucix-sidecar
sudo systemctl status crucix-sweep.timer
sudo systemctl status superagents-dashboard
```

## 7. Nginx reverse proxy (recommended)

```bash
apt install -y nginx certbot python3-certbot-nginx

cat > /etc/nginx/sites-available/superagents << 'EOF'
server {
    listen 80;
    server_name your-domain.com;

    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Crucix API (internal only - optional)
    location /crucix/ {
        proxy_pass http://127.0.0.1:3117/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/superagents /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# SSL with Let's Encrypt
certbot --nginx -d your-domain.com
```

## 8. Firewall

```bash
# Allow SSH, HTTP, HTTPS only
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Block direct access to internal ports (Crucix, Streamlit)
# They're only accessible via Nginx reverse proxy
```

## 9. Cron jobs for agent tasks

```bash
# Edit crontab for scheduled agent runs
crontab -e

# Example: Run biotech FDA tracker daily at 6 AM UTC
0 6 * * * cd /home/superagents/Super_Agents && .venv/bin/python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals -- --days 1 >> /var/log/superagents/biotech.log 2>&1

# Example: Run simulation weekly on Mondays
0 8 * * 1 cd /home/superagents/Super_Agents && .venv/bin/python -m super_agents simulate scenarios/hormuz_zero_transit.yaml >> /var/log/superagents/simulations.log 2>&1
```

## 10. Monitoring

```bash
# Create log directory
mkdir -p /var/log/superagents

# Check dashboard
curl -s http://localhost:8501 | head -5

# Check Crucix
curl -s http://localhost:3117/health

# View sweep timer status
systemctl list-timers | grep crucix

# View recent logs
journalctl -u superagents-dashboard -n 50 --no-pager
journalctl -u crucix-sidecar -n 50 --no-pager
```

## Quick Reference

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 8501 | https://your-domain.com |
| Crucix API | 3117 | Internal only |
| SSH | 22 | `ssh superagents@your-domain.com` |

| Command | What it does |
|---------|-------------|
| `python -m super_agents list` | Show all agents |
| `python -m super_agents crucix sweep --store` | Run Crucix + persist |
| `python -m super_agents simulate scenarios/*.yaml` | Run simulation |
| `systemctl restart superagents-dashboard` | Restart dashboard |
| `systemctl restart crucix-sidecar` | Restart Crucix |

## Hostinger-Specific Notes

- **KVM 2 plan** ($8.99/mo) is minimum: 2 vCPU, 8GB RAM, 100GB SSD
- Use **Ubuntu 22.04** template when creating VPS
- Hostinger panel has a built-in firewall — configure it to match ufw rules
- For domain: point A record to VPS IP in Hostinger DNS manager
- SSH keys: upload via Hostinger panel > VPS > SSH Keys for passwordless login
