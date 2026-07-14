import pytest
from cryptobot.formatters import escape_md, format_funding_alert, format_price_alert


def test_escape_md_special_chars():
    raw = "BTC_USDT [100%] *high* `alert` ~test~"
    escaped = escape_md(raw)
    assert "\_" in escaped
    assert "\[" in escaped
    assert "\*" in escaped
    assert "\`" in escaped
    assert "\~" in escaped


def test_escape_md_none_or_empty():
    assert escape_md("") == ""
    assert escape_md(None) == ""


def test_format_funding_alert_positive():
    msg = format_funding_alert(
        symbol="BTCUSDT",
        exchange="binance",
        rate=0.0015,
        annualized=164.25,
        next_funding_time="16:00 UTC",
    )
    assert "*BTCUSDT*" in msg
    assert "BINANCE" in msg
    assert "+0.1500%" in msg
    assert "164.25%" in msg
    assert "16:00 UTC" in msg


def test_format_funding_alert_negative():
    msg = format_funding_alert(
        symbol="ETHUSDT",
        exchange="bybit",
        rate=-0.00045,
        annualized=-49.275,
        next_funding_time="20:00 UTC",
    )
    assert "*ETHUSDT*" in msg
    assert "-0.0450%" in msg
    assert "BYBIT" in msg


def test_format_funding_extreme_value():
    # shitcoin extreme spike test
    msg = format_funding_alert(
        symbol="1000PEPEUSDT",
        exchange="binance",
        rate=-0.02,
        annualized=-2190.0,
        next_funding_time="00:00 UTC",
    )
    assert "-2.0000%" in msg
    assert "-2190.00%" in msg


def test_format_price_alert_pump():
    msg = format_price_alert(
        symbol="SOLUSDT",
        exchange="binance",
        price=145.20,
        change_pct=5.42,
        window_minutes=15,
    )
    assert "*SOLUSDT*" in msg
    assert "+5.42%" in msg
    assert "15m" in msg
    assert "145.2" in msg


def test_format_price_alert_dump():
    msg = format_price_alert(
        symbol="DOGEUSDT",
        exchange="bybit",
        price=0.12345,
        change_pct=-8.12,
        window_minutes=5,
    )
    assert "*DOGEUSDT*" in msg
    assert "-8.12%" in msg
    assert "5m" in msg
