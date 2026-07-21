import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")
    
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    MEM0_API_KEY: str = os.getenv("MEM0_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Parse MCP Servers
    mcp_servers_raw: str = os.getenv("MCP_SERVERS", "[]")
    try:
        MCP_SERVERS: list = json.loads(mcp_servers_raw)
    except Exception:
        MCP_SERVERS: list = []

    # Detect if we should run in Mock Mode for LLM / APIs
    @property
    def is_mock_mode(self) -> bool:
        return not self.OPENAI_API_KEY or self.OPENAI_API_KEY.startswith("mock-")

settings = Settings()
