Answers a phone call in Vietnamese. The caller speaks, the machine understands, looks the
answer up, and replies in a human voice.

Balance, last transaction, daily limit, card lock. Rates, fees, opening hours and eleven
other topics. Transfer to a person when it cannot help.

Everything runs on the machine that answers. No cloud service, no API key.

```
Zoiper --SIP--> Asterisk (Docker) --AudioSocket TCP--> switchboard.py
                                                        |-- gipformer   hear
                                                        |-- Qwen3-4B    understand
                                                        |-- Piper       speak
```

The dialplan is one line. Everything else is Python.

## A call

```
caller      tôi muốn biết số dư tài khoản
switchboard Anh chị bấm số điện thoại rồi bấm dấu thăng ạ.
caller      presses 0901234567#
switchboard Dạ số dư tài khoản của anh chị là 12 triệu 450 nghìn đồng.

caller      lãi suất tiết kiệm bao nhiêu
switchboard Dạ lãi suất tiết kiệm sáu tháng là bốn phẩy sáu phần trăm một năm...

caller      tôi muốn khoá thẻ
switchboard Anh chị xác nhận khoá thẻ ạ?
caller      đúng rồi
switchboard Dạ em đã khoá thẻ của anh chị thành công.
```

Sample phone numbers: `0901234567` `0987654321` `0912345678`

Four seconds to nine per turn on an i7-1185G7 with no discrete GPU. One call at a time.

## Install

Docker, Python and sox:

```bash
sudo apt-get install -y docker.io docker-compose-v2 python3-pip python3-venv sox
sudo usermod -aG docker $USER
```

Leave WSL and come back, or Docker reports `permission denied`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The speech recogniser, 73MB:

```bash
mkdir -p ~/gipformer && cd ~/gipformer
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('g-group-ai-lab/gipformer1.5-65M-rnnt', local_dir='.')"
```

The language model. Take the newest `bin-ubuntu-openvino-*-x64.tar.gz` from the
`ggml-org/llama.cpp` releases, and `intel-opencl-icd` to put it on the iGPU:

```bash
mkdir -p ~/llamacpp/openvino && cd ~/llamacpp
tar -xzf llama-ov.tar.gz -C openvino
sudo apt-get install -y intel-opencl-icd clinfo
```

The speech synthesiser, 63MB:

```bash
mkdir -p ~/piper && cd ~/piper
curl -L -o piper.tar.gz https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
tar -xzf piper.tar.gz
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json
```

A softphone. Zoiper 5 or Linphone, account `1001`, password `matkhau1001`, server the WSL
address from `ip addr show eth0`. Turn DTMF sending on, the phone number arrives that way.

Change the SIP passwords in `asterisk/config/pjsip.conf` before this listens to anything but
localhost.

## Running

Three terminals.

```bash
cd ~/llamacpp/openvino/llama-b*
GGML_OPENVINO_DEVICE=GPU ./llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M -c 2048 -t 4 --host 127.0.0.1 --port 8080
```

```bash
sudo service docker start
docker compose up -d
docker exec tongdai asterisk -rx "pjsip show endpoints"
```

`1001` has to read `Not in use`. `Unavailable` means the softphone has not registered, so
restart it.

```bash
cd app
source ../.venv/bin/activate
python3 switchboard.py 2>/dev/null
```

Wait for `AudioSocket dang cho o 127.0.0.1:9092`, then dial **600**.

`200` echoes your own voice back. `900` dials a person directly.

## Figures change while it runs

`app/docs/figures.json` holds the rates, the exchange rate and the gold price. Edit it and
the next caller hears the new number. No restart, no code change.

Numbers are spelled out (*"bốn phẩy sáu"*, not `4.6%`) because the synthesiser reads symbols
as silence.

## Not trusting the model

A 4B model does not follow an instruction because the prompt asks it to. Five places where it
went wrong, each blocked with a fact instead of a sentence in the prompt:

| It did this | Blocked by |
|---|---|
| Made up a phone number, copied from an example in the prompt | the number has to arrive as DTMF, a digital signal that cannot be misheard |
| Made up interest rates and a gold price | a self-composed reply containing a digit is dropped, and the topic is looked up by keyword instead |
| Called `lock_card` when the caller asked where their girlfriend was | anything that changes data waits for the caller to say yes |
| Wrote a malformed command that reached the caller's speaker | a reply still holding `@` is never played |
| Ran out of tokens mid-sentence, and the fragment was read aloud | `finish_reason` says the model stopped early, so the reply is dropped |

The third one locked a card in a test call.

## Tests

No models, no container, no phone call:

```bash
pytest
```

53 tests, under a second. A conversation without speaking, needs only llama-server:

```bash
cd tests
python3 try_without_calling.py
python3 try_without_calling.py "tôi muốn khoá thẻ" "đúng rồi"
```

`try_audiosocket.py` echoes a call back to check the audio path.
`compare_speech_models.py` times two recognisers over the same recordings.

## Layout

```
app/
  switchboard.py       sockets, audio frames, the call loop
  conversation.py      one turn: ask the model, pick an action, filter the reply
  models.py            the three models
  audiosocket.py       the AudioSocket protocol
  bank_data.py         customers and the four lookups
  bank_docs.py         documents, re-read when the file changes
  voice_library.py     keeps generated speech for next time
  transcript_fixup.py  near-homophones, "số dừa" to "số dư"
  prompt.txt
  docs/
    topics.json
    figures.json

asterisk/config/       five Asterisk config files

tests/
```

Identifiers are English. Vietnamese is left where a Vietnamese person reads or hears it: the
sentences the switchboard speaks, the prompt, the documents, and the log. `CONTRIBUTING.md`
says which is which.

## Parts

| | | License |
|---|---|---|
| Switchboard | Asterisk 23.4.1 | GPLv2 |
| Hear | `g-group-ai-lab/gipformer1.5-65M-rnnt`, sherpa-onnx int8 | MIT |
| Understand | `unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M`, llama.cpp + OpenVINO | Apache 2.0 |
| Speak | Piper `vi_VN-vais1000-medium` | MIT |
| Speak, repeated sentences | VieNeu-TTS v3-Turbo | Apache 2.0 |