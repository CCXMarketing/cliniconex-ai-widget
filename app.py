from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import openai
import os
import json
import traceback
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
    try:
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
    except Exception as e:
        print("❌ Error logging to Google Sheets:", str(e))
        traceback.print_exc()

# ✅ AI endpoint
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
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
                "module": matched_solution.get("solution", "N/A"),
                "feature": matched_solution.get("features_used", "N/A"),
                "solution": matched_solution.get("description", "N/A"),
                "benefits": matched_solution.get("benefits", "N/A"),
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

    except Exception as e:
        print("❌ Internal Server Error:", str(e))
        traceback.print_exc()
        return jsonify({
            "type": "error",
            "message": "Internal Server Error"
        }), 500

# ✅ Render-compatible port binding
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Starting Cliniconex AI widget on port {port}")
    app.run(host="0.0.0.0", port=port)
