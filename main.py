from flask import Flask, request
import os
import requests
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
user_journals = {}
user_prayers = {}

@app.route('/')
def home():
    return 'PastorJoebot is online and listening.'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_input = data['message'].get('text', '').strip()

        if user_input.lower().startswith('/journal'):
            entry = user_input[8:].strip()
            if entry:
                user_journals.setdefault(chat_id, []).append(entry)
                reply = "📝 Journal entry saved."
            else:
                reply = "Please write something after /journal to save it."

        elif user_input.lower() == '/myjournal':
            entries = user_journals.get(chat_id, [])
            reply = "📖 Your journal entries:\n" + "\n".join(f"- {e}" for e in entries[-5:]) if entries else "📭 No journal entries yet."

        elif user_input.lower().startswith('/pray'):
            prayer = user_input[5:].strip()
            if prayer:
                user_prayers.setdefault(chat_id, []).append(prayer)
                reply = "🙏 I've recorded your prayer. Lifting it to the Lord with you."
            else:
                reply = "Please write something after /pray to submit a request."

        elif user_input.lower() == '/myprayers':
            prayers = user_prayers.get(chat_id, [])
            reply = "🕊️ Your recent prayer requests:\n" + "\n".join(f"- {p}" for p in prayers[-5:]) if prayers else "📭 No prayer requests found."

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
                        "You are PastorJoebot, a modern voice echoing the Spirit of Christ as revealed in the Gospels. "
                        "You speak like a compassionate, wise friend—gentle, honest, and deeply rooted in Jesus’ teachings. "
                        "Let the words of Christ in the New Testament shape your tone, attitude, and heart. "
                        "Avoid sounding robotic or overly formal—speak plainly, relationally, and with spiritual depth. "
                        "When users share, listen first. Affirm what is true. Encourage honest prayer and spiritual curiosity. "
                        "When helpful, reflect relevant scriptures, simple prayers, or open-ended questions. "
                        "You may offer short blessings, journaling prompts, or wisdom summaries, but only if they serve the moment. "
                        "Speak into the user's world—aware of modern struggles like burnout, doubt, parenting, identity, technology, and loneliness. "
                        "Above all, be present. Don’t lecture. Don’t fix. Simply walk with them, like Jesus with the disciples on the road to Emmaus. "
                        "When appropriate, gently reflect patterns in the user’s spiritual walk, as if you’re growing to know them personally. "
                        "Your goal is to be a faithful, Spirit-led companion who helps people find meaning, peace, and hope in Jesus."
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


