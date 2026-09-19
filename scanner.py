import time
import requests
from config import logger, TELEGRAM_TOKEN, CHAT_ID, RUN_MODE, CORE_WATCHLIST
from http_client import HTTP
from market_data import fetch_1d_context, fetch_live_price, fetch_4h_data, fetch_order_book, get_dynamic_movers
from signals import analyze_market_direction
from setups import evaluate_market_condition
from structure import format_price

def _send_single_telegram_chunk(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    for attempt in range(1, 4):
        try:
            res = HTTP.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=12)
            if res.status_code == 429:
                time.sleep(res.json().get("parameters", {}).get("retry_after", 3))
                continue
            if res.status_code == 400 and "can't parse entities" in res.text.lower():
                HTTP.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=12)
                return
            res.raise_for_status()
            return
        except requests.RequestException:
            time.sleep(1.5 * attempt)

def send_telegram(msg):
    if not msg:
        return
    max_len = 3800
    if len(msg) <= max_len:
        _send_single_telegram_chunk(msg)
        return
    paragraphs = msg.split("\n\n")
    current_chunk = ""
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_len:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                _send_single_telegram_chunk(current_chunk.strip())
                time.sleep(1.0)
            current_chunk = para + "\n\n"
    if current_chunk.strip():
        _send_single_telegram_chunk(current_chunk.strip())

def check_4h_market():
    logger.info("Initializing 4H Tactical Scanner...")
    logger.info(f"Execution mode: {RUN_MODE}")

    top_l1, top_ai = get_dynamic_movers()
    full_watchlist = list(dict.fromkeys(CORE_WATCHLIST + top_l1 + top_ai))

    alerts_fired = 0
    manual_summary = (
        "🧭 *[MANUAL 4H MARKET DIRECTION REPORT]* 🧭\n"
        "_Where prices are likely heading from current levels:_\n\n"
    )

    for symbol in full_watchlist:
        coin_name = symbol.replace("USDT", "")

        try:
            c4 = fetch_4h_data(symbol)
            live_price = fetch_live_price(symbol)
            if live_price is None: live_price = c4["price"]

            ob = fetch_order_book(symbol, live_price)
            d1 = fetch_1d_context(symbol)

            p_str = format_price(live_price)
            completed_4h_str = format_price(c4["price"])
            support_str = format_price(ob["bid_wall_price"])
            resist_str = format_price(ob["ask_wall_price"])

            if RUN_MODE != "schedule":
                verdict, action_note = analyze_market_direction(c4, ob, d1, live_price=live_price)
                manual_summary += f"• *{coin_name}* (${p_str}) : *{verdict}*\n  ↳ {action_note}\n\n"

            setups = evaluate_market_condition(c4, ob, d1, target_price_reference=live_price)

            for setup in setups:
                stype = setup["type"]
                alerts_fired += 1

                if stype == "RELIEF_SCALP":
                    msg = (
                        f"⚡ *SHORT-TERM BOUNCE ALERT* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🛡️ *Strongest Visible Buy Support:* ${support_str}\n"
                        f"• 📉 *Price is:* {abs(setup['ema_stretch']):.1f}% below the 4H 20-EMA\n"
                        f"• 📏 *EMA20 Distance:* {setup['ema_stretch_atr']:.1f} ATR\n"
                        f"• ⚡ *RSI:* {c4['rsi']:.1f}\n"
                        f"• 📊 *Trading Activity:* {c4['vol_ratio']:.1f}x normal\n\n"
                        "*Why the bot flagged this:*\n"
                        "• Price has fallen unusually far relative to this coin's normal 4H movement.\n"
                        "• Sellers may be exhausted.\n"
                        "• Trading activity has become unusually strong.\n"
                        "• The daily trend is still weak, so this is a bounce setup rather than a confirmed long-term reversal.\n\n"
                        f"• 🎯 *Target 1:* ${format_price(setup['tp1'])} (short-term trend)\n"
                        f"• 🎯 *Target 2:* ${format_price(setup['tp2'])}\n"
                        f"• 🛑 *Invalidation:* 4H close below ${format_price(setup['stop'])}\n\n"
                        "📍 *What to do:* This is a short-term bounce warning. Open the chart and check whether buyers are actually holding support."
                    )
                elif stype == "ACCUMULATION_IGNITION":
                    msg = (
                        f"🚀 *BUYING MOMENTUM BUILDING* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 📈 *Trading Activity:* {c4['vol_ratio']:.1f}x normal\n"
                        f"• ⏳ *Time Spent Below Short-Term Trend:* {c4['candles_below_ema20']} candles ({c4['candles_below_ema20'] * 4}h)\n"
                        f"• 🛡️ *Visible Buy Support:* ${support_str}\n\n"
                        "*Why the bot flagged this:*\n"
                        "• Price spent a long time weak before moving upward.\n"
                        "• Trading activity suddenly increased.\n"
                        "• Buyers pushed price back above the recent range.\n"
                        "• Momentum has turned upward.\n\n"
                        f"• 🎯 *Target 1:* ${format_price(setup['tp1'])} ({setup['tp1_type']} | +{setup['tp1_pct']:.1f}%)\n"
                        f"• 🎯 *Target 2:* ${format_price(setup['tp2'])} ({setup['tp2_type']} | +{setup['tp2_pct']:.1f}%)\n"
                        f"• 🛑 *Invalidation:* 4H close below ${format_price(setup['stop'])}\n\n"
                        "📍 *What to do:* Open the chart and check whether the breakout is holding. This is a spot-buying setup, not a guarantee of continuation."
                    )
                elif stype in ["BUY_CONFIRMED", "BUY_EARLY"]:
                    header = "🟢 *STRONG BUYING SIGNAL*" if stype == "BUY_CONFIRMED" else "🟡 *EARLY BUYING WARNING*"
                    intro = "Several signs are lining up that buyers may be taking control." if stype == "BUY_CONFIRMED" else "Some signs suggest that buyers may be starting to take control."
                    msg = (
                        f"{header} : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🛡️ *Visible Buy Support:* ${support_str}\n"
                        f"• 💧 *Visible Sell Orders Within 1%:* ${ob['ask_depth_1pct']:,.0f}\n"
                        f"• 🌍 *Daily RSI:* {d1['rsi']:.1f}\n\n"
                        f"*What this means:*\n• {intro}\n\n"
                        "*Why the bot flagged this:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "📍 *What to do:* Open the chart and check support, candle structure and whether buyers are actually following through."
                    )
                elif stype == "RALLY_OVERHEATING":
                    msg = (
                        f"🟠 *RALLY RUNNING HOT* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🎯 *Visible Sell Area:* ${resist_str}\n"
                        f"• 💧 *Visible Buy Orders Within 1%:* ${ob['bid_depth_1pct']:,.0f}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f}\n\n"
                        "*What this means:*\n"
                        "• Price has moved up very strongly.\n"
                        "• The move is becoming stretched.\n"
                        "• Visible order-book liquidity is shown only as context and is not used to create the alert.\n"
                        "• This does NOT mean the rally is over.\n\n"
                        "*Why the bot flagged this:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "⚠️ *Important:* This is a WARNING, not a sell signal and not a confirmed top.\n\n"
                        "📍 *What to do:* Open the chart and watch for an actual loss of momentum or a reversal before making a decision."
                    )
                elif stype == "TOP_EXHAUSTION_DEVELOPING":
                    msg = (
                        f"🟡 *TOP EXHAUSTION DEVELOPING* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🎯 *Visible Sell Area:* ${resist_str}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f} (previously {c4['prev_rsi']:.1f})\n\n"
                        "*What this means:*\n"
                        "• The rally is still alive, but buyers are starting to lose strength.\n"
                        "• Momentum has begun weakening.\n"
                        "• The latest price action is showing some selling/rejection.\n"
                        "• This is more serious than simply having an overextended price.\n\n"
                        "*What the bot sees:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "⚠️ *Important:* This is still NOT a confirmed reversal.\n\n"
                        "📍 *What to do:* Open the chart and watch whether price actually breaks back below its short-term trend."
                    )
                elif stype == "TOP_REVERSAL_CONFIRMED":
                    msg = (
                        f"🔴 *TOP REVERSAL CONFIRMED* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 📉 *4H 20-EMA:* ${format_price(c4['ema20'])}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f}\n"
                        f"• 🎯 *Visible Sell Area:* ${resist_str}\n\n"
                        "*What this means:*\n"
                        "• The price has now fallen back below its short-term trend.\n"
                        "• Momentum is weakening.\n"
                        "• RSI is turning downward.\n"
                        "• The latest 4H candle shows sellers gaining control.\n\n"
                        "*Why the bot flagged this:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "🔴 *This is different from the earlier warning:* the bot is no longer saying only that the rally is stretched. It is now seeing actual reversal evidence.\n\n"
                        "📍 *What to do:* This is the alert to open the chart and review profit-taking or risk management for existing spot holdings."
                    )
                elif stype == "SELLING_PRESSURE_EASING":
                    msg = (
                        f"🔵 *SELLING PRESSURE EASING* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🛡️ *Visible Buy Support:* ${support_str}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f}\n"
                        f"• 📊 *Volume:* {c4['vol_ratio']:.1f}x normal\n\n"
                        "*What this means:*\n"
                        "• The decline is showing its first signs of losing pressure.\n"
                        "• Buyers are beginning to respond at lower prices.\n"
                        "• This is an early observation, not a confirmed bottom.\n\n"
                        "*What the bot sees:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "⚠️ *Important:* Price can continue falling even after this warning.\n\n"
                        "📍 *What to do:* Watch whether the improvement continues on the next completed 4H candle."
                    )
                elif stype == "BOTTOM_EXHAUSTION_DEVELOPING":
                    msg = (
                        f"🟡 *BOTTOM EXHAUSTION DEVELOPING* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 🛡️ *Visible Buy Support:* ${support_str}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f} (previously {c4['prev_rsi']:.1f})\n\n"
                        "*What this means:*\n"
                        "• The decline is showing multiple signs of losing strength.\n"
                        "• Buyers are responding more strongly than before.\n"
                        "• Momentum is beginning to improve.\n"
                        "• This is stronger evidence than a simple oversold reading.\n\n"
                        "*What the bot sees:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "⚠️ *Important:* This is NOT a confirmed reversal yet.\n\n"
                        "📍 *What to do:* Watch whether price can reclaim and hold its short-term trend."
                    )
                elif stype == "BOTTOM_REVERSAL_CONFIRMED":
                    msg = (
                        f"🟢 *BOTTOM REVERSAL CONFIRMED* : {coin_name}\n\n"
                        f"• *Current Price:* ${p_str}\n"
                        f"• *4H Candle Close:* ${completed_4h_str}\n"
                        f"• 📈 *4H 20-EMA:* ${format_price(c4['ema20'])}\n"
                        f"• ⚡ *4H RSI:* {c4['rsi']:.1f}\n"
                        f"• 🛡️ *Visible Buy Support:* ${support_str}\n\n"
                        "*What this means:*\n"
                        "• Price has reclaimed the short-term 4H trend.\n"
                        "• RSI is turning upward.\n"
                        "• Momentum is strengthening.\n"
                        "• Buyers are showing rejection of lower prices.\n\n"
                        "*Why the bot flagged this:*\n• " + "\n• ".join(setup["reasons"]) + "\n\n"
                        "⚠️ *Important:* This confirms reversal evidence, not a guaranteed continuation.\n\n"
                        "📍 *What to do:* Open the chart and check whether price can hold above the 4H 20-EMA and continue making higher lows."
                    )
                else:
                    continue

                send_telegram(msg)
                time.sleep(1.0)

        except Exception as e:
            logger.error(f"Failed 4H analysis for {symbol}: {e}")
            continue

    if RUN_MODE != "schedule":
        manual_summary += (
            "──────────────\n"
            f"✅ *Scan Complete.* {len(full_watchlist)} coins checked. "
            f"{alerts_fired} active alert(s) sent."
        )
        send_telegram(manual_summary)
