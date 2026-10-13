import json
from datetime import datetime, timedelta
from pathlib import Path

from utils.common import BASE_DIR
from utils.log import log

GRUDGE_FILE = BASE_DIR / "grudge.json"
GRUDGE_WINDOW_HOURS = 12


class GrudgeList:
    def add(self, user_id: int) -> None:
        data = self._load()
        expiry = (datetime.now() + timedelta(hours=GRUDGE_WINDOW_HOURS)).isoformat()
        data[str(user_id)] = expiry
        self._save(data)
        log.info(f"Grudge added for user {user_id}, expires {expiry}")

    def holds_grudge(self, user_id: int) -> bool:
        data = self._load()
        key = str(user_id)
        if key not in data:
            return False
        if datetime.now() > datetime.fromisoformat(data[key]):
            del data[key]
            self._save(data)
            log.info(f"Grudge expired for user {user_id}")
            return False
        return True

    def _load(self) -> dict:
        if not GRUDGE_FILE.exists():
            return {}
        with GRUDGE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict) -> None:
        with GRUDGE_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
