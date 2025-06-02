
import json
import openai
import re
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

openai.api_key = "YOUR_API_KEY"

def generate_gpt_solution(message):
    gpt_prompt = f"""You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings.

Cliniconex offers the **Automated Care Platform (ACP)** — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:

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
2. Select **one or more features** from the list above.
3. Write **one concise paragraph** explaining how the selected product(s) and feature(s) solve the issue.
4. Provide a list of **2–3 specific operational benefits**.

Respond ONLY in this exact JSON format:

{{{{
  "product": "Automated Care Messaging",
  "feature": "ACM Messenger – Sends personalized messages via voice, SMS, or email. | ACM Alerts – Notifies staff only when human follow-up is needed.",
  "how_it_works": "One paragraph that connects the solution to the problem and explains how the feature fits into the broader ACP.",
  "benefits": [
    "Reduces staff workload by eliminating manual communications.",
    "Improves patient satisfaction with timely and transparent updates.",
    "Integrates directly with your EMR for seamless automation."
  ]
}}}}

Do not include anything outside the JSON block.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": gpt_prompt}],
            temperature=0.7
        )
        result_text = response['choices'][0]['message']['content']

        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            match = re.search(r'\{\s*\"product\"[\s\S]*?\}', result_text)
            if match:
                return json.loads(match.group(0))
            else:
                print("❌ Regex fallback failed to extract JSON.")
                return None
    except Exception as e:
        print("❌ GPT fallback error:", e)
        return None
