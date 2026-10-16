# Phân tích bảo mật

## Mục đích

OGK Parental Control có đặc thù là phần mềm giám sát - vốn dễ bị lạm dụng thành malware. Tài liệu này phân tích các biện pháp bảo mật đã làm, hạn chế còn tồn tại, và cảnh báo cho người dùng.

## Tuân thủ "Danh mục cấm" (theo yêu cầu giáo viên)

| Hành vi cấm | OGK có làm không? |
|---|---|
| Đọc nội dung tin nhắn/email/tài liệu | ❌ KHÔNG - chỉ lưu metadata |
| Ẩn tiến trình/dịch vụ (rootkit) | ❌ KHÔNG - Service hiển thị trong Services |
| Gửi dữ liệu bên thứ ba | ❌ KHÔNG - chỉ giao tiếp với server cấu hình sẵn |
| Thử trên trẻ thật / máy người khác | ⚠️ CẢNH BÁO trong README |

## Các biện pháp bảo mật đã áp dụng

### 1. Mật khẩu
- Hash bằng **bcrypt** với cost factor = 12 (~250ms/hash, chống brute-force)
- Không bao giờ lưu plain text
- Không log mật khẩu

### 2. JWT Token
- Ký bằng **HS256**
- Hết hạn sau 24 giờ
- Secret key lưu trong env var (không commit vào git)
- Cảnh báo rõ ràng nếu dùng secret mặc định

### 3. Device Token
- Sinh ngẫu nhiên 32 bytes (`secrets.token_urlsafe`)
- Hash bằng bcrypt trước khi lưu DB
- So sánh qua bcrypt (chậm nhưng an toàn)

### 4. HTTPS
- Có sẵn hỗ trợ HTTPS với self-signed cert
- Script `gen_cert.bat` để tạo cert
- ⚠️ Trong production, nên dùng Let's Encrypt

### 5. Audit Log
- Mọi hành động của phụ huynh (đổi luật, phản hồi yêu cầu) đều ghi log
- Bao gồm: ai, làm gì, lúc nào, từ IP nào
- Trẻ có thể xem log này (nguyên tắc NT5)

### 6. Allowlist nghiêm ngặt
- Domain: luôn cho phép 111.vn, .gov.vn, .edu.vn, Windows Update
- Process: không bao giờ chặn system, defender, settings
- → Trẻ luôn gọi được cứu hỏa, vào web trường

## Hạn chế còn tồn tại

### H1. Device Token lookup chưa tối ưu
- Hiện tại phải duyệt qua tất cả device để so sánh bcrypt
- Database lớn sẽ chậm
- **Cải tiến**: dùng HMAC thay vì bcrypt, hoặc index theo prefix

### H2. Không có rate limiting
- Ai đó biết JWT có thể spam API
- **Cải tiến**: thêm `slowapi` rate limit

### H3. Không có 2FA
- Chỉ cần username + password
- **Cải tiến**: thêm TOTP 2FA cho user admin

### H4. Không mã hóa database
- SQLite lưu plain text trên disk
- Nếu attacker có file DB → đọc được hết
- **Cải tiến**: dùng SQLCipher

### H5. DNS proxy có thể bị bypass
- Con có thể đổi DNS thủ công sang 8.8.8.8
- **Khắc phục**: dùng Windows Firewall chặn outgoing port 53 (cần quyền SYSTEM)
- Hiện tại: chỉ chặn được khi máy dùng DNS mặc định

### H6. App Controller có thể bị bypass
- Con có thể đổi tên process (vd `chrome.exe` → `myapp.exe`)
- **Khắc phục**: thêm check thêm parent process, command line, hash

### H7. Không có kill switch
- Nếu server down → Agent vẫn chặn theo policy local cũ
- Phụ huynh không tắt được từ xa
- **Cải tiến**: thêm endpoint "emergency unlock"

## Cảnh báo cho người dùng

⚠️ **Phần mềm này chỉ dành cho mục đích giáo dục**

- KHÔNG cài lên máy người khác khi chưa được phép
- KHÔNG dùng để theo dõi người lớn - vi phạm pháp luật
- KHÔNG dùng làm công cụ kiểm soát bạo lực
- NÊN thông báo rõ cho trẻ biết phần mềm đang chạy
- NÊN thường xuyên xem log kiểm toán

## Cấu hình Production (khuyến nghị)

```bash
# Đổi secret mạnh
export OGK_JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

# Dùng HTTPS thật (Let's Encrypt)
export OGK_USE_HTTPS=true
export OGK_SSL_CERT=/path/to/cert.pem
export OGK_SSL_KEY=/path/to/key.pem

# Chạy ở chế độ production
export OGK_ENV=production
```

## Đánh giá tổng thể

| Tiêu chí | Đánh giá |
|---|---|
| Mã hóa truyền thông | ✅ Có (HTTPS) |
| Xác thực | ✅ JWT + bcrypt |
| Phân quyền | ⚠️ Cơ bản (chỉ parent/admin) |
| Audit | ✅ Có đầy đủ |
| Minh bạch | ✅ Tốt (theo yêu cầu) |
| Chống bypass | ⚠️ Còn yếu (DNS, app) |
| Kill switch | ❌ Chưa có |
| 2FA | ❌ Chưa có |
