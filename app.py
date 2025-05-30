# ✅ Updated app.py with GPT validation for matrix match
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

# ✅ GPT fallback generation
def get_gpt_fallback(message):
    fallback_prompt = f"""
You are a Cliniconex expert who has extensive and deep knowledge of the products and solutions and can provide a solution for any issue you come across. Whether it's one product or multiple products that form a solution, you know what to recommend. You are also an expert in the features each product offers and can easily provide recommendations.

Based on the following issue from a healthcare provider:
"{message}"

Your task is to:
1. Identify the most relevant Cliniconex product (Automated Care Messaging or Automated Care Scheduling).
2. Choose one or more matching features from this list: ACM Messaging, ACM Vault, ACM Alerts, ACM Concierge, ACS Booking, ACS Forms, ACS Surveys.
3. Explain how the product addresses the issue.
4. Provide 2–3 concrete benefits in Cliniconex’s tone of voice.
5. Include how ACM or ACS fits into the broader Automated Care Platform.

Return JSON like:
{{
  "product": "Automated Care Scheduling",
  "feature": "ACS Booking – Enables self-service scheduling for patients via online portals.",
  "how_it_works": "Explain in one paragraph...",
  "benefits": "Bullet-style phrasing."
}}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": fallback_prompt}]
    )
    return json.loads(response.choices[0].message.content)

# ✅ Matrix result validator
def validate_matrix_with_gpt(message, matrix_result):
    validation_prompt = f"""
You are an expert at reviewing healthcare solutions from Cliniconex.

A user has entered the issue:
"{message}"

A solution was found in the matrix:
Product: {matrix_result['product']}
Features: {matrix_result['feature']}
Solution: {matrix_result['solution']}
Benefits: {matrix_result['benefits']}

Does this matrix solution logically and effectively address the user's issue?
Respond only with "yes" or "no".
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": validation_prompt}]
    )
    return response.choices[0].message.content.strip().lower() == "yes"

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
            module = matched_solution.get("product", "N/A")
            feature_list = matched_solution.get("features", [])
            feature = ", ".join(feature_list) if feature_list else "N/A"
            how_it_works = matched_solution.get("solution", "N/A")
            benefits = matched_solution.get("benefits", "N/A")
            matched_issue = matched_solution.get("issue", "N/A")
            keyword = matched_keyword or "N/A"

            matrix_result = {
                "type": "solution",
                "module": module,
                "feature": feature,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": keyword,
                "status": "matrix",
                "matched_issue": matched_issue,
                "matched_solution": how_it_works
            }

            if validate_matrix_with_gpt(message, matrix_result):
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
                return jsonify(matrix_result)

        # 🔁 Fall back to GPT
        gpt_response = get_gpt_fallback(message)
        log_to_google_sheets(
            message,
            page_url,
            gpt_response.get("product", "GPT generated"),
            gpt_response.get("feature", "GPT generated"),
            "gpt-fallback",
            "GPT generated",
            gpt_response.get("how_it_works", "N/A"),
            "GPT"
        )

        return jsonify({
            "type": "solution",
            "module": gpt_response.get("product", "N/A"),
            "feature": gpt_response.get("feature", "N/A"),
            "solution": gpt_response.get("how_it_works", "N/A"),
            "benefits": gpt_response.get("benefits", "N/A"),
            "keyword": "GPT"
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
