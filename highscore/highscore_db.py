# Add these imports to your existing server.py
import aiosqlite
import asyncio
from contextlib import asynccontextmanager

# Database setup
DB_FILE = "annotations.db"

async def init_db():
    """Initialize the database with required tables"""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS annotations (
                username TEXT,
                pair_id TEXT,
                class_name TEXT,
                timestamp TEXT,
                PRIMARY KEY (username, pair_id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                username TEXT PRIMARY KEY,
                total_annotations INTEGER DEFAULT 0,
                last_annotation TEXT
            )
        """)
        
        # Index for faster leaderboard queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_stats_total 
            ON user_stats(total_annotations DESC)
        """)
        
        await db.commit()

# Replace your file-based functions with these:

async def update_annotation_db(annotation: AnnotationUpdate):
    """Update annotation in database"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Check if this pair was previously annotated by this user
        cursor = await db.execute(
            "SELECT class_name FROM annotations WHERE username = ? AND pair_id = ?",
            (annotation.username, annotation.pairId)
        )
        old_annotation = await cursor.fetchone()
        old_class = old_annotation[0] if old_annotation else None
        
        # Update/insert the annotation
        await db.execute("""
            INSERT OR REPLACE INTO annotations 
            (username, pair_id, class_name, timestamp) 
            VALUES (?, ?, ?, ?)
        """, (annotation.username, annotation.pairId, annotation.className, 
              datetime.now().isoformat()))
        
        # Calculate new total for user (excluding "no_annotation")
        cursor = await db.execute("""
            SELECT COUNT(*) FROM annotations 
            WHERE username = ? AND class_name != 'no_annotation'
        """, (annotation.username,))
        new_total = (await cursor.fetchone())[0]
        
        # Update user stats
        await db.execute("""
            INSERT OR REPLACE INTO user_stats 
            (username, total_annotations, last_annotation) 
            VALUES (?, ?, ?)
        """, (annotation.username, new_total, datetime.now().isoformat()))
        
        # Get grand total
        cursor = await db.execute(
            "SELECT COUNT(*) FROM annotations WHERE class_name != 'no_annotation'"
        )
        grand_total = (await cursor.fetchone())[0]
        
        await db.commit()
        return new_total, grand_total

async def get_leaderboard_db():
    """Get leaderboard from database"""
    async with aiosqlite.connect(DB_FILE) as db:
        # Get leaderboard
        cursor = await db.execute("""
            SELECT username, total_annotations, last_annotation 
            FROM user_stats 
            WHERE total_annotations > 0
            ORDER BY total_annotations DESC
        """)
        users = await cursor.fetchall()
        
        leaderboard = []
        for username, total, last_annotation in users:
            # Get class breakdown for this user
            class_cursor = await db.execute("""
                SELECT class_name, COUNT(*) 
                FROM annotations 
                WHERE username = ? AND class_name != 'no_annotation'
                GROUP BY class_name
            """, (username,))
            classes = dict(await class_cursor.fetchall())
            
            leaderboard.append({
                "username": username,
                "total": total,
                "classes": classes,
                "lastAnnotation": last_annotation
            })
        
        # Get total annotations
        cursor = await db.execute(
            "SELECT COUNT(*) FROM annotations WHERE class_name != 'no_annotation'"
        )
        total_annotations = (await cursor.fetchone())[0]
        
        return leaderboard, total_annotations

# Update your FastAPI endpoints:

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.post("/api/annotate")
async def update_annotation(annotation: AnnotationUpdate):
    try:
        print(f"[SERVER] Received annotation from {annotation.username}")
        user_total, grand_total = await update_annotation_db(annotation)
        
        return {
            "success": True,
            "userTotal": user_total,
            "grandTotal": grand_total
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed: {e}")

@app.get("/api/leaderboard")
async def get_leaderboard():
    try:
        leaderboard, total_annotations = await get_leaderboard_db()
        
        return {
            "leaderboard": leaderboard,
            "totalAnnotations": total_annotations,
            "lastUpdated": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {e}")

# Migration script to convert existing JSON data:
async def migrate_from_json():
    """One-time migration from JSON to SQLite"""
    if not os.path.exists("highscore_list.json"):
        return
        
    with open("highscore_list.json", 'r') as f:
        json_data = json.load(f)
    
    async with aiosqlite.connect(DB_FILE) as db:
        for username, user_data in json_data.get("users", {}).items():
            # Migrate pairs data
            for pair_id, class_name in user_data.get("pairs", {}).items():
                await db.execute("""
                    INSERT OR IGNORE INTO annotations 
                    (username, pair_id, class_name, timestamp) 
                    VALUES (?, ?, ?, ?)
                """, (username, pair_id, class_name, 
                      user_data.get("lastAnnotation", datetime.now().isoformat())))
            
            # Migrate user stats
            await db.execute("""
                INSERT OR IGNORE INTO user_stats 
                (username, total_annotations, last_annotation) 
                VALUES (?, ?, ?)
            """, (username, user_data.get("total", 0), 
                  user_data.get("lastAnnotation", datetime.now().isoformat())))
        
        await db.commit()
    
    print("Migration from JSON completed!")

# Add to your startup:
@app.on_event("startup")
async def startup_event():
    await init_db()
    await migrate_from_json()  # One-time migration