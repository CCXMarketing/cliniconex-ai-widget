# Refactored Cliniconex AI Solution Advisor Backend
import os
import json
import re
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ✅ Flask setup
app = Flask(__name__)
CORS(app)

# ✅ Environment and API setup
openai.api_key = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

# ✅ Load solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# ✅ Google Sheets setup
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
sheet = build("sheets", "v4", credentials=credentials).spreadsheets()

# ✅ Utility Functions
def normalize(text):
    return text.lower().strip()

def score_keywords(message, item):
    return sum(1 for k in item.get("keywords", []) if k.lower() in message)

def get_best_matrix_match(message):
    best_score, best_item, best_keyword = 0, None, None
    for item in solution_matrix:
        score = score_keywords(message, item)
        if score > best_score:
            best_score = score
            best_item = item
            best_keyword = next((k for k in item.get("keywords", []) if k.lower() in message), None)
    return best_score, best_item, best_keyword

def validate_gpt_response(parsed):
    required_keys = {"product", "feature", "how_it_works", "benefits"}
    return all(k in parsed and parsed[k] for k in required_keys)

def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'{.*}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else None

def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        values = [[timestamp, prompt, product, feature, status, matched_issue, matched_solution, page_url, keyword]]
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Advisor Logs!A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
    except Exception as e:
        print("❌ Error logging to Google Sheets:", str(e))
        traceback.print_exc()

def generate_gpt_solution(message):
    gpt_prompt = f"""
You are a Cliniconex solutions expert...
"""  # Full prompt elided here for brevity (same as original)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": gpt_prompt}],
            temperature=0.7
        )
        raw_output = response['choices'][0]['message']['content']
        print("🧠 GPT raw output:\n", raw_output)
        parsed = extract_json(raw_output)
        return parsed if validate_gpt_response(parsed) else None
    except Exception as e:
        print("❌ GPT fallback error:", str(e))
        traceback.print_exc()
        return None

# ✅ Main AI Route
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        print("📩 /ai endpoint hit")
        print("🔍 Message received:", message)

        matrix_score, matrix_item, keyword = get_best_matrix_match(message)
        gpt_response = generate_gpt_solution(message)

        use_matrix = (
            matrix_score >= 2 and matrix_item and gpt_response and
            gpt_response.get("product", "").lower() in matrix_item.get("product", "").lower()
        )

        if use_matrix:
            response = {
                "type": "solution",
                "module": matrix_item.get("product", "N/A"),
                "feature": ", ".join(matrix_item.get("features", [])) or "N/A",
                "solution": matrix_item.get("solution", "N/A"),
                "benefits": matrix_item.get("benefits", "N/A"),
                "keyword": keyword or "N/A"
            }
            log_to_google_sheets(message, page_url, response["module"], response["feature"], "matrix", matrix_item.get("issue", "N/A"), response["solution"], keyword)
            return jsonify(response)

        elif gpt_response:
            benefits = gpt_response.get("benefits", [])
            benefits_str = "\n".join(f"- {b}" for b in benefits) if isinstance(benefits, list) else str(benefits)
            response = {
                "type": "solution",
                "module": gpt_response.get("product", "N/A"),
                "feature": gpt_response.get("feature", "N/A"),
                "solution": gpt_response.get("how_it_works", "No solution provided"),
                "benefits": benefits_str,
                "keyword": message
            }
            log_to_google_sheets(message, page_url, response["module"], response["feature"], "gpt-fallback", "GPT generated", response["solution"], message)
            return jsonify(response)

        return jsonify({"type": "no_match", "message": "We couldn't generate a relevant solution."})

    except Exception as e:
        print("❌ Internal Server Error:", str(e))
        traceback.print_exc()
        return jsonify({"type": "error", "message": "Internal Server Error"}), 500

# ✅ Start app for Render
if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
