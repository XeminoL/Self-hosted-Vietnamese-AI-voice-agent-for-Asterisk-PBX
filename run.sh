#!/usr/bin/env bash
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LLAMA_BIN="$HOME/llamacpp/llama-b10738/llama-server"
MODEL_REPO="unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M"
LLM_HOST=127.0.0.1
LLM_PORT=8080
AUDIOSOCKET_PORT=9092
SIP_PORT=5060
CONTAINER=tongdai
LLM_THREADS=4
LLM_CONTEXT=2048
LLM_READY_TIMEOUT=180
LOG_DIR="$PROJECT_DIR/logs"

RED=$'\033[31m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; OFF=$'\033[0m'

say() { printf '%s\n' "$*"; }
ok() { printf '%s  ok%s  %s\n' "$GREEN" "$OFF" "$*"; }
warn() { printf '%s warn%s %s\n' "$YELLOW" "$OFF" "$*"; }
die() { printf '%sfailed%s %s\n' "$RED" "$OFF" "$*"; exit 1; }

port_taken() {
    [ -n "$(ss -tlnH "sport = :$1" 2>/dev/null)" ]
}

container_on_port() {
    docker ps --format '{{.Names}}|{{.Ports}}' 2>/dev/null \
        | awk -F'|' -v p=":$1->" 'index($2, p) { print $1; exit }'
}

process_on_port() {
    ss -tlnpH "sport = :$1" 2>/dev/null | grep -o 'users:(("[^"]*"' | head -1 | cut -d'"' -f2
}

describe_port_user() {
    local container process
    container="$(container_on_port "$1")"
    if [ -n "$container" ]; then
        printf 'the docker container %s' "$container"
        return
    fi
    process="$(process_on_port "$1")"
    if [ -n "$process" ]; then
        printf '%s' "$process"
    else
        printf 'something this script cannot name'
    fi
}

wait_for_llm() {
    local waited=0
    while [ "$waited" -lt "$LLM_READY_TIMEOUT" ]; do
        if curl -sf "http://$LLM_HOST:$LLM_PORT/health" >/dev/null 2>&1; then
            return 0
        fi
        if ! kill -0 "$LLAMA_PID" 2>/dev/null; then
            return 1
        fi
        sleep 2
        waited=$((waited + 2))
        printf '\r  loading the model ... %ss' "$waited"
    done
    printf '\n'
    return 1
}

stop_quietly() {
    local pid=$1 name=$2
    kill -0 "$pid" 2>/dev/null || return
    kill "$pid" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do
        kill -0 "$pid" 2>/dev/null || { ok "$name stopped"; return; }
        sleep 0.5
    done
    kill -9 "$pid" 2>/dev/null
    ok "$name killed"
}

shut_down() {
    trap - EXIT INT TERM
    printf '\n'
    say "${BOLD}Shutting down${OFF}"
    [ -n "${SWITCHBOARD_PID:-}" ] && stop_quietly "$SWITCHBOARD_PID" "switchboard"
    [ -n "${LLAMA_PID:-}" ] && stop_quietly "$LLAMA_PID" "llama-server"
    if [ "${STARTED_ASTERISK:-no}" = yes ]; then
        (cd "$PROJECT_DIR" && docker compose down >/dev/null 2>&1) && ok "Asterisk stopped"
    else
        say "  Asterisk left running, it was already up before this script"
    fi
    say "Logs kept in logs/"
}

check_requirements() {
    say "${BOLD}Checking what the switchboard needs${OFF}"
    [ -x "$LLAMA_BIN" ] || die "llama-server not found at $LLAMA_BIN"
    ok "llama-server"

    [ -x "$PROJECT_DIR/.venv/bin/python" ] || die "python venv missing, run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    "$PROJECT_DIR/.venv/bin/python" -c 'import sherpa_onnx, vieneu, webrtcvad, numpy' 2>/dev/null \
        || die "python packages missing, run: .venv/bin/pip install -r requirements.txt"
    ok "python packages"

    for tool in sox docker curl; do
        command -v "$tool" >/dev/null || die "$tool not installed, run: sudo apt install $tool"
    done
    ok "sox, docker, curl"

    [ -x "$HOME/piper/piper/piper" ] || die "piper not found at ~/piper/piper/piper"
    [ -f "$HOME/piper/vi_VN-vais1000-medium.onnx" ] || die "piper voice not found at ~/piper/"
    ok "piper and its Vietnamese voice"

    for part in encoder decoder joiner; do
        [ -f "$HOME/gipformer/$part.int8.onnx" ] || die "gipformer $part.int8.onnx not found in ~/gipformer/"
    done
    ok "gipformer"

    docker info >/dev/null 2>&1 || die "docker is not running, start Docker Desktop first"
    ok "docker is running"
}

clear_previous_run() {
    local stale
    stale=$(pgrep -f 'switchboard\.py' 2>/dev/null; pgrep -f 'llama-server' 2>/dev/null)
    [ -z "$stale" ] && return

    warn "an earlier run left processes behind, probably from closing the window with X"
    for pid in $stale; do
        kill "$pid" 2>/dev/null
    done
    sleep 3
    for pid in $stale; do
        kill -9 "$pid" 2>/dev/null
    done
    sleep 1
    ok "cleared them"
}

free_the_ports() {
    say ""
    say "${BOLD}Checking the ports${OFF}"

    if port_taken "$LLM_PORT"; then
        local container
        container="$(container_on_port "$LLM_PORT")"
        printf '%s\n' "${RED}Port $LLM_PORT is already taken${OFF} by ${BOLD}$(describe_port_user "$LLM_PORT")${OFF}, and the language model needs it."
        if [ -n "$container" ]; then
            say "That container belongs to another project. Stop it yourself with:"
            say "    ${BOLD}docker stop $container${OFF}"
            say "then start it again with  ${BOLD}docker start $container${OFF}  when you are done here."
        fi
        exit 1
    fi
    ok "port $LLM_PORT free for the language model"

    if port_taken "$AUDIOSOCKET_PORT"; then
        printf '%s\n' "${RED}Port $AUDIOSOCKET_PORT is taken${OFF} by $(describe_port_user "$AUDIOSOCKET_PORT"). Another copy of the switchboard is probably still running."
        exit 1
    fi
    ok "port $AUDIOSOCKET_PORT free for the audio stream"

    if port_taken "$SIP_PORT" && [ "$(container_on_port "$SIP_PORT")" != "$CONTAINER" ]; then
        warn "port $SIP_PORT is taken by $(describe_port_user "$SIP_PORT"), the softphone may fail to register"
    fi
}

start_asterisk() {
    say ""
    say "${BOLD}Starting Asterisk${OFF}"
    if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = true ]; then
        ok "already running"
        return
    fi
    (cd "$PROJECT_DIR" && docker compose up -d >"$LOG_DIR/asterisk.log" 2>&1) \
        || die "docker compose failed, see logs/asterisk.log"
    STARTED_ASTERISK=yes
    ok "container $CONTAINER is up, softphones can register on port $SIP_PORT"
}

start_llm() {
    say ""
    say "${BOLD}Starting the language model${OFF} (first run downloads about 2.5 GB)"
    "$LLAMA_BIN" -hf "$MODEL_REPO" -c "$LLM_CONTEXT" -t "$LLM_THREADS" \
        --host "$LLM_HOST" --port "$LLM_PORT" >"$LOG_DIR/llama.log" 2>&1 &
    LLAMA_PID=$!
    wait_for_llm || die "the language model did not come up, see logs/llama.log"
    printf '\r'
    ok "answering on $LLM_HOST:$LLM_PORT"
}

start_switchboard() {
    say ""
    say "${BOLD}Starting the switchboard${OFF} (loading the speech models takes a minute)"
    say ""
    say "Dial 600 from your softphone. Press Ctrl+C here to stop everything."
    say ""
    cd "$PROJECT_DIR/app" || die "cannot enter app/"
    PYTHONUNBUFFERED=1 "$PROJECT_DIR/.venv/bin/python" switchboard.py &
    SWITCHBOARD_PID=$!
    while kill -0 "$SWITCHBOARD_PID" 2>/dev/null; do
        sleep 1 &
        wait $! 2>/dev/null
    done
    wait "$SWITCHBOARD_PID" 2>/dev/null
    SWITCHBOARD_PID=
}

mkdir -p "$LOG_DIR"
trap shut_down EXIT INT TERM

say ""
say "${BOLD}Vietnamese voice switchboard${OFF}"
say ""
check_requirements
clear_previous_run
free_the_ports
start_asterisk
start_llm
start_switchboard