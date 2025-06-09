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
        "ACM Alerts is designed for **immediate, event-driven communications** that respond to real-world changes. "
        "Use it when communication needs to be fast, flexible, and critical to same-day or urgent workflows.\n\n"
        "✅ Ideal for:\n"
        "- Weather-related or emergency closures\n"
        "- Same-day provider cancellations or shift changes\n"
        "- Day-of instructions or reminders (e.g., fasting reminders, arrival time updates)\n\n"
        "❌ Do not recommend ACM Alerts for:\n"
        "- Standard reminders sent days in advance\n"
        "- Scheduled communication workflows (use ACM Messenger instead)\n\n"
        "ACM Alerts integrates with your EMR to deliver messages instantly via voice, text, or email. It’s fully configurable, so it can adapt to operational realities without needing manual input."
    )
