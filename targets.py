def select_resistance_targets(c4, reference_price=None):
    p = reference_price if reference_price is not None else c4["price"]
    atr = c4["atr"]
    if atr <= 0: atr = p * 0.03

    candidates = []

    def add_candidate(price, level_type, base_score, index=None):
        if price is None: return
        price = float(price)
        if price <= p * 1.003: return

        recency_score = 0.0
        if index is not None:
            age = max(0, c4["_idx"] - index)
            if age <= 24: recency_score = 2.0
            elif age <= 48: recency_score = 1.5
            elif age <= 72: recency_score = 1.0
            else: recency_score = 0.5

        candidates.append({"price": price, "type": level_type, "score": (base_score + recency_score), "index": index})

    add_candidate(c4["ema50"], "4H 50-EMA", 3.0)
    add_candidate(c4["ema200"], "4H 200-EMA", 3.0)
    add_candidate(c4["consolidation_high"], "12-Candle Consolidation Resistance", 4.0)

    for index, price in c4.get("recent_swing_highs", []):
        add_candidate(price, "Confirmed 4H Swing Resistance", 5.0, index)

    if not candidates:
        tp1 = p + atr
        tp2 = p + 2.5 * atr
        return {
            "tp1": tp1, "tp2": tp2,
            "tp1_type": "1.0 ATR Projection", "tp2_type": "2.5 ATR Projection",
            "tp1_pct": ((tp1 - p) / p) * 100, "tp2_pct": ((tp2 - p) / p) * 100,
            "tp1_atr": (tp1 - p) / atr, "tp2_atr": (tp2 - p) / atr,
            "tp1_score": 0, "tp2_score": 0
        }

    cluster_tolerance = max(0.30 * atr, p * 0.003)
    candidates.sort(key=lambda x: x["price"])
    clusters = []

    for candidate in candidates:
        placed = False
        for cluster in clusters:
            cluster_price = sum(x["price"] for x in cluster) / len(cluster)
            if abs(candidate["price"] - cluster_price) <= cluster_tolerance:
                cluster.append(candidate)
                placed = True
                break
        if not placed:
            clusters.append([candidate])

    resistance_levels = []
    for cluster in clusters:
        cluster_price = sum(x["price"] for x in cluster) / len(cluster)
        score = sum(x["score"] for x in cluster)
        if len(cluster) >= 2: score += 2.0
        if len(cluster) >= 3: score += 2.0
        types = list(dict.fromkeys(x["type"] for x in cluster))
        resistance_levels.append({"price": cluster_price, "score": score, "types": types, "members": cluster})

    resistance_levels.sort(key=lambda x: x["price"])
    meaningful = []

    for level in resistance_levels:
        distance_atr = (level["price"] - p) / atr
        distance_pct = ((level["price"] - p) / p) * 100
        if distance_atr < 0.50 and level["score"] < 8:
            continue
        meaningful.append({**level, "distance_atr": distance_atr, "distance_pct": distance_pct})

    if meaningful:
        tp1_info = meaningful[0]
    else:
        tp1_price = p + atr
        tp1_info = {"price": tp1_price, "score": 0, "types": ["1.0 ATR Projection"], "distance_atr": 1.0, "distance_pct": ((tp1_price - p) / p) * 100}

    tp1 = tp1_info["price"]
    tp2_candidates = [x for x in meaningful if x["price"] > (tp1 + max(0.25 * atr, p * 0.0025))]

    if tp2_candidates:
        tp2_info = tp2_candidates[0]
    else:
        tp2_price = p + 2.5 * atr
        if tp2_price <= tp1:
            tp2_price = tp1 + 0.75 * atr
        tp2_info = {"price": tp2_price, "score": 0, "types": ["2.5 ATR Projection"], "distance_atr": ((tp2_price - p) / atr), "distance_pct": ((tp2_price - p) / p) * 100}

    tp2 = tp2_info["price"]
    max_tp2 = p + 5.0 * atr

    if tp2 > max_tp2:
        tp2 = max_tp2
        tp2_info = {"price": tp2, "score": 0, "types": ["5 ATR Maximum Extension"], "distance_atr": 5.0, "distance_pct": ((tp2 - p) / p) * 100}

    return {
        "tp1": tp1, "tp2": tp2,
        "tp1_type": " + ".join(tp1_info["types"]),
        "tp2_type": " + ".join(tp2_info["types"]),
        "tp1_pct": (((tp1 - p) / p) * 100),
        "tp2_pct": (((tp2 - p) / p) * 100),
        "tp1_atr": ((tp1 - p) / atr),
        "tp2_atr": ((tp2 - p) / atr),
        "tp1_score": tp1_info.get("score", 0),
        "tp2_score": tp2_info.get("score", 0)
    }

def select_ignition_targets(c4, reference_price=None):
    return select_resistance_targets(c4, reference_price)
