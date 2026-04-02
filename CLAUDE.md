# CLAUDE.md — ExtremoAmbiente AI Assistant

## Project Overview

**Assignment 2** for PDAI (Prototyping Products with AI) at ESADE MiBA.
Built on top of the ExtremoAmbiente-A1 Streamlit prototype (corporate event quoting tool for a Portuguese adventure tourism company).

A **conversational AI assistant** for Extremo Ambiente staff, powered by a single LangGraph ReAct agent with specialized tools. Unlike a rigid multi-agent pipeline, this is a **flexible chat interface** — the user drives the conversation and invokes tools on demand, like a ChatGPT tailored for adventure tourism operations.

Features user authentication, per-event conversation persistence, enhanced email templates, smart place search, route optimization with pickup/drop-off support, and general conversational LLM capability.

**Student**: Pedro Resende

---

## Architecture

### Single Agent + Tools (LangGraph ReAct)

```
  Staff Member ←→  Login (username/password)
                        │
                        ▼
               ┌─────────────────┐
               │  Chat UI         │  ← Next.js + per-user thread persistence
               │  (Next.js)       │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │  LangGraph Agent │  ← Single ReAct agent with tools
               │   (GPT-4o)      │     + general conversation (no tools)
               └────────┬────────┘
                        │
        ┌───────┬───────┼───────┬──────────┐
        ▼       ▼       ▼       ▼          ▼
  ┌─────────┐┌──────┐┌──────┐┌──────┐┌──────────┐
  │ Place   ││Route ││Event ││Email ││Google    │
  │ Search  ││Estim.││Route ││Draft ││Maps URL  │
  └─────────┘└──────┘└──────┘└──────┘└──────────┘
  Google Maps  Routes  Optimized  LLM-based   URL Builder
  Places API   API v2  Waypoints  templates
```

The agent decides when to call tools based on the conversation. No fixed sequence — the user can search places, plan routes, draft emails, or just chat, in any order.

### General LLM Capability

When the user's question doesn't require tools, the agent responds directly from its knowledge. It can:
- Answer questions about Portugal (geography, culture, weather, customs)
- Provide event planning advice (best seasons, group dynamics, rain contingency)
- Help with business tasks (client communication, pricing, proposals)
- Assist with writing beyond emails (social media, reports, meeting notes)
- Brainstorm creative event themes and activity combinations
- Have natural, friendly conversation as a knowledgeable colleague

Tools are only invoked when they genuinely add value (real place data, actual driving times, structured templates).

### User Authentication & Thread Persistence

- Simple username/password login on the frontend (stored in localStorage)
- Thread metadata stores `username` and optional `event_name`
- Threads filtered per-user via `client.threads.search({ metadata: { username } })`
- Users can tag conversations with event names (e.g., "Vodafone Team Building March 2025")
- PostgreSQL (local Docker or AWS RDS) for checkpoint persistence

### Tools

| Tool | Purpose | Backend |
|------|---------|---------|
| **search_places** | Search for activities, venues, restaurants near a location with activity type filtering | Google Maps Places API + Geocoding |
| **geocode_address** | Convert address to lat/lng coordinates | Google Geocoding API |
| **get_travel_time** | Calculate drive/walk times between two points | Google Maps Routes API v2 |
| **plan_event_route** | Optimized multi-stop route with pickup/drop-off points | Google Maps Routes API v2 |
| **build_google_maps_url** | Generate shareable Google Maps directions URL | URL construction |
| **draft_email** | Generate professional client emails from templates (proposal, follow-up, confirmation, thank-you) | LLM with structured templates |

### Place Search Activity Types

| Type | Examples |
|------|----------|
| `natural_sights` | Viewpoints, parks, nature reserves, beaches, waterfalls |
| `cultural` | Museums, historic sites, monuments, wine cellars |
| `restaurants` | Restaurants, wine bars, traditional food experiences |
| `venues` | Event spaces, hotels with meeting rooms, quintas |
| `general` | No filter (default) |

**Excluded**: Cycling tours, bike rentals, segway tours, scooter tours, and other competitor activities are automatically filtered out.

### Email Templates

| Template | Use Case |
|----------|----------|
| `proposal` | Full event proposal with itinerary, pricing structure, included services |
| `follow_up` | Follow-up after initial contact |
| `confirmation` | Event confirmation with logistics details |
| `thank_you` | Post-event thank you message |

All templates support **Portuguese (PT-PT)** and **English** with Extremo Ambiente branding.

### Language

- The assistant is **bilingual (Portuguese PT-PT / English)**.
- It auto-detects the user's language and responds accordingly.
- The `draft_email` tool accepts a `language` parameter (`pt` or `en`).
- All tool outputs and templates work in both languages.

---

## Tech Stack

- **LangGraph** — ReAct agent orchestration with tool calling
- **LangChain** — Tool definitions, chat models
- **OpenAI GPT-4o** — LLM backbone
- **Google Maps APIs** — Places (New), Routes v2, Geocoding
- **LangGraph Server** — Serves the agent via API
- **Agent Chat UI** — Next.js frontend with authentication and per-user threads
- **PostgreSQL** — Thread/checkpoint persistence (local Docker or AWS RDS)
- **Redis** — LangGraph server cache (local Docker or AWS ElastiCache)
- **AWS CloudFormation** — Infrastructure as Code for production deployment

---

## Project Structure

```
Extremo_chatbot/
├── CLAUDE.md
├── README.md
├── prompt.md                     # Evolution requirements spec v1
├── prompt-v2.md                  # Requirements spec v2 (fixes + AWS)
├── .env.example
├── .gitignore
│
├── agent/                        # LangGraph backend
│   ├── __init__.py
│   ├── graph.py                  # ReAct agent graph definition
│   ├── state.py                  # Chat state schema (messages only)
│   ├── prompts.py                # System prompt (bilingual, EA context, general LLM)
│   └── tools/
│       ├── __init__.py           # Exports ALL_TOOLS list
│       ├── google_maps.py        # search_places, geocode, travel_time, plan_event_route, maps_url
│       └── email_drafter.py      # Email drafting with templates (proposal, follow_up, etc.)
│
├── langgraph.json                # LangGraph server config
├── pyproject.toml                # Python dependencies
├── Dockerfile                    # LangGraph API base image
├── docker-compose.yml            # Local dev: postgres + redis + backend + frontend
│
├── infra/                        # AWS infrastructure
│   ├── cloudformation.yaml       # Full ECS Fargate stack (~$122/month)
│   ├── cloudformation-ec2.yaml   # Simple EC2 + Docker Compose (~$22/month)
│   ├── deploy.sh                 # ECS deployment script
│   └── deploy-ec2.sh             # EC2 deployment script
│
├── scripts/
│   └── ec2-setup.sh              # Legacy EC2 setup script
│
└── ui/                           # Next.js chat frontend
    ├── package.json
    ├── next.config.mjs
    ├── .env.example
    └── src/
        ├── app/
        │   ├── page.tsx          # Main chat page
        │   ├── layout.tsx        # Root layout
        │   └── api/[..._path]/route.ts  # API passthrough to LangGraph
        ├── providers/
        │   ├── Auth.tsx          # Username auth context + login form
        │   ├── Stream.tsx        # LangGraph stream connection (no config form)
        │   ├── Thread.tsx        # Thread list (filtered by user)
        │   └── client.ts         # LangGraph SDK client factory
        ├── components/thread/    # Chat UI, messages, history sidebar
        └── lib/
            └── app-config.ts     # App name/description
```

---

## Commands

```bash
# Backend (local dev)
pip install -e .
langgraph dev                     # Start LangGraph dev server on :2024

# Frontend (local dev)
cd ui && pnpm install && pnpm dev # Start Next.js on :3000

# Production (Docker Compose — local)
docker compose up --build         # Start all services

# Production — Simple EC2 (~$22/month)
./infra/deploy-ec2.sh --region eu-west-1 --key-pair my-key

# Production — Full ECS (~$122/month)
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot
```

---

## Environment Variables

```bash
# === Local Development ===
OPENAI_API_KEY=sk-...
GOOGLE_MAPS_API_KEY=...

# === LangSmith (optional) ===
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=extremoambiente-a2

# === Production (AWS) — managed by CloudFormation parameters ===
# POSTGRES_URI=postgres://langgraph:PASSWORD@rds-endpoint:5432/langgraph
# REDIS_URI=redis://elasticache-endpoint:6379

# === Frontend (set in docker-compose or CloudFormation) ===
# NEXT_PUBLIC_API_URL=http://localhost:2024
# NEXT_PUBLIC_ASSISTANT_ID=agent
```

---

## AWS Deployment

The `infra/` directory contains two CloudFormation options:

| Option | Template | Cost | Best for |
|--------|----------|------|----------|
| **EC2 Simple** | `cloudformation-ec2.yaml` | **~$22/month** | Prototypes, demos, class projects |
| **ECS Production** | `cloudformation.yaml` | **~$122/month** | Production, scaling, high availability |

### Option A: EC2 Simple (~$22/month) — Recommended for prototypes

Single EC2 `t3.small` running Docker Compose. Everything on one machine: PostgreSQL, Redis, LangGraph backend, Next.js frontend.

```
Internet
   │
   ▼
┌──────────────────────────────┐
│  EC2 Instance (t3.small)     │  ← Elastic IP
│                              │
│  ┌──────────┐ ┌──────────┐  │
│  │ Frontend  │ │ Backend  │  │
│  │ :3000     │ │ :8123    │  │
│  └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐  │
│  │ PostgreSQL│ │ Redis    │  │  ← Docker Compose
│  │ :5432     │ │ :6379    │  │
│  └──────────┘ └──────────┘  │
└──────────────────────────────┘
```

**Cost breakdown**: EC2 t3.small ~$15 + EIP ~$3.65 + 30GB gp3 ~$2.40 = **~$22/month**

```bash
# Deploy
./infra/deploy-ec2.sh --region eu-west-1 --key-pair my-key

# With options
./infra/deploy-ec2.sh --region eu-west-1 --key-pair my-key \
  --instance-type t3.small \
  --git-repo https://github.com/user/Extremo_chatbot.git \
  --ssh-cidr 203.0.113.5/32

# SSH into the instance
ssh -i my-key.pem ubuntu@<PUBLIC_IP>

# Check boot progress
ssh -i my-key.pem ubuntu@<PUBLIC_IP> 'tail -f /var/log/user-data.log'
```

### Option B: ECS Production (~$122/month)

Full production architecture with ALB, ECS Fargate, managed RDS, ElastiCache, private subnets, and service discovery.

```
Internet
   │
   ▼
┌──────────────────┐
│  Application      │
│  Load Balancer    │  ← Public ALB, port 80
│  (ALB)            │
└────────┬─────────┘
         │
         ▼
   ┌──────────┐
   │ Frontend  │  ← ECS Fargate (Next.js :3000)
   │ Service   │     proxies /api/* to backend
   └─────┬────┘     via Cloud Map DNS
         │
         ▼
   ┌──────────┐
   │ Backend   │  ← ECS Fargate (LangGraph :8000)
   │ Service   │     backend.extremo.local
   └─────┬────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌───────────┐
│ RDS    │ │ ElastiCache│  ← Private subnets
│Postgres│ │ Redis      │
│ :5432  │ │ :6379      │
└────────┘ └───────────┘
```

**Cost breakdown**: NAT ~$35 + ALB ~$23 + Fargate ~$31 + RDS ~$18 + Redis ~$12 + misc ~$3 = **~$122/month**

```bash
# Deploy (builds Docker images, pushes to ECR, deploys stack)
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot

# With a specific AWS profile
./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot --profile myprofile
```

### ECS Resources Created

| Resource | Type | Details |
|----------|------|---------|
| VPC | Networking | 10.0.0.0/16, 2 public + 2 private subnets |
| NAT Gateway | Networking | Single NAT for private subnet egress |
| ALB | Load Balancer | Internet-facing, port 80 |
| ECS Cluster | Compute | Fargate, 2 services (backend + frontend) |
| RDS | Database | PostgreSQL 16, db.t3.micro, 20GB gp3 |
| ElastiCache | Cache | Redis 7, cache.t3.micro |
| ECR | Registry | 2 repos (extremo-backend, extremo-frontend) |
| Cloud Map | Discovery | Internal DNS: backend.extremo.local |
| CloudWatch | Logging | 30-day retention for both services |

---

## Key Design Decisions

1. **Single ReAct agent** (not multi-agent) — simpler, more flexible; user controls the flow
2. **Tool-augmented chat + general LLM** — tools are available but optional; the agent also answers general questions, brainstorms ideas, helps with writing, and has natural conversation
3. **Bilingual by default** — system prompt instructs the agent to mirror the user's language (PT-PT or EN)
4. **Email drafter with templates** — structured templates (proposal, follow-up, confirmation, thank-you) with EA branding in both languages
5. **Activity type filtering** — place search categorizes by type (natural sights, cultural, restaurants, venues) and excludes competitor activities
6. **Route optimization** — plan_event_route tool handles pickup/drop-off with waypoint optimization
7. **No fixed pipeline** — user can search places, plan routes, draft emails — any order
8. **Username-based auth** — simple login with thread metadata filtering for per-user persistence
9. **Metadata-based thread filtering** — uses LangGraph's built-in thread metadata (username, event_name) for per-user, per-event organization
10. **Minimal state** — only `messages` in the graph state; no complex multi-agent coordination needed
11. **AWS CloudFormation** — Infrastructure as Code for reproducible production deployments with VPC, ECS Fargate, RDS, ElastiCache
12. **Cloud Map service discovery** — Frontend reaches backend via internal DNS, only frontend is exposed through ALB
