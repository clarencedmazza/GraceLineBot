from flask import Flask, request
import os
import requests
import openai
from datetime import datetime
import redis
import logging
import re
import random
from datetime import datetime
import json  

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

from dotenv import load_dotenv
load_dotenv()

redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("REDIS_URL environment variable is not set")

r = redis.from_url(redis_url)

# Save devotional to Redis
def save_user_devotional(chat_id, content):
    r.set(f"user_devo:{chat_id}", content)

# Load devotional from Redis
def get_user_devotional(chat_id):
    result = r.get(f"user_devo:{chat_id}")
    return result.decode('utf-8') if result else None
 

def current_time():
    return datetime.now().strftime("%b %d, %Y %I:%M %p")

@app.route('/')
def home():
    return 'GraceLine is online and listening.'

@app.route('/health')
def health():
    return 'OK', 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()

        if 'message' in data:
            chat_id = data['message']['chat']['id']
            user_input = data['message'].get('text', '').strip()
            logging.info(f"Message from {chat_id}: {user_input[:30]}...")

            # 1. Crisis check
            crisis_reply = check_for_crisis(user_input)
            if crisis_reply:
                logging.warning(f"Crisis response triggered for {chat_id}")
                send_telegram_message(chat_id, crisis_reply)
                return 'OK', 200

            # 2. Command handling or GPT fallback
            reply = handle_custom_commands(chat_id, user_input)
            send_telegram_message(chat_id, reply)

        return 'OK', 200

    except Exception as e:
        logging.exception("🔥 Unhandled error in /webhook")
        return 'Internal Server Error', 500

def handle_custom_commands(chat_id, user_input):
    lower_input = user_input.lower()

    try:
        if lower_input.startswith('/journal'):
            entry = user_input[8:].strip()
            if entry:
                entry_text = f"📝 {current_time()} - {entry}"
                r.lpush(f"journal:{chat_id}", entry_text)
                return "Your journal entry was saved. Thank you for reflecting."
            return "✍️ To write a journal entry, type: `/journal Today I felt...`"

        elif lower_input == '/myjournal':
            entries = [e.decode('utf-8') for e in r.lrange(f"journal:{chat_id}", 0, 4)]
            if not entries:
                return "📬 No journal entries yet. Try `/journal` to start one."
            return "📖 Your last journal entries:\n\n" + "\n".join(entries)

        elif lower_input == '/deletejournal':
            removed = r.lpop(f"journal:{chat_id}")
            if removed:
                return f"🗑️ Removed your last journal entry:\n\n{removed.decode('utf-8')}"
            return "There are no journal entries to delete."

        elif lower_input.startswith('/pray'):
            prayer = user_input[5:].strip()
            if prayer:
                prayer_text = f"🙏 {current_time()} - {prayer}"
                r.lpush(f"prayer:{chat_id}", prayer_text)
                return "I've recorded your prayer. The Lord is near."
            return "🕊️ To send a prayer, type: `/pray Lord, I need help with...`"

        elif lower_input == '/myprayers':
            prayers = [p.decode('utf-8') for p in r.lrange(f"prayer:{chat_id}", 0, 4)]
            if not prayers:
                return "📬 No prayer requests yet. Use `/pray` to submit one."
            return "🔧 Your recent prayers:\n\n" + "\n".join(prayers)

        elif lower_input == '/deleteprayer':
            removed = r.lpop(f"prayer:{chat_id}")
            if removed:
                return f"🗑️ Removed your last prayer:\n\n{removed.decode('utf-8')}"
            return "There are no prayers to delete."

        elif lower_input == '/devo':
            from tasks import queue_devotional
            queue_devotional(chat_id)
            return "📖 Preparing your devotional... I'll send it shortly."


        elif lower_input in ['another verse', 'more scripture', 'share another verse', 'can i hear another verse']:
            return generate_additional_verse()

        elif lower_input == '/meditate':
            last_devo = get_user_devotional(chat_id)
            if not last_devo:
                return "🕊️ No devotional found yet. Start with `/devo` first."
            return generate_meditation_from_devo(last_devo)


        elif lower_input == '/start':
            return (
                "👋 *Welcome to GraceLine!*\n\n"
                "GraceLine offers a quiet line of grace in a noisy world—guiding you gently toward Jesus through prayer, scripture, and reflection..\n\n"
                "🙏 *A short prayer:*\n"
                "_Lord, thank You for walking with me. Guide my thoughts, stir my heart, and help me find rest in Your presence._\n\n"
                "*Here are a few ways you can use me:*\n"
                "• `/journal I’m feeling...` — to write a personal journal\n"
                "• `/myjournal` — to see your past journal entries\n"
                "• `/pray Lord, help me...` — to record a prayer\n"
                "• `/myprayers` — to review past prayers\n"
                "• `/devo` — to receive a fresh, Scripture-based devotional\n"
                "• `/meditate` — to reflect on your latest devotional\n"
                "• `/help` — for more guidance\n\n"
                "✝️ I’m here to walk beside you — not to fix, but to listen, reflect, and remind you that God is near."
            )

        elif lower_input == '/help':
            return (
                "🛠 *GraceLine Help Guide*\n\n"
                "Im here to walk with you in your journey with God-through daily devotionals, journaling, and prayer:\n\n"
                "📖 *Daily Devotionals:*\n"
                "`/devo` — Get a short, expository devotional\n"
                "`/meditate` — Reflect deeper on your last devo\n\n"
                "✍️ *Journaling:*\n"
                "`/journal Today I...` — Write a journal entry\n"
                "`/myjournal` — View your recent entries\n"
                "`/deletejournal` — Delete your latest entry\n\n"
                "🙏 *Prayer:*\n"
                "`/pray God, I...` — Record a private prayer\n"
                "`/myprayers` — Review recent prayers\n"
                "`/deleteprayer` — Remove your last prayer\n\n"
                "💬 You can also just talk to me — I’ll listen and respond like a wise, caring friend in Christ.\n\n"
                "If you're ever in deep distress, I’ll gently point you toward help. You're not alone."
            )

        # Fallback to GPT
        return chat_with_gpt(user_input)

    except Exception as e:
        logging.exception(f"Command handling error for user {chat_id}")
        return "Something went wrong while processing your command. Please try again later."

def chat_with_gpt(message):
    try:
        system_prompt = """
You are GraceLine, a modern conversational voice drawing from the Spirit of God as revealed in the full counsel of Scripture.
You speak like a compassionate, wise friend—gentle, honest, and deeply rooted in Jesus’ teachings.
Let the person and posture of Christ in the New Testament shape your tone, mindset, and heart.

You walk with users in their process of sanctification—the ongoing transformation of their hearts, minds, and lives to reflect Christlikeness.
This means encouraging faith, humility, obedience, love, and surrender in everyday moments.

Avoid sounding robotic or overly formal—speak plainly, relationally, and with spiritual depth.
When users share, listen first. Affirm what is true. Encourage honest prayer, spiritual curiosity, and the slow work of grace.
Only offer journaling prompts or open-ended reflection questions occasionally — when it feels natural, like in a quiet pause or after something meaningful has been shared.

Avoid asking follow-up questions in every response. Let the conversation breathe. Think like Jesus on the road to Emmaus — curious, patient, and present.

If a user asks for help, encouragement, or a verse, answer simply and kindly. Only ask something deeper if it genuinely fits the flow of the moment.

Speak into the user’s world—aware of modern struggles like burnout, doubt, parenting, identity, technology, and loneliness.
Offer hope that these are not roadblocks, but invitations into deeper surrender and maturity in Christ.

Above all, be present. Don’t lecture. Don’t fix. Walk with them like Jesus on the road to Emmaus—curious, patient, illuminating.
When a user seeks prayer, never pray for them or with them. Instead, guide them in prayer using language like,
“Here’s something you might pray…” or “Let’s bring this to God together.” Be a companion in prayer, not an intercessor.

As trust grows, gently reflect patterns in the user’s spiritual walk, as if you’re growing to know them personally.
Speak to their journey with kindness and clarity.

Your goal is to be a faithful, gracious, Spirit-led companion—not to solve, but to shepherd souls into the likeness of Christ through love, truth, and grace.
Every response must be original and tailored. Avoid recycled phrasing or generic replies.
Always respond in a way that directly acknowledges the user’s unique message, season, and need.
"""

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        return response['choices'][0]['message']['content'].strip()

    except Exception as e:
        logging.exception("OpenAI error in chat_with_gpt")
        return "I'm having trouble connecting to my spiritual guidance center. Please try again later."

def extract_verse_reference(text):
    """
    Attempts to extract the first recognizable Bible verse reference from a string.
    Supports formats like:
    - John 3:16
    - Philippians 4:6–7
    - Romans 8:28–30
    - 1 John 1:9
    """
    pattern = r"\b(?:[1-3]\s)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s\d+:\d+(?:[-–]\d+)?\b"
    match = re.search(pattern, text)
    return match.group(0).strip() if match else None

def is_verse_used_this_year(verse_ref):
    year_key = f"used_devo_verses:{datetime.now().year}"
    return r.sismember(year_key, verse_ref)

def mark_verse_as_used(verse_ref):
    year_key = f"used_devo_verses:{datetime.now().year}"
    r.sadd(year_key, verse_ref)

def generate_devotional(chat_id=None):
    prompt = """
You are a Christian writer. Craft a daily devotional (max 200 words) that is biblical, and wise. Your tone should feel like a compassionate mentor, and the exegesis should be simple and profound.

Follow this structure:

1. Scripture (ESV)
Begin with a short, complete ESV passage (2–5 verses) that is spiritually rich but not overused. Include the full citation (e.g., Romans 8:38–39). Choose a verse that lends itself to reflection and invites fresh insight.

2. Insight
Gently unpack the verse in its biblical and historical context. Let the truth shine, but speak it with warmth, not academic distance. When helpful, weave in the voices of trusted christian writers. Let Scripture breathe—avoid sounding like a commentary.

You may use imagery, analogy, or even metaphor.

3. Application
Speak into the heart. Address real human struggles—anxiety, shame, distraction, longing, fear, or grief. Help the reader feel seen, understood, and gently called forward into Christlikeness.

Let this be felt truth, not just stated truth.

When appropriate, a metaphor, or a line that catches the breath. Let beauty serve clarity, not obscure it.

4. Closing
End with:
- A short, soulful, and scripted first person prayer flowing naturally from the devotional.
- A reflection question that draws the reader deeper into personal communion with God.

Tone Guidelines:
- Write with spiritual depth, literary grace, and pastoral warmth.
- Avoid clichés, religious platitudes, or overly formal theological language.
- Prioritize beauty, intimacy, and Christ-centered hope.

Begin now.
"""
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            content = response['choices'][0]['message']['content'].strip()
            verse_ref = extract_verse_reference(content)

            logging.info(f"[DEVO] Attempt {attempt + 1} - Verse found: {verse_ref or 'None'}")

            if verse_ref and not is_verse_used_this_year(verse_ref):
                mark_verse_as_used(verse_ref)
                if chat_id:
                    save_user_devotional(chat_id, content)
                    send_telegram_message(chat_id, content)  
                return content  # This is still returned regardless of whether chat_id exists


        except Exception as e:
            logging.exception("Error generating or checking devotional verse")

    return (
        "🕊️ I wasn’t able to generate a fresh devotional today without repeating a verse. "
        "Please try again tomorrow."
    )

def generate_additional_verse():
    try:
        prompt = (
            "Share one encouraging Bible verse (ESV), followed by a short, uplifting reflection (1–2 sentences). "
            "Speak in a warm, personal tone, like a friend walking with someone in faith."
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.exception("OpenAI error in generate_additional_verse")
        return "Sorry, I wasn’t able to share a verse right now. Try again in a moment."

def generate_meditation_from_devo(devo_text):
    try:
        prompt = (
            f"Based on the following devotional, write a short meditation question or spiritual reflection prompt "
            f"to help someone go deeper with God into the content of the devotional. Be gentle, honest, and personal.\n\n{devo_text}"
        )
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return "🧘‍♂️ Reflect on this:\n" + response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.exception("OpenAI error in generate_meditation_from_devo")
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
        logging.exception("OpenAI error in check_for_crisis")
        return None

def send_welcome_keyboard(chat_id):
    keyboard = {
        "keyboard": [
            ["📝 Journal", "🙏 Prayer"],
            ["📖 Devotional", "🧘 Meditate"],
            ["❓ Help"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

    payload = {
        "chat_id": chat_id,
        "text": (
            "GraceLine is here to walk with you. Choose one of the options below to begin.\n\n"
            "You can always type a command too, like /pray or /devo."
        ),
        "reply_markup": json.dumps(keyboard)
    }

    try:
        requests.post(f"{BOT_URL}/sendMessage", json=payload)
    except Exception as e:
        logging.exception(f"Error sending welcome keyboard to {chat_id}")

def send_telegram_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.exception(f"Telegram message error for {chat_id}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)





