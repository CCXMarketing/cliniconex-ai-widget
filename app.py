from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import traceback
import openai
import requests
from rapidfuzz import fuzz

# ✅ Load solution data
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solutions_data = json.load(f)

# ✅ OpenAI key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ✅ Flask setup
app = Flask(__name__)
CORS(app, resources={r"/ai": {"origins": "https://cliniconex.com"}})

# 🔍 Fuzzy match
def find_best_solution(user_input):
    best_match = None
    best_score = 0
    for item in solutions_data:
        for kw in item.get("keywords", []):
            score = fuzz.partial_ratio(user_input.lower(), kw.lower())
            if score > best_score:
                best_score = score
                best_match = item
    return best_match if best_score >= 60 else None

# 🔁 Main endpoint
@app.route("/ai", methods=["POST"])
def ai_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        email = data.get("email", "").strip()

        if not message:
            return jsonify({"type": "unclear", "message": "Please provide a message."}), 400

        match = find_best_solution(message)

        if match:
            response = {
                "type": "solution",
                "module": match["product"],
                "feature": match["features"][0] if match.get("features") else "N/A",
                "solution": match["solution"]
            }

            # ✅ Log to Google Sheets
            try:
                requests.post(
                    "https://script.google.com/macros/s/AKfycby5ukM-KojTCFLeEo1gXzrNE2gBc9wxBdeXvcKdQayU9WXOn7EWVV-x5JeySKydd8CM/exec",  # replace with your actual ID
                    json={
                        "input": message,
                        "email": email or "Not provided",
                        "module": response["module"],
                        "feature": response["feature"],
                        "type": response["type"],
                        "status": "success"
                    }
                )
            except Exception as log_err:
                print("⚠️ Logging failed:", log_err)

            return jsonify(response)

        else:
            return jsonify({
                "type": "unclear",
                "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
            })

    except Exception as e:
        return jsonify({
            "error": "Could not complete request",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Cliniconex AI Solution Advisor is running!", 200

# 🟢 Run server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
