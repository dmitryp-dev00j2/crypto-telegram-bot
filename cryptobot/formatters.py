def _fmt_price(val: float) -> str:
    if val < 0.0001:
        return f"${val:.8f}"
    elif val < 1.0:
        return f"${val:.4f}"
    elif val < 100.0:
        return f"${val:.2f}"
    return f"${val:,.2f}"


def format_funding_alert(
    symbol: str,
    exchange: str,
    rate_pct: float,
    predicted_pct: float | None = None,
    interval_hours: int = 8,
) -> str:
    # FIXME: bybit 8h vs 4h intervals mess up raw apr comparison on some weird pairs
    multiplier = (24 / interval_hours) * 365
    apr = rate_pct * multiplier
    
    icon = "🔥" if rate_pct > 0 else "🧊"
    tag = "SHORTS PAY" if rate_pct > 0 else "LONGS PAY (NEGATIVE)"

    # print(f"DEBUG: {symbol} rate={rate_pct} apr={apr}")

    lines = [
        f"{icon} *FUNDING ALERT* | `{exchange.upper()}`",
        f"Symbol: *{symbol}*",
        f"Rate: `{rate_pct:+.4f}%` / {interval_hours}h ({tag})",
        f"Est. APR: `{apr:+.1f}%`",
    ]
    
    if predicted_pct is not None:
        lines.append(f"Next period: `{predicted_pct:+.4f}%`")
        
    return "\n".join(lines)


def format_price_spike(
    symbol: str,
    exchange: str,
    change_pct: float,
    current_price: float,
    volume_24h: float | None = None,
    window_min: int = 5,
) -> str:
    icon = "🚀" if change_pct > 0 else "🩸"
    direction = "PUMP" if change_pct > 0 else "DUMP"
    
    lines = [
        f"{icon} *PRICE {direction}* ({window_min}m) | `{exchange.upper()}`",
        f"Symbol: *{symbol}*",
        f"Change: `{change_pct:+.2f}%`",
        f"Price: `{_fmt_price(current_price)}`",
    ]
    
    if volume_24h is not None:
        if volume_24h >= 1_000_000:
            vol_str = f"${volume_24h / 1_000_000:.1f}M"
        else:
            vol_str = f"${volume_24h / 1_000:.0f}K"
        lines.append(f"24h Vol: `{vol_str}`")
        
    return "\n".join(lines)


def format_spread_alert(symbol: str, binance_rate: float, bybit_rate: float) -> str:
    diff = binance_rate - bybit_rate
    abs_diff = abs(diff)
    
    return "\n".join([
        "⚡ *FUNDING DISCREPANCY*",
        f"Symbol: *{symbol}*",
        f"Binance: `{binance_rate:+.4f}%`",
        f"Bybit:   `{bybit_rate:+.4f}%`",
        f"Spread:  `{abs_diff:.4f}%`",
    ])
