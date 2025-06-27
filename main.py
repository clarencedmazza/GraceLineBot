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
user_devotionals = {}  # To track last devotional per user

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

        # Check for mental health crisis first
        crisis_reply = check_for_crisis(user_input)
        if crisis_reply:
            send_telegram_message(chat_id, crisis_reply)
            return 'OK', 200

        # Handle commands and fallback to GPT
        reply = handle_custom_commands(chat_id, user_input)
        send_telegram_message(chat_id, reply)

    return 'OK', 200

def handle_custom_commands(chat_id, user_input):
    lower_input = user_input.lower()

    if lower_input.startswith('/journal'):
        entry = user_input[8:].strip()
        if entry:
            entry_text = f"\ud83d\udcdd {current_time()} - {entry}"
            user_journals.setdefault(chat_id, []).append(entry_text)
            return "Your journal entry was saved. Thank you for reflecting."
        return "\u270d\ufe0f To write a journal entry, type: `/journal Today I felt...`"

    elif lower_input == '/myjournal':
        entries = user_journals.get(chat_id, [])
        if not entries:
            return "\ud83d\udcec No journal entries yet. Try `/journal` to start one."
        return "\ud83d\udcd6 Your last journal entries:\n\n" + "\n".join(entries[-5:])

    elif lower_input == '/deletejournal':
        if user_journals.get(chat_id):
            removed = user_journals[chat_id].pop()
            return f"\ud83d\uddd1\ufe0f Removed your last journal entry:\n\n{removed}"
        return "There are no journal entries to delete."

    elif lower_input.startswith('/pray'):
        prayer = user_input[5:].strip()
        if prayer:
            prayer_text = f"\ud83d\ude4f {current_time()} - {prayer}"
            user_prayers.setdefault(chat_id, []).append(prayer_text)
            return "I've recorded your prayer. The Lord is near."
        return "\ud83d\udd4a\ufe0f To send a prayer, type: `/pray Lord, I need help with...`"

    elif lower_input == '/myprayers':
        prayers = user_prayers.get(chat_id, [])
        if not prayers:
            return "\ud83d\udcec No prayer requests yet. Use `/pray` to submit one."
        return "\ud83d\udd27 Your recent prayers:\n\n" + "\n".join(prayers[-5:])

    elif lower_input == '/deleteprayer':
        if user_prayers.get(chat_id):
            removed = user_prayers[chat_id].pop()
            return f"\ud83d\uddd1\ufe0f Removed your last prayer:\n\n{removed}"
        return "There are no prayers to delete."

    elif lower_input == '/devo':
        return generate_devotional(chat_id)

    elif lower_input in ['another verse', 'more scripture', 'share another verse', 'can i hear another verse']:
        return generate_additional_verse()

    elif lower_input == '/meditate':
        last_devo = user_devotionals.get(chat_id)
        if not last_devo:
            return "\ud83d\udd4a\ufe0f No devotional found yet. Start with `/devo` first."
        return generate_meditation_from_devo(last_devo)

    # Fallback to GPT for conversation
    return chat_with_gpt(user_input)

def chat_with_gpt(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PastorJoebot, a modern voice drawing from the Spirit of God as revealed in the full council of the bible. "
                        "You speak like a compassionate, wise friend—gentle, honest, and deeply rooted in Jesus’ teachings. "
                        "Let the person of Christ in the New Testament shape your tone, attitude, and heart. "
                        "Avoid sounding robotic or overly formal—speak plainly, relationally, and with spiritual depth. "
                        "When users share, listen first. Affirm what is true. Encourage honest prayer and spiritual curiosity. "
                        "When helpful, reflect relevant scriptures, simple prayers, or open-ended questions. "
                        "You may offer short blessings, journaling prompts, or wisdom summaries, but only if they serve the moment. "
                        "Speak into the user's world—aware of modern struggles like burnout, doubt, parenting, identity, technology, and loneliness. "
                        "Above all, be present. Don’t lecture. Don’t fix. Simply walk with them, like Jesus with the disciples on the road to Emmaus. "
                        "When a user seeks prayer, never pray for them or with them. Instead, guide them in prayer using language like, "
                        "'Here’s something you might pray' or 'Let’s bring this to God together.' Be a companion in prayer—not an intercessor. "
                        "When appropriate, gently reflect patterns in the user’s spiritual walk, as if you’re growing to know them personally. "
                        "Your goal is to be a faithful, Spirit-led companion who helps people find meaning, peace, and hope in Jesus. "
                        "Every response must be original and tailored. Avoid repeating phrases or cycling the same generic replies. "
                        "Always respond in a way that directly acknowledges the user's specific message or need."
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"\ud83d\udd25 OpenAI error: {e}")
        return "I'm having trouble connecting to my spiritual guidance center. Please try again later."

def generate_devotional(chat_id=None):
    try:
        prompt = (
            "Write a short, encouraging, and theologically daily Christian devotional (under 200 words) "
            "based on a verse from the bible. Speak in a personal, modern tone, as if to a friend. "
            "Include:\n"
            "- A verse (ESV)\n"
            "- A brief reflection\n"
            "- One sentence prayer"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response['choices'][0]['message']['content'].strip()

        if chat_id:
            user_devotionals[chat_id] = content

        return content
    except Exception as e:
        print(f"\ud83d\udd25 Devotional error: {e}")
        return "Sorry, I wasn't able to generate today's devotional. Please try again soon."

def generate_additional_verse():
    try:
        prompt = (
            "Share one encouraging Bible verse (ESV), followed by a short, uplifting reflection (1–2 sentences). "
            "Speak in a warm, personal tone, like a friend walking with someone in faith."
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"\ud83d\udd25 Additional verse error: {e}")
        return "Sorry, I wasn’t able to share a verse right now. Try again in a moment."

def generate_meditation_from_devo(devo_text):
    try:
        prompt = (
            f"Based on the following devotional, write a short meditation question or spiritual reflection prompt "
            f"to help someone go deeper with God into the content of the devotional. Be gentle, honest, and personal.\n\n{devo_text}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return "\ud83e\uddd8\u200d\u2642\ufe0f Reflect on this:\n" + response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"\ud83d\udd25 Meditation error: {e}")
        return "Sorry, I couldn’t generate a meditation right now."

def check_for_crisis(message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a crisis safety classifier in a Christian mental health bot. "
                        "Your only job is to evaluate if this message contains signs of serious emotional or mental distress—"
                        "including suicidal thoughts, self-harm, abuse, or severe hopelessness.\n\n"
                        "If yes, respond ONLY with:\n"
                        "CRISIS: I'm really sorry you're feeling this way. You're not alone. "
                        "Please call or text 988 to speak with someone right away.\n\n"
                        "If safe, respond only with: SAFE\n\n"
                        "Do not explain. Do not analyze. Only classify."
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        output = response['choices'][0]['message']['content'].strip()
        return output if output.startswith("CRISIS:") else None
    except Exception as e:
        print(f"\ud83d\udd25 Crisis detection error: {e}")
        return None

def send_telegram_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"\ud83d\udd25 Telegram message error: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)




