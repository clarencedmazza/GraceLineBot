from flask import Flask, request
import os
import requests
import openai
from datetime import datetime
import redis
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Connect to Redis
r = redis.from_url(os.getenv("REDIS_URL"))

user_devotionals = {}  # Still in memory for now 

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
            return generate_devotional(chat_id)

        elif lower_input in ['another verse', 'more scripture', 'share another verse', 'can i hear another verse']:
            return generate_additional_verse()

        elif lower_input == '/meditate':
            last_devo = user_devotionals.get(chat_id)
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
                "I offer spiritual tools grounded in Scripture and grace:\n\n"
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
When helpful, reflect relevant scriptures, simple prayers, or open-ended questions that invite the user to grow in Christ.
You may offer short blessings, journaling prompts, or wisdom summaries—but only if they serve the moment and help the user draw nearer to Jesus.

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

def generate_devotional(chat_id=None):
    try:
        prompt = """
You are a seasoned Christian spiritual guide with deep knowledge of Scripture, theology, and church history. Write a daily devotional (under 400 words) that follows this structure:

1. Scripture: Begin with a short passage from the ESV (preferably 2–5 verses that form a complete thought).
2. Insight: Explain the passage’s original context and meaning, drawing from the best of Christian tradition (e.g., Spurgeon, Keller, Lewis, Bonhoeffer, Willard, Tozer).
3. Application: Speak directly to the reader with warmth, clarity, and pastoral honesty. Address real-life spiritual struggles with hope and humility.
4. Closing: End with a one-sentence prayer and an open-ended reflective question that invites the reader to respond personally to God.

Write with depth, gentleness, and grace—like a wise mentor walking beside a modern disciple. Avoid clichés, overused phrases, or shallow encouragement. Use rich imagery and spirit-led language that draws hearts toward Jesus.
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response['choices'][0]['message']['content'].strip()

        if chat_id:
            user_devotionals[chat_id] = content

        return content
    except Exception as e:
        logging.exception("OpenAI error in generate_devotional")
        return "Sorry, I wasn't able to generate today's devotional. Please try again soon."

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
        "reply_markup": keyboard
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





