# DJ HRM

Hệ thống HRM cloud (Web) cho nhà máy **DONGJU Sports Việt Nam** (~500 nhân sự).

> Tài liệu nghiệp vụ & luật thiết kế: thư mục [`HIEN_PHAP/`](./HIEN_PHAP/) — đọc `00_README_CHO_AI.md` trước.

## Stack

| Lớp | Công nghệ |
|-----|-----------|
| Backend | Python FastAPI + SQLAlchemy + Alembic |
| Frontend | React (Vite) + TypeScript + AG-Grid |
| DB / Cache | PostgreSQL 16 + Redis 7 |
| Deploy | Docker Compose (local → VPS VN) |

## Chạy local (Windows 10 + Docker Desktop)

```powershell
copy .env.example .env
docker compose up --build
docker compose exec api python -m app.scripts.seed
```

- Web Portal: http://localhost:5173  
- API docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### Tài khoản seed (P0.4/P0.5)

| User | Mật khẩu | Quyền |
|------|----------|--------|
| `admin` | theo `ADMIN_PASSWORD` trong `.env` | 8/8 + `ai_query` |
| `hr.demo` | `HrDemo@123456` | 7 module, **không** Cấu Hình |
| Worker MSNV `5290` | `1234` (đổi lần đầu) | Cổng `/worker` (không vào Portal 8 ô) |

Click ô không có quyền → popup COSMOS AI tiếng Việt (ô vẫn hiện đủ).  
Worker Portal: http://localhost:5173/worker/login

### Agent Mitapro (máy nhà máy)

Xem [`apps/agent/README.md`](./apps/agent/README.md). Mock thử:

```powershell
cd apps\agent
copy config.example.env .env
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
python -m dj_agent.main --mock --once
```

## Nguyên tắc vàng (rút gọn)

1. **Không hard-code** thông số nghiệp vụ (tiền, %, hệ số…) — nằm trong Policy Engine / Cấu Hình  
2. **Decimal** cho mọi tiền tệ  
3. Lỗi UI/API bằng **tiếng Việt**  
4. Portal **8 ô**, không sidebar  
5. **Vừa đủ** (P11): không microservices / K8s / over-engineering  

## Production / VPS (P6.1)

- Compose: `docker-compose.prod.yml` + `docker-compose.ssl.yml` (Caddy HTTPS)
- Mẫu env: `.env.prod.example` → `.env.prod`
- Deploy: `./ops/deploy.sh --ssl` — chi tiết [`ops/DEPLOY_VPS.md`](./ops/DEPLOY_VPS.md)
- Agent cloud: `apps/agent/config.cloud.example.env`
- Backup: [`ops/README.md`](./ops/README.md)

## Lộ trình

Xem `HIEN_PHAP/09_LO_TRINH_PHIEN.md`.
