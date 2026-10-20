#!/usr/bin/env bash
# start.sh — jalankan Odoo 20 lokal dengan PostgreSQL container odoo20-db
set -e

ROOT="/home/ram/Documents/Odoo"

# 1. Pastikan database container hidup (rebuild/restart otomatis kalau belum)
if ! docker ps --filter "name=odoo20-db" --filter "status=running" | grep -q odoo20-db; then
  echo "[*] Container odoo20-db tidak jalan → starting..."
  docker start odoo20-db 2>/dev/null || docker run -d --name odoo20-db \
    --restart unless-stopped \
    -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=odoo20 \
    -p 5433:5432 postgres:17-alpine
  sleep 3
fi
docker exec odoo20-db pg_isready -U odoo >/dev/null || { echo "[!] DB belum siap, tunggu beberapa detik"; sleep 3; }

# 2. Matikan instance Odoo lama (kalau ada)
pkill -f "odoo-bin -c $ROOT/odoo20.conf" 2>/dev/null || true
sleep 1

# 3. Start server Odoo di background
cd "$ROOT"
nohup ./venv/bin/python odoo/odoo-bin -c odoo20.conf > odoo.log 2>&1 &
echo "[✓] Odoo PID: $!"
echo "    log : tail -f $ROOT/odoo.log"
echo "    web : http://localhost:8069  (admin / admin)"
echo "[*] Menunggu server siap..."
for i in $(seq 1 30); do
  sleep 2
  if curl -s -o /dev/null -w "" "http://localhost:8069/web/login" 2>/dev/null; then
    echo "[✓] Server UP → http://localhost:8069"
    exit 0
  fi
done
echo "[!] Belum up dalam 60s — cek log: tail -50 $ROOT/odoo.log"
exit 1
