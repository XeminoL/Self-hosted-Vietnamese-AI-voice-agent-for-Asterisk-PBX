import hashlib
import json
import time
import urllib.error
import urllib.request
from collections import namedtuple

from accounts import LOOKUPS
from domain import PHRASES, PROMPT_TEMPLATE
from knowledge import topic_names

LLM_BASE = "http://127.0.0.1:8080"
CHAT_URL = LLM_BASE + "/v1/chat/completions"
WARM_SLOT = 0
MAX_REPLY_TOKENS = 20
TEMPERATURE = 0
REMEMBERED_TURNS = 4
TOPIC_SLOT = "{topics}"
LOOKUP_SLOT = "{lookups}"
TOPIC_SEPARATOR = " · "
LOOKUP_SEPARATOR = "|"

ModelReply = namedtuple("ModelReply", "text cut_off timings")


def system_prompt():
    return (PROMPT_TEMPLATE
            .replace(TOPIC_SLOT, TOPIC_SEPARATOR.join(topic_names()))
            .replace(LOOKUP_SLOT, LOOKUP_SEPARATOR.join(LOOKUPS)))


def ask(history, slot=None):
    body = {
        "messages": [{"role": "system", "content": system_prompt()}] + history[-REMEMBERED_TURNS:],
        "max_tokens": MAX_REPLY_TOKENS,
        "temperature": TEMPERATURE,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if slot is not None:
        body["id_slot"] = slot
    request = urllib.request.Request(CHAT_URL, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())
    choice = result["choices"][0]
    return ModelReply(choice["message"]["content"].strip(), choice.get("finish_reason") == "length",
                      result.get("timings", {}))


def _call(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(LLM_BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, ValueError):
        return None


def _saved_prompt_name():
    models = _call("/v1/models") or {}
    model = (models.get("data") or [{}])[0].get("id", "")
    return "prompt-" + hashlib.sha1((model + system_prompt()).encode("utf-8")).hexdigest()[:16] + ".bin"


def warm_up():
    name = _saved_prompt_name()
    started = time.monotonic()
    restored = _call(f"/slots/{WARM_SLOT}?action=restore", {"filename": name}) or {}
    if restored.get("n_restored"):
        return f"restored from disk in {time.monotonic() - started:.1f}s"
    timings = ask([{"role": "user", "content": PHRASES["for_the_model"]["warm_up"]}], WARM_SLOT).timings
    saved = _call(f"/slots/{WARM_SLOT}?action=save", {"filename": name}) is not None
    return describe_timings(timings) + (", saved to disk for next time" if saved else "")


def describe_timings(timings):
    if not timings:
        return ""
    return (f"prompt {timings.get('prompt_n', 0)} tok in {timings.get('prompt_ms', 0) / 1000:.1f}s, "
            f"reply {timings.get('predicted_n', 0)} tok in {timings.get('predicted_ms', 0) / 1000:.1f}s, "
            f"cached {timings.get('cache_n', 0)}")
