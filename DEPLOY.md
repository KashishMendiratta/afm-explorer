# Deploying AFM Explorer

This walks through getting the stack live on a free AWS EC2 instance, with
HTTPS via Cloudflare Tunnel and automatic deploys from GitHub Actions.
Everything here targets **cost $0** for the first 12 months of an AWS
account; see the honesty note at the end for what happens after that.

## 1. Launch the EC2 instance

1. In the AWS Console, launch an EC2 instance:
   - AMI: **Ubuntu Server 22.04 LTS**
   - Instance type: **t3.micro** (covered by the AWS free tier: 750
     hrs/month for the first 12 months)
   - Storage: default 8-30GB gp3 is plenty
   - Key pair: create a new one, download the `.pem` file, keep it safe —
     it's the only way to SSH in
2. Security group: allow inbound
   - **22 (SSH)** — restrict the source to *your IP only*, not `0.0.0.0/0`
   - **80 (HTTP)** — `0.0.0.0/0` (nginx will serve the app here)
   - Leave 8000/8501 closed — nginx is the only public entry point; the
     backend and frontend containers aren't published outside the Docker
     network in the prod compose file
3. Note the instance's public IP once it's running.

## 2. Bootstrap the instance

SSH in and run the setup script (installs Docker, clones the repo, brings
up the production stack):

```bash
ssh -i your-key.pem ubuntu@<instance-public-ip>
export REPO_URL=https://github.com/<you>/afm-explorer.git
curl -fsSL https://raw.githubusercontent.com/<you>/afm-explorer/main/deploy/ec2-setup.sh | bash
```

(Or `git clone` the repo yourself and run `bash deploy/ec2-setup.sh` locally
on the instance — same effect, useful if the repo is private.)

At this point `http://<instance-public-ip>/` should show the AFM Explorer
frontend, proxied through nginx.

## 3. HTTPS via Cloudflare Tunnel (free, no port-80 ACME dance)

1. Add your domain to Cloudflare (free plan) if you haven't already, or use
   a subdomain you control.
2. On the EC2 instance: `curl -fsSL https://pkg.cloudflare.com/... | ...`
   per [Cloudflare's cloudflared install docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/),
   then:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create afm-explorer
   cloudflared tunnel route dns afm-explorer afm.yourdomain.com
   cloudflared tunnel run --url http://localhost:80 afm-explorer
   ```
3. Run `cloudflared` as a systemd service (`cloudflared service install`)
   so it survives reboots. Cloudflare terminates TLS for you — no certbot,
   no renewal cron, and it keeps working even if the instance's IP changes.

If you'd rather use classic certbot + a custom domain pointed straight at
the instance, that works too — nginx is already listening on 80, so
`certbot --nginx` is a standard drop-in; Cloudflare Tunnel is just less
setup and no DNS/firewall juggling.

## 4. CI/CD (GitHub Actions)

`.github/workflows/ci.yml` runs tests + lint + a Docker build check on
every push/PR. `.github/workflows/cd.yml` deploys to EC2 over SSH after CI
passes on `main`. Set these repo secrets (Settings → Secrets and variables
→ Actions):

| Secret | Value |
|---|---|
| `EC2_HOST` | the instance's public IP or DNS |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | the **private** key matching a public key already installed on the instance (paste the full `.pem` contents) |

Once set, every merge to `main` re-deploys automatically (`git pull` +
`docker compose up -d --build` on the instance).

## 5. Cost honesty

EC2's free tier (750 hrs/month, enough for one instance running 24/7) only
applies for **12 months from AWS account creation**. After that, a
`t3.micro` costs roughly **$7-8/month**. Two ways to stay at $0
indefinitely if that matters more to you than the AWS name on your CV:

- **Stop the instance between demos** (EC2 charges are per running-hour;
  a stopped instance costs only its EBS storage, a few cents/month) and
  start it before an interview/demo.
- **Migrate to Oracle Cloud's Always Free tier** (perpetually free ARM
  Ampere VMs) once the AWS free year is up — same `docker compose` setup
  works unchanged, just a different host. Lower resume recognition than
  AWS, which is why it's the fallback here and not the headline.

**Azure alternative:** if you already have Azure credits (e.g. a student
or free account), a `B1S` burstable VM under Azure's free tier works
identically — same Ubuntu + Docker + compose steps, same nginx config,
just launched through the Azure Portal instead of the EC2 console.
