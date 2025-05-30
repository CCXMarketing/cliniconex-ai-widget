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

# ✅ Google Sheets logging
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
def generate_gpt_solution(message):
    gpt_prompt = f"""
You are a Cliniconex expert with deep knowledge of all Cliniconex products and features. Given the issue:

\"{message}\"

Do the following:
1. Recommend the most relevant Cliniconex product(s): Automated Care Messaging (ACM), Automated Care Scheduling (ACS), or both.
2. Recommend one or more features from: ACM Messaging, ACM Vault, ACM Alerts, ACM Concierge, ACS Booking, ACS Forms, ACS Surveys.
3. Explain how the product(s) solve the issue.
4. List 2–3 benefits.

Tie all solutions back to the broader Automated Care Platform (ACP).

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
            messages=[{"role": "system", "content": gpt_prompt}],
            temperature=0.7
        )
        result_text = response['choices'][0]['message']['content']
        return json.loads(result_text)
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

        print("📩 /ai endpoint hit", flush=True)
        print("🔍 Message received:", message, flush=True)

        # Matrix keyword match
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

        # Decision logic
        if matched_solution:
            issue_text = matched_solution.get("issue", "").lower()
            if len(message.split()) >= 5 and matched_keyword not in issue_text:
                print("🤖 GPT fallback activated due to low keyword relevance", flush=True)
                matched_solution = None  # GPT will override

        # Return matrix match
        if matched_solution:
            module = matched_solution.get("product", "N/A")
            features = ", ".join(matched_solution.get("features", [])) or "N/A"
            how_it_works = matched_solution.get("solution", "N/A")
            benefits = matched_solution.get("benefits", "N/A")
            issue = matched_solution.get("issue", "N/A")
            keyword = matched_keyword or "N/A"

            log_to_google_sheets(message, page_url, module, features, "matrix", issue, how_it_works, keyword)

            return jsonify({
                "type": "solution",
                "module": module,
                "feature": features,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": keyword
            })

        # Fallback to GPT
        gpt_response = generate_gpt_solution(message)
        if gpt_response:
            product = gpt_response.get("product", "N/A")
            feature = gpt_response.get("feature", "N/A")
            how_it_works = gpt_response.get("how_it_works", "N/A")
            benefits = gpt_response.get("benefits", "N/A")

            log_to_google_sheets(message, page_url, product, feature, "gpt-fallback", "GPT generated", how_it_works, message)

            return jsonify({
                "type": "solution",
                "module": product,
                "feature": feature,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": message
            })

        print("❌ GPT fallback failed to generate a response.", flush=True)
        return jsonify({
            "type": "no_match",
            "message": "We couldn't generate a relevant solution."
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
