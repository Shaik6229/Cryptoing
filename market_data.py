import statistics
from config import logger, L1_L2_UNIVERSE, AI_UNIVERSE, CORE_WATCHLIST
from http_client import HTTP
from indicators import calculate_wilder_rsi, calculate_ema, calculate_atr, calculate_macd

def fetch_1d_context(symbol):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=1d&limit=500"
        res = HTTP.get(url, timeout=8)
        res.raise_for_status()

        raw = res.json()
        closes = [float(c[4]) for c in raw]

        if len(closes) < 3:
            raise ValueError("Insufficient 1D candle data")

        idx = len(closes) - 2
        rsi_series = calculate_wilder_rsi(closes)
        ema50 = calculate_ema(closes, 50)
        ema200 = calculate_ema(closes, 200)

        c_price = closes[idx]
        c_rsi = rsi_series[idx]
        c_ema50 = ema50[idx]
        c_ema200 = ema200[idx]

        bearish_points = 0
        if c_price < c_ema50: bearish_points += 1
        if c_ema50 < c_ema200: bearish_points += 1
        if c_rsi < 45: bearish_points += 1

        return {
            "price": c_price,
            "rsi": c_rsi,
            "ema50": c_ema50,
            "ema200": c_ema200,
            "is_bearish": (bearish_points >= 2)
        }
    except Exception as e:
        logger.warning(f"Could not fetch 1D context for {symbol}: {e}")
        return {"price": 0, "rsi": 50.0, "ema50": 0, "ema200": 0, "is_bearish": False}


def fetch_live_price(symbol):
    try:
        url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
        res = HTTP.get(url, timeout=6)
        res.raise_for_status()
        return float(res.json()["price"])
    except Exception as e:
        logger.warning(f"Could not fetch live price for {symbol}: {e}")
        return None


def fetch_4h_data(symbol, limit=500):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval=4h&limit={limit}"
    res = HTTP.get(url, timeout=10)
    res.raise_for_status()

    raw = res.json()
    if len(raw) < 50:
        raise ValueError(f"Insufficient 4H candle data for {symbol}")

    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    for c in raw:
        opens.append(float(c[1]))
        highs.append(float(c[2]))
        lows.append(float(c[3]))
        closes.append(float(c[4]))
        volumes.append(float(c[5]))

    idx = len(closes) - 2

    rsi_series = calculate_wilder_rsi(closes)
    _, _, macd_hist = calculate_macd(closes)
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)
    atr = calculate_atr(highs, lows, closes)

    c_open, c_close, c_low, c_high = opens[idx], closes[idx], lows[idx], highs[idx]
    c_rsi, c_hist, c_atr = rsi_series[idx], macd_hist[idx], atr[idx]

    prev_hist, prev_rsi = macd_hist[idx - 1], rsi_series[idx - 1]
    prev_close, prev_open, prev_high, prev_low = closes[idx - 1], opens[idx - 1], highs[idx - 1], lows[idx - 1]

    ema200_distance_atr = ((c_close - ema200[idx]) / c_atr if c_atr > 0 else 0.0)
    ema20_distance_atr = ((c_close - ema20[idx]) / c_atr if c_atr > 0 else 0.0)

    prior_lows = lows[:idx]
    prior_highs = highs[:idx]

    struct_low = min(prior_lows) if prior_lows else c_low
    struct_high = max(prior_highs) if prior_highs else c_high
    s_low_idx = prior_lows.index(struct_low) if prior_lows else 0
    s_high_idx = prior_highs.index(struct_high) if prior_highs else 0

    local_lows = [(i, lows[i]) for i in range(5, idx - 5) if lows[i] == min(lows[i - 5:i + 6])]
    local_highs = [(i, highs[i]) for i in range(5, idx - 5) if highs[i] == max(highs[i - 5:i + 6])]

    r_low_idx, r_low = local_lows[-1] if local_lows else (s_low_idx, struct_low)
    r_high_idx, r_high = local_highs[-1] if local_highs else (s_high_idx, struct_high)

    resistance_lookback = min(120, idx)
    resistance_start = max(0, idx - resistance_lookback)
    recent_highs = highs[resistance_start:idx]
    recent_swing_highs = [(i, highs[i]) for i in range(max(5, resistance_start), idx - 5) if highs[i] == max(highs[i - 5:i + 6])]

    consolidation_start = max(0, idx - 12)
    consolidation_high = max(highs[consolidation_start:idx]) if idx > 0 else c_high

    vol_window = volumes[max(0, idx - 20):idx]
    vol_median = statistics.median(vol_window) if vol_window else 1.0

    candle_range = (c_high - c_low)
    lower_wick_ratio = ((min(c_open, c_close) - c_low) / candle_range if candle_range > 0 else 0)
    upper_wick_ratio = ((c_high - max(c_open, c_close)) / candle_range if candle_range > 0 else 0)

    candles_below_ema20 = 0
    for i in range(idx - 1, max(0, idx - 25), -1):
        if closes[i] < ema20[i]:
            candles_below_ema20 += 1
        else:
            break

    return {
        "price": c_close,
        "open": c_open,
        "low": c_low,
        "high": c_high,
        "prev_price": prev_close,
        "prev_open": prev_open,
        "prev_low": prev_low,
        "prev_high": prev_high,
        "structural_low": struct_low,
        "structural_high": struct_high,
        "recent_swing_highs": recent_swing_highs,
        "recent_resistance_high": (max(recent_swing_highs, key=lambda x: x[1])[1] if recent_swing_highs else (max(recent_highs) if recent_highs else c_high)),
        "_idx": idx,
        "rsi": c_rsi,
        "prev_rsi": prev_rsi,
        "rsi_turning_down": (c_rsi < prev_rsi),
        "rsi_turning_up": (c_rsi > prev_rsi),
        "hist_slope_up": (c_hist > prev_hist),
        "hist_slope_down": (c_hist < prev_hist),
        "macd_hist_weakening": (c_hist < prev_hist),
        "macd_hist_strengthening": (c_hist > prev_hist),
        "macd_hist_crossed_positive": (c_hist > 0 and prev_hist <= 0),
        "bullish_div": (c_low <= r_low * 1.015 and c_rsi > rsi_series[r_low_idx]),
        "bearish_div": (c_high >= r_high * 0.985 and c_rsi < rsi_series[r_high_idx]),
        "vol_ratio": (volumes[idx] / vol_median if vol_median > 0 else 1.0),
        "lower_wick": lower_wick_ratio,
        "upper_wick": upper_wick_ratio,
        "bullish_candle": (c_close > c_open),
        "bearish_candle": (c_close < c_open),
        "bearish_rejection": (upper_wick_ratio >= 0.25 or (c_close < c_open and c_close < prev_close)),
        "strong_bearish_rejection": (upper_wick_ratio >= 0.35 or (c_close < c_open and c_close < prev_close and c_close <= (c_low + candle_range * 0.40))),
        "bullish_rejection": (lower_wick_ratio >= 0.25 or (c_close > c_open and c_close > prev_close)),
        "strong_bullish_rejection": (lower_wick_ratio >= 0.35 or (c_close > c_open and c_close > prev_close and c_close >= (c_low + candle_range * 0.60))),
        "ema20": ema20[idx],
        "ema50": ema50[idx],
        "ema200": ema200[idx],
        "prev_ema20": ema20[idx - 1],
        "below_ema20": (c_close < ema20[idx]),
        "crossed_below_ema20": (c_close < ema20[idx] and prev_close >= ema20[idx - 1]),
        "above_ema20": (c_close > ema20[idx]),
        "crossed_above_ema20": (c_close > ema20[idx] and prev_close <= ema20[idx - 1]),
        "ema200_ext": (((c_close - ema200[idx]) / ema200[idx]) * 100 if ema200[idx] != 0 else 0),
        "ema200_distance_atr": ema200_distance_atr,
        "ema20_distance_atr": ema20_distance_atr,
        "atr": c_atr,
        "candles_below_ema20": candles_below_ema20,
        "consolidation_high": consolidation_high
    }


def fetch_order_book(symbol, current_price):
    try:
        url = f"https://data-api.binance.vision/api/v3/depth?symbol={symbol}&limit=100"
        res = HTTP.get(url, timeout=6)
        res.raise_for_status()
        raw = res.json()

        bids = [[float(p), float(q)] for p, q in raw.get("bids", [])]
        asks = [[float(p), float(q)] for p, q in raw.get("asks", [])]

        if not bids or not asks:
            return {"bid_depth_1pct": 0, "ask_depth_1pct": 0, "bid_wall_price": current_price, "ask_wall_price": current_price}

        bids_1pct_levels = [x for x in bids if x[0] >= current_price * 0.99]
        asks_1pct_levels = [x for x in asks if x[0] <= current_price * 1.01]

        bid_depth = sum(p * q for p, q in bids_1pct_levels)
        ask_depth = sum(p * q for p, q in asks_1pct_levels)

        largest_bid = max(bids_1pct_levels, key=lambda x: x[0] * x[1]) if bids_1pct_levels else [current_price, 0]
        largest_ask = max(asks_1pct_levels, key=lambda x: x[0] * x[1]) if asks_1pct_levels else [current_price, 0]

        return {
            "bid_depth_1pct": bid_depth,
            "ask_depth_1pct": ask_depth,
            "bid_wall_price": largest_bid[0],
            "ask_wall_price": largest_ask[0]
        }
    except Exception as e:
        logger.warning(f"Could not fetch order book for {symbol}: {e}")
        return {"bid_depth_1pct": 0, "ask_depth_1pct": 0, "bid_wall_price": current_price, "ask_wall_price": current_price}


def get_dynamic_movers():
    try:
        res = HTTP.get("https://data-api.binance.vision/api/v3/ticker/24hr", timeout=10)
        res.raise_for_status()
        tickers = res.json()

        l1s = sorted([t for t in tickers if (t.get("symbol") in L1_L2_UNIVERSE and t.get("symbol") not in CORE_WATCHLIST)],
                     key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)

        ais = sorted([t for t in tickers if (t.get("symbol") in AI_UNIVERSE and t.get("symbol") not in CORE_WATCHLIST)],
                     key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)

        return [t["symbol"] for t in l1s[:3]], [t["symbol"] for t in ais[:3]]
    except Exception as e:
        logger.warning(f"Could not discover dynamic movers: {e}")
        return [], []
