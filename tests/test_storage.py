import time
import pytest
from cryptobot.storage import Storage


@pytest.fixture
def storage(tmp_path):
    db_path = tmp_path / "test_alerts.db"
    return Storage(str(db_path))


def test_initial_check_allows_alert(storage):
    assert storage.should_alert("BTCUSDT", "binance", "funding", cooldown_seconds=3600)


def test_cooldown_blocks_immediate_repeat(storage):
    storage.record_alert("BTCUSDT", "binance", "funding", {"rate": 0.002})
    assert not storage.should_alert("BTCUSDT", "binance", "funding", cooldown_seconds=3600)


def test_cooldown_is_per_exchange_and_type(storage):
    storage.record_alert("BTCUSDT", "binance", "funding", {"rate": 0.002})
    # different exchange should pass
    assert storage.should_alert("BTCUSDT", "bybit", "funding", cooldown_seconds=3600)
    # different alert type on same exchange should pass
    assert storage.should_alert("BTCUSDT", "binance", "price_spike", cooldown_seconds=3600)


def test_cooldown_expires(storage, monkeypatch):
    now = 1700000000.0
    monkeypatch.setattr(time, "time", lambda: now)

    storage.record_alert("ETHUSDT", "binance", "funding", {"rate": 0.001})
    assert not storage.should_alert("ETHUSDT", "binance", "funding", cooldown_seconds=60)

    # advance time past cooldown
    monkeypatch.setattr(time, "time", lambda: now + 65)
    assert storage.should_alert("ETHUSDT", "binance", "funding", cooldown_seconds=60)


def test_prune_old_records(storage, monkeypatch):
    base_time = 1700000000.0
    monkeypatch.setattr(time, "time", lambda: base_time)

    storage.record_alert("SOLUSDT", "binance", "price_spike", {"pct": 5.0})
    storage.record_alert("AVAXUSDT", "binance", "price_spike", {"pct": -6.0})

    # 3 days later
    monkeypatch.setattr(time, "time", lambda: base_time + 86400 * 3)
    storage.record_alert("BTCUSDT", "binance", "funding", {"rate": 0.001})

    # prune entries older than 2 days (172800s)
    deleted = storage.prune(max_age_seconds=172800)
    assert deleted == 2

    # recent record should still be in db
    with storage._connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()
        assert row[0] == 1
