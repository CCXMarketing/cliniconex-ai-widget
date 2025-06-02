from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from zoneinfo import ZoneInfo
import openai
import os
import json
import traceback
import re

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

# ✅ Logging to Google Sheets
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

# ✅ GPT fallback generator
def generate_gpt_solution(message):
    gpt_prompt = f"""\
You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.

Cliniconex offers the **Automated Care Platform (ACP)** — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:

**Automated Care Messaging (ACM):**
- **ACM Messenger** – Delivers personalized messages to patients, families, and staff using voice, SMS, or email.
- **ACM Vault** – Automatically stores all communications for compliance and auditing.
- **ACM Alerts** – Notifies staff only when human follow-up is needed.
- **ACM Concierge** – Shares real-time wait time data with patients and families.

**Automated Care Scheduling (ACS):**
- **ACS Booking** – Enables self-service appointment scheduling for patients.
- **ACS Forms** – Collects intake or follow-up information automatically.
- **ACS Surveys** – Gathers feedback from patients or families post-care.

A healthcare provider has described the following issue:
"{message}"

Your task is to:
1. Determine whether the issue aligns best with **Automated Care Messaging**, **Automated Care Scheduling**, or both.
2. Select **one or more features** from the list above that directly address the issue.
3. Write **one concise paragraph** explaining how the selected product(s) and feature(s) solve the issue—be specific about workflows and EMR integration.
4. Provide a list of **2–3 specific operational benefits** in a confident, helpful tone.

Respond **only** in this exact JSON format:

{{
  "product": "[Automated Care Messaging, Automated Care Scheduling, or both]",
  "feature": "[List of one or more features with short descriptions]",
  "how_it_works": "One paragraph that connects the solution to the problem and explains how the feature fits into the broader ACP.",
  "benefits": [
    "Clear and specific benefit 1.",
    "Clear and specific benefit 2.",
    "Optional third benefit."
  ]
}}

Do not include anything outside the JSON block.
Focus on solving the issue. Be specific. Use real-world healthcare workflow language.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": gpt_prompt}],
            temperature=0.7
        )
        result_text = response['choices'][0]['message']['content']
        print("🧠 GPT raw output:\n", result_text, flush=True)

        try:
            parsed = json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ Standard JSON parsing failed. Attempting regex fallback.")
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
            else:
                print("❌ Regex fallback failed to extract JSON.")
                return None

        required_keys = {"product", "feature", "how_it_works", "benefits"}
        if all(k in parsed and parsed[k] for k in required_keys):
            return parsed
        else:
            print("❌ Parsed GPT response missing required fields.")
            return None

    except Exception as e:
        print("❌ GPT fallback error:", str(e))
        traceback.print_exc()
        return None


# ✅ AI endpoint
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        best_matrix_score = 0
        best_matrix_match = None
        best_matrix_keyword = None

        def score_match(msg, item):
            return sum(1 for k in item.get("keywords", []) if k.lower() in msg)

        for item in solution_matrix:
            score = score_match(message, item)
            if score > best_matrix_score:
                best_matrix_score = score
                best_matrix_match = item
                best_matrix_keyword = next((k for k in item.get("keywords", []) if k.lower() in message), None)

        gpt_response = generate_gpt_solution(message)

        use_matrix = (
            best_matrix_score >= 2 and
            best_matrix_match and
            gpt_response and (
                gpt_response.get("product", "").lower() in best_matrix_match.get("product", "").lower()
            )
        )

        if use_matrix:
            item = best_matrix_match
            module = item.get("product", "N/A")
            features = ", ".join(item.get("features", [])) or "N/A"
            how_it_works = item.get("solution", "N/A")
            benefits = item.get("benefits", "N/A")
            issue = item.get("issue", "N/A")
            keyword = best_matrix_keyword or "N/A"

            log_to_google_sheets(message, page_url, module, features, "matrix", issue, how_it_works, keyword)

            return jsonify({
                "type": "solution",
                "module": module,
                "feature": features,
                "solution": how_it_works,
                "benefits": benefits,
                "keyword": keyword
            })

  elif gpt_response:
    # Normalize product/feature names...
    corrections = {
        "ACM Messaging": "ACM Messenger",
        "ACM Communication": "ACM Messenger",
        "ACS Scheduling": "ACS Booking"
    }

    for wrong, correct in corrections.items():
        gpt_response["feature"] = gpt_response.get("feature", "").replace(wrong, correct)
        gpt_response["product"] = gpt_response.get("product", "").replace(wrong, correct)

    # ✅ This should NOT be inside the loop
    product = gpt_response.get("product", "N/A")
    feature = gpt_response.get("feature", "N/A")
    how_it_works = gpt_response.get("how_it_works", "No solution provided")
    benefits = gpt_response.get("benefits", [])

    if isinstance(benefits, list):
        benefits_str = "\n".join(f"- {b}" for b in benefits)
    else:
        benefits_str = str(benefits)

    log_to_google_sheets(
        message, page_url, product, feature,
        "gpt-fallback", "GPT generated", how_it_works, message
    )

    return jsonify({
        "type": "solution",
        "module": product,
        "feature": feature,
        "solution": how_it_works,
        "benefits": benefits_str,
        "keyword": message
    })


        else:
            return jsonify({
                "type": "no_match",
                "message": "We couldn't generate a relevant solution."
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "type": "error",
            "message": "Internal Server Error"
        }), 500

# ✅ Render-compatible launch
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"✅ Starting Cliniconex AI widget on port {port}")
    app.run(host="0.0.0.0", port=port)
