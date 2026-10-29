# clone-your-voice

**Clone your voice on Apple Silicon: 100% local, private, and ready for Claude via MCP.**

Give it 10–20 seconds of someone speaking (with their permission) and a script. You get back a natural reading in that voice, the best of several takes, chosen by an automatic listener. Or design a brand-new voice from a one-line description. It also turns any audio or video into text and subtitles.

- **Runs on your Mac.** It uses VoxCPM2 and Whisper large-v3-turbo on MLX. There is no cloud and no API key, and no audio leaves the machine.
- **Picks the best take for you.** Each line is read several times. Whisper listens back, counts the mistakes, keeps the best take and joins the lines into one file.
- **Talk to it through your AI.** It is an MCP server: tell Claude "read this script in my voice" and it does the rest.
- **About 30 languages.** Vietnamese is the default, with numbers, dates and prices spelled out.

## Listen

16 seconds of a real voice, and that voice cloned to say new things. **[▶ Play them side by side](https://dattran082.github.io/clone-your-voice/)**

| Sample | Length | Audio |
|---|---|---|
| **Original recording** (Vietnamese; the only audio the clone was given) | 16 s | [original.mp3](docs/samples/original.mp3) |
| **Clone:** a new Vietnamese sentence, best of 4 takes | 5 s | [clone-vi.mp3](docs/samples/clone-vi.mp3) |
| **Clone:** speaking English (the reference has no English in it) | 8 s | [clone-en.mp3](docs/samples/clone-en.mp3) |
| **Clone:** reading a six-line *lục bát* poem, best of 5 takes per line | 15 s | [clone-poem.mp3](docs/samples/clone-poem.mp3) |

The reference voice is shared with the speaker's permission.

## Install

You need an Apple silicon Mac (M1 or later), about 8 GB of disk, and `brew install uv ffmpeg`.

```bash
git clone https://github.com/DatTran082/clone-your-voice.git
cd clone-your-voice
./install.sh --test                                     # env + models (~6 GB), then a test reading
claude mcp add --scope user voice -- "$PWD/voice-mcp"   # connect it to Claude Code
```

Open a new Claude Code session and ask, for example:

> Save my voice from ~/Downloads/me.m4a, seconds 5 to 20. It's my own voice.
>
> Read this script in my voice, 4 takes per line, and join them: …
>
> Make a warm, slow male narrator voice and read this paragraph.
>
> Transcribe ~/Movies/clip.mp4 into subtitles.

For Claude Desktop and other MCP clients, see [GUIDE.md](GUIDE.md). It also covers the tools, script-writing tips, troubleshooting and licences.

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

Clone only your own voice, or the voices of people who agreed. The tool asks for that confirmation before saving a voice. Do not impersonate anyone. Content with a cloned voice must carry the platform's AI-content label.

## License

The code is under the [MIT](LICENSE) licence. The models are downloaded by `install.sh` and keep their own licences: VoxCPM2 is Apache-2.0 and Whisper large-v3-turbo is MIT.
