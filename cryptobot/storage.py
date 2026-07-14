import sqlite3
import time
from pathlib import Path


class AlertStorage:
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_log (
                    key TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    last_sent_at REAL NOT NULL,
                    last_value REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_log_sent ON alert_log(last_sent_at)"
            )

    def should_alert(self, key: str, cooldown_seconds: float) -> bool:
        now = time.time()
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_sent_at FROM alert_log WHERE key = ?", (key,)
            ).fetchone()
            if row is None:
                return True
            return (now - float(row["last_sent_at"])) >= cooldown_seconds

    def record_alert(self, key: str, symbol: str, alert_type: str, value: float) -> None:
        now = time.time()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO alert_log (key, symbol, alert_type, last_sent_at, last_value)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    last_sent_at = excluded.last_sent_at,
                    last_value = excluded.last_value
                """,
                (key, symbol, alert_type, now, value),
            )

    def prune(self, max_age_seconds: float = 86400 * 7) -> int:
        cutoff = time.time() - max_age_seconds
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM alert_log WHERE last_sent_at < ?", (cutoff,))
            return cur.rowcount
