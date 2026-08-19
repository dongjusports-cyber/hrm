# DJ Sync Agent (máy nhà máy .122)

Đọc chấm công Mitapro (chỉ SELECT) → đẩy HTTPS lên portal VPS.

Cài đặt / chạy: **không** dùng máy .123. Gói USB:

1. Máy .123: `Thien-Admin\08-CHUAN-USB-122.bat` (chỉ khi Agent .122 hỏng)
2. Copy folder `USB-122-AGENT` sang USB
3. Máy .122: dán `D:\122-AGENT`, chạy `01` → `02` → `04`

Thư mục mẫu trong repo: `122/`. Không copy `.venv` giữa các máy.

## Dev / mock (máy có Python, API đang chạy)

```powershell
cd apps\agent
copy config.example.env .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python -m dj_agent.main --mock --once
```

Chạy thật: `python -m dj_agent.main --once` hoặc vòng lặp `python -m dj_agent.main`.
