import json
import os
import time
from datetime import datetime
from market_service import get_market_data

PORTFOLIO_FILE = 'portfolio.json'

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {"alerts": [], "balances": {}, "history": [], "snapshots": [], "newsletter_subs": []}
    with open(PORTFOLIO_FILE, 'r') as f:
        try:
            data = json.load(f)
            if "balances" not in data:
                data["balances"] = {}
            if "history" not in data:
                data["history"] = []
            if "snapshots" not in data:
                data["snapshots"] = []
            if "newsletter_subs" not in data:
                # Default to subscribing all users who have alerts/balances, or empty
                # Let's keep it empty and opt-in or auto-opt-in logic elsewhere
                data["newsletter_subs"] = [] 
            return data
        except json.JSONDecodeError:
            return {"alerts": [], "balances": {}, "history": [], "snapshots": [], "newsletter_subs": []}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_alert(symbol, target_price, condition, user_id):
    """
    Adds a new alert.
    condition: 'above' or 'below'
    """
    data = load_portfolio()
    
    # Normalize symbol simply (can rely on market_service logic later or verify now)
    # Ideally should verify symbol validity first
    
    
    alert = {
        "type": "price",
        "symbol": symbol,
        "target_price": float(target_price),
        "condition": condition,
        "user_id": user_id,
        "created_at": time.time(), # Timestamp for creation time
        "start_price": get_price_now(symbol), # Optional: Store starting price for comparison
        "current_level": -1 # Level of alert: -1=New, 0=Target Met, 1=5% Met, 2=10% Met
    }
    data["alerts"].append(alert)
    save_portfolio(data)
    return "Fiyat alarmı başarıyla eklendi."

def get_price_now(symbol):
    data = get_market_data(symbol)
    if data:
        return data['price']
    return 0.0

def add_time_alert(seconds, user_id, note=""):
    """
    Adds a time-based alert.
    """
    data = load_portfolio()
    now = time.time()
    trigger_timestamp = now + float(seconds)
    
    alert = {
        "type": "time",
        "trigger_timestamp": trigger_timestamp,
        "note": note,
        "user_id": user_id,
        "created_at": now,
        "duration_seconds": float(seconds)
    }
    data["alerts"].append(alert)
    save_portfolio(data)
    return f"Zamanlayıcı kuruldu. {seconds} saniye sonra hatırlatılacak."

def update_balance(user_id, symbol, amount, unit):
    """
    Updates user balance for a symbol.
    """
    data = load_portfolio()
    user_str = str(user_id)
    
    if user_str not in data["balances"]:
        data["balances"][user_str] = {}
        
    data["balances"][user_str][symbol] = {
        "amount": float(amount),
        "unit": unit
    }
    save_portfolio(data)
    return f"Bakiye güncellendi: {amount} {unit} {symbol}"

def get_portfolio_status(user_id):
    """
    Calculates total portfolio value in USD and TRY.
    """
    data = load_portfolio()
    user_str = str(user_id)
    balances = data.get("balances", {}).get(user_str, {})
    
    if not balances:
        return "Henüz kayıtlı bir bakiyeniz bulunmuyor."
        
    report = "📊 **Portföy Durumu**\n\n"
    total_usd = 0.0
    total_try = 0.0
    
    # Get USD/TRY rate
    usd_try_rate = 1.0
    try:
        usd_data = get_market_data("TRY=X")
        if usd_data:
            usd_try_rate = usd_data['price']
    except:
        pass # Default 1.0 if fails, though unlikely to be useful if valid
        
    for symbol, details in balances.items():
        amount = details['amount']
        unit = details['unit']
        
        # Determine query symbol and multiplier for price
        query_symbol = symbol
        multiplier = 1.0 # Multiplier to adjust price to match user's unit
        
        # Gold Logic
        if "ALTIN" in symbol.upper() or "GOLD" in symbol.upper() or symbol.upper() == "GC=F":
            query_symbol = "GC=F" # Yahoo Finance Gold Futures (oz)
            if unit.lower() in ["gr", "gram", "g"]:
                # User has Gram, Market is Oz.
                # 1 Oz = 31.1035 Gram
                # So user's amount in Oz = amount / 31.1035
                # Value = (amount / 31.1035) * price_per_oz
                multiplier = 1.0 / 31.1035
                
        market_data = get_market_data(query_symbol)
        if not market_data:
            report += f"- {symbol}: Fiyat alınamadı.\n"
            continue
            
        price = market_data['price']
        currency = market_data.get('currency', 'USD')
        
        # Calculate Value in asset's currency
        # If user has 540 Grams, and we use multiplier for Oz price:
        # Value = 540 * (1/31..) * Price(Oz)
        val_in_asset_curr = amount * multiplier * price
        
        val_usd = 0.0
        val_try = 0.0
        
        if currency == 'USD':
            val_usd = val_in_asset_curr
            val_try = val_usd * usd_try_rate
        elif currency == 'TRY':
            val_try = val_in_asset_curr
            val_usd = val_try / usd_try_rate if usd_try_rate > 0 else 0
        else:
             # Fallback or Todo: Cross rates
             val_usd = val_in_asset_curr # Assume USD for unknown
             val_try = val_usd * usd_try_rate
             
        total_usd += val_usd
        total_try += val_try
        
        if "ALTIN" in symbol.upper() and multiplier != 1.0:
             # Add specific info about conversion
             ons_amount = amount / 31.1035
             report += f"- {amount} {unit} {symbol} (~{ons_amount:.2f} Ons)\n"
             report += f"  Değer: {val_usd:.2f} $ / {val_try:.2f} ₺\n"
        else:
             report += f"- {amount} {unit} {symbol}\n"
             report += f"  Değer: {val_usd:.2f} $ / {val_try:.2f} ₺\n"
             
    report += "\n"
    report += f"💰 **Toplam Tahmini Değer:**\n"
    report += f"{total_usd:.2f} $\n"
    report += f"{total_try:.2f} ₺"
    
    return report

    return report

    return report

def subscribe_newsletter(user_id):
    data = load_portfolio()
    subs = data.get("newsletter_subs", [])
    if user_id not in subs:
        subs.append(user_id)
        data["newsletter_subs"] = subs
        save_portfolio(data)
    return "Günlük bülten aboneliğiniz başlatıldı. (Her gün 08:00 ve 18:00)"

def unsubscribe_newsletter(user_id):
    data = load_portfolio()
    subs = data.get("newsletter_subs", [])
    if user_id in subs:
        subs.remove(user_id)
        data["newsletter_subs"] = subs
        save_portfolio(data)
        return "Günlük bülten iptal edildi."
    return "Zaten abone değilsiniz."

def get_newsletter_subscribers():
    data = load_portfolio()
    return data.get("newsletter_subs", [])

def save_snapshot(label):
    """
    Saves a snapshot of current prices for all user-relevant symbols.
    label: 'morning' or 'evening'
    """
    data = load_portfolio()
    
    # Collect all relevant symbols from alerts and balances
    symbols = set()
    for alert in data.get("alerts", []):
        if alert.get("type", "price") == "price":
            symbols.add(alert['symbol'])
    
    for user_bals in data.get("balances", {}).values():
        for sym in user_bals.keys():
            symbols.add(sym)
            
    # Also add watchlist for market summary
    watchlist = ["THYAO.IS", "GARAN.IS", "BIST100", "USDTRY=X", "GC=F", "BTC-USD", "ETH-USD", "AAPL", "TSLA"]
    for w in watchlist:
        symbols.add(w)
        
    prices = {}
    for sym in symbols:
        # Special case for some symbols normalization handled in get_market_data or here
        # Assuming get_market_data handles it or returns None
        mdata = get_market_data(sym)
        if mdata:
            prices[sym] = mdata['price']
            
    snapshot = {
        "timestamp": time.time(),
        "label": label,
        "prices": prices
    }
    
    # Keep only last few snapshots to save space? Or needed history?
    # For comparison we usually need just the last one of opposite type or immediate previous.
    if "snapshots" not in data:
        data["snapshots"] = []
    
    # Append
    data["snapshots"].append(snapshot)
    
    # Trim to last 10 to keep file size small
    if len(data["snapshots"]) > 10:
        data["snapshots"] = data["snapshots"][-10:]
        
    save_portfolio(data)
    return snapshot

def get_last_snapshot(current_label):
    """
    Returns the most relevant previous snapshot for comparison.
    If current is 'morning' (08:00) -> compare with yesterday 'evening' or 'morning'? 
    User said: "sabah 8 deki piyasa fiyatlarına göre karşılaştırması" (vs yesterday evening)
    If current is 'morning', looks for last 'evening'. 
    If current is 'evening', looks for today 'morning'.
    """
    data = load_portfolio()
    snaps = data.get("snapshots", [])
    if not snaps:
        return None
        
    target_label = 'evening' if current_label == 'morning' else 'morning'
    
    # Reverse search
    for snap in reversed(snaps):
        # Allow comparing to same label if opposite missing? 
        # Ideally find last opposite.
        if snap['label'] == target_label:
            return snap
            
    # Fallback to just the very last one
    return snaps[-1] if snaps else None

def generate_newsletter(user_id, label):
    """
    Generates the newsletter text for a user.
    """
    data = load_portfolio()
    
    # 1. Get Comparisons
    # First ensure we have a fresh snapshot for NOW (or created just before calling this)
    # Actually, we should call save_snapshot ONCE globally before generating for users, 
    # but here we might just use live values vs Last Snapshot.
    # Let's assume save_snapshot was called by the job handler right before this loop.
    # So we get the very last snapshot as "Current" and the one before that as "Previous".
    
    snaps = data.get("snapshots", [])
    if not snaps:
        return None # Should not happen if saved before
        
    current_snap = snaps[-1] # This morning/evening
    prev_snap = get_last_snapshot(label)
    
    if not prev_snap:
         # No previous data to compare
         prev_snap = current_snap # Diff will be 0
         
    curr_prices = current_snap.get('prices', {})
    prev_prices = prev_snap.get('prices', {})
    
    # Get USD Rate for Balances
    usd_try = curr_prices.get("TRY=X", 1.0)
    if not usd_try: 
        m = get_market_data("TRY=X")
        usd_try = m['price'] if m else 1.0

    report = f"📰 **Piyasa Bülteni ({label.capitalize()})**\n_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
    
    # A) Alarmı olan hisseler
    user_str = str(user_id)
    user_alerts = [a for a in data.get("alerts", []) if str(a.get('user_id')) == user_str and a.get('type')=='price']
    
    relevant_symbols = set([a['symbol'] for a in user_alerts])
    # Add balance symbols
    user_balances = data.get("balances", {}).get(user_str, {})
    for s in user_balances.keys():
        relevant_symbols.add(s)
        
    if relevant_symbols:
        report += "📉 **Takip Listeniz:**\n"
        for sym in relevant_symbols:
            cp = curr_prices.get(sym)
            pp = prev_prices.get(sym)
            
            if cp and pp:
                diff = cp - pp
                pct = ((cp - pp) / pp) * 100
                icon = "🟢" if diff >= 0 else "🔴"
                # Try handling None carefully
                report += f"{icon} {sym}: {pp:.2f} -> {cp:.2f} (%{pct:+.2f})\n"
            else:
                report += f"⚪ {sym}: Veri yok/yetersiz.\n"
        report += "\n"

    # B) Bakiye
    if user_balances:
        total_usd_cur = 0.0
        total_usd_prev = 0.0
        
        for sym, det in user_balances.items():
            amt = det['amount']
            unit = det['unit']
            
            # Gold multiplier logic duplicate (should refactor but keep simple here)
            mult = 1.0
            query_sym = sym
            if "ALTIN" in sym.upper() or "GOLD" in sym.upper() or sym.upper() == "GC=F":
                query_sym = "GC=F"
                if unit.lower() in ["gr", "gram", "g"]:
                    mult = 1.0 / 31.1035
            
            curr_p = curr_prices.get(query_sym, 0)
            prev_p = prev_prices.get(query_sym, 0) # Use 0 if missing
            
            if prev_p == 0: prev_p = curr_p # Avoid div/0 or huge logic jumps
            
            # Val calc (simplified, assume USD based assets mainly or handle convert)
            # Assuming market_service returns USD for most, TRY for stocks maybe?
            # We need Currency info which is not in simple prices dict map.
            # Only storing prices is a limitation of simple snapshot. 
            # We will approximate: If symbol ends with .IS -> TRY. Else USD.
            
            is_try = sym.endswith(".IS") or sym == "TRY=X"
            
            # Current Val
            val_c = amt * mult * curr_p
            if is_try: val_c = val_c / usd_try if usd_try > 0 else 0
            total_usd_cur += val_c
            
            # Prev Val
            val_p = amt * mult * prev_p
            if is_try: val_p = val_p / usd_try if usd_try > 0 else 0 # alert: using current USD rate for prev value? 
            # Ideally use prev USD rate.
            prev_usd_rate = prev_prices.get("TRY=X", 1.0)
            if is_try: val_p = val_p / prev_usd_rate if prev_usd_rate > 0 else 0
            
            total_usd_prev += val_p
            
        diff_bal = total_usd_cur - total_usd_prev
        pct_bal = 0.0
        if total_usd_prev > 0:
            pct_bal = (diff_bal / total_usd_prev) * 100
            
        total_try_cur = total_usd_cur * usd_try
        
        report += "💰 **Varlık Durumu:**\n"
        report += f"💵 Toplam: {total_usd_cur:.2f} $ (~{total_try_cur:.2f} ₺)\n"
        report += f"📊 Değişim: {diff_bal:+.2f} $ (%{pct_bal:+.2f})\n\n"

    # C) Top Movers (Global/BIST List)
    # We scan our pre-defined 'watchlist' from save_snapshot
    report += "🌍 **Piyasa Özeti (Günlük):**\n"
    watchlist = ["BIST100", "THYAO.IS", "GARAN.IS", "BTC-USD", "ETH-USD", "AAPL", "GC=F"]
    
    movers = []
    for w in watchlist:
        cp = curr_prices.get(w)
        pp = prev_prices.get(w)
        if cp and pp:
            pct = ((cp - pp) / pp) * 100
            movers.append((w, pct, cp))
    
    # Sort by abs change pct (Volatility) or just Gainers? "En çok değer kazanan ve kaybeden"
    # Let's sort by pct desc
    movers.sort(key=lambda x: x[1], reverse=True)
    
    # Take top 2 and bottom 2
    if len(movers) > 4:
        top = movers[:2]
        bottom = movers[-2:]
        display_list = top + bottom
        # Remove duplicates if any overlap
        display_list = list(dict.fromkeys(display_list)) 
    else:
        display_list = movers
        
    for item in display_list:
        sym, pct, cp = item
        icon = "🟢" if pct >= 0 else "🔴"
        report += f"{icon} {sym}: {cp:.2f} (%{pct:+.2f})\n"
        
    report += "\n⚠️ _Bülteni iptal etmek için: /iptal_bulten_"
    return report

def delete_alert(user_id, alert_index):
    """
    Deletes an alert based on its 1-based index in the user's list.
    """
    print(f"DEBUG: delete_alert called for user {user_id}, index {alert_index}")
    data = load_portfolio()
    alerts = data.get("alerts", [])
    user_str = str(user_id)
    
    # 1. Find user's alerts to map index
    user_indices = [] # Stores actual indices in the main 'alerts' list
    for i, a in enumerate(alerts):
        if str(a.get('user_id')) == user_str:
            user_indices.append(i)
            
    print(f"DEBUG: Found {len(user_indices)} alerts for user. Indices: {user_indices}")

    if not user_indices:
        return "Silinecek aktif alarmınız yok."
        
    if alert_index < 1 or alert_index > len(user_indices):
        return f"Geçersiz numara. 1 ile {len(user_indices)} arasında bir sayı belirtin."
        
    # 2. Identify target index in main list
    target_main_index = user_indices[alert_index - 1]
    print(f"DEBUG: Target main index to delete: {target_main_index}")
    
    # 3. Get details for confirmation message before deleting
    removed_alert = alerts[target_main_index]
    symbol = removed_alert.get('symbol', 'Zamanlayıcı')
    target = removed_alert.get('target_price', '')
    note = removed_alert.get('note', '')
    
    desc = f"{symbol} > {target}" if removed_alert.get('type') == 'price' else f"Zamanlayıcı ({note})"
    
    # 4. Remove
    # We remove by index. Since we loaded freshly, this is safe unless concurrency high (unlikely here)
    del alerts[target_main_index]
    
    data["alerts"] = alerts
    save_portfolio(data)
    print("DEBUG: Alert deleted and saved.")
    
    return f"✅ İptal edildi: {desc}"

def get_active_alerts(user_id):
    """
    Returns a formatted list of active alerts for the user.
    """
    data = load_portfolio()
    alerts = data.get("alerts", [])
    user_str = str(user_id)
    
    user_alerts = [a for a in alerts if str(a.get('user_id')) == user_str]
    
    if not user_alerts:
        return "📭 Henüz aktif bir alarmınız yok."
        
    report = "📋 **Aktif Alarmlarınız**:\n\n"
    
    for i, alert in enumerate(user_alerts, 1):
        alert_type = alert.get("type", "price")
        created_at = alert.get("created_at", 0)
        dt_str = datetime.fromtimestamp(created_at).strftime('%d/%m %H:%M')
        
        if alert_type == "price":
            symbol = alert['symbol']
            target = alert['target_price']
            condition = alert.get('condition', 'above')
            level = alert.get('current_level', -1)
            
            cond_sym = ">=" if condition == 'above' else "<="
            level_str = ""
            if level >= 0:
                level_str = f" | Seviye: {level} (Tamamlanan: %{level*5})"
            
            report += f"{i}. 📉 **[Fiyat]** {symbol} {cond_sym} {target}\n"
            report += f"   📅 {dt_str}{level_str}\n"
            
        elif alert_type == "time":
            trigger_time = alert['trigger_timestamp']
            remaining = trigger_time - time.time()
            note = alert.get("note", "")
            
            rem_str = "Süre doldu"
            if remaining > 0:
                mins = int(remaining / 60)
                secs = int(remaining % 60)
                rem_str = f"{mins}dk {secs}sn"
            
            report += f"{i}. ⏳ **[Zaman]** {note if note else 'Zamanlayıcı'}\n"
            report += f"   ⏱️ Kalan: {rem_str} | 📅 {dt_str}\n"
            
    return report

def check_alerts():
    """
    Checks all alerts and returns a list of notifications to send.
    Handles progressive levels (%0, %5, 10%).
    """
    data = load_portfolio()
    alerts = data.get("alerts", [])
    history = data.get("history", [])
    
    triggered_alerts = []
    remaining_alerts = []
    
    # Cache prices to avoid spamming API
    price_cache = {}
    
    # Get USD/TRY rate once for conversions
    usd_try_rate = 1.0
    try:
        usd_data = get_market_data("TRY=X")
        if usd_data:
            usd_try_rate = usd_data['price']
    except:
        pass

    for alert in alerts:
        alert_type = alert.get("type", "price")
        user_id = alert['user_id']
        created_at = alert.get("created_at", time.time())
        created_at_fmt = datetime.fromtimestamp(created_at).strftime('%d/%m/%Y %H:%M')
        
        should_remove = False # Whether to move to history
        trigger_info = None # If triggered, holds {message, repeat_count}

        if alert_type == "time":
            trigger_time = alert['trigger_timestamp']
            if time.time() >= trigger_time:
                # Time alerts are always 1-time and done
                should_remove = True
                note = alert.get("note", "")
                duration = alert.get("duration_seconds", 0)
                
                # Format duration nicely
                duration_str = f"{int(duration)} saniye"
                if duration >= 60:
                    mins = int(duration / 60)
                    duration_str = f"{mins} dakika"
                    if mins >= 60:
                        hours = int(mins / 60)
                        duration_str = f"{hours} saat"

                message = (
                    f"⏰ ZAMANLAYICI: Süre Doldu!\n\n"
                    f"📌 Detaylar:\n"
                    f"• Kurulan Süre: {duration_str}\n"
                    f"• Alarm Kurma Zamanı: {created_at_fmt}\n"
                    f"• Not: {note}"
                )
                trigger_info = {"message": message, "repeat_count": 1}
        
        elif alert_type == "price":
            symbol = alert['symbol']
            target = alert['target_price']
            condition = alert['condition']
            current_level = alert.get("current_level", -1)
            
            if symbol not in price_cache:
                market_data = get_market_data(symbol)
                price_cache[symbol] = market_data
            
            market_data = price_cache[symbol]
            current_price = market_data['price'] if market_data else None
            currency = market_data['currency'] if market_data else "USD"
            
            if current_price is None:
                remaining_alerts.append(alert)
                continue
            
            # Helper to calculate message
            def build_message(title_suffix, change_val):
                current_usd = current_price
                current_try = current_price
                if currency == "USD":
                    current_try = current_price * usd_try_rate
                elif currency == "TRY":
                    current_usd = current_price / usd_try_rate if usd_try_rate > 0 else 0
                
                # Start price based percentage
                start_price = alert.get("start_price", target)
                total_change_pct = 0.0
                if start_price > 0:
                    total_change_pct = ((current_price - start_price) / start_price) * 100

                return (
                    f"🔔 ALARM: {title_suffix}\n\n"
                    f"📌 Detaylar:\n"
                    f"• Alarm Kurma Zamanı: {created_at_fmt}\n"
                    f"• Hedeflediğiniz Değer: {target} {currency}\n"
                    f"• Şu Anki Değer: {current_usd:.2f} $ / {current_try:.2f} ₺\n"
                    f"• Başlangıca Göre Değişim: %{total_change_pct:.2f}"
                )

            # --- LEVEL LOGIC ---
            # Thresholds for 'above' condition mainly
            
            new_level = current_level
            
            # Base Condition
            base_met = False
            if condition == 'above' and current_price >= target:
                base_met = True
            elif condition == 'below' and current_price <= target:
                base_met = True
            
            if base_met:
                percent_diff = abs((current_price - target) / target) * 100
                
                # LEVEL 2: 10%
                if percent_diff >= 10:
                    if current_level < 2:
                        # Jump to level 2 - Fire 5 times
                        new_level = 2
                        should_remove = True # Done after this
                        trigger_info = {
                            "message": build_message(f"{symbol} Hedefi %10 Aşti! (KRİTİK ARTIS)", percent_diff),
                            "repeat_count": 5
                        }
                # LEVEL 1: 5%
                elif percent_diff >= 5:
                    if current_level < 1:
                        new_level = 1
                        trigger_info = {
                            "message": build_message(f"{symbol} Hedefi %5 Aşti!", percent_diff),
                            "repeat_count": 3
                        }
                # LEVEL 0: Base Target
                else:
                    if current_level < 0:
                        new_level = 0
                        trigger_info = {
                            "message": build_message(f"{symbol} Hedefi Geçti!", percent_diff),
                            "repeat_count": 1
                        }
            
            if trigger_info:
                alert["current_level"] = new_level
                
        # Handling Trigger
        if trigger_info:
            triggered_alerts.append({
                "user_id": user_id,
                "message": trigger_info["message"],
                "repeat_count": trigger_info["repeat_count"]
            })
        
        # Handling Persistence
        if should_remove:
            # Move to history
            # Add completion info
            alert["completed_at"] = time.time()
            alert["final_message"] = trigger_info["message"] if trigger_info else "Completed"
            history.append(alert)
        else:
            remaining_alerts.append(alert)
            
    # Save updates
    data["alerts"] = remaining_alerts
    data["history"] = history
    save_portfolio(data)
    
    return triggered_alerts
