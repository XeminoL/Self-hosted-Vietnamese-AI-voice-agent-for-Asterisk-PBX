import hashlib
import json
import os
import time
import unicodedata
import urllib.error
import urllib.request

from bank_data import (ACTIONS, CONFIRMATION_QUESTIONS, caller_consented,
                       needs_confirmation)
from bank_docs import available_topics, find_topic_by_keyword, keywords_found, read_topic
from transcript_fixup import fix_near_homophones

LLM_BASE = "http://127.0.0.1:8080"
LLM_URL = LLM_BASE + "/v1/chat/completions"
WARM_SLOT = 0
MAX_REPLY_TOKENS = 20
TEMPERATURE = 0
REMEMBERED_TURNS = 4

TAG_ACTION = "@TRA"
TAG_TRANSFER = "@CHUYEN"
TAG_DOCUMENT = "@DOC"

ASK_FOR_PHONE_NUMBER = "Anh chị bấm số điện thoại rồi bấm dấu thăng ạ."
OUT_OF_SCOPE = "Dạ chỗ này em không nắm được, em xin phép chuyển anh chị cho nhân viên nhé."
DID_NOT_CATCH = "Dạ em chưa nghe rõ ạ."
DEFAULT_ACTION_AFTER_DIALING = "tra_so_du"
WARM_UP_SENTENCE = "alo"
ASKS_TO_DIAL = "bấm"
OWN_ACCOUNT_WORDS = ("của tôi", "của mình", "số dư", "giao dịch", "khoá thẻ", "khóa thẻ")
TOPIC_LIST_SLOT = "{danh_sach_chu_de}"
TOPIC_SEPARATOR = " · "
REPEAT_OPENING = "Dạ như em vừa nói, "
POLITE_OPENING = "Dạ "
APOLOGY_OPENING = "Dạ em xin lỗi, "
ASK_AGAIN_AFTER_MISTAKE = "Dạ em xin lỗi, anh chị hỏi lại giúp em cụ thể hơn được không ạ?"
OBJECTION_OPENINGS = ("không phải", "không đúng", "chưa đúng", "sai rồi", "sai", "nhầm rồi",
                      "nhầm", "không không")
OBJECTION_ANYWHERE = ("sai rồi", "nhầm rồi", "không hỏi", "hỏi cái khác", "trả lời sai",
                      "không phải cái đó", "không phải cái này", "không phải ý đó")
OBJECTION_FILLERS = ("ơ", "ờ", "à", "ủa", "em ơi", "chị ơi")
OBJECTIONS_BEFORE_TRANSFER = 2
STILL_THERE = "Dạ anh chị còn nghe máy không ạ?"
GOODBYE = "Dạ em cảm ơn anh chị đã gọi, chúc anh chị một ngày tốt lành ạ."
GOODBYE_AFTER_SILENCE = "Dạ em không nghe thấy anh chị nữa, em xin phép cúp máy. Chào anh chị ạ."
ANYTHING_ELSE = "Dạ không có gì ạ, anh chị cần em hỗ trợ gì thêm không ạ?"
THANKS = ("cảm ơn", "cám ơn", "thank you", "thanks")
CLOSING = ("tạm biệt", "bye", "bai bai", "hết rồi", "vậy thôi", "thế thôi", "vậy được rồi",
           "không cần gì nữa", "không còn gì", "không cần nữa", "chào em", "chào em nhé")
NOTHING_MORE = ("không", "hết", "thôi", "khỏi", "vậy thôi", "đủ rồi")
CANCELLED = "Dạ vâng, em không làm nữa ạ. Anh chị cần em hỗ trợ gì thêm không ạ?"
MENU_ACTIONS = {"1": "tra_so_du", "2": "tra_giao_dich", "3": "tra_han_muc", "4": "khoa_the"}
STAFF_KEY = "0"
MENU = ("Dạ anh chị bấm một để tra số dư, bấm hai nghe giao dịch gần nhất, bấm ba tra hạn mức, "
        "bấm bốn khoá thẻ, hoặc bấm không để gặp nhân viên ạ.")
WHY_WE_NEED_THE_NUMBER = ("Dạ em cần số điện thoại để tìm đúng tài khoản của anh chị, số chỉ dùng để tra thôi ạ. "
                          "Anh chị không tiện thì em chuyển qua nhân viên nhé?")
OFFER_STAFF = "Dạ em xin lỗi đã làm anh chị phiền, anh chị có muốn em chuyển qua nhân viên không ạ?"
RELUCTANT_TO_DIAL = ("không có điện thoại", "không có số", "không nhớ số", "quên số", "không nhớ",
                     "không muốn", "không bấm", "sao phải", "tại sao", "để làm gì", "bấm làm gì",
                     "không tiện")
ANNOYED = ("phiền quá", "phiền ghê", "lâu quá", "mệt quá", "bực quá", "chán quá", "rắc rối quá",
           "lằng nhằng")
ASKS_FOR_STAFF = ("nhân viên", "người thật", "tổng đài viên", "gặp người")
IDENTITY_TOPIC = "tro_ly_tu_dong"
YES_TO_STAFF = ("ừ", "ờ", "được", "có", "vâng", "dạ", "ok", "chuyển đi", "chuyển giúp",
                "chuyển luôn", "đồng ý")
NO_TO_STAFF = ("không", "thôi", "khỏi", "chưa", "đừng")

SAME_MEANING_SENTENCES = (
    (ASK_FOR_PHONE_NUMBER,
     "Dạ anh chị bấm giúp em số điện thoại, xong bấm dấu thăng nhé.",
     "Dạ anh chị bấm số điện thoại đăng ký, rồi kết thúc bằng dấu thăng ạ."),
    (OUT_OF_SCOPE,
     "Dạ phần này em chưa hỗ trợ được, em chuyển anh chị qua nhân viên nhé.",
     "Dạ việc này nhân viên sẽ giúp anh chị rõ hơn, em chuyển máy nhé."),
    (DID_NOT_CATCH,
     "Dạ anh chị nói lại giúp em được không ạ?",
     "Dạ em nghe chưa rõ, anh chị nói chậm lại giúp em nhé."),
    (ASK_AGAIN_AFTER_MISTAKE,
     "Dạ em nhầm rồi, anh chị cần hỏi gì để em trả lời lại ạ?"),
) + tuple(
    (question, "Dạ anh chị chắc chắn muốn khoá thẻ phải không ạ?")
    for question in CONFIRMATION_QUESTIONS.values()
)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "prompt.txt"), encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read().strip()


def system_prompt():
    return PROMPT_TEMPLATE.replace(TOPIC_LIST_SLOT, TOPIC_SEPARATOR.join(available_topics()))


def ask_llm(history, slot=None):
    request_body = {
        "messages": [{"role": "system", "content": system_prompt()}] + history[-REMEMBERED_TURNS:],
        "max_tokens": MAX_REPLY_TOKENS,
        "temperature": TEMPERATURE,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if slot is not None:
        request_body["id_slot"] = slot
    request = urllib.request.Request(
        LLM_URL, data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())
    choice = result["choices"][0]
    return (choice["message"]["content"].strip(),
            choice.get("finish_reason") == "length",
            result.get("timings", {}))


def _call_llm_server(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(LLM_BASE + path, data=data,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, ValueError):
        return None


def _saved_prompt_name():
    models = _call_llm_server("/v1/models") or {}
    model = (models.get("data") or [{}])[0].get("id", "")
    return "prompt-" + hashlib.sha1((model + system_prompt()).encode("utf-8")).hexdigest()[:16] + ".bin"


def warm_up_llm():
    name = _saved_prompt_name()
    started = time.monotonic()
    restored = _call_llm_server(f"/slots/{WARM_SLOT}?action=restore", {"filename": name}) or {}
    if restored.get("n_restored"):
        return f"nap lai tu file sau {time.monotonic() - started:.1f}s"
    timings = ask_llm([{"role": "user", "content": WARM_UP_SENTENCE}], WARM_SLOT)[2]
    saved = _call_llm_server(f"/slots/{WARM_SLOT}?action=save", {"filename": name}) is not None
    return describe_timings(timings) + (" | da luu ra file cho lan sau" if saved else "")


def describe_timings(timings):
    if not timings:
        return ""
    return (f"nap {timings.get('prompt_n', 0)}tk/{timings.get('prompt_ms', 0) / 1000:.1f}s"
            f" | sinh {timings.get('predicted_n', 0)}tk/"
            f"{timings.get('predicted_ms', 0) / 1000:.1f}s"
            f" | cache {timings.get('cache_n', 0)}")


def _plain_name(name):
    letters = unicodedata.normalize("NFD", name.lower().replace("đ", "d"))
    return "".join(c for c in letters if not unicodedata.combining(c))


def match_known_name(written, known_names):
    plain = _plain_name(written)
    starts = [name for name in known_names if plain.startswith(name)]
    return max(starts, key=len) if starts else None


def parse_document_topic(sentence):
    topic = _arguments_after_tag(sentence, TAG_DOCUMENT, 1)
    if not topic:
        return None
    return match_known_name(topic[0], available_topics())


def parse_action_name(sentence):
    parts = _arguments_after_tag(sentence, TAG_ACTION, 1)
    return match_known_name(parts[0], ACTIONS) if parts else None


def parse_action_command(sentence):
    parts = _arguments_after_tag(sentence, TAG_ACTION, 2)
    action = match_known_name(parts[0], ACTIONS) if parts else None
    if not action:
        return None
    phone_number = "".join(c for c in parts[1] if c.isdigit())
    return action, phone_number


def strip_tags(sentence):
    for tag in (TAG_ACTION, TAG_DOCUMENT, TAG_TRANSFER):
        if tag in sentence:
            sentence = sentence.split(tag, 1)[0]
    return sentence.strip()


def _arguments_after_tag(sentence, tag, count):
    if tag not in sentence:
        return None
    parts = sentence.split(tag, 1)[1].strip().split()
    if len(parts) < count:
        return None
    return [p.strip("[](){}:,.") for p in parts[:count]]


def _with_opening(opening, reply):
    rest = reply[len(POLITE_OPENING):] if reply.startswith(POLITE_OPENING) else reply
    return opening + rest[:1].lower() + rest[1:]


def say_differently(reply, last_reply):
    if not reply or reply != last_reply:
        return reply
    for group in SAME_MEANING_SENTENCES:
        if reply in group:
            return group[(group.index(reply) + 1) % len(group)]
    return _with_opening(REPEAT_OPENING, reply)


def _words_of(sentence):
    for mark in ",.!?":
        sentence = sentence.replace(mark, " ")
    return " " + " ".join(sentence.lower().split()) + " "


def says_any(caller_sentence, phrases):
    words = _words_of(caller_sentence)
    return any(f" {phrase} " in words for phrase in phrases)


def wants_staff(caller_sentence):
    if says_any(caller_sentence, ASKS_FOR_STAFF):
        return True
    return says_any(caller_sentence, YES_TO_STAFF) and not says_any(caller_sentence, NO_TO_STAFF)


def is_objection(caller_sentence):
    sentence = caller_sentence.lower()
    words = sentence.replace(",", " ").replace(".", " ").replace("!", " ").split()
    for filler in OBJECTION_FILLERS:
        if words[:len(filler.split())] == filler.split():
            words = words[len(filler.split()):]
    opens_with_objection = any(
        words[:len(opening.split())] == opening.split() for opening in OBJECTION_OPENINGS)
    return opens_with_objection or any(phrase in sentence for phrase in OBJECTION_ANYWHERE)


def _without_keywords(caller_sentence, topic):
    sentence = caller_sentence.lower()
    for word in keywords_found(caller_sentence, topic):
        sentence = sentence.replace(word.lower(), " ")
    return sentence


def asks_about_own_account(caller_sentence):
    return any(word in caller_sentence.lower() for word in OWN_ACCOUNT_WORDS)


def contains_digit(sentence):
    return any(char.isdigit() for char in sentence)


class TurnResult:
    def __init__(self, reply="", log=(), transfer=False, hang_up=False):
        self.reply = reply
        self.log = list(log)
        self.transfer = transfer
        self.hang_up = hang_up


class Conversation:
    def __init__(self):
        self.history = []
        self.action_awaiting_confirmation = None
        self.last_reply = None
        self.last_topic = None
        self.topic_this_turn = None
        self.objections_in_a_row = 0
        self.pending_action = None

    def expects_number(self):
        return self.pending_action is not None or self._just_asked_to_dial()

    def _just_asked_to_dial(self):
        return any(self.last_reply in group for group in SAME_MEANING_SENTENCES
                   if ASK_FOR_PHONE_NUMBER in group)

    def respond(self, transcript, dialed_number, menu_key=""):
        self.topic_this_turn = None
        result = self._respond(transcript, dialed_number, menu_key)
        self.last_topic = self.topic_this_turn
        result.reply = say_differently(result.reply, self.last_reply)
        if result.reply:
            self.last_reply = result.reply
        if not (self._just_asked_to_dial() or self.last_reply == WHY_WE_NEED_THE_NUMBER):
            self.pending_action = None
        if self.history and self.history[-1]["role"] == "user":
            remembered = f"{TAG_DOCUMENT} {self.last_topic}" if self.last_topic else result.reply
            self.history.append({"role": "assistant", "content": remembered})
        return result

    def _respond(self, transcript, dialed_number, menu_key):
        if menu_key:
            self.history.append({"role": "user", "content": f"(bấm phím {menu_key})"})
            return self._press(menu_key)
        if not transcript and not dialed_number:
            return TurnResult(reply=DID_NOT_CATCH)

        caller_sentence = self._build_caller_sentence(transcript, dialed_number)
        self.history.append({"role": "user", "content": caller_sentence})

        if dialed_number and self.pending_action:
            return self._run_pending_action(dialed_number)
        if self.action_awaiting_confirmation and transcript:
            return self._answer_confirmation(caller_sentence)

        reluctance = None if dialed_number or self.action_awaiting_confirmation \
            else self._handle_reluctance(caller_sentence)
        if reluctance:
            return reluctance

        goodbye = None if dialed_number or self.action_awaiting_confirmation \
            else self._handle_goodbye(caller_sentence)
        if goodbye:
            return goodbye

        if self.last_reply and not self.action_awaiting_confirmation and not dialed_number \
                and is_objection(caller_sentence):
            return self._handle_objection(caller_sentence)
        self.objections_in_a_row = 0

        topic = None if dialed_number else find_topic_by_keyword(caller_sentence)
        if topic and not asks_about_own_account(_without_keywords(caller_sentence, topic)):
            return TurnResult(self._read(topic), [f"tu khoa {topic} -> doc tai lieu, khong hoi LLM"])

        llm_sentence, ran_out_of_tokens, timings = ask_llm(self.history)
        log = [f"HIEU: {llm_sentence}"]
        timing_line = describe_timings(timings)
        if timing_line:
            log.insert(0, timing_line)

        return self._decide(caller_sentence, llm_sentence, dialed_number,
                            ran_out_of_tokens, log)

    def _press(self, key):
        if key == STAFF_KEY:
            return TurnResult(log=["phim 0 -> chuyen nhan vien"], transfer=True)
        action = MENU_ACTIONS.get(key)
        if not action:
            return TurnResult(MENU, [f"phim {key} -> doc menu"])
        self.pending_action = action
        self.action_awaiting_confirmation = None
        return TurnResult(ASK_FOR_PHONE_NUMBER, [f"phim {key} -> {action}, cho so dien thoai"])

    def _run_pending_action(self, phone_number):
        action, self.pending_action = self.pending_action, None
        if needs_confirmation(action):
            self.action_awaiting_confirmation = (action, phone_number)
            return TurnResult(CONFIRMATION_QUESTIONS[action], [f"HOI XAC NHAN truoc khi {action}"])
        return TurnResult(ACTIONS[action](phone_number), [f"TRA {action}({phone_number})"])

    def _answer_confirmation(self, caller_sentence):
        action, phone_number = self.action_awaiting_confirmation
        self.action_awaiting_confirmation = None
        if caller_consented(caller_sentence):
            return TurnResult(ACTIONS[action](phone_number),
                              [f"nguoi goi DONG Y -> TRA {action}({phone_number})"])
        return TurnResult(CANCELLED, ["nguoi goi KHONG dong y"])

    def _handle_goodbye(self, caller_sentence):
        if find_topic_by_keyword(caller_sentence):
            return None
        finishing = says_any(caller_sentence, CLOSING) or (
            self.last_reply in (ANYTHING_ELSE, CANCELLED) and says_any(caller_sentence, NOTHING_MORE))
        if finishing:
            return TurnResult(GOODBYE, ["nguoi goi chao -> chao lai roi cup"], hang_up=True)
        if says_any(caller_sentence, THANKS):
            return TurnResult(ANYTHING_ELSE, ["nguoi goi cam on -> hoi con can gi khong"])
        return None

    def _handle_reluctance(self, caller_sentence):
        offered_staff = self.last_reply in (WHY_WE_NEED_THE_NUMBER, OFFER_STAFF)
        asks_for_staff = says_any(caller_sentence, ASKS_FOR_STAFF) \
            and find_topic_by_keyword(caller_sentence) != IDENTITY_TOPIC
        if (offered_staff and wants_staff(caller_sentence)) or asks_for_staff:
            return TurnResult(log=["nguoi goi muon gap nhan vien -> chuyen"], transfer=True)
        if self._just_asked_to_dial() and says_any(caller_sentence, RELUCTANT_TO_DIAL):
            return TurnResult(WHY_WE_NEED_THE_NUMBER, ["nguoi goi ngai bam so -> giai thich"])
        if says_any(caller_sentence, ANNOYED):
            return TurnResult(OFFER_STAFF, ["nguoi goi buc -> moi gap nhan vien"])
        return None

    def _handle_objection(self, caller_sentence):
        self.objections_in_a_row += 1
        log = [f"PHAN DOI lan {self.objections_in_a_row} (cau truoc: {self.last_topic or self.last_reply})"]
        if self.objections_in_a_row >= OBJECTIONS_BEFORE_TRANSFER:
            self.objections_in_a_row = 0
            log.append("phan doi lien tiep -> chuyen nhan vien")
            return TurnResult(log=log, transfer=True)
        topic = find_topic_by_keyword(caller_sentence, skip=self.last_topic)
        if topic:
            log.append(f"DOC tai lieu moi: {topic}")
            return TurnResult(_with_opening(APOLOGY_OPENING, self._read(topic)), log)
        return TurnResult(ASK_AGAIN_AFTER_MISTAKE, log)

    def _read(self, topic):
        self.topic_this_turn = topic
        return read_topic(topic)

    @staticmethod
    def _build_caller_sentence(transcript, dialed_number):
        sentence = fix_near_homophones(transcript) if transcript else "đây"
        if dialed_number:
            sentence += f" (số điện thoại đã bấm: {dialed_number})"
        return sentence

    def _decide(self, caller_sentence, llm_sentence, dialed_number,
                ran_out_of_tokens, log):
        if TAG_TRANSFER in llm_sentence:
            return TurnResult(log=log, transfer=True)

        if TAG_DOCUMENT in llm_sentence:
            return TurnResult(self._settle_document(caller_sentence, llm_sentence, log), log)

        command = self._settle_command(caller_sentence, llm_sentence, dialed_number, log)
        if command:
            action_name, phone_number = command
            log.append(f"TRA {action_name}({phone_number})")
            return TurnResult(ACTIONS[action_name](phone_number), log)

        return TurnResult(
            self._filter_llm_sentence(caller_sentence, llm_sentence,
                                      ran_out_of_tokens, log), log)

    def _settle_document(self, caller_sentence, llm_sentence, log):
        chosen = parse_document_topic(llm_sentence)
        by_keyword = find_topic_by_keyword(caller_sentence)
        if by_keyword and by_keyword != chosen:
            log.append(f"LLM chon {chosen}, tu khoa trong cau noi la {by_keyword} -> dung {by_keyword}")
            chosen = by_keyword
        if not chosen:
            log.append(f"LLM bia chu de: {llm_sentence}")
            return OUT_OF_SCOPE
        log.append(f"DOC tai lieu: {chosen}")
        return self._read(chosen)

    def _settle_command(self, caller_sentence, llm_sentence, dialed_number, log):
        command = parse_action_command(llm_sentence)

        if self.action_awaiting_confirmation:
            awaiting = self.action_awaiting_confirmation
            self.action_awaiting_confirmation = None
            if caller_consented(caller_sentence):
                log.append(f"nguoi goi DONG Y -> chay {awaiting[0]}")
                return awaiting
            log.append("nguoi goi KHONG dong y")
            return None

        if command and needs_confirmation(command[0]):
            self.action_awaiting_confirmation = (command[0], dialed_number or command[1])
            log.append(f"HOI XAC NHAN truoc khi {command[0]}")
            return None

        if dialed_number and not command:
            log.append("co so da bam, LLM khong sinh @TRA")
            return DEFAULT_ACTION_AFTER_DIALING, dialed_number

        if command and dialed_number and command[1] != dialed_number:
            log.append(f"LLM viet sai so, dung so da bam {dialed_number}")
            return command[0], dialed_number

        if command and not dialed_number:
            log.append("LLM bia so, nguoi goi chua bam")
            return None

        return command

    def _filter_llm_sentence(self, caller_sentence, llm_sentence,
                             ran_out_of_tokens, log):
        sentence = strip_tags(llm_sentence)

        if self.action_awaiting_confirmation:
            return CONFIRMATION_QUESTIONS[self.action_awaiting_confirmation[0]]
        if not sentence:
            if TAG_ACTION not in llm_sentence:
                return DID_NOT_CATCH
            self.pending_action = parse_action_name(llm_sentence)
            if self.pending_action:
                log.append(f"nho viec {self.pending_action}, cho so dien thoai")
            return ASK_FOR_PHONE_NUMBER
        if ran_out_of_tokens:
            return self._rescue_unfinished(caller_sentence, sentence, log)
        if not contains_digit(sentence):
            return self._prefer_document(caller_sentence, sentence, log)

        topic = find_topic_by_keyword(caller_sentence)
        if topic:
            log.append(f"BIA SO LIEU -> tu khoa: {topic}")
            return self._read(topic)
        log.append(f"BIA SO LIEU, bo: {sentence}")
        return OUT_OF_SCOPE

    def _prefer_document(self, caller_sentence, sentence, log):
        if ASKS_TO_DIAL in sentence.lower() and asks_about_own_account(caller_sentence):
            return sentence
        topic = find_topic_by_keyword(caller_sentence)
        if not topic:
            return sentence
        log.append(f"LLM tu soan thay vi @DOC -> tu khoa: {topic}")
        return self._read(topic)

    def _rescue_unfinished(self, caller_sentence, sentence, log):
        topic = find_topic_by_keyword(caller_sentence)
        if topic:
            log.append(f"CAU BI CAT -> tu khoa: {topic}")
            return self._read(topic)
        log.append(f"CAU BI CAT, bo: {sentence}")
        return OUT_OF_SCOPE