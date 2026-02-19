import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EndpointVerify")

BASE_URL = "http://127.0.0.1:8001"

async def check_endpoint(client, path, method="GET", payload=None):
    try:
        if method == "GET":
            response = await client.get(f"{BASE_URL}{path}")
        else:
            response = await client.post(f"{BASE_URL}{path}", json=payload)
        
        logger.info(f"{method} {path}: {response.status_code}")
        if response.status_code == 404:
            logger.error(f"Endpoint {path} NOT FOUND")
        elif response.status_code >= 500:
            logger.error(f"Endpoint {path} SERVER ERROR: {response.text}")
        else:
            logger.info(f"Response: {response.text[:100]}...")
            return True
    except Exception as e:
        logger.error(f"{method} {path} FAILED: {str(e)}")
        return False

async def main():
    async with httpx.AsyncClient() as client:
        # Check /search
        await check_endpoint(client, "/search", "POST", {"query": "test", "location": "Kenya"})
        
        # Check /leads
        await check_endpoint(client, "/leads")
        
        # Check /scrapers
        await check_endpoint(client, "/scrapers")
        
        # Check /settings
        await check_endpoint(client, "/settings", "GET", None) # Admin route might need key

if __name__ == "__main__":
    asyncio.run(main())
