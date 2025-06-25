from flask import Flask, request
import os
import requests
from openai import OpenAI

app = Flask(__name__)

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route('/')
def home():
    return 'PastorJoebot is online and ready.'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_input = data['message'].get('text', '')
        reply = chat_with_gpt(user_input)
        send_telegram_message(chat_id, reply)
    return 'OK', 200

def chat_with_gpt(message):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are PastorJoebot, a deeply wise and Spirit-filled Christian counselor. "
                    "You speak with clarity, compassion, and theological depth. Respond with empathy, quoting Scripture where appropriate."
                )},
                {"role": "user", "content": message}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"🔥 OpenAI error: {e}")
        return "I'm having trouble connecting to my spiritual guidance center. Please try again soon."

def send_telegram_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

