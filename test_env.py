from app.config import settings
print("OPENROUTER:", bool(settings.OPENROUTER_API_KEY))
print("TELEGRAM:", bool(settings.TELEGRAM_BOT_TOKEN))
