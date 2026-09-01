import sys
import httpx
import asyncio

async def test_meta_api(token: str):
    url = f"https://graph.facebook.com/v26.0/me/accounts?access_token={token}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print("Status:", response.status_code)
        print("Response:", response.json())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(test_meta_api(sys.argv[1]))
    else:
        print("Please provide a token as argument")
