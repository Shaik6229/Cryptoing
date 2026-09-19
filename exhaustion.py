from config import EXTREME_EMA200_DISTANCE_ATR

def evaluate_top_exhaustion(c4, exit_score):
    reversal_confirmation = (
        c4["crossed_below_ema20"]
        and c4["rsi_turning_down"]
        and c4["macd_hist_weakening"]
        and c4["bearish_rejection"]
        and (
            exit_score >= 45
            or c4["bearish_div"]
            or c4["ema200_distance_atr"] >= EXTREME_EMA200_DISTANCE_ATR
            or c4["rsi"] > 65
        )
    )

    if reversal_confirmation:
        reasons = [
            "Price has closed back below the 4H 20-EMA.",
            "Momentum is weakening instead of continuing upward.",
            "RSI has started turning down.",
            "The latest candle shows signs that sellers are taking control."
        ]
        if c4["bearish_div"]:
            reasons.append("Price and momentum are no longer moving together.")
        return {"type": "TOP_REVERSAL_CONFIRMED", "reasons": reasons}

    deterioration_count = 0
    reasons = []

    if c4["rsi_turning_down"]:
        deterioration_count += 1
        reasons.append(f"RSI has started falling ({c4['prev_rsi']:.1f} → {c4['rsi']:.1f}).")

    if c4["macd_hist_weakening"]:
        deterioration_count += 1
        reasons.append("Momentum is starting to weaken.")

    if c4["bearish_rejection"]:
        deterioration_count += 1
        reasons.append("The latest candle shows selling/rejection near the top.")

    if c4["bearish_div"]:
        deterioration_count += 1
        reasons.append("Price is making a stronger push while momentum is weaker.")

    exhaustion_background = (
        exit_score >= 45
        or c4["rsi"] > 70
        or c4["ema200_distance_atr"] >= EXTREME_EMA200_DISTANCE_ATR
        or c4["bearish_div"]
    )

    if exhaustion_background and deterioration_count >= 2:
        return {"type": "TOP_EXHAUSTION_DEVELOPING", "reasons": reasons}

    if exit_score >= 45:
        return {"type": "RALLY_OVERHEATING", "reasons": []}

    return None

def evaluate_bottom_exhaustion(c4, buy_score):
    bottom_background = (
        buy_score >= 45
        or c4["bullish_div"]
        or c4["ema200_distance_atr"] <= -EXTREME_EMA200_DISTANCE_ATR
        or c4["rsi"] < 35.0
    )

    if not bottom_background:
        return None

    improvement_count = 0
    reasons = []

    if c4["rsi_turning_up"]:
        improvement_count += 1
        reasons.append(f"RSI is starting to recover ({c4['prev_rsi']:.1f} → {c4['rsi']:.1f}).")

    if c4["macd_hist_strengthening"]:
        improvement_count += 1
        reasons.append("MACD histogram is strengthening, showing that downward momentum is easing.")

    if c4["bullish_rejection"]:
        improvement_count += 1
        reasons.append("The latest 4H candle shows buyers rejecting lower prices.")

    if c4["bullish_div"]:
        improvement_count += 1
        reasons.append("Price is testing weakness while momentum is stronger than before.")

    reversal_confirmation = (
        c4["crossed_above_ema20"]
        and c4["rsi_turning_up"]
        and c4["macd_hist_strengthening"]
        and c4["bullish_rejection"]
        and (
            buy_score >= 45
            or c4["bullish_div"]
            or c4["ema200_distance_atr"] <= -EXTREME_EMA200_DISTANCE_ATR
            or c4["rsi"] < 35.0
        )
    )

    if reversal_confirmation:
        confirmed_reasons = [
            "Price has closed back above the 4H 20-EMA.",
            "RSI has started turning upward.",
            "Momentum is strengthening.",
            "The latest candle shows buyers rejecting lower prices."
        ]
        if c4["bullish_div"]:
            confirmed_reasons.append("Price and momentum are showing bullish divergence.")
        return {"type": "BOTTOM_REVERSAL_CONFIRMED", "reasons": confirmed_reasons}

    if improvement_count >= 2:
        return {"type": "BOTTOM_EXHAUSTION_DEVELOPING", "reasons": reasons}

    if improvement_count >= 1:
        return {"type": "SELLING_PRESSURE_EASING", "reasons": reasons}

    return None
