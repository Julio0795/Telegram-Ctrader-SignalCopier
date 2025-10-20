import re
import datetime
import json
import os
from telethon import TelegramClient, events
from flask import Flask, jsonify, render_template, request
import asyncio

# --- 1. CONFIGURATION & DATA PERSISTENCE ---
API_ID = ; API_HASH = ''; DATA_FILE = "bot_data.json"

def get_default_channel_profile():
    # This function uses the global bot_data, which needs to be available
    current_balance = bot_data.get("global_settings", {}).get("account_balance", 0)
    if current_balance == 0:
        current_balance = 1000
        
    return {
        "cbot_magic_number": 0,
        "parser_regex": "",
        "channel_name": "Awaiting First Signal...",
        "starting_balance": current_balance, "is_active": True, "trading_mode": "instant", "lot_size": 0.01, 
        "instant_sl_pips": 500,
        "instant_tp_pips": 200,
        "trailing_stop_enabled": False, "trailing_pips": 200, 
        "recovery_trade_enabled": False, "recovery_pips_loss": 100, "recovery_lot_size": 0.02, 
        "recovery_sl_pips": 500,
        "recovery_tp_pips": 100,
        "max_lot_enabled": False, "max_lot_base_currency": 100, "max_lot_base_lots": 0.01, 
        "trade_history": [], "total_pips": 0.0, "total_usd": 0.0
    }

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            data.setdefault("global_settings", {})
            data.setdefault("accounts", {})
            data.setdefault("activity_log", [])
            data.setdefault("signal_feed", [])
            data.setdefault("channels", {})
            for profile in data["channels"].values():
                profile.setdefault("channel_name", "Awaiting First Signal...")
                profile.setdefault("parser_regex", "")
                profile.setdefault("cbot_magic_number", 0)
                profile.setdefault("instant_sl_pips", 500)
                profile.setdefault("instant_tp_pips", 200)
                profile.setdefault("recovery_sl_pips", 500)
                profile.setdefault("recovery_tp_pips", 100)
                if "starting_balance" not in profile or profile["starting_balance"] == 0:
                    profile["starting_balance"] = 1000 # Default if not found
            return data
    return {"channels": {}, "global_settings": {}, "accounts": {}, "activity_log": [], "signal_feed": []}

def save_data():
    with open(DATA_FILE, 'w') as f: json.dump(bot_data, f, indent=4)

bot_data = load_data()
signal_queues = {}

# --- 2. FLASK APP ---
app = Flask(__name__)

def log_message(message, level="INFO"):
    log_entry = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}"
    print(log_entry)
    bot_data["activity_log"].insert(0, {"timestamp": datetime.datetime.now().isoformat(), "level": level, "message": message})
    if len(bot_data["activity_log"]) > 200: bot_data["activity_log"].pop()
    save_data()

@app.route('/')
def dashboard(): return render_template('dashboard.html')

@app.route('/log')
def log_viewer(): return render_template('log_viewer.html')

@app.route('/get_state')
def get_state(): return jsonify(bot_data)

@app.route('/update_channel_settings', methods=['POST'])
def update_channel_settings():
    data = request.get_json()
    channel_id = str(data.get("channel_id"))
    if channel_id in bot_data["channels"]:
        profile = bot_data["channels"][channel_id]
        for key, value in data.items():
            if key in profile:
                try:
                    original_type = type(profile[key])
                    if original_type == bool: profile[key] = bool(value)
                    elif original_type == int: profile[key] = int(float(value)) # Handle float from UI
                    elif original_type == float: profile[key] = float(value)
                    else: profile[key] = value
                except (ValueError, TypeError): log_message(f"Could not convert value for {key}", "WARN")
        save_data()
        log_message(f"Updated settings for channel {channel_id}", "SUCCESS")
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Channel not found"}), 400

@app.route('/add_channel', methods=['POST'])
def add_channel():
    data = request.get_json(); channel_id = str(data.get("channel_id"))
    if channel_id and channel_id not in bot_data["channels"]:
        bot_data["channels"][channel_id] = get_default_channel_profile(); save_data(); log_message(f"Added new channel: {channel_id}", "SUCCESS"); return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/remove_channel', methods=['POST'])
def remove_channel():
    data = request.get_json()
    channel_id = str(data.get("channel_id"))
    
    if channel_id and channel_id in bot_data["channels"]:
        # 1. Get the channel info BEFORE deleting it
        channel_to_remove = bot_data["channels"][channel_id]
        channel_name = channel_to_remove.get('channel_name', channel_id)
        magic_number_to_check = str(channel_to_remove.get('cbot_magic_number', '0'))

        # 2. Delete the channel profile itself
        del bot_data["channels"][channel_id]
        log_message(f"Removed channel '{channel_name}' ({channel_id})", "SUCCESS")

        # 3. Check if any OTHER channel is still using this magic number
        is_magic_number_in_use = False
        if magic_number_to_check != '0': # No need to check for the default '0'
            for other_channel in bot_data["channels"].values():
                if str(other_channel.get('cbot_magic_number')) == magic_number_to_check:
                    is_magic_number_in_use = True
                    break # Found it, no need to keep looking

        # 4. If the magic number is no longer in use, remove its account data
        if not is_magic_number_in_use and magic_number_to_check in bot_data["accounts"]:
            del bot_data["accounts"][magic_number_to_check]
            log_message(f"Cleaned up stale account data for Magic Number #{magic_number_to_check}", "INFO")

        save_data()
        return jsonify({"status": "success"})

    log_message(f"Failed to remove non-existent channel ID: {channel_id}", "ERROR")
    return jsonify({"status": "error", "message": "Channel not found"}), 400


@app.route('/report_trade_close', methods=['POST'])
def report_trade_close():
    data = request.get_json()
    channel_id = data.get("channel_id")
    magic_number = str(data.get("magic_number", 0))
    if channel_id and str(channel_id) in bot_data["channels"]:
        profile = bot_data["channels"][str(channel_id)]
        trade_record = {"timestamp": datetime.datetime.now().isoformat(), "symbol": data.get("symbol"), "direction": data.get("direction"), "pips": data.get("pips"), "usd_profit": data.get("usd_profit"), "entry_price": data.get("entry_price"), "close_price": data.get("close_price")}
        profile["trade_history"].insert(0, trade_record)
        profile["total_pips"] = sum(t["pips"] for t in profile["trade_history"])
        profile["total_usd"] = sum(t["usd_profit"] for t in profile["trade_history"])
        
        bot_data["accounts"][magic_number] = {"balance": data.get("account_balance")}
        save_data()
        log_message(f"CLOSED TRADE REPORT [Magic #{magic_number}]: {trade_record['direction']} {trade_record['symbol']} | P/L: ${trade_record['usd_profit']:.2f}", "SUCCESS")
        return jsonify({"status": "success"})
    log_message(f"Rejected closed trade report for unknown channel ID: {channel_id}", "ERROR")
    return jsonify({"status": "error", "message": "Channel ID not found"}), 400

@app.route('/get_signal/<int:magic_number>')
def get_signal(magic_number):
    magic_key = str(magic_number)
    if magic_key in signal_queues and signal_queues[magic_key]:
        signal = signal_queues[magic_key].pop(0)
        log_message(f"Delivering signal to cBot with Magic Number {magic_key}", "SUCCESS")
        return jsonify(signal)
    return jsonify({"status": "no_new_signal"})

# --- 3. TELEGRAM & DYNAMIC PARSING LOGIC ---
initial_channel_ids = [int(cid) for cid in bot_data["channels"].keys()]
client = TelegramClient('bot_session', API_ID, API_HASH)

@client.on(events.NewMessage(chats=initial_channel_ids))
async def new_message_handler(event):
    # --- THIS IS THE CRITICAL FIX ---
    global bot_data
    bot_data = load_data()
    # --- END OF FIX ---

    channel_id=str(event.chat_id);profile=bot_data["channels"].get(channel_id)
    if not profile or not profile["is_active"]: return
    
    if profile["channel_name"] == "Awaiting First Signal...":
        try: chat_entity = await event.get_chat(); profile["channel_name"] = chat_entity.title; log_message(f"Discovered name for {channel_id}: '{profile['channel_name']}'", "SUCCESS"); save_data()
        except Exception as e: log_message(f"Could not get channel name for {channel_id}: {e}", "WARN")

    log_message(f"Message received from {profile['channel_name']}.")

    regex_rule = profile.get("parser_regex")
    if not regex_rule:
        log_message(f"No parser Regex for {profile['channel_name']}. Skipping.", "WARN")
        return

    base_signal = None
    try:
        match = re.search(regex_rule, event.raw_text, re.IGNORECASE | re.DOTALL)
        if match:
            data = match.groupdict()
            if profile['trading_mode'] == 'precise':
                base_signal = {"direction": data.get("direction","").upper(), "symbol": data.get("symbol","XAUUSD").upper().replace("/",""), "entry": float(data.get("entry",0)), "sl": float(data.get("sl",0)), "tp": float(data.get("tp",0)), "parameter_type": "price"}
                if not all([base_signal["direction"], base_signal["sl"], base_signal["tp"]]): base_signal = None
            elif profile['trading_mode'] == 'instant':
                base_signal = {
                    "direction": data.get("direction","").upper(), 
                    "symbol": data.get("symbol","XAUUSD").upper().replace("/",""), 
                    "sl": profile.get("instant_sl_pips", 500),
                    "tp": profile.get("instant_tp_pips", 200),
                    "parameter_type": "pips"
                }
                if not base_signal["direction"]: base_signal = None
    except Exception as e:
        log_message(f"Error parsing with custom Regex: {e}", "ERROR")
        base_signal = None
    
    if base_signal:
        feed_entry = { "timestamp": datetime.datetime.now().isoformat(), "channel_id": channel_id, "signal_data": base_signal }
        bot_data["signal_feed"].insert(0, feed_entry)
        if len(bot_data["signal_feed"]) > 50: bot_data["signal_feed"].pop()
        
        base_signal.update(profile); base_signal["channel_id"] = channel_id
        
        magic_number_for_channel = str(profile.get("cbot_magic_number", 0))
        if magic_number_for_channel != "0":
            if magic_number_for_channel not in signal_queues:
                signal_queues[magic_number_for_channel] = []
            signal_queues[magic_number_for_channel].append(base_signal)
            log_message(f"QUEUED SIGNAL for Magic Number {magic_number_for_channel}", "INFO")
        else:
            log_message(f"Signal from {profile['channel_name']} ignored (no Magic Number assigned).", "WARN")
    else:
        log_message(f"Message from {profile['channel_name']} did not match its Regex for '{profile['trading_mode']}' mode.", "WARN")

# --- 4. STARTUP LOGIC ---
async def start_telegram():
    if not initial_channel_ids: log_message("No channels configured.", "WARN"); return
    try: await client.start(phone=''); log_message("Telegram client connected.", "SUCCESS"); await client.run_until_disconnected()
    except Exception as e: log_message(f"FATAL ERROR: {e}", "ERROR")
async def main():
    log_message("Starting application..."); flask_task=asyncio.to_thread(app.run,host='0.0.0.0',port=5000); telegram_task=start_telegram(); await asyncio.gather(flask_task,telegram_task)
if __name__ == "__main__": asyncio.run(main())