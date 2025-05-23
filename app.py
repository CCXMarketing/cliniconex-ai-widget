from flask import Flask, request, jsonify
import openai
import os

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

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    reply = response['choices'][0]['message']['content']
    
    # Safely parse the reply
    import json
    try:
        parsed = json.loads(reply)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": "Could not parse response", "details": str(e), "raw": reply})

# ✅ Required for Render — expose the correct host/port
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
