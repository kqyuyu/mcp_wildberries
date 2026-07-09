import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


@dataclass
class Config:
    api_token: str
    sandbox_mode: bool
    yaml_file: Path
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "Config":
        env_path = Path(__file__).parent.parent.parent / ".env"
        load_dotenv(env_path)

        return cls(
            api_token=os.getenv("WILDBERRIES_API_TOKEN", ""),
            sandbox_mode=os.getenv("WILDBERRIES_SANDBOX", "false").lower() == "true",
            yaml_file=Path(os.getenv("WILDBERRIES_YAML_FILE", "data/02-items.yaml")),
            timeout=int(os.getenv("WILDBERRIES_TIMEOUT", "30")),
        )

    @property
    def domains(self) -> Dict[str, str]:
        if self.sandbox_mode:
            return {
                "content": "content-api-sandbox.wildberries.ru",
                "marketplace": "marketplace-api-sandbox.wildberries.ru",
                "feedbacks": "feedbacks-api-sandbox.wildberries.ru",
                "supplies": "supplies-api-sandbox.wildberries.ru",
                "advert": "advert-api-sandbox.wildberries.ru",
                "statistics": "statistics-api-sandbox.wildberries.ru",
                "discounts": "discounts-prices-api-sandbox.wildberries.ru",
            }
        return {
            "content": "content-api.wildberries.ru",
            "marketplace": "marketplace-api.wildberries.ru",
            "feedbacks": "feedbacks-api.wildberries.ru",
            "supplies": "supplies-api.wildberries.ru",
            "advert": "advert-api.wildberries.ru",
            "statistics": "statistics-api.wildberries.ru",
            "discounts": "discounts-prices-api.wildberries.ru",
        }

    def get_domain(self, path: str) -> str:
        path_lower = path.lower()

        if "feedback" in path_lower or "rating" in path_lower:
            return self.domains["feedbacks"]
        elif "content" in path_lower or "product" in path_lower or "card" in path_lower:
            return self.domains["content"]
        elif "marketplace" in path_lower or "order" in path_lower:
            return self.domains["marketplace"]
        elif "supply" in path_lower:
            return self.domains["supplies"]
        elif "advert" in path_lower or "campaign" in path_lower:
            return self.domains["advert"]
        elif "statistic" in path_lower or "report" in path_lower:
            return self.domains["statistics"]
        elif "discount" in path_lower or "price" in path_lower:
            return self.domains["discounts"]
        else:
            return self.domains["content"]