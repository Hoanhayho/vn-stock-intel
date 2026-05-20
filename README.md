# 📈 Vietnam Stock Intelligence Dashboard

Công cụ phân tích cổ phiếu Việt Nam — theo dõi giá thực, phát hiện pump, tín hiệu lướt sóng.

---

## 🚀 Cài đặt & Chạy (5 phút)

### Bước 1 — Cài Python (nếu chưa có)
Tải tại: https://www.python.org/downloads/  
✅ Tích vào **"Add Python to PATH"** khi cài.

### Bước 2 — Mở Terminal / Command Prompt
- **Windows**: nhấn `Win + R`, gõ `cmd`, Enter
- **Mac**: mở **Terminal** trong Applications

### Bước 3 — Vào thư mục app
```
cd đường_dẫn_đến_thư_mục_vn_stock_intel
```
Ví dụ: `cd C:\Users\TenAnh\Downloads\vn_stock_intel`

### Bước 4 — Cài thư viện (chỉ cần làm 1 lần)
```
pip install -r requirements.txt
```
Đợi khoảng 1–2 phút cho đến khi xong.

### Bước 5 — Chạy app
```
streamlit run app.py
```
Browser sẽ tự mở tại **http://localhost:8501** 🎉

---

## 📊 Tính năng

| Tab | Nội dung |
|-----|----------|
| **Tổng quan** | Bảng tất cả mã theo dõi: giá, % ngày, pump score, tín hiệu |
| **Pump Detector** | Cảnh báo cổ phiếu có dấu hiệu thổi giá (volume đột biến, tăng nhanh bất thường) |
| **Lướt sóng T+** | Cơ hội lướt sóng T+2/T+3 với target và cắt lỗ gợi ý |
| **Chi tiết** | Biểu đồ nến + MA5/MA20 + Volume + RSI cho từng mã |

## 🔧 Các preset sẵn có
- VN30 Blue-chip
- Ngân hàng (VCB, TCB, MBB...)
- Thép & Vật liệu (HPG, HSG...)
- Bất động sản (VIC, VHM, NVL...)
- Công nghệ (FPT, CMG...)
- Tiêu dùng & Bán lẻ (VNM, MWG...)

## ⚠️ Disclaimer
Đây là công cụ **hỗ trợ phân tích kỹ thuật**, không phải lời khuyên đầu tư.  
Dữ liệu từ TCBS/VCI qua thư viện vnstock — độ trễ theo phiên giao dịch.  
Tất cả quyết định đầu tư là trách nhiệm của người dùng.

---

## ❓ Lỗi thường gặp

**"vnstock not found"**  
→ Chạy lại: `pip install vnstock --upgrade`

**"No module named streamlit"**  
→ Chạy: `pip install streamlit`

**Không có dữ liệu cho một mã**  
→ Kiểm tra mã đúng theo sàn HOSE/HNX (VD: `VCB` không phải `vcb`)

**Cổng 8501 bị chiếm**  
→ Chạy: `streamlit run app.py --server.port 8502`
