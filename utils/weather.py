import requests

def get_omsk_weather():
    try:
        # юзаем wttr.in для города
        response = requests.get("https://wttr.in/Omsk?format=%C+%t", timeout=5)
        if response.status_code == 200:
            return response.text
        return "ясно, +20°C" # заглушка
    except:
        return "уютная омская погода"