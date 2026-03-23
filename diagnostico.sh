#!/bin/bash
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario, MidiaCondominio
from comunicacao.models import MuralPost
from classificados.models import Anuncio
import os

print('=== MIDIAS DO CONDOMINIO ===')
for m in MidiaCondominio.objects.all():
    existe = os.path.exists('/app/' + str(m.arquivo)) if m.arquivo else False
    print('  ' + str(m.id) + ' | ' + m.tipo + ' | ' + m.categoria + ' | ativo: ' + str(m.ativo) + ' | arquivo: ' + str(m.arquivo) + ' | existe: ' + str(existe))

print('')
print('=== RESUMO MIDIAS ===')
print('Total midias: ' + str(MidiaCondominio.objects.count()))
print('Fotos condominio ativas: ' + str(MidiaCondominio.objects.filter(categoria='condominio', ativo=True, tipo='foto').count()))
print('Videos condominio ativos: ' + str(MidiaCondominio.objects.filter(categoria='condominio', ativo=True, tipo='video').count()))
print('Fotos projetos futuros ativas: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', ativo=True, tipo='foto').count()))
print('Videos projetos futuros ativos: ' + str(MidiaCondominio.objects.filter(categoria='projetos_futuros', ativo=True, tipo='video').count()))
print('Midias INATIVAS (pendentes): ' + str(MidiaCondominio.objects.filter(ativo=False).count()))
for m in MidiaCondominio.objects.filter(ativo=False):
    print('  INATIVA: ' + str(m.id) + ' | ' + m.tipo + ' | ' + m.categoria + ' | ' + str(m.arquivo))

print('')
print('=== RESUMO GERAL ===')
print('Posts pendentes: ' + str(MuralPost.objects.filter(aprovado=False).count()))
print('Posts aprovados: ' + str(MuralPost.objects.filter(aprovado=True).count()))
print('Anuncios pendentes: ' + str(Anuncio.objects.filter(status='pendente').count()))
print('Anuncios aprovados: ' + str(Anuncio.objects.filter(status='aprovado').count()))
print('Usuarios pendentes: ' + str(Usuario.objects.filter(aprovado=False, is_active=True).count()))
print('Moradores aprovados: ' + str(Usuario.objects.filter(aprovado=True).count()))
"
