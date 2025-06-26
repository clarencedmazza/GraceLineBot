from flask import Flask, request, jsonify
import openai
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def home():
    return "🧭 AbideBot is ready to help you make wise decisions."

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    chat_id = data['message']['chat']['id']
    user_input = data['message'].get('text', '').strip()

    # Trigger decision helper
    if user_input.lower().startswith("/decide"):
        return send_reply(chat_id, "🧭 Please describe your situation or decision you're facing. Be as honest and detailed as you like.")

    # Let GPT guide the full decision process based on a single user message
    return handle_decision(chat_id, user_input)

def handle_decision(chat_id, user_input):
    system_prompt = """
You are AbideBot, a wise Christian mentor inspired by Greg Koukl's book *Decision Making and the Will of God*.

Your purpose is to help people make important life decisions by guiding them through biblical wisdom. You do not rely on mystical signs or feelings. You trust God's revealed will in Scripture and encourage people to:
1. Ask if the choice violates God’s moral will.
2. Use wisdom (consider goals, consequences, advice, desires, logic).
3. Choose freely with faith if both options are morally good and wise.

You are emotionally attuned, spiritually grounded, and respectful of the user’s autonomy. You gently challenge false beliefs, affirm truth, and encourage peace in freedom.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=0.7
    )

    bot_reply = response.choices[0].message['content']
    return send_reply(chat_id, bot_reply)

def send_reply(chat_id, text):
    return jsonify({
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })

if __name__ == "__main__":
    app.run(debug=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


