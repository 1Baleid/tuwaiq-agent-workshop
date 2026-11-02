"""
llm.py - talk to the LLM (every session uses this).

    import llm
    reply = llm.chat([{"role": "user", "content": "Say hello in Arabic"}])

Which LLM answers is decided by LLM_PROVIDER in config.py. All providers speak the same
"OpenAI-compatible" API, so this file never changes when you switch provider.
"""
import os
import sys
import time

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

import config

_clients = {}  # one client per provider, created the first time it is needed


def get_api_key(name):
    """Find an API key: the .env file or environment first, then Colab Secrets."""
    if name is None:  # local models need no key
        return "not-needed"
    from dotenv import load_dotenv
    load_dotenv(config.ROOT / ".env", override=True)  # copies the lines of .env into os.environ (if it exists)
    if os.environ.get(name):
        return os.environ[name]
    if "google.colab" in sys.modules:  # running inside a Colab notebook
        from google.colab import userdata
        try:
            return userdata.get(name)
        except Exception as e:  # secret missing, or "Notebook access" switched off
            raise RuntimeError(f"Colab could not read the secret {name} ({type(e).__name__}). Click the key "
                               f"icon on the left, add {name}, and switch 'Notebook access' on.") from None
    raise RuntimeError(f"No {name} found. Copy .env.example to .env and paste your key after {name}=")


def get_client():
    """The OpenAI-compatible client for the provider chosen in config.py."""
    name = config.LLM_PROVIDER
    provider = config.PROVIDERS[name]
    key = get_api_key(provider["key_name"])  # read every time, so a replaced key is used at once
    if name not in _clients or _clients[name].api_key != key:
        # max_retries=0: the library would quietly retry failed calls. We retry ourselves
        # (Session 4) so that you can see every failure and every retry.
        _clients[name] = OpenAI(base_url=provider["base_url"], api_key=key, max_retries=0)
    return _clients[name]


def chat(messages):
    """Send chat messages to the LLM and return its reply as text (one try, no retries)."""
    provider = config.PROVIDERS[config.LLM_PROVIDER]
    response = get_client().chat.completions.create(
        model=provider["model"],
        messages=messages,
        max_tokens=config.MAX_OUTPUT_TOKENS,
        timeout=config.LLM_TIMEOUT_SECONDS,  # give up on this call after this many seconds
        **provider.get("options", {}),
    )
    return response.choices[0].message.content or ""


# Errors worth trying again: too many requests (429), too slow, network problem, server error (5xx).
RETRY_ERRORS = (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)


def chat_with_retries(messages, log=print):
    """Like chat(), but when the call fails for a temporary reason, wait and try again
    (up to LLM_MAX_RETRIES times). Session 4."""
    # TODO (Session 4): call chat(); on a RETRY_ERRORS error wait (retry_wait) and try again, up to config.LLM_MAX_RETRIES times
    return chat(messages)  # no retries yet


def retry_wait(error, attempt):
    """Seconds to wait before the next try. If the server says how long (the Retry-After
    header on a 429), use that; otherwise wait 2, 4, 8... seconds (exponential backoff)."""
    response = getattr(error, "response", None)
    retry_after = response.headers.get("retry-after") if response is not None else None
    try:
        return min(float(retry_after), 60)
    except (TypeError, ValueError):
        return 2 ** (attempt + 1)
