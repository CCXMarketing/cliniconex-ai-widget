from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
import json

app = Flask(__name__)
CORS(app)  # Allows cross-origin requests from browser (required for frontend widget)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"error": "Missing input", "details": "No message provided"}), 400

    prompt = f"""
You are a product advisor for Cliniconex, a healthcare communication company.

Healthcare professionals will describe challenges they're facing. These inputs may be short, vague, or have typos.

Your job is to:
1. Interpret what they mean as best you can — even if it's just a few words like "no shows", "scheduling", or "burnout".
2. If the meaning is clear, respond with a single best-matched Cliniconex module, key feature, explanation, and link.
3. If the input is vague, provide 2 to 3 possible modules with brief explanations in a list, each with its own feature and link.

Respond using one of the JSON formats below. These are examples of the structure only — you must choose your own best-matched values based on the user input.

**If the input is clear:**
{{
  "type": "solution",
  "module": "Product module name here",
  "feature": "Specific feature name",
  "solution": "Plain English explanation",
  "link": "https://cliniconex.com/products#relevant-section"
}}

**If the input is vague:**
{{
  "type": "unclear",
  "clarification": "I'm not exactly sure what you mean. Did you mean one of the following?",
  "options": [
    {{
      "module": "Module A",
      "feature": "Feature A",
      "explanation": "Short explanation of what this does.",
      "link": "https://cliniconex.com/products#section-a"
    }},
    {{
      "module": "Module B",
      "feature": "Feature B",
      "explanation": "Short explanation of what this does.",
      "link": "https://cliniconex.com/products#section-b"
    }}
  ]
}}

Here is the user input:
"{message}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Use gpt-3.5-turbo for lower cost if needed
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
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
