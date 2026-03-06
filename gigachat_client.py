# -*- coding: utf-8 -*-
import aiohttp
import config
import json
import base64
from urllib.parse import urlencode

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

async def get_gigachat_token():
    scope = "GIGACHAT_API_PERS"
    
    # 1. Формируем Basic Auth вручную (client_id:client_secret)
    credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    # 2. Заголовки
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    # 3. Тело запроса (строка, не dict!)
    body = f"scope={scope}"
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Отправляем как строку, чтобы точно ушел form-urlencoded
        async with session.post(AUTH_URL, data=body, headers=headers) as resp:
            response_text = await resp.text()
            
            # Логирование для отладки (скрываем секрет)
            print(f"🔍 Auth Request: POST {AUTH_URL}")
            print(f"🔑 Client ID Start: {config.GIGACHAT_CLIENT_ID[:5]}...")
            print(f"📡 Response Status: {resp.status}")
            print(f"📄 Response Body: {response_text}")
            
            if resp.status == 200:
                json_data = await resp.json()
                print("✅ Token received successfully")
                return json_data["access_token"]
            else:
                print(f"❌ GigaChat Auth Failed: {resp.status}")
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
        "model": "GigaChat",
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

