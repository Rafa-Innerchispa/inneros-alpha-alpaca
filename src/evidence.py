from __future__ import annotations

import os
from typing import Any

from pymongo import MongoClient

from .models import PipelineResult


class EvidenceStore:
    """Persist pipeline evidence without making persistence a trading dependency.

    Memory is always available. Mongo is optional and enabled only when
    INNEROS_MONGO_URI is configured. Mongo failures never turn into fake success;
    the caller can inspect backend/error state in health metadata.
    """

    def __init__(self) -> None:
        self.mongo_uri = os.getenv("INNEROS_MONGO_URI", "").strip()
        self.db_name = os.getenv("INNEROS_MONGO_DB", "inneros_alpha_alpaca")
        self.collection_name = os.getenv("INNEROS_MONGO_COLLECTION", "pipeline_runs")
        self._memory: dict[str, dict[str, Any]] = {}
        self.last_error: str | None = None

    @property
    def backend(self) -> str:
        return "mongo+memory" if self.mongo_uri else "memory"

    def _collection(self):
        if not self.mongo_uri:
            return None
        client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=1200)
        client.admin.command("ping")
        return client[self.db_name][self.collection_name]

    def persist(self, result: PipelineResult) -> None:
        document = result.model_dump(mode="json")
        document["schema_version"] = "inneros.alpha.evidence.v1"
        self._memory[result.correlation_id] = document
        if not self.mongo_uri:
            return
        try:
            collection = self._collection()
            collection.replace_one(
                {"correlation_id": result.correlation_id},
                document,
                upsert=True,
            )
            self.last_error = None
        except Exception as exc:
            self.last_error = type(exc).__name__

    def get(self, correlation_id: str) -> dict[str, Any] | None:
        cached = self._memory.get(correlation_id)
        if cached is not None:
            return cached
        if not self.mongo_uri:
            return None
        try:
            collection = self._collection()
            document = collection.find_one({"correlation_id": correlation_id}, {"_id": 0})
            self.last_error = None
            return document
        except Exception as exc:
            self.last_error = type(exc).__name__
            return None
