import asyncio
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv(".env.local")
load_dotenv(".env")
load_dotenv("../.env.local")
load_dotenv("../.env")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai.gemini_provider import GeminiProvider
from app.core.config import settings

async def run_live_gemini_image_test():
    if os.getenv("ENABLE_GEMINI_LIVE_TEST", "false").lower() not in ("true", "1"):
        print("Live smoke test skipped. Set ENABLE_GEMINI_LIVE_TEST=true to run live image generation.")
        return

    provider = GeminiProvider()
    if not provider.is_configured:
        print("[ERROR] GEMINI_API_KEY is not configured in environment.")
        return

    print(f"Testing live Gemini image generation with model '{provider.image_model}'...")
    test_prompt = "Create a clean professional 1:1 advertising image for a modern SaaS marketing intelligence platform."

    try:
        result = await provider.generate_image(
            prompt=test_prompt,
            aspect_ratio="1:1"
        )
        data = result.get("data")
        mime_type = result.get("mime_type", "image/png")
        print(f"[SUCCESS] Image generated successfully! ({len(data)} bytes, mime: {mime_type})")

        # Save to scratch / output
        out_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "live_gemini_smoke_test.png")
        with open(out_file, "wb") as f:
            f.write(data)
        print(f"[SAVED] Saved live output image to {out_file}")

    except Exception as e:
        print(f"[FAILED] Live generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_live_gemini_image_test())
