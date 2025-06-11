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

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://cliniconex.com"}})

openai.api_key = os.getenv("OPENAI_API_KEY")
PORT = int(os.getenv("PORT", 10000))
SHEET_ID = "1jL-iyQiVcttmEMfy7j8DA-cyMM-5bcj1TLHLrb4Iwsg"
SERVICE_ACCOUNT_FILE = "service_account.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet = build("sheets", "v4", credentials=credentials).spreadsheets()

def count_tokens(text, model="gpt-4"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'{.*}', text, re.DOTALL)
        return json.loads(match.group(0)) if match else None

def log_to_google_sheets(prompt, page_url, product, module, status, matched_issue, matched_solution, full_solution=None, token_count=None, token_cost=None):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        module_str = ', '.join(module) if isinstance(module, list) else module
        formatted_solution = f"Recommended Product: {product}\n\nModules: {module_str}\n\nHow it works: {matched_solution}"


        values = [[
            timestamp, prompt, product, module_str, status,
            matched_issue, matched_solution, page_url,
            "N/A", formatted_solution,
            token_count or "N/A", token_cost or "N/A"
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
            "module": [],
            "how_it_works": "Cliniconex does not currently offer a solution for this issue. The described challenge falls outside the scope of the Automated Care Platform (ACP).",
            "benefits": ["Not applicable"],
            "roi": "Not applicable",
            "disclaimer": "Not applicable",
            "full_solution": "No solution generated due to unsupported request."
        }

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
        ✅ Always refer to product and module names exactly as listed: 
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
Here is a refined version of your special instructions to embed in the system prompt:

### 🧠 Special Instructions for Accurate Feature Selection and Solution Formation:

1. **ACM Vault Usage Rule**  
   - ACM Vault is **not a standalone messaging tool**.  
   - It is a **secure extension of ACM Messenger** used for encrypted communications via email.  
   - **Always include ACM Messenger** when recommending ACM Vault. Never present Vault in isolation.

2. **Handling No-Shows or Missed Appointments**  
   - If the input refers to “no shows,” “missed appointments,” or “missed visits,” recommend **ACM Alerts** for same-day, real-time reminders.  
   - Recommend **ACM Messenger** only when the issue involves **routine appointment reminders** sent **days in advance**.

3. **Family Portals and Login Requests**  
   - Cliniconex **does not offer a dedicated login portal** for families.  
   - Instead, emphasize that **ACM Messenger** and **ACM Vault** provide **secure, automated updates** to family members via voice, text, or email—without requiring logins or portals.

4. **High Manual Workload or Need for Automation**  
   - If the input involves operational inefficiencies, communication bottlenecks, or staff burden from repetitive tasks (e.g., calling patients), prioritize **ACM Alerts**.  
   - Use **ACM Messenger** only for predictable, advance-scheduled outreach.

5. **Message Creation, Optimization, or Staff Support with Communication**  
   - Recommend the **AI Message Assistant** only when the task involves **creating or refining** healthcare messages.  
   - Clearly state it is a feature within **ACM Messenger**, helping staff write effective messages quickly.  
   - Do not force AI into solutions unless explicitly relevant.

6. **Patient Confusion or Unpreparedness Before Appointments**  
   - If the issue is patients arriving unprepared or confused:  
     - Recommend **ACS Forms** for collecting information beforehand.  
     - Recommend **ACM Alerts** for just-in-time, real-time instructions close to the appointment.  
     - Use **ACM Messenger** only for well-in-advance scheduled communication.

7. **EMR/EHR Integration and Workflow Compatibility**  
   - Cliniconex integrates **directly with major EMR/EHR systems** to enable real-time, automated communication.  
   - Highlight **zero-disruption implementation** and **no need for middleware or portals**.  
   - Emphasize that communications are **driven by live clinical data**—not manual input.

8. **Clarifying ACM Alerts Use Cases**  
   - ACM Alerts is for **event-triggered, dynamic messaging**—ideal for same-day updates, urgent changes, or appointment confirmations.  
   - Use it for:
     - Last-minute changes (e.g., provider cancellations, new availability)
     - Timely reminders (e.g., “arrive 15 min early,” “don’t forget fasting”)
     - Waitlist offers or urgent campaigns  
   - Do **not** recommend ACM Alerts for:
     - Routine reminders sent days in advance
     - Static workflows (use ACM Messenger instead)


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
    print(f"🔢 Token count for GPT prompt: {input_token_count}")

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
        parsed["module"] = parsed.pop("feature", [])

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
            "module": ["ACM Messenger"],
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

        gpt_response = generate_gpt_solution(message)
        token_count = gpt_response.pop("token_count", 0)
        token_cost = gpt_response.pop("token_cost", 0)

        product = gpt_response.get("product", "N/A")
        modules = gpt_response.get("module", [])
        module_str = ', '.join(modules) if isinstance(modules, list) else modules
        how_it_works = gpt_response.get("how_it_works", "N/A")

        full_solution = f"Recommended Product: {product}\n\nModules: {module_str}\n\nHow it works: {how_it_works}"

        response = {
            "type": "solution",
            "product": product,
            "module": module_str or "N/A",
            "solution": how_it_works or "N/A",
            "benefits": "\n".join(gpt_response.get("benefits", [])) or "N/A",
            "roi": gpt_response.get("roi", "N/A"),
            "disclaimer": gpt_response.get("disclaimer", "")
        }

        log_to_google_sheets(message, page_url, product, modules, "gpt", product, how_it_works, full_solution, token_count, token_cost)
        return jsonify(response)

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": "An error occurred."}), 500

if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
