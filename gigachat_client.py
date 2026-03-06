# -*- coding: utf-8 -*-
import aiohttp
import config
import json

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

async def get_gigachat_token():
    data = {
        "scope": "GIGACHAT_API_PERS"
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        auth = aiohttp.BasicAuth(config.GIGACHAT_CLIENT_ID, config.GIGACHAT_CLIENT_SECRET)
        async with session.post(AUTH_URL, auth=auth, data=data) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
            else:
                error_text = await resp.text()
                raise Exception(f"GigaChat auth error: {resp.status} - {error_text}")

async def analyze_text(text: str, agency: str = "Unknown", location: str = "Unknown") -> str:
    token = await get_gigachat_token()
    
    system_prompt = (
        "You are a legal assistant specializing in Russian administrative law. "
        "Analyze the response from a government agency. Consider the agency type and region context. "
        "1. Summarize the main points of the response. "
        "2. Identify possible grounds for appeal (deadline violations, formal responses, "
        "unanswered questions, references to invalid regulations, jurisdiction issues). "
        "3. If no violations found, state that clearly. "
        "4. Keep the answer structured, concise, and professional. "
        "5. IMPORTANT: Add a disclaimer that this is not official legal advice."
    )

    payload = {
        "model": "GigaChat-2-Max",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Agency: {agency}\nRegion: {location}\n\nResponse text:\n{text}"}
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
                return f"Analysis service error: {resp.status} - {error_text}"
