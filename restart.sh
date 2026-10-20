#!/usr/bin/env bash
# restart.sh — restart server Odoo dengan install module (opsional -i list di argumen)
cd /home/ram/Documents/Odoo
pkill -9 -f "odoo-bin -c odoo20.conf" 2>/dev/null
sleep 2
if [ -n "$1" ]; then
  INSTALL="-i $1"
else
  INSTALL=""
fi
rm -f odoo.log
nohup ./venv/bin/python odoo/odoo-bin -c odoo20.conf $INSTALL > odoo.log 2>&1 &
echo "PID $!"
for i in $(seq 1 45); do
  sleep 2
  if curl -s -o /dev/null "http://localhost:8069/web/login" 2>/dev/null; then
    echo "[OK] UP after $((i*2))s"; exit 0
  fi
done
echo "[!] Belum up 90s"; tail -20 odoo.log
exit 1
