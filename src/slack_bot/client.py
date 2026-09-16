import httpx
import logging
from .config import Config

logger = logging.getLogger(__name__)

class SlackClient:
    """Interface for communicating with the FastAPI MCP Server."""

    def __init__(self):
        self.base_url = Config.API_BASE_URL
        self.api_key = Config.MCP_API_KEY
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["X-API-KEY"] = self.api_key

    async def save_memory(self, domain: str, concept: str, value: str, tags: str = None, ttl_seconds: int = 0):
        """
        Pushes captured Slack content to the MCP project memory.

        :param domain: The Slack Channel ID
        :param concept: Unique key (e.g., slack_msg_{ts})
        :param value: The text content to store
        :param tags: Comma-separated tags (e.g., 'Knowledge,Decision')
        :param ttl_seconds: Time-to-live in seconds (0 for permanent)
        """
        url = f"{self.base_url}/memory/save"
        payload = {
            "domain": domain,
            "concept": concept,
            "value": value,
            "tags": tags,
            "ttl_seconds": ttl_seconds
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred while saving memory: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred while saving memory: {e}")
            raise
