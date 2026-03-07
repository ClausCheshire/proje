async def get_gigachat_token():
    """Получение токена через OAuth (Client ID + Client Secret)"""
    current_time = time.time()
    
    # Проверяем кэш — если токен ещё валиден, возвращаем его
    if _token_cache["token"] and current_time < _token_cache["expires_at"]:
        print(f"✅ [AUTH] Using cached token (expires in {_token_cache['expires_at'] - current_time:.0f}s)")
        return _token_cache["token"]
    
    print("=" * 60)
    print("🔑 [AUTH] Requesting new token from SberCloud...")
    print("=" * 60)
    print(f"🔑 [AUTH] Client ID: {config.GIGACHAT_CLIENT_ID[:10]}...{config.GIGACHAT_CLIENT_ID[-5:]}")
    print(f"🔑 [AUTH] Client Secret length: {len(config.GIGACHAT_CLIENT_SECRET)}")
    print(f"🔑 [AUTH] Auth URL: {AUTH_URL}")
    print("=" * 60)
    
    # Пробуем scope по очереди (PERS сначала, потом обычный)
    scopes_to_try = ["GIGACHAT_API_PERS", "GIGACHAT_API"]
    
    for scope in scopes_to_try:
        print(f"\n🔑 [AUTH] Trying scope: {scope}")
        print("-" * 60)
        
        # Формируем Basic Auth
        credentials = f"{config.GIGACHAT_CLIENT_ID}:{config.GIGACHAT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        # ТОЛЬКО scope, БЕЗ RqUID (RqUID нужен только для /chat/completions)
        data = {"scope": scope}
        
        print(f"📤 [AUTH] Request headers: Content-Type={headers['Content-Type']}")
        print(f"📤 [AUTH] Request data: scope={scope}")
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        try:
            async with aiohttp.ClientSession(connector=connector, timeout=AUTH_TIMEOUT) as session:
                async with session.post(AUTH_URL, data=data, headers=headers) as resp:
                    response_text = await resp.text()
                    
                    print(f"📡 [AUTH] Response Status: {resp.status}")
                    print(f"📡 [AUTH] Response Headers: {dict(resp.headers)}")
                    print(f"📡 [AUTH] Response Body: {response_text}")
                    print("-" * 60)
                    
                    if resp.status == 200:
                        try:
                            json_data = await resp.json()
                            access_token = json_data["access_token"]
                            expires_in = json_data.get("expires_in", 1800)
                            
                            # Сохраняем в кэш (с запасом 5 минут)
                            _token_cache["token"] = access_token
                            _token_cache["expires_at"] = current_time + expires_in - 300
                            
                            print(f"✅ [AUTH] Token received with scope '{scope}'")
                            print(f"✅ [AUTH] Token expires in: {expires_in - 300}s")
                            print(f"✅ [AUTH] Token starts with: {access_token[:20]}...")
                            print("=" * 60)
                            return access_token
                        except Exception as json_err:
                            print(f"❌ [AUTH] Failed to parse JSON response: {json_err}")
                            print(f"❌ [AUTH] Raw response: {response_text}")
                            raise Exception(f"Invalid JSON response: {json_err}")
                    else:
                        print(f"❌ [AUTH] Failed with scope '{scope}': HTTP {resp.status}")
                        
                        # Пытаемся распарсить ошибку в JSON формате
                        try:
                            error_json = await resp.json()
                            print(f"❌ [AUTH] Error JSON: {error_json}")
                            error_code = error_json.get("error", "unknown")
                            error_desc = error_json.get("error_description", "No description")
                            print(f"❌ [AUTH] Error Code: {error_code}")
                            print(f"❌ [AUTH] Error Description: {error_desc}")
                        except:
                            print(f"❌ [AUTH] Error Body (plain text): {response_text}")
                        
                        # Если это был последний scope — выбрасываем ошибку
                        if scope == scopes_to_try[-1]:
                            print("=" * 60)
                            print("❌ [AUTH] GigaChat auth failed with all scopes")
                            print("=" * 60)
                            print("💡 [AUTH] Troubleshooting:")
                            print("  1. Check IAM → Applications → OAuth Client (not API Key)")
                            print("  2. Check role 'gigachat.ai.user' is assigned")
                            print("  3. Check for spaces/quotes in Railway Variables")
                            print("  4. Try curl test from documentation")
                            print("=" * 60)
                            raise Exception(
                                f"GigaChat auth failed: HTTP {resp.status}\n"
                                f"Error: {response_text[:500]}\n"
                                f"Check: 1) OAuth Client in IAM, 2) Role assigned, 3) No spaces in keys"
                            )
                        else:
                            print(f"⚠️ [AUTH] Will try next scope: {scopes_to_try[scopes_to_try.index(scope) + 1]}")
                        
        except asyncio.TimeoutError:
            print(f"⏰ [AUTH] Timeout with scope '{scope}' (>{AUTH_TIMEOUT.total}s)")
            if scope == scopes_to_try[-1]:
                raise Exception("GigaChat auth timeout. Check network connection.")
        except aiohttp.ClientConnectionError as conn_err:
            print(f"🔌 [AUTH] Connection error with scope '{scope}': {conn_err}")
            if scope == scopes_to_try[-1]:
                raise Exception(f"Connection failed: {conn_err}")
        except Exception as e:
            print(f"⚠️ [AUTH] Unexpected error with scope '{scope}': {type(e).__name__}: {str(e)}")
            if scope == scopes_to_try[-1]:
                raise
        finally:
            await connector.close()
    
    # Если оба scope не сработали
    raise Exception("GigaChat auth failed with all scopes. Check credentials in SberCloud.")
