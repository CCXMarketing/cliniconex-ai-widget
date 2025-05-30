from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openai
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ✅ Load environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Flask setup
app = Flask(__name__)
CORS(app)

# ✅ Load solutions with keywords
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# ✅ Google Sheets logging
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

# ✅ Keyword matcher
def find_keyword_match(user_input):
    input_lower = user_input.lower()
    for entry in solution_matrix:
        for keyword in entry.get("keywords", []):
            if keyword.lower() in input_lower:
                print(f"🔑 Keyword match found: '{keyword}' in '{user_input}'")
                return entry
    return None

# ✅ GPT fallback
def get_gpt_solution(user_input):
    prompt = f"""
You are a helpful assistant working for Cliniconex, a healthcare communication company.
Your task is to interpret vague or brief input from healthcare professionals and return a JSON with:
- type: "solution" or "unclear"
- module: Cliniconex product module (e.g., Automated Care Messaging)
- feature: Feature(s) used (e.g., ACM Messaging, ACM Alerts)
- solution: How it solves the problem
- benefits: Tangible outcomes

Only describe solutions using the following Cliniconex modules and features:
ACM Messaging, ACM Alerts, ACM Vault, ACM Concierge, ACS Booking, ACS Forms, ACS Surveys.

If no appropriate solution exists, respond with:
{{"type": "unclear"}}

Respond only in this JSON format.

Input: "{user_input}"
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()
        return json.loads(reply)
    except Exception as e:
        print(f"❌ GPT error: {e}")
        return {"type": "unclear", "message": "We couldn’t generate a response at this time."}

# ✅ Main endpoint
@app.route("/ai", methods=["POST"])
def ai_route():
    try:
        data = request.json
        message = data.get("message", "").strip()
        page_url = data.get("page_Url", "")  # ✅ Capture page URL

        if not message:
            return jsonify({"type": "unclear", "message": "Please provide a message."}), 400

        match = find_keyword_match(message)
        if match:
            features_list = match.get("features", [])
            feature_display = " | ".join([f"{feat.strip()}" for feat in features_list])
            feature_display = feature_display.replace("|", "<strong> | </strong>")

            row = [
                str(datetime.now()),
                message,
                match.get("product", ""),
                feature_display,
                "solution",
                "matrix",
                match.get("issue", ""),
                match.get("solution", ""),
                page_url
            ]
            log_to_google_sheet(row)

            return jsonify({
                "type": "solution",
                "module": match.get("product", ""),
                "feature": f"Feature: {feature_display}" if feature_display else "Feature: Not specified",
                "solution": match.get("solution", ""),
                "benefits": match.get("benefits", "")
            })

        else:
            gpt_result = get_gpt_solution(message)
            if gpt_result.get("type") == "solution":
                features_raw = gpt_result.get("feature", "")
                features = [f.strip() for f in features_raw.split(",") if f.strip()]
                feature_display = " | ".join(features)
                feature_display = feature_display.replace("|", "<strong> | </strong>")

                row = [
                    str(datetime.now()),
                    message,
                    gpt_result.get("module", ""),
                    feature_display,
                    "solution",
                    "gpt-fallback",
                    "",
                    gpt_result.get("solution", ""),
                    page_url
                ]
                log_to_google_sheet(row)

                return jsonify({
                    "type": "solution",
                    "module": gpt_result.get("module", ""),
                    "feature": f"Feature: {feature_display}" if feature_display else "Feature: Not specified",
                    "solution": gpt_result.get("solution", ""),
                    "benefits": gpt_result.get("benefits", "")
                })

            return jsonify(gpt_result)

    except Exception as e:
        print(f"❌ Internal error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# ✅ Health check
@app.route("/", methods=["GET"])
def index():
    return "✅ Cliniconex AI Solution Advisor is running."

if __name__ == "__main__":
    app.run(debug=False, port=10000, host="0.0.0.0")
