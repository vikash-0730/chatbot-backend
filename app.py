from flask import Flask, request, jsonify
from flask_cors import CORS
from model import predict_with_confidence
from responses import responses
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

# 🔥 Translation function
def translate_to_english(text):
    try:
        return GoogleTranslator(source='auto', target='en').translate(text)
    except Exception:
        return text

# 🔥 Keyword override (fix for ML mistakes)
def keyword_override(text):
    text = text.lower()

    payment_keywords = ["paisa", "payment", "deduct", "upi", "transaction", "money"]
    refund_keywords = ["refund", "return", "wapas"]
    order_keywords = ["order", "parcel", "delivery", "track"]

    for word in payment_keywords:
        if word in text:
            return "payment_issue"

    for word in refund_keywords:
        if word in text:
            return "refund"

    for word in order_keywords:
        if word in text:
            return "order_status"

    return None


@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_msg = request.json.get("message")

        if not user_msg:
            return jsonify({"response": "Please enter a message"})

        # 🔥 Step 1: Translate
        translated_msg = translate_to_english(user_msg)

        # 🔥 Step 2: Keyword override first
        override_intent = keyword_override(user_msg)

        if override_intent:
            intent = override_intent
            confidence = 1.0
        else:
            # 🔥 Step 3: ML prediction
            intent, confidence = predict_with_confidence(translated_msg)

        # 🔥 Debug logs (console me dikhega)
        print("User:", user_msg)
        print("Translated:", translated_msg)
        print("Intent:", intent, "Confidence:", confidence)

        # 🔥 Step 4: Low confidence fallback
        if confidence < 0.3:
            return jsonify({
                "response": "I didn’t understand. Try asking about orders, refund or payment."
            })

        # 🔥 Step 5: Get response
        reply = responses.get(intent, "Something went wrong")

        return jsonify({
            "response": reply,
            "intent": intent,
            "confidence": float(confidence),
            "translated": translated_msg
        })

    except Exception as e:
        return jsonify({
            "response": "Server error, please try again later.",
            "error": str(e)
        })


if __name__ == "__main__":
    app.run(debug=True)