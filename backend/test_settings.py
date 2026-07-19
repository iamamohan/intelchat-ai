from app.config import settings

print("Key Length :", len(settings.GEMINI_API_KEY or ""))
print("Key Prefix :", (settings.GEMINI_API_KEY or "")[:5])
print("Provider   :", settings.LLM_PROVIDER)
print("Model      :", settings.LLM_MODEL)