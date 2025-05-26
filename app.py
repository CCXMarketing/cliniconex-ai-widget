from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from openai import OpenAI
# import requests  # Uncomment if you want to enable Google Sheets logging

app = Flask(__name__)
CORS(app)  # Enables CORS for all domains

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data.get('message', '').strip()

    prompt = f"""
You are a helpful assistant working for Cliniconex, a healthcare communication company.

A healthcare professional will enter a short question or problem — it might be vague, have typos, or be just a couple words.

Your job:
1. If the meaning is clear, respond with a product **module**, **feature**, **solution explanation**, and **product link**.
2. If the input is too unclear to confidently answer, return a polite message asking them to rephrase.

Respond in **strict JSON** in one of these two formats:

# If input is clear:
{{
  "type": "solution",
  "module": "Name of the most relevant Cliniconex product module",
  "feature": "Name of one key feature in that module",
  "solution": "Plain-English explanation of how it helps solve their problem",
  "link": "https://cliniconex.com/products/#relevant-feature-anchor"
}}

# If input is vague:
{{
  "type": "unclear",
  "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
}}

User input: "{message}"
"""

    result = {
        "prompt": message,
        "module": "",
        "feature": "",
        "type": "",
        "status": "Error",
        "notes": ""
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response.choices[0].message.content

        try:
            parsed = json.loads(reply)
            result.update({
                "module": parsed.get("module", ""),
                "feature": parsed.get("feature", ""),
                "type": parsed.get("type", ""),
                "status": "Success",
                "notes": parsed.get("solution", parsed.get("message", ""))
            })
            return jsonify(parsed)
        except Exception as e:
            result["notes"] = "JSON parse error: " + str(e)
            return jsonify({
                "type": "unclear",
                "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
            })

    except Exception as e:
        result["notes"] = str(e)
        return jsonify({
            "error": "Could not complete request",
            "details": str(e)
        })

    # 🔒 Optional: Log to Google Sheets (disabled for now)
    """
    try:
        sheets_url = "https://script.google.com/macros/s/YOUR_SCRIPT_ID_HERE/exec"
        requests.post(sheets_url, json=result, timeout=5)
    except Exception as log_err:
        print("Logging to Sheets failed:", log_err)
    """

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
