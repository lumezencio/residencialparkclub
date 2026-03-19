#!/bin/bash
# ============================================
# UPDATE - Residencial Park Club
# Atualiza o site em produção (DokeHost)
# Uso: bash ~/parkclub/update.sh
# ============================================

cd ~/parkclub

echo "==============================="
echo "  Atualizando Park Club..."
echo "==============================="

echo "[1/5] Baixando código novo..."
git pull origin main

echo "[2/5] Reconstruindo container..."
docker compose -f docker-compose.prod.yml build --no-cache web

echo "[3/5] Reiniciando serviços..."
docker compose -f docker-compose.prod.yml up -d

echo "[4/5] Migrações e arquivos estáticos..."
sleep 5
docker exec parkclub_web python manage.py migrate --noinput
docker exec parkclub_web python manage.py collectstatic --noinput

echo "[5/5] Criando usuários..."
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
# Deletar e recriar alexjunior para garantir dados corretos
Usuario.objects.filter(username='alexjunior').delete()
u = Usuario.objects.create_user('alexjunior', '', 'NDyfkOz0x8Gv')
u.first_name = 'Alex'
u.last_name = 'Junior'
u.tipo = 'moderador'
u.aprovado = True
u.is_staff = True
u.is_active = True
u.save()
print('Moderador alexjunior criado com sucesso!')
print('is_active:', u.is_active, 'aprovado:', u.aprovado, 'tipo:', u.tipo)
" || echo "ERRO ao criar usuario"

echo ""
echo "==============================="
echo "  Atualização concluída!"
echo "  Site: https://condominioparkclub.com.br"
echo "==============================="
