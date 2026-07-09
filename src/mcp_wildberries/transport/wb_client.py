"""HTTP клиент для Wildberries API"""

import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WBClient:
    """Клиент для Wildberries API"""

    def __init__(self, token: str, timeout: int = 30):
        self.token = token
        self.timeout = timeout

    async def call(
            self,
            method: str,
            url: str,
            params: Optional[Dict] = None,
            json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Вызывает API метод"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json_data,
                )
                response.raise_for_status()

                if response.text:
                    return response.json()
                return {"status": response.status_code, "message": "Success"}

        except httpx.TimeoutException:
            logger.error(f"Timeout calling {url}")
            raise TimeoutError(f"Request to {url} timed out")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"API error {e.response.status_code}: {e.response.text}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise