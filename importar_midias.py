"""
Script para importar mídias da pasta 'midias e fotos' para o banco de dados.
Execute: python manage.py shell < importar_midias.py
"""
import os
import shutil
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "parkclub.settings")

import django
django.setup()

from core.models import MidiaCondominio

MEDIA_SOURCE = Path(r"C:\Projetos\residencialparkclub\midias e fotos")
MEDIA_DEST = Path(r"C:\Projetos\residencialparkclub\media\condominio")

MEDIA_DEST.mkdir(parents=True, exist_ok=True)

count_fotos = 0
count_videos = 0

for arquivo in sorted(MEDIA_SOURCE.iterdir()):
    if not arquivo.is_file():
        continue

    ext = arquivo.suffix.lower()
    nome = arquivo.name

    # Verificar se já existe
    if MidiaCondominio.objects.filter(arquivo=f"condominio/{nome}").exists():
        print(f"  Já existe: {nome}")
        continue

    # Copiar arquivo para media/condominio/
    destino = MEDIA_DEST / nome
    if not destino.exists():
        shutil.copy2(str(arquivo), str(destino))

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        tipo = "foto"
        count_fotos += 1
    elif ext in (".mp4", ".avi", ".mov", ".webm"):
        tipo = "video"
        count_videos += 1
    else:
        continue

    MidiaCondominio.objects.create(
        titulo=f"Residencial Park Club",
        tipo=tipo,
        arquivo=f"condominio/{nome}",
        descricao="Foto do condomínio" if tipo == "foto" else "Vídeo do condomínio",
        ativo=True,
        destaque=(count_fotos <= 3 or count_videos <= 1),
        ordem=count_fotos if tipo == "foto" else count_videos,
    )
    print(f"  Importado: {nome} ({tipo})")

print(f"\nImportação concluída!")
print(f"  Fotos: {count_fotos}")
print(f"  Vídeos: {count_videos}")
print(f"  Total: {count_fotos + count_videos}")
