from flask import Flask, request, jsonify
import requests, datetime, json, os

app = Flask(__name__)

# Your webhooks
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1440802864174862531/SixFxy-C9fNq9suB81XpE6ontKSk3YGOmoT-lkn7uQlIt0KBjyhgbH11iSe4OzqkLO-2"
LOW_VALUE_WEBHOOK = "https://discord.com/api/webhooks/1440813903012434112/FRg-sEsrxysrBn3wU_i90NEAXrxanzpIyuD7Qy6BgSu4hP32oOmXh2EoyxnYOTdydm2E"

HIGHLIGHT_MIN = 11_000_000
LOW_VALUE_MAX = 10_999_999

# Fly.io mounts persistent volume at /data
STORAGE_DIR = "/data"
JSON_FILE = os.path.join(STORAGE_DIR, "lo.json")

os.makedirs(STORAGE_DIR, exist_ok=True)
if not os.path.exists(JSON_FILE):
    with open(JSON_FILE, "w") as f:
        json.dump([], f)

def parse_value(t):
    if not isinstance(t, str): return 0
    t = t.replace("$","").replace("/s","").strip().upper()
    m = 1
    if "K" in t: m = 1000
    if "M" in t: m = 1000000
    if "B" in t: m = 1000000000
    t = t.replace("K","").replace("M","").replace("B","")
    try: return int(float(t)*m)
    except: return 0

def send_highlight(player, pets):
    high = [f"{p.get('display_name','Pet')} — {p.get('generation','0')}" for p in pets if parse_value(p.get("generation","0")) >= HIGHLIGHT_MIN]
    if high:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [{"title": "High Value Pet Found!", "color": 16711680, "fields": [{"name": "Player", "value": player}, {"name": "≥11M/s", "value": "\n".join(f"**{x}**" for x in high)}], "timestamp": datetime.datetime.utcnow().isoformat()}]})

def send_low(player, pets):
    low = [f"{p.get('display_name','Pet')} — {p.get('generation','0')}" for p in pets if parse_value(p.get("generation","0")) <= LOW_VALUE_MAX]
    if low:
        requests.post(LOW_VALUE_WEBHOOK, json={"embeds": [{"title": "Low Value Pets", "color": 255, "fields": [{"name": "Player", "value": player}, {"name": "≤10M/s", "value": "\n".join(low)}], "timestamp": datetime.datetime.utcnow().isoformat()}]})

@app.route("/upload/", methods=["POST"])
def upload():
    try:
        data = request.get_json(force=True)
        player = data.get("player", "Unknown")
        data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        send_highlight(player, data.get("pets", []))
        send_low(player, data.get("pets", []))

        with open(JSON_FILE, "r") as f: logs = json.load(f)
        logs.append(data)
        with open(JSON_FILE, "w") as f: json.dump(logs, f, indent=2)

        return jsonify({"status": "ok", "total": len(logs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    try: count = len(json.load(open(JSON_FILE)))
    except: count = 0
    return jsonify({"message": "Pet Logger Running on Fly.io", "logs": count, "view": "/data"})

@app.route("/data")
def view():
    try: return jsonify(json.load(open(JSON_FILE)))
    except: return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
