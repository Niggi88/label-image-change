# review_db.py
import sqlite3
from datetime import datetime
import threading

class ReviewDatabaseManager:
    def __init__(self, db_path="reviews.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    pair_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    predicted TEXT,
                    expected TEXT,
                    decision TEXT,
                    model_name TEXT,
                    timestamp TEXT,
                    PRIMARY KEY(pair_id, reviewer)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_stats (
                    decision TEXT PRIMARY KEY,
                    count INTEGER NOT NULL
                )
            """)

            # default rows (optional but useful)
            conn.execute("INSERT OR IGNORE INTO review_stats(decision, count) VALUES ('accepted', 0)")
            conn.execute("INSERT OR IGNORE INTO review_stats(decision, count) VALUES ('corrected', 0)")

            conn.commit()

        self._initialized = True
        print(f"[REVIEW_DB] Initialized review DB at {self.db_path}")


    # ------------ INSERT -----------------

    def insert_review(self, pair_id, reviewer, predicted, expected, decision, model_name):
        if not self._initialized:
            self.initialize()

        normalized_new = (decision or "").strip().lower()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:

                # DEBUG: Eingehende Daten
                print("\n[DEBUG] --- insert_review call ---")
                print("[DEBUG] incoming pair:", pair_id)
                print("[DEBUG] incoming reviewer:", reviewer)
                print("[DEBUG] incoming decision:", repr(normalized_new))

                # 1. existierende Review holen
                row = conn.execute("""
                    SELECT decision
                    FROM reviews
                    WHERE pair_id = ? AND reviewer = ?
                """, (pair_id, reviewer)).fetchone()

                if row is not None:
                    normalized_old = (row[0] or "").strip().lower()

                    print("[DEBUG] existing review found.")
                    print("[DEBUG] old decision:", repr(normalized_old))

                    # 2. gleiche decision → nichts tun
                    if normalized_old == normalized_new:
                        print("[INFO] Identical review detected → skipping")
                        return

                    print("[INFO] Decision changed → adjusting counters")

                    # 3. Counter: alte -1
                    conn.execute("""
                        UPDATE review_stats
                        SET count = count - 1
                        WHERE decision = ?
                    """, (normalized_old,))

                    # 4. Counter: neue +1
                    conn.execute("""
                        INSERT INTO review_stats(decision, count)
                        VALUES (?, 1)
                        ON CONFLICT(decision)
                        DO UPDATE SET count = count + 1
                    """, (normalized_new,))

                    # 5. Review updaten
                    conn.execute("""
                        UPDATE reviews
                        SET predicted=?, expected=?, decision=?, model_name=?, timestamp=?
                        WHERE pair_id=? AND reviewer=?
                    """, (
                        predicted,
                        expected,
                        normalized_new,
                        model_name,
                        datetime.now().isoformat(),
                        pair_id,
                        reviewer
                    ))
                    conn.commit()

                    print(f"[INFO] Review updated: {normalized_old} → {normalized_new}")
                    print("[DEBUG] counters updated.")
                    return

                else:
                    print("[DEBUG] no existing review found → inserting new one.")

                    # counter +1
                    conn.execute("""
                        INSERT INTO review_stats(decision, count)
                        VALUES (?, 1)
                        ON CONFLICT(decision)
                        DO UPDATE SET count = count + 1
                    """, (normalized_new,))

                    # review Insert
                    conn.execute("""
                        INSERT INTO reviews
                        (pair_id, reviewer, predicted, expected, decision, model_name, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pair_id,
                        reviewer,
                        predicted,
                        expected,
                        normalized_new,
                        model_name,
                        datetime.now().isoformat()
                    ))
                    conn.commit()

                    print("[INFO] New review inserted.")
                    print("[DEBUG] counter incremented.")



    # ------------ ANALYTICS -----------------

    def get_user_stats(self):
        if not self._initialized:
            self.initialize()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT reviewer,
                    SUM(CASE WHEN decision='accepted' THEN 1 ELSE 0 END) AS accepted,
                    SUM(CASE WHEN decision='corrected' THEN 1 ELSE 0 END) AS corrected
                FROM reviews
                GROUP BY reviewer
            """)

            stats = {}
            for reviewer, accepted, corrected in cursor.fetchall():
                stats[reviewer] = {
                    "accepted": accepted or 0,
                    "corrected": corrected or 0,
                    "total": (accepted or 0) + (corrected or 0)
                }

            return stats



    def get_model_stats(self):
        if not self._initialized:
            self.initialize()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT model_name, 
                       SUM(CASE WHEN decision='accepted' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN decision='corrected' THEN 1 ELSE 0 END)
                FROM reviews 
                GROUP BY model_name
            """)

            out = []
            for model, ok, wrong in cursor.fetchall():
                out.append({
                    "modelName": model,
                    "accepted": ok or 0,
                    "corrected": wrong or 0,
                    "accuracy": (ok / (ok + wrong)) if (ok + wrong) > 0 else None
                })
            return out


    def get_model_class_stats(self, model_name):
        if not self._initialized:
            self.initialize()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT
                    expected AS class,
                    SUM(CASE WHEN decision='accepted' THEN 1 ELSE 0 END) AS correct,
                    SUM(CASE WHEN decision='corrected' THEN 1 ELSE 0 END) AS incorrect
                FROM reviews
                WHERE model_name = ?
                GROUP BY expected
            """, (model_name,))

            rows = cursor.fetchall()

            out = []
            for class_name, correct, incorrect in rows:
                correct = correct or 0
                incorrect = incorrect or 0
                total = correct + incorrect
                error_rate = (incorrect / total) if total > 0 else 0.0

                out.append({
                    "class": class_name,
                    "correct": correct,
                    "incorrect": incorrect,
                    "errorRate": error_rate
                })

            # sort by error rate descending
            out.sort(key=lambda x: x["errorRate"], reverse=True)

            return out



# global singleton
_review_manager = ReviewDatabaseManager()

def init_review_db():
    _review_manager.initialize()

def insert_review(**kwargs):
    _review_manager.insert_review(**kwargs)

def get_user_review_stats():
    return _review_manager.get_user_stats()

def get_model_review_stats():
    return _review_manager.get_model_stats()

def get_model_class_stats():
    return _review_manager.get_model_class_stats()