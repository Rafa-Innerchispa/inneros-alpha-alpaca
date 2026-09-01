from __future__ import annotations

from typing import Any

from .config import Settings


class EvidenceStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def persist(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.inneros_mongo_uri:
            return {"ok": True, "stored": False, "reason": "mongo_uri_not_configured"}
        try:
            from pymongo import MongoClient

            client = MongoClient(self.settings.inneros_mongo_uri, serverSelectionTimeoutMS=2000)
            db = client[self.settings.inneros_mongo_db]
            result = db[collection].insert_one(document)
            return {"ok": True, "stored": True, "inserted_id": str(result.inserted_id)}
        except Exception as exc:
            return {"ok": False, "stored": False, "error": type(exc).__name__, "detail": str(exc)[:300]}
