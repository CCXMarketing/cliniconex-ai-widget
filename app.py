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
from rapidfuzz import fuzz
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

def fuzzy_score(message, item):
    return max(fuzz.partial_ratio(message, k.lower()) for k in item.get("keywords", []))

def get_best_matrix_match(message):
    best_score, best_item, best_keyword = 0, None, None
    for item in solution_matrix:
        score = score_keywords(message, item)
        fuzzy = fuzzy_score(message, item)
        final_score = score + (1 if fuzzy > 85 else 0)  # add 1 if a fuzzy match is strong
        if final_score > best_score:
            best_score = final_score
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

def log_to_google_sheets(prompt, page_url, product, feature, status, matched_issue, matched_solution, keyword, full_solution=""):
    try:
        timestamp = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M:%S")
        feature_str = ', '.join(feature) if isinstance(feature, list) else feature

        values = [[
            timestamp,               # Timestamp
            prompt,                  # Prompt
            product,                 # Product
            feature_str,             # Feature
            status,                  # Status
            matched_issue,           # Matched Issue
            matched_solution,        # Matched Solution
            page_url,                # Page URL
            keyword,                 # Keyword
            full_solution            # Full Solution
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
    gpt_prompt = f"""
PROMPT = """
You are a Cliniconex solutions expert with deep expertise in the company’s full suite of products and features. You can confidently assess any healthcare-related issue and determine the most effective solution—whether it involves a single product or a combination of offerings. You understand how each feature functions within the broader Automated Care Platform (ACP) and are skilled at tailoring precise recommendations to address real-world clinical, operational, and administrative challenges.

Cliniconex offers the Automated Care Platform (ACP) — a complete system for communication, coordination, and care automation. ACP is composed of two core solutions:

Automated Care Messaging (ACM)

ACM Messenger  
Delivers personalized, EMR-integrated messages using voice, SMS, or email.  
Use Cases include:
✅ 1. Urgent Communications / Emergency Notifications
ACM Messenger is used to alert patients of a same-day clinic closure.
ACM Messenger is used to inform staff of an urgent meeting.
ACM Messenger is used to notify families of an emergency lockdown.
ACM Messenger is used to deliver real-time weather-related closures.
ACM Messenger is used to send mass evacuation instructions.
ACM Messenger is used to escalate IT or EMR outages to staff.
ACM Messenger is used to deliver unexpected staff absence alerts.
ACM Messenger is used to cancel same-day group activities.
ACM Messenger is used to inform patients of facility power issues.
ACM Messenger is used to alert caregivers about urgent clinical changes.
ACM Messenger is used to provide real-time infection control updates.
ACM Messenger is used to notify of transportation disruptions.
ACM Messenger is used to inform about telehealth connection issues.
ACM Messenger is used to issue urgent policy compliance updates.
ACM Messenger is used to instruct families during rapid care plan changes.
ACM Messenger is used to send building access restriction updates.
ACM Messenger is used to alert about hazardous spills or safety risks.
ACM Messenger is used to confirm emergency contact updates.
ACM Messenger is used to cascade critical staffing updates.
ACM Messenger is used to send building maintenance shutdown notices.

✅ 2. Regulatory & Compliance Messaging
ACM Messenger is used to distribute HIPAA/PIPEDA consent forms.
ACM Messenger is used to confirm emergency contact accuracy.
ACM Messenger is used to notify families of changes in resident rights.
ACM Messenger is used to send documentation reminders for audits.
ACM Messenger is used to announce policy and procedure updates.
ACM Messenger is used to distribute medication policy updates.
ACM Messenger is used to deliver compliance-related announcements.
ACM Messenger is used to send reminders about annual privacy training.
ACM Messenger is used to share emergency preparedness plans.
ACM Messenger is used to issue reminders for safety inspections.
ACM Messenger is used to communicate changes in admission protocols.
ACM Messenger is used to distribute codes of conduct or ethics.
ACM Messenger is used to track acknowledgment of regulatory changes.
ACM Messenger is used to confirm training participation.
ACM Messenger is used to alert when documentation is overdue.
ACM Messenger is used to deliver flu shot declination forms.
ACM Messenger is used to share regulatory deadline notices.
ACM Messenger is used to document communication compliance.
ACM Messenger is used to deliver state-specific care notifications.
ACM Messenger is used to coordinate compliance audit prep.

✅ 3. Reputation & Community Management
ACM Messenger is used to thank families for positive feedback.
ACM Messenger is used to share patient success stories.
ACM Messenger is used to notify families of resident milestones.
ACM Messenger is used to distribute family newsletters.
ACM Messenger is used to invite families to participate in surveys.
ACM Messenger is used to highlight community involvement initiatives.
ACM Messenger is used to request online reviews and testimonials.
ACM Messenger is used to invite media to facility events.
ACM Messenger is used to communicate brand updates.
ACM Messenger is used to send personalized holiday greetings.
ACM Messenger is used to issue congratulations for referrals.
ACM Messenger is used to announce new services or amenities.
ACM Messenger is used to showcase staff spotlights or recognition.
ACM Messenger is used to invite families to open houses or tours.
ACM Messenger is used to share resident social activity highlights.
ACM Messenger is used to inform families of changes to family council.
ACM Messenger is used to highlight facility improvements.
ACM Messenger is used to promote community partnerships.
ACM Messenger is used to deliver custom thank-you messages.
ACM Messenger is used to confirm engagement with community events.

✅ 4. Operational Efficiencies
ACM Messenger is used to confirm appointment bookings.
ACM Messenger is used to notify of schedule changes.
ACM Messenger is used to send no-show or cancellation alerts.
ACM Messenger is used to update families on appointment delays.
ACM Messenger is used to confirm transportation arrangements.
ACM Messenger is used to distribute forms digitally before visits.
ACM Messenger is used to update on medication pickups or refills.
ACM Messenger is used to notify of provider unavailability.
ACM Messenger is used to alert about lab result availability.
ACM Messenger is used to coordinate internal shift swaps.
ACM Messenger is used to distribute updated activity calendars.
ACM Messenger is used to notify of billing due dates or errors.
ACM Messenger is used to confirm service requests (e.g., housekeeping).
ACM Messenger is used to send out reminders for family conferences.
ACM Messenger is used to broadcast open clinic slots.
ACM Messenger is used to collect intake information pre-visit.
ACM Messenger is used to notify of therapy rescheduling.
ACM Messenger is used to send reminders for document signatures.
ACM Messenger is used to request missing patient data.
ACM Messenger is used to streamline interdepartmental coordination.

✅ 5. Health Education & Preventative Care
ACM Messenger is used to deliver personalized health tips.
ACM Messenger is used to send preventative care reminders.
ACM Messenger is used to distribute seasonal wellness guides.
ACM Messenger is used to share health articles or videos.
ACM Messenger is used to promote vaccination clinics.
ACM Messenger is used to deliver chronic disease management info.
ACM Messenger is used to share mental health resources.
ACM Messenger is used to promote physical activity sessions.
ACM Messenger is used to alert about nutrition classes.
ACM Messenger is used to share smoking cessation programs.
ACM Messenger is used to notify of wellness events or fairs.
ACM Messenger is used to distribute medication adherence tools.
ACM Messenger is used to remind about hydration best practices.
ACM Messenger is used to deliver senior safety tips.
ACM Messenger is used to share educational resources for caregivers.
ACM Messenger is used to promote fall prevention content.
ACM Messenger is used to explain home care post-discharge.
ACM Messenger is used to distribute FAQs on new diagnoses.
ACM Messenger is used to support virtual group education sessions.
ACM Messenger is used to highlight preventative screenings.

ACM Vault

✅ 1. Secure Communication & Data Protection (20 use cases)
ACM Vault is used to send encrypted patient messages securely.
ACM Vault is used to share sensitive documents with families.
ACM Vault is used to ensure HIPAA, PIPEDA, and PHIPA compliance in outreach.
ACM Vault is used to avoid unsecured email or manual document handovers.
ACM Vault is used to protect medical records from unauthorized access.
ACM Vault is used to prevent data breaches during outbound communications.
ACM Vault is used to comply with regional and national privacy laws.
ACM Vault is used to share care plans securely with authorized recipients.
ACM Vault is used to store a traceable log of shared sensitive information.
ACM Vault is used to eliminate paper-based processes for privacy-sensitive updates.
ACM Vault is used to distribute test results securely to families or caregivers.
ACM Vault is used to centralize encrypted communication history for audit purposes.
ACM Vault is used to safeguard patient photos or assessments sent to families.
ACM Vault is used to share billing or insurance documents securely.
ACM Vault is used to prevent exposure of contact or health information in group messages.
ACM Vault is used to provide a compliant alternative to consumer messaging apps.
ACM Vault is used to support defensible documentation in case of regulatory review.
ACM Vault is used to protect personally identifiable information (PII) during events or incidents.
ACM Vault is used to control document expiration and access limits.
ACM Vault is used to ensure security without burdening frontline staff.

✅ 2. Clinical & Administrative Collaboration (20 use cases)
ACM Vault is used to coordinate care across clinical teams securely.
ACM Vault is used to distribute discharge instructions confidentially.
ACM Vault is used to share post-appointment care summaries.
ACM Vault is used to transmit signed consent forms securely.
ACM Vault is used to forward medication change notices to authorized parties.
ACM Vault is used to issue secure staff-to-staff messaging around patient care.
ACM Vault is used to communicate internal clinical alerts without risking breaches.
ACM Vault is used to simplify multidisciplinary care plan sharing.
ACM Vault is used to securely submit patient forms to admin or medical teams.
ACM Vault is used to enable inter-departmental communication that protects PHI.
ACM Vault is used to notify families of changes to living arrangements or care levels.
ACM Vault is used to send follow-ups related to regulatory or clinical compliance.
ACM Vault is used to deliver important documentation during care transitions.
ACM Vault is used to document internal reviews with secure timestamps.
ACM Vault is used to transmit secure intake assessments to necessary staff.
ACM Vault is used to alert on infection status or quarantine needs.
ACM Vault is used to reduce the time spent manually handling confidential communications.
ACM Vault is used to track and verify communication access.
ACM Vault is used to reduce reliance on in-person handoffs or internal mail.
ACM Vault is used to automatically sync secure messages with EMR systems when integrated.

✅ 3. Family & Caregiver Engagement (20 use cases)
ACM Vault is used to send incident reports to family members securely.
ACM Vault is used to keep family caregivers informed while protecting patient dignity.
ACM Vault is used to update families on a resident’s health status privately.
ACM Vault is used to send mental health or behavioral updates discreetly.
ACM Vault is used to respond to family questions with secure file attachments.
ACM Vault is used to issue care updates during hospital-to-facility transitions.
ACM Vault is used to deliver scheduled weekly health snapshots.
ACM Vault is used to securely share advance care planning documentation.
ACM Vault is used to simplify end-of-life planning communications.
ACM Vault is used to inform designated caregivers without breaching confidentiality.
ACM Vault is used to notify about vaccination status or medical procedures.
ACM Vault is used to build trust through secure, transparent communication.
ACM Vault is used to proactively provide documentation for insurance or legal use.
ACM Vault is used to confirm informed consent in advance of procedures.
ACM Vault is used to send therapy updates or evaluations.
ACM Vault is used to support care coordination for residents with multiple caregivers.
ACM Vault is used to keep long-distance families connected without compromising privacy.
ACM Vault is used to streamline secure follow-up after major incidents or hospitalizations.
ACM Vault is used to notify POAs (Power of Attorney) without revealing more than necessary.
ACM Vault is used to deliver secure updates to guardians or court-appointed representatives.

ACM Alerts

✅ 1. Urgent Communications / Emergency Notifications
ACM Alerts is used to notify of a fire alarm or drill.
ACM Alerts is used to announce a COVID-19 outbreak.
ACM Alerts is used to send active shooter or lockdown alerts.
ACM Alerts is used to distribute boil water advisories.
ACM Alerts is used to alert of power outages affecting patient rooms.
ACM Alerts is used to inform about generator testing or failure.
ACM Alerts is used to issue a missing resident alert (Code Silver).
ACM Alerts is used to notify staff of HVAC system failures.
ACM Alerts is used to reroute emergency transport access.
ACM Alerts is used to communicate flooding in specific facility areas.
ACM Alerts is used to initiate evacuation instructions.
ACM Alerts is used to inform of emergency 911 service disruptions.
ACM Alerts is used to share hazardous material exposure alerts.
ACM Alerts is used to activate quarantine protocols.
ACM Alerts is used to warn of severe winter storms.
ACM Alerts is used to prepare for hurricanes or tornadoes.
ACM Alerts is used to request critical staff coverage.
ACM Alerts is used to notify of a facility security breach.
ACM Alerts is used to update infection prevention protocols.
ACM Alerts is used to communicate visitation restrictions.

✅ 2. Regulatory & Compliance Messaging
ACM Alerts is used to request annual flu vaccine consent.
ACM Alerts is used to share new health directives from authorities.
ACM Alerts is used to communicate inspection summaries.
ACM Alerts is used to update infection control measures.
ACM Alerts is used to notify families of policy changes.
ACM Alerts is used to promote mandated satisfaction surveys.
ACM Alerts is used to send fire safety compliance reminders.
ACM Alerts is used to distribute monthly medication updates.
ACM Alerts is used to share resident rights and privacy policies.
ACM Alerts is used to provide emergency preparedness plans.
ACM Alerts is used to remind of HIPAA billing rights.
ACM Alerts is used to automate compliance documentation requests.
ACM Alerts is used to schedule regulatory communication.
ACM Alerts is used to issue data privacy policy updates.
ACM Alerts is used to confirm audit trail communications.
ACM Alerts is used to follow up on admission documentation.
ACM Alerts is used to share infection count summaries.
ACM Alerts is used to send quarterly compliance updates.
ACM Alerts is used to communicate dietary compliance changes.
ACM Alerts is used to request health insurance form completion.

✅ 3. Reputation & Community Management
ACM Alerts is used to share facility awards or certifications.
ACM Alerts is used to distribute family satisfaction survey results.
ACM Alerts is used to spotlight and thank staff members.
ACM Alerts is used to celebrate resident milestones.
ACM Alerts is used to share community involvement news.
ACM Alerts is used to invite families to council meetings.
ACM Alerts is used to release monthly newsletters.
ACM Alerts is used to share new facility photos or tours.
ACM Alerts is used to announce renovations or upgrades.
ACM Alerts is used to welcome new clinicians or leadership.
ACM Alerts is used to distribute testimonials or gratitude messages.
ACM Alerts is used to share local media coverage.
ACM Alerts is used to send holiday greetings.
ACM Alerts is used to celebrate staff anniversaries.
ACM Alerts is used to promote open house events.
ACM Alerts is used to coordinate care planning meetings.
ACM Alerts is used to support fundraising event promotions.
ACM Alerts is used to share annual reports or summaries.
ACM Alerts is used to launch new recreational programs.
ACM Alerts is used to highlight public health recognitions.

✅ 4. Operational Efficiencies
ACM Alerts is used to request shift coverage or swaps.
ACM Alerts is used to announce policy updates to staff.
ACM Alerts is used to communicate new procedures.
ACM Alerts is used to notify of breakroom or kitchen closures.
ACM Alerts is used to share digital form availability.
ACM Alerts is used to issue maintenance updates.
ACM Alerts is used to announce scheduled fire drills.
ACM Alerts is used to communicate parking changes.
ACM Alerts is used to remind staff about chart audits.
ACM Alerts is used to alert staff about system downtime.
ACM Alerts is used to send meeting invites or reminders.
ACM Alerts is used to prompt certification renewals.
ACM Alerts is used to notify about supply delivery issues.
ACM Alerts is used to schedule infection control training.
ACM Alerts is used to share laundry service disruptions.
ACM Alerts is used to update staff contact directories.
ACM Alerts is used to inform about benefits enrollment.
ACM Alerts is used to adjust daily meal schedule notices.
ACM Alerts is used to remind about staff flu clinics.
ACM Alerts is used to update staff on policy manual changes.

✅ 5. Health Education & Preventative Care
ACM Alerts is used to remind patients about flu shots.
ACM Alerts is used to share COVID-19 booster availability.
ACM Alerts is used to promote pneumococcal vaccines.
ACM Alerts is used to distribute diabetes awareness resources.
ACM Alerts is used to invite to healthy eating programs.
ACM Alerts is used to notify about blood pressure clinics.
ACM Alerts is used to reinforce medication reconciliation.
ACM Alerts is used to promote fall prevention tips.
ACM Alerts is used to schedule dental hygiene clinics.
ACM Alerts is used to announce wellness seminars.
ACM Alerts is used to share mental health support resources.
ACM Alerts is used to issue sun safety reminders.
ACM Alerts is used to distribute stroke prevention content.
ACM Alerts is used to send breast cancer screening reminders.
ACM Alerts is used to highlight medication safety tips.
ACM Alerts is used to prepare residents for allergy seasons.
ACM Alerts is used to promote smoking cessation programs.
ACM Alerts is used to educate about infection prevention.
ACM Alerts is used to onboard patients with health kits.
ACM Alerts is used to run hydration awareness campaigns.

ACM Concierge

✅ 1. Wait Time Transparency (20 use cases)
ACM Concierge is used to display real-time wait time estimates for walk-in patients.
ACM Concierge is used to reduce patient uncertainty during long wait periods.
ACM Concierge is used to update estimated wait times directly from the EMR.
ACM Concierge is used to eliminate the need for staff to manually communicate delays.
ACM Concierge is used to keep patient expectations realistic.
ACM Concierge is used to reduce perceived wait times through transparency.
ACM Concierge is used to automate front-desk communication.
ACM Concierge is used to publish wait times on clinic websites.
ACM Concierge is used to show last updated timestamps to ensure data relevance.
ACM Concierge is used to promote clinic efficiency and modernity.
ACM Concierge is used to compete with nearby clinics by advertising low wait times.
ACM Concierge is used to discourage patient interruptions at reception.
ACM Concierge is used to show dynamic updates during busy walk-in periods.
ACM Concierge is used to set accurate expectations before patients leave home.
ACM Concierge is used to enhance patient satisfaction with self-serve information.
ACM Concierge is used to build trust through transparent communication.
ACM Concierge is used to reduce aggressive patient behavior related to delays.
ACM Concierge is used to maintain visibility on wait performance.
ACM Concierge is used to give patients an alternative to asking staff directly.
ACM Concierge is used to present information in both English and French time formats.

✅ 2. Queue Display & Flow Management (20 use cases)
ACM Concierge is used to visually display the order of patients in queue.
ACM Concierge is used to reduce repeated “am I next?” inquiries.
ACM Concierge is used to show patient initials or anonymized names on screen.
ACM Concierge is used to clearly indicate who is next in line.
ACM Concierge is used to update the queue in real-time as patients are seen.
ACM Concierge is used to minimize front-desk staff disruptions.
ACM Concierge is used to help patients track their progress in the queue.
ACM Concierge is used to reduce anxiety by showing movement in the queue.
ACM Concierge is used to display the queue on a waiting room monitor.
ACM Concierge is used to eliminate manual status updates for waiting patients.
ACM Concierge is used to enhance the perception of clinic organization.
ACM Concierge is used to automatically trigger alerts when a patient is near the top of the queue.
ACM Concierge is used to streamline patient flow during walk-in clinics.
ACM Concierge is used to align operational processes with patient expectations.
ACM Concierge is used to support a quiet and more efficient front office.
ACM Concierge is used to build patient confidence in clinic communication.
ACM Concierge is used to tailor queue display branding using CSS.
ACM Concierge is used to support multi-lingual display configurations.
ACM Concierge is used to minimize miscommunications about position in line.
ACM Concierge is used to ensure consistency in patient flow management.

✅ 3. Patient Return Messaging (20 use cases)
ACM Concierge is used to allow patients to leave the clinic and receive a return notification.
ACM Concierge is used to help patients manage their time while waiting.
ACM Concierge is used to send automated messages when it’s nearly a patient’s turn.
ACM Concierge is used to reduce in-clinic crowding during high traffic times.
ACM Concierge is used to manage long wait times more empathetically.
ACM Concierge is used to deliver leave/return messages via text, voice, or email.
ACM Concierge is used to notify patients who left when they are approaching the top of the queue.
ACM Concierge is used to offer virtual queueing as an amenity.
ACM Concierge is used to reduce no-show risks by maintaining queue visibility.
ACM Concierge is used to reassure patients that they won’t lose their place.
ACM Concierge is used to customize return notifications based on clinic preferences.
ACM Concierge is used to enhance access for families with young children or mobility challenges.
ACM Concierge is used to enable leave messaging with minimal staff intervention.
ACM Concierge is used to modernize the walk-in experience.
ACM Concierge is used to reduce frustration during extended clinic wait times.
ACM Concierge is used to boost satisfaction in time-sensitive environments.
ACM Concierge is used to improve queue re-entry timing with automated logic.
ACM Concierge is used to manage patient expectations during delays.
ACM Concierge is used to proactively retain walk-in patients who might otherwise leave.
ACM Concierge is used to reduce front desk time spent explaining queue logistics.

Automated Care Scheduling (ACS)

ACS Booking

✅ 1. Patient Self-Scheduling & Access (20 use cases)
ACS Booking is used to allow patients to schedule appointments 24/7.
ACS Booking is used to reduce reliance on phone calls for appointment booking.
ACS Booking is used to empower patients with more control over their care access.
ACS Booking is used to streamline new patient onboarding.
ACS Booking is used to reduce patient wait times by filling scheduling gaps.
ACS Booking is used to increase appointment volume through ease of access.
ACS Booking is used to minimize back-and-forth communication with patients.
ACS Booking is used to ensure booking flexibility across different appointment types.
ACS Booking is used to optimize online bookings based on provider preferences.
ACS Booking is used to encourage early scheduling for preventive visits.
ACS Booking is used to enable appointment requests outside business hours.
ACS Booking is used to improve patient satisfaction through convenience.
ACS Booking is used to reduce front desk workload and call volume.
ACS Booking is used to let patients choose their preferred provider and time slot.
ACS Booking is used to drive return visits through embedded rescheduling features.
ACS Booking is used to guide patients through appointment type selection.
ACS Booking is used to triage patients to the right service automatically.
ACS Booking is used to accommodate urgent or priority care scheduling.
ACS Booking is used to provide a seamless mobile-friendly booking experience.
ACS Booking is used to improve accessibility for patients with disabilities.

✅ 2. Provider & Clinic Workflow Optimization (20 use cases)
ACS Booking is used to align provider schedules with real-time availability.
ACS Booking is used to reduce appointment gaps and improve time utilization.
ACS Booking is used to balance in-person and virtual appointments.
ACS Booking is used to optimize multi-provider clinics or group practices.
ACS Booking is used to configure appointment types per provider or location.
ACS Booking is used to block time for administrative work or breaks.
ACS Booking is used to balance load between high- and low-volume providers.
ACS Booking is used to automate follow-up visit scheduling.
ACS Booking is used to streamline specialist referrals and appointment routing.
ACS Booking is used to track cancellations and rebook instantly.
ACS Booking is used to reduce no-show rates through confirmation logic.
ACS Booking is used to ensure appointments are booked based on set rules.
ACS Booking is used to protect high-demand slots for priority patients.
ACS Booking is used to maintain control over last-minute bookings.
ACS Booking is used to configure default durations by appointment type.
ACS Booking is used to collect custom booking information ahead of visits.
ACS Booking is used to redirect patients when a provider is unavailable.
ACS Booking is used to sync with provider calendars in real-time.
ACS Booking is used to manage walk-ins and bookings on the same platform.
ACS Booking is used to accommodate recurring or long-term patient visits.

✅ 3. Growth, Engagement & Marketing (20 use cases)
ACS Booking is used to boost patient acquisition through online channels.
ACS Booking is used to convert website visitors into booked appointments.
ACS Booking is used to promote seasonal or special clinic events (e.g., flu shots).
ACS Booking is used to offer booking links in marketing emails.
ACS Booking is used to reduce referral leakage by simplifying scheduling.
ACS Booking is used to improve first impression for new patients.
ACS Booking is used to retain patients by offering easy rescheduling options.
ACS Booking is used to enable campaign-specific appointment links.
ACS Booking is used to provide multilingual booking experiences.
ACS Booking is used to collect and segment patient demographics.
ACS Booking is used to advertise last-minute availability in real time.
ACS Booking is used to increase Google Business conversion by linking to booking.
ACS Booking is used to drive attendance to clinics and screening programs.
ACS Booking is used to automatically track which marketing channel led to a booking.
ACS Booking is used to promote new provider availability or clinic expansion.
ACS Booking is used to enable direct booking from social media.
ACS Booking is used to support digital health transformation strategies.
ACS Booking is used to build loyalty by offering patient-centered flexibility.
ACS Booking is used to gain insights into peak demand periods.
ACS Booking is used to enhance brand trust by offering modern access tools.

ACS Forms

✅ 1. Streamlined Patient Data Collection (20 use cases)
ACS Forms is used to collect demographic information before appointments.
ACS Forms is used to gather patient medical histories digitally.
ACS Forms is used to automate intake forms for new patients.
ACS Forms is used to capture consent for treatment electronically.
ACS Forms is used to collect insurance and billing information.
ACS Forms is used to digitize health questionnaires and risk assessments.
ACS Forms is used to replace clipboard-based in-clinic paperwork.
ACS Forms is used to ensure accuracy and completeness in data entry.
ACS Forms is used to eliminate scanning and manual filing of paper forms.
ACS Forms is used to reduce administrative errors and duplicate entries.
ACS Forms is used to pre-fill known patient data for faster completion.
ACS Forms is used to verify allergies and medication lists in advance.
ACS Forms is used to gather reason-for-visit details for better prep.
ACS Forms is used to shorten in-clinic wait and processing times.
ACS Forms is used to gather pre-screening info for infectious diseases.
ACS Forms is used to support remote form completion on mobile devices.
ACS Forms is used to ensure required fields are completed before submission.
ACS Forms is used to collect social determinants of health data.
ACS Forms is used to prepare patients for procedures by collecting relevant history.
ACS Forms is used to collect digital signatures securely and compliantly.

✅ 2. Operational Efficiency & Workflow Automation (20 use cases)
ACS Forms is used to auto-sync patient data with the EMR.
ACS Forms is used to reduce front-desk workload by eliminating manual form entry.
ACS Forms is used to route completed forms directly to appropriate departments.
ACS Forms is used to flag incomplete or missing information before check-in.
ACS Forms is used to replace faxed intake and pre-appointment documents.
ACS Forms is used to support multi-clinic workflows with location-specific forms.
ACS Forms is used to enable providers to review submissions before appointments.
ACS Forms is used to digitize internal forms like referral requests.
ACS Forms is used to simplify the onboarding of new providers or services.
ACS Forms is used to integrate screening logic into form workflows.
ACS Forms is used to trigger reminders for uncompleted forms.
ACS Forms is used to reduce patient back-and-forth during the intake process.
ACS Forms is used to collect appointment-specific forms based on visit type.
ACS Forms is used to enable pre-clinic triage and prioritization.
ACS Forms is used to track completion rates for performance metrics.
ACS Forms is used to monitor compliance with intake procedures.
ACS Forms is used to ensure up-to-date consent on file.
ACS Forms is used to support same-day visits with fast digital intake.
ACS Forms is used to prepare staff in advance with real-time data capture.
ACS Forms is used to decrease appointment delays due to paperwork bottlenecks.

✅ 3. Patient Experience & Engagement (20 use cases)
ACS Forms is used to offer patients a simple, guided digital experience.
ACS Forms is used to remove the stress of completing paperwork in the waiting room.
ACS Forms is used to allow patients to complete forms on their own time.
ACS Forms is used to offer mobile-friendly, accessible form interfaces.
ACS Forms is used to reduce redundant information requests.
ACS Forms is used to empower patients by involving them in data accuracy.
ACS Forms is used to personalize the experience with form logic tailored to patient type.
ACS Forms is used to allow parents or caregivers to complete forms remotely.
ACS Forms is used to improve communication clarity with multilingual options.
ACS Forms is used to provide educational content embedded within forms.
ACS Forms is used to give patients control over what they share and when.
ACS Forms is used to increase confidence in clinic professionalism and modernity.
ACS Forms is used to simplify the first visit for new patients.
ACS Forms is used to ensure patients are better prepared for their visit.
ACS Forms is used to allow feedback collection at the end of a care episode.
ACS Forms is used to reduce wait-time frustration by completing forms in advance.
ACS Forms is used to collect patient preferences around communication or care.
ACS Forms is used to streamline appointment check-in on arrival.
ACS Forms is used to increase follow-through with form-linked appointment confirmations.
ACS Forms is used to enhance overall satisfaction by offering a frictionless admin experience.
    
ACS Surveys

✅ 1. Patient Feedback & Satisfaction (20 use cases)
ACS Surveys is used to measure patient satisfaction after visits.
ACS Surveys is used to capture feedback on provider experience.
ACS Surveys is used to identify issues in the check-in process.
ACS Surveys is used to assess the clarity of communication during care.
ACS Surveys is used to gather insights about front-desk interactions.
ACS Surveys is used to improve care quality through patient comments.
ACS Surveys is used to benchmark satisfaction over time.
ACS Surveys is used to gauge comfort with virtual or hybrid visits.
ACS Surveys is used to evaluate the usefulness of patient education.
ACS Surveys is used to collect Net Promoter Scores (NPS).
ACS Surveys is used to discover unmet patient expectations.
ACS Surveys is used to identify and follow up on negative feedback.
ACS Surveys is used to assess accessibility for differently-abled patients.
ACS Surveys is used to tailor services based on patient input.
ACS Surveys is used to test new workflows or pilot programs.
ACS Surveys is used to measure satisfaction across multiple locations.
ACS Surveys is used to support service recovery initiatives.
ACS Surveys is used to improve online reputation by prompting review links.
ACS Surveys is used to ensure family caregivers are engaged and heard.
ACS Surveys is used to enhance loyalty and patient retention through ongoing feedback.

✅ 2. Clinical Insights & Quality Improvement (20 use cases)
ACS Surveys is used to evaluate adherence to clinical protocols.
ACS Surveys is used to collect feedback on pain management outcomes.
ACS Surveys is used to monitor post-operative recovery experiences.
ACS Surveys is used to assess effectiveness of chronic care management.
ACS Surveys is used to collect PREMs (Patient Reported Experience Measures).
ACS Surveys is used to conduct follow-up on treatment effectiveness.
ACS Surveys is used to track patient progress over time.
ACS Surveys is used to evaluate care coordination between providers.
ACS Surveys is used to inform quality assurance initiatives.
ACS Surveys is used to identify clinical workflow bottlenecks.
ACS Surveys is used to monitor patient-reported side effects.
ACS Surveys is used to ensure patient understanding of medication changes.
ACS Surveys is used to gather insights post-discharge or transition of care.
ACS Surveys is used to collect information for QIP (Quality Improvement Programs).
ACS Surveys is used to detect gaps in communication about diagnoses.
ACS Surveys is used to solicit patient perspectives on shared decision-making.
ACS Surveys is used to monitor consistency across care teams.
ACS Surveys is used to generate evidence for process redesign.
ACS Surveys is used to validate the success of care plans or interventions.
ACS Surveys is used to integrate patient voice into clinical strategy.

✅ 3. Operations, Compliance & Staff Engagement (20 use cases)
ACS Surveys is used to assess operational performance across departments.
ACS Surveys is used to collect feedback on digital tools and form usability.
ACS Surveys is used to verify staff friendliness and professionalism.
ACS Surveys is used to measure appointment access and ease of booking.
ACS Surveys is used to audit compliance with health equity initiatives.
ACS Surveys is used to evaluate wait times and patient flow satisfaction.
ACS Surveys is used to support regulatory documentation requirements.
ACS Surveys is used to collect staff input on training needs.
ACS Surveys is used to track employee Net Promoter Scores (eNPS).
ACS Surveys is used to monitor burnout or morale indicators.
ACS Surveys is used to collect incident follow-up feedback anonymously.
ACS Surveys is used to support accreditation and certification processes.
ACS Surveys is used to evaluate onboarding and discharge processes.
ACS Surveys is used to identify risks to patient safety from an operational lens.
ACS Surveys is used to check satisfaction after implementing new technology.
ACS Surveys is used to support internal performance evaluations.
ACS Surveys is used to detect early warning signs of service decline.
ACS Surveys is used to streamline staff suggestions into actionable insights.
ACS Surveys is used to support employee retention strategies.
ACS Surveys is used to assess satisfaction with ancillary services like labs or pharmacy.

Here is a real-world issue described by a healthcare provider:  
"{message}"

Your task is to:
1. Determine whether the issue aligns best with Automated Care Messaging, Automated Care Scheduling, or both.
2. Select one or more features from the list above that are most relevant. If only one feature is needed to solve the issue, provide just that feature. If multiple features are needed, provide a list of all the relevant features.
3. Write one concise paragraph explaining how the selected product(s) and feature(s) solve the issue — include how this fits within the broader Automated Care Platform (ACP).
4. Provide a list of 2–3 specific operational benefits written in Cliniconex’s confident, helpful tone.
5. ROI: Reduces [issue] by X%, increasing clinic revenue by an estimated $Y/year or saving Z hours/year in staff time.
6. Disclaimer: "Note: The ROI estimates provided are based on typical industry benchmarks and assumptions for healthcare settings. Actual ROI may vary depending on clinic size, patient volume, and specific operational factors."
"""

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

        use_matrix = (
            matrix_score >= 1 and matrix_item and
            gpt_response.get("product", "").lower() in matrix_item.get("product", "").lower()
        )

        if use_matrix:
            status = "matrix"
            matched_issue = matrix_item.get("product", "N/A")
            full_solution = matrix_item.get("solution", "")
            response = {
                "type": "solution",
                "module": matrix_item.get("product", "N/A"),
                "feature": ", ".join(matrix_item.get("features", [])) or "N/A",
                "solution": full_solution,
                "benefits": matrix_item.get("benefits", "N/A"),
                "keyword": keyword or "N/A"
            }
            log_to_google_sheets(message, page_url, matrix_item.get("product", "N/A"),
                                 matrix_item.get("features", []), status, matched_issue,
                                 "N/A", keyword, full_solution)
        else:
            status = "fallback"
            matched_issue = "N/A"
            full_solution = gpt_response.get("how_it_works", "")
            response = {
                "type": "solution",
                "module": gpt_response.get("product", "N/A"),
                "feature": ", ".join(gpt_response.get("feature", [])) or "N/A",
                "solution": full_solution,
                "benefits": "\n".join(gpt_response.get("benefits", [])) or "N/A",
                "roi": gpt_response.get("roi", "N/A"),
                "disclaimer": gpt_response.get("disclaimer", "N/A")
            }
            log_to_google_sheets(message, page_url, gpt_response.get("product", "N/A"),
                                 gpt_response.get("feature", []), status, matched_issue,
                                 gpt_response.get("product", "N/A"), "N/A", full_solution)

        return jsonify(response)
    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({"error": str(e)}), 500



# ✅ Start app for Render
if __name__ == "__main__":
    print(f"✅ Starting Cliniconex AI widget on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
