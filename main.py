from flask import Flask, request
import requests, os, openai

app = Flask(__name__)

# Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_URL = f"https://api.telegram.org/bot{TOKEN}"

# Memory per chat (in-memory only)
conversation_memory = {}

@app.route('/')
def home():
    return 'PastorJoebot is live!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'message' not in data:
        return 'No data', 400

    chat_id = data['message']['chat']['id']
    user_input = data['message'].get('text') or ''

    # Store conversation
    if chat_id not in conversation_memory:
        conversation_memory[chat_id] = []
    conversation_memory[chat_id].append(user_input)

    # GPT Response
    reply = chat_with_gpt(chat_id, user_input)
    send_message(chat_id, reply)
    return 'OK', 200

def chat_with_gpt(chat_id, user_input):
    openai.api_key = OPENAI_API_KEY

    context = [
        {
            "role": "system",
            "content": (
                "You are PastorJoebot, a Spirit-filled, theologically grounded, emotionally intelligent Christian pastor with a doctorate-level command of the entire Bible. "
                "You offer biblically faithful, spiritually mature, and deeply compassionate guidance. "
                "You respond with grace, quote Scripture in context, and offer robust theology and pastoral wisdom. "
                "Avoid clichés and engage in thoughtful, conversational dialogue. You never shut down questions; you lean in and walk with people in their struggles and joys."
            )
        },
        *[{"role": "user", "content": msg} for msg in conversation_memory.get(chat_id, [])[-3:]],
        {"role": "user", "content": user_input}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=context
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return ("I'm having a temporary issue connecting to my spiritual guidance center. Please try again in a moment."
                " If the issue persists, please let my creator know. 🙏")

def send_message(chat_id, text):
    url = f'{BOT_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send message: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
