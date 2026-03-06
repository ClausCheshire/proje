# -*- coding: utf-8 -*-
import aiohttp
import config

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

async def get_gigachat_token():
    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(config.GIGACHAT_CLIENT_ID, config.GIGACHAT_CLIENT_SECRET)
        async with session.post(AUTH_URL, auth=auth, data={"scope": "GIGACHAT_API_PERS"}) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
            else:
                raise Exception(f"GigaChat auth error: {resp.status}")

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

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Включаем информацию об органе и регионе в запрос
    user_content = (
        f"Agency: {agency}\n"
        f"Region: {location}\n\n"
        f"Response text to analyze:\n{text}"
    )
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"Analysis service error: {resp.status}"
