import logging
from slack_sdk import WebClient
from .config import Config

logger = logging.getLogger(__name__)

class ThreadResolver:
    """Logic for fetching and formatting Slack threads into a structured transcript."""

    def __init__(self):
        self.client = WebClient(token=Config.SLACK_BOT_TOKEN)

    def resolve_thread(self, channel_id: str, thread_ts: str) -> str:
        """
        Fetches all messages in a Slack thread and formats them as a transcript.

        :param channel_id: The Slack Channel ID
        :param thread_ts: The timestamp of the parent message
        :return: A formatted string transcript of the conversation
        """
        try:
            # Fetch thread replies
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )

            messages = result.get("messages", [])
            if not messages:
                return ""

            transcript_lines = []
            for msg in messages:
                user_id = msg.get("user", "System/Bot")
                text = msg.get("text", "")

                # Basic user resolution could be added here to get real names,
                # but for now we use User IDs for stability.
                transcript_lines.append(f"[{user_id}]: {text}")

            return "\n".join(transcript_lines)

        except Exception as e:
            logger.error(f"Error resolving thread {thread_ts} in channel {channel_id}: {e}")
            return ""
