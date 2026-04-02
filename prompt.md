# Prompt: Build the Extremo Ambiente Corporate Event Chatbot

## Context

You are working on an existing LangGraph + Next.js chatbot project for **Extremo Ambiente**, a Portuguese adventure tourism company based in Sintra that organizes corporate events. The project already has a working foundation — a single ReAct agent with Google Maps tools and an email drafter, a Next.js chat UI, and Docker Compose deployment with PostgreSQL + Redis.

Your job is to **evolve this into a production-ready chatbot** with user authentication, per-event conversation persistence, and improved tools. All infrastructure will run on **AWS**.

---

## Existing Codebase (what you're starting from)

### Project Structure
```
Extremo_chatbot/
├── CLAUDE.md                     # Project docs (needs updating)
├── agent/
│   ├── __init__.py
│   ├── graph.py                  # ReAct agent (GPT-4o, create_react_agent)
│   ├── state.py                  # Minimal state: just messages
│   ├── prompts.py                # Bilingual system prompt (PT-PT / EN)
│   └── tools/
│       ├── __init__.py           # Exports ALL_TOOLS list
│       ├── google_maps.py        # search_places, geocode_address, get_travel_time, build_google_maps_url
│       └── email_drafter.py      # draft_email tool (returns template instructions for LLM)
├── langgraph.json                # {"graphs": {"agent": "./agent/graph.py:graph"}}
├── pyproject.toml                # Python deps (langgraph, langchain, langchain-openai)
├── Dockerfile                    # LangGraph API base image
├── docker-compose.yml            # postgres:16 + redis:7 + backend + frontend
├── scripts/ec2-setup.sh          # EC2 Docker install script
└── ui/                           # Next.js frontend (Agent Chat UI template)
    ├── src/
    │   ├── app/page.tsx          # Main chat page
    │   ├── app/api/[..._path]/route.ts  # API passthrough proxy to LangGraph
    │   ├── providers/Stream.tsx  # LangGraph stream connection + config form
    │   ├── providers/Thread.tsx  # Thread list (client.threads.search)
    │   ├── providers/client.ts   # LangGraph SDK client factory
    │   ├── components/thread/    # Chat UI, messages, history sidebar
    │   └── lib/app-config.ts     # App name/description
    └── package.json
```

### Current Agent (`agent/graph.py`)
```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
graph = create_react_agent(model=llm, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)
```

### Current Tools
1. **`search_places(query, location_bias, center_lat, center_lng)`** — Google Places API (New), 15km radius filter, returns JSON array of places
2. **`geocode_address(address)`** — Google Geocoding API -> lat/lng
3. **`get_travel_time(origin_lat, origin_lng, dest_lat, dest_lng, travel_mode)`** — Google Routes API v2, DRIVE or WALK, traffic-aware
4. **`build_google_maps_url(stops_json)`** — Generates shareable Google Maps directions URL from list of stops
5. **`draft_email(context, language, tone)`** — Returns structured prompt instructions for the LLM to compose the email

### Current State (`agent/state.py`)
```python
class AgentState(dict):
    messages: Annotated[list[AnyMessage], add_messages]
```

### Current Persistence
- **Development**: LangGraph pickle checkpoints (`.langgraph_api/`)
- **Production**: PostgreSQL via docker-compose (`POSTGRES_URI`)
- **No user authentication** — all threads visible to everyone
- Thread ID stored in URL params (`?threadId=uuid`)

### Current Frontend
- Next.js with `@langchain/langgraph-sdk` for streaming
- Config form shown if no `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_ASSISTANT_ID` env vars
- Thread history sidebar fetches all threads via `client.threads.search()`
- No login, no user concept, no per-user filtering

---

## Requirements (what needs to change)

### 1. User Authentication & Per-User Chat Persistence

**Goal**: Each staff member logs in with a username. Their conversations are saved and associated with their account. Each conversation can be linked to a specific corporate event.

**Implementation**:
- Add a **simple authentication layer** to the Next.js frontend (username-based login — can be a simple form with username/password against a database)
- Store the **logged-in username** in the app state
- When creating a new thread, attach `metadata: { username: "<user>", event_name: "<optional event name>" }` to the LangGraph thread
- Filter threads by username: `client.threads.search({ metadata: { username: currentUser } })`
- Allow users to **name/tag conversations by event** (e.g., "Vodafone Team Building March 2025")
- Show only the current user's threads in the history sidebar
- Use **AWS RDS (PostgreSQL)** instead of the local docker postgres for production persistence

### 2. Email Proposals with Pre-Defined Template

**Goal**: The chatbot can generate professional proposal emails using a structured template specific to Extremo Ambiente's corporate event offerings.

**Implementation**:
- Enhance the `draft_email` tool to support a **`template` parameter** with at least these options:
  - `"proposal"` — Full event proposal with itinerary, pricing structure, included services
  - `"follow_up"` — Follow-up after initial contact
  - `"confirmation"` — Event confirmation with logistics
  - `"thank_you"` — Post-event thank you
- Each template should have a **pre-defined structure** with placeholders that get filled from conversation context:
  - **Proposal template**: Subject, greeting, event overview (date, group size, location), proposed itinerary (time slots with activities), what's included, pricing notes, next steps, sign-off
  - Include Extremo Ambiente branding elements (company name, tagline, contact info)
- The tool should return rich template instructions so the LLM composes the final email with all details from the conversation
- Support both **Portuguese (PT-PT)** and **English**

### 3. Google Maps Place Search (Refined)

**Goal**: Search for places suitable for corporate events — focus on **natural sights and cultural activities**. Explicitly avoid activities that could be done by competitors (like cycling or other kind of tours).

**Implementation**:
- Update `search_places` to add an **`activity_type` parameter** with options like:
  - `"natural_sights"` — Viewpoints, parks, nature reserves, beaches, waterfalls, mountains
  - `"cultural"` — Museums, historic sites, monuments, wine cellars, traditional markets
  - `"restaurants"` — Restaurants, wine bars, traditional food experiences
  - `"venues"` — Event spaces, hotels with meeting rooms, quintas
  - `"general"` — No filter (default, current behavior)
- Add a **negative filter** in the system prompt and tool logic: explicitly exclude results to other tours comapnies like related to cycling, jeep tours, sliding or similar competitor activities
- Update the system prompt to instruct the agent about what types of activities Extremo Ambiente offers (jeep tours, walking tours, RZR off-road, wine tastings, cultural tours, kayaking, surf, hiking, food experiences) and what to avoid suggesting

### 4. Route Optimization with Pickup & Drop-off

**Goal**: Create optimized routes for corporate events that account for a defined pickup point and drop-off point (often the same — e.g., the client's hotel).

**Implementation**:
- Create a new tool **`plan_event_route(pickup, dropoff, stops_json, optimize=True)`** that:
  - Takes a pickup location (start), drop-off location (end), and a list of intermediate stops
  - If `optimize=True`, reorders the intermediate stops to minimize total travel time (using the Google Routes API to compute an optimized waypoint order)
  - Returns: ordered list of stops with travel times between each, total duration, total distance, and a Google Maps URL
  - Uses the existing `geocode_address` and `get_travel_time` internally
- The existing `get_travel_time` and `build_google_maps_url` tools should remain available for ad-hoc queries
- The system prompt should instruct the agent to always ask about pickup/drop-off when planning a full event route

### 5. Bilingual Support (Portuguese PT-PT and English)

**Current**: Already implemented in the system prompt. **Keep and refine**:
- Ensure all tool outputs, error messages, and template text work in both languages
- The email templates must have proper PT-PT and EN versions
- System prompt should continue to auto-detect language and respond accordingly

### 6. AWS Infrastructure

**Goal**: Deploy everything on AWS with proper production infrastructure.

**Implementation**:
- **AWS RDS** (PostgreSQL) — Replace the local docker postgres with an RDS instance for thread/checkpoint persistence
- **AWS ElastiCache** (Redis) — Replace docker redis
- **AWS ECS (Fargate)** or **EC2** — Run the LangGraph backend and Next.js frontend containers
- **AWS ALB** — Load balancer in front of the services
- Update `docker-compose.yml` for local development (keep local postgres/redis)
- Create a separate **production deployment config** (ECS task definitions or updated ec2-setup script)
- Update `.env.example` with all new AWS-related variables
- The `scripts/ec2-setup.sh` should be updated or a new deployment script created for the AWS setup

---

## Files to Update

### `CLAUDE.md`
Rewrite to reflect the new architecture:
- User auth + per-user/per-event thread persistence
- Enhanced email templates (proposal, follow-up, confirmation, thank-you)
- Refined place search (natural sights, cultural — no cycling)
- Route optimization with pickup/drop-off
- AWS infrastructure (RDS, ElastiCache, ECS/EC2, Cognito)
- Updated project structure
- Updated environment variables
- Updated commands

### `agent/graph.py`
- May need updates if state changes or if you add middleware for user context

### `agent/state.py`
- Consider adding user context fields if needed by the agent (username, event metadata)

### `agent/prompts.py`
- Update system prompt to:
  - Mention the new tools (route planning with pickup/drop-off, enhanced email templates)
  - Explicitly instruct to avoid cycling/bike activities
  - Mention Extremo Ambiente's specific offerings
  - Instruct to ask about pickup/drop-off when planning routes
  - Instruct to ask about event details (group size, date, budget) when drafting proposals

### `agent/tools/__init__.py`
- Export the new/updated tools

### `agent/tools/google_maps.py`
- Add `activity_type` filter to `search_places`
- Add negative filter for cycling-related results
- Add new `plan_event_route` tool with route optimization

### `agent/tools/email_drafter.py`
- Add template parameter and pre-defined templates (proposal, follow_up, confirmation, thank_you)
- Bilingual template structures

### `ui/src/providers/Stream.tsx`
- Replace the config form with a login form (username/password)
- Pass username to thread metadata

### `ui/src/providers/Thread.tsx`
- Filter threads by current user's username
- Support event name tagging

### `ui/src/components/thread/`
- Add ability to name/tag a conversation with an event name
- Show event name in thread history
- Show only current user's threads

### `docker-compose.yml`
- Keep for local dev
- Add comments about production AWS alternatives

### `pyproject.toml`
- Add any new dependencies

### `langgraph.json`
- Update if graph entry point changes

### `.env.example`
- Add new variables (AWS RDS URI, Cognito config, etc.)

---

## Key Constraints

1. **Do NOT suggest cycling, jeep tours, or other competitor tours** — these are competitor services. Filter them out of place search results and instruct the agent to avoid them.
2. **Keep the single ReAct agent architecture** — don't over-engineer with multi-agent. One agent with good tools is sufficient.
3. **Bilingual always** — every user-facing string, template, and tool output must work in PT-PT and EN.
4. **LangGraph thread persistence** — use LangGraph's built-in thread/checkpoint system with PostgreSQL. Don't build a separate message database.
5. **Metadata-based user filtering** — use LangGraph thread metadata to associate threads with users and events. This is the idiomatic approach.
6. **Production-ready** — error handling, proper env var management, no hardcoded secrets.

---

## Deliverables

Please implement the changes in this order:

1. **Update `CLAUDE.md`** with the new architecture and clean up references to the old multi-agent approach
2. **Enhance `agent/tools/email_drafter.py`** with pre-defined templates
3. **Update `agent/tools/google_maps.py`** — add activity_type filter, cycling exclusion, and `plan_event_route` tool
4. **Update `agent/prompts.py`** — refined system prompt
5. **Update `agent/tools/__init__.py`** and **`agent/state.py`** if needed
6. **Add user authentication to the frontend** — login form, username state, thread filtering by user, event tagging
7. **Update `docker-compose.yml`**, `.env.example`**, and deployment configs for AWS
8. **Update `pyproject.toml`** with any new dependencies

Start by reading all the existing files to understand the current implementation before making changes. Ask me if anything is unclear.
