from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import traceback
import openai
from rapidfuzz import fuzz

# ✅ Load solutions from JSON
with open("cliniconex_solutions.json", "r", encoding="utf-8") as f:
    solutions_data = json.load(f)

# ✅ Set your OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ✅ Flask app setup
app = Flask(__name__)
CORS(app, resources={r"/ai": {"origins": "https://cliniconex.com"}})

# ✅ Match logic: Find best match using fuzzy search
def find_best_match(user_input):
    best_score = 0
    best_match = None
    for row in solutions_data:
        combined_text = f"{row['issue']} {row['solution']} {row['benefits']}"
        score = fuzz.partial_ratio(user_input.lower(), combined_text.lower())
        if score > best_score:
            best_score = score
            best_match = row
    return best_match

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

        match = find_best_match(message)

        if not match:
            return jsonify({
                "type": "unclear",
                "message": "Sorry, I couldn't find a solution that matches. Could you rephrase your issue?"
            })

        # ✅ GPT prompt using matched solution
        prompt = f"""
You are a helpful assistant working for Cliniconex, a healthcare communication company.

A healthcare professional will enter a short question or problem - it might be vague, have typos, or be just a couple words.

Your job:
1. If the meaning is clear, respond with a product module, feature, solution explanation, benefits, and product link.
2. If the input is too unclear to confidently answer, return a polite message asking them to rephrase.

Respond in strict JSON in one of these two formats:

# If input is clear:
{{
  "type": "solution",
  "module": "{match['product']}",
  "feature": "{match['features'][0] if match['features'] else 'N/A'}",
  "solution": "{match['solution']}",
  "benefits": "{match['benefits']}",
  
}}

# If input is vague:
{{
  "type": "unclear",
  "message": "Sorry, I didn't quite understand. Could you try asking that another way?"
}}

User input: "{message}"
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        reply = response.choices[0].message.content

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
