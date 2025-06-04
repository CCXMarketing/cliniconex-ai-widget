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

# ✅ CORS configuration to allow only specific origin (replace with actual frontend URL)
CORS(app, resources={r"/*": {"origins": "https://cliniconex.com"}})

# ✅ Environment and API setup
openai.api_key = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

# ✅ Google Sheets setup
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = build("sheets", "v4", credentials=credentials).spreadsheets()

# ✅ Utility Functions
def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'{.*}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else None

def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        feature_str = ', '.join(feature) if isinstance(feature, list) else feature
        values = [[timestamp, prompt, product, feature_str, status, matched_issue, matched_solution, page_url, keyword]]
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
<INSERT PROMPT CONTENT HERE>
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": gpt_prompt}],
            temperature=0.7
        )
        raw_output = response['choices'][0]['message']['content']
        print("🧠 GPT raw output:\n", raw_output)

        parsed = extract_json(raw_output)

        if parsed is None:
            parsed = {
                "product": "Automated Care Messaging",
                "feature": ["ACM Messenger", "ACS Booking"],
                "how_it_works": "Placeholder solution based on the issue description.",
                "benefits": [
                    "Automates communications to reduce administrative workload.",
                    "Improves patient engagement by providing reminders."
                ],
                "roi": "Reduces no-show rates by 20%, increasing clinic revenue by an estimated $50,000/year due to more patients attending follow-ups.",
                "disclaimer": "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
            }

        if "roi" not in parsed:
            parsed["roi"] = "Estimated ROI placeholder: Reduces operational inefficiencies, saving significant staff time."
        if "disclaimer" not in parsed:
            parsed["disclaimer"] = "The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."

        return parsed
    except Exception as e:
        print("❌ GPT fallback error:", str(e))
        return {
            "product": "Automated Care Messaging",
            "feature": ["ACM Messenger", "ACS Booking"],
            "how_it_works": "Error in generating solution, please try again.",
            "benefits": [
                "Automates communications to reduce administrative workload.",
                "Improves patient engagement by providing reminders."
            ],
            "roi": "Reduces no-show rates by 20%, increasing clinic revenue by an estimated $50,000/year.",
            "disclaimer": "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
        }

# ✅ Main AI Route
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        print("📩 /ai endpoint hit")
        print("🔍 Message received:", message)

        gpt_response = generate_gpt_solution(message)

        status = "fallback"
        matched_issue = "N/A"
        response = {
            "type": "solution",
            "module": gpt_response.get("product", "N/A"),
            "feature": ", ".join(gpt_response.get("feature", [])) or "N/A",
            "solution": gpt_response.get("how_it_works", "N/A"),
            "benefits": "\n".join(gpt_response.get("benefits", [])) or "N/A",
            "roi": gpt_response.get("roi", "N/A"),
            "disclaimer": gpt_response.get("disclaimer", "N/A")
        }

        log_to_google_sheets(message, page_url, gpt_response.get("product", "N/A"), gpt_response.get("feature", []), status, matched_issue, gpt_response.get("product", "N/A"), "N/A")

        return jsonify(response)
    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": "An error occurred."}), 500

# ✅ Start app for Render
if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
