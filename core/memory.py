import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from config import settings

class LocalMemoryStore:
    """Fallback local memory store using SQLite."""
    def __init__(self, db_path: str = "memories.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    text TEXT,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def add(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        metadata_str = json.dumps(metadata or {})
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO memories (user_id, text, metadata) VALUES (?, ?, ?)",
                (user_id, text, metadata_str)
            )
            conn.commit()
            return str(cursor.lastrowid)
        finally:
            conn.close()

    def search(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, text, metadata, timestamp FROM memories WHERE user_id = ? AND text LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, f"%{query}%", limit)
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
            
        results = []
        for row in rows:
            results.append({
                "id": str(row[0]),
                "text": row[1],
                "metadata": json.loads(row[2]),
                "timestamp": row[3]
            })
        return results

    def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, text, metadata, timestamp FROM memories WHERE user_id = ? ORDER BY timestamp DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
        finally:
            conn.close()
            
        results = []
        for row in rows:
            results.append({
                "id": str(row[0]),
                "text": row[1],
                "metadata": json.loads(row[2]),
                "timestamp": row[3]
            })
        return results

    def delete(self, memory_id: str):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
        finally:
            conn.close()

class MemoryManager:
    """Manages memory using Mem0 or fallback to LocalMemoryStore."""
    def __init__(self):
        self.use_mem0 = bool(settings.MEM0_API_KEY)
        if self.use_mem0:
            try:
                from mem0 import Memory
                self.client = Memory()
            except ImportError:
                print("Failed to import mem0, using local fallback.")
                self.use_mem0 = False
                self.client = LocalMemoryStore()
        else:
            self.client = LocalMemoryStore()

    def add_memory(self, user_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        if self.use_mem0:
            res = self.client.add(text, user_id=user_id, metadata=metadata)
            return res.get("id") if isinstance(res, dict) else str(res)
        else:
            return self.client.add(user_id, text, metadata)

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if self.use_mem0:
            res = self.client.search(query, user_id=user_id, limit=limit)
            # Normalize to uniform format
            normalized = []
            for r in res:
                normalized.append({
                    "id": r.get("id"),
                    "text": r.get("memory"),
                    "metadata": r.get("metadata", {}),
                    "timestamp": r.get("created_at")
                })
            return normalized
        else:
            return self.client.search(user_id, query, limit)

    def get_all_memories(self, user_id: str) -> List[Dict[str, Any]]:
        if self.use_mem0:
            res = self.client.get_all(user_id=user_id)
            normalized = []
            for r in res:
                normalized.append({
                    "id": r.get("id"),
                    "text": r.get("memory"),
                    "metadata": r.get("metadata", {}),
                    "timestamp": r.get("created_at")
                })
            return normalized
        else:
            return self.client.get_all(user_id)

    def delete_memory(self, memory_id: str):
        if self.use_mem0:
            self.client.delete(memory_id)
        else:
            self.client.delete(memory_id)
