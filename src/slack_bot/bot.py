import os
import logging
import asyncio
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import Config
from .client import SlackClient
from .resolver import ThreadResolver

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SlackBot")

# Initialize Bolt App
app = App(token=Config.SLACK_BOT_TOKEN)
slack_client = SlackClient()
thread_resolver = ThreadResolver()

# Map of reaction emojis to tags
REACTION_MAP = {
    "books": "Knowledge",    # 📚
    "white_check_mark": "Decision", # ✅
    "memo": "Action"         # 📝
}

async def capture_to_mcp(domain_id, ts, text, tag):
    """Helper to send captured content to the MCP server."""
    concept = f"slack_msg_{ts}"
    try:
        result = await slack_client.save_memory(
            domain=domain_id,
            concept=concept,
            value=text,
            tags=tag
        )
        logger.info(f"Successfully captured {tag} from {domain_id}: {concept}")
        return True
    except Exception as e:
        logger.error(f"Failed to capture content to MCP: {e}")
        return False

@app.event("reaction_added")
def handle_reaction_added(event, say, client):
    """Handles emoji reactions as triggers for knowledge capture."""
    emoji = event.get("reaction")
    item_user = event.get("user")
    item = event.get("item") # contains type and channel/ts

    if emoji not in REACTION_MAP:
        return

    tag = REACTION_MAP[emoji]
    domain_id = item.get("channel")
    ts = item.get("ts")

    # Use asyncio to call the async client from a sync Bolt handler
    loop = asyncio.get_event_loop()

    def process():
        # Resolve content: If it's a thread, get the whole thing, otherwise just the message
        try:
            replies = client.conversations_replies(channel=domain_id, ts=ts)
            if len(replies.get("messages", [])) > 1:
                content = thread_resolver.resolve_thread(domain_id, ts)
                logger.info(f"Capturing thread as {tag}")
            else:
                # Just the single message text
                msg_data = client.conversations_replies(channel=domain_id, ts=ts)["messages"][0]
                content = msg_data.get("text", "")
                logger.info(f"Capturing single message as {tag}")

            # Store in MCP
            loop.run_until_complete(capture_to_mcp(domain_id, ts, content, tag))

            # Confirm to user in thread
            say(text=f"Captured as {tag}!", thread_ts=ts)
        except Exception as e:
            logger.error(f"Error in reaction handler: {e}")

    process()

@app.event("app_mention")
def handle_mention(event, say, client):
    """Handles @bot mentions for 'Deep Context' capture."""
    domain_id = event.get("channel")
    ts = event.get("ts")

    loop = asyncio.get_event_loop()

    def process():
        try:
            # Mentions usually imply the current thread should be saved
            content = thread_resolver.resolve_thread(domain_id, ts)
            loop.run_until_complete(capture_to_mcp(domain_id, ts, content, "DeepContext"))
            say(text="Deep context captured and stored in knowledge base! 🚀", thread_ts=ts)
        except Exception as e:
            logger.error(f"Error in mention handler: {e}")

    process()

if __name__ == "__main__":
    # Initialize SocketModeHandler for easy local development
    handler = SocketModeHandler(app, Config.SLACK_APP_TOKEN)
    logger.info("Slack Knowledge Harvester Bot is starting...")
    handler.start()
