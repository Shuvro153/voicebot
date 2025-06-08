import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

def generate_voice_with_fallback(text, voice_id, settings):
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",  # optional, you can remove this
        "voice_settings": settings,
        "output_format": "mp3_44100_128",
        "with_history": True
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Voice generation failed. Status code: {response.status_code}")

    # Save audio content
    audio_data = response.content

    # Get history from /history endpoint
    time.sleep(1.5)  # wait for history to register
    history_res = requests.get("https://api.elevenlabs.io/v1/history", headers=headers)
    if history_res.status_code == 200:
        items = history_res.json().get("history", [])
        if items:
            history_item_id = items[0]["history_item_id"]
        else:
            raise Exception("No history found in ElevenLabs.")
    else:
        raise Exception("Failed to retrieve history.")

    return audio_data, ELEVENLABS_API_KEY, history_item_id


def delete_history_item(history_id, api_key):
    url = f"https://api.elevenlabs.io/v1/history/{history_id}"
    headers = {
        "xi-api-key": api_key
    }
    response = requests.delete(url, headers=headers)
    return response.status_code == 200
