SeABank

Tài liệu đặc tả yêu cầu người dùng (URD)

CÔNG CỘNG

Mã hiệu: H_99_14_55_01_xxxx

Ngày hiệu lực: 07/03/2025

Lần ban hành/sửa đổi: 1/0

<table><tr><td>12,13.<br/>1,</td><td>SB</td><td><p>- Đầu vào: mã Customer ID</p><p>- Thực hiện: Kiểm tra KH có TKTT chưa?</p><table><thead><tr><td>Nếu</td><td>Thì</td></tr></thead><tbody><tr><td>Đã có TKTT</td><td>Chuyển bước (13.1) – Hiển thị màn hình điền thông tin đăng ký mở EBANK.<br/>→ Chuyển tiếp Quy trình đăng ký mở eBank cho KH đã có TKTT.</td></tr><tr><td>Chưa có TKTT</td><td>Chuyển bước 13.2 – Hệ thống Hiển thị màn hình đăng ký dịch vụ Combo cho Khách hàng.</td></tr></tbody></table></td></tr><tr><td>13.2</td><td>SB</td><td><p>Màn hình đăng ký các dịch vụ combo khi mở ekyc: Hiển thị danh sách các dịch vụ đi kèm để KH lựa chon đăng ký.</p><p>Danh sách dịch vụ đi kèm này sẽ được cấu hình theo yêu cầu tai muc 1.3 trong tài liệu này (các dịch vụ có trạng thái = ACTIVE). Thứ tự Hiển thị các nhóm sản phẩm, sản phẩm mặc định Hiển thị của từng nhóm, nội dung mô tả cho từng nhóm sản phẩm được Hiển thị theo cấu hình mô tại tại mục 1.3</p><p>- Trường hợp mỗi nhóm sản phẩm có nhiều hơn 1 sản phẩm thì Hiển thị như sau:</p><table><thead><tr><td>STT</td><td>Ảnh mockup</td><td>Mô tả mockup</td></tr></thead><tbody><tr><td>1</td><td><img src="https://i.imgur.com/12345.png" alt="Mockup of a mobile app interface for a financial service. The screen shows a red header with white text that reads 'Đăng ký dịch vụ, tiện ích'. Below the header, there are four sections with icons and text. The first section has an icon of a wallet and text that reads 'Mở tài khoản thanh toán định kèm dịch vụ Ebank'. The second section has an icon of a bell and text that reads 'Đăng ký nhận thông báo biến động số dư qua SMS và ứng dụng'. The third section has an icon of a document and text that reads 'Phí định ký (góm VAT): 33,000 VND/tháng. Xem chi tiết biểu phi tại đây'. The fourth section has an icon of a card and text that reads 'Phí được thu từ thông Quy客 đăng ký dịch vụ. Tin BĐSD sẽ gửi về SĐT và thiết bị Quy客 đang dùng.''. The fifth section has an icon of a card and text that reads 'Thẻ Ghi nợ - Visa Gold Debit. Hoàn tiến lên đến 1%. Nhiều ưu đãi hấp dẫn. Chi tiết tại đây'. The sixth section has an icon of a card and text that reads 'Thẻ Tín dụng - "Tên thể". Hoàn tiến lên đến 3%. Nhiều ưu đãi hấp dẫn. Chi tiết tại đây'. The seventh section has an icon of a card and text that reads 'Thẻ Đa năng - "Tên thể". Phi giao dịch ngoại tệ chỉ 1.65%. Nhiều ưu đãi hấp dẫn. Chi tiết tại đây'."></td><td><p><strong>A. Tiêu đề:</strong><br/>VN: “Đăng ký dịch vụ, tiện ích”<br/>EG: “Registration of services”</p><p><strong>B. Vùng nội dung Hiển thị</strong><br/>-Hiển thị các sản phẩm có status="ACTIVE", sắp xếp theo [Thứ tự xuất hiện] giá trị tăng dẫn từ 1 tới n.<br/>-Mô tả các trường tương ứng sẽ được cấu hình tại mục 1.3 sẽ Hiển thị lên giao diện như sau:</p></td></tr></tbody></table></td></tr></table>

Tài liệu Public

ĐVST: KHCN/SP Ekyc (Hoàng Thị Phượng)

IP Phone: 04.8136

Email: phuong.ht3@seabank.com.vn

Trang 15/75