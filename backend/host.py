import httpx


async def get_public_ip() -> str | None:
    """Return the public IP address of the host as a string."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.ipify.org?format=json", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            return data.get("ip")
    except Exception:
        return None
