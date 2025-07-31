# server.py - FastAPI annotation leaderboard server
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Optional
import json
import os
from pathlib import Path

app = FastAPI(title="Annotation Leaderboard API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file path
DATA_FILE = "highscore_list.json"

# Request models
class AnnotationUpdate(BaseModel):
    username: str
    className: str
    pairId: str
    count: int = 1

# Response models
class UserStats(BaseModel):
    total: int
    classes: Dict[str, int]
    lastAnnotation: str

class LeaderboardUser(BaseModel):
    username: str
    total: int
    classes: Dict[str, int]
    lastAnnotation: str

class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardUser]
    totalAnnotations: int
    lastUpdated: str

# Initialize data file if it doesn't exist
def initialize_data_file():
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "users": {},
            "totalAnnotations": 0,
            "lastUpdated": datetime.now().isoformat()
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(initial_data, f, indent=2)

# Read data from file
def read_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

# Write data to file
def write_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Initialize on startup
initialize_data_file()

# API Routes

@app.get("/api/stats")
async def get_stats():
    """Get all statistics"""
    try:
        data = read_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read stats")

@app.post("/api/annotate")
async def update_annotation(annotation: AnnotationUpdate):
    try:
        print(f"[SERVER] Received annotation from {annotation.username} for {annotation.pairId}: {annotation.className}")
        data = read_data()

        user_data = data["users"].setdefault(annotation.username, {
            "total": 0,
            "classes": {},
            "lastAnnotation": None,
            "pairs": {}
        })

        pair_id = annotation.pairId
        new_class = annotation.className
        old_class = user_data["pairs"].get(pair_id)

        is_new_pair = old_class is None
        class_changed = old_class != new_class
        is_no_annotation = (new_class == "no_annotation")

        # Remove previous class if changing to "no_annotation"
        if is_no_annotation:
            if old_class and old_class != "no_annotation":
                user_data["total"] -= 1
                data["totalAnnotations"] -= 1

                # Decrement count for old class
                user_data["classes"][old_class] = user_data["classes"].get(old_class, 1) - 1
                if user_data["classes"][old_class] <= 0:
                    del user_data["classes"][old_class]
            # Increment class count for no_annotation
            if is_new_pair or class_changed:
                user_data["classes"][new_class] = user_data["classes"].get(new_class, 0) + 1

        else:
            # Not "no_annotation"
            if is_new_pair:
                user_data["total"] += 1
                data["totalAnnotations"] += 1
            elif class_changed and old_class != "no_annotation":
                # Changing from one real class to another
                user_data["classes"][old_class] = user_data["classes"].get(old_class, 1) - 1
                if user_data["classes"][old_class] <= 0:
                    del user_data["classes"][old_class]

            if is_new_pair or class_changed:
                user_data["classes"][new_class] = user_data["classes"].get(new_class, 0) + 1

        # Always track the pair's latest state
        user_data["pairs"][pair_id] = new_class
        now = datetime.now().isoformat()
        user_data["lastAnnotation"] = now
        data["lastUpdated"] = now

        write_data(data)

        print(f"[SERVER] Updated {annotation.username}: pair={pair_id}, class={new_class}, total={user_data['total']}, classes={user_data['classes']}")

        return {
            "success": True,
            "userTotal": user_data["total"],
            "grandTotal": data["totalAnnotations"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update annotation: {e}")




@app.get("/api/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard():
    """Get the leaderboard sorted by total annotations"""
    try:
        data = read_data()
        
        # Convert users dict to sorted leaderboard list
        leaderboard = []
        for username, stats in data["users"].items():
            leaderboard.append({
                "username": username,
                "total": stats["total"],
                "classes": stats["classes"],
                "lastAnnotation": stats["lastAnnotation"]
            })
        
        # Sort by total annotations (descending)
        leaderboard.sort(key=lambda x: x["total"], reverse=True)
        
        return {
            "leaderboard": leaderboard,
            "totalAnnotations": data["totalAnnotations"],
            "lastUpdated": data["lastUpdated"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get leaderboard")

# Mount static files (for serving the HTML)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Serve the main page
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# Example usage from your labeling tool:


if __name__ == "__main__":
    import uvicorn
    # Run with: python server.py
    # Or with hot reload: uvicorn server:app --reload
    uvicorn.run(app, host="0.0.0.0", port=8010)
