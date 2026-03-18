import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import MidiaCondominio, Informacao, Usuario
from .forms import CadastroForm, UploadMidiaForm
from classificados.models import Anuncio
from comunicacao.models import MuralPost, MensagemAdministracao


def home(request):
    # Mídias do condomínio (atuais)
    fotos = list(MidiaCondominio.objects.filter(tipo="foto", categoria="condominio", ativo=True))
    videos = list(MidiaCondominio.objects.filter(tipo="video", categoria="condominio", ativo=True))

    # Mídias de projetos futuros (separadas)
    fotos_futuro = list(MidiaCondominio.objects.filter(tipo="foto", categoria="projetos_futuros", ativo=True))
    videos_futuro = list(MidiaCondominio.objects.filter(tipo="video", categoria="projetos_futuros", ativo=True))

    # Classificados e infos
    destaques = Anuncio.objects.filter(status="aprovado").order_by("-destaque", "-criado_em")[:6]
    informacoes = Informacao.objects.filter(ativo=True)

    # Embaralhar para variar a cada visita
    random.shuffle(fotos)
    random.shuffle(videos)
    random.shuffle(fotos_futuro)
    random.shuffle(videos_futuro)

    # Fotos para o hero slideshow (8 fotos com transição lenta)
    hero_fotos = fotos[:8]

    # Galeria: todas as mídias misturadas (fotos + vídeos)
    todas_midias = fotos + videos
    random.shuffle(todas_midias)

    context = {
        "hero_fotos": hero_fotos,
        "todas_midias": todas_midias,
        "fotos_futuro": fotos_futuro,
        "videos_futuro": videos_futuro,
        "destaques": destaques,
        "informacoes": informacoes,
    }
    return render(request, "core/home.html", context)


def cadastro(request):
    if request.method == "POST":
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.aprovado = False
            user.save()
            messages.success(
                request,
                "Cadastro realizado com sucesso! Aguarde a aprovação da administração.",
            )
            return redirect("core:login")
    else:
        form = CadastroForm()
    return render(request, "core/cadastro.html", {"form": form})


@login_required
def perfil(request):
    return render(request, "core/perfil.html")


def sobre(request):
    informacoes = Informacao.objects.filter(ativo=True)
    fotos = list(MidiaCondominio.objects.filter(tipo="foto", categoria="condominio", ativo=True))
    fotos_futuro = list(MidiaCondominio.objects.filter(tipo="foto", categoria="projetos_futuros", ativo=True))
    random.shuffle(fotos)
    return render(request, "core/sobre.html", {
        "informacoes": informacoes,
        "fotos": fotos[:20],
        "fotos_futuro": fotos_futuro,
    })


@login_required
def galeria(request):
    """Página de galeria completa com upload para moradores e admins."""
    fotos_cond = MidiaCondominio.objects.filter(categoria="condominio", ativo=True).order_by("-criado_em")
    fotos_futuro = MidiaCondominio.objects.filter(categoria="projetos_futuros", ativo=True).order_by("-criado_em")

    if request.method == "POST":
        form = UploadMidiaForm(request.POST, request.FILES)
        arquivos = request.FILES.getlist("arquivos")
        if form.is_valid() and arquivos:
            categoria = form.cleaned_data["categoria"]
            titulo = form.cleaned_data["titulo"] or "Residencial Park Club"
            descricao = form.cleaned_data["descricao"] or ""

            # Admins: fotos ficam ativas imediatamente
            # Moradores: fotos ficam inativas até aprovação
            ativo = request.user.is_staff

            count = 0
            for arquivo in arquivos[:20]:  # máximo 20 por vez
                ext = arquivo.name.rsplit(".", 1)[-1].lower() if "." in arquivo.name else ""
                if ext in ("jpg", "jpeg", "png", "webp", "avif"):
                    tipo = "foto"
                elif ext in ("mp4", "mov", "avi", "webm"):
                    tipo = "video"
                else:
                    continue

                MidiaCondominio.objects.create(
                    titulo=titulo,
                    tipo=tipo,
                    arquivo=arquivo,
                    descricao=descricao,
                    categoria=categoria,
                    ativo=ativo,
                    destaque=False,
                )
                count += 1

            if request.user.is_staff:
                messages.success(request, f"{count} arquivo(s) enviado(s) com sucesso!")
            else:
                messages.success(request, f"{count} arquivo(s) enviado(s)! Aguarde aprovação da administração.")
            return redirect("core:galeria")
    else:
        form = UploadMidiaForm()

    return render(request, "core/galeria.html", {
        "form": form,
        "fotos_cond": fotos_cond,
        "fotos_futuro": fotos_futuro,
    })


@login_required
def moderacao(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Acesso restrito a administradores.")

    anuncios_pendentes = Anuncio.objects.filter(status="pendente").order_by("-criado_em")
    posts_pendentes = MuralPost.objects.filter(aprovado=False).order_by("-criado_em")
    usuarios_pendentes = Usuario.objects.filter(aprovado=False, is_active=True).order_by("-data_cadastro")
    midias_pendentes = MidiaCondominio.objects.filter(ativo=False).order_by("-criado_em")
    mensagens_novas = MensagemAdministracao.objects.filter(status="nova").order_by("-criado_em")

    return render(request, "core/moderacao.html", {
        "anuncios_pendentes": anuncios_pendentes,
        "posts_pendentes": posts_pendentes,
        "usuarios_pendentes": usuarios_pendentes,
        "midias_pendentes": midias_pendentes,
        "mensagens_novas": mensagens_novas,
    })


@login_required
def moderar_item(request, tipo, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Acesso restrito.")

    acao = request.POST.get("acao", "")

    if tipo == "anuncio":
        item = get_object_or_404(Anuncio, pk=pk)
        if acao == "aprovar":
            item.status = "aprovado"
            item.save()
            messages.success(request, f"Anúncio '{item.titulo}' aprovado!")
        elif acao == "rejeitar":
            item.status = "rejeitado"
            item.save()
            messages.warning(request, f"Anúncio '{item.titulo}' rejeitado.")

    elif tipo == "post":
        item = get_object_or_404(MuralPost, pk=pk)
        if acao == "aprovar":
            item.aprovado = True
            item.save()
            messages.success(request, f"Post '{item.titulo}' aprovado!")
        elif acao == "rejeitar":
            item.delete()
            messages.warning(request, "Post removido.")

    elif tipo == "usuario":
        item = get_object_or_404(Usuario, pk=pk)
        if acao == "aprovar":
            item.aprovado = True
            item.save()
            messages.success(request, f"Morador {item.get_full_name()} aprovado!")
        elif acao == "rejeitar":
            item.is_active = False
            item.save()
            messages.warning(request, f"Morador {item.get_full_name()} rejeitado.")

    elif tipo == "midia":
        item = get_object_or_404(MidiaCondominio, pk=pk)
        if acao == "aprovar":
            item.ativo = True
            item.save()
            messages.success(request, "Mídia aprovada!")
        elif acao == "rejeitar":
            item.delete()
            messages.warning(request, "Mídia removida.")

    return redirect("core:moderacao")
