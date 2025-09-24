from llama_cpp import Llama
from transformers import pipeline
import re

sentiment_analyzer = pipeline("sentiment-analysis")


# Load the model once
llm = Llama(
    model_path="models/Mistral.gguf",  # Adjust if needed
    chat_format="chatml"
)


# Mapping tone to system message
tone_map = {
    "Empathetic": "You're a kind, understanding listener.",
    "Sassy": "You're witty and a little sarcastic.",
    "Wholesome": "You're friendly and positive.",
    "Therapist": "You're calm, thoughtful, and sound like a therapist."
}

def run_confession_bot(message, tone="Empathetic"):
    from flask import session

    # System tone prompt
    system_prompt = {"role": "system", "content": tone_map.get(tone, tone_map["Empathetic"])}

    # Build conversation from history
    history = session.get("history", [])
    messages = [system_prompt]

    for turn in history:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["bot"]})

    # Add current user message
    messages.append({"role": "user", "content": message})

    # Log for debugging
    # print(f"📜 [DEBUG] Building prompt with {len(history)} history items")

    # Run the model
    response = llm.create_chat_completion(
        messages=messages,
        temperature=0.7,
        max_tokens=512
    )

    # Get bot reply
    bot_reply = response["choices"][0]["message"]["content"].strip()

    # Append the latest user+bot turn to history
    # print(f"📝 [DEBUG] Appending to history at {__name__} - run_confession_bot()")
    history.append({"user": message, "bot": bot_reply})
    session["history"] = history
    session.modified = True

    # print(f"✅ [DEBUG] History now has {len(history)} items")

    return bot_reply


def score_deed_with_sentiment(deed: str):
    result = sentiment_analyzer(deed)[0]
    label, score = result['label'], result['score']

    if label == "POSITIVE":
        # Scale from 0 to +10 based on confidence
        points = round(score * 10)
        reason = f"Positive deed (confidence {score:.2f})"
    elif label == "NEGATIVE":
        # Scale from 0 to -10 based on confidence
        points = -round(score * 10)
        reason = f"Negative deed (confidence {score:.2f})"
    else:
        points = 0
        reason = "Neutral deed"

    print(f"🤖 [DEBUG] Sentiment: {label}, Score: {score:.2f}, Points: {points}")
    return points, reason

