# DJ Sync Agent (Windows / Mitapro)

Đọc chấm công **Mitapro SQL Server** (read-only) → đẩy HTTPS JSON lên DJ HRM API.

```
[Mitapro MITACOSQL] --SELECT--> [DJ Agent] --X-Agent-Token--> [/api/integrations/mitapro/push]
```

## Yêu cầu máy nhà máy

- Windows có Mitapro + SQL Server (`.\SQLEXPRESS` / DB `MITACOSQL`)
- [ODBC Driver 17 hoặc 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Python 3.11+ (khuyến nghị 3.12)
- API DJ HRM đang chạy (local Docker hoặc Cloud VPS) + `AGENT_TOKEN` khớp

## Cài đặt nhanh

```powershell
cd D:\HRM\dj-hrm\apps\agent
copy config.example.env .env
# Sửa DJ_API_BASE_URL + DJ_AGENT_TOKEN + MITAPRO_ODBC trong .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### Chạy thử không cần SQL (mock)

API phải đang chạy và token khớp `.env` gốc dự án:

```powershell
python -m dj_agent.main --mock --once
```

### Chạy thật trên máy Mitapro

```powershell
python -m dj_agent.main --once    # 1 lần
python -m dj_agent.main           # vòng lặp mỗi SYNC_INTERVAL_MINUTES
```

Nút **Đồng bộ ngay** trên Web tạo job `requested` — Agent poll `/api/integrations/mitapro/pending` rồi đẩy dữ liệu.

## Query đọc punch (Hiến pháp 04)

```sql
SELECT nv.MaNhanVien, io.MaChamCong, io.GioCham
FROM CheckInOut io
JOIN NHANVIEN nv ON nv.MaChamCong = io.MaChamCong
WHERE io.GioCham >= @from AND io.GioCham < @to
```

Cột vào/ra / số máy: **xác nhận trên máy SQLEXPRESS** rồi bổ sung vào `sql_reader.py`.

## Trỏ Cloud VPS (P6.1)

```powershell
copy config.cloud.example.env .env
# DJ_API_BASE_URL=https://your.domain
# DJ_AGENT_TOKEN=<trùng AGENT_TOKEN VPS>
# DJ_AGENT_REQUIRE_HTTPS=1
python -m dj_agent.main --once
```

Khi `DJ_AGENT_REQUIRE_HTTPS=1`, Agent từ chối URL `http://`.

## Bảo mật

- Chỉ SELECT — không UPDATE/DELETE Mitapro
- Chỉ push lên API bằng `DJ_AGENT_TOKEN`
- Cloud: bắt buộc HTTPS (`config.cloud.example.env`)
- Không commit file `.env` / `agent_state.json` có secret

## Icon khay hệ thống

P2.2 tập trung đồng bộ ổn định (console + log). Tray xanh/vàng/đỏ có thể thêm sau (pystray) khi Agent đã chạy ổn 7 ngày.
