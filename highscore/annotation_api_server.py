# annotation_api_server.py - Updated to use SQLite database (NO ASYNC CHANGES!)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Optional
import os
from pathlib import Path

from pathlib import Path
import os, io, json
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# where to store things on the server (adjust if needed)
# DATA_ROOT = Path(os.getenv("ANNOTATION_DATA_ROOT", "/srv/label_data")).resolve()
# ANNOTATIONS_DIR = DATA_ROOT / "annotations"  # <session_id>.json uploaded here
# IMAGES_DIR = DATA_ROOT / "images"            # images stored by their relative_path

# ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
# IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# ONLY CHANGE: Replace JSON import with database import
# OLD: import json
# NEW: Import your database module
from highscore_db import initialize_data_file, read_data, write_data, get_database_stats

app = FastAPI(title="Annotation Leaderboard API")

from review_db import init_review_db
init_review_db()


# Enable CORS (UNCHANGED)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve files under: http(s)://<host>:<port>/images/<relative_path>
# app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


# REMOVE: No more DATA_FILE needed!
# OLD: DATA_FILE = "highscore_list.json"

# Request models (UNCHANGED)
class AnnotationUpdate(BaseModel):
    username: str
    className: str
    pairId: str
    count: int = 1

# Response models (UNCHANGED)
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

# REMOVE: Old functions are now in database.py!
# OLD: def initialize_data_file(): ...
# OLD: def read_data(): ...  
# OLD: def write_data(data): ...

# Initialize on startup (UNCHANGED - still synchronous!)
initialize_data_file()

# API Routes (COMPLETELY UNCHANGED!)

@app.get("/api/stats")
async def get_stats():
    """Get all statistics (UNCHANGED)"""
    try:
        data = read_data()  # Same call, no await needed!
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read stats")

@app.post("/api/annotate")
async def update_annotation(annotation: AnnotationUpdate):
    # YOUR EXISTING CODE - COMPLETELY UNCHANGED!
    try:
        print(f"[SERVER] Received annotation from {annotation.username} for {annotation.pairId}: {annotation.className}")
        data = read_data()  # Same call!

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
            if is_new_pair or old_class == "no_annotation":
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
        user_data["pairTimestamps"] = user_data.get("pairTimestamps", {})
        user_data["pairTimestamps"][pair_id] = datetime.now().isoformat()
        now = datetime.now().isoformat()
        user_data["lastAnnotation"] = now
        data["lastUpdated"] = now

        write_data(data)  # Same call!

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
    """Get the leaderboard sorted by total annotations (UNCHANGED)"""
    try:
        data = read_data()  # Same call!
        
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

# BONUS: New endpoint to check database health
@app.get("/api/database/stats")
async def get_database_stats_endpoint():
    """Get database statistics and health info"""
    try:
        return get_database_stats()  # No await needed!
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to get database stats")

# Mount static files (UNCHANGED)
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Serve the main page (UNCHANGED)
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')








def _iter_annotation_files():
    return sorted(ANNOTATIONS_DIR.glob("*.json"))

@app.get("/unsure")
def list_unsure_pairs(limit: int = 1000):
    """
    Returns items like:
    {
      "session_id": "...",
      "session_path": "<meta root or session_id>",
      "pair_id": 42,
      "im1_url": "/images/<relative_path>",
      "im2_url": "/images/<relative_path>"
    }
    """
    out = []
    total = 0
    for ann_file in _iter_annotation_files():
        session_id = ann_file.stem
        try:
            data = json.loads(ann_file.read_text())
        except Exception as e:
            print("[UNSURE] skip", ann_file, "->", e)
            continue

        meta_root = (data.get("_meta") or {}).get("root")  # optional; used for context only

        for k, entry in data.items():
            if k == "_meta":
                continue
            ps = entry.get("pair_state")
            if ps not in (None, "no_annotation"):   # only unsure
                continue
            im1_rel = entry.get("im1_path")
            im2_rel = entry.get("im2_path")
            if not im1_rel or not im2_rel:
                continue

            out.append({
                "session_id": session_id,
                "session_path": meta_root or session_id,
                "pair_id": int(k),
                "im1_url": f"/images/{im1_rel}",
                "im2_url": f"/images/{im2_rel}",
            })
            total += 1
            if total >= limit:
                return out
    return out



## for inconsistent highscore reporting ##

from left_for_review import (
    get_left_for_review_count,
    get_annotator_review_progress,
)
from review_pair_registry import get_total_pairs

from review_db import (
    init_review_db,
    insert_review,
    get_user_review_stats,
    get_annotator_review_stats,
    get_model_review_stats,
    get_model_class_stats,
    get_total_review_count,
    get_reviewed_pair_ids_by_model,
)

class InconsistentReview(BaseModel):
    pairId: str
    predicted: str
    expected: str
    annotated_by: str
    reviewer: str
    decision: str
    modelName: str


@app.post("/api/inconsistent/review")
async def receive_inconsistent_review(rec: InconsistentReview):
    print("rec: ", rec)
    try:
        insert_review(
            pair_id=rec.pairId,
            annotated_by=rec.annotated_by,
            reviewer=rec.reviewer,
            predicted=rec.predicted,
            expected=rec.expected,
            decision=rec.decision,
            model_name=rec.modelName
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, f"Failed to save review: {e}")


@app.get("/api/inconsistent/userstats")
async def inconsistent_user_stats():
    """
    Groups reviewers into two categories:
    - 'has': more (or equal) accepted predictions than corrected
    - 'was': more corrected predictions than accepted
    """

    raw = get_user_review_stats()  # already returns { user: {accepted, corrected, total} }

    print("raw user stats: ", raw)
    grouped = {
        "has": {},
    }

    for user, stats in raw.items():
        accepted = stats.get("accepted", 0)
        corrected = stats.get("corrected", 0)
        total = stats.get("total", accepted + corrected)

        grouped["has"][user] = {
            "total": total,
            "accepted": accepted,
            "corrected": corrected
        }

    return grouped

@app.get("/api/inconsistent/stats/annotators")
async def inconsistent_annotator_stats():

    raw = get_annotator_review_stats()

    grouped = {
        "was": {}
    }

    for annotated_by, stats in raw.items():
        accepted = stats.get("accepted", 0)
        corrected = stats.get("corrected", 0)
        total = stats.get("total", accepted + corrected)

        grouped["was"][annotated_by] = {
            "total": total,
            "accepted": accepted,
            "corrected": corrected,
            "errorRate": stats["errorRate"]
        }

    return grouped

@app.get("/api/inconsistent/total")
async def inconsistent_total():
    """
    Returns the total number of reviewed items in the database.
    """
    try:
        total = get_total_review_count()
        return {"total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load total count: {e}")


@app.get("/api/inconsistent/modelstats")
async def inconsistent_model_stats():
    return get_model_review_stats()

@app.get("/api/inconsistent/modelstats/{model_name}/classes")
async def model_class_stats(model_name: str):
    return get_model_class_stats(model_name)


@app.get("/api/inconsistent/progress/{model_name}")
async def inconsistent_progress(model_name: str):
    reviewed = get_reviewed_pair_ids_by_model(model_name)
    total = get_total_pairs(model_name)
    left = get_left_for_review_count(model_name)

    return {
        "model": model_name,
        "reviewed": len(reviewed),
        "total": total,
        "left": left,
        "progress": len(reviewed) / total if total > 0 else 0.0
    }

@app.get("/api/inconsistent/progress/{model_name}/annotators")
async def annotator_progress(model_name: str):
    from review_pair_registry import _load_pairs

    data = _load_pairs(model_name)

    annotators = sorted({
        entry["annotated_by"].strip()
        for entry in data.values()
        if isinstance(entry.get("annotated_by"), str)
           and entry.get("annotated_by").strip()
    })

    return [
        get_annotator_review_progress(model_name, annotator)
        for annotator in annotators
    ]


if __name__ == "__main__":
    import uvicorn
    # INSTALL: pip install (no aiosqlite needed - using regular sqlite3!)
    uvicorn.run(app, host="0.0.0.0", port=8010)
