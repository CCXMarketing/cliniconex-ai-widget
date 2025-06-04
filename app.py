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

    You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. Your task is to confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.
    
    Cliniconex offers the Automated Care Platform (ACP) — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:
    
    Automated Care Messaging (ACM)
    
   The following feature lists are drawn from real-world implementations and represent known, proven capabilities. These are examples, not limitations — Cliniconex modules are highly configurable and support a wide range of operational, clinical, and compliance needs.

Default Behavior: If an issue doesn’t exactly match a predefined use case but shares intent, category, or operational context with a listed capability, treat it as a valid match. Use your understanding of healthcare workflows to apply the most suitable module — even if the scenario isn’t explicitly listed.

🔒 Exceptions – Mandatory Feature Mapping:

If a scenario involves urgent, safety-critical communication — including drills, evacuations, lockdowns, outbreaks, severe weather alerts, compliance broadcasts, or staffing emergencies — you must classify the solution as **ACM Alerts**.

These scenarios require:
- Real-time distribution
- Broad audience targeting
- Compliance traceability
- Operational continuity

📛 Do not recommend ACM Messenger, Vault, or Concierge for these situations unless PHI, encrypted documents, or individual scheduling is directly involved.

These modules are tied to safety, security, and compliance scenarios that demand precision. Do not generalize these to other features like ACM Messenger or ACM Concierge.

    Automated Care Messaging (ACM)
    
    ACM Messenger
    Used for proactive, personalized, and mass outreach via SMS, email, or voice:
    - ACM Messenger is used to alert patients of a same-day clinic closure.
    - ACM Messenger is used to notify families of an emergency lockdown.
    - ACM Messenger is used to deliver unexpected staff absence alerts.
    - ACM Messenger is used to distribute HIPAA/PIPEDA consent forms.
    - ACM Messenger is used to send documentation reminders for audits.
    - ACM Messenger is used to confirm emergency contact updates.
    - ACM Messenger is used to thank families for positive feedback.
    - ACM Messenger is used to invite families to open houses or tours.
    - ACM Messenger is used to notify of appointment reschedules or delays.
    - ACM Messenger is used to distribute intake forms before visits.
    - ACM Messenger is used to update on therapy session changes.
    - ACM Messenger is used to alert about lab result availability.
    - ACM Messenger is used to notify of telehealth disruptions.
    - ACM Messenger is used to deliver preventative care reminders.
    - ACM Messenger is used to share seasonal wellness guides.
    - ACM Messenger is used to promote vaccination clinics.
    - ACM Messenger is used to support virtual group education sessions.
    - ACM Messenger is used to issue urgent policy compliance updates.
    - ACM Messenger is used to deliver custom thank-you messages.
    - ACM Messenger is used to confirm transportation arrangements.
    
    ACM Alerts
    Used to initiate real-time alerts or compliance broadcasts:
    - ACM Alerts is used to notify of a fire alarm or drill.
    - ACM Alerts is used to send lockdown or active shooter alerts.
    - ACM Alerts is used to announce a COVID-19 outbreak.
    - ACM Alerts is used to share hazardous material exposure alerts.
    - ACM Alerts is used to inform about generator failure or HVAC disruption.
    - ACM Alerts is used to request shift coverage or swaps.
    - ACM Alerts is used to send inspection summary alerts.
    - ACM Alerts is used to distribute medication or dietary compliance updates.
    - ACM Alerts is used to communicate flooding in facility areas.
    - ACM Alerts is used to warn of severe weather or issue boil water advisories.
    - ACM Alerts is used to activate evacuation instructions.
    - ACM Alerts is used to schedule infection control training.
    - ACM Alerts is used to prompt staff for chart audits.
    - ACM Alerts is used to send HIPAA billing rights reminders.
    - ACM Alerts is used to onboard patients with health kits.
    - ACM Alerts is used to communicate visitation restrictions.
    - ACM Alerts is used to share new directives from health authorities.
    - ACM Alerts is used to send wellness seminar invites.
    - ACM Alerts is used to distribute family satisfaction survey results.
    - ACM Alerts is used to promote flu shot clinics and COVID-19 boosters.
    
    ACM Vault
    Used for secure, compliant, and encrypted messaging:
    - ACM Vault is used to send encrypted patient messages securely.
    - ACM Vault is used to deliver incident reports to family members.
    - ACM Vault is used to distribute signed consent forms securely.
    - ACM Vault is used to share PHI without breaching compliance.
    - ACM Vault is used to log communications for audit trails.
    - ACM Vault is used to transmit care updates post-discharge.
    - ACM Vault is used to respond to family questions with attachments.
    - ACM Vault is used to securely share end-of-life care plans.
    - ACM Vault is used to forward medication change notifications.
    - ACM Vault is used to protect patient dignity during behavioral updates.
    
    ACM Concierge
    Used for real-time wait time display and patient queue transparency:
    - ACM Concierge is used to display real-time wait estimates for walk-ins.
    - ACM Concierge is used to update queues dynamically during high traffic.
    - ACM Concierge is used to show anonymized patient positions.
    - ACM Concierge is used to notify patients when they are near the top of the queue.
    - ACM Concierge is used to automate leave-and-return messaging.
    - ACM Concierge is used to reduce front-desk interruptions.
    - ACM Concierge is used to allow families to wait off-site.
    - ACM Concierge is used to reduce no-shows via return prompts.
    - ACM Concierge is used to improve perceived wait fairness.
    - ACM Concierge is used to display estimated wait times in bilingual formats.
    
    Automated Care Scheduling (ACS)
    Same as above: These use cases reflect known capabilities but are not exhaustive. Apply functional reasoning to align features even if the use case is not verbatim.
      
    ACS Booking
    Used for self-service appointment scheduling:
    - ACS Booking is used to allow patients to schedule appointments 24/7.
    - ACS Booking is used to sync availability in real time with provider calendars.
    - ACS Booking is used to reduce no-shows via automated confirmations.
    - ACS Booking is used to promote flu shot campaigns or seasonal events.
    - ACS Booking is used to drive attendance via links in email or social media.
    - ACS Booking is used to balance load between multiple providers.
    - ACS Booking is used to handle urgent care bookings efficiently.
    - ACS Booking is used to triage patients into the right services.
    - ACS Booking is used to accommodate recurring or long-term visits.
    - ACS Booking is used to advertise last-minute openings in real time.
    
    ACS Forms
    Used to collect digital forms pre-visit:
    - ACS Forms is used to gather patient demographics before arrival.
    - ACS Forms is used to automate intake forms for new patients.
    - ACS Forms is used to collect consent for treatment electronically.
    - ACS Forms is used to route completed forms directly to departments.
    - ACS Forms is used to replace paper intake processes.
    - ACS Forms is used to pre-fill forms with EMR-linked patient data.
    - ACS Forms is used to collect medical history and risk assessments.
    - ACS Forms is used to notify staff of incomplete forms before check-in.
    - ACS Forms is used to streamline pre-visit triage.
    - ACS Forms is used to digitally capture secure signatures.
    
    ACS Surveys
    Used for post-visit or ongoing feedback:
    - ACS Surveys is used to measure patient satisfaction after appointments.
    - ACS Surveys is used to assess front desk or provider interactions.
    - ACS Surveys is used to benchmark Net Promoter Scores (NPS).
    - ACS Surveys is used to monitor recovery after procedures.
    - ACS Surveys is used to track feedback across multiple clinic sites.
    - ACS Surveys is used to gather family caregiver engagement insights.
    - ACS Surveys is used to identify service recovery opportunities.
    - ACS Surveys is used to validate chronic care outcomes.
    - ACS Surveys is used to audit compliance and patient experience.
    - ACS Surveys is used to assess staff morale and operational effectiveness.
    
    For each issue presented:
    1. Identify if the issue aligns with Automated Care Messaging, Automated Care Scheduling, or both.
    2. Select the most relevant module(s) (e.g., ACM Alerts, ACS Forms) and list all that apply.
    3. Explain in a short paragraph how the selected module(s) solve the issue using language from the Cliniconex brand book.
    4. List 2–3 operational benefits, clearly stated and value-driven.
    5. Add an ROI calculation, using the following format:
       - ROI: Reduces [issue] by X%, increasing clinic revenue by an estimated $Y/year or saving Z hours/year in staff time.
    6. Include this disclaimer at the end:
       - Disclaimer: "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
    
    
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
          "roi": "Reduces no-show rates by 20%, increasing clinic revenue by an estimated $50,000/year due to more patients attending follow-ups.",
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
            matrix_score >= 3 and matrix_item and
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
                "benefits": "\n".join(gpt_response.get("benefits", [])) or "N/A",
                "roi": gpt_response.get("roi", "N/A"),
                "disclaimer": gpt_response.get("disclaimer", "N/A")
            }
            log_to_google_sheets(message, page_url, gpt_response.get("product", "N/A"), gpt_response.get("feature", []), status, matched_issue, gpt_response.get("product", "N/A"), "N/A")

        return jsonify(response)
    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": "An error occurred."}), 500


# ✅ Start app for Render
if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
