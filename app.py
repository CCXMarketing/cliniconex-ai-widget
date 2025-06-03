# Refactored Cliniconex AI Solution Advisor Backend
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
CORS(app)

# ✅ Environment and API setup
openai.api_key = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

# ✅ Load solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# ✅ Google Sheets setup
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
sheet = build("sheets", "v4", credentials=credentials).spreadsheets()

# ✅ Utility Functions
def normalize(text):
    return text.lower().strip()

def score_keywords(message, item):
    return sum(1 for k in item.get("keywords", []) if k.lower() in message)

def get_best_matrix_match(message):
    best_score, best_item, best_keyword = 0, None, None
    for item in solution_matrix:
        score = score_keywords(message, item)
        if score > best_score:
            best_score = score
            best_item = item
            best_keyword = next((k for k in item.get("keywords", []) if k.lower() in message), None)
    return best_score, best_item, best_keyword

def validate_gpt_response(parsed):
    required_keys = {"product", "feature", "how_it_works", "benefits"}
    return all(k in parsed and parsed[k] for k in required_keys)

def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'{.*}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else None

def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        
        # Join the features into a single string
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
    You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.
    
    Cliniconex offers the **Automated Care Platform (ACP)** — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:
    
    - **Automated Care Messaging (ACM)** – used to streamline outreach to patients, families, and staff through voice, SMS, and email.
    - **Automated Care Scheduling (ACS)** – used to automate appointment scheduling and related workflows.
    
    These solutions include the following features:
    
    **Automated Care Messaging (ACM):**
    - **ACM Messenger** – Delivers personalized messages to patients, families, and staff using voice, SMS, or email. Commonly used for appointment reminders, procedure instructions, care plan updates, and general announcements. Messages can include dynamic content, embedded links, and conditional logic based on EMR data.
    - **ACM Vault** – Automatically stores every message sent or received in a secure, audit-ready repository. Enables full traceability of communication history for regulatory compliance, quality assurance, or care review. Vault entries are accessible by staff for follow-up, and optionally viewable by patients or families.
    - **ACM Alerts** – Triggers staff notifications based on communication outcomes. Alerts can be used to flag unconfirmed appointments, failed message deliveries, or lack of patient response. This ensures human follow-up is only initiated when truly needed, saving staff time and avoiding missed care opportunities.
    - **ACM Concierge** – Pulls real-time queue and scheduling data from your EMR to inform patients and families about estimated wait times, delays, or provider availability. Used to manage expectations and reduce front desk call volume during high-traffic periods. Can also support mobile-first communication workflows (e.g., “wait in car until called”).
    
    **Automated Care Scheduling (ACS):**
    - **ACS Booking** – Provides patients with an easy-to-use, self-service interface to schedule, confirm, cancel, or reschedule their own appointments online. Integrates with the EMR to reflect real-time availability and automatically sends confirmations and reminders to reduce no-shows.
    - **ACS Forms** – Sends digital intake, consent, or follow-up forms to patients before their visit. Automatically collects and routes responses to the appropriate staff or EMR fields, reducing paperwork and front-desk bottlenecks. Also supports automated reminders for incomplete forms.
    - **ACS Surveys** – Sends brief post-care or post-visit surveys to patients or families to gather feedback on experience, satisfaction, or outcomes. Survey responses can be analyzed for trends and used to inform continuous improvement, patient engagement, or compliance reporting.
    
    Here is a real-world issue described by a healthcare provider:
    "{message}"
    
    Your task is to:
    1. Determine whether the issue aligns best with **Automated Care Messaging**, **Automated Care Scheduling**, or both.
    2. Select **one or more features** from the list above that are most relevant. If only one feature is needed to solve the issue, provide just that feature. If multiple features are needed, provide a list of all the relevant features.
    3. Write **one concise paragraph** explaining how the selected product(s) and feature(s) solve the issue inputted — include how this fits within the overall Automated Care Platform (ACP).
    4. Provide a list of **2–3 specific operational benefits** written in Cliniconex’s confident, helpful tone.
    5. **Include ROI**: If relevant and calculable, provide an estimated **ROI** calculation in the following format:
       - **ROI**: Reduces [issue] by **X%**, increasing clinic revenue by an estimated **$Y/year** or saving **Z hours/year** in staff time. 
       - If **ROI is not calculated** or **not available**, omit both the **ROI** and **disclaimer** fields entirely.
    6. **Provide a disclaimer** that the ROI estimates are based on typical industry benchmarks and assumptions for healthcare settings:
       - **Disclaimer**: "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
    
    Respond ONLY in this exact JSON format:
    
    {{" 
      "product": "Automated Care Messaging",
      "feature": ["ACM Messenger", "ACM Alerts"],
      "how_it_works": "One paragraph that connects the solution to the problem and explains how the feature fits into the broader ACP.",
      "benefits": ["Reduces administrative workload by automating appointment reminders", "Improves patient satisfaction by reducing missed appointments", "Optimizes resource allocation by reducing no-shows"],
      "roi": "Reduces no-shows by **20%**, improving clinic revenue by an estimated **$50,000/year** due to more patients attending follow-ups.",
      "disclaimer": "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
    }}
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
            print("⚠️ GPT returned invalid response:", raw_output)
            return None

        if validate_gpt_response(parsed):
            # Check if ROI is available, if not, remove it and the disclaimer
            if "roi" not in parsed or parsed["roi"] == "":
                parsed.pop("roi", None)
                parsed.pop("disclaimer", None)

            return parsed
        else:
            print("⚠️ GPT response missing required fields.")
            return None
    except Exception as e:
        print("❌ GPT fallback error:", str(e))
        traceback.print_exc()
        return None



# ✅ Main AI Route
@app.route("/ai", methods=["POST"])
def get_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        print("📩 /ai endpoint hit")
        print("🔍 Message received:", message)

        matrix_score, matrix_item, keyword = get_best_matrix_match(message)
        gpt_response = generate_gpt_solution(message)

        use_matrix = (
            matrix_score >= 2 and matrix_item and gpt_response and
            gpt_response.get("product", "").lower() in matrix_item.get("product", "").lower()
        )

        if use_matrix:
            response = {
                "type": "solution",
                "module": matrix_item.get("product", "N/A"),
                "feature": ", ".join(matrix_item.get("features", [])) or "N/A",
                "solution": matrix_item.get("solution", "N/A"),
                "benefits": matrix_item.get("benefits", "N/A"),
                "keyword": keyword or "N/A"
            }
            log_to_google_sheets(message, page_url, response["module"], response["feature"], "matrix", matrix_item.get("issue", "N/A"), response["solution"], keyword)
            return jsonify(response)

        elif gpt_response:
            benefits = gpt_response.get("benefits", [])
            benefits_str = "\n".join(f"- {b}" for b in benefits) if isinstance(benefits, list) else str(benefits)
            response = {
                "type": "solution",
                "module": gpt_response.get("product", "N/A"),
                "feature": gpt_response.get("feature", "N/A"),
                "solution": gpt_response.get("how_it_works", "No solution provided"),
                "benefits": benefits_str,
                "keyword": message
            }
            log_to_google_sheets(message, page_url, response["module"], response["feature"], "gpt-fallback", "GPT generated", response["solution"], message)
            return jsonify(response)

        return jsonify({"type": "no_match", "message": "We couldn't generate a relevant solution."})

    except Exception as e:
        print("❌ Internal Server Error:", str(e))
        traceback.print_exc()
        return jsonify({"type": "error", "message": "Internal Server Error"}), 500

# ✅ Start app for Render
if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
