# Prompt v2: Fix Issues, Add General LLM Mode & AWS CloudFormation

## Context

This is a follow-up to the initial implementation of the Extremo Ambiente corporate event chatbot. The project is a LangGraph ReAct agent (GPT-4o) with Google Maps tools, email drafting templates, a Next.js chat UI with user authentication, and Docker Compose for deployment.

The initial implementation is solid but has specific issues to fix and two new requirements. **Read all files referenced below before making changes.**

---

## Part 1: Fix Existing Issues

### Issue 1 — Hide the config form from staff users (MEDIUM priority)

**Problem**: `ui/src/providers/Stream.tsx` still shows a technical config form (Deployment URL, Assistant ID, LangSmith API Key) if `NEXT_PUBLIC_API_URL` or `NEXT_PUBLIC_ASSISTANT_ID` env vars are missing. Staff users should never see LangGraph connection details.

**File**: `ui/src/providers/Stream.tsx` (lines 187-287)

**Fix**: Remove the config form entirely. Instead:
- Use hardcoded defaults: API URL = `http://localhost:2024`, Assistant ID = `agent`
- If env vars are set, use those. If not, fall back to defaults silently.
- If the connection fails, show a simple error message ("Service temporarily unavailable. Please try again later.") — not a technical config form.
- Remove the LangSmith API Key input. That should only be configurable via environment variables, not by staff users in the UI.
- The `EALogo` component and imports for `PasswordInput`, `Label`, `Input` related to the config form can be cleaned up if no longer needed.

**Current code to replace** (the `if (!finalApiUrl || !finalAssistantId)` block):
```tsx
// Currently shows a full config form — replace with:
// Silently use defaults, show error toast only on connection failure
```

### Issue 2 — No logout path when config form was shown (LOW priority)

**Problem**: This is fixed automatically by Issue 1 (removing the config form). But also verify that the logout button in `ui/src/components/thread/history/index.tsx` works in all states — both desktop sidebar (line 221-229) and mobile sheet (line 254-268).

**No file changes needed if Issue 1 is properly fixed.**

### Issue 3 — Route optimization uses haversine instead of driving time (LOW priority — acceptable for MVP)

**Problem**: `agent/tools/google_maps.py` `_optimize_stop_order()` (lines 371-406) uses straight-line haversine distance for the nearest-neighbor heuristic. For Portuguese geography (rivers, hills, bridges), this can give suboptimal ordering.

**File**: `agent/tools/google_maps.py`

**Fix**: This is acceptable for the MVP (3-8 stops, greedy heuristic is fine). But add a comment explaining the trade-off:
```python
def _optimize_stop_order(api_key: str, coords: list[tuple[float, float]]) -> list[int]:
    """Find a good ordering for intermediate stops using nearest-neighbor heuristic.

    Uses straight-line (haversine) distance rather than actual driving time to
    avoid O(n^2) API calls. For typical corporate events (3-8 stops in the same
    region), this produces near-optimal results. A full driving-time matrix would
    be more accurate but requires n*(n-1)/2 Routes API calls.
    """
```
Note: the `api_key` parameter is passed but unused — keep it in the signature for future upgrade to driving-time optimization, but add a comment noting this.

### Issue 4 — Hardcoded passwords flagged more clearly (LOW priority)

**Problem**: `ui/src/providers/Auth.tsx` has hardcoded passwords (`extremo2024`) in client-side code. This is fine for a prototype but should be clearly flagged.

**File**: `ui/src/providers/Auth.tsx` (lines 17-25)

**Fix**: Add a prominent comment block:
```typescript
// ⚠️ PROTOTYPE ONLY — hardcoded credentials for demo/staging
// In production, replace with:
//   - AWS Cognito user pool authentication
//   - Or a backend API endpoint that validates credentials against a database
//   - Passwords should NEVER be stored in client-side code
const STAFF_ACCOUNTS: Record<string, string> = {
```

---

## Part 2: General LLM Capability (when tools don't apply)

### Requirement

The chatbot should work as a **general-purpose conversational assistant** when the user's question doesn't require any tools. Right now the system prompt focuses heavily on tool usage. The agent should also be able to:

- Answer general questions about Portugal (geography, culture, weather, customs)
- Help with event planning decisions (best season, group dynamics, team-building theory)
- Discuss business topics (client relationship management, pricing strategy, follow-up timing)
- Help staff with writing tasks beyond emails (social media posts, internal reports, meeting notes)
- Have natural conversation — greet users, handle small talk, be personable
- Answer questions about Extremo Ambiente's services, history, and differentiators
- Help brainstorm creative event ideas and themes

### Implementation

**File**: `agent/prompts.py`

Update the `SYSTEM_PROMPT` to explicitly include a section about general conversation. Add this after the "## What you can do" section (before "## How to use tools"):

```
## General conversation
You are also a knowledgeable general assistant. When the user's question does not
require searching places, calculating routes, or drafting emails, simply answer
directly from your knowledge. You can:
- Answer questions about Portugal: geography, culture, history, weather by season,
  local customs, food and wine regions, transportation, visa requirements
- Provide event planning advice: best seasons for outdoor activities, group size
  considerations, rain contingency plans, team-building activity theory
- Help with business tasks: client communication strategies, pricing frameworks,
  proposal writing tips, follow-up best practices
- Assist with writing beyond emails: social media captions, internal event reports,
  meeting summaries, thank-you notes
- Brainstorm creative event themes and unique activity combinations
- Have natural, friendly conversation — you're a colleague, not just a tool

Only use tools when they genuinely add value (real place data, actual driving times,
structured email templates). For general knowledge questions, answer directly without
invoking any tools.
```

Also update the "## Tone" section to reinforce conversational ability:
```
## Tone
- Warm, helpful, and knowledgeable — like a well-traveled colleague
- You work FOR Extremo Ambiente — refer to it as "we" / "nós"
- Be proactive: suggest ideas, flag potential issues (group too large for a venue,
  travel time too long, etc.)
- Keep responses concise and actionable
- When chatting casually, be personable and engaging — not robotic
- If you don't know something specific, say so honestly and suggest how to find out
```

**File**: `agent/graph.py`

No changes needed — the `create_react_agent` already supports tool-free responses. The LLM will naturally respond without tools when the prompt instructs it to.

---

## Part 3: AWS CloudFormation Template

### Requirement

Create a CloudFormation template that deploys the full stack to AWS. The template should be self-contained and deployable with a single `aws cloudformation deploy` command.

### Architecture

```
Internet
   │
   ▼
┌──────────────────┐
│  Application      │
│  Load Balancer    │  ← Public ALB, ports 80/443
│  (ALB)            │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Frontend│ │Backend │  ← ECS Fargate services
│ :3000  │ │ :8000  │
└────────┘ └───┬────┘
               │
          ┌────┴────┐
          │         │
          ▼         ▼
    ┌──────────┐ ┌───────┐
    │ RDS      │ │ Redis │  ← Private subnets
    │ Postgres │ │ Elasti│
    │ :5432    │ │ Cache │
    └──────────┘ └───────┘
```

### File to create: `infra/cloudformation.yaml`

Create a single CloudFormation YAML template with these resources:

#### Networking
- **VPC** with CIDR `10.0.0.0/16`
- **2 public subnets** (for ALB and NAT Gateway) in different AZs
- **2 private subnets** (for ECS tasks, RDS, ElastiCache) in different AZs
- **Internet Gateway** attached to VPC
- **NAT Gateway** (single, in one public subnet) for private subnet egress
- **Route tables**: public subnets route to IGW, private subnets route to NAT

#### Security Groups
- **ALB SG**: inbound 80, 443 from anywhere; outbound to ECS SG
- **ECS SG**: inbound from ALB SG only (ports 3000, 8000); outbound all
- **RDS SG**: inbound 5432 from ECS SG only
- **Redis SG**: inbound 6379 from ECS SG only

#### Database
- **RDS PostgreSQL 16** (`db.t3.micro` or parameterized):
  - Engine: `postgres`, version `16`
  - Database name: `langgraph`
  - Master username: parameter (default `langgraph`)
  - Master password: parameter (no default, `NoEcho: true`)
  - Private subnets only (DB subnet group)
  - Multi-AZ: false (cost saving for prototype)
  - Storage: 20 GB gp3
  - Deletion protection: false (for easy cleanup)

#### Cache
- **ElastiCache Redis** (single node, `cache.t3.micro`):
  - Engine: `redis`, version `7.x`
  - Private subnets only (cache subnet group)
  - Number of nodes: 1

#### Container Registry
- **2 ECR repositories**: `extremo-backend` and `extremo-frontend`

#### ECS Cluster + Services
- **ECS Cluster** (Fargate)

- **Backend Task Definition**:
  - Image: `!Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/extremo-backend:latest`
  - CPU: 512, Memory: 1024
  - Port: 8000
  - Environment variables:
    - `OPENAI_API_KEY` — from parameter (NoEcho)
    - `GOOGLE_MAPS_API_KEY` — from parameter (NoEcho)
    - `POSTGRES_URI` — constructed from RDS endpoint: `!Sub postgres://${DBUsername}:${DBPassword}@${RDSInstance.Endpoint.Address}:5432/langgraph`
    - `REDIS_URI` — constructed from ElastiCache: `!Sub redis://${RedisCluster.RedisEndpoint.Address}:6379`
    - `LANGCHAIN_TRACING_V2` — parameter (default `true`)
    - `LANGSMITH_API_KEY` — from parameter (NoEcho, optional)
    - `LANGCHAIN_PROJECT` — parameter (default `extremoambiente-a2`)
  - Log group: `/ecs/extremo-backend`

- **Frontend Task Definition**:
  - Image: `!Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/extremo-frontend:latest`
  - CPU: 256, Memory: 512
  - Port: 3000
  - Environment variables:
    - `NEXT_PUBLIC_API_URL` — constructed from ALB DNS: `!Sub http://${ALB.DNSName}`  (backend target group will be on a path-based rule)
    - `NEXT_PUBLIC_ASSISTANT_ID` — `agent`
  - Log group: `/ecs/extremo-frontend`

- **Backend Service**: desired count 1, Fargate, attached to ALB target group (path `/api/*` or host-based)
- **Frontend Service**: desired count 1, Fargate, attached to ALB target group (default rule)

#### Load Balancer
- **Application Load Balancer** (internet-facing, public subnets)
- **Target Group: Backend** — health check `/info`, port 8000
- **Target Group: Frontend** — health check `/`, port 3000
- **Listener (port 80)**:
  - Default action: forward to frontend target group
  - Rule: path pattern `/api/*` forward to backend target group (this matches the Next.js API passthrough pattern)

**Important ALB routing note**: The Next.js frontend proxies API calls through `/api/[..._path]/route.ts` to the LangGraph backend. So the ALB should:
- Route ALL traffic to the frontend by default
- The frontend internally proxies `/api/*` calls to the backend via `NEXT_PUBLIC_API_URL`
- Alternative: route `/api/*` directly to backend at the ALB level (simpler, less Next.js overhead)

Choose the simpler approach: route everything to frontend, let Next.js proxy handle backend calls. Set `NEXT_PUBLIC_API_URL` to point to the backend target group's internal URL or the ALB with a path prefix.

Actually, the cleanest approach for this architecture:
- Frontend `NEXT_PUBLIC_API_URL` should point to the ALB URL with a `/backend` path prefix
- ALB listener rules: `/backend/*` -> backend target group (with path stripping if supported, or without — adjust the Next.js proxy to handle the prefix)

Simplest: just use two separate ports or the frontend's built-in proxy. Set `NEXT_PUBLIC_API_URL` to an internal service discovery URL or the ALB DNS. Since the Next.js API route handler (`/api/[..._path]`) proxies to `LANGGRAPH_API_URL`, set that as an environment variable pointing to the backend service via Cloud Map or direct ECS service connect.

**Recommended approach**:
- Use **AWS Cloud Map** (service discovery) for internal backend communication
- Frontend env: `LANGGRAPH_API_URL=http://backend.extremo.local:8000` (internal DNS)
- ALB only exposes the frontend on port 80
- The Next.js API route proxies requests internally to the backend

#### CloudWatch Logs
- Log groups for both ECS tasks with 30-day retention

#### IAM
- **ECS Task Execution Role**: allows pulling from ECR, writing to CloudWatch Logs
- **ECS Task Role**: minimal (no extra AWS service access needed)

### Parameters

```yaml
Parameters:
  Environment:
    Type: String
    Default: production
    AllowedValues: [production, staging]
  DBUsername:
    Type: String
    Default: langgraph
  DBPassword:
    Type: String
    NoEcho: true
    MinLength: 8
  OpenAIApiKey:
    Type: String
    NoEcho: true
  GoogleMapsApiKey:
    Type: String
    NoEcho: true
  LangSmithApiKey:
    Type: String
    NoEcho: true
    Default: ""
  LangChainProject:
    Type: String
    Default: extremoambiente-a2
```

### Outputs

```yaml
Outputs:
  ApplicationURL:
    Description: URL to access the chatbot
    Value: !Sub http://${ALB.DNSName}
  BackendURL:
    Description: Backend API URL (internal)
    Value: !Sub http://${ALB.DNSName}/api
  RDSEndpoint:
    Description: RDS PostgreSQL endpoint
    Value: !GetAtt RDSInstance.Endpoint.Address
  ECRBackendRepository:
    Description: ECR repository for backend image
    Value: !GetAtt BackendECR.RepositoryUri
  ECRFrontendRepository:
    Description: ECR repository for frontend image
    Value: !GetAtt FrontendECR.RepositoryUri
```

### Also create: `infra/deploy.sh`

A deployment helper script that:
1. Builds and pushes Docker images to ECR
2. Deploys/updates the CloudFormation stack
3. Waits for the stack to complete

```bash
#!/bin/bash
# Usage: ./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed and running
#   - .env file with OPENAI_API_KEY, GOOGLE_MAPS_API_KEY, etc.
```

The script should:
- Accept `--region`, `--stack`, and `--profile` flags
- Read secrets from `.env` file
- Build both Docker images (backend + frontend)
- Create ECR repos if they don't exist
- Push images to ECR
- Deploy CloudFormation with parameter overrides
- Print the application URL when done

---

## Part 4: Update CLAUDE.md and .env.example

### `CLAUDE.md`

Add these sections:
- **General LLM capability**: note that the chatbot works as a general assistant when tools aren't needed
- **AWS Deployment**: reference `infra/cloudformation.yaml` and `infra/deploy.sh`, list the AWS resources created
- **Infrastructure diagram** (ASCII art of the AWS architecture)
- Update the project structure to include `infra/` directory

### `.env.example`

Add comments explaining which vars are needed for local dev vs AWS deployment:
```bash
# === Local Development ===
OPENAI_API_KEY=sk-...
GOOGLE_MAPS_API_KEY=...

# === LangSmith (optional) ===
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=extremoambiente-a2

# === Production (AWS) — set these when deploying to AWS ===
# These are handled by CloudFormation parameters, not .env
# POSTGRES_URI=postgres://langgraph:PASSWORD@rds-endpoint:5432/langgraph
# REDIS_URI=redis://elasticache-endpoint:6379

# === Frontend (set in docker-compose or CloudFormation) ===
# NEXT_PUBLIC_API_URL=http://localhost:2024
# NEXT_PUBLIC_ASSISTANT_ID=agent
```

---

## Summary of deliverables

| # | What | Files |
|---|------|-------|
| 1 | Remove config form from Stream.tsx | `ui/src/providers/Stream.tsx` |
| 2 | Add comment to route optimizer | `agent/tools/google_maps.py` |
| 3 | Flag hardcoded passwords | `ui/src/providers/Auth.tsx` |
| 4 | Add general LLM conversation capability | `agent/prompts.py` |
| 5 | Create CloudFormation template | `infra/cloudformation.yaml` (new) |
| 6 | Create deployment script | `infra/deploy.sh` (new) |
| 7 | Update docs | `CLAUDE.md`, `.env.example` |

**Order of implementation**: 4 (prompts) -> 1 (Stream.tsx) -> 2,3 (minor fixes) -> 5 (CloudFormation) -> 6 (deploy script) -> 7 (docs)

Start by reading all referenced files to understand the current state. Ask me if anything is unclear.
