import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

SAMPLE_SECONDS = 2.0
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")
REPLAY = Path(__file__).resolve().parent / "replay_calls.py"
WINDOWS_SAMPLE = (
    "$p = Get-Process llama-server -ErrorAction SilentlyContinue | Select-Object -First 1;"
    "$t = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter \"Name='_Total'\").PercentProcessorTime;"
    "if ($p) { \"$($p.CPU) $($p.WorkingSet64) $t\" } else { \"0 0 $t\" }"
)


def switchboard_pid():
    found = subprocess.run(["pgrep", "-f", "switchboard.py"], capture_output=True, text=True).stdout.split()
    if not found:
        sys.exit("the switchboard is not running")
    return int(found[0])


def wsl_sample(pid):
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    cpu_seconds = (int(fields[11]) + int(fields[12])) / CLOCK_TICKS
    rss_kb = next(int(line.split()[1]) for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                  if line.startswith("VmRSS"))
    return cpu_seconds, rss_kb / 1024


def windows_sample():
    output = subprocess.run(["powershell.exe", "-NoProfile", "-Command", WINDOWS_SAMPLE],
                            capture_output=True, text=True).stdout.split()
    cpu_seconds, working_set, total = (float(value.replace(",", ".")) for value in output[:3])
    return cpu_seconds, working_set / 2 ** 20, total


def sample_until(done, pid, rows):
    last_wsl, _ = wsl_sample(pid)
    last_windows, _, _ = windows_sample()
    last_time = time.monotonic()
    while not done.is_set():
        time.sleep(SAMPLE_SECONDS)
        now = time.monotonic()
        wsl_cpu, wsl_mb = wsl_sample(pid)
        windows_cpu, windows_mb, total = windows_sample()
        elapsed = now - last_time
        rows.append({"switchboard_cores": (wsl_cpu - last_wsl) / elapsed, "switchboard_mb": wsl_mb,
                     "llm_cores": (windows_cpu - last_windows) / elapsed, "llm_mb": windows_mb,
                     "machine_percent": total})
        last_wsl, last_windows, last_time = wsl_cpu, windows_cpu, now


def main():
    together = sys.argv[1:2] == ["together"]
    scenarios = sys.argv[2:] or ["hoi_tai_lieu", "khoa_the_dong_y"]
    rows = []
    done = threading.Event()
    sampler = threading.Thread(target=sample_until, args=(done, switchboard_pid(), rows))
    sampler.start()
    replay = subprocess.run([sys.executable, str(REPLAY), *(["--together"] if together else []), *scenarios],
                            capture_output=True, text=True)
    done.set()
    sampler.join()
    print("\n".join(line for line in replay.stdout.splitlines() if line.strip()))
    how = "calls started together" if together else "one call at a time"
    print(f"\nload with {how}, {len(rows)} samples every {SAMPLE_SECONDS:.0f}s:")
    for key, unit in (("switchboard_cores", "cores"), ("switchboard_mb", "MB"),
                      ("llm_cores", "cores"), ("llm_mb", "MB"), ("machine_percent", "% of all CPUs")):
        values = [row[key] for row in rows]
        print(f"  {key:18s} mean {statistics.mean(values):7.1f}  max {max(values):7.1f}  {unit}")


if __name__ == "__main__":
    main()
