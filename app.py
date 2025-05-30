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

            print("✅ Returning result to frontend:", json.dumps(result, indent=2), flush=True)

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

        # ❌ No keyword match – use GPT fallback
        print("⚠️ No keyword match found. Using GPT fallback...", flush=True)

        try:
            gpt_prompt = f"A healthcare provider says: '{message}'. Based on Cliniconex solutions, suggest the most appropriate product, features, and how it helps. Be concise."
            gpt_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a healthcare product expert helping users find Cliniconex solutions."},
                    {"role": "user", "content": gpt_prompt}
                ],
                temperature=0.7
            )

            gpt_text = gpt_response.choices[0].message["content"].strip()

            result = {
                "type": "solution",
                "module": "GPT-generated",
                "feature": "GPT-generated",
                "solution": gpt_text,
                "benefits": "GPT-generated based on context.",
                "keyword": "N/A"
            }

            print("🤖 GPT Fallback Result:", json.dumps(result, indent=2), flush=True)

            log_to_google_sheets(
                message,
                page_url,
                "GPT-generated",
                "GPT-generated",
                "gpt-fallback",
                message,        # ✅ Log original prompt as matched issue
                gpt_text,
                "N/A"
            )

            return jsonify(result)

        except Exception as e:
            print("❌ GPT fallback failed:", str(e), flush=True)
            traceback.print_exc()
            return jsonify({
                "type": "error",
                "message": "GPT fallback failed"
            }), 500

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
