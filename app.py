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

# ✅ AI endpoint
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        print("📩 /ai endpoint hit", flush=True)
        print("🔍 Message received:", message, flush=True)

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
            module = matched_solution.get("product", "N/A")
            feature_list = matched_solution.get("features", [])
            feature = ", ".join(feature_list) if feature_list else "N/A"
            how_it_works = matched_solution.get("solution", "N/A")
            benefits = matched_solution.get("benefits", "N/A")
            matched_issue = matched_solution.get("issue", "N/A")
            keyword = matched_keyword or "N/A"

            result = {
                "type": "solution",
                "module": module,
                "feature": feature,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": keyword
            }

            log_to_google_sheets(
                message,
                page_url,
                module,
                feature,
                "matrix",
                matched_issue,
                how_it_works,
                keyword
            )

            return jsonify(result)

        # ✅ GPT fallback
        gpt_prompt = f"""
You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.

Based on the following issue from a healthcare provider:
"{message}"

Your task is to:
1. Identify the most relevant Cliniconex product or combination of products (Automated Care Messaging and/or Automated Care Scheduling) as part of the overarching Automated Care Platform.
2. Select the most appropriate feature(s) from this list: ACM Messaging, ACM Vault, ACM Alerts, ACM Concierge, ACS Booking, ACS Forms, ACS Surveys.
3. Clearly explain how the chosen product(s) and features address the issue, written in a clear and professional tone suitable for healthcare decision-makers.
4. Provide 2–3 specific, tangible benefits written in Cliniconex’s tone: outcome-focused, value-driven, and patient/staff-centric.

Return only a valid JSON object in this format:
{{
  "product": "Automated Care Messaging",
  "feature": "ACM Messaging – Delivers messages over voice, text, and email. Channel Ranking – Uses EMR history to select the most effective method for each recipient.",
  "how_it_works": "Explain in 2–3 sentences how the solution resolves the issue, written in the tone of a solution overview.",
  "benefits": "• Reduces staff workload by automating message delivery\\n• Increases patient engagement using preferred communication channels\\n• Improves care coordination and reduces missed appointments"
}}
"""

        gpt_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": gpt_prompt}],
            temperature=0.4
        )

        parsed = json.loads(gpt_response.choices[0].message["content"])
        module = parsed.get("product", "N/A")
        feature = parsed.get("feature", "N/A")
        how_it_works = parsed.get("how_it_works", "N/A")
        benefits = parsed.get("benefits", "N/A")

        result = {
            "type": "solution",
            "module": module,
            "feature": feature,
            "solution": how_it_works,
            "benefits": benefits,
            "keyword": message
        }

        log_to_google_sheets(
            message,
            page_url,
            module,
            feature,
            "gpt-fallback",
            "GPT-generated",
            how_it_works,
            message
        )

        return jsonify(result)

    except Exception as e:
        print("❌ Internal Server Error:", str(e), flush=True)
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
