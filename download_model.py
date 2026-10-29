"""Parallel range downloader for a Hugging Face repo (one connection here ran at ~0.4 MB/s; twelve ranges at
3–8 MB/s). Files already complete are skipped, so it resumes. Stdlib only.

  python download_model.py <repo> <dest> [glob ...]   (a folder already complete is left as it is)"""
import fnmatch
import http.client
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:                                   # the Mac's own trust store: works behind SSL-inspecting firewalls too
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    try:                               # else certifi's (Homebrew's Python finds no CA certificates of its own)
        import ssl

        import certifi
        urllib.request.install_opener(urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))))
    except ImportError:
        pass


def complete(dest):
    """Whether a model folder is whole: its config, every weight file its index lists (or one weights file), no
    unfinished parts."""
    if not os.path.isfile(os.path.join(dest, "config.json")):
        return False
    names = os.listdir(dest)
    if any(n.endswith(".part") for n in names):
        return False
    index = os.path.join(dest, "model.safetensors.index.json")
    if os.path.isfile(index):
        with open(index) as f:
            shards = set(json.load(f)["weight_map"].values())
        return all(os.path.isfile(os.path.join(dest, n)) for n in shards)
    return any(n.endswith(".safetensors") for n in names)

CHUNK = 16 * 1024 * 1024
WORKERS = 12


def files(repo):
    try:
        with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}?blobs=true") as r:
            m = json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Error: Hugging Face returned {e.code}. If a firewall blocks it, switch networks (a phone "
                         "hotspot, say) or copy the model folders from a machine that has them (see GUIDE.md).")
    except urllib.error.URLError as e:
        raise SystemExit(f"Error: cannot reach Hugging Face ({e.reason}).")
    return [(f["rfilename"], f.get("size") or 0) for f in m["siblings"]]


def cdn_url(url):
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req) as r:
        return r.url


def get_range(url, path, start, end):
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) != end - start + 1:
                raise OSError(f"short read {len(data)}")
            with open(path, "r+b") as f:
                f.seek(start)
                f.write(data)
            return len(data)
        except (OSError, http.client.HTTPException) as e:  # retry flaky ranges (timeouts, resets, short reads)
            print(f"  retry {start}: {e}", flush=True)
            time.sleep(2 + attempt)
    raise OSError(f"range {start}-{end} failed")


def fetch(repo, name, size, dest):
    out = os.path.join(dest, name)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) == size:
        return
    url = f"https://huggingface.co/{repo}/resolve/main/{name}"
    if size < CHUNK:
        urllib.request.urlretrieve(url, out)
        return
    url = cdn_url(url)
    part = out + ".part"
    with open(part, "wb") as f:
        f.truncate(size)
    t0 = time.time()
    ranges = [(s, min(s + CHUNK, size) - 1) for s in range(0, size, CHUNK)]
    with ThreadPoolExecutor(WORKERS) as ex:
        done = 0
        for n in ex.map(lambda r: get_range(url, part, *r), ranges):
            done += n
            mb = done / 1e6
            print(f"  {name}: {mb:.0f}/{size/1e6:.0f} MB, {mb/(time.time()-t0):.1f} MB/s", flush=True)
    os.replace(part, out)


def main():
    repo, dest, *globs = sys.argv[1:]
    if complete(dest):
        print(f"already complete: {dest}", flush=True)
        return
    for name, size in files(repo):
        if globs and not any(fnmatch.fnmatch(name, g) for g in globs):
            continue
        print(f"{name} ({size/1e6:.1f} MB)", flush=True)
        fetch(repo, name, size, dest)
    print("ok", repo, flush=True)


if __name__ == "__main__":
    main()
