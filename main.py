from flask import Flask, request
import requests
import os

app = Flask(__name__)

TOKEN = os.getenv("BOT_TOKEN")
BOT_URL = f'https://api.telegram.org/bot{TOKEN}'

@app.route('/')
def home():
    return 'PastorJoebot is live!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if data is None:
        return 'No data', 400

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message']['text']
        reply = handle_message(text)
        send_message(chat_id, reply)

    return 'OK', 200

def handle_message(text):
    if 'anxious' in text.lower():
        return "Fear not, for I am with you. - Isaiah 41:10"
    return "God bless you. I'm here if you want to talk."

def send_message(chat_id, text):
    url = f'{BOT_URL}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
