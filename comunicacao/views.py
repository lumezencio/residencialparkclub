from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import MuralPost, MensagemAdministracao
from .forms import MuralPostForm, ComentarioForm, MensagemAdmForm


@login_required
def mural(request):
    posts = MuralPost.objects.filter(aprovado=True)
    categoria = request.GET.get("categoria")
    if categoria:
        posts = posts.filter(categoria=categoria)

    if request.method == "POST":
        form = MuralPostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user

            # Avisos e eventos: só superuser pode criar
            if post.categoria in ("aviso", "evento") and not request.user.is_superuser:
                messages.error(request, "Apenas administradores podem publicar avisos e eventos.")
                return redirect("comunicacao:mural")

            # Superuser: aprovação automática
            if request.user.is_superuser:
                post.aprovado = True
                post.save()
                messages.success(request, "Publicação aprovada automaticamente!")
            else:
                post.aprovado = False
                post.save()
                messages.success(request, "Publicação enviada! Aguarde aprovação do moderador.")
            return redirect("comunicacao:mural")
    else:
        form = MuralPostForm(user=request.user)

    return render(request, "comunicacao/mural.html", {
        "posts": posts,
        "form": form,
        "categoria_filtro": categoria,
    })


@login_required
def detalhe_post(request, pk):
    post = get_object_or_404(MuralPost, pk=pk, aprovado=True)
    if request.method == "POST":
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.post = post
            comentario.autor = request.user
            comentario.save()
            messages.success(request, "Comentário adicionado!")
            return redirect("comunicacao:detalhe_post", pk=pk)
    else:
        form = ComentarioForm()

    return render(request, "comunicacao/detalhe_post.html", {
        "post": post,
        "form": form,
    })


@login_required
def mensagem_administracao(request):
    if request.method == "POST":
        form = MensagemAdmForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.remetente = request.user
            msg.save()
            messages.success(request, "Mensagem enviada à administração!")
            return redirect("comunicacao:mensagem_adm")
    else:
        form = MensagemAdmForm()

    minhas_mensagens = MensagemAdministracao.objects.filter(remetente=request.user)
    return render(request, "comunicacao/mensagem_adm.html", {
        "form": form,
        "mensagens": minhas_mensagens,
    })
