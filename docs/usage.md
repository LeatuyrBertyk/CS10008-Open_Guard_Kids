# Hướng dẫn sử dụng

> Dành cho phụ huynh và trẻ sử dụng hàng ngày.

## Phần 1: Dành cho phụ huynh

### Đăng nhập

1. Mở trình duyệt (Chrome/Edge/Firefox)
2. Vào: **http://127.0.0.1:8000** (hoặc địa chỉ server bạn cài)
3. Nhập username + password
4. Bấm "Đăng nhập"

Lần đầu dùng tài khoản demo: `admin` / `admin123`. **Hãy đổi mật khẩu ngay.**

### Tổng quan Dashboard

Sau khi đăng nhập, bạn thấy:

- **📊 Tổng quan các thiết bị** - mỗi máy của con là 1 card
- Mỗi card hiển thị:
  - Tên con
  - 🟢 Online / ⚪ Offline
  - Thời gian dùng hôm nay (phút)
  - Lần cuối truy cập
  - 2 nút: **📊 Chi tiết** và **⚙️ Luật**

### Xem chi tiết 1 trẻ

Bấm **📊 Chi tiết** trên card con:

- **Thời gian dùng trong 7 ngày** (tổng phút)
- **Số lần bị chặn** trong 7 ngày
- **Top ứng dụng** - con dùng nhiều nhất
- **Top website** - con vào nhiều nhất
- **Lịch sử sự kiện** - mỗi lần mở app, vào web, bị chặn

### Đặt luật cho con

Bấm **⚙️ Luật** trên card con, hoặc vào chi tiết → "Sửa luật":

#### Giới hạn thời gian
- Nhập số phút tối đa/ngày
- Mặc định: 120 phút (2 tiếng)
- Con sẽ bị khóa máy khi hết

#### Giờ đi ngủ
- Đặt khoảng thời gian (vd 22:00 - 06:00)
- Trong khoảng này, máy sẽ tự khóa

#### Ứng dụng bị chặn
- Mỗi tên app 1 dòng
- Ví dụ:
  ```
  steam
  discord
  vlc
  ```
- Tên process không có `.exe` (vd `chrome`, không phải `chrome.exe`)

#### Website bị chặn
- Mỗi domain 1 dòng
- Ví dụ:
  ```
  facebook.com
  tiktok.com
  ```
- Hệ thống sẽ chặn cả subdomain

#### Website được phép thêm
- Ngoài danh sách mặc định (111.vn, gov.vn, edu.vn, Windows Update)
- Bạn có thể thêm các trang tin cậy

#### Lịch chặn theo giờ
- Mỗi dòng: `thứ:giờ_bắt_đầu-giờ_kết_thúc`
- Thứ: `mon` `tue` `wed` `thu` `fri` `sat` `sun`
- Ví dụ:
  ```
  mon:19:00-21:00
  wed:19:00-21:00
  sat:14:00-22:00
  sun:14:00-22:00
  ```
- Trong khoảng này, máy sẽ bị khóa

Bấm **💾 Lưu thay đổi** - luật mới sẽ được Agent nhận trong vòng 60 giây.

### Phản hồi yêu cầu của con

Khi con bấm "Xin thêm giờ" hoặc "Bị chặn nhầm", bạn nhận được yêu cầu.

1. Vào menu **📬 Yêu cầu** ở trên cùng
2. Có 4 tab:
   - ⏳ Chờ phản hồi
   - ✅ Đã duyệt
   - ❌ Đã từ chối
   - 📋 Tất cả
3. Bấm **💬 Phản hồi** trên yêu cầu
4. Chọn **Duyệt** hoặc **Từ chối**
5. Nhập số phút cộng thêm (nếu duyệt)
6. Viết lời nhắn cho con
7. Bấm **Gửi phản hồi**

Con sẽ nhận được thông báo ngay lập tức.

## Phần 2: Dành cho trẻ

> Phần mềm này **không phải** công cụ theo dõi lén. Mọi thứ đều minh bạch.

### Khi phần mềm đang chạy

Bạn sẽ thấy:
- **Biểu tượng 🛡️ OGK** ở khay hệ thống (góc phải màn hình, cạnh đồng hồ)
- Có thể thấy cửa sổ thông tin khi bạn click vào biểu tượng

### Bạn có thể xem

Click chuột phải vào biểu tượng 🛡️ → **Mở bảng thông tin**:

- ⏱️ **Bao nhiêu phút còn lại** hôm nay
- 📋 **Luật nào đang áp dụng** (do bố mẹ đặt)
- 🕐 **Giờ đi ngủ** là khi nào
- 🚫 **Ứng dụng/web nào bị chặn**

### Khi bạn cần thêm giờ

1. Click chuột phải vào biểu tượng 🛡️
2. Chọn **⏰ Xin thêm giờ**
3. Nhập lý do (vd: "Con làm bài tập")
4. Nhập số phút muốn thêm
5. Bấm OK

Bố mẹ sẽ nhận được thông báo và phản hồi. Trong thời gian chờ, bạn vẫn dùng máy bình thường.

### Khi bạn nghĩ bị chặn nhầm

1. Click chuột phải vào biểu tượng 🛡️
2. Chọn **🚫 Bị chặn nhầm?**
3. Nhập tên app/trang web bị chặn
4. Giải thích lý do
5. Bấm OK

Bố mẹ sẽ xem xét và có thể bỏ chặn nếu đúng là nhầm.

### Khi máy bị khóa

Máy bị khóa khi:
- Hết thời gian cho phép trong ngày
- Đến giờ đi ngủ
- Trong giờ chặn theo lịch

**Máy không bị khóa hoàn toàn** - bạn vẫn có thể:
- Gọi điện khẩn cấp (111)
- Vào web trường, web chính phủ (.gov.vn, .edu.vn)
- Cập nhật Windows
- Mở phần mềm OGK để xin thêm giờ

### Nguyên tắc sử dụng

Phần mềm này giúp bạn:
- ✅ Có giờ giấc sinh hoạt lành mạnh
- ✅ Tránh các trang web không phù hợp
- ✅ Tập trung học bài

Phần mềm KHÔNG:
- ❌ Đọc nội dung tin nhắn, email, tài liệu của bạn
- ❌ Gửi dữ liệu cho bên thứ ba
- ❌ Ẩn hoạt động (bạn luôn thấy biểu tượng 🛡️)
- ❌ Chặn khi gọi khẩn cấp

Nếu bạn có thắc mắc, hãy nói chuyện với bố mẹ.

## Phần 3: Các câu hỏi thường gặp (FAQ)

### Phụ huynh

**Hỏi: Phần mềm có theo dõi nội dung con gõ trên bàn phím không?**
Trả lời: **KHÔNG**. Chỉ lưu tên app (vd "chrome"), tên miền (vd "facebook.com"), thời gian. Không lưu nội dung, hình ảnh, tin nhắn.

**Hỏi: Nếu server down, con có thể bỏ chặn không?**
Trả lời: Không. Agent lưu policy cuối cùng xuống local. Khi mất mạng, vẫn chặn theo policy đó. Khi có mạng lại, đồng bộ với server.

**Hỏi: Con có thể gỡ phần mềm không?**
Trả lời: Cần quyền Administrator. Bạn không nên cho con quyền này. Nếu đã cho, cài đặt dưới dạng service giúp khó gỡ hơn.

**Hỏi: Tôi có thể dùng 1 tài khoản cho nhiều máy không?**
Trả lời: Có. 1 user (phụ huynh) có thể quản lý nhiều Child, mỗi Child có thể có nhiều Device.

**Hỏi: Khi con thay đổi tên máy, có bị mất liên kết không?**
Trả lời: Không. Liên kết dựa trên device_id (số), không phải hostname.

### Trẻ em

**Hỏi: Bố mẹ có đọc được tin nhắn Zalo của mình không?**
Trả lời: Không. Phần mềm chỉ biết bạn đang dùng Zalo bao nhiêu phút, không đọc nội dung.

**Hỏi: Tại sao tôi phải cài phần mềm này?**
Trả lời: Để giúp bạn có giờ giấc tốt, tránh các trang web không phù hợp, và tập trung học bài. Đây là công cụ hỗ trợ, không phải hình phạt.

**Hỏi: Khi máy bị khóa, tôi có gọi được cấp cứu không?**
Trả lời: Có. Phần mềm **luôn** cho phép gọi 111 và vào các trang chính phủ, trường học.

**Hỏi: Nếu tôi nghĩ trang web bị chặn nhầm?**
Trả lời: Click biểu tượng 🛡️ → "Bị chặn nhầm" → gửi cho bố mẹ. Bố mẹ sẽ xem xét.

---

Nếu có thắc mắc khác, liên hệ tác giả đồ án.
