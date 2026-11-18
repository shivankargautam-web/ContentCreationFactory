# AI Content Factory

Turn a sentence like **“Generate 10 shorts about Kafka architecture. Publish one per day at 9AM EST.”** into researched, scripted, rendered, and scheduled YouTube Shorts and Instagram Reels.

## Architecture

```text
Next.js 15 (frontend) ──HTTP/JWT──► FastAPI (backend, async) ──► PostgreSQL (SQLAlchemy 2 + Alembic)
                                        │
                                        ├─► Redis ◄── Celery worker / beat
                                        │              │
                                        │              └─ LangGraph pipeline per short:
                                        │                 START → Research → Script → SEO → Video → Publisher → END
                                        │
                                        └─► OpenAI · ElevenLabs · FFmpeg · S3 · YouTube Data API · Instagram Graph API
```

| Layer | Location | Responsibility |
|---|---|---|
| API | `backend/app/api` | Routers, request validation, auth/RBAC dependencies |
| Services | `backend/app/services` | Use cases (campaigns, generation, publishing, analytics) and provider adapters |
| Agents | `backend/app/agents` | Research, Script, SEO, Video, Publisher agents |
| Workflows | `backend/app/workflows` | LangGraph `StateGraph` wiring the agents in order |
| Repository | `backend/app/repository` | Async SQLAlchemy repositories + unit of work |
| Models | `backend/app/models` | ORM tables: `users`, `campaigns`, `content_items`, `videos`, `publishing_jobs`, `platform_accounts`, `analytics` |
| Scheduler | `backend/app/scheduler` | Celery app, tasks, and DST-safe schedule planner |
| Composition root | `backend/app/container.py` | Dependency injection; swaps real vs. offline adapters |

### How a campaign runs

1. `POST /api/v1/campaigns` parses the instruction (count, topic, cadence, time, timezone, start date) using rules first, with the LLM filling gaps.
2. The Research agent’s series planner splits the topic into N distinct episode angles. One `content_item` is created per short, each with a UTC `scheduled_at` that keeps the local wall-clock time across DST changes.
3. A Celery `generation` task runs the LangGraph pipeline for each item:
   - **Research**: summary, facts, outline, keywords.
   - **Script**: hook, body beats, CTA.
   - **SEO**: title, description, hashtags, tags.
   - **Video**: storyboard, optional DALL·E scenes, ElevenLabs voiceover, SRT captions, then FFmpeg renders a 1080×1920 H.264/AAC MP4 with burned-in captions.
   - **Publisher**: creates one idempotent `publishing_job` per platform. A job that is already due is published immediately.
4. Celery beat runs `dispatch_due_jobs` every minute. Jobs are claimed with `FOR UPDATE SKIP LOCKED`, uploaded (YouTube resumable upload or Instagram Reel container → publish), and retried up to 3 times.
5. Celery beat runs `collect_analytics` hourly and stores cumulative snapshots. The analytics API aggregates the latest snapshot per job.

### Offline mode

With no `OPENAI_API_KEY` or `ELEVENLABS_API_KEY`, deterministic offline generators and silent audio are used. With `PUBLISHING_DRY_RUN=true` and no connected account, publishing is simulated. The full pipeline, including real FFmpeg rendering, works with no external credentials.

## Quick start (Docker)

```bash
cp .env.example .env          # optionally add OpenAI / ElevenLabs keys
docker compose up --build
```

- Frontend: http://localhost:3000 (the first registered user becomes **admin**)
- API docs: http://localhost:8000/docs
- OpenAPI contract: [`docs/openapi.json`](docs/openapi.json); summary in [`docs/API.md`](docs/API.md)

Services: `frontend`, `backend`, `worker`, `beat`, `postgres`, `redis`.

## Local development

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.scheduler.celery_app:celery_app worker -Q default,generation,publishing,analytics -l INFO
celery -A app.scheduler.celery_app:celery_app beat -l INFO

# frontend
cd frontend && npm install && npm run dev
```

## Tests and quality gates

```bash
cd backend
pytest                                   # unit + integration (SQLite by default)
TEST_DATABASE_URL=postgresql+asyncpg://acf:acf@localhost:5432/acf_test pytest   # against Postgres
ruff check . && ruff format --check . && mypy app
alembic upgrade head && alembic check    # migration matches models

cd ../frontend
npm run lint && npm run typecheck && npm test && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of these, plus `terraform validate` and a Docker Compose smoke test.

## Roles

| Role | Can |
|---|---|
| admin | Everything, including viewing all campaigns and managing user roles |
| editor | Create and manage their own campaigns, connect platform accounts |
| viewer | Read-only access to their own campaigns and analytics |

## Connecting platforms

Use **Settings → Connected accounts** (`POST /api/v1/platform-accounts`). Tokens are Fernet-encrypted at rest and are never returned by the API.

- **YouTube**: a channel ID plus an OAuth access token and refresh token with the `youtube.upload` scope. `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` must be set so expiring tokens refresh automatically.
- **Instagram**: an Instagram Business account ID plus a long-lived token with `instagram_content_publish`. The Graph API fetches the video by URL, so production must use `STORAGE_BACKEND=s3`; presigned URLs are generated automatically.

## Observability

- Structured JSON logs (structlog) include `request_id`, `trace_id`, and `span_id`.
- OpenTelemetry traces cover FastAPI, SQLAlchemy, HTTPX, Redis, Celery, and every agent node. Set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT`.
- On AWS, an ADOT sidecar exports traces to X-Ray. CloudWatch log metric filters alarm on `generation.failed` and `publish.failed`.

## Deploying to AWS

`infra/terraform` provisions:

- VPC with public and private subnets, plus NAT
- ALB with optional HTTPS
- ECS Fargate services: `api`, `worker`, `beat`, `frontend`, with autoscaling
- RDS PostgreSQL 16 (encrypted, Multi-AZ)
- ElastiCache Redis
- S3 media bucket (private, versioned, lifecycle rules)
- ECR repositories
- Secrets Manager
- CloudWatch log groups, alarms, and a dashboard

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
# push images to the output ECR repos, then put real provider keys into the app secret:
aws secretsmanager put-secret-value --secret-id "$(terraform output -raw app_secret_arn)" --secret-string file://secrets.json
```

The frontend calls the API on its own origin. Locally, Next.js rewrites proxy `/api` and `/media` to `BACKEND_INTERNAL_URL`. On AWS, the ALB routes `/api/*` to the backend directly.
