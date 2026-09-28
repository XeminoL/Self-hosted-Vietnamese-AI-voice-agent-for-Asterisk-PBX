import unicodedata

TAG_LOOKUP = "@LOOKUP"
TAG_TRANSFER = "@TRANSFER"
TAG_DOC = "@DOC"
TAGS = (TAG_LOOKUP, TAG_DOC, TAG_TRANSFER)
ARGUMENT_TRIM = "[](){}<>:,."


def _plain(name):
    letters = unicodedata.normalize("NFD", name.lower().replace("đ", "d"))
    return "".join(c for c in letters if not unicodedata.combining(c))


def match_known_name(written, known_names):
    plain = _plain(written)
    starts = [name for name in known_names if plain.startswith(name)]
    return max(starts, key=len) if starts else None


def _arguments_after(reply, tag, count):
    if tag not in reply:
        return None
    parts = reply.split(tag, 1)[1].split()
    if len(parts) < count:
        return None
    return [part.strip(ARGUMENT_TRIM) for part in parts[:count]]


def asks_for_transfer(reply):
    return TAG_TRANSFER in reply


def document_topic(reply, known_topics):
    arguments = _arguments_after(reply, TAG_DOC, 1)
    return match_known_name(arguments[0], known_topics) if arguments else None


def lookup_name(reply, known_lookups):
    arguments = _arguments_after(reply, TAG_LOOKUP, 1)
    return match_known_name(arguments[0], known_lookups) if arguments else None


def lookup_command(reply, known_lookups):
    arguments = _arguments_after(reply, TAG_LOOKUP, 2)
    lookup = match_known_name(arguments[0], known_lookups) if arguments else None
    if not lookup:
        return None
    return lookup, "".join(c for c in arguments[1] if c.isdigit())


def without_tags(reply):
    for tag in TAGS:
        reply = reply.split(tag, 1)[0]
    return reply.strip()


def contains_digit(text):
    return any(char.isdigit() for char in text)
