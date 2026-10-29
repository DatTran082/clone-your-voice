"""The engine behind the voice MCP server (server.py): speech to text with Whisper large-v3-turbo and voice cloning
with VoxCPM2, both on Apple Silicon through MLX, plus a small library of reference voices. General purpose:
any script, any voice; Vietnamese gets numbers, dates and prices spelled out before reading.

Everything here is synchronous and must run on one thread (MLX keeps its GPU stream per thread): server.py calls it
through a single-worker executor. Models, the env, the voice library and the user's pronunciations live in
$VOICE_MCP_HOME (default ~/.cache/voice-mcp); generated audio goes to $VOICE_MCP_OUTPUT (default
~/Documents/voice-mcp-output).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from vi_numbers import spell_out

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")   # VoxCPM2's config warns harmlessly on every load

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("VOICE_MCP_HOME", Path.home() / ".cache" / "voice-mcp"))
OUTPUT = Path(os.environ.get("VOICE_MCP_OUTPUT", Path.home() / "Documents" / "voice-mcp-output"))
WHISPER = HOME / "whisper-turbo"
VOXCPM = HOME / "VoxCPM2-bf16"
VOICES = HOME / "voices"
PRONOUNCE = [HERE / "pronunciations.txt", HOME / "pronunciations.txt"]   # the package's, then the user's
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
REF_RANGE = (5.0, 25.0)      # reference clip length that clones well, s
SPEECH_RMS = 0.08            # every take's level when joined (≈ −22 dBFS RMS: room left for a final loudness pass)
CUE_CHARS = 42               # a subtitle line's length at most, characters
CUE_PAUSE = 0.35             # a pause this long (s) between two words starts a new subtitle line
MAX_LINES, MAX_CHARS = 80, 500
MODES = ("clone", "clone_style", "design")
_MODEL: dict[str, Any] = {}


class VoiceError(ValueError):
    """A problem the caller can fix (bad input, missing setup); its message is shown to the user."""


def _need(path, what):
    if not path.exists():
        raise VoiceError(f"{what} is missing at {path}. Run install.sh first.")


def _file(path, what="file"):
    p = Path(path).expanduser()
    if not p.is_file():
        raise VoiceError(f"{what} not found: {p}")
    return p


# ------------------------------------------------------------------ audio

def to_wav(src, dst, start=None, end=None):
    """Any audio or video → mono 16-bit WAV at its own rate (ffmpeg), optionally a time range."""
    if shutil.which("ffmpeg") is None:
        raise VoiceError("ffmpeg not found (brew install ffmpeg).")
    cut = (["-ss", f"{start}"] if start is not None else []) + (["-to", f"{end}"] if end is not None else [])
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *cut, "-i", str(src), "-ac", "1",
                        "-c:a", "pcm_s16le", str(dst)], capture_output=True, text=True, check=False)
    if r.returncode != 0 or not Path(dst).exists():
        raise VoiceError(f"ffmpeg could not read {src}: {r.stderr.strip()}")
    return Path(dst)


def trim(wav, sr, floor_db=-40.0):
    level = 20 * np.log10(np.abs(wav) + 1e-9)
    idx = np.where(level > floor_db)[0]
    if len(idx) == 0:
        return wav
    return wav[max(idx[0] - int(0.02 * sr), 0):min(idx[-1] + int(0.08 * sr), len(wav))]


def _even(wav):
    return wav / (np.sqrt(np.mean(wav ** 2)) + 1e-9) * SPEECH_RMS


# ------------------------------------------------------------------ speech to text

def _whisper(path, language, words=False):
    import mlx_whisper
    _need(WHISPER, "The Whisper model")
    return mlx_whisper.transcribe(str(path), path_or_hf_repo=str(WHISPER), language=language or None,
                                  word_timestamps=words, condition_on_previous_text=False)


def cues(result, width=CUE_CHARS):
    """Subtitle lines from the word times: a new line where the speaker pauses, after a sentence's or clause's end,
    or before it would pass `width` characters unless the sentence ends within the next two words."""
    words = [w for s in result["segments"] for w in s.get("words", [])]
    say = lambda ws: " ".join(w["word"].strip() for w in ws)
    ends = lambda w: w["word"].strip().endswith((".", "!", "?", "…"))
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and w["start"] - cur[-1]["end"] >= CUE_PAUSE:
            out.append(cur); cur = []
        if cur and len(say(cur + [w])) > width:
            k = next((j for j in range(i, min(i + 2, len(words))) if ends(words[j])), None)
            if k is None or len(say(cur + words[i:k + 1])) > width * 1.3:
                out.append(cur); cur = []
        cur.append(w)
        if ends(w) or (w["word"].strip().endswith((",", ";", ":")) and len(say(cur)) > width * 0.6):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return [{"start": round(c[0]["start"], 2), "end": round(c[-1]["end"], 2), "text": say(c)} for c in out]


def _srt_time(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def transcribe(audio_path, language="vi", output_dir=None, formats=("txt", "srt", "json")):
    """Speech → text: the full text, subtitle cues, and the files written (txt, srt, json with word times)."""
    src = _file(audio_path, "Audio file")
    kinds = set(formats)
    if not kinds <= {"txt", "srt", "json"}:
        raise VoiceError("formats may only be txt, srt, json.")
    result = _whisper(src, language, words=True)
    lines = cues(result)
    dest = Path(output_dir).expanduser() if output_dir else src.parent
    dest.mkdir(parents=True, exist_ok=True)
    stem, files = dest / src.stem, []
    text = result["text"].strip()
    if "txt" in kinds:
        files.append(stem.with_suffix(".txt")); files[-1].write_text(text + "\n", encoding="utf-8")
    if "srt" in kinds:
        files.append(stem.with_suffix(".srt"))
        files[-1].write_text("\n".join(f"{i}\n{_srt_time(c['start'])} --> {_srt_time(c['end'])}\n{c['text']}\n"
                                       for i, c in enumerate(lines, 1)), encoding="utf-8")
    if "json" in kinds:
        segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip(),
                 "words": [{"start": round(w["start"], 2), "end": round(w["end"], 2), "word": w["word"].strip()}
                           for w in s.get("words", [])]} for s in result["segments"]]
        files.append(stem.with_suffix(".json"))
        files[-1].write_text(json.dumps({"text": text, "segments": segs}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    end = result["segments"][-1]["end"] if result["segments"] else 0.0
    return {"text": text, "speech_until_seconds": round(end, 2), "cues": lines, "files": [str(f) for f in files]}


# ------------------------------------------------------------------ voice library

def _voice_dir(name):
    if not NAME.match(name or ""):
        raise VoiceError("A voice name is 1–40 characters: lower-case letters, digits and hyphens, e.g. 'lan-warm'.")
    return VOICES / name


def _voice(name):
    d = _voice_dir(name)
    if not (d / "reference.wav").exists():
        known = ", ".join(v["name"] for v in list_voices()) or "none yet"
        raise VoiceError(f"No voice named '{name}' (registered: {known}). Use register_voice first.")
    meta = json.loads((d / "voice.json").read_text(encoding="utf-8"))
    return d, meta


def register_voice(name, audio_path, consent_confirmed, start_seconds=None, end_seconds=None, transcript=None,
                   notes="", language="vi"):
    """Keep a reference clip under a name. Without a transcript Whisper drafts one, which must then be checked
    word for word (set_voice_transcript): 'clone' mode follows it."""
    if consent_confirmed is not True:
        raise VoiceError("Only voices whose speaker agreed to be cloned may be registered: confirm consent first.")
    src = _file(audio_path, "Audio file")
    if start_seconds is not None and end_seconds is not None and end_seconds <= start_seconds:
        raise VoiceError("end_seconds must be after start_seconds.")
    d = _voice_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    ref = to_wav(src, d / "reference.wav", start_seconds, end_seconds)
    seconds = sf.info(str(ref)).duration
    warnings = []
    if not REF_RANGE[0] <= seconds <= REF_RANGE[1]:
        warnings.append(f"The clip is {seconds:.1f} s; {REF_RANGE[0]:.0f}–{REF_RANGE[1]:.0f} s clones best.")
    source = "given"
    if not transcript:
        transcript, source = _whisper(ref, language)["text"].strip(), "whisper-draft"
        warnings.append("The transcript is Whisper's draft: have it checked word for word, then set_voice_transcript.")
    (d / "reference.txt").write_text(transcript.strip() + "\n", encoding="utf-8")
    meta = {"name": name, "source": str(src), "start_seconds": start_seconds, "end_seconds": end_seconds,
            "seconds": round(seconds, 2), "transcript_source": source, "consent_confirmed": True,
            "notes": notes, "registered": time.strftime("%Y-%m-%d %H:%M")}
    (d / "voice.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return {**meta, "reference_audio": str(ref), "transcript": transcript.strip(), "warnings": warnings}


def set_voice_transcript(name, transcript):
    d, meta = _voice(name)
    if not transcript.strip():
        raise VoiceError("The transcript is empty.")
    (d / "reference.txt").write_text(transcript.strip() + "\n", encoding="utf-8")
    meta["transcript_source"] = "checked"
    (d / "voice.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"name": name, "transcript": transcript.strip(), "transcript_source": "checked"}


def list_voices():
    out = []
    for d in sorted(VOICES.glob("*/voice.json")):
        meta = json.loads(d.read_text(encoding="utf-8"))
        meta["transcript"] = (d.parent / "reference.txt").read_text(encoding="utf-8").strip()
        meta["reference_audio"] = str(d.parent / "reference.wav")
        out.append(meta)
    return out


# ------------------------------------------------------------------ pronunciations and spoken forms

def pronunciations():
    """'Word = how to say it' pairs: the package's list, then the user's (which win)."""
    pairs = {}
    for p in PRONOUNCE:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    k, v = (s.strip() for s in line.split("=", 1))
                    if k:
                        pairs[k.lower()] = (k, v)
    return list(pairs.values())


def set_pronunciation(word, spoken):
    if not word.strip() or not spoken.strip() or "=" in word + spoken or "\n" in word + spoken:
        raise VoiceError("word and spoken must be non-empty single lines without '='.")
    path = PRONOUNCE[1]
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    rows = [r for r in rows if not ("=" in r and r.split("=", 1)[0].strip().lower() == word.strip().lower())]
    rows.append(f"{word.strip()} = {spoken.strip()}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"word": word.strip(), "spoken": spoken.strip(), "all": [f"{k} = {v}" for k, v in pronunciations()]}


def spoken(text, pairs, language="vi"):
    """What the model is given: the pronunciations applied; in Vietnamese also numbers, dates and prices in words."""
    for k, v in pairs:
        text = re.sub(rf"(?<!\w){re.escape(k)}(?!\w)", v, text, flags=re.IGNORECASE)
    return spell_out(text) if language == "vi" else text


def script_lines(script):
    rows = [s.strip() for s in script.splitlines()]
    rows = [s for s in rows if s and not s.startswith("#")]
    if not rows:
        raise VoiceError("The script has no lines to read.")
    if len(rows) > MAX_LINES:
        raise VoiceError(f"The script has {len(rows)} lines; at most {MAX_LINES} per call.")
    long = [i + 1 for i, s in enumerate(rows) if len(s) > MAX_CHARS]
    if long:
        raise VoiceError(f"Lines {long} are longer than {MAX_CHARS} characters: split them into sentences.")
    return rows


# ------------------------------------------------------------------ text to speech in a cloned voice

def _syllables(text):
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text.lower()))


def wrong_syllables(ref, heard, language="vi"):
    """Word (in Vietnamese: syllable) edit distance; tones and accents count ('hồn' ≠ 'hôn')."""
    x, y = _syllables(ref), _syllables(spell_out(heard) if language == "vi" else heard)
    d = list(range(len(y) + 1))
    for i in range(1, len(x) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(y) + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x[i - 1] != y[j - 1]))
    return d[len(y)]


def _voxcpm():
    if "vox" not in _MODEL:
        from mlx_audio.tts.utils import load
        _need(VOXCPM, "The VoxCPM2 model")
        _MODEL["vox"] = load(str(VOXCPM))
    return _MODEL["vox"]


def _clone_kwargs(mode, voice, reference_audio, reference_transcript, style, tmp):
    if mode not in MODES:
        raise VoiceError(f"mode must be one of {', '.join(MODES)}.")
    if mode == "design":
        if not style:
            raise VoiceError("mode 'design' needs a style describing the voice, best in English "
                             "(e.g. \"A young woman's voice, warm and bright, speaking slowly\").")
        return {"instruct": style}, None
    if voice:
        d, _ = _voice(voice)
        ref, text = d / "reference.wav", (d / "reference.txt").read_text(encoding="utf-8").strip()
    elif reference_audio:
        ref, text = to_wav(_file(reference_audio, "Reference audio"), Path(tmp) / "ref.wav"), reference_transcript
    else:
        raise VoiceError("Give a registered voice (or reference_audio), or use mode 'design'.")
    if mode == "clone_style":
        return {"ref_audio": str(ref), **({"instruct": style} if style else {})}, str(ref)
    if not text:
        raise VoiceError("mode 'clone' needs the reference's exact transcript (reference_transcript).")
    return {"ref_audio": str(ref), "prompt_audio": str(ref), "prompt_text": text + " "}, str(ref)


def synthesize(script, voice=None, mode="clone", style=None, takes=3, score=True, join=True, pause_seconds=0.5,
               output_dir=None, seed=1000, steps=16, cfg=2.0, language="vi", reference_audio=None,
               reference_transcript=None, progress=None):
    """Read each script line `takes` times in the voice; with `score`, Whisper reads every take back and the take
    with the fewest wrong syllables (then the shortest) becomes line-NN_best.wav; with `join`, the lines' best takes
    (or first) are joined into joined.wav. `progress(done, total, message)` is called after each take."""
    import mlx.core as mx
    for key, val, lo, hi in (("takes", takes, 1, 8), ("steps", steps, 4, 32), ("cfg", cfg, 2.0, 4.0),
                             ("pause_seconds", pause_seconds, 0.0, 3.0)):
        if not lo <= val <= hi:
            raise VoiceError(f"{key} must be between {lo} and {hi}.")
    rows = script_lines(script)
    pairs = pronunciations()
    out = Path(output_dir).expanduser() if output_dir else OUTPUT / time.strftime(f"%Y%m%d-%H%M%S-{voice or mode}")
    out.mkdir(parents=True, exist_ok=True)
    total, done = len(rows) * takes * (2 if score else 1), 0
    with tempfile.TemporaryDirectory() as tmp:
        kw, ref = _clone_kwargs(mode, voice, reference_audio, reference_transcript, style, tmp)
        model = _voxcpm()
        sr = model.sample_rate
        lines = []
        for i, text in enumerate(rows, 1):
            say = spoken(text, pairs, language)
            line = {"line": i, "text": text, "spoken": say, "takes": []}
            for k in range(takes):
                mx.random.seed(seed + k)
                wav = np.concatenate([np.array(r.audio) for r in model.generate(
                    text=say, inference_timesteps=steps, cfg_value=cfg, **kw)]).astype(np.float32)
                p = out / f"line-{i:02d}_{k}.wav"
                sf.write(str(p), wav, sr)
                line["takes"].append({"take": k, "seed": seed + k, "file": str(p), "seconds": round(len(wav) / sr, 2)})
                done += 1
                if progress:
                    progress(done, total, f"line {i}/{len(rows)}, take {k + 1}/{takes}")
            lines.append(line)
    if score:
        for line in lines:
            for t in line["takes"]:
                t["heard"] = _whisper(t["file"], language)["text"].strip()
                t["wrong_syllables"] = wrong_syllables(line["spoken"], t["heard"], language)
                done += 1
                if progress:
                    progress(done, total, f"scoring line {line['line']}")
            best = min(line["takes"], key=lambda t: (t["wrong_syllables"], t["seconds"]))
            line["best"] = str(out / f"line-{line['line']:02d}_best.wav")
            line["best_take"] = best["take"]
            shutil.copyfile(best["file"], line["best"])
        _score_table(lines, out / "SCORES.md")
    joined = None
    if join:
        gap = np.zeros(int(pause_seconds * sr), dtype=np.float32)
        parts = []
        for line in lines:
            wav, _ = sf.read(line.get("best") or line["takes"][0]["file"], dtype="float32")
            parts += [_even(trim(wav, sr)), gap]
        joined = out / "joined.wav"
        sf.write(str(joined), np.clip(np.concatenate(parts[:-1]), -0.99, 0.99), sr)
    result = {"output_dir": str(out), "voice": voice, "mode": mode, "reference_audio": ref, "sample_rate": sr,
              "lines": lines, "joined": str(joined) if joined else None,
              "scores": str(out / "SCORES.md") if score else None,
              "note": "Scores only rank takes (Whisper mishears too): the user must listen before use. "
                      "Posts using a cloned voice must carry the platform's AI-content label."}
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def _score_table(lines, path):
    rows = ["# Takes and scores", "",
            ("Wrong = syllables Whisper heard differently from the line (tones included). Whisper mishears too, "
             "so this only ranks the takes; listen before use. ★ = chosen."), "",
            "| Line | Take | Wrong | Seconds | Whisper heard |", "|---|---|---|---|---|"]
    for line in lines:
        for t in line["takes"]:
            star = " ★" if t["take"] == line.get("best_take") else ""
            rows.append(f"| {line['line']}{star} | {t['take']} | {t['wrong_syllables']} | {t['seconds']} | {t['heard']} |")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def status():
    """What is installed: models, voices, pronunciations."""
    return {"home": str(HOME), "output": str(OUTPUT), "voxcpm2": VOXCPM.exists(), "whisper": WHISPER.exists(),
            "ffmpeg": shutil.which("ffmpeg") is not None, "voices": [v["name"] for v in list_voices()],
            "pronunciations": [f"{k} = {v}" for k, v in pronunciations()]}
