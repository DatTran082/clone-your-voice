"""End-to-end check of the voice MCP server, as an AI client sees it: start voice-mcp over stdio, list the tools,
then (unless --quick) design a voice from a description, read two lines with it, and transcribe the joined result.
No personal voice is needed. About a minute on an M-series Mac.

  ~/.cache/voice-mcp/mlx-env/bin/python selftest.py [--quick]
"""
import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

HERE = Path(__file__).resolve().parent
EXPECTED = {"voice_status", "transcribe_audio", "register_voice", "set_voice_transcript", "list_voices",
            "set_pronunciation", "synthesize_speech"}
SCRIPT = "Xin chào, đây là bài đọc thử.\nHẹn gặp lại bạn vào ngày 30/11."


def payload(result):
    if result.is_error:
        raise SystemExit(f"tool error: {result.content[0].text}")
    return result.structured_content


async def main(quick):
    params = StdioServerParameters(command=str(HERE / "voice-mcp"))
    async with Client(params, read_timeout_seconds=900) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        missing = EXPECTED - names
        print("tools:", ", ".join(sorted(names)))
        if missing:
            raise SystemExit(f"missing tools: {missing}")
        status = payload(await client.call_tool("voice_status", {}))
        print("status:", json.dumps(status, ensure_ascii=False))
        if not (status["voxcpm2"] and status["whisper"] and status["ffmpeg"]):
            raise SystemExit("models or ffmpeg missing: run install.sh")
        if quick:
            print("ok (quick)")
            return
        with tempfile.TemporaryDirectory() as out:
            async def progress(done, total, message):
                print(f"  {done:.0f}/{total:.0f} {message or ''}", flush=True)
            r = payload(await client.call_tool("synthesize_speech", {
                "script": SCRIPT, "mode": "design", "takes": 1, "output_dir": out,
                "style": "A young woman's voice, warm and bright, speaking slowly"}, progress_callback=progress))
            for line in r["lines"]:
                t = line["takes"][0]
                print(f"  line {line['line']}: said «{line['spoken']}» heard «{t['heard']}» wrong {t['wrong_syllables']}")
            heard = payload(await client.call_tool("transcribe_audio", {"audio_path": r["joined"], "output_dir": out}))
            print("joined.wav heard:", heard["text"])
            if not heard["text"]:
                raise SystemExit("nothing heard in the synthesized audio")
    print("ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
    asyncio.run(main(ap.parse_args().quick))
    sys.exit(0)
