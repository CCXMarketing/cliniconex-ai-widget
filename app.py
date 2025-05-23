from flask import Flask, request, jsonify
import openai
import os
import json

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/ai', methods=['POST'])
def ai_solution():
    data = request.get_json()
    message = data['message']

    prompt = f"""You are a helpful assistant for a healthcare company. Based on the input, suggest the most relevant Cliniconex product or module.

    Input: "{message}"

    Respond in JSON with:
    {{
      "solution": "Short paragraph explaining the matched product.",
      "module": "Product name",
      "link": "https://cliniconex.com/products"
    }}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        reply = response.choices[0].message.content
        parsed = json.loads(reply)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": "Could not complete request", "details": str(e)})

# Render-specific port binding
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
