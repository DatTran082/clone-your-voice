"""Voice MCP server (stdio): lets an AI assistant turn a script into speech in a cloned or designed voice and
transcribe audio, locally on a Mac with Apple Silicon (MLX). The work is voice_core.py's; this file exposes it as
MCP tools.

Every engine call runs on one dedicated thread: MLX keeps its GPU stream per thread, and the SDK would otherwise run
each sync tool on whichever worker thread is free. Models load on first use and stay loaded.

  claude mcp add --scope user voice -- <this folder>/voice-mcp
"""
import asyncio
import functools
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

import voice_core as V

ENGINE = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx")

INSTRUCTIONS = """Local voice tools: Whisper large-v3-turbo for speech to text, VoxCPM2 for text to speech with voice
cloning or voice design (about 30 languages; `language` defaults to Vietnamese, "vi").

Workflow for a voice-over:
1. list_voices. If the wanted voice is not there, register_voice from a clean 10–20 s recording of one speaker
   (no music). Only with the speaker's consent: ask the user, never assume it.
2. If register_voice returned a Whisper draft transcript, show it to the user and have it corrected word for word,
   then set_voice_transcript: 'clone' mode follows that transcript, and errors in it make the voice drift.
3. synthesize_speech with the script, one sentence or phrase per line (punctuation sets the pauses). Numbers, dates
   (30/11) and prices (25.000đ) are spelled out automatically in Vietnamese; names the model misreads go in
   set_pronunciation (the list is in voice_status).
4. Report the files: each line's takes, the chosen best take and joined.wav. Whisper's scores only rank takes:
   tell the user to listen before using them, and that posts with a cloned voice need the AI-content label.

Synthesis takes about 15 s per take of a short line (plus ~3 s per take when scoring); keep scripts short or
lower `takes` for quick drafts."""

mcp = MCPServer("voice", instructions=INSTRUCTIONS, version="1.0.0", log_level="WARNING")


async def _run(fn, *args, ctx: Context | None = None, **kwargs):
    """fn on the engine thread; VoiceError becomes a message the model sees; progress reaches the client."""
    loop = asyncio.get_running_loop()
    if ctx is not None and "progress" in fn.__code__.co_varnames:
        def progress(done, total, message):
            asyncio.run_coroutine_threadsafe(ctx.report_progress(done, total, message), loop)
        kwargs["progress"] = progress
    try:
        return await loop.run_in_executor(ENGINE, functools.partial(fn, *args, **kwargs))
    except V.VoiceError as e:
        raise ToolError(str(e)) from e
    except Exception as e:                    # a local tool: the model may see what broke
        traceback.print_exc(file=sys.stderr)
        raise ToolError(f"{type(e).__name__}: {e}") from e


@mcp.tool(annotations=ToolAnnotations(title="Voice tools status", read_only_hint=True, open_world_hint=False))
async def voice_status() -> dict[str, Any]:
    """Check the setup: whether the models and ffmpeg are installed, the registered voices, the pronunciation list,
    and where audio is written."""
    return await _run(V.status)


@mcp.tool(annotations=ToolAnnotations(title="Transcribe audio", read_only_hint=False, destructive_hint=False,
                                      open_world_hint=False))
async def transcribe_audio(audio_path: str, language: str = "vi", output_dir: str | None = None,
                           formats: list[Literal["txt", "srt", "json"]] | None = None) -> dict[str, Any]:
    """Speech to text with Whisper large-v3-turbo for any audio or video file (mp3, wav, m4a, mp4, mov…).

    Returns the full text and subtitle cues (split where the speaker pauses, at clause ends, ≤ ~42 characters), and
    writes .txt, .srt and .json (word times) next to the file or in output_dir. language: "vi" (default), "en", …,
    or "" to detect. Whisper mishears names and verse; treat the text as a draft."""
    return await _run(V.transcribe, audio_path, language, output_dir, formats or ["txt", "srt", "json"])


@mcp.tool(annotations=ToolAnnotations(title="Register a reference voice", read_only_hint=False,
                                      destructive_hint=True, idempotent_hint=True, open_world_hint=False))
async def register_voice(name: str, audio_path: str, consent_confirmed: bool, start_seconds: float | None = None,
                         end_seconds: float | None = None, transcript: str | None = None,
                         notes: str = "") -> dict[str, Any]:
    """Save a reference clip of one speaker under a name, for synthesize_speech. Replaces a voice of the same name.

    name: lower-case letters, digits, hyphens (e.g. "lan-warm"). audio_path: a recording; start_seconds and
    end_seconds cut 10–20 s of clean speech (one speaker, no music). consent_confirmed must be true and only after
    the user has said the speaker agreed to have their voice cloned. transcript: the clip's exact words; if omitted,
    Whisper drafts it and the user must check it (then set_voice_transcript)."""
    return await _run(V.register_voice, name, audio_path, consent_confirmed, start_seconds, end_seconds, transcript,
                      notes)


@mcp.tool(annotations=ToolAnnotations(title="Correct a voice's transcript", read_only_hint=False,
                                      destructive_hint=False, idempotent_hint=True, open_world_hint=False))
async def set_voice_transcript(name: str, transcript: str) -> dict[str, Any]:
    """Set the exact words spoken in a registered voice's reference clip (word for word, with the right tones).
    'clone' mode continues from this transcript, so a wrong word makes the cloned voice drift."""
    return await _run(V.set_voice_transcript, name, transcript)


@mcp.tool(annotations=ToolAnnotations(title="List voices", read_only_hint=True, open_world_hint=False))
async def list_voices() -> dict[str, Any]:
    """The registered reference voices: name, clip length, transcript and whether it was checked, notes."""
    return {"voices": await _run(V.list_voices)}


@mcp.tool(annotations=ToolAnnotations(title="Set a pronunciation", read_only_hint=False, destructive_hint=False,
                                      idempotent_hint=True, open_world_hint=False))
async def set_pronunciation(word: str, spoken: str) -> dict[str, Any]:
    """Teach how to say a word the model reads wrong (a brand, a foreign word): every script has `word` replaced by
    `spoken` before reading, e.g. word "Matcha", spoken "Mát-cha". Replaces an earlier entry for the same word."""
    return await _run(V.set_pronunciation, word, spoken)


@mcp.tool(annotations=ToolAnnotations(title="Synthesize speech", read_only_hint=False, destructive_hint=False,
                                      open_world_hint=False))
async def synthesize_speech(script: str, ctx: Context, voice: str | None = None,
                            mode: Literal["clone", "clone_style", "design"] = "clone", style: str | None = None,
                            takes: int = 3, score: bool = True, join: bool = True, pause_seconds: float = 0.5,
                            output_dir: str | None = None, seed: int = 1000, steps: int = 16, cfg: float = 2.0,
                            language: str = "vi", reference_audio: str | None = None,
                            reference_transcript: str | None = None) -> dict[str, Any]:
    """Read a script aloud in a cloned voice; 48 kHz mono WAV files.

    script: one sentence or phrase per line (lines starting with # are skipped; ≤ 80 lines, ≤ 500 characters each).
    voice: a registered voice name. mode: "clone" (closest to the reference: timbre and phrasing; needs the
    reference's exact transcript), "clone_style" (the reference's timbre read the way `style` describes, e.g.
    "warm, gentle, smiling, unhurried"), "design" (a new voice from `style` alone, no reference; English
    descriptions work best). Instead of `voice`, reference_audio (+ reference_transcript for "clone") may be given.

    takes: readings per line (1–8, different seeds). score: Whisper reads every take back and the take with the
    fewest wrong syllables becomes line-NN_best.wav (table in SCORES.md). join: the best takes, trimmed and levelled,
    joined with pause_seconds between lines into joined.wav. seed: the first take's seed (same seed, text and voice
    reproduce a take). steps 4–32 (16 clean, 10 faster); cfg 2.0–4.0 (higher follows the text and voice more
    tightly, may sound stiffer). Files go to output_dir or a new folder under ~/Documents/voice-mcp-output."""
    return await _run(V.synthesize, script, voice, mode, style, takes, score, join, pause_seconds, output_dir, seed,
                      steps, cfg, language, reference_audio, reference_transcript, ctx=ctx)


if __name__ == "__main__":
    mcp.run()
