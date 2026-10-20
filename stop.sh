#!/usr/bin/env bash
# stop.sh — matikan server Odoo lokal
ROOT="/home/ram/Documents/Odoo"
pkill -f "odoo-bin.*odoo20\.conf"
echo "[✓] Odoo dihentikan (container odoo20-db biarkan tetap hidup)"
