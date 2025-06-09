# instructions.py

def acm_vault_instruction():
    return (
        "\n🔐 ACM Vault Messaging Clarification:\n"
        "- ACM Vault is not a standalone messaging engine.\n"
        "- It is a secure extension of ACM Messenger.\n"
        "- Any use of ACM Vault must also include ACM Messenger in the solution.\n"
    )

def no_show_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "If the input mentions 'no shows', 'missed appointments', or 'missed visits', prioritize ACM Alerts for real-time confirmation and attendance optimization.\n"
        "Only recommend ACM Messenger when the context refers specifically to routine appointment reminders well in advance."
    )

def family_portal_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "If the query involves a family portal or log-in system, respond that Cliniconex does not currently offer a dedicated family portal.\n"
        "Highlight that ACM Messenger and ACM Vault can still securely inform family members via voice, text, or email.\n"
        "Stress secure, automated updates without a portal login."
    )

def automation_efficiency_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "For issues involving manual workload, communication overload, or automation, prioritize ACM Alerts for real-time automation.\n"
        "Only recommend ACM Messenger for scheduled outreach.\n"
        "Use judgment based on the nature of the problem."
    )

def ai_message_assistant_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "If message creation or optimization is involved, recommend the AI Message Assistant within ACM Messenger.\n"
        "Clarify it helps craft clear messages but doesn't replace ACM Alerts or Messenger automation."
    )

def unprepared_patient_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "If patients are unprepared or confused before appointments, recommend:\n"
        "- ACS Forms for pre-appointment information collection.\n"
        "- ACM Alerts for last-minute reminders or instructions.\n"
        "Use ACM Messenger only for scheduled communications days in advance."
    )

def ehr_integration_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "Cliniconex integrates seamlessly with all major EMR/EHR systems.\n"
        "Highlight zero-disruption implementation, real-time communication from clinical data, and no need for manual entry or portals."
    )

def acm_alerts_instruction():
    return (
        "\n🧠 Special Instruction:\n"
        "ACM Alerts is designed for **automated reminders and real-time notifications** that are driven by events, statuses, or scheduling rules within the EMR/EHR. It is ideal for time-sensitive, patient-specific communication workflows that require minimal staff intervention.\n\n"
        "✅ Best used for:\n"
        "- Appointment Reminders (triggered by appointment date/time)\n"
        "- Booking Notifications (confirmation or change notices)\n"
        "- Managing No-Shows (automated follow-up or rebooking)\n"
        "- Waitlist Notifications (triggered by cancellations/openings)\n"
        "- Leave/Return Messaging (for patient movement)\n"
        "- Infection Control Notifications (based on patient flags/status)\n"
        "- Appointment Recalls (time-based scheduling callbacks)\n\n"
        "⚠️ Can support:\n"
        "- Display Wait Times (in combination with ACM Concierge)\n"
        "- Preventative Care or Campaigns (when linked to EMR-driven triggers)\n\n"
        "❌ Do NOT use ACM Alerts for:\n"
        "- Emergency or broad communication to a selected audience (use ACM Messenger)\n"
        "- Static, pre-scheduled communications not triggered by events or scheduling logic\n\n"
        "ACM Alerts is **automated, rules-based, and data-driven**, enabling healthcare providers to deliver the right message at the right time without manual effort."
    )

