# voice-mcp

MCP server cho trợ lý AI (Claude Code, Claude Desktop…): **đọc kịch bản thành giọng nói** bằng giọng mẫu nhân bản (VoxCPM2) hoặc giọng tạo từ mô tả, và **nghe chép lời** âm thanh, video ra chữ và phụ đề (Whisper large-v3-turbo). Chạy hoàn toàn trên máy Mac chip Apple (MLX), không gửi âm thanh đi đâu.

*An MCP server for AI assistants: text-to-speech with voice cloning or voice design (VoxCPM2) and speech-to-text (Whisper large-v3-turbo), running locally on Apple Silicon via MLX. Vietnamese by default, about 30 languages.*

## Cài nhanh

Cần máy Mac chip Apple (M1 trở lên), khoảng 8 GB ổ đĩa, và `brew install uv ffmpeg`.

```bash
git clone https://github.com/DatTran082/voice-mcp.git
cd voice-mcp
./install.sh --test
claude mcp add --scope user voice -- "$PWD/voice-mcp"
```

Sau đó mở phiên Claude Code mới và nói với AI, ví dụ "đọc kịch bản này bằng giọng …".

Hướng dẫn đầy đủ: [GUIDE.md](GUIDE.md). Gồm cài đặt, kết nối Claude Desktop, các công cụ, mẹo viết kịch bản, lỗi thường gặp, giấy phép.

## Các công cụ

| Công cụ | Làm gì |
|---|---|
| `synthesize_speech` | Đọc kịch bản (mỗi dòng một câu). Ba kiểu: `clone`, `clone_style`, `design`. Mỗi câu đọc vài lần, Whisper chọn lần ít sai nhất, ghép thành `joined.wav`. |
| `register_voice` | Lưu giọng mẫu (10–20 giây). Chỉ khi người nói đã đồng ý. |
| `set_voice_transcript` | Sửa lời mẫu cho đúng từng chữ. |
| `list_voices` | Liệt kê các giọng đã lưu. |
| `set_pronunciation` | Dạy cách đọc tên riêng, từ nước ngoài. |
| `transcribe_audio` | Chép lời ra txt, srt và json (thời gian từng chữ). |
| `voice_status` | Kiểm tra cài đặt. |

## Lưu ý

Chỉ nhân bản giọng của người đã đồng ý. Nội dung đăng lên có giọng nhân bản phải gắn nhãn AI theo quy định của nền tảng.

Mô hình do `install.sh` tải từ Hugging Face: VoxCPM2 theo giấy phép Apache-2.0, Whisper theo MIT.
