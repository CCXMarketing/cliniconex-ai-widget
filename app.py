from flask import Flask, request, jsonify
import os
import json
import traceback

from openai import OpenAI
from httpx import Timeout, Client as HTTPXClient

print("✅ OpenAI SDK version:", OpenAI.__module__)

# Environment
openai_api_key = os.environ.get("OPENAI_API_KEY")

# Manually override transport (bypass proxy error)
custom_http_client = HTTPXClient(
    timeout=Timeout(10.0, connect=5.0),
    follow_redirects=True,
)

client = OpenAI(api_key=openai_api_key, http_client=custom_http_client)

app = Flask(__name__)

@app.before_request
def log_request_info():
    print(f"➡️ Incoming request: {request.method} {request.path}")

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

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response.choices[0].message.content

        try:
            parsed = json.loads(reply)
            return jsonify(parsed)
        except Exception:
            return jsonify({
                "type": "unclear",
                "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
            })

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ Full Exception Traceback:\n", tb)

        return jsonify({
            "error": "Could not complete request",
            "details": str(e),
            "trace": tb
        })

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Flask app is running!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
