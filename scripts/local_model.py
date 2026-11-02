"""
local_model.py - Plan B: a small open model run by Ollama (no API key, no rate limits).

In Colab, first choose a GPU (Runtime > Change runtime type > T4 GPU), then in a cell:
    import scripts.local_model as local_model
    local_model.start()          # installs Ollama, starts it, downloads the model (~4 GB, ~3-5 min)
    import config
    config.LLM_PROVIDER = "local"

On a laptop: install Ollama from https://ollama.com/download, then run
    python scripts/local_model.py
and set LLM_PROVIDER = "local" in config.py.
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # so `import config` works
import config  # noqa: E402

OLLAMA_VERSION = "0.40.13"  # pinned: Ollama publishes new versions almost every day
SERVER = "http://localhost:11434"


def server_running():
    try:
        urllib.request.urlopen(SERVER, timeout=2)
        return True
    except OSError:
        return False


def run(command):
    print("$", command, flush=True)
    subprocess.run(command, shell=True, check=True)


def start_server():
    """Start `ollama serve` in the background with workshop-friendly settings."""
    env = {**os.environ,
           "OLLAMA_CONTEXT_LENGTH": "8192",  # default is 4096; longer prompts would be cut silently
           "OLLAMA_KEEP_ALIVE": "-1"}        # keep the model loaded (default: unload after 5 idle minutes)
    log_path = ROOT / "logs" / "ollama.log"
    log_path.parent.mkdir(exist_ok=True)
    subprocess.Popen(["ollama", "serve"], env=env, stdout=open(log_path, "w"), stderr=subprocess.STDOUT)
    for _ in range(30):
        if server_running():
            return
        time.sleep(1)
    raise RuntimeError(f"Ollama did not start. Look at {log_path}")


def start(model=None):
    """Make sure an Ollama server is running and the local model is downloaded and loaded."""
    model = model or config.PROVIDERS["local"]["model"]
    if not server_running():
        if "google.colab" in sys.modules and not shutil.which("ollama"):
            if not shutil.which("nvidia-smi"):
                print("WARNING: no GPU. Each answer will take 20-40 s. Use Runtime > Change runtime type > T4 GPU.")
            run("apt-get -qq install -y zstd pciutils > /dev/null")  # the installer needs zstd; pciutils finds the GPU
            run(f"curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION={OLLAMA_VERSION} sh")
        elif not shutil.which("ollama"):
            sys.exit("Ollama is not installed. Get it from https://ollama.com/download, then run this again.")
        start_server()  # Colab has no systemd, so the installer cannot start the server for us
    run(f"ollama pull {model}")
    from openai import OpenAI
    OpenAI(base_url=f"{SERVER}/v1", api_key="ollama").chat.completions.create(
        model=model, messages=[{"role": "user", "content": "Say OK"}], max_tokens=5)  # loads the model
    run("ollama ps")  # the PROCESSOR column should say 100% GPU
    print(f'\nReady: {model}. Now use it with LLM_PROVIDER = "local" (config.py), or config.LLM_PROVIDER = "local".')


if __name__ == "__main__":
    start()
