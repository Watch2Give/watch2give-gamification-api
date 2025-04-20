# Watch2Give Gamification API

This FastAPI-based microservice powers the gamified engagement system for **Watch2Give**, tracking user streaks, token earnings, badges, and giving stats.

##  Features

-  **Ad Watch Logging** – Track and reward users for ad views
-  **Streak System** – Maintain daily engagement streaks (with grace period)
-  **Badge Unlocking** – Automatically unlock badges for token streaks or giving milestones
-  **Leaderboard** – Rank users based on tokens earned or proof of giving
-  **Give Tracker** – Count verified donations with proof-of-giving integration
-  **User Stats API** – Fetch stats on tokens, streak, gives, badges

##  Running the Server

```bash
# Make sure you're in the gamification-api directory
uvicorn gamification_rewards:app --reload
```

> SQLite DB file `rewards.db` will be created on first run.

## 📁 Endpoints Overview

| Method | Route                        | Description                              |
|--------|-----------------------------|------------------------------------------|
| POST   | `/log_watch`                | Log ad token earnings + streak updates   |
| GET    | `/leaderboard`              | View top users by `tokens` or `gives`    |
| POST   | `/unlock_badge`             | Force unlock badge manually              |
| GET    | `/user/{user_id}`           | Get user’s tokens, streak, gives, badges |
| POST   | `/record_give/{user_id}`    | Increment user's gives by amount         |
| GET    | `/check_rewards/{user_id}`  | Get new/unlocked badges & next targets   |

##  Streak Logic

- Max streak: **5 days**
- Grace period: **36 hours**
- Tracked in `last_active` column and updated on watch logs

##  Dependencies

Stored in [`requirements.txt`](requirements.txt). To install:

```bash
pip install -r requirements.txt
```

Main packages used:
- `fastapi`
- `pydantic`
- `uvicorn`
- `sqlite3` (builtin)

##  File Structure

```
gamification-api/
├── gamification_rewards.py   # Main FastAPI app
├── requirements.txt
└── rewards.db                # Auto-generated SQLite DB
```

##  Example Usage (log_watch)

```json
POST /log_watch
{
  "user_id": "alice123",
  "ad_tokens_earned": 10
}
```

##  Future Additions

- JWT-based user auth
- Token expiry tracking
- Admin panel to view stats

---
