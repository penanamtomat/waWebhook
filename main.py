from fastapi import FastAPI, Request, HTTPException, Query
from pydantic import BaseModel
import requests
import os
import random, string
from dotenv import load_dotenv
from pocketbase import PocketBase
from typing import Optional

#load env variables
load_dotenv()

#generate webhook token
# def generate_token(length=16):
#     """Generate random token using random library."""
#     characters = string.ascii_letters + string.digits  # Huruf dan angka
#     return ''.join(random.choices(characters, k=length))

POCKETBASE_URL = "http://127.0.0.1:8090"
WEBHOOK_VERIFY_TOKEN = "randomajastringnya"
GOOGLE_CHAT_WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAAAHVrlY1c/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=dgJqP-CKRJiVJm0Sf-4J2JDEdSrYPH29Lr7S0QGOCzs"
GRAPH_API_TOKEN = "EAAQmDJB3E3gBO8ISRm06t2Djxc22AIHPYqaBGChuLc889pjFlGZCvLYPibTzXZATEAZABNF6jGSkTpJndFqALSMeOAsZChSxuCF8kaARTOQZCqDinUd3CzsZBmxUn1VB6Y7dgUSPfVBK3JOR2MZBt98ikcLqLQ6UkRlrdqO8QBvoHIs0IkeXUzNVGkOeMyRvHZBL1gZDZD"

app = FastAPI()
pb = PocketBase(POCKETBASE_URL)
pb.admins.auth_with_password("dimasalfadam05@gmail.com", "dimasitsecrnd")

#model data webhook
class webhookPayload(BaseModel):
    event: str
    entry: list

#root endpoint
@app.get('/')
def main():
    return {'message': 'This service is run'}

#verification endpoint for webhook whatsapp (GET)
@app.get("/webhook")
def verify_webhook(
    hub_mode: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
    hub_challenge: Optional[str] = None  # Gunakan str agar tidak error parsing
):
    """Verifikasi Webhook WhatsApp API"""
    if hub_mode == "subscribe" and hub_verify_token == WEBHOOK_VERIFY_TOKEN:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")

# Webhook event handler (POST)
@app.post("/webhook")
async def webhook_handler(request: Request):
    payload = await request.json()

    if "entry" not in payload or not payload["entry"]:
        raise HTTPException(status_code=400, detail="Invalid payload")

    entry = payload["entry"][0]
    changes = entry.get("changes", [])
    if not changes:
        return {"message": "No changes detected"}

    value = changes[0].get("value", {})
    messages = value.get("messages", [])

    if messages:
        message_data = messages[0]
        message_id = message_data.get("id")
        from_user = message_data.get("from")
        message_type = message_data.get("type")
        message_text = message_data.get("text", {}).get("body", "")

        # Save message to PocketBase
        save_message_to_pocketbase(message_id, from_user, message_type, message_text)

        # Send to Google Chat
        google_chat_message = f"New WhatsApp message from {from_user}: {message_text}"
        send_to_google_chat(google_chat_message)

    return {"message": "Webhook received successfully"}

# Function to download media from WhatsApp
def download_media(media_id: str, filename: str):
    """download file media dari WhatsApp API"""
    url = f"https://graph.facebook.com/v19.0/{media_id}/"
    headers = {"Authorization": f"Bearer {GRAPH_API_TOKEN}"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching media data: {response.text}")
        return None

    media_data = response.json()
    media_url = media_data.get("url")

    if not media_url:
        print("No media URL found")
        return None

    media_response = requests.get(media_url, headers=headers)
    if media_response.status_code == 200:
        with open(filename, "wb") as file:
            file.write(media_response.content)
        print(f"File downloaded: {filename}")
        return filename
    else:
        print(f"Failed to download file: {media_response.text}")
        return None
    
#save msg to pocketbase
def save_message_to_pocketbase(message_id: str, from_user: str, message_type: str, message_text: str):
    """Simpan pesan ke database PocketBase"""
    try:
        record = pb.collection("messages").create({
            "id": message_id,
            "from_user": from_user,
            "message_type": message_type,
            "message_text": message_text
        })
        print("Message saved to PocketBase:", record)
    except Exception as e:
        print("Error saving to PocketBase:", str(e))

#send chat msg to google chat
def send_to_google_chat(message: str):
    """Mengirim pesan ke Google Chat menggunakan Webhook"""
    payload = {"text": message}
    response = requests.post(GOOGLE_CHAT_WEBHOOK, json=payload)
    if response.status_code == 200:
        print("Message sent to Google Chat")
    else:
        print(f"Failed to send message: {response.text}")