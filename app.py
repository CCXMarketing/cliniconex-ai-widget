
from flask import Flask, request, jsonify
from openai import OpenAI
import os
import json

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data['message']

    # Use the refined, helpful advisor tone in the prompt
    prompt = f"""
You are a product advisor for Cliniconex, a healthcare communication company.

A healthcare professional will describe a challenge they’re facing. Your job is to:
1. Understand their problem in plain terms.
2. Recommend the most relevant Cliniconex module.
3. Highlight one specific feature within that module that would solve their problem — but explain it in simple, human-friendly language.
4. End with a helpful link where they can learn more.

Speak clearly, like you're chatting with a smart but busy clinic or hospital admin. Don’t use jargon or internal names unless necessary. Prioritize clarity.

Respond in this JSON format:
{{
  "module": "Cliniconex product name",
  "feature": "Name of feature you're highlighting",
  "solution": "Plain English explanation of how it helps",
  "link": "https://cliniconex.com/products"
}}

User input: "{message}"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content

        try:
            parsed = json.loads(reply)
            return jsonify(parsed)
        except Exception as e:
            return jsonify({"error": "Could not parse response", "details": str(e), "raw": reply})

    except Exception as e:
        return jsonify({"error": "Could not complete request", "details": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
