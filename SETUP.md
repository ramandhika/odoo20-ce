# Odoo 20 — Local Setup (Best Practice: Source + venv + Docker Postgres)

Replikasi cara setup dari nol sampai jalan, di `/home/ram/Documents/Odoo`.

## Prasyarat
- git, Docker daemon jalan
- Python 3.12 (di-install via [uv](https://docs.astral.sh/uv/), tanpa sudo)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  uv python install 3.12
  ```

## Step 1 — Clone Odoo 20 (shallow, hemat bandwidth)
```bash
cd ~/Documents/Odoo
git clone --depth 1 -b 20.0 https://github.com/odoo/odoo.git odoo
# perdalam ke 10 commit terakhir (bukan full history):
cd odoo && git fetch --depth=10 origin 20.0
```

## Step 2 — Virtual environment + dependencies
```bash
cd ~/Documents/Odoo
uv venv --python 3.12 venv
uv pip install --python ./venv/bin/python -r odoo/requirements.txt
```

## Step 3 — Container PostgreSQL khusus Odoo 20
Port **5433** (untuk tidak tabrakan dengan postgres lokal di 5432).
```bash
docker run -d --name odoo20-db --restart unless-stopped \
  -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=odoo20 \
  -p 5433:5432 postgres:17-alpine
# verifikasi:
docker exec odoo20-db pg_isready -U odoo
```

## Step 4 — Config: `odoo20.conf`
```ini
[options]
db_host = localhost
db_port = 5433
db_user = odoo
db_password = odoo
db_name = odoo20
addons_path = /home/ram/Documents/Odoo/odoo/addons,/home/ram/Documents/Odoo/custom-addons
data_dir = /home/ram/Documents/Odoo/odoo-data
http_port = 8069
workers = 2
```

## Step 5 — Jalankan server
```bash
cd ~/Documents/Odoo
./venv/bin/python odoo/odoo-bin -c odoo20.conf
# -i base akan otomatis jalan saat database baru dibuat via web
```
Buka: **http://localhost:8069** *(login: admin / admin setelah setup DB pertama)*

## Step 6 — Index codebase (codebase-memory-mcp)
Setelah fork proyek pertama berhasil, index repo untuk navigasi cepat:
```bash
codebase-memory-mcp  ; lalu panggil tool index_project dari MCP
```

## Troubleshooting cepat
| Gejala | Fix |
|---|---|
| `psycopg2 OperationalError` | cek `docker ps` → odoo20-db hidup? port 5433 benar? |
| Port 8069 dipakai | `ss -ltnp | grep 8069`, pindah `http_port` |
| Module errors saat install deps | beberapa butuh header C (libldap dll.) — lihat log pip |
