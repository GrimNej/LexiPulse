# LexiPulse

Adaptive Daily Vocabulary Newsletter — completely free, forever.

## What It Does

Every morning at 7:00 AM NPT, LexiPulse sends each registered user an email containing three advanced English words, complete with definitions, etymology, pronunciation, and example sentences. Users interact entirely through tracked links in the email — no app, no login, no dashboard.

- **Too Easy** raises their difficulty level
- **Too Hard** lowers it
- **Just Right** confirms the current level
- **Send Me More** delivers up to four bonus newsletters per day

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

See `Plan.md` for the full setup and deployment guide.

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
