# Cách sửa code này

## Trước khi sửa

```bash
source moi-truong/bin/activate
pytest
```
49 test phải đậu hết. Nếu đã đỏ từ đầu thì đừng sửa gì, tìm nguyên nhân trước.

## Sau khi sửa

```bash
pytest
```
Và nếu sửa phần hội thoại, chạy thêm:
```bash
cd kiem-thu && python3 thu_khong_can_goi.py
```
(cần llama-server đang chạy)

## Sửa gì thì vào file nào

| Muốn đổi | Sửa file |
|---|---|
| Cách máy nói chuyện, giọng điệu | `dieu-khien/loi_dan.txt` |
| Lãi suất, tỷ giá, giá vàng | `dieu-khien/tai-lieu/so_lieu.json` |
| Câu trả lời cho chủ đề chung | `dieu-khien/tai-lieu/tai_lieu.json` |
| Thêm chủ đề mới | `tai_lieu.json` + danh sách trong `loi_dan.txt` + `TU_KHOA` trong `tai_lieu_ngan_hang.py` |
| Dữ liệu khách hàng, việc tra được | `dieu-khien/du_lieu_ngan_hang.py` |
| Ngưỡng nghe, thời gian chờ | hằng số đầu `dieu-khien/tong_dai.py` |
| Độ dài câu trả lời, số lượt nhớ | hằng số đầu `dieu-khien/hoi_thoai.py` |
| Đổi mô hình nghe/nói | `dieu-khien/mo_hinh.py` |

Mọi hằng số nằm ở **đầu file**, không rải trong hàm.

## Ba quy tắc của code này

**1. Không tin mô hình, kiểm bằng dữ kiện.**
Số điện thoại lấy từ DTMF chứ không từ chữ mô hình viết. Số liệu chỉ đến từ tài liệu. Việc thay đổi dữ liệu phải có người xác nhận. Chi tiết ở mục "Không tin mô hình" trong `README.md`.

**2. Không chữa lỗi mô hình bằng cách viết thêm vào lời dẫn.**
Đã thử nhiều lần, mô hình 4B không tuân dù có ví dụ y hệt. Chặn bằng code thì chắc.

**3. Không hard code từng ca.**
Bảng "chữ này thành số kia" đã bị bỏ vì mỗi lỗi mới lại phải thêm một dòng, không có điểm dừng. Thay bằng DTMF.

## Chỗ dễ hỏng

| Chỗ | Vì sao |
|---|---|
| `audiosocket.py` — độ dài khung | **big-endian**, còn mẫu audio là **little-endian**. Sai một chỗ là lệch hết khung |
| `_doc_du` | phải đọc cho **đủ** số byte, TCP có thể cắt gói giữa đường |
| Loại khung lạ | Asterisk 23.1 thêm type `0x11`–`0x18`. **Đừng** `assert loai == 0x10` |
| `loi_dan.txt` | đổi một chữ là **mất sạch cache** của llama-server, lượt đầu chậm lại |
| Ngưỡng VAD | mức 3 (khắt khe nhất). Hạ xuống là nó nhận cả nhạc |

## Đo hiệu năng

`thu_khong_can_goi.py` in ra thời gian nạp/sinh token và cache của llama-server. Đó là chỗ xem khi thấy chậm — nếu `cache 0` mỗi lượt thì lời dẫn vừa bị đổi.

⚠️ Tắt `tong_dai.py` khi đo, hai bên tranh CPU làm số cao gấp rưỡi.
