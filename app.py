from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import traceback
import openai  # ✅ Correct import

# ✅ Set API key for OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ✅ Flask app setup
app = Flask(__name__)
CORS(app, resources={r"/ai": {"origins": "https://cliniconex.com"}})

@app.route("/ai", methods=["POST"])
def ai_solution():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({
                "type": "unclear",
                "message": "Please provide a message."
            }), 400

        # ✅ Prompt formatting
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

        # ✅ Call OpenAI with correct method
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response.choices[0].message.content

        # ✅ Parse strict JSON response
        try:
            return jsonify(json.loads(reply))
        except json.JSONDecodeError:
            return jsonify({
                "type": "unclear",
                "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
            })

    except Exception as e:
        return jsonify({
            "error": "Could not complete request",
            "details": str(e),
            "trace": traceback.format_exc()
        }), 500

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Cliniconex AI Solution Advisor is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
