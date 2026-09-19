from config import RELIEF_EMA20_STRETCH_ATR, EXTREME_EMA200_DISTANCE_ATR
from targets import select_ignition_targets
from exhaustion import evaluate_top_exhaustion, evaluate_bottom_exhaustion

def evaluate_market_condition(c4, ob, d1, target_price_reference=None):
    p = c4["price"]
    ema20 = c4["ema20"]
    ema20_distance_atr = c4["ema20_distance_atr"]

    active_setups = []

    if (
        d1["is_bearish"]
        and ema20_distance_atr <= -RELIEF_EMA20_STRETCH_ATR
        and c4["rsi"] <= 28.0
        and c4["vol_ratio"] >= 2.2
    ):
        tp1 = ema20
        tp2_candidates = [v for v in [c4["ema50"], c4["consolidation_high"], c4["structural_high"]] if v > tp1]
        tp2 = min(tp2_candidates) if tp2_candidates else tp1 * 1.04

        active_setups.append({
            "type": "RELIEF_SCALP",
            "ema_stretch": (((p - ema20) / ema20) * 100 if ema20 != 0 else 0),
            "ema_stretch_atr": abs(ema20_distance_atr),
            "tp1": tp1,
            "tp2": tp2,
            "stop": c4["low"] * 0.992
        })

    if (
        c4["candles_below_ema20"] >= 10
        and p > ema20
        and c4["open"] <= ema20 * 1.005
        and p >= c4["consolidation_high"] * 0.998
        and c4["vol_ratio"] >= 1.6
        and c4["bullish_candle"]
        and c4["upper_wick"] <= 0.25
        and (c4["macd_hist_crossed_positive"] or c4["hist_slope_up"])
    ):
        targets = select_ignition_targets(c4, reference_price=target_price_reference)
        active_setups.append({
            "type": "ACCUMULATION_IGNITION",
            "tp1": targets["tp1"], "tp2": targets["tp2"],
            "tp1_type": targets["tp1_type"], "tp2_type": targets["tp2_type"],
            "tp1_pct": targets["tp1_pct"], "tp2_pct": targets["tp2_pct"],
            "tp1_atr": targets["tp1_atr"], "tp2_atr": targets["tp2_atr"],
            "tp1_score": targets["tp1_score"], "tp2_score": targets["tp2_score"],
            "stop": min(c4["low"], p * 0.96),
            "reasons": [
                f"Price spent {c4['candles_below_ema20']} candles below its short-term trend before breaking upward.",
                f"Trading activity suddenly increased ({c4['vol_ratio']:.1f}x normal).",
                "Price pushed back above the recent consolidation area.",
                "Momentum has turned upward."
            ]
        })

    buy_score = 0
    exit_score = 0
    buy_factors = []
    exit_factors = []

    if p - c4["structural_low"] <= 1.5 * c4["atr"]:
        buy_score += 15
        buy_factors.append("Price is close to the lowest major level in the 4H lookback.")

    if c4["ema200_distance_atr"] <= -EXTREME_EMA200_DISTANCE_ATR:
        buy_score += 10
        buy_factors.append(f"Price is deeply extended below its long-term 4H trend ({c4['ema200_distance_atr']:.1f} ATR below EMA200).")

    if c4["rsi"] < 30:
        buy_score += 15
        buy_factors.append(f"Selling has become extreme (RSI {c4['rsi']:.1f}).")

    if c4["bullish_div"]:
        buy_score += 15
        buy_factors.append("Price is showing stronger buying momentum than before.")

    if c4["lower_wick"] >= 0.35:
        buy_score += 10
        buy_factors.append("Buyers strongly rejected lower prices.")

    if c4["structural_high"] - p <= 1.5 * c4["atr"]:
        exit_score += 15
        exit_factors.append("Price is close to the highest major level in the 4H lookback.")

    if c4["ema200_distance_atr"] >= EXTREME_EMA200_DISTANCE_ATR:
        exit_score += 10
        exit_factors.append(f"Price is deeply extended above its long-term 4H trend ({c4['ema200_distance_atr']:.1f} ATR above EMA200).")

    if c4["rsi"] > 70:
        exit_score += 15
        exit_factors.append(f"The rally is extremely stretched (RSI {c4['rsi']:.1f}).")

    if c4["bearish_div"]:
        exit_score += 15
        exit_factors.append("Price is pushing higher while momentum is becoming weaker.")

    if c4["upper_wick"] >= 0.35:
        exit_score += 10
        exit_factors.append("Sellers strongly rejected higher prices.")

    if d1["is_bearish"]:
        buy_score = max(0, buy_score - 25)

    if buy_score >= 65:
        active_setups.append({"type": "BUY_CONFIRMED", "score": buy_score, "reasons": buy_factors})
    elif buy_score >= 45:
        active_setups.append({"type": "BUY_EARLY", "score": buy_score, "reasons": buy_factors})

    top_setup = evaluate_top_exhaustion(c4, exit_score)
    if top_setup is not None:
        if top_setup["type"] == "TOP_REVERSAL_CONFIRMED":
            active_setups.append(top_setup)
        elif top_setup["type"] == "TOP_EXHAUSTION_DEVELOPING":
            top_setup["score"] = exit_score
            active_setups.append(top_setup)
        elif top_setup["type"] == "RALLY_OVERHEATING":
            top_setup["score"] = exit_score
            top_setup["reasons"] = exit_factors
            active_setups.append(top_setup)

    bottom_setup = evaluate_bottom_exhaustion(c4, buy_score)
    if bottom_setup is not None:
        if bottom_setup["type"] == "BOTTOM_REVERSAL_CONFIRMED":
            active_setups.append(bottom_setup)
        elif bottom_setup["type"] == "BOTTOM_EXHAUSTION_DEVELOPING":
            bottom_setup["score"] = buy_score
            active_setups.append(bottom_setup)
        elif bottom_setup["type"] == "SELLING_PRESSURE_EASING":
            bottom_setup["score"] = buy_score
            active_setups.append(bottom_setup)

    return active_setups
