#!/bin/bash
# ============================================
# UPDATE - Residencial Park Club
# Atualiza o site em producao (DokeHost)
# Uso: bash ~/parkclub/update.sh
# ============================================

cd ~/parkclub

# Auto-atualizar: baixa o codigo e re-executa o script atualizado
if [ "$1" != "--running" ]; then
    echo "Baixando codigo novo..."
    git pull origin main
    echo "Re-executando script atualizado..."
    exec bash ~/parkclub/update.sh --running
fi

echo "==============================="
echo "  Atualizando Park Club..."
echo "==============================="

echo ""
echo "[1/7] Reconstruindo container..."
docker compose -f docker-compose.prod.yml build --no-cache web

echo ""
echo "[2/7] Reiniciando servicos..."
docker compose -f docker-compose.prod.yml up -d

# Garante que o proxy compartilhado esta rodando (evita conflito de portas)
if [ -d /opt/proxy ]; then
    echo "  -> Verificando proxy compartilhado..."
    cd /opt/proxy && docker compose up -d
    docker network connect parkclub_backend shared_proxy 2>/dev/null || true
    cd ~/parkclub
fi

echo ""
echo "[3/7] Migracoes e arquivos estaticos..."
sleep 5
docker exec parkclub_web python manage.py migrate --noinput
docker exec parkclub_web python manage.py collectstatic --noinput

echo ""
echo "[4/7] Criando usuarios..."
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
if not Usuario.objects.filter(username='alexjunior').exists():
    u = Usuario.objects.create_user('alexjunior', '', 'NDyfkOz0x8Gv')
    u.first_name = 'Alex'
    u.last_name = 'Junior'
    u.tipo = 'moderador'
    u.aprovado = True
    u.is_staff = True
    u.is_active = True
    u.save()
    print('Moderador alexjunior criado!')
else:
    print('Moderador alexjunior ja existe.')
" || echo "ERRO ao criar usuario"

echo ""
echo "[5/7] Limpeza de disco..."
docker image prune -af 2>/dev/null
docker builder prune -af 2>/dev/null
truncate -s 0 /var/lib/docker/containers/*/*-json.log 2>/dev/null
apt-get clean 2>/dev/null
journalctl --vacuum-size=50M 2>/dev/null
echo "Limpeza concluida."

echo ""
echo "[6/7] Diagnostico..."
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
from comunicacao.models import MuralPost
from classificados.models import Anuncio, FotoAnuncio

print('--- ANUNCIOS ---')
for a in Anuncio.objects.all():
    fotos = FotoAnuncio.objects.filter(anuncio=a).count()
    print('  ID:' + str(a.pk) + ' | ' + a.titulo[:40] + ' | ' + a.status + ' | ' + a.tipo + ' | ' + a.autor.first_name + ' | fotos:' + str(fotos))

print('')
print('Aprovados: ' + str(Anuncio.objects.filter(status='aprovado').count()))
print('Pendentes: ' + str(Anuncio.objects.filter(status='pendente').count()))
print('Vendidos: ' + str(Anuncio.objects.filter(status='vendido').count()))
print('')
print('--- RESUMO ---')
print('Posts pendentes: ' + str(MuralPost.objects.filter(aprovado=False).count()))
print('Posts aprovados: ' + str(MuralPost.objects.filter(aprovado=True).count()))
print('Usuarios pendentes: ' + str(Usuario.objects.filter(aprovado=False, is_active=True).count()))
print('Moradores aprovados: ' + str(Usuario.objects.filter(aprovado=True).count()))
"

echo ""
echo "[7/7] Status do disco:"
df -h / | tail -1

echo ""
echo "==============================="
echo "  Atualizacao concluida!"
echo "  Site: https://condominioparkclub.com.br"
echo "==============================="
