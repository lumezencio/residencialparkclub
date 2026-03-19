#!/bin/bash
# ============================================
# UPDATE - Residencial Park Club
# Atualiza o site em produção (DokeHost)
# Uso: bash ~/parkclub/update.sh
# ============================================

set -e

cd ~/parkclub

echo "==============================="
echo "  Atualizando Park Club..."
echo "==============================="

echo "[1/4] Baixando código novo..."
git pull origin main

echo "[2/4] Reconstruindo container..."
docker compose -f docker-compose.prod.yml build --no-cache web

echo "[3/4] Reiniciando serviços..."
docker compose -f docker-compose.prod.yml up -d

echo "[4/4] Atualizando arquivos estáticos..."
docker exec parkclub_web python manage.py collectstatic --noinput
docker exec parkclub_web python manage.py migrate --noinput

# Criar moderador alexjunior se não existir
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
if not Usuario.objects.filter(username='alexjunior').exists():
    u = Usuario.objects.create_user('alexjunior', '', 'NDyfkOz0x8Gv')
    u.first_name = 'Alex'
    u.last_name = 'Junior'
    u.tipo = 'moderador'
    u.aprovado = True
    u.is_staff = True
    u.save()
    print('Moderador alexjunior criado!')
else:
    print('alexjunior ja existe')
"

echo ""
echo "==============================="
echo "  Atualização concluída!"
echo "  Site: https://condominioparkclub.com.br"
echo "==============================="
