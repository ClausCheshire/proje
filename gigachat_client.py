# -*- coding: utf-8 -*-
import aiohttp
import config
import base64
import asyncio

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Таймауты для запросов (секунды)
AUTH_TIMEOUT = aiohttp.ClientTimeout(total=30)
CHAT_TIMEOUT = aiohttp.ClientTimeout(total=120)  # Анализ может занимать время

async def get_gigachat_token():
    scopes_to_try = ["GIGACHAT_API_PERS", "GIGACHAT_API"]
    
    credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    
    base_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    for scope in scopes_to_try:
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector, timeout=AUTH_TIMEOUT) as session:
            data = {"scope": scope}
            try:
                print(f"🔍 Auth attempt with scope: {scope}")
                async with session.post(AUTH_URL, data=data, headers=base_headers) as resp:
                    response_text = await resp.text()
                    print(f"📡 Auth Status: {resp.status}, Body: '{response_text[:200]}'")
                    
                    if resp.status == 200:
                        json_data = await resp.json()
                        print(f"✅ Token received")
                        return json_data["access_token"]
                    else:
                        print(f"❌ Auth failed with scope {scope}")
            except asyncio.TimeoutError:
                print(f"⏰ Auth timeout with scope {scope}")
            except Exception as e:
                print(f"⚠️ Auth error with scope {scope}: {type(e).__name__}: {e}")
            finally:
                await connector.close()
    
    raise Exception("GigaChat auth failed with all scopes. Check credentials in SberCloud.")

async def analyze_text(text: str, agency: str = "Unknown", location: str = "Unknown") -> str:
    print(f"🚀 Starting analyze_text() for agency={agency}, location={location}")
    
    try:
        token = await get_gigachat_token()
        print("✅ Got token, preparing chat request")
    except Exception as e:
        print(f"❌ Failed to get token: {e}")
        return f"❌ Authentication error: {e}. Check your SberCloud credentials."
    
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
            {"role": "user", "content": f"Agency: {agency}\nRegion: {location}\n\nText:\n{text[:2000]}"}  # Обрезаем слишком длинные тексты
        ],
        "profanity_check": True
    }

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    connector = aiohttp.TCPConnector(ssl=False)
    
    try:
        print("📤 Sending request to GigaChat API...")
        async with aiohttp.ClientSession(connector=connector, timeout=CHAT_TIMEOUT) as session:
            async with session.post(CHAT_URL, json=payload, headers=headers) as resp:
                response_text = await resp.text()
                print(f"📡 Chat Status: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    result = data["choices"][0]["message"]["content"]
                    print(f"✅ Received result, length: {len(result)}")
                    return result
                else:
                    print(f"❌ Chat API error: {resp.status} - {response_text[:200]}")
                    return f"❌ GigaChat API error: {resp.status}. Response: {response_text[:200]}"
    except asyncio.TimeoutError:
        print("⏰ Chat request timed out")
        return "⏰ Request timed out. The analysis is taking too long. Try again with a shorter text."
    except Exception as e:
        print(f"⚠️ Chat request error: {type(e).__name__}: {e}")
        return f"❌ Error during analysis: {type(e).__name__}: {e}"
    finally:
        await connector.close()
        print("🔌 Connector closed")

