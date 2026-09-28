import json
import os

from caller_words import phrases_said
from domain import DOMAIN_DIR

TOPICS_FILE = DOMAIN_DIR / "topics.json"
FIGURES_FILE = DOMAIN_DIR / "figures.json"

_loaded = {}
_next_answer = {}


def _read(path):
    path = str(path)
    if not os.path.exists(path):
        return {}
    modified = os.path.getmtime(path)
    cached = _loaded.get(path)
    if cached and cached[0] == modified:
        return cached[1]
    with open(path, encoding="utf-8") as handle:
        content = json.load(handle)
    _loaded[path] = (modified, content)
    return content


def topic_names():
    return list(_read(TOPICS_FILE))


def keywords_heard(sentence, topic):
    return phrases_said(sentence, _read(TOPICS_FILE).get(topic, {}).get("keywords", ()))


def find_topic(sentence, skip=None):
    scores = {
        name: sum(len(keyword) for keyword in keywords_heard(sentence, name))
        for name in topic_names()
        if name != skip
    }
    best = max(scores, key=scores.get, default=None)
    return best if best and scores[best] else None


def _fill_figures(answer):
    for name, value in _read(FIGURES_FILE).items():
        answer = answer.replace("{" + name + "}", str(value))
    return answer


def answers(topic):
    topic_entry = _read(TOPICS_FILE).get(topic)
    return [_fill_figures(answer) for answer in topic_entry["answers"]] if topic_entry else []


def answer(topic):
    choices = answers(topic)
    if not choices:
        return None
    turn = _next_answer.get(topic, 0) % len(choices)
    _next_answer[topic] = turn + 1
    return choices[turn]
