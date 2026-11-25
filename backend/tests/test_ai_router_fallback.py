"""AI router: Groq first, then Gemini; both failing raises with both reasons."""
import asyncio

import pytest

from app.services.ai.ai_router import MultiTierAIProvider


class Fake:
    def __init__(self, model, result=None, error=None):
        self.model, self.result, self.error, self.calls = model, result, error, 0

    async def _call_api(self, messages):
        self.calls += 1
        if self.error:
            raise RuntimeError(self.error)
        return self.result


def make(groq, gemini):
    p = MultiTierAIProvider()
    p.groq, p.gemini = groq, gemini
    return p


def run(p):
    return asyncio.run(p._call_api([{"role": "user", "content": "hi"}]))


def test_groq_answers_and_gemini_is_not_called():
    g, m = Fake("llama", "from groq"), Fake("flash", "from gemini")
    p = make(g, m)
    assert run(p) == "from groq" and p.model == "llama" and m.calls == 0


def test_gemini_answers_when_groq_fails():
    p = make(Fake("llama", error="rate limited"), Fake("flash", "from gemini"))
    assert run(p) == "from gemini" and p.model == "gemini/flash"


def test_both_failing_raises_with_both_reasons():
    p = make(Fake("llama", error="groq down"), Fake("flash", error="gemini down"))
    with pytest.raises(Exception) as exc:
        run(p)
    assert "groq down" in str(exc.value) and "gemini down" in str(exc.value)
    assert not hasattr(p, "openrouter")
