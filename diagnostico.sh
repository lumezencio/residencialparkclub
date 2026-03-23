#!/bin/bash
echo "=== DIAGNOSTICO MIDIAS ==="
docker exec parkclub_web python manage.py shell -c "
from core.models import MidiaCondominio
import os

print('TODAS AS MIDIAS NO BANCO:')
for m in MidiaCondominio.objects.all().order_by('categoria', 'tipo'):
    caminho = '/app/' + str(m.arquivo)
    existe = os.path.exists(caminho)
    tamanho = 0
    if existe:
        tamanho = os.path.getsize(caminho)
    print('  id=' + str(m.id) + ' | ' + m.categoria + ' | ' + m.tipo + ' | ativo=' + str(m.ativo) + ' | existe=' + str(existe) + ' | tamanho=' + str(tamanho) + ' | ' + str(m.arquivo))

print('')
print('RESUMO:')
print('  Total: ' + str(MidiaCondominio.objects.count()))
print('  Condominio fotos ativas: ' + str(MidiaCondominio.objects.filter(categoria='condominio', ativo=True, tipo='foto').count()))
print('  Condominio videos ativos: ' + str(MidiaCondominio.objects.filter(categoria='condominio', ativo=True, tipo='video').count()))
print('  Projetos futuros fotos ativas: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', ativo=True, tipo='foto').count()))
print('  Projetos futuros videos ativos: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', ativo=True, tipo='video').count()))
print('  Midias INATIVAS: ' + str(MidiaCondominio.objects.filter(ativo=False).count()))
"

echo ""
echo "=== ARQUIVOS FISICOS NA PASTA MEDIA ==="
docker exec parkclub_web find /app/media/condominio -type f 2>/dev/null | head -30
docker exec parkclub_web du -sh /app/media/ 2>/dev/null
