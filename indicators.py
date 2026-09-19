def calculate_wilder_rsi(closes, period=14):
    n = len(closes)
    rsi = [50.0] * n
    if n < period + 1:
        return rsi

    gains = [0.0] * n
    losses = [0.0] * n

    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains[i] = diff
        else:
            losses[i] = -diff

    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rsi[period] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

    for i in range(period):
        rsi[i] = rsi[period]

    return rsi

def calculate_ema(data, period):
    n = len(data)
    if n == 0:
        return []

    ema = [data[0]] * n
    k = 2.0 / (period + 1)

    for i in range(1, n):
        ema[i] = data[i] * k + ema[i - 1] * (1.0 - k)

    return ema

def calculate_rma(data, period):
    n = len(data)
    rma = [0.0] * n
    if n < period:
        return rma

    rma[period - 1] = sum(data[:period]) / period

    for i in range(period, n):
        rma[i] = (rma[i - 1] * (period - 1) + data[i]) / period

    for i in range(period - 1):
        rma[i] = rma[period - 1]

    return rma

def calculate_atr(highs, lows, closes, period=14):
    n = len(closes)
    if n == 0:
        return []

    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]

    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )

    return calculate_rma(tr, period)

def calculate_macd(closes):
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)

    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal_line = calculate_ema(macd_line, 9)
    hist = [macd_line[i] - signal_line[i] for i in range(len(closes))]

    return macd_line, signal_line, hist
