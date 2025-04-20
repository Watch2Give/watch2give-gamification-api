# gamification_rewards.py
import sqlite3
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# ===== SETUP ===== #
app = FastAPI()

# Initialize SQLite DB
def init_db():
    conn = sqlite3.connect("rewards.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            ad_tokens INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 1,
            last_active DATE,
            badges TEXT DEFAULT '[]',
            sponsor_credits TEXT DEFAULT '{}',
            gives INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Create tables on startup

# ===== MODELS ===== #
class UserAction(BaseModel):
    user_id: str
    ad_tokens_earned: Optional[int] = 0

class BadgeRequest(BaseModel):
    user_id: str
    badge_name: str

class GiveRequest(BaseModel):
    count: int = 1  # Default to 1 if not specified

# ===== CORE FUNCTIONS ===== #
def get_db_connection():
    return sqlite3.connect("rewards.db")


def is_consecutive_day(last_active) -> bool:
    """
    Checks if a user's last activity was yesterday.
    """
    return datetime.now().date() - last_active == timedelta(days=1)


# ===== API ENDPOINTS ===== #
@app.post("/log_watch")
def log_ad_watch(action: UserAction):
    conn = get_db_connection()
    cursor = conn.cursor()


    #print('action.user_id: ',action.user_id)
    #print('action.ad_tokens_earned:',action.ad_tokens_earned)

    # Insert user if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    """, (action.user_id,))

    # Get current last_active date
    cursor.execute("""
        SELECT last_active FROM users WHERE user_id = ?
    """, (action.user_id,))
    last_active = cursor.fetchone()[0]
    #print('last_active: ', last_active)

    # Update tokens (always)
    cursor.execute("""
        UPDATE users
        SET ad_tokens = ad_tokens + ?
        WHERE user_id = ?
    """, (action.ad_tokens_earned, action.user_id))


    # Only update date if last_active is not today
    today = datetime.now().date()
    if last_active:
        #print('1111')
        last_active_date = datetime.strptime(last_active, "%Y-%m-%d").date()

        if is_consecutive_day(last_active_date):
            print('1111')
            cursor.execute("""
                UPDATE users SET streak_days = streak_days + 1
                WHERE user_id = ?
            """, (action.user_id,))

        if last_active_date!=today and not is_consecutive_day(last_active_date):
            cursor.execute("""
                UPDATE users SET streak_days = 1
                WHERE user_id = ?
            """, (action.user_id,))


        if last_active_date != today:
            cursor.execute("""
                UPDATE users
                SET last_active = DATE('now')
                WHERE user_id = ?
            """, (action.user_id,))
    else:
        # If no last_active exists, set it to today
        cursor.execute("""
            UPDATE users
            SET last_active = DATE('now')
            WHERE user_id = ?
        """, (action.user_id,))



    conn.commit()
    conn.close()
    return {"status": "success", "tokens_added": action.ad_tokens_earned}

@app.get("/leaderboard")
def get_leaderboard(limit: int = 10, sort_by: str = "ad_tokens"):
    """
    Get leaderboard sorted by either tokens or gives
    Parameters:
    - limit: number of top users to return (default: 10)
    - sort_by: "ad_tokens" or "gives" (default: "tokens")
    """
    # Validate sort_by parameter
    if sort_by not in ["ad_tokens", "gives"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_by parameter. Must be 'ad_tokens' or 'gives'"
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get leaderboard based on selected metric
    cursor.execute(f"""
        SELECT user_id, ad_tokens, gives 
        FROM users 
        ORDER BY {sort_by} DESC 
        LIMIT ?
    """, (limit,))
    
    leaderboard = [
        {
            "user_id": row[0],
            "tokens": row[1],
            "gives": row[2],
            "rank": idx + 1
        }
        for idx, row in enumerate(cursor.fetchall())
    ]
    
    conn.close()
    
    return {
        "sort_by": sort_by,
        "leaderboard": leaderboard
    }

@app.post("/unlock_badge")
def unlock_badge(request: BadgeRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    badges_json = cursor.execute("""
        SELECT badges FROM users WHERE user_id = ?
    """, (request.user_id,)).fetchone()[0]
    badges = json.loads(badges_json)

    if request.badge_name not in badges:
        badges.append(request.badge_name)
        cursor.execute("""
            UPDATE users SET badges = ?
            WHERE user_id = ?
        """, (json.dumps(badges), request.user_id))
        conn.commit()
        conn.close()
        return {"status": "badge_unlocked", "badge": request.badge_name}
    conn.close()
    return {"status": "already_has_badge"}

@app.get("/user/{user_id}")
def get_user_stats(user_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ad_tokens, streak_days, badges, gives
        FROM users WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "tokens": row[0],
        "streak": row[1],
        "badges": json.loads(row[2]),
        "gives": row[3]
    }



@app.post("/record_give/{user_id}")
def record_give(user_id: str, request: GiveRequest):
    """
    Increments the user's give count by specified amount when they submit verified proof.
    Returns the updated give count.
    """
    if request.count <= 0:
        raise HTTPException(status_code=400, detail="Count must be positive")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First verify user exists
        cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Increment gives count by specified amount
        cursor.execute("""
            UPDATE users 
            SET gives = gives + ? 
            WHERE user_id = ?
            RETURNING gives
        """, (request.count, user_id))
        
        new_give_count = cursor.fetchone()[0]
        conn.commit()
        
        return {
            "status": "success",
            "user_id": user_id,
            "added_gives": request.count,
            "new_give_count": new_give_count
        }
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()



# ===== SPONSOR REWARDS ===== #
@app.get("/check_rewards/{user_id}")
def check_rewards(user_id: str):
    # All possible badges with their unlock conditions
    all_badges = [
        # Give-based badges (sorted by threshold)
        {"name": "First Giver", "type": "give", "threshold": 1},
        {"name": "V-Buck", "type": "give", "threshold": 5},
        {"name": "Robux", "type": "give", "threshold": 10},
        {"name": "Generous Giver", "type": "give", "threshold":20},
        {"name": "Philanthropist", "type": "give", "threshold": 50},
        {"name": "Ultimate Giver", "type": "give", "threshold": 100},
        
        # Streak-based badges (sorted by days)
        {"name": "3-day Streak", "type": "streak", "threshold": 3},
        {"name": "5-day Streak", "type": "streak", "threshold": 5},
        {"name": "10-day Streak", "type": "streak", "threshold": 10},
        {"name": "30-day Champion", "type": "streak", "threshold": 30}
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user data (now including gives count)
    cursor.execute("""
        SELECT ad_tokens, streak_days, badges, gives FROM users WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    current_tokens, current_streak, badges_json, current_gives = result
    unlocked_badges = json.loads(badges_json) if badges_json else []
    
    response = {
        "current_tokens": current_tokens,
        "current_streak": current_streak,
        "current_gives": current_gives,
        "new_badges_unlocked": [],
        "next_give_badge": None,
        "next_streak_badge": None
    }
    
    # Check for new badges to unlock
    for badge in all_badges:
        meets_threshold = (
            (badge["type"] == "give" and current_gives >= badge["threshold"]) or
            (badge["type"] == "streak" and current_streak >= badge["threshold"])
        )
        
        if meets_threshold and badge["name"] not in unlocked_badges:
            unlocked_badges.append(badge["name"])
            response["new_badges_unlocked"].append(badge["name"])
    
    # Find next give badge
    for badge in sorted([b for b in all_badges if b["type"] == "give"], key=lambda x: x["threshold"]):
        if badge["name"] not in unlocked_badges:
            response["next_give_badge"] = {
                "name": badge["name"],
                "needed": badge["threshold"] - current_gives,
                "threshold": badge["threshold"]
            }
            break
    
    # Find next streak badge
    for badge in sorted([b for b in all_badges if b["type"] == "streak"], key=lambda x: x["threshold"]):
        if badge["name"] not in unlocked_badges:
            response["next_streak_badge"] = {
                "name": badge["name"],
                "needed": badge["threshold"] - current_streak,
                "threshold": badge["threshold"]
            }
            break
    
    # Update database if new badges were unlocked
    if response["new_badges_unlocked"]:
        cursor.execute("""
            UPDATE users SET badges = ? WHERE user_id = ?
        """, (json.dumps(unlocked_badges), user_id))
        conn.commit()
    
    conn.close()
    return response



# ===== RUN SERVER ===== #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)