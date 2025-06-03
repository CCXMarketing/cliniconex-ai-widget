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
PORT = int(os.getenv("PORT", 10000))  # Ensure this is set properly from environment or defaults to 10000
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

# ✅ Load solution matrix
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

# ✅ Google Sheets setup
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
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
    - **ACM Messenger**, **ACM Vault**, **ACM Alerts**, **ACM Concierge**, **ACS Booking**, **ACS Forms**, and **ACS Surveys**.

    Here is a real-world issue described by a healthcare provider:
    "{message}"

    Your task is to:
    1. Determine whether the issue aligns best with **Automated Care Messaging**, **Automated Care Scheduling**, or both.
    2. Select **one or more features** from the list above that are most relevant. If only one feature is needed to solve the issue, provide just that feature. If multiple features are needed, provide a list of all the relevant features.
    3. Write **one concise paragraph** explaining how the selected product(s) and feature(s) solve the issue inputted — include how this fits within the broader Automated Care Platform (ACP).
    4. Provide a list of **2–3 specific operational benefits** written in Cliniconex’s confident, helpful tone.
    5. **Include ROI**: Provide an estimated **ROI calculation** in the following format:
       - **ROI**: Reduces [issue] by **X%**, increasing clinic revenue by an estimated **$Y/year** or saving **Z hours/year** in staff time.
    6. **Provide a disclaimer** that the ROI estimates are based on typical industry benchmarks and assumptions for healthcare settings:
       - **Disclaimer**: "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."

    Respond ONLY in this exact JSON format:

    {{
      "product": "Automated Care Messaging",
      "feature": ["ACM Messenger", "ACS Booking"],  // Can also be a single feature
      "how_it_works": "One paragraph that connects the solution to the problem and explains how the feature fits into the broader ACP.",
      "benefits": [
        "Reduces administrative workload by automating appointment reminders.",
        "Improves patient satisfaction and care by reducing missed appointments.",
        "Optimizes resource allocation by reducing no-shows and prompt rescheduling."
      ],
      "roi": "Reduces no-show rates by **20%**, increasing clinic revenue by an estimated **$50,000/year** due to more patients attending follow-ups.",
      "Note": "The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
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
        raw_output = response['choices'][0]['message']['content']
        print("🧠 GPT raw output:\n", raw_output)

        parsed = extract_json(raw_output)
        
        if parsed is None:
            # GPT fallback: construct a default response with placeholder ROI and disclaimer
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

        # Ensure ROI and disclaimer are always present
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

        matrix_score, matrix_item, keyword = get_best_matrix_match(message)
        gpt_response = generate_gpt_solution(message)

        # Determine whether we are using a matrix solution or a GPT fallback
        use_matrix = (
            matrix_score >= 2 and matrix_item and
            gpt_response.get("product", "").lower() in matrix_item.get("product", "").lower()
        )

        if use_matrix:
            # Log the matrix solution and related details
            status = "matrix"
            matched_issue = matrix_item.get("product", "N/A")  # Match to the product/issue
            response = {
                "type": "solution",
                "module": matrix_item.get("product", "N/A"),
                "feature": ", ".join(matrix_item.get("features", [])) or "N/A",
                "solution": matrix_item.get("solution", "N/A"),
                "benefits": matrix_item.get("benefits", "N/A"),
                "keyword": keyword or "N/A"
            }
            log_to_google_sheets(message, page_url, matrix_item.get("product", "N/A"), matrix_item.get("features", []), status, matched_issue, "N/A", keyword)
        else:
            # Log the fallback solution and related details
            status = "fallback"
            matched_issue = "N/A"  # No matrix match
            response = {
                "type": "solution",
                "module": gpt_response.get("product", "N/A"),
                "feature": ", ".join(gpt_response.get("feature", [])) or "N/A",
                "solution": gpt_response.get("how_it_works", "N/A"),
                "
