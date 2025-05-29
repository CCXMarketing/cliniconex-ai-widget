from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openai
import os
import json
from rapidfuzz import process, fuzz
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load the solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# Helper function to find best match from matrix
def find_best_match(user_input):
    issues = [entry["issue"] for entry in solution_matrix]
    match, score, index = process.extractOne(user_input, issues, scorer=fuzz.token_sort_ratio)
    if score > 70:
        return solution_matrix[index]
    else:
        return None

# Helper function to log to Google Sheets
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

# Endpoint to get AI solution
@app.route("/ai", methods=["POST"])
def ai_route():
    try:
        data = request.json
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"type": "unclear", "message": "Message input was empty."}), 400

        match = find_best_match(message)

        if match:
            row_data = [
                str(datetime.now()),
                message,
                match.get('product', ''),
                match['features'][0] if match.get('features') else '',
                "solution",
                "success",
                match.get('issue', ''),
                match.get('solution', '')
            ]
            log_to_google_sheet(row_data)

            return jsonify({
                "type": "solution",
                "module": match.get("product", ""),
                "feature": match["features"][0] if match.get("features") else '',
                "solution": match.get("solution", ""),
                "benefits": match.get("benefits", "")
            })
        else:
            return jsonify({
                "type": "unclear",
                "message": "We couldn’t match your issue to a known solution. Please try rephrasing."
            })
    except Exception as e:
        print(f"❌ Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Health check
@app.route("/", methods=["GET"])
def index():
    return "✅ Cliniconex Solution Advisor is running."

if __name__ == "__main__":
    app.run(debug=False, port=10000, host="0.0.0.0")
