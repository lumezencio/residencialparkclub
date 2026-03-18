#!/bin/bash
# ============================================
# DEPLOY - Residencial Park Club
# Execute na DigitalOcean após clonar o repo
# ============================================

set -e

DOMAIN="condominioparkclub.com.br"
EMAIL="condominioparkclubpassos@gmail.com"

echo "============================================"
echo "  DEPLOY - Residencial Park Club"
echo "============================================"

# 1. Instalar Docker (se não tiver)
if ! command -v docker &> /dev/null; then
    echo "[1/7] Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "[1/7] Docker já instalado."
fi

# 2. Instalar Docker Compose plugin
if ! docker compose version &> /dev/null; then
    echo "[2/7] Instalando Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin
else
    echo "[2/7] Docker Compose já instalado."
fi

# 3. Clonar/atualizar repositório
echo "[3/7] Atualizando código..."
if [ -d "/opt/parkclub" ]; then
    cd /opt/parkclub
    git pull origin main
else
    git clone https://github.com/lumezencio/residencialparkclub.git /opt/parkclub
    cd /opt/parkclub
fi

# 4. Copiar mídia local se existir
echo "[4/7] Preparando mídia..."
mkdir -p /opt/parkclub/media

# 5. Subir com config inicial (sem SSL) para gerar certificado
echo "[5/7] Subindo containers (modo inicial sem SSL)..."
cp nginx/nginx-initial.conf nginx/nginx-active.conf
sed -i 's|./nginx/nginx.conf|./nginx/nginx-active.conf|' docker-compose.prod.yml 2>/dev/null || true

docker compose -f docker-compose.prod.yml up -d --build

echo "Aguardando containers iniciarem..."
sleep 10

# 6. Rodar migrações e collectstatic
echo "[6/7] Configurando banco de dados..."
docker exec parkclub_web python manage.py migrate --noinput
docker exec parkclub_web python manage.py collectstatic --noinput

# Criar superuser se não existir
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
if not Usuario.objects.filter(username='mezencio').exists():
    Usuario.objects.create_superuser('mezencio', 'lucianomezencio@gmail.com', 'facil2025', first_name='luciano', last_name='tocha', tipo='admin', aprovado=True, bloco='27', apartamento='402')
    print('Superuser mezencio criado')
else:
    print('Superuser mezencio já existe')
"

# 7. Gerar certificado SSL
echo "[7/7] Gerando certificado SSL..."
docker run --rm \
    -v parkclub_certbot_www:/var/www/certbot \
    -v parkclub_certbot_certs:/etc/letsencrypt \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d www.$DOMAIN

# Trocar para config com SSL
echo "Ativando HTTPS..."
cp nginx/nginx.conf nginx/nginx-active.conf
docker compose -f docker-compose.prod.yml restart nginx

echo ""
echo "============================================"
echo "  DEPLOY CONCLUÍDO!"
echo "============================================"
echo ""
echo "  Site: https://$DOMAIN"
echo "  Admin: https://$DOMAIN/admin/"
echo "  Login: mezencio"
echo ""
echo "  Para atualizar no futuro:"
echo "    cd /opt/parkclub"
echo "    git pull origin main"
echo "    docker compose -f docker-compose.prod.yml up -d --build"
echo "    docker exec parkclub_web python manage.py migrate"
echo "    docker exec parkclub_web python manage.py collectstatic --noinput"
echo ""
