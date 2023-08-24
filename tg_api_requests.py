import aiohttp


async def get_bot_info(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response_json = await response.json()

                if response_json["ok"]:
                    return response_json["result"]['username']
                else:
                    print("Error occurred while getting bot info:")
                    print(response_json)
    except aiohttp.ClientError as e:
        print("Error occurred while sending the request:", e)

    return None


async def check_token_validity(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getMe"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response_json = await response.json()

                if response_json["ok"]:
                    return response_json["result"]
                else:
                    print("Error occurred while getting bot info:")
                    print(response_json)
    except aiohttp.ClientError as e:
        print("Error occurred while sending the request:", e)

    return


