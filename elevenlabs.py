import requests
from config import ELEVENLABS_API_KEY

def generate_voice(text, voice_id, settings):
    text = text.encode('utf-16', 'surrogatepass').decode('utf-16')
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "voice_settings": {
            "stability": settings.get("stability", 0.5),
            "similarity_boost": settings.get("similarity_boost", 0.75)
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Error: {response.status_code} - {response.text}")

def list_voices():
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [(voice['name'], voice['voice_id']) for voice in data['voices']]
    else:
        raise Exception(f"Failed to fetch voice list: {response.status_code}")

def get_voice_name_by_id(voice_id):
    voices = list_voices()
    for name, vid in voices:
        if vid == voice_id:
            return name
    return "Unknown"
