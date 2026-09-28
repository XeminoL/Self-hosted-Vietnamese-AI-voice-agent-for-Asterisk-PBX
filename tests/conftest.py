import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import accounts
import llm_client


@pytest.fixture(autouse=True)
def fresh_customers():
    accounts.reset_customers()


@pytest.fixture(autouse=True)
def no_real_model(request, monkeypatch):
    if request.node.get_closest_marker("real_model"):
        return

    def refuse(history, slot=None):
        raise AssertionError("the model was asked but the test gave it no reply")

    monkeypatch.setattr(llm_client, "ask", refuse)


@pytest.fixture
def model(monkeypatch):
    replies = []

    def answer_from_script(history, slot=None):
        assert replies, "the model was asked more often than the test expected"
        return llm_client.ModelReply(replies.pop(0), False, {})

    monkeypatch.setattr(llm_client, "ask", answer_from_script)
    return replies
