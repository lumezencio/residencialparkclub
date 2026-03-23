#!/bin/bash
echo "=== LIMPANDO REGISTROS ORFAOS ==="
docker exec parkclub_web python manage.py shell -c "
from core.models import MidiaCondominio
import os
count = 0
for m in MidiaCondominio.objects.filter(categoria='projetos_futuros'):
    if not os.path.exists('/app/' + str(m.arquivo)):
        print('Removendo: ' + str(m.arquivo))
        m.delete()
        count += 1
print('Removidos: ' + str(count) + ' registros orfaos')
"

echo ""
echo "=== COPIANDO ARQUIVOS DE MIDIAS PARA O CONTAINER ==="
mkdir -p /tmp/projetos_futuros
cd ~/parkclub/media/condominio/projetos_futuros 2>/dev/null

if [ ! -d ~/parkclub/media/condominio/projetos_futuros ] || [ -z "$(ls ~/parkclub/media/condominio/projetos_futuros/ 2>/dev/null)" ]; then
    echo "Pasta local vazia. Baixando do GitHub..."
    cd ~/parkclub && git pull origin main
fi

echo ""
echo "=== CRIANDO PASTA NO CONTAINER ==="
docker exec parkclub_web mkdir -p /app/media/condominio/projetos_futuros

echo ""
echo "=== COPIANDO ARQUIVOS ==="
docker cp ~/parkclub/media/condominio/projetos_futuros/. parkclub_web:/app/media/condominio/projetos_futuros/

echo ""
echo "=== REGISTRANDO MIDIAS NO BANCO ==="
docker exec parkclub_web python manage.py shell -c "
from core.models import MidiaCondominio
import os

pasta = '/app/media/condominio/projetos_futuros'
extensoes_foto = ['jpg', 'jpeg', 'png', 'webp', 'avif']
extensoes_video = ['mp4', 'mov', 'avi', 'webm']
count = 0

for arquivo in os.listdir(pasta):
    ext = arquivo.rsplit('.', 1)[-1].lower() if '.' in arquivo else ''
    caminho_rel = 'condominio/projetos_futuros/' + arquivo

    ja_existe = MidiaCondominio.objects.filter(arquivo=caminho_rel).exists()
    if ja_existe:
        print('Ja existe: ' + arquivo)
        continue

    if ext in extensoes_foto:
        tipo = 'foto'
    elif ext in extensoes_video:
        tipo = 'video'
    else:
        continue

    MidiaCondominio.objects.create(
        titulo='Projeto Futuro',
        tipo=tipo,
        arquivo=caminho_rel,
        descricao='',
        categoria='projetos_futuros',
        ativo=True,
        destaque=False,
    )
    count += 1
    print('Adicionado: ' + arquivo + ' (' + tipo + ')')

print('')
print('Total adicionados: ' + str(count))
print('Projetos futuros fotos: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', tipo='foto', ativo=True).count()))
print('Projetos futuros videos: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', tipo='video', ativo=True).count()))
"

echo ""
echo "=== VERIFICANDO ==="
docker exec parkclub_web ls -la /app/media/condominio/projetos_futuros/ | head -30
echo ""
echo "=== CONCLUIDO ==="
