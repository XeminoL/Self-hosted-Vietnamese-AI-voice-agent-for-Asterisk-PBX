from dataclasses import dataclass, field

import accounts
import knowledge
import llm_client
import model_reply
from caller_words import (accepts_staff, asks_about_own_account, asks_for_staff, consented, is_objection,
                          says_any, without_phrases, word_count)
from domain import MENU, PHRASES, WORDS
from transcript_fixup import fix_near_homophones

OBJECTIONS_BEFORE_TRANSFER = 2
MAX_WORDS_OF_NOISE = 1

OPENINGS = PHRASES["openings"]
FOR_THE_MODEL = PHRASES["for_the_model"]
ASK_FOR_PHONE_NUMBER = PHRASES["ask_for_phone_number"][0]
OUT_OF_SCOPE = PHRASES["out_of_scope"][0]
DID_NOT_CATCH = PHRASES["did_not_catch"][0]
ASK_AGAIN_AFTER_MISTAKE = PHRASES["ask_again_after_mistake"][0]
CONFIRMATION_QUESTIONS = {lookup: sentences[0] for lookup, sentences in PHRASES["confirm"].items()}

SAME_MEANING_SENTENCES = tuple(
    tuple(PHRASES[name]) for name in ("ask_for_phone_number", "out_of_scope", "did_not_catch",
                                      "ask_again_after_mistake")
) + tuple(tuple(sentences) for sentences in PHRASES["confirm"].values())
ASKING_FOR_NUMBER = tuple(PHRASES["ask_for_phone_number"])


def with_opening(opening, reply):
    polite = OPENINGS["polite"]
    rest = reply[len(polite):] if reply.startswith(polite) else reply
    return opening + rest[:1].lower() + rest[1:]


def say_differently(reply, last_reply):
    if not reply or reply != last_reply:
        return reply
    for group in SAME_MEANING_SENTENCES:
        if reply in group:
            return group[(group.index(reply) + 1) % len(group)]
    return with_opening(OPENINGS["repeat"], reply)


@dataclass
class TurnResult:
    reply: str = ""
    notes: list = field(default_factory=list)
    transfer: bool = False
    hang_up: bool = False
    lookup: str = None
    topic: str = None


class Conversation:
    def __init__(self):
        self.history = []
        self.last_reply = None
        self.last_topic = None
        self.topic_this_turn = None
        self.pending_lookup = None
        self.awaiting_confirmation = None
        self.objections_in_a_row = 0

    def expects_number(self):
        return self.pending_lookup is not None or self._just_asked_for_number()

    def _just_asked_for_number(self):
        return self.last_reply in ASKING_FOR_NUMBER

    def respond(self, transcript, dialed_number="", menu_key=""):
        self.topic_this_turn = None
        result = self._reply_to(transcript, dialed_number, menu_key)
        result.topic = self.last_topic = self.topic_this_turn
        result.reply = say_differently(result.reply, self.last_reply)
        if result.reply:
            self.last_reply = result.reply
        if not (self._just_asked_for_number() or self.last_reply == PHRASES["why_we_need_the_number"]):
            self.pending_lookup = None
        if self.history and self.history[-1]["role"] == "user":
            remembered = f"{model_reply.TAG_DOC} {self.last_topic}" if self.last_topic else result.reply
            self.history.append({"role": "assistant", "content": remembered})
        return result

    def _reply_to(self, transcript, dialed_number, menu_key):
        if menu_key:
            self._remember_caller(FOR_THE_MODEL["pressed_key"].format(key=menu_key))
            return self._press(menu_key)
        if not transcript and not dialed_number:
            return TurnResult(DID_NOT_CATCH)

        sentence = self._caller_sentence(transcript, dialed_number)
        self._remember_caller(sentence)
        if dialed_number and self.pending_lookup:
            return self._run_pending_lookup(dialed_number)
        if self.awaiting_confirmation:
            return self._answer_confirmation(sentence)
        if dialed_number:
            return self._ask_model(sentence, dialed_number)

        for rule in (self._staff_or_reluctance, self._goodbye, self._objection):
            result = rule(sentence)
            if result:
                return result
        self.objections_in_a_row = 0

        topic = knowledge.find_topic(sentence)
        if topic and not asks_about_own_account(without_phrases(sentence, knowledge.keywords_heard(sentence, topic))):
            return TurnResult(self._read(topic), [f"keyword for {topic}, reading it without the model"])
        if word_count(transcript) <= MAX_WORDS_OF_NOISE:
            return TurnResult(DID_NOT_CATCH, ["a single word and no rule for it, asking again"])
        return self._ask_model(sentence, dialed_number)

    def _remember_caller(self, content):
        self.history.append({"role": "user", "content": content})

    @staticmethod
    def _caller_sentence(transcript, dialed_number):
        sentence = fix_near_homophones(transcript) if transcript else FOR_THE_MODEL["no_words"]
        if dialed_number:
            sentence += " " + FOR_THE_MODEL["dialed"].format(number=dialed_number)
        return sentence

    def _read(self, topic):
        self.topic_this_turn = topic
        return knowledge.answer(topic)

    def _press(self, key):
        if key == MENU["staff"]:
            return TurnResult(notes=[f"key {key}, transfer to staff"], transfer=True)
        lookup = MENU["lookups"].get(key)
        if not lookup:
            return TurnResult(PHRASES["menu"], [f"key {key}, reading the menu"])
        self.pending_lookup = lookup
        self.awaiting_confirmation = None
        return TurnResult(ASK_FOR_PHONE_NUMBER, [f"key {key}, {lookup} after the number"], lookup=lookup)

    def _run_pending_lookup(self, phone_number):
        lookup, self.pending_lookup = self.pending_lookup, None
        if accounts.needs_confirmation(lookup):
            self.awaiting_confirmation = (lookup, phone_number)
            return TurnResult(CONFIRMATION_QUESTIONS[lookup], [f"asking to confirm {lookup}"], lookup=lookup)
        return TurnResult(accounts.run_lookup(lookup, phone_number), [f"{lookup}({phone_number})"], lookup=lookup)

    def _answer_confirmation(self, sentence):
        lookup, phone_number = self.awaiting_confirmation
        self.awaiting_confirmation = None
        if consented(sentence):
            return TurnResult(accounts.run_lookup(lookup, phone_number),
                              [f"caller agreed, {lookup}({phone_number})"], lookup=lookup)
        return TurnResult(PHRASES["cancelled"], [f"caller did not agree to {lookup}"], lookup=lookup)

    def _staff_or_reluctance(self, sentence):
        offered_staff = self.last_reply in (PHRASES["why_we_need_the_number"], PHRASES["offer_staff"])
        if (offered_staff and accepts_staff(sentence)) or asks_for_staff(sentence):
            return TurnResult(notes=["caller wants a person, transfer"], transfer=True)
        if self._just_asked_for_number() and says_any(sentence, WORDS["reluctant_to_dial"]):
            return TurnResult(PHRASES["why_we_need_the_number"], ["caller will not dial, explaining why"])
        if says_any(sentence, WORDS["annoyed"]):
            return TurnResult(PHRASES["offer_staff"], ["caller is annoyed, offering a person"])
        return None

    def _goodbye(self, sentence):
        if knowledge.find_topic(sentence):
            return None
        asked_anything_else = self.last_reply in (PHRASES["anything_else"], PHRASES["cancelled"])
        if says_any(sentence, WORDS["closing"]) or (asked_anything_else and says_any(sentence, WORDS["nothing_more"])):
            return TurnResult(PHRASES["goodbye"], ["caller said goodbye"], hang_up=True)
        if says_any(sentence, WORDS["thanks"]):
            return TurnResult(PHRASES["anything_else"], ["caller said thanks, asking if there is more"])
        return None

    def _objection(self, sentence):
        if not self.last_reply or not is_objection(sentence):
            return None
        self.objections_in_a_row += 1
        notes = [f"objection {self.objections_in_a_row} to {self.last_topic or self.last_reply}"]
        if self.objections_in_a_row >= OBJECTIONS_BEFORE_TRANSFER:
            self.objections_in_a_row = 0
            return TurnResult(notes=notes + ["objected twice in a row, transfer"], transfer=True)
        topic = knowledge.find_topic(sentence, skip=self.last_topic)
        if topic:
            return TurnResult(with_opening(OPENINGS["apology"], self._read(topic)), notes + [f"reading {topic} instead"])
        return TurnResult(ASK_AGAIN_AFTER_MISTAKE, notes)

    def _ask_model(self, sentence, dialed_number):
        answer = llm_client.ask(self.history)
        notes = [line for line in (llm_client.describe_timings(answer.timings), f"model: {answer.text}") if line]
        if model_reply.asks_for_transfer(answer.text):
            return TurnResult(notes=notes, transfer=True)
        if model_reply.TAG_DOC in answer.text:
            return TurnResult(self._settle_document(sentence, answer.text, notes), notes)
        command = self._settle_lookup(answer.text, dialed_number, notes)
        if command:
            lookup, phone_number = command
            notes.append(f"{lookup}({phone_number})")
            return TurnResult(accounts.run_lookup(lookup, phone_number), notes, lookup=lookup)
        return TurnResult(self._check_free_reply(sentence, answer, notes), notes)

    def _settle_document(self, sentence, text, notes):
        chosen = model_reply.document_topic(text, knowledge.topic_names())
        by_keyword = knowledge.find_topic(sentence)
        if by_keyword and by_keyword != chosen:
            notes.append(f"model chose {chosen}, the keywords say {by_keyword}")
            chosen = by_keyword
        if not chosen:
            notes.append("model made up a topic")
            return OUT_OF_SCOPE
        notes.append(f"reading {chosen}")
        return self._read(chosen)

    def _settle_lookup(self, text, dialed_number, notes):
        command = model_reply.lookup_command(text, accounts.LOOKUPS)
        if command and not dialed_number:
            notes.append("model made up a phone number, asking the caller to dial")
            return None
        if not dialed_number:
            return None
        if not command:
            notes.append(f"number dialed but no lookup named, {accounts.DEFAULT_AFTER_DIALING}")
            return accounts.DEFAULT_AFTER_DIALING, dialed_number
        lookup, written_number = command
        if written_number != dialed_number:
            notes.append(f"model wrote {written_number}, using the dialed {dialed_number}")
        if accounts.needs_confirmation(lookup):
            self.awaiting_confirmation = (lookup, dialed_number)
            notes.append(f"asking to confirm {lookup}")
            return None
        return lookup, dialed_number

    def _check_free_reply(self, sentence, answer, notes):
        spoken = model_reply.without_tags(answer.text)
        if self.awaiting_confirmation:
            return CONFIRMATION_QUESTIONS[self.awaiting_confirmation[0]]
        if not spoken:
            if model_reply.TAG_LOOKUP not in answer.text:
                return DID_NOT_CATCH
            self.pending_lookup = model_reply.lookup_name(answer.text, accounts.LOOKUPS)
            if self.pending_lookup:
                notes.append(f"{self.pending_lookup} after the number")
            return ASK_FOR_PHONE_NUMBER
        if answer.cut_off:
            return self._document_or_out_of_scope(sentence, notes, f"reply cut off: {spoken}")
        if model_reply.contains_digit(spoken):
            return self._document_or_out_of_scope(sentence, notes, f"made-up figures: {spoken}")
        if says_any(spoken, WORDS["asks_to_dial"]) and asks_about_own_account(sentence):
            return spoken
        topic = knowledge.find_topic(sentence)
        if not topic:
            return spoken
        notes.append(f"model answered freely, keyword for {topic}")
        return self._read(topic)

    def _document_or_out_of_scope(self, sentence, notes, problem):
        topic = knowledge.find_topic(sentence)
        if topic:
            notes.append(f"{problem}, reading {topic}")
            return self._read(topic)
        notes.append(f"{problem}, dropped")
        return OUT_OF_SCOPE
