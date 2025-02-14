from flask import Flask, request, jsonify
import requests, os, json
#from dotenv import load_dotenv
from pocketbase import PocketBase

#as long as it is prepared to store key values
#load_dotenv()

#initialize key values
WEBHOOK_VERIFY_TOKEN = ""
GOOGLE_CHAT_WEBHOOK = ""
GRAPH_API_TOKEN = ""
POCKETBASE_URL = ""
PHONE_NUMBER_ID = "564629343400647"

#instance server flask
app = Flask(__name__)

#initialize pocketbase
pb = PocketBase(POCKETBASE_URL)

#debugging login pocketbase
try:
    pb.admins.auth_with_password("dimasalfadam05@gmail.com", "dimasitsecrnd")
    print("login pocketbase")
except Exception as e:
    print(str(e))

#debugging log request
@app.before_request
def log_request_info():
    print("=== Incoming Request Info ===")
    print(f"headers: {request.headers}")
    print(f"data: {request.data.decode("utf-8")}")

#verification webhook from meta
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    hub_mode = request.args.get("hub.mode")
    hub_challenge = request.args.get("hub.challenge")
    hub_verify_token = request.args.get("hub.verify_token")

    if hub_mode == "subscribe" and hub_verify_token == WEBHOOK_VERIFY_TOKEN:
        return hub_challenge
    return "Verification failed", 403

#webhook handler
@app.route("/webhook", methods=["POST"])
def webhook_post():
    #get data from sender whatsapp
    payload = request.get_json()
    
    #debug check IP addr
    #sender_ip = request.remote_addr

    #validate payload
    if not payload or "entry" not in payload:
        return jsonify({"error": "Invalid payload"}), 400
    
    #dump information from sender
    entry = payload["entry"][0]
    changes = entry.get("changes", [])
    if not changes:
        return jsonify({"message": "No changes detected"}), 200

    value = changes[0].get("value", {})
    messages = value.get("messages", [])

    if messages:
        message_data = messages[0]
        from_user = message_data.get("from")
        message_type = message_data.get("type")
        message_text = message_data.get("text", {}).get("body", "")

        sendReplyMsg(from_user, "Terima kasih, pesan Anda sedang diproses.", "")

        #save message to pocketbase
        save_msg_to_pocketbase(from_user, message_type, message_text)

        #send to google chat
        google_chat_msg = f"New WhatsApp message from {from_user}: {message_text}"
        send_to_google_chat(google_chat_msg)

        print(f"Pesan diterima dari {from_user}: {message_text}")

    return jsonify({"message": "Webhook received successfully"}), 200

#save data to pocketbase
def save_msg_to_pocketbase(from_user: str, message_type: str, message_text: str):
    try:
        data = {
            "from_user": from_user,
            "message_type": message_type,
            "message_text": message_text
        }
        print(f"Data successfully saved to pocketbase: {json.dumps(data, indent=4)}")

        record = pb.collection("messages").create(data)
        print(f"Message saved to PocketBase:", record)

    except Exception as e:
        print(f"Error saving to PocketBase: {str(e)}")

#send msg to google chat
def send_to_google_chat(message: str):
    payload = {"text": message}
    response = requests.post(GOOGLE_CHAT_WEBHOOK, json=payload)

    #check status response
    if response.status_code == 200:
        print("Message sent to Google Chat")
    else:
        print(f"Failed to send message: {response.text}")

#download media from whatsapp
def download_media(media_id: str, filename: str):
    url = f"https://graph.facebook.com/v21.0/{media_id}/"
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

#reply msg to sender whatsapp
def sendReplyMsg(recipient, msgText, replyMsgID):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "text": {"body": msgText},
        "context": {"message_id": replyMsgID}
    }

    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("Reply message successfully")
    else:
        print("Failed to reply message: {response.text}")

#mark the message as read
def markAsRead(msgID):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": msgID
    }

    headers = {
        "Authorization": f"Bearer {GRAPH_API_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("Reply message successfully")
    else:
        print("Failed to reply message: {response.text}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3004, debug=True)