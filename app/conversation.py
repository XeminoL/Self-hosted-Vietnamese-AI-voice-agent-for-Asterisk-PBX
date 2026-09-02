import json
import os
import urllib.request

from bank_data import (ACTIONS, CONFIRMATION_QUESTIONS, caller_consented,
                       needs_confirmation)
from bank_docs import available_topics, find_topic_by_keyword, read_topic
from transcript_fixup import fix_near_homophones

LLM_URL = "http://127.0.0.1:8080/v1/chat/completions"
MAX_REPLY_TOKENS = 20
REMEMBERED_TURNS = 4

TAG_ACTION = "@TRA"
TAG_TRANSFER = "@CHUYEN"
TAG_DOCUMENT = "@DOC"

ASK_FOR_PHONE_NUMBER = "Anh chị bấm số điện thoại rồi bấm dấu thăng ạ."
OUT_OF_SCOPE = "Dạ chỗ này em không nắm được, em xin phép chuyển anh chị cho nhân viên nhé."
DID_NOT_CATCH = "Dạ em chưa nghe rõ ạ."
DEFAULT_ACTION_AFTER_DIALING = "tra_so_du"

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "prompt.txt"), encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()


def ask_llm(history):
    body = json.dumps({
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history[-REMEMBERED_TURNS:],
        "max_tokens": MAX_REPLY_TOKENS,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    request = urllib.request.Request(
        LLM_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())
    return result["choices"][0]["message"]["content"].strip(), result.get("timings", {})


def describe_timings(timings):
    if not timings:
        return ""
    return (f"nap {timings.get('prompt_n', 0)}tk/{timings.get('prompt_ms', 0) / 1000:.1f}s"
            f" | sinh {timings.get('predicted_n', 0)}tk/"
            f"{timings.get('predicted_ms', 0) / 1000:.1f}s"
            f" | cache {timings.get('cache_n', 0)}")


def parse_document_topic(sentence):
    topic = _arguments_after_tag(sentence, TAG_DOCUMENT, 1)
    if not topic:
        return None
    return topic[0] if topic[0] in available_topics() else None


def parse_action_command(sentence):
    parts = _arguments_after_tag(sentence, TAG_ACTION, 2)
    if not parts or parts[0] not in ACTIONS:
        return None
    phone_number = "".join(c for c in parts[1] if c.isdigit())
    return parts[0], phone_number


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

    def respond(self, transcript, dialed_number):
        if not transcript and not dialed_number:
            return TurnResult(reply=DID_NOT_CATCH)

        caller_sentence = self._build_caller_sentence(transcript, dialed_number)
        self.history.append({"role": "user", "content": caller_sentence})

        llm_sentence, timings = ask_llm(self.history)
        log = [f"HIEU: {llm_sentence}"]
        timing_line = describe_timings(timings)
        if timing_line:
            log.insert(0, timing_line)

        result = self._decide(caller_sentence, llm_sentence, dialed_number, log)
        self.history.append({"role": "assistant", "content": result.reply})
        return result

    @staticmethod
    def _build_caller_sentence(transcript, dialed_number):
        sentence = fix_near_homophones(transcript) if transcript else "đây"
        if dialed_number:
            sentence += f" (số điện thoại đã bấm: {dialed_number})"
        return sentence

    def _decide(self, caller_sentence, llm_sentence, dialed_number, log):
        if TAG_TRANSFER in llm_sentence:
            return TurnResult(log=log, transfer=True)

        topic = parse_document_topic(llm_sentence)
        if topic:
            log.append(f"DOC tai lieu: {topic}")
            return TurnResult(read_topic(topic), log)

        command = self._settle_command(caller_sentence, llm_sentence, dialed_number, log)
        if command:
            action_name, phone_number = command
            log.append(f"TRA {action_name}({phone_number})")
            return TurnResult(ACTIONS[action_name](phone_number), log)

        return TurnResult(self._filter_llm_sentence(caller_sentence, llm_sentence, log), log)

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

    def _filter_llm_sentence(self, caller_sentence, llm_sentence, log):
        sentence = strip_tags(llm_sentence)

        if self.action_awaiting_confirmation:
            return CONFIRMATION_QUESTIONS[self.action_awaiting_confirmation[0]]
        if not sentence:
            return ASK_FOR_PHONE_NUMBER if TAG_ACTION in llm_sentence else DID_NOT_CATCH
        if not contains_digit(sentence):
            return sentence

        topic = find_topic_by_keyword(caller_sentence)
        if topic:
            log.append(f"BIA SO LIEU -> tu khoa: {topic}")
            return read_topic(topic)
        log.append(f"BIA SO LIEU, bo: {sentence}")
        return OUT_OF_SCOPE
