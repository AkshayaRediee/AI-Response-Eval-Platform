"""
Wraps the OpenAI call. If no OPENAI_API_KEY is set, falls back to canned
demo responses so the app is fully clickable/screenshot-able out of the box.
"""
import os

DEMO_MODE = not bool(os.getenv("OPENAI_API_KEY"))

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_DEMO_RESPONSES = [
    "The Krebs cycle (citric acid cycle) takes place in the mitochondrial matrix and "
    "generates NADH and FADH2 for the electron transport chain. It runs eight steps "
    "per turn, starting with acetyl-CoA combining with oxaloacetate to form citrate.",
    "A load balancer distributes incoming requests across multiple servers so no single "
    "instance is overwhelmed. Common algorithms include round robin, least connections, "
    "and IP hashing.",
    "France's population is approximately 68 million as of the most recent estimates.",
    "To reverse a linked list iteratively, walk the list while re-pointing each node's "
    "`next` to the previous node, tracking `prev`, `curr`, and `next` pointers.",
]


def generate_response(prompt: str, model: str = DEFAULT_MODEL) -> tuple[str, str]:
    """Returns (response_text, model_used)."""
    if DEMO_MODE:
        import hashlib
        idx = int(hashlib.sha256(prompt.encode()).hexdigest(), 16) % len(_DEMO_RESPONSES)
        return (
            f"[DEMO MODE — no OPENAI_API_KEY set] {_DEMO_RESPONSES[idx]}",
            f"{model} (demo)",
        )

    from openai import OpenAI
    client = OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return completion.choices[0].message.content, model
