# Tổng đài AI tiếng Việt chạy tại chỗ

Gọi vào một số nội bộ, nói tiếng Việt, máy nghe hiểu và trả lời bằng giọng người.
Tra được số dư, giao dịch, khoá thẻ, hạn mức. Trả lời thông tin chung (lãi suất, tỷ giá, phí, giờ làm việc). Chuyển máy cho nhân viên khi cần.

**Toàn bộ chạy trên máy tại chỗ. Không gửi gì lên đám mây. Không tốn tiền dịch vụ.**

*Self-Hosted Vietnamese AI Voice Agent for Asterisk PBX*

---

## Chạy được trên máy gì

Đã chạy thật trên: Intel i7-1185G7 (4 nhân, 2020) · 32GB RAM · **không GPU rời** · Windows 11 + WSL2 Ubuntu 24.04.

| Cần | Vì sao |
|---|---|
| 4 nhân CPU trở lên | ba mô hình chạy cùng lúc |
| 8GB RAM cấp cho WSL | mô hình chiếm ~4GB |
| 5GB đĩa | mô hình + Docker |
| iGPU Intel (tuỳ chọn) | nạp câu hỏi nhanh gấp 5 lần |

---

## Cài từ đầu

### 1. Docker trong WSL2

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 python3-pip python3-venv sox
sudo usermod -aG docker $USER
```
Rồi **thoát WSL và vào lại**: nếu không sẽ báo `permission denied`.

⚠️ **Mạng không thông IPv6 thì Docker không tải được image:**
```bash
sudo ip -6 addr flush dev eth0
sudo service docker restart
```
Phải gõ lại sau mỗi lần khởi động máy.

### 2. Thư viện Python

```bash
cd "<thư mục dự án>"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Mô hình nghe (gipformer, 73MB)

```bash
mkdir -p ~/gipformer && cd ~/gipformer
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('g-group-ai-lab/gipformer1.5-65M-rnnt', local_dir='.')"
```

### 4. Mô hình hiểu (llama.cpp + OpenVINO)

Vào trang phát hành của `ggml-org/llama.cpp`, tải bản `bin-ubuntu-openvino-*-x64.tar.gz` mới nhất:

```bash
mkdir -p ~/llamacpp/openvino && cd ~/llamacpp
tar -xzf llama-ov.tar.gz -C openvino
```

Dùng iGPU Intel thì thêm:
```bash
sudo apt-get install -y intel-opencl-icd clinfo
clinfo -l
```
Phải thấy dòng có `Intel` và `Graphics`.

### 5. Mô hình nói (Piper, 63MB)

```bash
mkdir -p ~/piper && cd ~/piper
curl -L -o piper.tar.gz https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz
tar -xzf piper.tar.gz
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json
```

### 6. Softphone

Cài **Zoiper 5** (hoặc Linphone) trên Windows, khai:

| | |
|---|---|
| Tài khoản | `1001` |
| Mật khẩu | `matkhau1001` |
| Máy chủ | địa chỉ IP của WSL (`ip addr show eth0`) |

⚠️ Zoiper phải bật **gửi DTMF**: tổng đài nhận số điện thoại qua bàn phím.

🔒 **Mật khẩu SIP trong `asterisk/config/pjsip.conf` là mật khẩu mẫu.** Đổi trước khi cho máy nghe được từ mạng ngoài. Tổng đài SIP mở ra Internet với mật khẩu đoán được là bị quét rồi gọi quốc tế mất tiền.

---

## Chạy hằng ngày

Cần **ba cửa sổ terminal**.

**Cửa sổ 1: mô hình hiểu:**
```bash
cd ~/llamacpp/openvino/llama-b*
GGML_OPENVINO_DEVICE=GPU ./llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M -c 2048 -t 4 --host 127.0.0.1 --port 8080
```

**Cửa sổ 2: tổng đài:**
```bash
sudo service docker start
sudo ip -6 addr flush dev eth0
cd "<thư mục dự án>"
docker compose up -d
docker exec tongdai asterisk -rx "pjsip show endpoints"
```
Số 1001 phải ở trạng thái `Not in use`.

**Cửa sổ 3: bộ điều khiển:**
```bash
cd "<thư mục dự án>/app"
source ../.venv/bin/activate
python3 switchboard.py 2>/dev/null
```

Chờ `AudioSocket dang cho o 127.0.0.1:9092`, rồi từ Zoiper **gọi số 600**.

---

## Kiểm thử

**Test tự động**: không cần model, không cần container, không cần gọi điện:
```bash
source .venv/bin/activate
pytest
```
49 test, chạy dưới 1 giây.

**Thử hội thoại không cần nói**: chỉ cần cửa sổ 1:
```bash
cd tests
python3 try_without_calling.py
python3 try_without_calling.py "tôi muốn khoá thẻ" "đúng rồi"
```
In cả thời gian nạp/sinh token và cache của llama-server, dùng để tìm chỗ chậm.
⚠️ Tắt `switchboard.py` khi đo: hai bên tranh CPU làm số cao gấp rưỡi.

**Thử đường tiếng AudioSocket:**
```bash
cd tests
python3 try_audiosocket.py
```
Rồi gọi 600, nó vọng lại tiếng bạn.

**So mô hình nghe:**
```bash
cd tests
python3 compare_speech_models.py <file.sln> ...
```

---

## Các số gọi được

| Số | Làm gì |
|---|---|
| **600** | tổng đài AI — cái chính |
| 200 | vọng lại tiếng mình (thử đường tiếng) |
| 900 | chuyển thẳng cho nhân viên (1002) |

---

## Thử được gì

```
Người gọi: "tôi muốn biết số dư tài khoản"
Tổng đài:  "Anh chị bấm số điện thoại rồi bấm dấu thăng ạ."
Người gọi: bấm 0901234567 #
Tổng đài:  "Dạ số dư tài khoản của anh chị là 12 triệu 450 nghìn đồng."

Người gọi: "lãi suất tiết kiệm bao nhiêu"
Tổng đài:  "Dạ lãi suất tiết kiệm sáu tháng là bốn phẩy sáu phần trăm một năm..."

Người gọi: "tôi muốn khoá thẻ"
Tổng đài:  "Anh chị xác nhận khoá thẻ ạ?"
Người gọi: "đúng rồi"
Tổng đài:  "Dạ em đã khoá thẻ của anh chị thành công."
```

Ba số điện thoại trong dữ liệu mẫu: `0901234567` · `0987654321` · `0912345678`

---

## Cấu tạo

```
Zoiper --SIP--> Asterisk (Docker) --AudioSocket TCP--> switchboard.py
                                                        |-- gipformer   nghe
                                                        |-- Qwen3-4B    hiểu
                                                        |-- Piper       nói
```

Dialplan chỉ **một dòng** cho toàn bộ tổng đài AI. Mọi logic nằm trong Python.

Định danh trong code viết tiếng Anh; tiếng Việt để dành cho câu tổng đài nói, lời dẫn LLM và tài liệu. Chi tiết ở `CONTRIBUTING.md`.

| File | Việc |
|---|---|
| `app/switchboard.py` | mạng, đọc/ghi khung tiếng, vòng cuộc gọi |
| `app/conversation.py` | một lượt hội thoại: gọi LLM, chọn việc, lọc câu trả lời |
| `app/models.py` | bọc ba mô hình (nghe · nói nhanh · nói đẹp) |
| `app/audiosocket.py` | giao thức AudioSocket |
| `app/bank_data.py` | dữ liệu khách hàng + 4 việc tra được |
| `app/bank_docs.py` | tra tài liệu, đọc lại file khi nó đổi |
| `app/voice_library.py` | nhớ câu đã sinh để lần sau phát ngay |
| `app/transcript_fixup.py` | sửa từ gần âm ("số dừa" thành "số dư") |
| `app/prompt.txt` | lời dẫn cho LLM — sửa được không cần sửa code |
| `app/docs/*.json` | tài liệu và số liệu — **đổi lúc đang chạy** |

| Khối | Dùng gì | Giấy phép |
|---|---|---|
| Tổng đài | Asterisk 23.4.1 | GPLv2 |
| Nghe | `g-group-ai-lab/gipformer1.5-65M-rnnt` (sherpa-onnx int8) | MIT |
| Hiểu | `unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M` (llama.cpp + OpenVINO) | Apache 2.0 |
| Nói (động) | Piper `vi_VN-vais1000-medium` | MIT |
| Nói (câu hay lặp) | VieNeu-TTS v3-Turbo, giọng *Mỹ Duyên* | Apache 2.0 |

**Không dùng dịch vụ trả tiền nào. Không gửi dữ liệu ra ngoài máy.**

---

## Số liệu đổi được lúc đang chạy

`app/docs/figures.json` chứa lãi suất, tỷ giá, giá vàng. Sửa file là tổng đài đọc số mới **ngay lượt sau**: không khởi động lại, không sửa code.

Đây là chỗ hệ thống ngân hàng ghi số vào. Số viết **thành chữ** (*"bốn phẩy sáu"*) vì máy đọc ký hiệu phần trăm không ra.

---

## Nhanh chậm ra sao

Đo thật trên máy nói ở trên:

| Khối | Thời gian |
|---|---|
| Nghe (gipformer) | **0,2 – 0,6s** |
| Hiểu (Qwen3-4B) | 3,5 – 4,5s khi tra tài liệu · 5 – 8s khi tự soạn câu |
| Nói (Piper) | 1,2 – 1,7s · **0s** nếu câu đã có trong thư viện |
| **Một lượt** | **4 – 9 giây** |

⚠️ **Lượt đầu tiên sau khi bật llama-server mất ~25 giây**, không phải 4-9. Cache tiền tố chưa có gì
nên nó phải nạp trọn lời dẫn 950 token. Lượt thứ hai trở đi mới nhanh. Xem `cache` trong log: bằng 0
là đang nạp lại từ đầu.

⚠️ **Không đạt chuẩn ngành (200–400ms).** Đó là giá của việc chạy mô hình trên CPU không GPU: repo tương tự (`hkjarral/Asterisk-AI-Voice-Agent`) cũng ghi 5–15 giây mỗi lượt.

**Nhiều cuộc gọi song song:** kiến trúc chịu được (mỗi cuộc một luồng, ba mô hình dùng chung an toàn), nhưng **llama-server xử lý tuần tự** nên 3 cuộc mất 26 giây thay vì 9. Thực tế phục vụ **1 cuộc tại một thời điểm** với độ trễ chấp nhận được.

---

## Không tin mô hình — chặn bằng code

Bốn chỗ mô hình hay sai, đều chặn bằng dữ kiện thay vì bằng lời dẫn:

| Mô hình làm sai | Chặn thế nào |
|---|---|
| Bịa số điện thoại (chép từ ví dụ trong lời dẫn) | số phải **thật sự được bấm** trên bàn phím; DTMF là tín hiệu số nên không nghe sai |
| Bịa lãi suất, tỷ giá, giá vàng | câu mô hình **tự soạn** mà có chữ số thì bỏ, tìm chủ đề theo từ khoá, không có thì nói không nắm được |
| Gọi `khoa_the` khi không ai yêu cầu | việc **thay đổi dữ liệu** phải qua một lượt xác nhận, người gọi nói "đúng rồi" mới chạy |
| Viết sai khuôn lệnh, lệnh lọt ra loa | câu trả lời còn chứa `@` thì không phát |

---

## Chưa làm được

| | |
|---|---|
| **Nói chen ngang** (barge-in) | ⚠️ **đã làm được rồi tắt.** Tiếng máy dội lại làm cắt lời giả gần mọi lượt (bài toán triệt tiếng vọng). Và câu trả lời chỉ 2-3 giây nên cắt lời tiết kiệm ~1 giây, trong khi thời gian chờ thật là 4-9 giây lúc máy **im lặng**. Đường còn lại: cho bấm DTMF để ngừng phát |
| **Phòng có nhạc CÓ GIỌNG HÁT** | tiếng nói lẫn giọng hát thì nghe sai nhiều. Đã thử 4 cách, không cách nào đủ. Lý do là **cấu trúc**: mọi mô hình lọc ồn được huấn luyện để **GIỮ** giọng người nên giữ luôn giọng hát |
| **Hỏi gì cũng trả lời được** | mô hình 4B không có kiến thức đó. Trả lời được 17 chủ đề ngân hàng, ngoài ra thì nói không biết và chuyển nhân viên |
| Nhận dạng người gọi | chưa có |

---

## Hỏng thì xem đâu

| Triệu chứng | Nguyên nhân hay gặp |
|---|---|
| Gọi 600 không ai bắt | cửa sổ 3 chưa chạy, hoặc Zoiper mất đăng ký (tắt/mở lại Zoiper) |
| `pjsip show endpoints` ra `Unavailable` | Zoiper chưa đăng ký. Container vừa dựng lại thì phải tắt/mở Zoiper |
| Docker không tải được image | IPv6 — chạy `sudo ip -6 addr flush dev eth0` |
| Container tự tắt, log `ASTERISK EXITING` | thiếu file trong `asterisk/config/` (gắn thư mục này **che hết** file gốc của image) |
| Khối hiểu trả về rỗng | mô hình bật thinking mode — phải có `chat_template_kwargs` với `enable_thinking` bằng false |
| Bấm số mà log không in gì | Zoiper chưa bật gửi DTMF |
| `Invalid input shape` | đoạn ghi quá ngắn — gipformer cần tối thiểu ~1 giây |
| Log đầy `Creating a resampler` | sherpa-onnx tự đổi 8kHz sang 16kHz, bình thường. Chạy với `2>/dev/null` |