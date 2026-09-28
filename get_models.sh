#!/usr/bin/env bash
set -euo pipefail

GIPFORMER_REPO="https://huggingface.co/g-group-ai-lab/gipformer1.5-68M-rnnt/resolve/main"
GIPFORMER_DIR="$HOME/gipformer"
GIPFORMER_FILES="encoder.int8.onnx decoder.int8.onnx joiner.int8.onnx tokens.txt"
GIPFORMER_ENCODER_SHA256="b528768939c7711a889be81a718ea7f2ee50d0d2d384d53f399e15b44bd9408c"

PIPER_REPO="https://huggingface.co/CakeByVPBank/piper-pgl-v4-vi_VN-version39_epoch39/resolve/main"
PIPER_DIR="$HOME/piper/cake"
PIPER_VOICE="vi_VN-csa-voice-piper-v3-medium.onnx"

LLAMA_BUILD="b11212"
LLAMA_ZIP_URL="https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_BUILD/llama-$LLAMA_BUILD-bin-win-vulkan-x64.zip"
GEMMA_URL="https://huggingface.co/ggml-org/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_0.gguf"
GEMMA_FILE="gemma-4-E2B-it-Q4_0.gguf"

GREEN=$'\033[32m'; OFF=$'\033[0m'
ok() { printf '%s  ok%s  %s\n' "$GREEN" "$OFF" "$*"; }

fetch() {
    local url=$1 target=$2
    if [ -s "$target" ]; then
        ok "$(basename "$target") already here"
        return
    fi
    mkdir -p "$(dirname "$target")"
    printf 'downloading %s\n' "$(basename "$target")"
    curl -fL --progress-bar -o "$target.part" "$url"
    mv "$target.part" "$target"
    ok "$(basename "$target")"
}

windows_home() {
    command -v cmd.exe >/dev/null || return 1
    wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')" 2>/dev/null
}

for file in $GIPFORMER_FILES; do
    fetch "$GIPFORMER_REPO/$file" "$GIPFORMER_DIR/$file"
done
echo "$GIPFORMER_ENCODER_SHA256  $GIPFORMER_DIR/encoder.int8.onnx" | sha256sum -c --quiet \
    && ok "gipformer encoder checksum"

fetch "$PIPER_REPO/$PIPER_VOICE" "$PIPER_DIR/$PIPER_VOICE"
fetch "$PIPER_REPO/$PIPER_VOICE.json" "$PIPER_DIR/$PIPER_VOICE.json"

if home="$(windows_home)"; then
    fetch "$GEMMA_URL" "$home/llamacpp/models/$GEMMA_FILE"
    llama_dir="$home/llamacpp/vulkan/llama-$LLAMA_BUILD"
    if [ -f "$llama_dir/llama-server.exe" ]; then
        ok "llama.cpp $LLAMA_BUILD for Windows already here"
    else
        fetch "$LLAMA_ZIP_URL" "$home/llamacpp/llama-$LLAMA_BUILD-win-vulkan.zip"
        mkdir -p "$llama_dir"
        python3 -m zipfile -e "$home/llamacpp/llama-$LLAMA_BUILD-win-vulkan.zip" "$llama_dir"
        ok "llama.cpp $LLAMA_BUILD unpacked to $llama_dir"
    fi
else
    printf 'no Windows side found, run.sh will download Gemma through llama-server -hf on first start\n'
fi
