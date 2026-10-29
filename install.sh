#!/bin/zsh
# Sets up the voice MCP server on an Apple Silicon Mac: the Python env (uv, Python 3.12, requirements.txt)
# and the two models (VoxCPM2 bf16 and Whisper large-v3-turbo, MLX builds from Hugging Face), in $VOICE_MCP_HOME
# (default ~/.cache/voice-mcp). Safe to run again: what is already there is kept, downloads resume.
#   ./install.sh          install, then a quick check that the server starts
#   ./install.sh --test   also read two lines aloud through the server (about a minute)
set -e
cd "${0:A:h}"
H=${VOICE_MCP_HOME:-$HOME/.cache/voice-mcp}
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || { echo "Cần máy Mac chip Apple (M1 trở lên)."; exit 1 }
for t in uv ffmpeg; do
  command -v $t >/dev/null || { echo "Thiếu $t: cài bằng 'brew install $t' rồi chạy lại."; exit 1 }
done
free=$(df -g "$HOME" | awk 'NR==2 {print $4}')
(( free >= 10 )) || echo "Chú ý: ổ đĩa còn ${free} GB, bộ công cụ cần khoảng 8 GB."
mkdir -p $H
echo "1/3 Môi trường Python → $H/mlx-env"
[[ -x $H/mlx-env/bin/python ]] || uv venv --python 3.12 $H/mlx-env
uv pip install --quiet --python $H/mlx-env/bin/python -r requirements.txt
echo "2/3 Mô hình nhân bản giọng VoxCPM2 (≈ 4,6 GB) → $H/VoxCPM2-bf16"
$H/mlx-env/bin/python download_model.py mlx-community/VoxCPM2-bf16 $H/VoxCPM2-bf16 "*.json" "*.safetensors" "*.md"
echo "3/3 Mô hình nghe chép lời Whisper large-v3-turbo (≈ 1,6 GB) → $H/whisper-turbo"
$H/mlx-env/bin/python download_model.py mlx-community/whisper-large-v3-turbo $H/whisper-turbo "*.json" "*.safetensors" "*.md"
echo "Kiểm tra server …"
$H/mlx-env/bin/python selftest.py $([[ $1 == --test ]] || echo --quick)
cat <<MSG

Cài xong. Đăng ký server với Claude Code (một lần):
  claude mcp add --scope user voice -- ${0:A:h}/voice-mcp
Với Claude Desktop: xem GUIDE.md, mục "Kết nối với AI".
MSG
