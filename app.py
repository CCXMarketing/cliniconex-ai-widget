from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json

app = Flask(__name__)
CORS(app, origins=["https://cliniconex.com"])

openai.api_key = os.getenv("OPENAI_API_KEY")

def query_model(message, model_name):
    prompt = f"""Suggest the most relevant Cliniconex product for this input: "{message}"

Respond in JSON like:
{{
  "solution": "Short explanation.",
  "module": "Product name",
  "link": "https://cliniconex.com/products"
}}"""

    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data.get('message', '')

    try:
        # Try GPT-4 first
        return jsonify(query_model(message, "gpt-4"))
    except Exception as e1:
        try:
            # Fallback to GPT-3.5
            return jsonify(query_model(message, "gpt-3.5-turbo"))
        except Exception as e2:
            return jsonify({
                "error": "Could not complete request.",
                "details": str(e2),
                "fallback_error": str(e1)
            })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
