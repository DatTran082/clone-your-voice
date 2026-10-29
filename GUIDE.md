# voice-mcp: hướng dẫn sử dụng

Đây là một **MCP server**, tức một bộ công cụ cắm vào trợ lý AI (Claude Code, Claude Desktop hoặc ứng dụng AI khác hỗ trợ MCP). Sau khi kết nối, bạn chỉ cần nói với AI bằng lời thường, ví dụ "đọc kịch bản này bằng giọng chị Lan", và AI sẽ tự gọi công cụ.

Bộ công cụ làm ba việc, chạy hoàn toàn trên máy Mac, không gửi âm thanh đi đâu:

1. **Đọc kịch bản thành giọng nói bằng giọng mẫu** (nhân bản giọng, mô hình VoxCPM2).
   - Mỗi câu đọc vài lần.
   - Whisper nghe lại và chọn lần đọc ít sai nhất.
   - Các câu được ghép thành một tệp WAV 48 kHz.
2. **Lưu giọng mẫu** vào một thư viện có tên, để lần sau chỉ cần gọi tên giọng.
3. **Nghe chép lời** từ âm thanh hoặc video ra chữ, phụ đề `.srt` và thời gian từng chữ (mô hình Whisper large-v3-turbo).

Dùng được cho nhiều việc: giọng đọc video, quảng cáo, bài giảng, sách nói, tin nhắn thoại, phụ đề cho video có sẵn… Mô hình đọc được khoảng 30 ngôn ngữ; mặc định là tiếng Việt, và với tiếng Việt thì số, ngày, giá tiền được tự đổi thành chữ.

## Yêu cầu

- Máy Mac chip Apple (M1 trở lên). Mô hình chạy bằng MLX nên không dùng được trên Windows hay Mac chip Intel.
- Khoảng 8 GB ổ đĩa: môi trường Python 1,2 GB, VoxCPM2 4,6 GB, Whisper 1,6 GB. Khi chạy cần khoảng 6 GB RAM trống (kích thước hai mô hình).
- `uv` và `ffmpeg`. Nếu chưa có, cài bằng `brew install uv ffmpeg`.
- Mạng xem được huggingface.co, chỉ cần cho lần cài đầu.

## Cài đặt

Lấy gói về bằng một trong hai cách:

- `git clone https://github.com/DatTran082/voice-mcp.git` (repo riêng tư: chủ repo phải mời bạn vào trước). Cập nhật sau này bằng `git pull`.
- Giải nén tệp `voice-mcp.zip` được gửi cho bạn.

Rồi chạy:

```bash
cd voice-mcp
./install.sh
```

Script làm bốn việc:

1. Tạo môi trường Python 3.12 với đúng các phiên bản trong `requirements.txt`.
2. Tải hai mô hình về `~/.cache/voice-mcp/`.
3. Thử khởi động server.
4. In ra lệnh để kết nối với AI.

Chạy lại lúc nào cũng được: phần đã có thì giữ nguyên, tải dở thì tải tiếp. Chạy `./install.sh --test` thì script còn đọc thử hai câu qua server (mất khoảng 1 phút).

**Nếu mạng chặn Hugging Face** (mạng công ty có tường lửa sẽ báo "Hugging Face trả về 403"), có hai cách:

- Đổi sang mạng khác (ví dụ phát 4G từ điện thoại) rồi chạy lại `./install.sh`.
- Chép hai thư mục `VoxCPM2-bf16` và `whisper-turbo` từ một máy đã cài vào `~/.cache/voice-mcp/` của máy mới, rồi chạy `./install.sh`.

## Kết nối với AI

**Claude Code** (làm một lần):

```bash
claude mcp add --scope user voice -- ~/Documents/voice-mcp/voice-mcp
```

Sau đó mở phiên Claude Code mới. Lệnh `claude mcp list` sẽ thấy `voice` ở trạng thái đã kết nối.

**Claude Desktop:** mở tệp `~/Library/Application Support/Claude/claude_desktop_config.json` và thêm vào mục `mcpServers` (thay `<tên-máy>` bằng tên người dùng trên máy), rồi khởi động lại Claude Desktop:

```json
{
  "mcpServers": {
    "voice": {
      "command": "/Users/<tên-máy>/Documents/voice-mcp/voice-mcp"
    }
  }
}
```

**Ứng dụng AI khác hỗ trợ MCP:** khai báo một server kiểu stdio với lệnh là đường dẫn tới `voice-mcp`, không cần tham số.

## Cách dùng: nói với AI

Ví dụ những câu có thể nói:

- "Kiểm tra bộ công cụ giọng nói đã sẵn sàng chưa."
- "Lưu giọng chị Lan từ tệp ~/Downloads/lan.m4a, đoạn từ giây 12 đến giây 28. Chị Lan đã đồng ý cho nhân bản giọng."
- "Đọc kịch bản này bằng giọng lan, mỗi câu 4 lần, rồi ghép lại: …"
- "Đọc thử câu 'Chào bạn, hôm nay uống gì nè?' bằng giọng lan nhưng vui tươi, nhanh hơn."
- "Tạo một giọng nam trầm, ấm, đọc chậm để đọc câu này."
- "Chép lời video ~/Movies/clip.mp4 ra phụ đề."
- "Từ 'Matcha' đọc là 'Mát-cha'."

AI được dặn sẵn quy trình sau:

1. Xem các giọng đã lưu.
2. Lưu giọng mới, nhưng chỉ khi bạn xác nhận người đó đã đồng ý.
3. Đưa bạn xem bản chép lời nháp của giọng mẫu và sửa cho đúng từng chữ.
4. Đọc kịch bản.
5. Báo lại các tệp, kèm lời nhắc nghe lại trước khi dùng và gắn nhãn AI khi đăng.

### Viết kịch bản cho dễ đọc

- **Mỗi dòng một câu hoặc một vế.** Dấu phẩy ngắt hơi ngắn, dấu chấm ngắt dài. Dòng bắt đầu bằng `#` bị bỏ qua.
- **Số, ngày, giá tiền tự đổi thành chữ trước khi đọc:**
  - "30/11" thành "ba mươi tháng mười một";
  - "25.000đ" và "25k" thành "hai mươi lăm nghìn đồng" và "hai mươi lăm nghìn";
  - "10%" thành "mười phần trăm".

  Kết quả trả về có dòng `spoken` cho biết từng câu thực sự được đọc thế nào.
- **Tên riêng, từ nước ngoài:** bảo AI "từ X đọc là Y" để thêm vào bảng cách đọc của bạn. Bảng này áp dụng cho mọi kịch bản về sau.

### Giọng mẫu tốt

- chỉ một người nói, không có nhạc nền, tiếng ồn hay tiếng vang phòng;
- giọng tự nhiên, đúng cách đọc bạn muốn (đọc thơ thì lấy đoạn đọc thơ, nói chuyện thì lấy đoạn nói chuyện);
- dài 10–20 giây, cắt trọn câu;
- **lời mẫu đúng từng chữ, từng dấu.** Whisper chép nháp và hay nhầm (ví dụ "chùm hoa" thành "chuồng hoa"). Kiểu đọc `clone` bám theo lời này, lời sai thì giọng lệch.

## Các công cụ

Phần này để tra cứu; AI tự chọn công cụ và tham số.

| Công cụ | Làm gì | Tham số chính |
|---|---|---|
| `voice_status` | Kiểm tra mô hình, ffmpeg, danh sách giọng, bảng cách đọc, thư mục ghi tệp | không có |
| `list_voices` | Các giọng đã lưu | không có |
| `register_voice` | Lưu một đoạn giọng mẫu dưới một tên (ghi đè giọng cùng tên) | `name`, `audio_path`, `consent_confirmed` (bắt buộc đúng), `start_seconds`, `end_seconds`, `transcript`, `notes` |
| `set_voice_transcript` | Sửa lời mẫu cho đúng từng chữ | `name`, `transcript` |
| `set_pronunciation` | Thêm hoặc sửa cách đọc một từ | `word`, `spoken` |
| `synthesize_speech` | Đọc kịch bản | `script`, `voice`, `mode`, `style`, `takes`, `score`, `join`, `pause_seconds`, `output_dir`, `seed`, `steps`, `cfg` |
| `transcribe_audio` | Chép lời âm thanh hoặc video | `audio_path`, `language`, `output_dir`, `formats` |

Ba kiểu đọc của `synthesize_speech` (`mode`):

| Kiểu | Cần gì | Khi nào dùng |
|---|---|---|
| `clone` (mặc định) | Giọng đã lưu, có lời mẫu đúng | Giống giọng mẫu nhất, cả âm sắc lẫn cách ngắt nghỉ. Giọng đọc của video giới thiệu dùng kiểu này. |
| `clone_style` | Giọng đã lưu và `style` | Giữ âm sắc của mẫu nhưng đổi cách đọc, ví dụ `"warm, gentle, smiling, unhurried"` |
| `design` | Chỉ `style` | Tạo một giọng mới từ mô tả, không cần mẫu, ví dụ `"A young woman's voice, warm and bright, speaking slowly"` |

Mô tả giọng (`style`) viết bằng tiếng Anh cho kết quả ổn định nhất. Kịch bản thì vẫn viết tiếng Việt.

Các tham số khác:
- `takes` (1–8, mặc định 3): số lần đọc mỗi câu.
- `steps` (4–32, mặc định 16): 10 thì nhanh hơn, 16 thì tiếng sạch hơn.
- `cfg` (2,0–4,0, mặc định 2,0): cao hơn thì bám chữ và giọng chặt hơn, nhưng có thể cứng giọng.
- `seed` (mặc định 1000): cùng câu, cùng giọng, cùng `seed` thì đọc ra y hệt.

## Kết quả

Mỗi lần đọc tạo một thư mục mới trong `~/Documents/voice-mcp-output/`, tên gồm ngày giờ và tên giọng. AI cũng có thể ghi vào thư mục bạn chỉ định.

| Tệp | Là gì |
|---|---|
| `line-01_0.wav`, `line-01_1.wav`… | Từng lần đọc của từng câu |
| `line-01_best.wav`… | Lần ít sai nhất của mỗi câu |
| `joined.wav` | Cả bài: các lần tốt nhất, cắt khoảng lặng, cân âm lượng, nghỉ 0,5 giây giữa các câu |
| `SCORES.md` | Bảng chấm: số tiếng Whisper nghe khác câu gốc (tính cả dấu thanh), độ dài, Whisper nghe được gì |
| `result.json` | Toàn bộ kết quả, để AI hoặc script khác đọc lại |

**Luôn nghe lại trước khi dùng.** Bảng chấm chỉ giúp xếp hạng, vì chính Whisper cũng nghe nhầm, nhất là tên riêng và thơ. Giọng có hợp hay không thì phải nghe bằng tai. Nếu thích một lần đọc khác lần được chọn, cứ dùng tệp `line-NN_<lần>.wav` đó.

Tốc độ đo trên MacBook Pro M5, 24 GB:
- lần gọi đầu nạp mô hình mất vài giây, các lần sau mô hình đã nạp sẵn;
- mỗi lần đọc một câu ngắn (khoảng 3 giây giọng) mất khoảng 15 giây;
- chấm mỗi lần đọc mất khoảng 3 giây.

Đọc 2 câu × 2 lần, có chấm và ghép, hết khoảng 1 phút.

## Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| AI không thấy công cụ `voice` | Kiểm tra `claude mcp list`, mở phiên mới. Chạy `./install.sh` để xem server khởi động được không. |
| "Hugging Face trả về 403" khi cài | Mạng chặn trang tải mô hình. Xem phần Cài đặt. |
| "Only voices whose speaker agreed…" | AI cần bạn xác nhận người nói đã đồng ý trước khi lưu giọng. |
| Giọng ra không giống mẫu | Dùng mẫu sạch hơn, dài 10–20 giây. Kiểm tra lại lời mẫu đúng từng chữ. |
| Đọc sai dấu hoặc sai một chữ | Đọc thêm vài lần (`takes` 5–6). Thêm dấu phẩy để tách chữ khó. Thêm cách đọc bằng `set_pronunciation`. |
| Kịch bản dài bị ngắt giữa chừng | Chia kịch bản thành nhiều lần gọi hoặc giảm `takes`. Với Claude Code, có thể đặt thời gian chờ dài hơn bằng biến `MCP_TOOL_TIMEOUT` (mili giây) trước khi mở. |
| Máy chậm hoặc nóng | Giảm `steps` xuống 10, đọc ít lần hơn, đóng ứng dụng nặng (Blender…). |

## Giấy phép và lưu ý khi dùng

- **Giấy phép:** cả hai mô hình và các thư viện đều dùng thương mại được.

  | Thành phần | Nguồn | Giấy phép |
  |---|---|---|
  | VoxCPM2 | OpenBMB; bản MLX `mlx-community/VoxCPM2-bf16` | Apache-2.0 |
  | Whisper large-v3-turbo | OpenAI; bản MLX `mlx-community/whisper-large-v3-turbo` | MIT |
  | `mlx`, `mlx-audio`, `mlx-whisper`, MCP Python SDK (`mcp`) | | MIT |
- **Chỉ nhân bản giọng của người đã đồng ý.** Công cụ không cho lưu giọng khi chưa xác nhận điều này. Không dùng giọng nhân bản để giả làm người khác, và không dùng giọng người nổi tiếng.
- **Bài đăng có giọng nhân bản phải gắn nhãn nội dung AI** theo quy định của nền tảng (TikTok, Facebook, YouTube).

## Các tệp

Trong thư mục `voice-mcp/`:

| Tệp | Là gì |
|---|---|
| `voice-mcp` | Lệnh khởi động server (dùng môi trường Python của bộ công cụ) |
| `server.py` | Khai báo các công cụ MCP và lời dặn quy trình cho AI |
| `voice_core.py` | Phần xử lý: chép lời, thư viện giọng, đọc, chấm, ghép |
| `vi_numbers.py` | Đọc số, ngày, giá tiền thành chữ tiếng Việt |
| `pronunciations.txt` | Mẫu bảng cách đọc (đi kèm gói, để trống) |
| `install.sh` | Cài môi trường, tải mô hình, kiểm tra server |
| `download_model.py` | Tải mô hình từ Hugging Face bằng nhiều luồng, tải tiếp được khi đứt |
| `selftest.py` | Bài thử: khởi động server như một ứng dụng AI, đọc hai câu, chép lời lại |
| `requirements.txt` | Phiên bản các thư viện đã chạy được |
| `examples/sentences.txt` | Kịch bản mẫu |

Dữ liệu nằm ngoài thư mục này, trong `~/.cache/voice-mcp/` (đổi bằng biến `VOICE_MCP_HOME`):
- `mlx-env/`: môi trường Python;
- `VoxCPM2-bf16/`, `whisper-turbo/`: hai mô hình;
- `voices/<tên>/`: mỗi giọng đã lưu gồm `reference.wav`, `reference.txt` và `voice.json`;
- `pronunciations.txt`: bảng cách đọc của bạn (`set_pronunciation` ghi vào đây; ưu tiên hơn bảng đi kèm gói).

Âm thanh tạo ra nằm trong `~/Documents/voice-mcp-output/` (đổi bằng biến `VOICE_MCP_OUTPUT`).
