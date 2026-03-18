from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Anuncio, FotoAnuncio
from .forms import AnuncioForm


def lista_anuncios(request):
    anuncios = Anuncio.objects.filter(status="aprovado")

    tipo = request.GET.get("tipo")
    if tipo in ("venda", "aluguel"):
        anuncios = anuncios.filter(tipo=tipo)

    quartos = request.GET.get("quartos")
    if quartos:
        anuncios = anuncios.filter(quartos=quartos)

    busca = request.GET.get("busca")
    if busca:
        anuncios = anuncios.filter(
            Q(titulo__icontains=busca) | Q(descricao__icontains=busca)
        )

    ordem = request.GET.get("ordem", "-criado_em")
    if ordem in ("valor", "-valor", "-criado_em", "criado_em"):
        anuncios = anuncios.order_by(ordem)

    return render(request, "classificados/lista.html", {
        "anuncios": anuncios,
        "tipo_filtro": tipo,
        "busca": busca or "",
    })


def detalhe_anuncio(request, pk):
    anuncio = get_object_or_404(Anuncio, pk=pk, status="aprovado")
    anuncio.visualizacoes += 1
    anuncio.save(update_fields=["visualizacoes"])
    return render(request, "classificados/detalhe.html", {"anuncio": anuncio})


@login_required
def criar_anuncio(request):
    if request.method == "POST":
        form = AnuncioForm(request.POST)
        fotos = request.FILES.getlist("fotos")
        if form.is_valid():
            anuncio = form.save(commit=False)
            anuncio.autor = request.user
            anuncio.status = "pendente"
            anuncio.save()
            for i, foto in enumerate(fotos[:10]):
                FotoAnuncio.objects.create(
                    anuncio=anuncio,
                    imagem=foto,
                    principal=(i == 0),
                    ordem=i,
                )
            messages.success(request, "Anúncio enviado! Aguarde aprovação da administração.")
            return redirect("classificados:lista")
    else:
        form = AnuncioForm()
    return render(request, "classificados/criar.html", {"form": form})


@login_required
def meus_anuncios(request):
    anuncios = Anuncio.objects.filter(autor=request.user)
    return render(request, "classificados/meus_anuncios.html", {"anuncios": anuncios})
