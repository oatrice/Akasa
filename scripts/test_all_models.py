
import asyncio
import sys
import os

# เพิ่ม project root เข้า sys.path เพื่อให้ import app ได้
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services import llm_service

# Note: Renamed to _test_model to prevent pytest from discovering it as a test
async def _test_model(alias, identifier):
    print(f"Testing model: {alias} ({identifier})...", end=" ", flush=True)
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Reply with only one word: 'Success'."},
        {"role": "user", "content": "Hello"}
    ]
    try:
        reply = await llm_service.get_llm_reply(messages, model=identifier)
        if "success" in reply.lower():
            print("✅ PASS")
            return True
        else:
            print(f"⚠️ UNEXPECTED REPLY: {reply}")
            return False
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        return False

async def main():
    print("=== Akasa Multi-Model Connectivity Test ===")
    print(f"Environment: {settings.ENVIRONMENT}")
    
    results = []
    for alias, info in settings.AVAILABLE_MODELS.items():
        success = await _test_model(alias, info["identifier"])
        results.append((alias, success))
        # หน่วงเวลาเล็กน้อยเพื่อเลี่ยง rate limit
        await asyncio.sleep(1)

    print("\n=== Summary ===")
    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed < total:
        print("Failed models:")
        for alias, success in results:
            if not success:
                print(f"- {alias}")

if __name__ == "__main__":
    asyncio.run(main())
