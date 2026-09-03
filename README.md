A phone switchboard that answers in Vietnamese with no cloud service behind it.

```
Zoiper --SIP--> Asterisk (Docker) --AudioSocket TCP--> switchboard.py
                                                        |-- gipformer   
                                                        |-- Qwen3-4B    
                                                        |-- Piper       
```

## Models

| | | License |
|---|---|---|
| Switchboard | Asterisk 23.4.1 | GPLv2 |
| Hear | gipformer-65M | MIT |
| Understand | Qwen3-4B | Apache 2.0 |
| Speak | Piper | MIT |
| Speak, repeated sentences | VieNeu-TTS v3-Turbo | Apache 2.0 |

## Running

llama-server on `127.0.0.1:8080`, with `GGML_OPENVINO_DEVICE=GPU` for the Intel iGPU:

```bash
GGML_OPENVINO_DEVICE=GPU ./llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M -c 2048 -t 4 --host 127.0.0.1 --port 8080
```

```bash
docker compose up -d
cd app && python3 switchboard.py 2>/dev/null
```

Register a softphone as `1001` and use Zoiper 5 to dial:

**600**: the switchboard.
**200**: echoes the caller back.
**900**: dials a person.