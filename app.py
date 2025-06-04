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
- Automated Care Messaging (ACM)
- Automated Care Scheduling (ACS)

The following feature lists are drawn from real-world implementations and represent known, proven capabilities. These are **examples, not limitations** — Cliniconex modules are highly configurable and support a wide range of operational, clinical, and compliance needs.

---

### 🔄 General Matching Rule
If an issue doesn’t exactly match a predefined use case but shares **intent, category, or operational context**, treat it as a valid match. Apply the most functionally appropriate module(s), even if the scenario is not explicitly listed.

---

### 🔐 Mandatory Feature Mapping
If a scenario involves urgent, safety-critical communication (e.g., drills, evacuations, lockdowns, outbreaks, severe weather alerts, compliance broadcasts, staffing emergencies):
- ✅ Assign **ACM Alerts**.
- ❌ Do **not** recommend ACM Messenger, Vault, or Concierge unless PHI, encryption, or individual scheduling is involved.

These events require:
- Real-time distribution
- Broad audience targeting
- Compliance traceability
- Operational continuity

---

### 🔁 Clarification: “Unprepared Patients”
If patients are arriving without completing forms, consents, medical histories, or required documents:
- ✅ Assign **ACS Forms**.
- ❌ Do **not** default to ACM Messenger or ACS Booking.

---

### 🔹 ACM Modules
**ACM Messenger** — Proactive communication: reminders, policy updates, event invites
**ACM Alerts** — Safety + compliance broadcasts: fire drills, lockdowns, emergencies
**ACM Vault** — Secure PHI delivery: encrypted messages, consent forms, family updates
**ACM Concierge** — Real-time wait management: queue transparency, bilingual display

---

### 🔹 ACS Modules
**ACS Booking** — Patient-led scheduling: sync calendars, reschedule, triage
**ACS Forms** — Digital intake & consents: auto-routing, EMR integration
**ACS Surveys** — Feedback & compliance tracking: NPS, recovery, morale audits

---

### ✅ Response Requirements
1. Select ACP category: ACM, ACS, or both
2. List all applicable feature modules
3. Explain how they solve the issue (use real healthcare language)
4. List 2–3 operational benefits
5. Include ROI (format: Reduces [issue] by X%, saves Y hours or $Z)
6. End with this disclaimer:
   > Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors.

---

### 💾 Return This JSON Format Only:
```json
{
  "product": "Automated Care Messaging",
  "feature": ["ACM Messenger", "ACS Booking"],
  "how_it_works": "One paragraph connecting the solution to the issue, using real-world healthcare workflows.",
  "benefits": [
    "Reduces administrative workload by automating appointment reminders.",
    "Improves patient satisfaction and care by reducing missed appointments.",
    "Optimizes resource allocation by reducing no-shows and prompt rescheduling."
  ],
  "roi": "Reduces no-show rates by 20%, increasing clinic revenue by an estimated $50,000/year.",
  "Note": "The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
}
```
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
        use_matrix = False

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
