# Sửa code này

## Trước khi sửa

```bash
source .venv/bin/activate
pytest
```
49 test phải đậu hết. Đỏ ngay từ đầu thì đừng sửa gì, tìm nguyên nhân trước.

## Sau khi sửa

```bash
pytest
```
Sửa phần hội thoại thì chạy thêm:
```bash
cd tests && python3 try_without_calling.py
```
(cần llama-server đang chạy)

## Sửa gì thì vào file nào

| Muốn đổi | Sửa file |
|---|---|
| Cách máy nói chuyện, giọng điệu | `app/prompt.txt` |
| Lãi suất, tỷ giá, giá vàng | `app/docs/figures.json` |
| Câu trả lời cho chủ đề chung | `app/docs/topics.json` |
| Thêm chủ đề mới | `topics.json` + danh sách trong `prompt.txt` + `KEYWORDS` trong `bank_docs.py` |
| Dữ liệu khách hàng, việc tra được | `app/bank_data.py` |
| Ngưỡng nghe, thời gian chờ | hằng số đầu `app/switchboard.py` |
| Độ dài câu trả lời, số lượt nhớ | hằng số đầu `app/conversation.py` |
| Đổi mô hình nghe/nói | `app/models.py` |

Mọi hằng số nằm ở **đầu file**, không rải trong hàm.

## Ba quy tắc của code này

**1. Không tin mô hình, kiểm bằng dữ kiện.**
Số điện thoại lấy từ DTMF chứ không từ chữ mô hình viết. Số liệu chỉ đến từ tài liệu. Việc thay đổi dữ liệu phải có người xác nhận. Chi tiết ở mục "Không tin mô hình" trong `README.md`.

**2. Không chữa lỗi mô hình bằng cách viết thêm vào lời dẫn.**
Đã thử nhiều lần, mô hình 4B không tuân dù có ví dụ y hệt. Chặn bằng code thì chắc.

**3. Không hard code từng ca.**
Bảng "chữ này thành số kia" đã bị bỏ vì mỗi lỗi mới lại phải thêm một dòng, không có điểm dừng. Thay bằng DTMF.

## Tên trong code

Định danh (biến, hàm, lớp, file) viết tiếng Anh. Tiếng Việt chỉ nằm ở chỗ người Việt đọc hoặc nghe:

| Giữ tiếng Việt | Vì sao |
|---|---|
| Câu tổng đài nói với người gọi | người gọi nghe |
| `prompt.txt` | mô hình phải trả lời tiếng Việt |
| `docs/*.json` | tài liệu đọc cho người gọi |
| Khoá trong `ACTIONS` và `KEYWORDS` (`tra_so_du`, `gia_vang`) | mô hình viết đúng mấy chữ này sau `@TRA` và `@DOC` — đổi là phải sửa `prompt.txt` theo |
| Từ trong `CONSENT_WORDS`, `REFUSAL_WORDS` | là tiếng người gọi nói |
| Dòng log in ra terminal | Khang đọc |

## Chỗ dễ hỏng

| Chỗ | Vì sao |
|---|---|
| `audiosocket.py` — độ dài khung | **big-endian**, còn mẫu audio là **little-endian**. Sai một chỗ là lệch hết khung |
| `_read_exactly` | phải đọc cho **đủ** số byte, TCP có thể cắt gói giữa đường |
| Loại khung lạ | Asterisk 23.1 thêm type `0x11`–`0x18`. **Đừng** `assert frame_type == 0x10` |
| `prompt.txt` | đổi một chữ là **mất sạch cache** của llama-server, lượt đầu chậm lại |
| Ngưỡng VAD | mức 3 (khắt khe nhất). Hạ xuống là nó nhận cả nhạc |

## Đo hiệu năng

`try_without_calling.py` in ra thời gian nạp/sinh token và cache của llama-server. Đó là chỗ xem khi thấy chậm: nếu `cache 0` mỗi lượt thì lời dẫn vừa bị đổi.

⚠️ Tắt `switchboard.py` khi đo, hai bên tranh CPU làm số cao gấp rưỡi.
