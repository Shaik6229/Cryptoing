from structure import format_price
from targets import select_resistance_targets

def analyze_market_direction(c4, ob, d1, live_price=None):
    technical_price = c4["price"]
    p = live_price if live_price is not None else technical_price

    up_score = 0
    down_score = 0
    drivers = []

    if technical_price > c4["ema20"]:
        up_score += 2
        drivers.append("price is above the short-term trend")
    else:
        down_score += 2
        drivers.append("price is below the short-term trend")

    if technical_price > c4["ema50"]: up_score += 1
    else: down_score += 1

    if c4["hist_slope_up"]:
        up_score += 2
        drivers.append("momentum is improving")
    elif c4["hist_slope_down"]:
        down_score += 2
        drivers.append("momentum is weakening")

    if c4["rsi"] >= 52: up_score += 1
    elif c4["rsi"] <= 48: down_score += 1

    if c4["bullish_div"]:
        up_score += 2
        drivers.append("buyers are showing stronger momentum")
    elif c4["bearish_div"]:
        down_score += 2
        drivers.append("buyers are showing weaker momentum")

    if not d1["is_bearish"]:
        up_score += 1
    else:
        down_score += 1
        drivers.append("the daily trend is still weak")

    if ob["bid_depth_1pct"] > 0 and ob["ask_depth_1pct"] > 0:
        if ob["bid_depth_1pct"] > 1.2 * ob["ask_depth_1pct"]:
            drivers.append("visible bid liquidity is currently stronger")
        elif ob["ask_depth_1pct"] > 1.2 * ob["bid_depth_1pct"]:
            drivers.append("visible sell liquidity is currently stronger")

    reason_str = ", ".join(drivers[:2]) if drivers else "mixed conditions"

    if up_score >= down_score + 2:
        verdict = "🔼 UP BIAS"
        targets = select_resistance_targets(c4, reference_price=p)
        floors = [v for v in [c4["ema20"], ob["bid_wall_price"], c4["structural_low"]] if v < p * 0.995]
        floor_price = max(floors) if floors else p * 0.95
        action_note = (
            f"Target: ${format_price(targets['tp1'])} "
            f"({targets['tp1_type']} | +{targets['tp1_pct']:.1f}% | {targets['tp1_atr']:.1f} ATR) | "
            f"Support: ${format_price(floor_price)} ({reason_str})"
        )
    elif down_score >= up_score + 2:
        verdict = "🔽 DOWN BIAS"
        downside_candidates = [v for v in [c4["ema20"], c4["ema50"], ob["bid_wall_price"], c4["structural_low"]] if v < p * 0.995]
        target_price = max(downside_candidates) if downside_candidates else p * 0.95
        ceilings = [v for v in [c4["ema20"], c4["ema50"], ob["ask_wall_price"]] if v > p * 1.005]
        ceiling_price = min(ceilings) if ceilings else p * 1.05
        action_note = f"Downside: ${format_price(target_price)} | Ceiling: ${format_price(ceiling_price)} ({reason_str})"
    else:
        verdict = "⚖️ SIDEWAYS"
        action_note = f"Range: ${format_price(c4['low'])} – ${format_price(c4['high'])} (Price is moving without a clear direction)"

    return verdict, action_note
