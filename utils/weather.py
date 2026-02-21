import httpx
import logging
import asyncio

async def get_omsk_weather():
    # координаты Омска
    lat = 54.99
    lon = 73.37
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&wind_speed_unit=ms"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()["current"]
                temp = round(data["temperature_2m"])
                code = data["weather_code"]
                
                # расшифровка
                descriptions = {
                    0: "ясно ☀️",
                    1: "преимущественно ясно 🌤", 2: "переменная облачность ⛅️", 3: "пасмурно ☁️",
                    45: "туманно 🌫", 48: "иней 🌫",
                    51: "легкая морось 🌧", 53: "умеренная морось 🌧", 55: "сильная морось 🌧",
                    61: "небольшой дождь 🌦", 63: "умеренный дождь 🌧", 65: "сильный дождь ⛈",
                    71: "небольшой снег ❄️", 73: "умеренный снег ❄️", 75: "сильный снег ❄️",
                    77: "снежная крупа 🌨",
                    80: "ливневые дожди 🌧", 81: "сильные ливни ⛈", 82: "очень сильные ливни ⛈",
                    85: "небольшой снегопад 🌨", 86: "сильный снегопад 🌨",
                    95: "гроза ⚡️"
                }
                
                weather_desc = descriptions.get(code, "необычная погода")
                return f"{temp}°C, {weather_desc}"
            else:
                return "уютная омская погода"
    except Exception as e:
        logging.error(f"Weather error: {e}")
        return "уютная омская погода"
    
if __name__ == "__main__":
    print(asyncio.run(get_omsk_weather()))