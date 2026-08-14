# P6.1 — Deploy VPS VN + SSL + Agent trỏ cloud

Theo Hiến pháp: Local → VPS Việt Nam, HTTPS bắt buộc trên cloud, Docker Compose, Agent on-prem push HTTPS.

## 1. Chuẩn bị VPS

- Ubuntu 22.04+ (hoặc tương đương), Docker + Compose plugin
- Domain trỏ A/AAAA về IP VPS (trước khi `--ssl`)
- Firewall: mở **22, 80, 443**; đóng 5432 / 6379 / 8000 / 8080 ra Internet
- Tài nguyên khuyến nghị (11§11.3): 4 vCPU / 8GB RAM / SSD

```bash
# Ví dụ UFW
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 2. Đưa mã + secret lên VPS

```bash
git clone <repo> dj-hrm && cd dj-hrm
cp .env.prod.example .env.prod
nano .env.prod   # đổi mọi secret
chmod +x ops/deploy.sh ops/preflight_prod.sh ops/backup.sh ops/restore.sh
./ops/preflight_prod.sh .env.prod
```

Bắt buộc trong `.env.prod`:

| Biến | Ghi chú |
|------|---------|
| `APP_ENV=production` | Bật kiểm tra secret cứng |
| `JWT_SECRET` | ≥ 24 ký tự ngẫu nhiên |
| `AGENT_TOKEN` | Khớp Agent nhà máy |
| `POSTGRES_PASSWORD` | Mạnh |
| `ADMIN_PASSWORD` | Đổi ngay sau seed |
| `CORS_ORIGINS` | `https://your.domain` (không `*`) |
| `TRUSTED_HOSTS` | domain (+ `localhost` nếu cần) |
| `DOMAIN` | Domain công khai (cho Caddy) |
| `CADDY_EMAIL` | Email Let's Encrypt |

## 3. Deploy

### Lần đầu (HTTP nội bộ / kiểm tra trước DNS)

```bash
./ops/deploy.sh --seed
# Health: http://VPS_IP:8080/health
```

### Production HTTPS (P6.1)

DNS đã trỏ →:

```bash
./ops/deploy.sh --ssl
# Health: https://DOMAIN/health
```

Caddy (`docker-compose.ssl.yml`) tự xin chứng chỉ Let's Encrypt và reverse proxy tới `web`.

Cập nhật sau này:

```bash
git pull
./ops/deploy.sh --ssl --skip-backup   # hoặc bỏ --skip-backup để backup trước
```

## 4. Agent nhà máy → cloud

Trên máy Windows Mitapro **(.122 — repo vẫn `D:\HRM\dj-hrm`)**:

```powershell
cd D:\HRM\dj-hrm\apps\agent
copy config.cloud.example.env .env
# Sửa:
#   DJ_API_BASE_URL=https://your.domain
#   DJ_AGENT_TOKEN=<trùng AGENT_TOKEN trên VPS>
#   DJ_AGENT_REQUIRE_HTTPS=1
.\.venv\Scripts\pip install -r requirements.txt
python -m dj_agent.main --once
python -m dj_agent.main
```

Agent từ chối chạy nếu `DJ_AGENT_REQUIRE_HTTPS=1` mà URL không phải `https://`.

Kiểm trên Portal: Cấu Hình → trạng thái Agent / Đồng bộ ngay.

## 5. Backup trên VPS

```bash
./ops/backup.sh
# Cron gợi ý (mỗi ngày 02:00):
# 0 2 * * * cd /opt/dj-hrm && ./ops/backup.sh >> /var/log/djhrm-backup.log 2>&1
```

## 6. Checklist nghiệm thu P6.1

- [ ] `https://DOMAIN/health` OK (db + redis)
- [ ] Đăng nhập Admin / Worker qua HTTPS
- [ ] CORS không lỗi trên trình duyệt
- [ ] Agent `--once` push được punch lên cloud
- [ ] Firewall không mở Postgres/Redis
- [ ] Backup script chạy được trên VPS
