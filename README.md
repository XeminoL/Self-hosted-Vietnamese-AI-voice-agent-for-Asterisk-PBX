# Vietnamese voice agent for Asterisk

A phone switchboard that answers callers in Vietnamese and runs entirely on a laptop CPU, with no GPU and no cloud service. A caller dials 600, speaks, and hears the reply about 1.5 s after finishing a sentence. It looks up an account once the number is keyed in, asks before changing anything, and hands the call to a person on extension 1002 when it cannot help. Across 488 test calls spoken by four synthetic voices through a phone codec it understood 96% of what was asked, and every miss came from a misheard word rather than a wrong decision.

[![A scripted call to 600](docs/demo-call.png)](docs/demo-call.mp4)

Asterisk takes the call and streams it over AudioSocket to the switchboard, where gipformer turns speech into text, Gemma-4-E2B on llama.cpp works out what the caller wants, and Piper speaks the answer. Plain rules settle most turns before the model is asked, which keeps replies fast and stops the model from inventing figures. The bank is only an example. Everything it says and listens for lives in `app/domain/`, so another business needs new data there and its own lookups in `app/accounts.py`, not a new switchboard.

## Running

It was built on Windows 11 with WSL and Docker, with the model running as a Windows program.

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
./get_models.sh
bash run.sh
```

Register a softphone as 1001 with the password in `asterisk/config/pjsip.conf` and dial 600. `pytest` runs the tests, and the ones that need the model skip when it is not running.

## License

Asterisk is GPLv2, gipformer and the Piper Cake voice are MIT, Gemma 4 is Apache 2.0 and llama.cpp is MIT. piper-tts is GPL-3.0, so a copy of this project that ships it is GPL-3.0 as well.
