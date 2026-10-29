# clone-your-voice: user guide

clone-your-voice is an **MCP server**: a set of tools that plugs into an AI assistant (Claude Code, Claude Desktop, or any app that supports MCP). Once it is connected, you ask the assistant in plain words, for example "read this script in Lan's voice", and the assistant calls the tools itself.

It does three things, entirely on your Mac; no audio leaves the machine:

1. **Reads a script aloud** in a cloned voice (VoxCPM2). Each line is read a few times, Whisper listens back and picks the take with the fewest mistakes, and the lines are joined into one 48 kHz WAV file.
2. **Keeps reference voices** in a named library, so later you only need the voice's name.
3. **Transcribes** audio or video to text, `.srt` subtitles and word timings (Whisper large-v3-turbo).

Use it for anything that needs a voice: video voice-overs, ads, lessons, audiobooks, voice messages, subtitles for existing videos. The model speaks about 30 languages. The default is Vietnamese; in Vietnamese, numbers, dates and prices are spelled out automatically.

## Requirements

- **Mac:** Apple silicon (M1 or later). The models run on MLX, so Windows and Intel Macs are not supported.
- **Disk:** about 8 GB (Python env 1.2 GB, VoxCPM2 4.6 GB, Whisper 1.6 GB).
- **Memory:** about 6 GB of free RAM while running (the size of the two models).
- **Tools:** `uv` and `ffmpeg`: `brew install uv ffmpeg`.
- **Network:** access to huggingface.co, for the first install only.

## Install

Get the package in one of two ways:

- `git clone https://github.com/DatTran082/clone-your-voice.git`. Update later with `git pull`.
- Unzip a `clone-your-voice.zip` someone sent you.

Then run:

```bash
cd clone-your-voice
./install.sh
```

The script:

1. creates a Python 3.12 env with the exact versions in `requirements.txt`;
2. downloads the two models into `~/.cache/voice-mcp/`;
3. checks that the server starts;
4. prints the command that connects it to your AI.

It is safe to run again: what is already there is kept, and interrupted downloads resume. `./install.sh --test` also reads two lines aloud through the server (about a minute).

**If your network blocks Hugging Face** (behind a corporate firewall, the install reports "Hugging Face returned 403"), there are two ways around it:

- Switch networks (a phone hotspot, for example) and run `./install.sh` again.
- Copy the `VoxCPM2-bf16` and `whisper-turbo` folders from a machine that has them into `~/.cache/voice-mcp/` on the new one, then run `./install.sh`. It sees the models are complete and only builds the Python env.

## Connect to your AI

**Claude Code**, once:

```bash
claude mcp add --scope user voice -- ~/clone-your-voice/voice-mcp      # use the folder you installed into
```

Open a new Claude Code session. `claude mcp list` should show `voice` as connected.

**Claude Desktop:** open `~/Library/Application Support/Claude/claude_desktop_config.json`, add the server under `mcpServers` (with your own path), and restart Claude Desktop:

```json
{
  "mcpServers": {
    "voice": {
      "command": "/Users/<you>/clone-your-voice/voice-mcp"
    }
  }
}
```

**Other MCP clients:** add a stdio server whose command is the path to `voice-mcp`, with no arguments.

## Using it: talk to your AI

Things you can say:

- "Check whether the voice tools are ready."
- "Save Lan's voice from ~/Downloads/lan.m4a, from second 12 to second 28. Lan agreed to have her voice cloned."
- "Read this script in the voice lan, 4 takes per line, and join them: …"
- "Read 'Hi, what would you like to drink today?' in lan's voice, but cheerful and a bit faster."
- "Make a deep, warm, slow male voice and read this line with it."
- "Transcribe ~/Movies/clip.mp4 into subtitles."
- "'Matcha' should be read as 'Mát-cha'."

The assistant is given this workflow by the server:

1. Check the saved voices.
2. Save a new voice only after you confirm the speaker agreed.
3. Show you the draft transcript of the reference so you can correct it word for word.
4. Read the script.
5. Report the files, with a reminder to listen before use and to label AI content when posting.

### Writing a script that reads well

- **One sentence or phrase per line.** A comma is a short pause, a full stop a longer one. Lines starting with `#` are skipped.
- **Vietnamese numbers, dates and prices are spelled out before reading:**
  - "30/11" becomes "ba mươi tháng mười một";
  - "25.000đ" and "25k" become "hai mươi lăm nghìn đồng" and "hai mươi lăm nghìn";
  - "10%" becomes "mười phần trăm".

  The result's `spoken` field shows how each line was actually read.
- **Names and foreign words:** tell the assistant "X is read as Y" and it adds that to your pronunciation list. The list applies to every script from then on.

### A good reference voice

- one speaker, no background music, noise or room echo;
- natural, in the manner you want (a poem reading for poems, conversation for conversation);
- 10–20 seconds long, cut on whole sentences;
- **a transcript that is exact, word for word, with the right accents.** Whisper's draft is often wrong (for example "chùm hoa" heard as "chuồng hoa"). `clone` mode follows this transcript; mistakes in it make the voice drift.

## Tools

For reference; the assistant picks the tools and parameters itself.

| Tool | What it does | Main parameters |
|---|---|---|
| `voice_status` | Checks the models, ffmpeg, saved voices, pronunciation list and output folder | none |
| `list_voices` | Lists the saved voices | none |
| `register_voice` | Saves a reference clip under a name (replaces a voice of the same name) | `name`, `audio_path`, `consent_confirmed` (must be true), `start_seconds`, `end_seconds`, `transcript`, `notes` |
| `set_voice_transcript` | Sets the reference's exact transcript | `name`, `transcript` |
| `set_pronunciation` | Adds or changes how a word is read | `word`, `spoken` |
| `synthesize_speech` | Reads a script aloud | `script`, `voice`, `mode`, `style`, `takes`, `score`, `join`, `pause_seconds`, `output_dir`, `seed`, `steps`, `cfg`, `language` |
| `transcribe_audio` | Transcribes audio or video | `audio_path`, `language`, `output_dir`, `formats` |

The three modes of `synthesize_speech`:

| `mode` | Needs | Use it for |
|---|---|---|
| `clone` (default) | A saved voice with an exact transcript | The closest match to the reference: timbre and phrasing |
| `clone_style` | A saved voice and a `style` | The reference's timbre read another way, e.g. `"warm, gentle, smiling, unhurried"` |
| `design` | A `style` only | A new voice from a description, no reference, e.g. `"A young woman's voice, warm and bright, speaking slowly"` |

Write `style` in English for the most stable results; the script itself can be in any supported language.

Other parameters:

| Parameter | Range | Default | Effect |
|---|---|---|---|
| `takes` | 1–8 | 3 | Readings per line. |
| `steps` | 4–32 | 16 | Denoising steps: 10 is faster, 16 cleaner. |
| `cfg` | 2.0–4.0 | 2.0 | Higher follows the text and voice more tightly, but may sound stiffer. |
| `seed` | any | 1000 | The same line, voice and seed reproduce a take exactly. |
| `language` | language code | `vi` | Language for scoring and spelling out numbers; `""` lets Whisper detect it. |

## Output

Each run creates a new folder in `~/Documents/voice-mcp-output/`, named with the date, time and voice. The assistant can also write to a folder you name.

| File | What it is |
|---|---|
| `line-01_0.wav`, `line-01_1.wav`… | Every take of every line |
| `line-01_best.wav`… | Each line's take with the fewest mistakes |
| `joined.wav` | The whole script: best takes, silence trimmed, levels matched, 0.5 s between lines |
| `SCORES.md` | The scores: words Whisper heard differently from the line (accents count), length, what Whisper heard |
| `result.json` | The full result, for the assistant or another script |

**Always listen before use.** The scores only rank the takes; Whisper mishears too, especially names and verse. Whether a voice fits is for your ears to judge. If you prefer a take other than the chosen one, use its `line-NN_<take>.wav`.

Speed, measured on a MacBook Pro M5 with 24 GB:
- **First call:** a few seconds to load the models. They stay loaded after that.
- **Reading:** about 15 s per take of a short line (about 3 s of speech).
- **Scoring:** about 3 s per take.

Two lines × two takes with scoring and joining take about a minute.

## Troubleshooting

| Symptom | What to do |
|---|---|
| The assistant does not see the `voice` tools | Check `claude mcp list` and open a new session. Run `./install.sh` to see whether the server starts. |
| "Hugging Face returned 403" during install | Your network blocks the model downloads. See Install. |
| "Only voices whose speaker agreed…" | The assistant needs your confirmation that the speaker consented before saving a voice. |
| The voice does not sound like the reference | Use a cleaner reference of 10–20 s. Check that the transcript is exact. |
| A wrong accent or word | Read more takes (`takes` 5–6). Add a comma to separate the hard word. Add a pronunciation with `set_pronunciation`. |
| Long scripts stop halfway | Split the script into several calls or lower `takes`. In Claude Code you can raise the tool timeout with the `MCP_TOOL_TIMEOUT` environment variable (milliseconds) before starting it. |
| The Mac is slow or hot | Lower `steps` to 10, read fewer takes, close heavy apps. |

## Licences and responsible use

**Licences:** both models and all libraries allow commercial use.

| Component | Source | Licence |
|---|---|---|
| VoxCPM2 | OpenBMB; MLX build `mlx-community/VoxCPM2-bf16` | Apache-2.0 |
| Whisper large-v3-turbo | OpenAI; MLX build `mlx-community/whisper-large-v3-turbo` | MIT |
| `mlx`, `mlx-audio`, `mlx-whisper`, MCP Python SDK (`mcp`) | | MIT |

**Clone only the voices of people who agreed.** The tool refuses to save a voice until that is confirmed. Do not use a cloned voice to impersonate anyone, and do not clone public figures.

**Content with a cloned voice must carry the AI-content label** that the platform requires (TikTok, Facebook, YouTube…).

## Files

In the `clone-your-voice/` folder (the server itself is called `voice`, its launcher `voice-mcp`):

| File | What it is |
|---|---|
| `voice-mcp` | Starts the server with the tools' own Python env |
| `server.py` | The MCP tools and the workflow instructions for the assistant |
| `voice_core.py` | The engine: transcription, voice library, reading, scoring, joining |
| `vi_numbers.py` | Vietnamese numbers, dates and prices in words |
| `pronunciations.txt` | A template pronunciation list shipped with the package (empty) |
| `install.sh` | Installs the env, downloads the models, checks the server |
| `download_model.py` | Downloads models from Hugging Face over parallel connections, resuming if interrupted |
| `selftest.py` | A check that starts the server as an AI client would, reads two lines and transcribes them back |
| `requirements.txt` | The library versions known to work |
| `LICENSE` | MIT, for this code (the models keep their own licences) |
| `examples/script-vi.txt`, `examples/script-en.txt` | Sample scripts in Vietnamese and English |

**Data** lives outside the package, in `~/.cache/voice-mcp/` (change it with `VOICE_MCP_HOME`):
- `mlx-env/`: the Python env;
- `VoxCPM2-bf16/` and `whisper-turbo/`: the two models;
- `voices/<name>/`: each saved voice, as `reference.wav`, `reference.txt` and `voice.json`;
- `pronunciations.txt`: your own pronunciation list. `set_pronunciation` writes here, and it takes precedence over the package's.

**Generated audio** goes to `~/Documents/voice-mcp-output/` (change it with `VOICE_MCP_OUTPUT`).
