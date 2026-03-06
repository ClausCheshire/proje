# -*- coding: utf-8 -*-
import aiohttp
import config
import base64

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

async def get_gigachat_token():
    # Пробуем scope по очереди
    scopes_to_try = ["GIGACHAT_API_PERS", "GIGACHAT_API"]
    
    # Формируем Basic Auth вручную один раз
    credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    base_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    for scope in scopes_to_try:
        # Создаем НОВЫЕ коннектор и сессию для каждой попытки
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            data = {"scope": scope}
            try:
                async with session.post(AUTH_URL, data=data, headers=base_headers) as resp:
                    response_text = await resp.text()
                    
                    print(f"🔍 Trying scope: {scope}")
                    print(f"📡 Status: {resp.status}")
                    print(f"📄 Body: '{response_text}'")
                    
                    if resp.status == 200:
                        json_data = await resp.json()
                        print(f"✅ Token received with scope: {scope}")
                        return json_data["access_token"]
                    else:
                        print(f"❌ Failed with scope: {scope}")
            except Exception as e:
                print(f"⚠️ Error with scope {scope}: {e}")
            finally:
                # Явно закрываем коннектор
                await connector.close()
    
    # Если оба scope не сработали
    raise Exception("GigaChat auth failed with all scopes. Check your credentials.")

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
