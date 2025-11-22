from flask import Flask, request, jsonify
import requests, datetime, json, os

app = Flask(__name__)

# ==================== CONFIG ====================
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1440802864174862531/SixFxy-C9fNq9suB81XpE6ontKSk3YGOmoT-lkn7uQlIt0KBjyhgbH11iSe4OzqkLO-2"
LOW_VALUE_WEBHOOK = "https://discord.com/api/webhooks/1440813903012434112/FRg-sEsrxysrBn3wU_i90NEAXrxanzpIyuD7Qy6BgSu4hP32oOmXh2EoyxnYOTdydm2E"

HIGHLIGHT_MIN = 11_000_000
LOW_VALUE_MAX = 10_999_999

# Railway mounts volume at /data → we use a subfolder to avoid permission issues
STORAGE_DIR = "/data/petfinder"
JSON_FILE = os.path.join(STORAGE_DIR, "lo.json")

# Create folder + empty file (safe on Railway)
os.makedirs(STORAGE_DIR, exist_ok=True)
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w") as f:
        json.dump([], f)

# ==================== PARSER & DISCORD ====================
def parse_value(t):
    if not isinstance(t, str): return 0
    t = t.replace("$","").replace("/s","").strip().upper()
    m = 1
    if "K" in t: m, t = 1000, t.replace("K","")
    if "M" in t: m, t = 1000000, t.replace("M","")
    if "B" in t: m, t = 1000000000, t.replace("B","")
    try: return int(float(t)*m)
    except: return 0

def send_highlight(player, pets):
    high = [f"{p.get('display_name','Pet')} — {p.get('generation','0')}" 
            for p in pets if parse_value(p.get("generation","0")) >= HIGHLIGHT_MIN]
    if not high: return
    embed = {"title": "High Value Pet Found!", "color": 0xFF0000,
             "fields": [{"name": "Player", "value": player},
                        {"name": "≥11M/s", "value": "\n".join(f"**{x}**" for x in high)}],
             "timestamp": datetime.datetime.utcnow().isoformat()}
    requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})

def send_low(player, pets):
    low = [f"{p.get('display_name','Pet')} — {p.get('generation','0')}" 
           for p in pets if parse_value(p.get("generation","0")) <= LOW_VALUE_MAX]
    if not low: return
    embed = {"title": "Low Value Pets", "color": 0x00AAFF,
             "fields": [{"name": "Player", "value": player},
                        {"name": "≤10M/s", "value": "\n".join(low)}],
             "timestamp": datetime.datetime.utcnow().isoformat()}
    requests.post(LOW_VALUE_WEBHOOK, json={"embeds": [embed]})

# ==================== ROUTES ====================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        data = request.get_json(force=True)
        if not data: return jsonify({"error": "No JSON"}), 400
        player = data.get("player", "Unknown")
        data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        send_highlight(player, data.get("pets", []))
        send_low(player, data.get("pets", []))

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
    try: count = len(json.load(open(JSON_FILE)))
    except: count = 0
    return jsonify({"message": "Pet Logger Running on Railway", "logs": count, "view": "/data"})

@app.route("/data")
def view():
    try:
        with open(JSON_FILE) as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
