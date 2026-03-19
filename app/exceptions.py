"""
Custom, application-specific exceptions.
"""

class UserChatIdNotFoundException(Exception):
    """Raised when the chat_id for a given user_id cannot be found."""
    pass

class BotBlockedException(Exception):
    """Raised when a message fails because the user has blocked the bot."""
    pass


class LLMTimeoutError(Exception):
    """Raised when an LLM request times out."""


class LLMUpstreamError(Exception):
    """Raised when an upstream LLM provider returns an error."""


class LLMMalformedResponseError(Exception):
    """Raised when the LLM provider returns an unusable payload."""
