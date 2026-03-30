#!/bin/bash
echo "==============================="
echo "  Limpeza de Disco - Park Club"
echo "==============================="

echo ""
echo "[1/5] Uso atual do disco:"
df -h / | tail -1

echo ""
echo "[2/5] Maiores consumidores:"
du -sh /var/lib/docker 2>/dev/null
du -sh /var/log 2>/dev/null
du -sh ~/parkclub/media 2>/dev/null
du -sh /var/lib/docker/overlay2 2>/dev/null

echo ""
echo "[3/5] Limpando imagens Docker antigas..."
docker image prune -af
docker builder prune -af

echo ""
echo "[4/5] Limpando logs do Docker..."
truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null
echo "Logs truncados."

echo ""
echo "[5/5] Limpando cache do sistema..."
apt-get clean 2>/dev/null
rm -rf /tmp/* 2>/dev/null
journalctl --vacuum-size=50M 2>/dev/null

echo ""
echo "==============================="
echo "  Uso do disco DEPOIS:"
df -h / | tail -1
echo "==============================="
