# mofa-letter

Adaptive Daily Newsletter — completely free, forever.

## What It Does

Every morning, mofa-letter sends each registered user a personalized newsletter on any topic they choose — finance, tech, philosophy, cooking, AI news, anything. Users interact entirely through tracked links in the email — no app, no login, no dashboard.

- **Send Me More** delivers bonus newsletters on demand (up to 5 per day)
- **Unsubscribe** anytime with one click
- **Any topic** — enter a custom prompt and the AI creative director designs the perfect newsletter

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI (Python 3.11+) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL via Supabase |
| AI / LLM | Groq API (`llama-3.3-70b-versatile`) |
| Email | Resend |
| Hosting | Oracle Cloud Always Free |
| Scheduler | GitHub Actions cron or VM cron |

## Quick Start

See `DEPLOYMENT.md` for the full setup and deployment guide.

## Admin Endpoints

All admin operations use `X-Admin-Key` header authentication.

- `POST /admin/users` — Create user
- `GET /admin/users` — List all users with stats
- `GET /admin/users/{id}` — Get user details
- `PATCH /admin/users/{id}` — Update user
- `DELETE /admin/users/{id}` — Deactivate user
- `POST /admin/users/{id}/send-now` — Manually send a newsletter (testing)

## License

Personal use. Built to be free forever.
