import unicodedata

from domain import WORDS

PUNCTUATION = ",.!?;:"
OLD_TONE_PLACEMENT = {
    "òa": "oà", "óa": "oá", "ỏa": "oả", "õa": "oã", "ọa": "oạ",
    "òe": "oè", "óe": "oé", "ỏe": "oẻ", "õe": "oẽ", "ọe": "oẹ",
    "ùy": "uỳ", "úy": "uý", "ủy": "uỷ", "ũy": "uỹ", "ụy": "uỵ",
}


def normalize(text):
    text = unicodedata.normalize("NFC", text.lower())
    for old, new in OLD_TONE_PLACEMENT.items():
        text = text.replace(old, new)
    for mark in PUNCTUATION:
        text = text.replace(mark, " ")
    return " ".join(text.split())


def phrases_said(sentence, phrases):
    padded = f" {normalize(sentence)} "
    return [phrase for phrase in phrases if f" {normalize(phrase)} " in padded]


def says_any(sentence, phrases):
    return bool(phrases_said(sentence, phrases))


def without_phrases(sentence, phrases):
    padded = f" {normalize(sentence)} "
    for phrase in sorted(phrases, key=len, reverse=True):
        padded = padded.replace(f" {normalize(phrase)} ", " ")
    return padded.strip()


def word_count(sentence):
    return len(normalize(sentence).split())


def _starts_with(words, phrase):
    phrase_words = normalize(phrase).split()
    return words[:len(phrase_words)] == phrase_words


def is_objection(sentence):
    words = normalize(sentence).split()
    for filler in WORDS["fillers"]:
        if _starts_with(words, filler):
            words = words[len(normalize(filler).split()):]
    opens_with_objection = any(_starts_with(words, opening) for opening in WORDS["objection_openings"])
    return opens_with_objection or says_any(sentence, WORDS["objection_anywhere"])


def asks_for_staff(sentence):
    return says_any(sentence, WORDS["asks_for_staff"]) and not says_any(sentence, WORDS["identity_questions"])


def accepts_staff(sentence):
    if asks_for_staff(sentence):
        return True
    return says_any(sentence, WORDS["staff_yes"]) and not says_any(sentence, WORDS["staff_no"])


def consented(sentence):
    return says_any(sentence, WORDS["confirm_yes"]) and not says_any(sentence, WORDS["confirm_no"])


def asks_about_own_account(sentence):
    return says_any(sentence, WORDS["own_account"])
