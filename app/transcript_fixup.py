import unicodedata

from domain import WORDS

TERMS = WORDS["misheard_terms"]
REAL_PHRASES = WORDS["real_phrases_that_look_misheard"]
LONG_TERM_EDIT_DISTANCE = 2
SHORT_TERM_EDIT_DISTANCE = 1
SHORT_TERM_LETTERS = 8


def _strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _edit_distance(first, second):
    if len(first) < len(second):
        first, second = second, first
    previous = list(range(len(second) + 1))
    for i, first_char in enumerate(first, start=1):
        current = [i]
        for j, second_char in enumerate(second, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (first_char != second_char)))
        previous = current
    return previous[-1]


def _allowed_distance(plain_term):
    return SHORT_TERM_EDIT_DISTANCE if len(plain_term) < SHORT_TERM_LETTERS else LONG_TERM_EDIT_DISTANCE


def fix_near_homophones(sentence):
    words = sentence.split()
    for term in TERMS:
        term_words = len(term.split())
        plain_term = _strip_accents(term)
        for position in range(len(words) - term_words + 1):
            span = " ".join(words[position:position + term_words])
            if span.lower() == term or span.lower() in REAL_PHRASES:
                continue
            if _edit_distance(_strip_accents(span), plain_term) <= _allowed_distance(plain_term):
                words[position:position + term_words] = term.split()
                break
    return " ".join(words)
