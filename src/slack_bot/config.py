import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # Slack API Tokens
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN") # Used for Socket Mode

    # FastAPI MCP Server
    # Default to localhost:8000 if not provided
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip('/')
    MCP_API_KEY = os.getenv("MCP_API_KEY")

    @classmethod
    def validate(cls):
        missing = []
        if not cls.SLACK_BOT_TOKEN: missing.append("SLACK_BOT_TOKEN")
        if not cls.SLACK_SIGNING_SECRET: missing.append("SLACK_SIGNING_SECRET")
        if not cls.SLACK_APP_TOKEN: missing.append("SLACK_APP_TOKEN")

        if missing:
            raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

Config.validate()
