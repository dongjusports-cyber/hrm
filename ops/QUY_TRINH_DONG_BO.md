# Quy trinh dong bo DJ-HRM: GitHub ↔ VPS ↔ may .123

## Nguyen tac

| Noi | Vai tro | Dong bo gi |
|-----|---------|------------|
| **GitHub** | Nguon code chuan (source of truth) | Code + lich su |
| **VPS** | Production — https://hrm.dongju-v.com | Code + **DB that** (359 NV) |
| **May .123** | Dev / Cursor ban ngay | Code (+ DB local rieng de test) |

**3 ban CODE** cung phien ban khi: push Git → deploy VPS → pull .123.

**DB khong tu dong 3 chieu** — du lieu that chi tren VPS (+ backup). May .123 dung Docker local rieng.

---

## Quy trinh hang ngay (de xuat)

### Toi — Cursor Cloud (test / sua bug)
1. Cloud agent tren repo `main` (hoac nhanh `nightly`)
2. Chay test: `cd apps/api && pytest`, `cd apps/web && npm test`
3. Sua loi → commit → **push GitHub**

### Sang — Dong bo (ban hoac AI tren may co SSH)
1. **VPS:** `Thien-Admin\05-DEPLOY-VPS.bat` hoac `python ops/deploy_vps_from_git.py`
2. **May .123:** `Thien-Admin\04-PULL-VE-123.bat`

---

## Script co san

| File | Viec |
|------|------|
| `Thien-Admin\01-THEM-DEPLOY-KEY.bat` | Khi VPS moi — copy key, mo GitHub |
| `Thien-Admin\02-DONG-BO-SANG.bat` | **Hang ngay** — deploy VPS + pull .123 |
| `Thien-Admin\04-PULL-VE-123.bat` | Chi git pull ve may .123 |
| `Thien-Admin\05-DEPLOY-VPS.bat` | Chi VPS pull + deploy |
| `Thien-Admin\03-MO-KHOA-PORTAL.bat` | Mo khoa admin/hr.demo |
| `ops/setup_github_deploy_key.py` | Tao Deploy Key tren VPS |
| `ops/verify_github_deploy_key.py` | Test VPS ↔ GitHub |

---

## GitHub Deploy Key (mot lan)

1. Chay: `python ops/setup_github_deploy_key.py`
2. Copy noi dung `ops/github_deploy_key.pub`
3. GitHub → repo **dongjusports-cyber/hrm** → Settings → Deploy keys → Add (chi doc, khong Allow write)
4. Test tren VPS: `ssh -T git@github.com`

Sau do VPS `git pull` khong can password.

---

## De xuat them (tuy chon)

1. **GitHub Actions** — tu chay pytest moi khi push (bat loi som)
2. **Nhanh `develop`** — Cloud sua tren develop, merge main khi on
3. **Tag release** — `v2026.08.15` truoc moi lan deploy VPS production
4. **Khong commit** `.env`, `vps-root.txt`, `THONG_TIN_VPS.txt`

---

## Cursor Cloud toi

Prompt mau:

> Chay full test API + web, sua fail, commit push main. Khong doi DB production.

Sang: `Thien-Admin\02-DONG-BO-SANG.bat`.
