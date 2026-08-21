# Deploying AFM Explorer

This document describes the production deployment currently used by AFM Explorer.

The application is deployed on an AWS EC2 instance using Docker Compose. nginx acts as the internal reverse proxy, Cloudflare Tunnel provides the public HTTPS endpoint, and GitHub Actions provides CI/CD.

**Production URL:** `https://afm.kashishmendiratta.com`

## Architecture

```text
Developer machine
      |
      | git push
      v
GitHub
      |
      | CI: tests, lint, Docker build
      |
      | CD after successful CI
      v
GitHub Actions
      |
      | OIDC
      v
AWS IAM
      |
      | temporary AWS credentials
      |
      | temporarily allows SSH from
      | the current GitHub runner IP
      v
AWS EC2
      |
      | Docker Compose
      v
nginx
   /       \
Streamlit   FastAPI
Frontend    Backend
      |
      v
Cloudflare Tunnel
      |
      | HTTPS
      v
afm.kashishmendiratta.com
```

## 1. AWS EC2

AFM Explorer currently runs on an Ubuntu EC2 instance.

Current setup:

* Ubuntu Server 26.04 LTS
* x86-64 architecture
* `t3.micro`
* gp3 EBS root volume
* Region: `eu-north-1` (Stockholm)

AWS Free Tier rules depend on when the AWS account was created. Do not assume that an EC2 instance will remain free indefinitely. Check the current AWS billing and Free Tier information before creating an instance.

### Security group

The EC2 instance is not directly exposed as a public web server.

Inbound access is restricted to:

```text
SSH / TCP / 22 / administrator public IP only
```

The following ports are not publicly exposed:

```text
80
443
8000
8501
```

Port `8000` is used internally by FastAPI and port `8501` by Streamlit.

nginx listens internally on port `80`.

Cloudflare Tunnel connects outbound from the EC2 instance to Cloudflare, so public inbound HTTP/HTTPS access to EC2 is not required.

## 2. Connecting to EC2 manually

The administrator connects using the EC2 SSH key:

```bash
ssh -i ~/.ssh/afm-explorer-key.pem ubuntu@<EC2_PUBLIC_IPV4>
```

The EC2 public IPv4 address is available from:

**AWS Console → EC2 → Instances → afm-explorer → Details**

The normal EC2 public IPv4 address may change if the instance is stopped and started unless an Elastic IP or another stable access mechanism is configured.

## 3. Repository setup on EC2

The repository is cloned onto the EC2 instance:

```bash
git clone https://github.com/KashishMendiratta/afm-explorer.git
cd afm-explorer
```

The production deployment uses:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --build
```

Check container status with:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps
```

Check logs with:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs
```

## 4. Production Docker topology

The production Compose configuration runs:

* FastAPI backend
* Streamlit frontend
* nginx reverse proxy

nginx is the internal entry point.

Routing:

```text
/       → Streamlit frontend
/api/   → FastAPI backend
```

The backend and frontend communicate over the Docker network rather than being exposed directly to the public Internet.

## 5. Cloudflare Tunnel

The domain `kashishmendiratta.com` is managed through Cloudflare.

AFM Explorer uses:

```text
afm.kashishmendiratta.com
```

A Cloudflare Tunnel named:

```text
afm-explorer
```

runs on the EC2 instance using `cloudflared`.

The published application route is:

```text
Hostname:
afm.kashishmendiratta.com

Service URL:
http://localhost:80
```

This means:

```text
Browser
   |
   | HTTPS
   v
Cloudflare
   |
   | Cloudflare Tunnel
   v
cloudflared on EC2
   |
   v
http://localhost:80
   |
   v
nginx
  / \
 /   \
Frontend FastAPI
```

### Check cloudflared

On EC2:

```bash
sudo systemctl status cloudflared
```

Recent logs:

```bash
sudo journalctl -u cloudflared --no-pager -n 50
```

The application can be checked externally using:

```text
https://afm.kashishmendiratta.com
```

Backend health check:

```text
https://afm.kashishmendiratta.com/api/health
```

## 6. Continuous Integration

CI is configured in:

```text
.github/workflows/ci.yml
```

It runs automatically on GitHub pushes and pull requests.

The CI pipeline performs:

1. Repository checkout
2. Python setup
3. Dependency installation
4. Ruff linting
5. `afm_core` tests
6. ML package tests
7. Backend tests
8. MCP server tests
9. Frontend Python syntax checks
10. Production Docker Compose configuration validation
11. Docker image build checks

Deployment should not run unless CI succeeds.

## 7. Continuous Deployment

CD is configured in:

```text
.github/workflows/cd.yml
```

Deployment occurs after successful CI on the `main` branch.

The deployment flow is:

```text
git push main
      |
      v
GitHub CI
      |
      | success
      v
GitHub CD
      |
      | OIDC
      v
AWS IAM
      |
      | short-lived AWS credentials
      v
temporary SSH rule
      |
      v
EC2
      |
      | update repository
      | rebuild Docker stack
      v
live deployment
```

## 8. GitHub OIDC authentication

GitHub Actions does not store a permanent AWS access key and secret.

Instead, GitHub authenticates to AWS using OpenID Connect (OIDC).

AWS identity provider:

```text
https://token.actions.githubusercontent.com
```

Audience:

```text
sts.amazonaws.com
```

IAM role:

```text
AFMExplorerGitHubDeployRole
```

The role trust policy is restricted to:

```text
GitHub owner:
KashishMendiratta

Repository:
afm-explorer

Branch:
main
```

The workflow uses:

```yaml
permissions:
  id-token: write
  contents: read
```

GitHub exchanges its OIDC identity token for temporary AWS credentials when the deployment runs.

## 9. Least-privilege EC2 permissions

The GitHub deployment IAM role is intentionally not given:

```text
AdministratorAccess
AmazonEC2FullAccess
```

Its EC2 permissions are limited to:

```text
ec2:AuthorizeSecurityGroupIngress
ec2:RevokeSecurityGroupIngress
```

and only for the security group attached to the AFM Explorer EC2 instance.

This allows the CD workflow to temporarily permit SSH from the current GitHub Actions runner.

## 10. Temporary GitHub Actions SSH access

The EC2 SSH port remains restricted rather than being publicly available at:

```text
0.0.0.0/0
```

During deployment:

1. GitHub determines the current runner's public IPv4 address.
2. AWS temporarily authorizes:

```text
TCP / 22 / <GITHUB_RUNNER_IP>/32
```

3. GitHub connects to EC2 using the deployment SSH key.
4. Deployment is performed.
5. The temporary security-group rule is revoked.

The rule removal runs even when deployment fails.

The administrator's own SSH rule remains separate.

## 11. GitHub repository configuration

Repository variables used by the CD workflow include:

```text
EC2_HOST
EC2_SECURITY_GROUP_ID
AWS_DEPLOY_ROLE_ARN
```

The private deployment SSH key is stored as a GitHub Actions repository secret:

```text
EC2_DEPLOY_KEY
```

Never commit private keys, Cloudflare tunnel tokens, AWS credentials, or other secrets to the repository.

## 12. Deployment commands

During deployment, the EC2 host updates the source code and rebuilds the production stack.

Typical commands are:

```bash
cd ~/afm-explorer

git fetch origin main
git reset --hard origin/main

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --build

docker image prune -f
```

After deployment, GitHub checks:

```text
https://afm.kashishmendiratta.com/api/health
```

to verify that the application is reachable.

## 13. Manual deployment fallback

If automated deployment fails, SSH into EC2 manually:

```bash
ssh -i ~/.ssh/afm-explorer-key.pem ubuntu@<EC2_PUBLIC_IPV4>
```

Then:

```bash
cd ~/afm-explorer

git fetch origin main
git reset --hard origin/main

docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --build
```

Check status:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps
```

Check logs:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs --tail=100
```

## 14. Security notes

Current deployment choices intentionally include:

* SSH restricted to known IPs.
* FastAPI and Streamlit ports are not publicly exposed.
* nginx is the internal reverse proxy.
* Cloudflare Tunnel provides the external HTTPS path.
* No inbound HTTP or HTTPS access is required on EC2.
* AWS access from GitHub uses OIDC and short-lived credentials.
* The GitHub IAM role follows least privilege.
* The GitHub deployment SSH key is separate from the administrator EC2 key.
* GitHub runner SSH access is temporary and removed after deployment.
* Secrets are stored outside the repository.

## 15. Current production endpoints

AFM Explorer:

```text
https://afm.kashishmendiratta.com
```

Health endpoint:

```text
https://afm.kashishmendiratta.com/api/health
```

## 16. Useful troubleshooting commands

### Check running containers

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps
```

### View recent Docker logs

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs --tail=100
```

### Follow Docker logs live

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  logs -f
```

### Test nginx from inside EC2

```bash
curl -I http://localhost
```

### Test FastAPI through nginx

```bash
curl http://localhost/api/health
```

### Check the Cloudflare Tunnel service

```bash
sudo systemctl status cloudflared
```

### View Cloudflare Tunnel logs

```bash
sudo journalctl -u cloudflared --no-pager -n 50
```

### Restart the tunnel if required

```bash
sudo systemctl restart cloudflared
```

### Check Docker service status

```bash
sudo systemctl status docker
```

## 17. Deployment lifecycle

The normal development and deployment lifecycle is:

```text
Edit code locally
      |
      v
Run local tests
      |
      v
Commit changes
      |
      v
git push origin main
      |
      v
GitHub Actions CI
      |
      | tests pass
      v
GitHub Actions CD
      |
      v
AWS EC2 deployment
      |
      v
Docker containers rebuilt
      |
      v
Cloudflare Tunnel
      |
      v
https://afm.kashishmendiratta.com
```

This means normal application updates should not require manually logging into the EC2 server.
