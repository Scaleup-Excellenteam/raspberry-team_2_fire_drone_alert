from flask import Flask, request, Response
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
NGROK_URL = os.getenv('NGROK_URL')

# Set up the Telegram webhook
TELEGRAM_INIT_WEBHOOK_URL = f'https://api.telegram.org/bot{TOKEN}/setWebhook?url={NGROK_URL}/message'
requests.get(TELEGRAM_INIT_WEBHOOK_URL)


@app.route('/sanity')
def sanity():
    return "Server is running"


@app.route('/message', methods=["GET","POST"])
def handle_message():
    # Get the JSON payload of the incoming message
    incoming_message = request.get_json()['message']

    # Send a response message
    response_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={incoming_message}"
    requests.get(response_url)

    return Response("success")

if __name__ == '__main__':
    app.run(port=5002)
