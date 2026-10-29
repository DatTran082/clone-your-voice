# voice-mcp

An MCP server for AI assistants (Claude Code, Claude Desktop…). It does two things, locally on Apple Silicon via MLX:
- **Text to speech** in a cloned voice, or a voice designed from a description (VoxCPM2).
- **Speech to text**: audio and video to text and subtitles (Whisper large-v3-turbo).

No audio leaves your Mac. It handles about 30 languages and defaults to Vietnamese.

## Quick start

You need an Apple silicon Mac (M1 or later), about 8 GB of disk, and `brew install uv ffmpeg`.

```bash
git clone https://github.com/DatTran082/voice-mcp.git
cd voice-mcp
./install.sh --test
claude mcp add --scope user voice -- "$PWD/voice-mcp"
```

Then open a new Claude Code session and ask, for example, "read this script in Lan's voice…".

The full guide is [GUIDE.md](GUIDE.md). It covers install, Claude Desktop, the tools, writing scripts, troubleshooting and licences.

## Tools

| Tool | What it does |
|---|---|
| `synthesize_speech` | Reads a script aloud, one sentence per line, in three modes: `clone`, `clone_style`, `design`. It reads several takes per line, Whisper picks the best, and the lines are joined into `joined.wav`. |
| `register_voice` | Saves a 10–20 s reference voice, only with the speaker's consent. |
| `set_voice_transcript` | Sets the reference's exact transcript. |
| `list_voices` | Lists the saved voices. |
| `set_pronunciation` | Teaches how to read names and foreign words. |
| `transcribe_audio` | Writes txt, srt and json (word timings). |
| `voice_status` | Checks the installation. |

## Responsible use

Clone only the voices of people who agreed. Content with a cloned voice must carry the platform's AI-content label.

`install.sh` downloads the models from Hugging Face. VoxCPM2 is Apache-2.0 and Whisper is MIT.
