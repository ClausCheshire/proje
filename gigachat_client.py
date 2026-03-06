# -*- coding: utf-8 -*-
import aiohttp
import config
import json
from urllib.parse import urlencode

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

async def get_gigachat_token():
    # 1. Пробуем основной scope, если не выйдет — в логе будет подсказка
    scope = "GIGACHAT_API_PERS"
    
    # 2. Кодируем данные строго как form-urlencoded
    data = urlencode({"scope": scope})
    
    # 3. Заголовки для OAuth
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 4. Basic Auth
        auth = aiohttp.BasicAuth(config.GIGACHAT_CLIENT_ID, config.GIGACHAT_CLIENT_SECRET)
        
        async with session.post(AUTH_URL, auth=auth, data=data, headers=headers) as resp:
            response_text = await resp.text()
            
            if resp.status == 200:
                json_data = await resp.json()
                return json_data["access_token"]
            else:
                # 5. Подробный лог ошибки для Railway
                print(f"❌ GigaChat Auth Failed: {resp.status}")
                print(f"📄 Response Body: {response_text}")
                print(f"🔑 Client ID: {config.GIGACHAT_CLIENT_ID[:5]}...") # Первые 5 символов для проверки
                raise Exception(f"GigaChat auth error: {resp.status} - {response_text}")

async def analyze_text(text: str, agency: str = "Unknown", location: str = "Unknown") -> str:
    token = await get_gigachat_token()
    
    system_prompt = (
        "You are a legal assistant specializing in Russian administrative law. "
        "Analyze the response from a government agency. "
        "1. Summarize the main points. "
        "2. Identify grounds for appeal. "
        "3. Add disclaimer: not official legal advice."
    )

    payload = {
        "model": "GigaChat", # Попробуем базовую модель для стабильности
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Agency: {agency}\nRegion: {location}\n\nText:\n{text}"}
        ],
        "profanity_check": True
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error_text = await resp.text()
                return f"Analysis error: {resp.status} - {error_text}"
