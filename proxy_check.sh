#!/bin/bash
# Verifica e garante que o proxy compartilhado esta rodando
# Rode este script apos qualquer mudanca que reinicie containers

echo "==================================="
echo "  Verificacao do Proxy Compartilhado"
echo "==================================="

# Verifica se shared_proxy esta rodando
if ! docker ps --format '{{.Names}}' | grep -q '^shared_proxy$'; then
    echo "AVISO: shared_proxy nao esta rodando!"
    echo "Tentando subir..."
    cd /opt/proxy && docker compose up -d
else
    echo "OK: shared_proxy rodando"
fi

# Verifica se shared_proxy esta conectado as redes corretas
NETS=$(docker inspect shared_proxy -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null)
echo ""
echo "Redes do shared_proxy: $NETS"

if ! echo "$NETS" | grep -q "parkclub_backend"; then
    echo "Reconectando parkclub_backend..."
    docker network connect parkclub_backend shared_proxy 2>/dev/null
fi

if ! echo "$NETS" | grep -q "web_ct_backend"; then
    echo "Reconectando web_ct_backend..."
    docker network connect web_ct_backend shared_proxy 2>/dev/null
fi

# Testa se Park Club responde
echo ""
echo "Testando Park Club..."
CODE=$(curl -sk -o /dev/null -w '%{http_code}' -H 'Host: condominioparkclub.com.br' https://localhost)
if [ "$CODE" = "200" ]; then
    echo "OK: Park Club respondendo (HTTP $CODE)"
else
    echo "AVISO: Park Club retornou HTTP $CODE"
fi

# Testa se CondoTower responde
echo ""
echo "Testando CondoTower..."
CODE=$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: condotower.com.br' http://localhost)
echo "CondoTower retornou HTTP $CODE"

echo ""
echo "Containers ativos:"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
