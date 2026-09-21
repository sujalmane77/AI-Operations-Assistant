import sys, os
from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.agent.llm as llm_module
from app.agent.llm import call_llm
from app.agent.system_prompt import SYSTEM_PROMPT


def test_basic_completion():
    response = call_llm(
        messages=[{"role": "user", "content": "Say 'test ok' and nothing else."}],
        system_prompt=SYSTEM_PROMPT,
    )
    assert response and len(response) > 0
    print("LLM response:", response)


def test_gemini_fallback_on_groq_failure():
    with patch.object(llm_module, "_call_groq", side_effect=RuntimeError("simulated Groq outage")):
        response = call_llm(
            messages=[{"role": "user", "content": "Say 'fallback ok' and nothing else."}],
            system_prompt=SYSTEM_PROMPT,
            max_retries=0,
        )
    assert response and len(response) > 0
    print("Fallback LLM response:", response)


if __name__ == "__main__":
    test_basic_completion()
    test_gemini_fallback_on_groq_failure()
    print("test_llm.py: passed")
