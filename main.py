from flask import Flask, request
import os
import requests
import openai
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

user_journals = {}
user_prayers = {}

def current_time():
    return datetime.now().strftime("%b %d, %Y %I:%M %p")

@app.route('/')
def home():
    return 'PastorJoebot is online and listening.'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_input = data['message'].get('text', '').strip()

        reply = handle_custom_commands(chat_id, user_input)
        send_telegram_message(chat_id, reply)

    return 'OK', 200

def handle_custom_commands(chat_id, user_input):
    lower_input = user_input.lower()

    if lower_input.startswith('/journal'):
        entry = user_input[8:].strip()
        if entry:
            entry_text = f"📝 {current_time()} - {entry}"
            user_journals.setdefault(chat_id, []).append(entry_text)
            return "Your journal entry was saved. Thank you for reflecting."
        return "✍️ To write a journal entry, type: `/journal Today I felt...`"

    elif lower_input == '/myjournal':
        entries = user_journals.get(chat_id, [])
        if not entries:
            return "📭 No journal entries yet. Try `/journal` to start one."
        return "📖 Your last journal entries:\n\n" + "\n".join(entries[-5:])

    elif lower_input == '/deletejournal':
        if user_journals.get(chat_id):
            removed = user_journals[chat_id].pop()
            return f"🗑️ Removed your last journal entry:\n\n{removed}"
        return "There are no journal entries to delete."

    elif lower_input.startswith('/pray'):
        prayer = user_input[5:].strip()
        if prayer:
            prayer_text = f"🙏 {current_time()} - {prayer}"
            user_prayers.setdefault(chat_id, []).append(prayer_text)
            return "I've recorded your prayer. The Lord is near to the brokenhearted."
        return "🕊️ To send a prayer, type: `/pray Lord, I need help with...`"

    elif lower_input == '/myprayers':
        prayers = user_prayers.get(chat_id, [])
        if not prayers:
            return "📭 No prayer requests yet. Use `/pray` to submit one."
        return "🕯️ Your recent prayers:\n\n" + "\n".join(prayers[-5:])

    elif lower_input == '/deleteprayer':
        if user_prayers.get(chat_id):
            removed = user_prayers[chat_id].pop()
            return f"🗑️ Removed your last prayer:\n\n{removed}"
        return "There are no prayers to delete."

    elif lower_input == '/devo':
        return get_daily_devotional()

    # Fallback to GPT for anything else
    return chat_with_gpt(user_input)

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

def get_daily_devotional():
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": (
                    "You are a Spirit-led Christian devotional writer. Create a fresh, daily devotional that sounds personal, honest, and rooted in Scripture. "
                    "Choose a single verse from the Bible (ESV). Begin with a short, engaging title. Then list the verse. Follow with a reflection that's two short paragraphs—"
                    "simple, clear, and heartfelt. End with a two-line prayer. Aim to encourage people who are weary, doubtful, anxious, or hungry for God. "
                    "Avoid lofty language or long sermons—write like someone walking with a friend. Let grace, truth, and hope come through in every word."
                )
            }]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"🔥 Devotional error: {e}")
        return "I'm having trouble retrieving today's devotional. Please try again later."

def send_telegram_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



