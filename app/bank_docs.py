import json
import os

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
TOPICS_FILE = os.path.join(DOCS_DIR, "topics.json")
FIGURES_FILE = os.path.join(DOCS_DIR, "figures.json")

_cache = {"topics": {}, "figures": {}, "mtime": {}}
_next_phrasing = {}


def _read_if_changed(path, key):
    if not os.path.exists(path):
        return _cache[key]
    mtime = os.path.getmtime(path)
    if _cache["mtime"].get(key) == mtime:
        return _cache[key]
    with open(path, encoding="utf-8") as f:
        _cache[key] = json.load(f)
    _cache["mtime"][key] = mtime
    return _cache[key]


def available_topics():
    return list(_read_if_changed(TOPICS_FILE, "topics").keys())


def find_topic_by_keyword(caller_sentence, skip=None):
    sentence = caller_sentence.lower()
    topics = _read_if_changed(TOPICS_FILE, "topics")
    matches = [
        (len(word), name)
        for name, topic in topics.items()
        if name != skip
        for word in topic.get("keywords", ())
        if word.lower() in sentence
    ]
    if not matches:
        return None
    return max(matches)[1]


def _fill_figures(sentence):
    figures = _read_if_changed(FIGURES_FILE, "figures")
    for figure, value in figures.items():
        sentence = sentence.replace("{" + figure + "}", str(value))
    return sentence


def topic_phrasings(name):
    topics = _read_if_changed(TOPICS_FILE, "topics")
    if name not in topics:
        return []
    return [_fill_figures(sentence) for sentence in topics[name]["answers"]]


def read_topic(name):
    phrasings = topic_phrasings(name)
    if not phrasings:
        return None
    turn = _next_phrasing.get(name, 0) % len(phrasings)
    _next_phrasing[name] = turn + 1
    return phrasings[turn]
