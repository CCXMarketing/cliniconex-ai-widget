from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from zoneinfo import ZoneInfo
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

# ✅ Logging function
def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        values = [[
            timestamp,
            prompt,
            product,
            feature,
            status,
            matched_issue,
            matched_solution,
            page_url,
            keyword
        ]]
        sheet.values().append(
            spreadsheetId=SHEET_ID,
            range="Advisor Logs!A1",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
    except Exception as e:
        print("❌ Error logging to Google Sheets:", str(e))
        traceback.print_exc()

# ✅ GPT fallback prompt
def generate_gpt_solution(issue):
    gpt_prompt = f"""
You are a Cliniconex expert who has deep knowledge of our products and features and can confidently recommend solutions to healthcare industry problems. Your task is to:

1. Identify whether the issue is best addressed by Automated Care Messaging (ACM), Automated Care Scheduling (ACS), or both.
2. Select one or more relevant features from: ACM Messaging, ACM Vault, ACM Alerts, ACM Concierge, ACS Booking, ACS Forms, ACS Surveys.
3. Clearly explain how the recommended solution addresses the issue.
4. Provide 2–3 concrete benefits in a friendly, clinical tone.

Note: These products are part of the larger Cliniconex Automated Care Platform that streamlines communication and scheduling for providers and patients.

Based on the issue:
\"\"\"{issue}\"\"\"

Return valid JSON exactly like:
{{
  "product": "Automated Care Messaging",
  "feature": "ACM Messaging – Delivers appointment updates via voice, text, or email.",
  "how_it_works": "Explain in a short paragraph...",
  "benefits": "- Improves patient communication\n- Reduces manual staff work\n- Decreases no-show rates"
}}
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{
                "role": "user",
                "content": gpt_prompt
            }],
            temperature=0.4
        )
        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        print("❌ GPT fallback failed:", str(e))
        traceback.print_exc()
        return None

# ✅ AI endpoint
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        print("📩 /ai endpoint hit")
        print("🔍 Message received:", message)

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
            # Matrix match result
            product = matched_solution.get("product", "N/A")
            feature_list = matched_solution.get("features", [])
            feature = ", ".join(feature_list) if feature_list else "N/A"
            how_it_works = matched_solution.get("solution", "N/A")
            benefits = matched_solution.get("benefits", "N/A")
            matched_issue = matched_solution.get("issue", "N/A")
            keyword = matched_keyword or "N/A"

            result = {
                "type": "solution",
                "module": product,
                "feature": feature,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": keyword
            }

            log_to_google_sheets(
                message,
                page_url,
                product,
                feature,
                "matrix",
                matched_issue,
                how_it_works,
                keyword
            )

            print("✅ Matrix match returned.")
            return jsonify(result)

        # ✅ GPT fallback
        gpt_result = generate_gpt_solution(message)
        if gpt_result:
            result = {
                "type": "solution",
                "module": gpt_result.get("product", "GPT fallback"),
                "feature": gpt_result.get("feature", "GPT fallback"),
                "solution": gpt_result.get("how_it_works", "Generated by GPT"),
                "benefits": gpt_result.get("benefits", "Generated by GPT"),
                "keyword": message
            }

            log_to_google_sheets(
                message,
                page_url,
                result["module"],
                result["feature"],
                "gpt-fallback",
                "GPT generated",
                result["solution"],
                result["keyword"]
            )

            print("✅ GPT fallback returned.")
            return jsonify(result)

        print("❌ No solution found. GPT fallback failed.")
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

# ✅ Port binding for Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Starting Cliniconex AI widget on port {port}")
    app.run(host="0.0.0.0", port=port)
