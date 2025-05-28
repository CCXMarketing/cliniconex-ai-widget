from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import traceback
import openai
import requests
from rapidfuzz import fuzz

with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solutions_data = json.load(f)

openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app, resources={r"/ai": {"origins": "https://cliniconex.com"}})

def find_best_match(user_input):
    best_score = 0
    best_match = None
    for row in solutions_data:
        combined_text = f"{row['issue']} {row['solution']} {row['benefits']}"
        score = fuzz.partial_ratio(user_input.lower(), combined_text.lower())
        if score > best_score:
            best_score = score
            best_match = row
    return best_match

@app.route("/ai", methods=["POST"])
def ai_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"type": "unclear", "message": "Please provide a message."}), 400

        match = find_best_match(message)

        if not match:
            return jsonify({"type": "unclear", "message": "Sorry, I couldn't find a solution that matches. Could you rephrase your issue?"})

        response = {
            "type": "solution",
            "module": match["product"],
            "feature": match["features"][0] if match["features"] else "N/A",
            "solution": match["solution"],
            "benefits": match["benefits"]
        }

        # ✅ Log to Google Sheets
        try:
            requests.post(
                "https://script.google.com/macros/s/AKfycbxTHQGjxjxLy9LI263ba6SGaheJOTNv8GyeRrhVFZxrsCS-YfBwCSu-HuMc5ceYqPpq/exec",
                json={
                    "input": message,
                    "module": response["module"],
                    "feature": response["feature"],
                    "type": response["type"],
                    "status": "success",
                    "issue": match["issue"],
                    "solution": match["solution"],
                    "benefits": match["benefits"]
                }
            )
        except Exception as log_err:
            print("⚠️ Logging failed:", log_err)

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "error": "Could not complete request",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Cliniconex AI Solution Advisor is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
