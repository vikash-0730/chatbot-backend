from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_with_confidence
from responses import responses
from deep_translator import GoogleTranslator
import os

import firebase_admin
from firebase_admin import credentials, db
import json

app = Flask(__name__)
CORS(app)

# 🔥 Firebase init
firebase_key = json.loads(os.environ.get("FIREBASE_KEY"))
cred = credentials.Certificate(firebase_key)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ai-chatbot-6b2d0-default-rtdb.firebaseio.com'
})

# 🔥 Session
user_sessions = {}

# 🔥 HISTORY LIMIT (IMPORTANT 🔥)
MAX_HISTORY = 5

# 🔥 Hinglish Dictionary
hinglish_map = {
    "pesa": "payment",
    "paisa": "payment",
    "paise": "payment",
    "money": "payment",

    "oder": "order",
    "ordr": "order",

    "wapas": "refund",
    "return": "refund"
}

def normalize_text(text):
    words = text.lower().split()
    return " ".join([hinglish_map.get(w, w) for w in words])


def get_user_by_phone(phone):
    try:
        phone = str(phone).strip().replace("+91", "")
        return db.reference(f'users/{phone}').get()
    except:
        return None


def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except:
        return text


def smart_intent(text):
    text = text.lower()

    # 🔥 ORDER HISTORY (highest priority)
    if any(word in text for word in ["history", "previous", "last"]):
        return "order_history"

    if "refund" in text:
        return "refund"

    if any(word in text for word in ["payment", "upi", "transaction", "deduct"]):
        return "payment_issue"

    if any(word in text for word in ["order", "delivery", "parcel", "track"]):
        return "order_status"

    return None


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")

        if not user_msg:
            return jsonify({"response": "Please enter a message"})

        user_msg = user_msg.strip()

        # =====================================================
        # 🔥 PHONE INPUT
        # =====================================================
        if user_msg.isdigit() and len(user_msg) >= 10:

            session = user_sessions.get("temp")

            if not session:
                return jsonify({"response": "Please ask your query first."})

            intent = session["intent"]
            phone = user_msg

            user_data = get_user_by_phone(phone)

            if not user_data:
                return jsonify({"response": "User not found."})

            name = user_data.get("name", "User")

            # 🔥 ORDER STATUS
            if intent == "order_status":
                order = user_data.get("order", {})
                reply = f"{name}, your order {order.get('item')} is {user_data.get('order_status')} 🚚"

            # 🔥 PAYMENT
            elif intent == "payment_issue":
                reply = f"{name}, your payment is {user_data.get('payment_status')} via {user_data.get('payment_mode')} 💳"

            # 🔥 REFUND
            elif intent == "refund":
                reply = f"{name}, refund for order {user_data.get('order', {}).get('id')} will be processed 💰"

            # 🔥 ORDER HISTORY (LIMITED 🔥)
            elif intent == "order_history":
                history = user_data.get("order_history", [])

                if history:
                    limited_history = history[-MAX_HISTORY:]  # 🔥 last 5 only
                    reply = f"{name}, your last {len(limited_history)} orders are: {', '.join(limited_history)} 📦"
                else:
                    reply = f"{name}, you have no previous orders."

            user_sessions.clear()
            return jsonify({"response": reply})

        # =====================================================
        # 🔥 NORMAL FLOW
        # =====================================================

        normalized_msg = normalize_text(user_msg)
        intent = smart_intent(normalized_msg)

        if not intent:
            translated_msg = translate_to_english(normalized_msg)
            intent, confidence = predict_with_confidence(translated_msg)
        else:
            confidence = 1.0

        print("User:", user_msg)
        print("Normalized:", normalized_msg)
        print("Intent:", intent)

        # 🔥 DATA INTENTS
        if intent in ["order_status", "payment_issue", "refund", "order_history"]:
            user_sessions["temp"] = {"intent": intent}
            return jsonify({"response": "Please provide your phone number to check details."})

        # 🔥 LOW CONFIDENCE
        if confidence < 0.3:
            return jsonify({
                "response": "I didn’t understand. Try asking about orders, refund or payment."
            })

        # 🔥 NORMAL CHAT
        reply = responses.get(intent, "Something went wrong")

        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({
            "response": "Server error",
            "error": str(e)
        })


@app.route("/test-user/<phone>")
def test_user(phone):
    return jsonify(get_user_by_phone(phone))


if __name__ == "__main__":
     app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)