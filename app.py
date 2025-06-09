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
import tiktoken
from instructions import (
    acm_vault_instruction,
    no_show_instruction,
    family_portal_instruction,
    automation_efficiency_instruction,
    ai_message_assistant_instruction,
    unprepared_patient_instruction,
    ehr_integration_instruction
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://cliniconex.com"}})

openai.api_key = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solution_matrix = json.load(f)

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = build("sheets", "v4", credentials=credentials).spreadsheets()

def normalize(text):
    return text.lower().strip()

def count_tokens(text, model="gpt-4"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def score_keywords(message, item):
    return sum(1 for k in item.get("keywords", []) if k.lower() in message)

def tag_input(message):
    tags = []
    msg = message.lower()
    if "overtime" in msg:
        tags.append("overtime")
    if "check-in" in msg:
        tags.append("check_in")
    if "secure message" in msg or "encrypted" in msg:
        tags.append("secure")
    if "portal" in msg or "family login" in msg:
        tags.append("no_portal")
    if "real-time" in msg or "last minute" in msg:
        tags.append("alerts")
    return tags

def generate_dynamic_instructions(tags):
    rules = []
    if "overtime" in tags:
        rules.append(automation_efficiency_instruction())
    if "check_in" in tags:
        rules.append(unprepared_patient_instruction())
    if "secure" in tags:
        rules.append(acm_vault_instruction())
    if "no_portal" in tags:
        rules.append(family_portal_instruction())
    if "alerts" in tags:
        rules.append(no_show_instruction())
    # Add catch-all rules or context-based instructions
    rules.extend([
        ehr_integration_instruction(),
        ai_message_assistant_instruction()
    ])
    return "\n".join(rules)

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

def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword, full_solution=None, token_count=None, token_cost=None):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        feature_str = ', '.join(feature) if isinstance(feature, list) else feature

        formatted_full_solution = f"""Recommended Product: {product}\n\n\nFeatures: {feature_str}\n\n\nHow it works: {matched_solution}"""

        full_solution_to_log = full_solution if full_solution else formatted_full_solution

        values = [[
            timestamp,
            prompt,
            product,
            feature_str,
            status,
            matched_issue,
            matched_solution,
            page_url,
            keyword,
            full_solution_to_log,
            token_count or "N/A",
            token_cost or "N/A"
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


def generate_gpt_solution(message):
    unsupported_terms = [
        "fax triage", "fax management", "referral processing", "document routing",
        "inbound fax", "ai scribe", "clinical scribe", "note transcription",
        "dictation", "charting assistant", "clinical documentation",
        "workflow automation", "internal task routing"
    ]

    if any(term in message.lower() for term in unsupported_terms):
        return {
            "product": "No Cliniconex Solution",
            "feature": [],
            "how_it_works": "Cliniconex does not currently offer a solution for this issue. The described challenge falls outside the scope of the Automated Care Platform (ACP).",
            "benefits": ["Not applicable"],
            "roi": "Not applicable",
            "disclaimer": "Not applicable",
            "full_solution": "No solution generated due to unsupported request."
        }

    tags = tag_input(message)
    special_instructions = generate_dynamic_instructions(tags)
    gpt_prompt = f"""
    You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.

    Cliniconex offers **Automated Care Platform (ACP)** — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:

    **Automated Care Messaging (ACM):**

    **ACM Messenger** delivers automated, personalized outreach across voice, text, and email—driven by EMR data. Designed to send timely reminders, instructions, and care updates, ACM Messenger uses dynamic content and configurable workflows to ensure the right information reaches the right person at the right time.

    **ACM Vault** provides secure, encrypted communication for sensitive health information—fully integrated with ACM Messenger. ACM Vault enables healthcare providers to send encrypted messages and documents via **email only**, ensuring HIPAA, PHIPA, and PIPEDA compliance. It is purpose-built to protect patient privacy, reduce risk, and support audit readiness while automating secure communication workflows.

    **ACM Alerts** – Real-time, automated notifications for urgent or time-sensitive updates—delivered via voice, text, or email. ACM Alerts empowers healthcare providers to reach patients, families, and staff instantly with critical messages such as closures, emergencies, or last-minute changes. Fully configurable and EMR-integrated, it ensures rapid, targeted outreach when every second counts.

    **ACM Concierge** – Real-time wait time displays and virtual queuing that keep patients informed and engaged. ACM Concierge integrates with your EMR to publish accurate queue updates on websites, in-clinic screens, or via text. Patients can opt in for return-time notifications, improving satisfaction, reducing front-desk interruptions, and creating a calmer, more efficient waiting experience.

    **Automated Care Scheduling (ACS):**

    **ACS Booking** – Lets patients book their own appointments online, anytime. Integrated with your EMR, it keeps schedules up to date, reduces no-shows, and saves staff time by cutting down on phone calls and manual entry. Simple for patients, easier for your team.

    **ACS Forms** – Digital forms that collect patient information before the appointment. Fully integrated with your EMR, ACS Forms replaces paper intake with customizable forms patients can complete online. Save time, reduce errors, and make check-ins easier for everyone.

    **ACS Surveys** – Automatically sends surveys to patients after visits or key events. Collects feedback, tracks trends, and helps you understand where to improve. Easy to set up, fully integrated with your EMR, and built to support better care through real insights.

    🛑 IMPORTANT: Do not use definite articles (e.g., “the”) in front of product or feature names.
        ✅ Always refer to product and feature names exactly as listed: 
        - Automated Care Messaging, Automated Care Scheduling
        - ACM Messenger, ACM Vault, ACM Alerts, ACM Concierge
        - ACS Booking, ACS Forms, ACS Surveys
        ❌ Do NOT say: “the ACM Messenger,” “the ACS Forms,” etc.

    🧩 Product Attribution Rule:
    - Assign "Automated Care Messaging" if all selected features are from ACM modules.
    - Assign "Automated Care Scheduling" if all selected features are from ACS modules.
    - Assign both ("Automated Care Messaging, Automated Care Scheduling") if features are drawn from both categories.
    - Never assign a product unless one of its features is used.

    Here is a real-world issue described by a healthcare provider:
    "{message}"

Special Instructions:
{special_instructions}

Your response must include:
1. product
2. feature
3. how_it_works (1 paragraph)
4. benefits (2-3 concise bullet points)
5. roi (quantified, realistic)
6. disclaimer (standardized)

Your job is to:

1. **Determine the best product(s)**: Choose between Automated Care Messaging, Automated Care Scheduling, or both.
2. **Select features** from the list below that best solve the issue. Include all relevant features but avoid unnecessary ones.
3. **Explain how the solution works** in one clear paragraph—connect the feature to the provider's challenge and show how it fits in ACP.
4. **List 2–3 operational benefits** tailored to the problem. Avoid repeating phrases from other solutions.
5. **Estimate ROI** tailored to the input:
- Focus on quantifiable gains: fewer calls, reduced no-shows, saved staff hours, increased patient throughput.
- Anchor estimates to the specific issue described.
- Keep numbers conservative and realistic (e.g., 10–25% efficiency gains).
- Vary the format to avoid repetition. Use hours/year, % improvement, $ saved, or reduced manual workload.

🛑 IMPORTANT: Do not use definite articles (“the”) before feature or product names.

🧩 Product Attribution Rule:
- Use "Automated Care Messaging" if all features are from ACM modules.
- Use "Automated Care Scheduling" if all features are from ACS modules.
- Use both if applicable.

Respond ONLY in this exact JSON format:

{{
"product": "Automated Care Messaging",
"feature": ["ACM Alerts", "ACS Forms"],
"how_it_works": "One paragraph tailored to the problem.",
"benefits": [
"Tailored benefit based on input.",
"Another tailored operational gain.",
"Optional third, if useful."
],
"roi": "Anchored to the specific challenge, e.g., Saves 250 hours/year by reducing phone calls for patient instructions.",
"disclaimer": "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
}}

    Do not include anything outside the JSON block.
    Focus on solving the issue. Be specific. Avoid generic or repeated phrases. Use real-world healthcare workflow language.
    """
    input_token_count = count_tokens(gpt_prompt)
    print(f"\U0001f522 Token count for GPT prompt: {input_token_count}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": gpt_prompt}],
            temperature=0.3
        )
        raw_output = response['choices'][0]['message']['content']
        parsed = extract_json(raw_output)

        if not parsed:
            raise ValueError("Invalid JSON from GPT")

        if "roi" not in parsed:
            parsed["roi"] = "Estimated ROI placeholder."
        if "disclaimer" not in parsed:
            parsed["disclaimer"] = "Standard disclaimer."

        parsed["full_solution"] = raw_output

        output_token_count = count_tokens(raw_output)
        total_token_count = input_token_count + output_token_count
        token_cost_usd = round((total_token_count / 1000) * 0.03, 5)

        parsed["token_count"] = total_token_count
        parsed["token_cost"] = token_cost_usd

        return parsed

    except Exception as e:
        print("❌ GPT fallback error:", str(e))
        return {
            "product": "Automated Care Messaging",
            "feature": ["ACM Messenger"],
            "how_it_works": "Error.",
            "benefits": ["Fallback benefit"],
            "roi": "Fallback ROI",
            "disclaimer": "Standard disclaimer.",
            "token_count": input_token_count,
            "token_cost": round((input_token_count / 1000) * 0.03, 5),
            "full_solution": "Error"
        }

@app.route("/ai", methods=["POST"])
def get_solution():
    print("🔔 🔔🔔 /ai called with payload:", request.get_json())
    try:
        data = request.get_json()
        message = data.get("message", "").lower()
        page_url = data.get("page_url", "")

        matrix_score, matrix_item, keyword = get_best_matrix_match(message)
        gpt_response = generate_gpt_solution(message)
        token_count = gpt_response.pop("token_count", 0)
        token_cost = gpt_response.pop("token_cost", 0)
        product = gpt_response.get("product", "N/A")
        features = gpt_response.get("feature", [])
        feature_str = ', '.join(features) if isinstance(features, list) else features
        how_it_works = gpt_response.get("how_it_works", "N/A")

        full_solution = f"""Recommended Product: {product}\n\n\n        Features: {feature_str}\n\n\n        How it works: {how_it_works}"""

        use_matrix = (
            matrix_score >= 2 and matrix_item and
            gpt_response.get("product", "").lower() in matrix_item.get("product", "").lower()
        )

        if use_matrix:
            status = "matrix"
            matched_issue = matrix_item.get("product", "N/A")
            response = {
                "type": "solution",
                "module": matrix_item.get("product", "N/A"),
                "feature": ", ".join(matrix_item.get("features", [])) or "N/A",
                "solution": matrix_item.get("solution", "N/A"),
                "benefits": matrix_item.get("benefits", "N/A"),
                "keyword": keyword or "N/A"
            }
            log_to_google_sheets(message, page_url, matrix_item.get("product", "N/A"), matrix_item.get("features", []), status, matched_issue, "N/A", keyword, full_solution, token_count, token_cost)
        else:
            status = "fallback"
            matched_issue = "N/A"
            response = {
                "type": "solution",
                "module": gpt_response.get("product", "N/A"),
                "feature": ", ".join(gpt_response.get("feature", [])) or "N/A",
                "solution": gpt_response.get("how_it_works", "N/A"),
                "benefits": "\n".join(gpt_response.get("benefits", [])) or "N/A",
                "roi": gpt_response.get("roi", "N/A"),
                "disclaimer": gpt_response.get("disclaimer", "")
            }
            log_to_google_sheets(message, page_url, gpt_response.get("product", "N/A"), gpt_response.get("feature", []), status, matched_issue, gpt_response.get("product", "N/A"), "N/A", full_solution, token_count, token_cost)

        return jsonify(response)
    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": "An error occurred."}), 500

if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
