import json
from pathlib import Path

DOMAIN_DIR = Path(__file__).resolve().parent / "domain"


def load_json(name):
    return json.loads((DOMAIN_DIR / name).read_text(encoding="utf-8"))


PHRASES = load_json("phrases.json")
WORDS = load_json("words.json")
MENU = load_json("menu.json")
PROMPT_TEMPLATE = (DOMAIN_DIR / "prompt.txt").read_text(encoding="utf-8").strip()
