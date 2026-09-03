import unicodedata

BANKING_TERMS = (
    "số dư", "tài khoản", "hạn mức", "giao dịch", "chuyển khoản",
    "số điện thoại", "nhân viên",
)
MAX_EDIT_DISTANCE = 2


def _strip_accents(text):
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (char_a != char_b),
            ))
        previous = current
    return previous[-1]


def fix_near_homophones(sentence):
    words = sentence.split()
    for term in BANKING_TERMS:
        term_length = len(term.split())
        for position in range(len(words) - term_length + 1):
            span = " ".join(words[position:position + term_length])
            if span.lower() == term:
                continue
            if _edit_distance(_strip_accents(span), _strip_accents(term)) <= MAX_EDIT_DISTANCE:
                words[position:position + term_length] = term.split()
                break
    return " ".join(words)