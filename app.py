from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openai
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ✅ Flask setup
app = Flask(__name__)
CORS(app)

# ✅ Load OpenAI key
openai.api_key = os.getenv("OPENAI_API_KEY")

# ✅ Load solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# ✅ Google Sheets setup
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "service_account.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
service = build("sheets", "v4", credentials=credentials)
sheet = service.spreadsheets()

# ✅ Logging function with keyword
def log_to_google_sheets(message, page_url, module, feature, solution, benefits, keyword):
    values = [[
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        page_url,
        message,
        module,
        feature,
        solution,
        benefits,
        keyword
    ]]
    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="Inputs!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

# ✅ AI endpoint
@app.route("/ai", methods=["POST"])
def get_solution():
    data = request.get_json()
    message = data.get("message", "").lower()
    page_url = data.get("page_url", "")

    matched_keyword = None
    matched_solution = None

    for item in solution_matrix:
        for keyword in item.get("keywords", []):
            if keyword.lower() in message:
                matched_keyword = keyword
                matched_solution = item
                break
        if matched_solution:
            break

    if matched_solution:
        result = {
            "type": "solution",
            "module": matched_solution.get("solution", ""),
            "feature": matched_solution.get("features_used", ""),
            "solution": matched_solution.get("description", ""),
            "benefits": matched_solution.get("benefits", ""),
            "keyword": matched_keyword or "N/A"
        }

        log_to_google_sheets(
            message, page_url,
            result["module"],
            result["feature"],
            result["solution"],
            result["benefits"],
            result["keyword"]
        )

        return jsonify(result)

    return jsonify({
        "type": "no_match",
        "message": "No matching solution found."
    })
