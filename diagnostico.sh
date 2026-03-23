#!/bin/bash
docker exec parkclub_web python manage.py shell -c "
from core.models import Usuario
from comunicacao.models import MuralPost
from classificados.models import Anuncio
for nome in ['Marina', 'Mateus', 'Crislaine']:
    users = Usuario.objects.filter(first_name__icontains=nome)
    for u in users:
        print('=== ' + u.get_full_name() + ' ===')
        print('  tipo: ' + u.tipo + ' | aprovado: ' + str(u.aprovado) + ' | ativo: ' + str(u.is_active))
        posts = MuralPost.objects.filter(autor=u)
        print('  Posts: ' + str(posts.count()))
        for p in posts:
            print('    - ' + p.titulo + ' | aprovado: ' + str(p.aprovado))
        anuncios = Anuncio.objects.filter(autor=u)
        print('  Anuncios: ' + str(anuncios.count()))
        for a in anuncios:
            print('    - ' + a.titulo + ' | status: ' + a.status)
print('=== RESUMO ===')
print('Posts pendentes: ' + str(MuralPost.objects.filter(aprovado=False).count()))
print('Posts aprovados: ' + str(MuralPost.objects.filter(aprovado=True).count()))
print('Anuncios pendentes: ' + str(Anuncio.objects.filter(status='pendente').count()))
print('Anuncios aprovados: ' + str(Anuncio.objects.filter(status='aprovado').count()))
print('Usuarios pendentes: ' + str(Usuario.objects.filter(aprovado=False, is_active=True).count()))
print('Moradores aprovados: ' + str(Usuario.objects.filter(aprovado=True).count()))
"
