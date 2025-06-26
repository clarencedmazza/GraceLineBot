from flask import Flask, request
import os
import requests
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
user_journals = {}


@app.route('/')
def home():
    return 'PastorJoebot is online and listening.'


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_input = data['message'].get('text', '')
        if user_input.lower().startswith('/journal'):
            entry = user_input[8:].strip()
            if entry:
                user_journals.setdefault(chat_id, []).append(entry)
                reply = "📝 Journal entry saved."
            else:
                reply = "Please write something after /journal to save it."
        elif user_input.lower() == '/myjournal':
            entries = user_journals.get(chat_id, [])
            if not entries:
                reply = "📭 No journal entries yet."
            else:
                reply = "📖 Your journal entries:\n" + "\n".join(f"- {e}" for e in entries[-5:])
        else:
            reply = chat_with_gpt(user_input)

        send_telegram_message(chat_id, reply)
    return 'OK', 200


def chat_with_gpt(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PastorJoebot, a humble voice shaped entirely by the words, teachings, and spirit of Jesus Christ as revealed in the Gospels. "
                        "Every response should reflect Christ’s compassion, wisdom, authority, and love. Speak as He might speak today: in clear, modern language, but always with grace, truth, and spiritual insight. "
                        "Do not preach. Instead, invite. Do not judge. Instead, illuminate. Let your words comfort the broken, challenge the proud, uplift the weary, and draw all hearts closer to God. "
                        "Prioritize storytelling, questions, silence when needed, and always Scripture when appropriate. Keep your responses, sincere, and Spirit-filled."
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"🔥 OpenAI error: {e}")
        return "I'm having trouble connecting to my spiritual guidance center. Please try again later."


def send_telegram_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

