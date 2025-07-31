# database.py - Synchronous drop-in replacement for your JSON operations
import sqlite3
import json
from datetime import datetime
import os
from typing import Dict, Any
import threading

class DatabaseManager:
    """
    Synchronous drop-in replacement for JSON file operations.
    Provides the exact same interface but uses SQLite for reliability.
    """
    
    def __init__(self, db_path: str = "annotations.db", json_backup_path: str = "highscore_list.json"):
        self.db_path = db_path
        self.json_backup_path = json_backup_path
        self._lock = threading.Lock()  # Thread safety for concurrent requests
        self._initialized = False
    
    def initialize(self):
        """Initialize the database - call this once at startup"""
        if self._initialized:
            return
            
        with sqlite3.connect(self.db_path) as conn:
            # Store the entire JSON structure as a single document
            conn.execute("""
                CREATE TABLE IF NOT EXISTS json_data (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Check if we have data
            cursor = conn.execute("SELECT value FROM json_data WHERE key = 'main'")
            result = cursor.fetchone()
            
            if not result:
                # Try to migrate from existing JSON file
                self._migrate_from_json(conn)
            
            conn.commit()
        
        self._initialized = True
        print(f"[DATABASE] Initialized SQLite database at {self.db_path}")
    
    def read_data(self) -> Dict[str, Any]:
        """
        Read data - exact same interface as your JSON version!
        Returns: dict with 'users', 'totalAnnotations', 'lastUpdated'
        """
        if not self._initialized:
            self.initialize()
            
        with self._lock:  # Thread safety
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT value FROM json_data WHERE key = 'main'")
                result = cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                else:
                    # Return empty structure if no data
                    return {
                        "users": {},
                        "totalAnnotations": 0,
                        "lastUpdated": datetime.now().isoformat()
                    }
    
    def write_data(self, data: Dict[str, Any]):
        """
        Write data - exact same interface as your JSON version!
        Args: data dict with 'users', 'totalAnnotations', 'lastUpdated'
        """
        if not self._initialized:
            self.initialize()
            
        with self._lock:  # Thread safety
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                
                # Update or insert the main data
                conn.execute("""
                    INSERT OR REPLACE INTO json_data (key, value, updated_at) 
                    VALUES ('main', ?, ?)
                """, (json.dumps(data, indent=2), now))
                
                conn.commit()
    
    def _migrate_from_json(self, conn):
        """Migrate data from existing JSON file if it exists"""
        if not os.path.exists(self.json_backup_path):
            # No existing file, create empty structure
            initial_data = {
                "users": {},
                "totalAnnotations": 0,
                "lastUpdated": datetime.now().isoformat()
            }
            
            conn.execute("""
                INSERT INTO json_data (key, value, created_at, updated_at) 
                VALUES ('main', ?, ?, ?)
            """, (
                json.dumps(initial_data, indent=2), 
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            print("[DATABASE] Created new empty database")
            return
        
        # Migrate from existing JSON file
        print(f"[DATABASE] Migrating from {self.json_backup_path}...")
        
        with open(self.json_backup_path, 'r') as f:
            json_data = json.load(f)
        
        conn.execute("""
            INSERT INTO json_data (key, value, created_at, updated_at) 
            VALUES ('main', ?, ?, ?)
        """, (
            json.dumps(json_data, indent=2),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # Backup the original file
        backup_name = f"{self.json_backup_path}.backup"
        os.rename(self.json_backup_path, backup_name)
        print(f"[DATABASE] Migration complete! Original file backed up as {backup_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if not self._initialized:
            self.initialize()
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT created_at, updated_at 
                FROM json_data 
                WHERE key = 'main'
            """)
            result = cursor.fetchone()
            
            data = self.read_data()
            
            return {
                "database_path": self.db_path,
                "database_created": result[0] if result else None,
                "database_updated": result[1] if result else None,
                "total_users": len(data["users"]),
                "total_annotations": data["totalAnnotations"],
                "last_updated": data["lastUpdated"]
            }

# Create global instance
_db_manager = DatabaseManager()

# PUBLIC API - These are your EXACT drop-in replacements!

def initialize_data_file():
    """EXACT drop-in replacement for your initialize_data_file() function"""
    _db_manager.initialize()

def read_data() -> Dict[str, Any]:
    """EXACT drop-in replacement for your read_data() function"""
    return _db_manager.read_data()

def write_data(data: Dict[str, Any]):
    """EXACT drop-in replacement for your write_data() function"""
    _db_manager.write_data(data)

# Bonus: Additional utility functions
def get_database_stats():
    """Get database health and statistics"""
    return _db_manager.get_stats()

def backup_to_json(backup_path: str = None):
    """Export current data back to JSON format"""
    if backup_path is None:
        backup_path = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    data = read_data()
    with open(backup_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[DATABASE] Data backed up to {backup_path}")
    return backup_path