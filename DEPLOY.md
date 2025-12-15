# PacketArch Deployment Guide

## GitHub-Based Deployment

PacketArch uses GitHub Actions for CI/CD. Pushing to `main` automatically deploys to production.

### Initial Server Setup (One-Time)

1. **SSH into your production server:**
   ```bash
   ssh user@your-server-ip
   ```

2. **Run the initialization script:**
   ```bash
   curl -sSL https://raw.githubusercontent.com/YOUR_ORG/PacketArch/main/scripts/server-init.sh | GITHUB_REPO=YOUR_ORG/PacketArch bash
   ```

   Or manually:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER

   # Clone and build
   git clone https://github.com/YOUR_ORG/PacketArch.git ~/packetarch
   cd ~/packetarch

   # Create .env
   cat > .env << 'EOF'
   POSTGRES_PASSWORD=your_secure_password
   SECRET_KEY=$(openssl rand -hex 32)
   ENCRYPTION_KEY=
   ADMIN_PASSWORD=your_admin_password
   DEBUG=false
   EOF

   # Build and start
   sudo docker compose up -d --build
   ```

3. **Set up SSH key authentication:**
   ```bash
   # On your local machine, generate a deploy key (if you don't have one)
   ssh-keygen -t ed25519 -f ~/.ssh/packetarch_deploy -N ""

   # Copy public key to server
   ssh-copy-id -i ~/.ssh/packetarch_deploy.pub user@your-server-ip
   ```

### GitHub Repository Setup

1. **Go to your repository Settings → Secrets and variables → Actions**

2. **Add these secrets:**

   | Secret | Description |
   |--------|-------------|
   | `SSH_HOST` | Production server IP address |
   | `SSH_USER` | SSH username on server |
   | `SSH_PRIVATE_KEY` | Contents of your deploy private key |
   | `POSTGRES_PASSWORD` | Database password |
   | `SECRET_KEY` | Application secret key (64 hex chars) |
   | `ENCRYPTION_KEY` | Optional encryption key |
   | `ADMIN_PASSWORD` | Admin user password |

3. **Get the private key:**
   ```bash
   cat ~/.ssh/packetarch_deploy
   ```
   Copy the entire output including `-----BEGIN/END-----` lines.

### Deployment Workflow

After setup, deployment is automatic:

```
Push to main → GitHub Actions → SSH to server → git pull → docker compose up
```

**Manual deployment trigger:**
- Go to Actions → Deploy to Production → Run workflow

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR to main | Lint + build test |
| `deploy.yml` | Push to main | Deploy to production |

### Monitoring

**Check deployment status:**
- GitHub: Actions tab shows workflow runs
- Server: `sudo docker compose ps`
- Logs: `sudo docker compose logs -f backend`

### Rollback

To rollback to a previous version:
```bash
ssh user@your-server-ip
cd ~/packetarch
git log --oneline -10  # Find commit to rollback to
git reset --hard <commit-hash>
sudo docker compose up -d --build
```

---

## Alternative: Direct Deployment (No GitHub)

If you prefer not to use GitHub Actions, use the `deploy.py` script:

```bash
python deploy.py
```

This uploads files directly from your machine via SFTP.

---

## Access URLs

| Service | URL |
|---------|-----|
| Frontend | `http://your-server:3001` |
| API Docs | `http://your-server:8001/api/docs` |
| pgAdmin (optional) | `http://your-server:5050` |

## Default Credentials

- **Username:** `admin`
- **Password:** Set via `ADMIN_PASSWORD` env var

---

## Troubleshooting

**Containers not starting:**
```bash
sudo docker compose logs
```

**Database issues:**
```bash
sudo docker compose down -v  # Wipes data!
sudo docker compose up -d --build
```

**Permission denied:**
```bash
sudo usermod -aG docker $USER
# Log out and back in
```
