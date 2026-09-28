A phone switchboard that answers in Vietnamese but no need for GPU and cloud service to use, only CPU and RAM.

(​I use a bank assistant as an example, but you can customize it for any use case. Also I use low-end laptop to run this.)

```
Zoiper --SIP--> Asterisk (Docker) --AudioSocket TCP--> switchboard.py
                     ^                                   |-- gipformer        hear
                     |                                   |-- Gemma-4-E2B      understand (llama.cpp on Windows, CPU)
                     +------- AMI redirect to 1002 ------|-- Piper Cake       speak
```

## Demo

[![A scripted call to 600, click for the video](docs/demo-call.png)](docs/demo-call.mp4)

[`docs/demo-call.mp4`](docs/demo-call.mp4), 60 s: a savings question, "that's wrong, I asked about gold", a card lock with the number keyed in and a yes, thanks and goodbye. The switchboard side is the current build as it sounds on the line. The caller is Piper speaker 1 sent through a μ-law phone codec, not a person. `tools/record_demo_call.py` records it.

An earlier call made from Zoiper on the older build (Qwen3-4B on the iGPU, VieNeu voice), so the voice and timing there are not the current ones:

![Zoiper in a call to 600](docs/call.png)

https://github.com/user-attachments/assets/eff0362e-6530-438b-a0b8-af9bb8bede9f

## What it does

- Answers 19 topics (interest rates, fees, opening hours, lost card...). Each topic has three phrasings and the same sentence is never said twice in a row.
- Reads a balance, the last transaction or the daily limit, and locks a card, once the caller keys in a phone number and `#`. Locking asks for a yes first.
- Key menu: 1 balance, 2 last transaction, 3 limit, 4 lock card, 0 staff, 9 reads the menu. `#` while it is talking cuts the reply short.
- Transfers to extension 1002 when the caller asks for a person, says the answer is wrong twice in a row, or presses 0.
- After 8 s of silence it asks if the caller is still there, then says goodbye and hangs up.
- One call at a time. A second caller hears a hold notice and is connected when the line frees.
- Every call is written to `app/calls/*.jsonl` with the time each stage took.

The model only decides when the rules cannot: a question with a clear topic keyword, a yes or no to a confirmation, a key press, a goodbye or a single word of noise never reaches it.

## Using it for something other than a bank

Everything the bank says or listens for lives in `app/domain/`. The code does not know it is a bank.

| File | What to change |
|---|---|
| `topics.json` | the questions it can answer: three phrasings per topic and the keywords that pick it |
| `figures.json` | numbers the answers quote, like prices or rates, so they can change without touching the sentences |
| `phrases.json` | every fixed sentence: greeting, asking for a number, goodbye, hold notice, the menu |
| `words.json` | what the caller might say: yes, no, goodbye, asking for a person, being annoyed |
| `menu.json` | which key runs which lookup |
| `customers.json` | the records a lookup reads, keyed by phone number |
| `prompt.txt` | who the assistant is and what it should never make up |

For a clinic, for example, the topics become opening hours, prices and which doctor works which day, and the customer records become appointments. The lookups themselves (check the balance, lock the card) are the only part written in code, in `app/accounts.py`: replace those four functions and the `LOOKUPS` table with the ones the new place needs, and list the ones that change data in `NEEDS_CONFIRMATION`.

After changing `app/domain/`, run `pytest`. The first start after a change takes about 25 s longer while the model reads the new prompt.

## Models and licenses

| | | License |
|---|---|---|
| Switchboard | Asterisk 23.4.1 (Docker) | GPLv2 |
| Hear | [gipformer1.5-68M-rnnt](https://huggingface.co/g-group-ai-lab/gipformer1.5-68M-rnnt) through sherpa-onnx | MIT, sherpa-onnx Apache 2.0 |
| Understand | [gemma-4-E2B-it Q4_0](https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF) on llama.cpp b11212 | Apache 2.0, llama.cpp MIT |
| Speak | [Piper Cake vi_VN](https://huggingface.co/CakeByVPBank/piper-pgl-v4-vi_VN-version39_epoch39), speaker 0, through piper-tts 1.8 | MIT, piper-tts GPL-3.0 |
| Voice activity, resampling | webrtcvad-wheels, soxr | MIT, LGPL-2.1 |

piper-tts is GPL-3.0, so a copy of this project that ships it falls under GPL-3.0 too.

## Running

Windows 11 with WSL (Ubuntu) and Docker. The model runs as a Windows program because Intel ships no Vulkan driver inside WSL, and the Windows firewall blocks WSL from calling out to Windows, so `app/llm_bridge.py` opens the connection from the Windows side instead.

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
./get_models.sh
```

`get_models.sh` puts gipformer in `~/gipformer`, the Piper voice in `~/piper/cake`, and Gemma plus llama.cpp in `%USERPROFILE%\llamacpp`. Then double-click `Start switchboard.bat` (or `bash run.sh` inside WSL). It starts Asterisk, the model and the switchboard, and stops all of them on Ctrl+C. Port 8080 has to be free.

I also set `processors=6` in `%USERPROFILE%\.wslconfig`, which leaves two threads to Windows so the screen does not stutter while the model is thinking.

Register a softphone as `1001` (the passwords are in `asterisk/config/pjsip.conf`) and dial:

**600**: the switchboard.
**200**: echoes the caller back.
**900**: dials a person on 1002.

A second softphone on `1002` receives the transfers.

## Numbers

Measured on 28/09 on an i7-1185G7 (4 cores, no graphics card, 32 GB), with `tools/replay_calls.py` playing the eight calls right after a fresh start and `tools/latency_report.py` reading the call logs. The caller voice is Piper speaker 1. 20 spoken turns.

| Stage | p50 | p95 |
|---|---|---|
| wait for the caller to stop | 0.80 s | 0.80 s |
| hear | 0.09 s | 0.14 s |
| understand | 0.10 s | 1.69 s |
| speak | 0.51 s | 0.72 s |
| caller stops -> reply starts | 1.49 s | 2.66 s |

The slowest turn was 3.61 s. The p95 comes from turns that reach the model; the rest are answered by the rules. Under load the laptop throttles to about 54% of its clock.

During a call the switchboard uses 0.3 of a core on average (1.8 at peak) and about 500 MB, llama-server 2.6 GB with peaks of 3 to 4 cores while it answers.

Two calls at once took up to 15 s per turn: llama-server has one slot, and the two conversations keep pushing each other's prompt out of the cache. That is why it holds the second caller instead.

### 122 sentences, four voices

`tools/spoken_test_set.tsv` has 122 caller sentences, each labelled with what the switchboard should do: one of the 19 topics, a lookup on the caller's own account, a transfer, a goodbye, or small talk. `tools/read_test_set.py` phones each one in as its own call, spoken by Piper Cake speakers 1 to 4 (the switchboard itself is speaker 0) through a μ-law phone codec. `tools/score_recordings.py` then reads the call logs.

| Caller voice | Word error rate | Understood |
|---|---|---|
| speaker 1 | 1.3% | 119/122 |
| speaker 2 | 1.7% | 119/122 |
| speaker 3 | 4.4% | 116/122 |
| speaker 4 | 4.9% | 115/122 |
| all four | 3.1% of 3,288 words | 469/488 (96.1%) |

Every miss started as a mishearing. "usd" was lost in all four voices, "để trống" came back as "để chống" in three, "chuyển" as "truyền" or "chuyện" in three, and "người thật hay máy" as "người thật hai máy" in two, which sends the caller to staff instead of answering. These are synthetic voices reading clean text. A person on a real line has not been measured yet; the same scripts score that run.

## Tests and tools

```bash
.venv/bin/python -m pytest
```

The two tests in `tests/test_model_battery.py` ask the running model 26 questions and skip when it is not up. The rest use a scripted model.

With the switchboard running:

- `tools/replay_calls.py` plays eight calls (card lock yes and no, key menu, documents, a caller who will not dial, silence, `#`, a second caller on hold) and checks each reply by transcribing it.
- `tools/measure_load.py` does the same while sampling CPU and RAM.
- `tools/latency_report.py --since "2026-09-28 10:00"` prints the table above from the call logs.
- `tools/chat.py "câu hỏi"` talks to the conversation by text, without a phone.
- `tools/read_test_set.py --voice 1` phones in the 122 sentences with a Piper voice.
- `tools/score_recordings.py --since "2026-09-28 10:37"` scores them from the call logs. For a run with a person, start with `RECORD_CALLS=1 bash run.sh` and read the lines into Zoiper one per turn.
- `tools/record_demo_call.py /tmp/demo` records the demo call above, both directions, with the text and timing of each line.