from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openai
import os
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 🔐 Load environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🚀 Flask app
app = Flask(__name__)
CORS(app)

# 📥 Load verified solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# 📝 Google Sheets logging
def log_to_google_sheet(row_data):
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        SERVICE_ACCOUNT_FILE = 'service_account.json'
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        SPREADSHEET_ID = '1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg'
        RANGE = 'Cliniconex AI Solution Widget Logs!A1'
        result = sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body={'values': [row_data]}
        ).execute()
        return result
    except Exception as e:
        print(f"❌ Google Sheets logging failed: {e}")
        return None

# 🔍 Keyword-based matcher
def find_keyword_match(user_input):
    user_words = set(re.findall(r'\b\w+\b', user_input.lower()))
    for entry in solution_matrix:
        entry_keywords = set(kw.lower() for kw in entry.get("keywords", []))
        if user_words & entry_keywords:
            return entry
    return None

# 🤖 GPT fallback
def get_gpt_solution(user_input):
    prompt = f"""
You are a helpful assistant working for Cliniconex, a healthcare communication company.
Your task is to interpret vague or brief input from healthcare professionals and return a JSON with:
- type: "solution" or "unclear"
- module: Cliniconex product module (e.g., Automated Care Messaging)
- feature: Feature used (e.g., ACM Messaging, ACM Alerts)
- solution: How it solves the problem
- benefits: Tangible outcomes

Respond only in this JSON format.

Input: "{user_input}"
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"❌ GPT error: {e}")
        return {"type": "unclear", "message": "We couldn’t generate a response at this time."}

# 🎯 Main endpoint
@app.route("/ai", methods=["POST"])
def ai_route():
    try:
        data = request.json
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"type": "unclear", "message": "Please provide a message."}), 400

        match = find_keyword_match(message)
        if match:
            row = [
                str(datetime.now()),
                message,
                match.get("product", ""),
                match["features"][0] if match.get("features") else "",
                "solution",
                "matrix",
                match.get("issue", ""),
                match.get("solution", "")
            ]
            log_to_google_sheet(row)
            return jsonify({
                "type": "solution",
                "module": match.get("product", ""),
                "feature": match["features"][0] if match.get("features") else "",
                "solution": match.get("solution", ""),
                "benefits": match.get("benefits", "")
            })
        else:
            gpt_result = get_gpt_solution(message)
            if gpt_result.get("type") == "solution":
                row = [
                    str(datetime.now()),
                    message,
                    gpt_result.get("module", ""),
                    gpt_result.get("feature", ""),
                    "solution",
                    "gpt-fallback",
                    "",
                    gpt_result.get("solution", "")
                ]
                log_to_google_sheet(row)
            return jsonify(gpt_result)

    except Exception as e:
        print(f"❌ Internal error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/", methods=["GET"])
def index():
    return "✅ Cliniconex AI Solution Advisor is running."

if __name__ == "__main__":
    app.run(debug=False, port=10000, host="0.0.0.0")
