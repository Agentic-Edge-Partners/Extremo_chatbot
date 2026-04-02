# AWS Deployment Instructions — Extremo Ambiente Chatbot

Complete guide to deploy the Extremo Ambiente corporate event chatbot on AWS.

Two deployment options:

| Option | Script | Cost | Best for |
|--------|--------|------|----------|
| **EC2 (simple)** | `./infra/deploy-ec2.sh` | ~$22/month | Prototypes, demos |
| **ECS Fargate (full)** | `./infra/deploy.sh` | ~$107/month | Production |

---

## Option A — EC2 Deployment (~$22/month)

Single EC2 instance running all services via Docker Compose. No NAT Gateway, no managed DB — everything on one `t3.small`.

### Prerequisites

Same as Option B (AWS CLI, Docker, API keys) — see below.  
Additionally: an **EC2 key pair** must exist in your target region.

```bash
# Create a key pair if you don't have one
aws ec2 create-key-pair --key-name extremo-key --region eu-west-1 \
  --query KeyMaterial --output text > extremo-key.pem
chmod 400 extremo-key.pem
```

### Deploy

```bash
# Prepare .env (same as Option B — Step 1)
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and GOOGLE_MAPS_API_KEY

chmod +x infra/deploy-ec2.sh
./infra/deploy-ec2.sh --region eu-west-1 --key-pair extremo-key --git-repo https://github.com/<YOUR_USER>/Extremo_chatbot.git
```

The script deploys a CloudFormation stack that:
1. Creates a VPC + public subnet + security group
2. Launches a `t3.small` EC2 instance with an Elastic IP
3. The instance auto-installs Docker, clones the repo, and starts all services via `docker compose up --build`

**Wait 8-12 minutes** after the script completes — the instance is still building Docker images on first boot.

Check progress:
```bash
ssh -i extremo-key.pem ubuntu@<PUBLIC_IP> 'tail -f /var/log/user-data.log'
```

Access the app at `http://<PUBLIC_IP>:3000`

### Update after code changes

The Elastic IP never changes, so store it in `.env` once after first deploy:
```bash
# One-time: save the public IP to .env (get it from CloudFormation output or the console)
echo 'PUBLIC_IP=<YOUR_ELASTIC_IP>' >> ~/app/.env
```

Then for every redeploy:
```bash
ssh -i extremo-key.pem ubuntu@<PUBLIC_IP>
cd ~/app
git pull
source .env
NEXT_PUBLIC_API_URL="http://$PUBLIC_IP:3000/api" \
LANGGRAPH_API_URL="http://backend:8000" \
docker compose up -d --build
```

`LANGGRAPH_API_URL=http://backend:8000` is always the same — it's Docker's internal DNS name for the backend container and never changes.

`NEXT_PUBLIC_API_URL` must be passed on every `--build` because it's baked into the Next.js image at build time.

### Tear down

```bash
aws cloudformation delete-stack --stack-name extremo-ec2 --region eu-west-1
```

---

## Option B — ECS Fargate Deployment (~$107/month)

Full production-grade setup: ECS Fargate, RDS PostgreSQL, ElastiCache Redis, ALB, Cloud Map.

## Architecture Overview

```
                         Internet
                            |
                            v
                    +---------------+
                    |  Application  |
                    |  Load Balancer|   <-- Public, port 80
                    |  (ALB)        |
                    +-------+-------+
                            |
                            v
                     +------------+
                     |  Frontend  |        <-- ECS Fargate (private subnet)
                     |  Next.js   |
                     |  :3000     |
                     +------+-----+
                            |
                            | Cloud Map (internal DNS)
                            | backend.extremo.local:8000
                            v
                     +------------+
                     |  Backend   |        <-- ECS Fargate (private subnet)
                     |  LangGraph |            NOT exposed via ALB
                     |  :8000     |
                     +------+-----+
                            |
                  +---------+---------+
                  |                   |
                  v                   v
           +------------+      +------------+
           |    RDS     |      | ElastiCache|   <-- Private subnets
           | PostgreSQL |      |   Redis    |
           |   :5432    |      |   :6379    |
           +------------+      +------------+
```

**Traffic flow:**
1. User opens `http://<ALB-DNS>` in browser
2. ALB routes **all traffic** to frontend (Next.js) — the backend is **not** exposed via ALB
3. Browser-side API calls hit `/api/*` (relative URL, baked at build time)
4. Next.js server-side API route handler proxies `/api/*` to the backend via Cloud Map (`backend.extremo.local:8000`)
5. Backend connects to RDS (thread/checkpoint storage) and Redis (cache)

**All containers run in private subnets.** Only the ALB is public. The backend is **internal-only** — reachable only via Cloud Map service discovery within the VPC.

---

## Prerequisites

Before starting, make sure you have:

### 1. AWS Account & CLI

```bash
# Install AWS CLI v2
# macOS:
brew install awscli

# Verify installation
aws --version

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (eu-west-1), Output format (json)
```

If you use named profiles:
```bash
aws configure --profile extremo
# Then use --profile extremo with all commands (or pass --profile to deploy.sh)
```

### 2. Docker

```bash
# macOS:
brew install --cask docker
# Then open Docker Desktop and ensure it's running

# Verify:
docker --version
docker compose version
```

### 3. API Keys

You need these keys ready:

| Key | Where to get it | Required |
|-----|-----------------|----------|
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys | Yes |
| `GOOGLE_MAPS_API_KEY` | https://console.cloud.google.com/apis/credentials | Yes |
| `LANGSMITH_API_KEY` | https://smith.langchain.com/settings | No (enables tracing) |

**Google Maps API key** must have these APIs enabled in Google Cloud Console:
- Places API (New)
- Routes API
- Geocoding API

### 4. IAM Permissions

The AWS user/role running the deployment needs these permissions:
- `cloudformation:*` (create/update/delete stacks)
- `ecs:*` (clusters, services, task definitions)
- `ecr:*` (repositories, push images)
- `ec2:*` (VPC, subnets, security groups, NAT, EIP)
- `elasticloadbalancingv2:*` (ALB, target groups, listeners)
- `rds:*` (database instances, subnet groups)
- `elasticache:*` (cache clusters, subnet groups)
- `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PassRole` (ECS execution/task roles)
- `logs:*` (CloudWatch log groups)
- `servicediscovery:*` (Cloud Map)
- `sts:GetCallerIdentity`

Or simply use `AdministratorAccess` for a prototype deployment.

---

## Step-by-Step Deployment

### Step 1: Prepare Environment File

From the project root, create your `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```bash
# === Required ===
OPENAI_API_KEY=sk-proj-your-actual-key-here
GOOGLE_MAPS_API_KEY=AIzaSy-your-actual-key-here

# === Optional (enables LangSmith tracing) ===
LANGSMITH_API_KEY=lsv2_pt_your-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=extremoambiente-a2
```

### Step 2: Set a Database Password

Either add it to `.env`:
```bash
echo 'DB_PASSWORD=YourSecurePassword123' >> .env
```

Or let the deploy script generate a random one. The script will **print the generated password** with a prominent banner — **copy it immediately** and add it to your `.env` for future deploys.

### Step 3: Make the Deploy Script Executable

```bash
chmod +x infra/deploy.sh
```

### Step 4: Run the Deployment

**Default region (eu-west-1, Ireland):**
```bash
./infra/deploy.sh
```

**Custom region and stack name:**
```bash
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot
```

**With a named AWS profile:**
```bash
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot --profile extremo
```

**Custom .env file:**
```bash
./infra/deploy.sh --env-file .env.production
```

### What the script does (in order):

1. Loads your `.env` and validates required keys
2. Logs into AWS ECR (container registry)
3. Creates ECR repositories (`extremo-backend`, `extremo-frontend`) if they don't exist
4. Builds the **backend** Docker image and pushes to ECR
5. Builds the **frontend** Docker image (with `NEXT_PUBLIC_API_URL=/api`) and pushes to ECR
6. Deploys the **CloudFormation stack** (`infra/cloudformation.yaml`) with your parameters
7. Waits for the stack to finish creating/updating (exits with error if deployment fails)
8. Prints the **Application URL** and all stack outputs

### Step 5: Wait for Deployment

First-time deployment takes **15-20 minutes** (RDS and NAT Gateway are the slowest resources). The script will wait and print progress.

If you want to monitor in the AWS Console:
- Go to **CloudFormation** > Stacks > `extremo-chatbot`
- Watch the **Events** tab for resource creation progress

### Step 6: Access the Application

When the script completes, it prints:

```
=========================================
  Deployment Complete!
=========================================

Application URL: http://extremo-production-alb-XXXXXXXXX.eu-west-1.elb.amazonaws.com
```

Open that URL in your browser. You should see the login screen.

**Default staff accounts:**

| Username | Password |
|----------|----------|
| admin | extremo2024 |
| pedro | extremo2024 |
| joana | extremo2024 |
| miguel | extremo2024 |
| ana | extremo2024 |

---

## Updating the Application

After making code changes, redeploy with the same command:

```bash
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot
```

The script rebuilds images, pushes them, and updates the CloudFormation stack. ECS will perform a **rolling update** — zero downtime.

**Important:** Use the same `DB_PASSWORD` as the initial deployment. If you didn't save it, set one explicitly in `.env` before the first deploy.

To force ECS to pull the new images (if only code changed, not infrastructure):

```bash
# Force new deployment for backend
aws ecs update-service \
  --cluster extremo-production \
  --service extremo-production-backend \
  --force-new-deployment \
  --region eu-west-1

# Force new deployment for frontend
aws ecs update-service \
  --cluster extremo-production \
  --service extremo-production-frontend \
  --force-new-deployment \
  --region eu-west-1
```

---

## AWS Resources Created

The CloudFormation stack creates these resources:

| Resource | Type | Details |
|----------|------|---------|
| **VPC** | `10.0.0.0/16` | Dedicated network for the application |
| **Public Subnets** (x2) | `10.0.1.0/24`, `10.0.2.0/24` | ALB and NAT Gateway (2 AZs) |
| **Private Subnets** (x2) | `10.0.10.0/24`, `10.0.11.0/24` | ECS, RDS, Redis (2 AZs) |
| **Internet Gateway** | | Public internet access for ALB |
| **NAT Gateway** | Single | Private subnet egress (ECS pulling images, API calls) |
| **ALB** | Internet-facing | Routes traffic to frontend only (backend is internal via Cloud Map) |
| **ECS Cluster** | Fargate | Serverless containers |
| **Backend Service** | 512 CPU / 1024 MB | LangGraph API server |
| **Frontend Service** | 256 CPU / 512 MB | Next.js chat UI |
| **RDS PostgreSQL 16** | `db.t3.micro`, 20 GB gp3 | Thread and checkpoint storage |
| **ElastiCache Redis 7** | `cache.t3.micro` | LangGraph server cache |
| **ECR Repositories** (x2) | | Backend and frontend Docker images |
| **Cloud Map** | `extremo.local` | Internal DNS for backend service discovery |
| **CloudWatch Logs** (x2) | 30-day retention | Backend and frontend container logs |
| **Security Groups** (x4) | | ALB, ECS, RDS, Redis (least-privilege) |
| **IAM Roles** (x2) | | ECS task execution and task roles |

### Estimated Monthly Cost (eu-west-1)

| Resource | Estimated Cost |
|----------|---------------|
| NAT Gateway | ~$35/month + data |
| ALB | ~$18/month + data |
| ECS Fargate (2 tasks) | ~$25/month |
| RDS db.t3.micro | ~$15/month |
| ElastiCache cache.t3.micro | ~$12/month |
| ECR (storage) | ~$1/month |
| CloudWatch Logs | ~$1/month |
| **Total** | **~$107/month** |

*Costs vary by usage. NAT Gateway is the largest fixed cost — for production, consider VPC endpoints for ECR/CloudWatch to reduce NAT traffic.*

---

## Monitoring & Troubleshooting

### View Container Logs

**Backend logs:**
```bash
aws logs tail /ecs/extremo-backend --follow --region eu-west-1
```

**Frontend logs:**
```bash
aws logs tail /ecs/extremo-frontend --follow --region eu-west-1
```

### Check ECS Service Status

```bash
# List services
aws ecs list-services --cluster extremo-production --region eu-west-1

# Describe backend service (check desired vs running count)
aws ecs describe-services \
  --cluster extremo-production \
  --services extremo-production-backend \
  --region eu-west-1 \
  --query 'services[0].{desired:desiredCount,running:runningCount,status:status,events:events[:3]}'
```

### Check Target Group Health

```bash
# Get frontend target group ARN
aws elbv2 describe-target-groups \
  --region eu-west-1 \
  --query 'TargetGroups[?starts_with(TargetGroupName,`extremo`)].{Name:TargetGroupName,ARN:TargetGroupArn}' \
  --output table

# Check health of targets (replace ARN)
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region eu-west-1
```

### Common Issues

#### 1. ECS tasks keep restarting
**Symptom:** Running count is 0, events show "task stopped"
**Fix:** Check logs for the failing container:
```bash
aws logs tail /ecs/extremo-backend --since 10m --region eu-west-1
```
Common causes:
- Missing or invalid `OPENAI_API_KEY` or `GOOGLE_MAPS_API_KEY`
- RDS not yet available (wait a few minutes after initial deploy)
- Container image not found in ECR (re-run `deploy.sh`)

#### 2. ALB returns 502 Bad Gateway
**Symptom:** Browser shows 502 error
**Fix:** The ECS tasks haven't started yet or are failing health checks. Wait 2-3 minutes after deployment. If it persists, check ECS service events and container logs.

#### 3. "Service temporarily unavailable" in the UI
**Symptom:** Login works but chat shows error toast
**Fix:** The frontend can't reach the backend. Check:
- Backend ECS service is running (`describe-services`)
- Cloud Map DNS is resolving (`backend.extremo.local`)
- Frontend target group health check passes (`/` returns 200)

#### 4. Thread history is empty
**Symptom:** No past conversations shown
**Fix:** Check that RDS is accessible from ECS:
- RDS security group allows port 5432 from ECS security group
- `POSTGRES_URI` environment variable is correctly set in backend task definition
- Check backend logs for database connection errors

#### 5. Google Maps tools return errors
**Symptom:** Place search or route tools fail
**Fix:** Verify your Google Maps API key has these APIs enabled:
- Places API (New) — not the legacy Places API
- Routes API — not the legacy Directions API
- Geocoding API

---

## Connecting to RDS Directly (Debugging)

RDS is in a private subnet, so you can't connect directly. Options:

### Option A: ECS Exec (recommended)
```bash
# Enable ECS Exec on the backend service (one-time)
aws ecs update-service \
  --cluster extremo-production \
  --service extremo-production-backend \
  --enable-execute-command \
  --region eu-west-1

# Wait for a new task to start, then exec into it
TASK_ID=$(aws ecs list-tasks --cluster extremo-production --service-name extremo-production-backend --region eu-west-1 --query 'taskArns[0]' --output text | rev | cut -d'/' -f1 | rev)

aws ecs execute-command \
  --cluster extremo-production \
  --task $TASK_ID \
  --container backend \
  --interactive \
  --command "/bin/sh" \
  --region eu-west-1

# Inside the container, connect to PostgreSQL:
# python -c "import os; print(os.environ['POSTGRES_URI'])"
```

### Option B: SSH Tunnel via a Bastion Host
Not set up by default. Add an EC2 bastion in a public subnet if needed.

---

## Tearing Down

To delete all AWS resources:

```bash
aws cloudformation delete-stack \
  --stack-name extremo-chatbot \
  --region eu-west-1
```

**This deletes everything**: VPC, ECS, ALB, RDS (including data), Redis, ECR repos, and all networking. There is no deletion protection on any resource.

Wait for deletion to complete:
```bash
aws cloudformation wait stack-delete-complete \
  --stack-name extremo-chatbot \
  --region eu-west-1
```

**Note:** The Elastic IP for the NAT Gateway may take a few minutes to release. If the stack deletion gets stuck, check the CloudFormation Events tab for the blocking resource.

To delete just the ECR images (if you want to keep the stack but clean storage):
```bash
aws ecr batch-delete-image \
  --repository-name extremo-backend \
  --image-ids imageTag=latest \
  --region eu-west-1

aws ecr batch-delete-image \
  --repository-name extremo-frontend \
  --image-ids imageTag=latest \
  --region eu-west-1
```

---

## Security Notes

- **API keys** are passed as CloudFormation parameters with `NoEcho: true` — they're masked in the console and CLI output, but stored in plaintext in the ECS task definition environment variables. For production, use **AWS Secrets Manager** + ECS secrets references instead.
- **Database password** is also a CloudFormation parameter. Same recommendation: use Secrets Manager for production.
- **Staff passwords** are hardcoded in the frontend code (`ui/src/providers/Auth.tsx`). For production, replace with **AWS Cognito** or a backend auth API.
- **ALB is HTTP only** (port 80). For production, add an **ACM certificate** and configure HTTPS (port 443) on the ALB listener. Then redirect port 80 to 443.
- **RDS and Redis** are not encrypted at rest by default. Add `StorageEncrypted: true` to the RDS resource and `TransitEncryptionEnabled: true` to Redis for production.

---

## Quick Reference

```bash
# Deploy (first time or updates)
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot

# View application URL
aws cloudformation describe-stacks \
  --stack-name extremo-chatbot \
  --region eu-west-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
  --output text

# View all outputs
aws cloudformation describe-stacks \
  --stack-name extremo-chatbot \
  --region eu-west-1 \
  --query 'Stacks[0].Outputs' \
  --output table

# Tail backend logs
aws logs tail /ecs/extremo-backend --follow --region eu-west-1

# Force redeploy after code changes
aws ecs update-service --cluster extremo-production --service extremo-production-backend --force-new-deployment --region eu-west-1
aws ecs update-service --cluster extremo-production --service extremo-production-frontend --force-new-deployment --region eu-west-1

# Tear down everything
aws cloudformation delete-stack --stack-name extremo-chatbot --region eu-west-1
```
