from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json

app = Flask(__name__)
CORS(app)  # <- Allows requests from browsers (important!)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"error": "Missing input", "details": "No message provided"}), 400

    # Refined prompt with clarification logic for vague inputs
    prompt = f"""
You are a product advisor for Cliniconex, a healthcare communication company.

A healthcare professional will describe a challenge they’re facing. It may be short, vague, or have typos.
Your job is to:
1. Interpret what they mean as best you can — even if it's just a few words like "no shows" or "scheduling".
2. Recommend the most relevant Cliniconex product module.
3. Suggest one specific feature within that module that solves the issue.
4. If the input is truly too unclear, ask a clarifying question in a friendly way.

Speak clearly, like you're chatting with a smart but busy clinic or hospital admin. Don’t use technical jargon. Use plain, helpful language.

Here are example short prompts and how to interpret them:
- "no shows" → Automated Appointment Reminders
- "burnout" → Workflow Automation
- "pt updates" → Family Broadcasts
- "shift chaos" → Shift Notifications
- "emr help" → EMR Integration

Respond in this JSON format:
{{
  "module": "Cliniconex product name (or 'Unclear')",
  "feature": "Specific feature name (or null)",
  "solution": "Plain English explanation (or clarifying question if unclear)",
  "link": "https://cliniconex.com/products"
}}

User input: "{message}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(reply)
            return jsonify(parsed)
        except Exception as e:
            return jsonify({
                "error": "Could not parse JSON",
                "details": str(e),
                "raw": reply
            }), 500

    except Exception as e:
        return jsonify({
            "error": "Could not complete request",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
