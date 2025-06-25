from flask import Flask, request
import requests, os, openai

app = Flask(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate tokens
if not BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Missing BOT_TOKEN or OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Simulated memory (session only)
conversation_memory = {}

# Journaling log
journal_entries = {}

# Daily verses (manual list for now)
daily_verses = [
    "Isaiah 41:10 - Fear not, for I am with you.",
    "Psalm 34:18 - The Lord is close to the brokenhearted.",
    "Romans 15:13 - May the God of hope fill you with joy and peace.",
]

@app.route('/')
def home():
    return 'PastorJoebot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    try:
        chat_id = data['message']['chat']['id']

        if 'voice' in data['message']:
            return send_message(chat_id, "Voice message received. Voice-to-text support is coming soon.")

        text = data['message'].get('text', '')

        # Memory
        memory = conversation_memory.get(chat_id, [])
        memory.append(text)
        conversation_memory[chat_id] = memory[-5:]  # limit memory to last 5 messages

        # Check for crisis language
        if any(word in text.lower() for word in ['suicidal', 'kill myself', 'worthless', 'no purpose']):
            crisis_response = (
                "I'm so sorry you're feeling this way. Please know that your life is deeply loved by God.\n\n"
                "Psalm 34:18 says, 'The Lord is close to the brokenhearted.' You're not alone.\n"
                "Would you like to be connected with a Christian counselor or local support group?"
            )
            return send_message(chat_id, crisis_response)

        # Check for prayer
        if "pray" in text.lower():
            return handle_prayer(chat_id, text)

        # Check for journaling
        if "journal" in text.lower() or "write" in text.lower():
            return start_journaling(chat_id)

        # Daily verse request
        if "verse" in text.lower():
            verse = daily_verses[0]  # rotate or randomize later
            return send_message(chat_id, f"📖 Today's verse: {verse}")

        # Church finder placeholder
        if "church" in text.lower() or "near me" in text.lower():
            return send_message(chat_id, "I’d love to help you find a local church. What’s your ZIP code? (Feature coming soon!)")

        # Default: pass to GPT
        reply = chat_with_gpt(chat_id, text)
        return send_message(chat_id, reply)

    except Exception as e:
        print("Webhook error:", e)
        return 'Error', 400

# --- Core ChatGPT Brain ---
def chat_with_gpt(chat_id, user_input):
    try:
        context = [
            {"role": "system", "content": "You are a wise and compassionate Christian pastor named PastorJoebot. Respond with empathy, scripture, and Spirit-led guidance."},
        ] + [{"role": "user", "content": msg} for msg in conversation_memory.get(chat_id, [])[-3:]]

        context.append({"role": "user", "content": user_input})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=context,
            temperature=0.8,
            max_tokens=200
        )

        return response['choices'][0]['message']['content'].strip()

    except Exception as e:
        print("GPT error:", e)
        return "I'm here for you, even when I can’t find the right words right away."

# --- Journaling ---
def start_journaling(chat_id):
    prompt = (
        "📝 Would you like to reflect on one of these?\n"
        "1. What are you feeling today?\n"
        "2. What is something you want to surrender to God?\n"
        "3. What verse has spoken to you recently?"
    )
    journal_entries[chat_id] = []
    return send_message(chat_id, prompt)

# --- Prayer Requests ---
def handle_prayer(chat_id, message):
    # Store or log request
    print(f"Prayer request from {chat_id}: {message}")
    return send_message(chat_id, "🙏 I’ve recorded your prayer request. Know that God hears you.")

# --- Telegram Send Message ---
def send_message(chat_id, text):
    url = f"{BOT_URL}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)
    return 'OK', 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

