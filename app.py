from flask import Flask, request, jsonify
import requests
import datetime
import json
import os

app = Flask(__name__)

# ==================== CONFIG ====================
# Discord Webhooks
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1440802864174862531/SixFxy-C9fNq9suB81XpE6ontKSk3YGOmoT-lkn7uQlIt0KBjyhgbH11iSe4OzqkLO-2"
LOW_VALUE_WEBHOOK = "https://discord.com/api/webhooks/1440813903012434112/FRg-sEsrxysrBn3wU_i90NEAXrxanzpIyuD7Qy6BgSu4hP32oOmXh2EoyxnYOTdydm2E"

# Value thresholds
HIGHLIGHT_MIN = 11_000_000   # Actually used as ≥11M now (you had comment ≥30M, but code says 11M)
LOW_VALUE_MAX = 10_999_999

# Path to persistent storage (Railway mounts volume here)
STORAGE_DIR = "/data"
JSON_FILE_PATH = os.path.join(STORAGE_DIR, "lo.json")

# Ensure directory and file exist
os.makedirs(STORAGE_DIR, exist_ok=True)
if not os.path.exists(JSON_FILE_PATH):
    with open(JSON_FILE_PATH, "w") as f:
        json.dump([], f)  # Start with empty list

# ===============================================
# VALUE PARSER ($2.5M/s → 2500000)
# ===============================================
def parse_value(text):
    if not isinstance(text, str):
        return int(text)
    text = text.replace("$", "").replace("/s", "").strip().upper()
    multiplier = 1
    if "K" in text:
        multiplier = 1_000
        text = text.replace("K", "")
    elif "M" in text:
        multiplier = 1_000_000
        text = text.replace("M", "")
    elif "B" in text:
        multiplier = 1_000_000_000
        text = text.replace("B", "")
    try:
        return int(float(text) * multiplier)
    except:
        return 0

# ===============================================
# HIGH VALUE WEBHOOK (≥ 11M/s)
# ===============================================
def send_discord_highlight(player, pets):
    high_value_items = []
    all_pet_names = []
    for pet in pets:
        name = pet.get("display_name", "Unknown Pet")
        value_raw = pet.get("generation", "0")
        all_pet_names.append(name)
        value = parse_value(value_raw)
        if value >= HIGHLIGHT_MIN:
            high_value_items.append(f"{name} — {value_raw}")

    if not high_value_items:
        return

    embed = {
        "title": "🚨 High Value Pet Found!",
        "color": 0xFF0000,
        "fields": [
            {"name": "Player", "value": player, "inline": False},
            {
                "name": "High Value Pets (≥ 11M/s)",
                "value": "\n".join(f"**{item}**" for item in high_value_items),
                "inline": False
            },
            {"name": "All Pets", "value": "```\n" + "\n".join(all_pet_names) + "\n```", "inline": False}
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    try:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
    except Exception as e:
        print("❌ Discord highlight failed:", e)

# ===============================================
# LOW VALUE WEBHOOK (≤ 10M/s)
# ===============================================
def send_low_value(player, pets):
    low_items = []
    for pet in pets:
        name = pet.get("display_name", "Unknown Pet")
        value_raw = pet.get("generation", "0")
        value = parse_value(value_raw)
        if value <= LOW_VALUE_MAX:
            low_items.append(f"{name} — {value_raw}")

    if not low_items:
        return

    embed = {
        "title": "🐾 Low Value Pets Logged",
        "color": 0x00AAFF,
        "fields": [
            {"name": "Player", "value": player, "inline": False},
            {"name": "Pets ≤ 10M/s", "value": "\n".join(low_items), "inline": False}
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    try:
        requests.post(LOW_VALUE_WEBHOOK, json={"embeds": [embed]})
    except Exception as e:
        print("❌ Low value webhook failed:", e)

# ===============================================
# MAIN UPLOAD ROUTE
# ===============================================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        player = data.get("player", "Unknown")
        pets = data.get("pets", [])
        data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Send Discord notifications
        send_discord_highlight(player, pets)
        send_low_value(player, pets)

        print(f"📦 Received data from {player} - {len(pets)} pets")

        # === Read current logs ===
        try:
            with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
                current_content = json.load(f)
            if not isinstance(current_content, list):
                current_content = []
        except:
            current_content = []

        # === Append new data ===
        current_content.append(data)

        # === Write back to volume ===
        with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(current_content, f, indent=2)

        print(f"✅ Log saved - Total entries: {len(current_content)}")
        return jsonify({"status": "ok", "total_logs": len(current_content)}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ===============================================
# STATUS PAGE
# ===============================================
@app.route("/", methods=["GET"])
def home():
    try:
        with open(JSON_FILE_PATH, "r") as f:
            logs = json.load(f)
        count = len(logs)
    except:
        count = 0
    return jsonify({
        "status": "Pet Finder Logger is running!",
        "storage": "Railway Volume (/data)",
        "total_logs": count,
        "uptime": datetime.datetime.utcnow().isoformat()
    }), 200

# ===============================================
# START SERVER
# ===============================================
if __name__ == "__main__":
    print("🚀 Starting Pet Finder Logger on Railway with Volume Storage")
    print(f"Data will be saved to: {JSON_FILE_PATH}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
