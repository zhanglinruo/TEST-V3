from app.core.openai_client import get_openai_client
from app.core.config import settings


def generate_sql(question: str, semantic_context: str) -> str:
    # Placeholder. Replace with a real prompt and function calling later.
    client = get_openai_client()
    _ = client
    _ = settings
    _ = semantic_context
    return "SELECT 1 AS placeholder"

