import logging
import random
import secrets
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from .models import (
    MidiaCondominio, Informacao, RegistroModeracao, Usuario, VisitaSite,
    Propaganda, SuspensaoMorador,
)
from datetime import datetime
from .forms import (
    CadastroForm, PerfilForm, UploadMidiaForm, CriarUsuarioForm,
    CadastroEmpresaForm, EditarMoradorForm, PropagandaForm,
)
from classificados.models import Anuncio
from comunicacao.models import MuralPost, MensagemAdministracao
from reservas.models import Espaco, LimiteReservaUsuario

logger = logging.getLogger(__name__)

# Alfabeto sem caracteres ambiguos (0/O, 1/l/I) - a senha e ditada/anotada no balcao.
ALFABETO_SENHA = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _gerar_senha(tamanho=12):
    """Senha aleatoria forte (secrets) com ao menos 1 minuscula, 1 maiuscula e 1 digito."""
    while True:
        senha = "".join(secrets.choice(ALFABETO_SENHA) for _ in range(tamanho))
        if (any(c.islower() for c in senha)
                and any(c.isupper() for c in senha)
                and any(c.isdigit() for c in senha)):
            return senha


# Upload de midias: so moderacao envia, e com teto de tamanho porque a VPS e
# compartilhada com outros sistemas em producao.
EXTENSOES_FOTO = ("jpg", "jpeg", "png", "webp", "avif")
EXTENSOES_VIDEO = ("mp4", "mov", "avi", "webm")
LIMITE_FOTO_MB = 15
LIMITE_VIDEO_MB = 200
MAX_ARQUIVOS_POR_ENVIO = 20


def _pode_moderar(user):
    # Portaria acompanha agendamentos e nada mais: nunca modera, mesmo que
    # alguem marque is_staff por engano no admin do Django.
    if user.tipo == "portaria":
        return False
    return user.is_staff or user.tipo in ("admin", "moderador")


def _e_privilegiado(user):
    return user.is_superuser or user.is_staff or user.tipo in ("admin", "moderador")


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

    # Anúncios aleatórios para a faixa de destaque
    anuncios_todos = list(Anuncio.objects.filter(status="aprovado"))
    random.shuffle(anuncios_todos)
    anuncios_random = anuncios_todos[:10]

    # Avisos: apenas posts de admin e moderador (nunca de moradores)
    todos_avisos = list(MuralPost.objects.filter(
        aprovado=True,
        autor__tipo__in=["admin", "moderador"]
    ).order_by("-fixado", "-criado_em")[:10])

    # Embaralhar para variar a cada visita
    random.shuffle(fotos)
    random.shuffle(videos)
    random.shuffle(fotos_futuro)
    random.shuffle(videos_futuro)

    # Hero slideshow: fotos E vídeos misturados (8 itens)
    hero_midias = fotos[:6] + videos[:2]
    random.shuffle(hero_midias)

    # Galeria: todas as mídias (recentes primeiro, depois aleatórias)
    todas_midias_ordered = list(MidiaCondominio.objects.filter(
        categoria="condominio", ativo=True
    ).order_by("-criado_em"))
    # 4 mais recentes ficam no topo, resto embaralha
    recentes = todas_midias_ordered[:4]
    restante = todas_midias_ordered[4:]
    random.shuffle(restante)
    todas_midias = recentes + restante

    # Projetos futuros: fotos e vídeos misturados
    midias_futuro = fotos_futuro + videos_futuro
    random.shuffle(midias_futuro)

    # Propagandas aprovadas para banners laterais (respeitando datas)
    hoje = timezone.now().date()
    propagandas_qs = Propaganda.objects.filter(status="aprovado", ativo=True)
    propagandas = []
    for p in propagandas_qs:
        if p.data_inicio and hoje < p.data_inicio:
            continue
        if p.data_fim and hoje > p.data_fim:
            continue
        propagandas.append(p)
    random.shuffle(propagandas)

    context = {
        "hero_midias": hero_midias,
        "todas_midias": todas_midias,
        "midias_futuro": midias_futuro,
        "destaques": destaques,
        "anuncios_random": anuncios_random,
        "avisos": todos_avisos,
        "informacoes": informacoes,
        "propagandas": propagandas,
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
                "Cadastro realizado com sucesso! Entre em contato com o Síndico ou Subsíndico pelo WhatsApp (035) 99809-0696 para aprovação da sua conta.",
            )
            return redirect("core:login")
    else:
        form = CadastroForm()
    return render(request, "core/cadastro.html", {"form": form})


@login_required
def perfil(request):
    if request.method == "POST":
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Dados atualizados com sucesso!")
            return redirect("core:perfil")
    else:
        form = PerfilForm(instance=request.user)
    return render(request, "core/perfil.html", {"form": form})


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
    """Galeria do condominio. Somente a moderacao envia novas midias."""
    fotos_cond = MidiaCondominio.objects.filter(categoria="condominio", ativo=True).order_by("-criado_em")
    fotos_futuro = MidiaCondominio.objects.filter(categoria="projetos_futuros", ativo=True).order_by("-criado_em")
    pode_enviar = _pode_moderar(request.user)

    if request.method == "POST":
        if not pode_enviar:
            return HttpResponseForbidden(
                "Somente administradores e moderadores podem enviar fotos e videos."
            )
        if request.user.bloqueado_para("galeria"):
            susp = request.user.suspensao_ativa
            prazo = f"ate {susp.fim:%d/%m/%Y}" if susp.fim else "por tempo indeterminado"
            messages.error(
                request,
                f"Voce esta suspenso de enviar fotos {prazo}. Motivo: {susp.motivo}"
            )
            return redirect("core:galeria")

        form = UploadMidiaForm(request.POST, request.FILES)
        arquivos = request.FILES.getlist("arquivos")
        if form.is_valid() and arquivos:
            categoria = form.cleaned_data["categoria"]
            titulo = form.cleaned_data["titulo"] or "Residencial Park Club"
            descricao = form.cleaned_data["descricao"] or ""

            enviados = 0
            recusados = []
            for arquivo in arquivos[:MAX_ARQUIVOS_POR_ENVIO]:
                ext = arquivo.name.rsplit(".", 1)[-1].lower() if "." in arquivo.name else ""
                if ext in EXTENSOES_FOTO:
                    tipo, limite_mb = "foto", LIMITE_FOTO_MB
                elif ext in EXTENSOES_VIDEO:
                    tipo, limite_mb = "video", LIMITE_VIDEO_MB
                else:
                    recusados.append(f"{arquivo.name} (formato nao aceito)")
                    continue

                if arquivo.size > limite_mb * 1024 * 1024:
                    recusados.append(f"{arquivo.name} (passa de {limite_mb} MB)")
                    continue

                MidiaCondominio.objects.create(
                    titulo=titulo,
                    tipo=tipo,
                    arquivo=arquivo,
                    descricao=descricao,
                    categoria=categoria,
                    # Enviado pela moderacao: ja entra no ar, na galeria e no
                    # sorteio do plano de fundo da home.
                    ativo=True,
                    destaque=False,
                )
                enviados += 1

            if enviados:
                onde = ("na galeria e no plano de fundo do site"
                        if categoria == "condominio" else "na secao de projetos futuros")
                logger.info(
                    "Midias enviadas: %s arquivo(s) categoria=%s por=%s",
                    enviados, categoria, request.user.username,
                )
                RegistroModeracao.registrar(
                    "midia_enviada", request.user, None,
                    f"{enviados} arquivo(s) em {dict(MidiaCondominio.CATEGORIA_CHOICES).get(categoria, categoria)}")
                messages.success(
                    request,
                    f"{enviados} arquivo(s) publicado(s) {onde}."
                )
            if recusados:
                messages.warning(
                    request,
                    "Nao enviados: " + "; ".join(recusados[:5])
                    + ("..." if len(recusados) > 5 else "")
                )
            if not enviados and not recusados:
                messages.error(request, "Nenhum arquivo valido foi selecionado.")
            return redirect("core:galeria")
    else:
        form = UploadMidiaForm()

    return render(request, "core/galeria.html", {
        "form": form,
        "fotos_cond": fotos_cond,
        "fotos_futuro": fotos_futuro,
        "pode_enviar": pode_enviar,
        "limite_foto_mb": LIMITE_FOTO_MB,
        "limite_video_mb": LIMITE_VIDEO_MB,
        "max_arquivos": MAX_ARQUIVOS_POR_ENVIO,
    })


@login_required
def moderacao(request):
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    anuncios_pendentes = Anuncio.objects.filter(status="pendente").order_by("-criado_em")
    anuncios_aprovados = Anuncio.objects.filter(status="aprovado").order_by("-criado_em")
    posts_pendentes = MuralPost.objects.filter(aprovado=False).order_by("-criado_em")
    avisos_ativos = MuralPost.objects.filter(aprovado=True).order_by("-fixado", "-criado_em")
    usuarios_pendentes = Usuario.objects.filter(aprovado=False, is_active=True).order_by("-data_cadastro")
    midias_pendentes = MidiaCondominio.objects.filter(ativo=False).order_by("-criado_em")
    mensagens_novas = MensagemAdministracao.objects.filter(status="nova").order_by("-criado_em")
    mensagens_total = MensagemAdministracao.objects.count()
    midias_ativas = MidiaCondominio.objects.filter(ativo=True).count()
    propagandas_pendentes = Propaganda.objects.filter(status="pendente").order_by("-criado_em")
    propagandas_ativas = Propaganda.objects.filter(status="aprovado").order_by("-criado_em")

    # Estatísticas de visitas
    hoje = timezone.now().date()
    visitas_hoje = VisitaSite.objects.filter(data=hoje).count()
    visitas_hoje_unicas = VisitaSite.objects.filter(data=hoje).values("ip").distinct().count()
    visitas_total = VisitaSite.objects.count()
    visitas_total_unicas = VisitaSite.objects.values("ip").distinct().count()

    # Páginas mais visitadas (top 5)
    paginas_populares = (
        VisitaSite.objects.values("pagina")
        .annotate(total=Count("id"))
        .order_by("-total")[:5]
    )

    # Lista de moderadores e moradores aprovados (só superadmin vê)
    moderadores = Usuario.objects.filter(tipo="moderador").select_related(
        "aprovado_por").order_by("first_name")
    moradores_aprovados = (
        Usuario.objects.filter(aprovado=True)
        .exclude(tipo="moderador").exclude(is_superuser=True)
        .select_related("aprovado_por")  # evita 1 consulta por card
        .order_by("first_name")
    )

    # Espacos reservaveis e limites individuais ja definidos (para o modal de limite)
    espacos_reserva = list(Espaco.objects.filter(ativo=True).order_by("nome"))
    limites_por_user = {}
    for lim in LimiteReservaUsuario.objects.select_related("espaco"):
        limites_por_user.setdefault(lim.usuario_id, []).append(lim)

    # Anota suspensao ativa em cada morador (1 query a mais; lista nao costuma ser gigante)
    agora_dt = timezone.now()
    suspensoes_por_user = {}
    for s in SuspensaoMorador.objects.filter(
        ativa=True, inicio__lte=agora_dt,
    ).filter(Q(fim__isnull=True) | Q(fim__gt=agora_dt)):
        suspensoes_por_user[s.usuario_id] = s
    for m in moradores_aprovados:
        m.suspensao = suspensoes_por_user.get(m.id)
        m.limites = limites_por_user.get(m.id, [])
        # So faz sentido ajustar cota de quem realmente reserva
        m.usa_reservas = m.tipo in ("morador", "proprietario")

    # Form de criar usuário (só superadmin)
    criar_usuario_form = CriarUsuarioForm() if request.user.is_superuser else None

    # Ultimas acoes da moderacao (o historico completo tem tela propria)
    registros_recentes = RegistroModeracao.objects.select_related(
        "moderador", "alvo_usuario")[:8]
    total_registros = RegistroModeracao.objects.count()

    # Senha recem-redefinida: exibida UMA unica vez e removida da sessao.
    senha_redefinida = request.session.pop("senha_redefinida", None)

    return render(request, "core/moderacao.html", {
        "anuncios_pendentes": anuncios_pendentes,
        "anuncios_aprovados": anuncios_aprovados,
        "posts_pendentes": posts_pendentes,
        "avisos_ativos": avisos_ativos,
        "usuarios_pendentes": usuarios_pendentes,
        "midias_pendentes": midias_pendentes,
        "mensagens_novas": mensagens_novas,
        "mensagens_total": mensagens_total,
        "midias_ativas": midias_ativas,
        "visitas_hoje": visitas_hoje,
        "visitas_hoje_unicas": visitas_hoje_unicas,
        "visitas_total": visitas_total,
        "visitas_total_unicas": visitas_total_unicas,
        "paginas_populares": paginas_populares,
        "moderadores": moderadores,
        "moradores_aprovados": moradores_aprovados,
        "criar_usuario_form": criar_usuario_form,
        "propagandas_pendentes": propagandas_pendentes,
        "propagandas_ativas": propagandas_ativas,
        "senha_redefinida": senha_redefinida,
        "espacos_reserva": espacos_reserva,
        "registros_recentes": registros_recentes,
        "total_registros": total_registros,
    })


@login_required
def criar_usuario(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Acesso restrito ao administrador.")

    if request.method == "POST":
        form = CriarUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            if form.cleaned_data["tipo"] in ("admin", "moderador"):
                user.is_staff = True
            # Criado ja liberado: quem criou e quem responde pela liberacao.
            user.registrar_aprovacao(request.user, salvar=False)
            user.save()
            RegistroModeracao.registrar(
                "cadastro_criado", request.user, user,
                f"Criado como {user.get_tipo_display()}")
            messages.success(request, f"Usuário '{user.username}' criado com sucesso como {user.get_tipo_display()}!")
            return redirect("core:moderacao")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect("core:moderacao")

    return redirect("core:moderacao")


@login_required
def moderar_item(request, tipo, pk):
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito.")

    acao = request.POST.get("acao", "")
    item = None

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
        elif acao == "deletar":
            titulo = item.titulo
            item.delete()
            messages.success(request, f"Anúncio '{titulo}' excluído.")

    elif tipo == "post":
        item = get_object_or_404(MuralPost, pk=pk)
        if acao == "aprovar":
            item.aprovado = True
            item.save()
            messages.success(request, f"Post '{item.titulo}' aprovado!")
        elif acao == "rejeitar":
            item.delete()
            messages.warning(request, "Post removido.")
        elif acao == "deletar":
            item.delete()
            messages.success(request, "Post/aviso excluído.")

    elif tipo == "usuario":
        item = get_object_or_404(Usuario, pk=pk)
        if acao == "aprovar":
            item.registrar_aprovacao(request.user)
            logger.info(
                "Cadastro liberado: morador=%s (id=%s) por=%s (id=%s)",
                item.username, item.pk, request.user.username, request.user.pk,
            )
            RegistroModeracao.registrar("cadastro_aprovado", request.user, item)
            messages.success(
                request,
                f"Morador {item.get_full_name() or item.username} aprovado por "
                f"{request.user.get_full_name() or request.user.username}."
            )
        elif acao == "rejeitar":
            item.is_active = False
            item.limpar_aprovacao(salvar=False)
            item.save(update_fields=["is_active", "aprovado", "aprovado_em", "aprovado_por"])
            logger.info(
                "Cadastro rejeitado: morador=%s (id=%s) por=%s",
                item.username, item.pk, request.user.username,
            )
            RegistroModeracao.registrar("cadastro_rejeitado", request.user, item)
            messages.warning(
                request,
                f"Morador {item.get_full_name() or item.username} rejeitado."
            )
        elif acao == "promover_moderador" and request.user.is_superuser:
            item.tipo = "moderador"
            item.is_staff = True
            item.save()
            RegistroModeracao.registrar("promovido_moderador", request.user, item)
            messages.success(request, f"{item.get_full_name()} agora é Moderador!")
        elif acao == "rebaixar_moderador" and request.user.is_superuser:
            item.tipo = "morador"
            item.is_staff = False
            item.save()
            RegistroModeracao.registrar("rebaixado_morador", request.user, item)
            messages.success(request, f"{item.get_full_name()} rebaixado para Morador.")

    elif tipo == "mensagem":
        item = get_object_or_404(MensagemAdministracao, pk=pk)
        if acao == "lida":
            item.status = "lida"
            item.save()
            messages.success(request, "Mensagem marcada como lida.")
        elif acao == "deletar":
            item.delete()
            messages.success(request, "Mensagem excluída.")

    elif tipo == "midia":
        item = get_object_or_404(MidiaCondominio, pk=pk)
        if acao == "aprovar":
            item.ativo = True
            item.save()
            messages.success(request, "Mídia aprovada!")
        elif acao == "rejeitar":
            item.delete()
            messages.warning(request, "Mídia removida.")

    elif tipo == "propaganda":
        item = get_object_or_404(Propaganda, pk=pk)
        if acao == "aprovar":
            item.status = "aprovado"
            item.save()
            messages.success(request, f"Propaganda '{item.titulo}' aprovada!")
        elif acao == "rejeitar":
            item.status = "rejeitado"
            item.save()
            messages.warning(request, f"Propaganda '{item.titulo}' rejeitada.")
        elif acao == "pausar":
            item.ativo = False
            item.save()
            messages.success(request, f"Propaganda '{item.titulo}' pausada.")
        elif acao == "ativar":
            item.ativo = True
            item.save()
            messages.success(request, f"Propaganda '{item.titulo}' ativada.")
        elif acao == "definir_datas" and request.user.is_superuser:
            data_inicio = request.POST.get("data_inicio", "").strip()
            data_fim = request.POST.get("data_fim", "").strip()
            from datetime import date as dt_date
            item.data_inicio = dt_date.fromisoformat(data_inicio) if data_inicio else None
            item.data_fim = dt_date.fromisoformat(data_fim) if data_fim else None
            item.save()
            msg_periodo = ""
            if item.data_inicio and item.data_fim:
                msg_periodo = f" de {item.data_inicio:%d/%m/%Y} até {item.data_fim:%d/%m/%Y}"
            elif item.data_inicio:
                msg_periodo = f" a partir de {item.data_inicio:%d/%m/%Y}"
            elif item.data_fim:
                msg_periodo = f" até {item.data_fim:%d/%m/%Y}"
            else:
                msg_periodo = " (sem limite de datas)"
            messages.success(request, f"Período de '{item.titulo}' definido{msg_periodo}.")
        elif acao == "deletar":
            item.delete()
            messages.success(request, "Propaganda excluída.")

    # Historico das acoes sobre conteudo (as de usuario ja sao gravadas acima)
    if item is not None and tipo != "usuario":
        mapa = {
            "aprovar": "conteudo_aprovado",
            "rejeitar": "conteudo_rejeitado",
            "deletar": "conteudo_excluido",
        }
        if acao in mapa:
            rotulos = {
                "anuncio": "Anuncio", "post": "Post do mural", "midia": "Midia",
                "mensagem": "Mensagem", "propaganda": "Propaganda",
            }
            titulo = (getattr(item, "titulo", "") or "").strip() or str(item)[:80]
            RegistroModeracao.registrar(
                mapa[acao], request.user, None,
                f"{rotulos.get(tipo, tipo)}: {titulo}")

    return redirect("core:moderacao")


@login_required
def suspender_morador(request, pk):
    """Aplica suspensao com modulos granulares escolhidos pelo moderador."""
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito.")
    if request.method != "POST":
        return redirect("core:moderacao")

    morador = get_object_or_404(Usuario, pk=pk)
    motivo = request.POST.get("motivo", "").strip()[:500]
    if not motivo:
        messages.error(request, "Motivo da suspensao e obrigatorio.")
        return redirect("core:moderacao")

    fim_str = request.POST.get("fim", "").strip()
    fim = None
    if fim_str:
        try:
            fim = datetime.fromisoformat(fim_str)
            if timezone.is_naive(fim):
                fim = timezone.make_aware(fim)
            if fim <= timezone.now():
                messages.error(request, "A data de fim deve ser no futuro.")
                return redirect("core:moderacao")
        except ValueError:
            messages.error(request, "Data de fim invalida.")
            return redirect("core:moderacao")

    # Modulos escolhidos (checkboxes do form)
    modulos_aceitos = ["reservas", "propagandas", "mural", "classificados", "galeria"]
    modulos_selecionados = [m for m in modulos_aceitos if request.POST.get(f"bloq_{m}")]
    if not modulos_selecionados:
        messages.error(request, "Selecione ao menos um modulo a bloquear.")
        return redirect("core:moderacao")

    # Encerra suspensoes anteriores
    SuspensaoMorador.objects.filter(usuario=morador, ativa=True).update(
        ativa=False, encerrada_em=timezone.now(), encerrada_por=request.user,
    )

    SuspensaoMorador.objects.create(
        usuario=morador,
        inicio=timezone.now(),
        fim=fim,
        motivo=motivo,
        aplicada_por=request.user,
        ativa=True,
        bloqueia_reservas="reservas" in modulos_selecionados,
        bloqueia_propagandas="propagandas" in modulos_selecionados,
        bloqueia_mural="mural" in modulos_selecionados,
        bloqueia_classificados="classificados" in modulos_selecionados,
        bloqueia_galeria="galeria" in modulos_selecionados,
    )
    prazo = f"ate {fim:%d/%m/%Y %H:%M}" if fim else "por tempo indeterminado"
    RegistroModeracao.registrar(
        "suspensao_aplicada", request.user, morador,
        f"{prazo}. Motivo: {motivo}")
    labels = {"reservas": "Reservas", "propagandas": "Propagandas",
              "mural": "Mural", "classificados": "Classificados", "galeria": "Galeria"}
    modulos_txt = ", ".join(labels[m] for m in modulos_selecionados)
    messages.success(
        request,
        f"Morador {morador.get_full_name() or morador.username} suspenso {prazo}. "
        f"Bloqueios: {modulos_txt}."
    )
    return redirect("core:moderacao")


@login_required
def remover_suspensao_morador(request, pk):
    """Remove a suspensao ativa de um morador (mantem historico)."""
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito.")
    if request.method != "POST":
        return redirect("core:moderacao")

    morador = get_object_or_404(Usuario, pk=pk)
    suspensoes = SuspensaoMorador.objects.filter(usuario=morador, ativa=True)
    n = suspensoes.update(ativa=False, encerrada_em=timezone.now(), encerrada_por=request.user)
    if n:
        RegistroModeracao.registrar("suspensao_removida", request.user, morador)
        messages.success(request, f"Suspensao de {morador.get_full_name() or morador.username} removida.")
    else:
        messages.warning(request, "Nenhuma suspensao ativa encontrada.")
    return redirect("core:moderacao")


@login_required
@require_POST
def redefinir_senha_usuario(request, pk):
    """Gera (ou define) uma nova senha para um usuario ja cadastrado.

    Regras de seguranca:
      - so moderador/admin/staff acessa;
      - moderador comum NAO redefine senha de outro moderador/admin/superuser
        (evita escalada de privilegio) - isso e exclusivo do superadmin;
      - ninguem redefine a propria senha por aqui (usar o perfil);
      - a senha em texto claro so aparece uma vez, no proximo carregamento do painel.
    """
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    alvo = get_object_or_404(Usuario, pk=pk)

    if alvo.pk == request.user.pk:
        messages.error(request, "Para alterar a sua propria senha, use a area de Perfil.")
        return redirect("core:moderacao")

    if _e_privilegiado(alvo) and not request.user.is_superuser:
        messages.error(
            request,
            "Somente o administrador pode redefinir a senha de outro moderador."
        )
        return redirect("core:moderacao")

    nova_senha = (request.POST.get("nova_senha") or "").strip()
    gerada = False
    if nova_senha:
        try:
            validate_password(nova_senha, alvo)
        except ValidationError as erro:
            for msg in erro.messages:
                messages.error(request, msg)
            return redirect("core:moderacao")
    else:
        nova_senha = _gerar_senha()
        gerada = True

    alvo.set_password(nova_senha)
    alvo.save(update_fields=["password"])

    # Trilha de auditoria nos logs do container (nunca registra a senha).
    logger.warning(
        "Senha redefinida: alvo=%s (id=%s) por=%s (id=%s) gerada=%s",
        alvo.username, alvo.pk, request.user.username, request.user.pk, gerada,
    )

    RegistroModeracao.registrar(
        "senha_redefinida", request.user, alvo,
        "Senha gerada pelo sistema" if gerada else "Senha definida manualmente")

    request.session["senha_redefinida"] = {
        "nome": alvo.get_full_name() or alvo.username,
        "usuario": alvo.username,
        "senha": nova_senha,
        "gerada": gerada,
    }
    return redirect("core:moderacao")


LIMITE_SEMANAL_MAX = 50


@login_required
@require_POST
def definir_limite_reservas(request, pk):
    """Ajusta (ou remove) a cota semanal de reservas de um morador.

    Sem excecao cadastrada vale o padrao do espaco. Com excecao, o numero aqui
    substitui o padrao para esse morador naquele espaco (0 = nao pode reservar).
    """
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    alvo = get_object_or_404(Usuario, pk=pk)
    if _e_privilegiado(alvo) and not request.user.is_superuser:
        messages.error(request, "Somente o administrador altera limites de um moderador.")
        return redirect("core:moderacao")

    espaco = get_object_or_404(Espaco, pk=request.POST.get("espaco"))
    nome_alvo = alvo.get_full_name() or alvo.username

    # Voltar ao padrao do espaco = apagar a excecao
    if request.POST.get("acao") == "padrao":
        apagados, _ = LimiteReservaUsuario.objects.filter(usuario=alvo, espaco=espaco).delete()
        if apagados:
            logger.warning(
                "Limite de reservas removido: alvo=%s (id=%s) espaco=%s por=%s",
                alvo.username, alvo.pk, espaco.slug, request.user.username,
            )
            RegistroModeracao.registrar(
                "limite_removido", request.user, alvo, f"Espaco {espaco.nome}")
            messages.success(
                request,
                f"{nome_alvo} voltou ao limite padrao de {espaco.nome}: "
                f"{espaco.max_reservas_por_semana_por_usuario} por semana."
            )
        else:
            messages.info(request, f"{nome_alvo} ja usava o limite padrao de {espaco.nome}.")
        return redirect("core:moderacao")

    try:
        maximo = int(request.POST.get("max_por_semana", ""))
    except (TypeError, ValueError):
        messages.error(request, "Informe um numero valido de reservas por semana.")
        return redirect("core:moderacao")

    if maximo < 0 or maximo > LIMITE_SEMANAL_MAX:
        messages.error(
            request,
            f"O limite semanal deve ficar entre 0 e {LIMITE_SEMANAL_MAX}."
        )
        return redirect("core:moderacao")

    motivo = (request.POST.get("motivo") or "").strip()[:200]
    LimiteReservaUsuario.objects.update_or_create(
        usuario=alvo, espaco=espaco,
        defaults={
            "max_por_semana": maximo,
            "motivo": motivo,
            "definido_por": request.user,
        },
    )
    logger.warning(
        "Limite de reservas definido: alvo=%s (id=%s) espaco=%s valor=%s por=%s",
        alvo.username, alvo.pk, espaco.slug, maximo, request.user.username,
    )
    RegistroModeracao.registrar(
        "limite_definido", request.user, alvo,
        f"{espaco.nome}: {maximo} por semana" + (f". Motivo: {motivo}" if motivo else ""))
    if maximo == 0:
        messages.success(
            request,
            f"{nome_alvo} esta impedido de reservar {espaco.nome} (limite 0 por semana)."
        )
    else:
        plural = "reserva" if maximo == 1 else "reservas"
        messages.success(
            request,
            f"{nome_alvo} agora pode fazer {maximo} {plural} por semana em {espaco.nome}."
        )
    return redirect("core:moderacao")


@login_required
def editar_morador(request, pk):
    """Abre o cadastro de um morador para a moderacao corrigir dados."""
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    morador = get_object_or_404(
        Usuario.objects.select_related("aprovado_por"), pk=pk)

    # Mesma regra das outras acoes: moderador comum nao mexe em moderador/admin
    if _e_privilegiado(morador) and not request.user.is_superuser:
        messages.error(
            request, "Somente o administrador altera o cadastro de outro moderador.")
        return redirect("core:moderacao")

    if request.method == "POST":
        form = EditarMoradorForm(request.POST, request.FILES, instance=morador)
        if form.is_valid():
            rotulos = {
                "first_name": "nome", "last_name": "sobrenome", "email": "e-mail",
                "cpf": "CPF", "telefone": "telefone", "bloco": "bloco",
                "apartamento": "apartamento", "foto_perfil": "foto",
            }
            alterados = [rotulos.get(c, c) for c in form.changed_data]
            form.save()
            if alterados:
                RegistroModeracao.registrar(
                    "cadastro_editado", request.user, morador,
                    "Alterou: " + ", ".join(alterados))
                logger.info(
                    "Cadastro alterado: morador=%s (id=%s) campos=%s por=%s",
                    morador.username, morador.pk, ",".join(form.changed_data),
                    request.user.username,
                )
                messages.success(
                    request,
                    f"Cadastro de {morador.get_full_name() or morador.username} "
                    f"atualizado ({', '.join(alterados)})."
                )
            else:
                messages.info(request, "Nada foi alterado.")
            return redirect("core:editar_morador", pk=morador.pk)
        messages.error(request, "Confira os campos destacados.")
    else:
        form = EditarMoradorForm(instance=morador)

    historico = (
        RegistroModeracao.objects.filter(alvo_usuario=morador)
        .select_related("moderador").order_by("-criado_em")[:50]
    )

    return render(request, "core/editar_morador.html", {
        "morador": morador,
        "form": form,
        "historico": historico,
        "suspensao": morador.suspensao_ativa,
    })


MORADORES_POR_PAGINA = 25

ORDENS_MORADORES = {
    "nome": ("first_name", "last_name"),
    "unidade": ("bloco", "apartamento", "first_name"),
    "recentes": ("-data_cadastro",),
    "antigos": ("data_cadastro",),
}


def _situacao_usuario(u, suspensos_ids):
    """Situacao mostrada no painel.

    Conta de staff/superadmin nunca passa pela fila de aprovacao, entao conta
    como liberada mesmo que a marca `aprovado` esteja desligada.
    """
    if not u.is_active:
        return "inativo"
    if u.pk in suspensos_ids:
        return "suspenso"
    if u.aprovado or u.is_staff or u.is_superuser:
        return "aprovado"
    return "fila"


@login_required
def painel_moradores(request):
    """Diretorio completo dos cadastros: buscar, filtrar, abrir e exportar."""
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    busca = (request.GET.get("q") or "").strip()
    filtro_tipo = request.GET.get("tipo") or ""
    filtro_situacao = request.GET.get("situacao") or ""
    ordem = request.GET.get("ordem") if request.GET.get("ordem") in ORDENS_MORADORES else "nome"

    qs = Usuario.objects.select_related("aprovado_por")

    if busca:
        qs = qs.filter(
            Q(first_name__icontains=busca) | Q(last_name__icontains=busca)
            | Q(username__icontains=busca) | Q(cpf__icontains=busca)
            | Q(email__icontains=busca) | Q(telefone__icontains=busca)
            | Q(bloco__icontains=busca) | Q(apartamento__icontains=busca)
        )
    if filtro_tipo:
        qs = qs.filter(tipo=filtro_tipo)

    # Quem esta com suspensao em vigor agora
    agora = timezone.now()
    suspensos_ids = set(
        SuspensaoMorador.objects.filter(ativa=True, inicio__lte=agora)
        .filter(Q(fim__isnull=True) | Q(fim__gt=agora))
        .values_list("usuario_id", flat=True)
    )

    if filtro_situacao == "aprovados":
        qs = qs.filter(is_active=True).filter(
            Q(aprovado=True) | Q(is_staff=True) | Q(is_superuser=True))
    elif filtro_situacao == "fila":
        qs = qs.filter(aprovado=False, is_active=True,
                       is_staff=False, is_superuser=False)
    elif filtro_situacao == "inativos":
        qs = qs.filter(is_active=False)
    elif filtro_situacao == "suspensos":
        qs = qs.filter(pk__in=suspensos_ids)

    qs = qs.order_by(*ORDENS_MORADORES[ordem])

    # Exportacao da lista filtrada
    if request.GET.get("export") == "csv":
        return _exportar_moradores_csv(qs, suspensos_ids, request.user)

    total_filtrado = qs.count()
    paginador = Paginator(qs, MORADORES_POR_PAGINA)
    pagina = paginador.get_page(request.GET.get("pagina"))
    for m in pagina:
        m.situacao = _situacao_usuario(m, suspensos_ids)

    # Numeros gerais (nao seguem o filtro: sao o retrato do condominio)
    todos = Usuario.objects.all()
    resumo = {
        "total": todos.count(),
        "aprovados": todos.filter(is_active=True).filter(
            Q(aprovado=True) | Q(is_staff=True) | Q(is_superuser=True)).count(),
        "fila": todos.filter(aprovado=False, is_active=True,
                             is_staff=False, is_superuser=False).count(),
        "suspensos": len(suspensos_ids),
        "inativos": todos.filter(is_active=False).count(),
    }

    # Mantem os filtros ao trocar de pagina
    parametros = request.GET.copy()
    parametros.pop("pagina", None)
    querystring = parametros.urlencode()

    return render(request, "core/painel_moradores.html", {
        "pagina": pagina,
        "total_filtrado": total_filtrado,
        "resumo": resumo,
        "busca": busca,
        "filtro_tipo": filtro_tipo,
        "filtro_situacao": filtro_situacao,
        "ordem": ordem,
        "tipos": Usuario.TIPO_CHOICES,
        "querystring": querystring,
    })


def _exportar_moradores_csv(qs, suspensos_ids, solicitante):
    """CSV da lista filtrada, para conferencia fora do sistema."""
    import csv

    resposta = HttpResponse(content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = (
        f'attachment; filename="moradores_{timezone.localdate():%Y-%m-%d}.csv"')
    resposta.write("﻿")  # BOM para o Excel em pt-BR
    escritor = csv.writer(resposta, delimiter=";")
    escritor.writerow([
        "Nome", "Usuario", "Tipo", "Bloco", "Apartamento", "Telefone", "E-mail",
        "CPF/CNPJ", "Situacao", "Liberado por", "Liberado em", "Cadastro em",
    ])
    rotulos = {"inativo": "Inativo", "suspenso": "Suspenso",
               "aprovado": "Aprovado", "fila": "Na fila"}
    for u in qs:
        situacao = rotulos[_situacao_usuario(u, suspensos_ids)]
        escritor.writerow([
            u.get_full_name() or u.username, u.username, u.get_tipo_display(),
            u.bloco or "", u.apartamento or "", u.telefone or "", u.email or "",
            u.cpf or "", situacao, u.aprovado_por_nome,
            u.aprovado_em.strftime("%d/%m/%Y %H:%M") if u.aprovado_em else "",
            u.data_cadastro.strftime("%d/%m/%Y"),
        ])
    RegistroModeracao.registrar(
        "lista_exportada", solicitante, None,
        f"Exportou {qs.count()} cadastro(s) em CSV")
    return resposta


@login_required
def historico_moderacao(request):
    """Historico geral: tudo que a moderacao fez, com filtros."""
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito a administradores e moderadores.")

    registros = RegistroModeracao.objects.select_related(
        "moderador", "alvo_usuario")

    filtro_moderador = request.GET.get("moderador") or ""
    filtro_acao = request.GET.get("acao") or ""
    busca = (request.GET.get("q") or "").strip()

    if filtro_moderador.isdigit():
        registros = registros.filter(moderador_id=int(filtro_moderador))
    if filtro_acao:
        registros = registros.filter(acao=filtro_acao)
    if busca:
        registros = registros.filter(
            Q(alvo_nome__icontains=busca)
            | Q(moderador_nome__icontains=busca)
            | Q(descricao__icontains=busca)
        )

    total = registros.count()
    registros = list(registros[:300])

    moderadores = Usuario.objects.filter(
        acoes_moderacao__isnull=False).distinct().order_by("first_name")

    return render(request, "core/historico_moderacao.html", {
        "registros": registros,
        "total": total,
        "moderadores": moderadores,
        "acoes": RegistroModeracao.ACAO_CHOICES,
        "filtro_moderador": filtro_moderador,
        "filtro_acao": filtro_acao,
        "busca": busca,
    })


@login_required
def excluir_midia(request, pk):
    if not _pode_moderar(request.user):
        return HttpResponseForbidden("Acesso restrito.")

    midia = get_object_or_404(MidiaCondominio, pk=pk)
    if request.method == "POST":
        rotulo = midia.titulo or f"{midia.get_tipo_display()} #{midia.pk}"
        midia.delete()
        RegistroModeracao.registrar("midia_excluida", request.user, None, rotulo)
        messages.success(request, "Mídia excluída com sucesso.")
    return redirect("core:galeria")


def cadastro_empresa(request):
    """Cadastro para empresas e fornecedores."""
    if request.method == "POST":
        form = CadastroEmpresaForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.aprovado = False
            user.save()
            messages.success(
                request,
                "Cadastro realizado com sucesso! Aguarde a aprovação da administração para publicar suas propagandas.",
            )
            return redirect("core:login")
    else:
        form = CadastroEmpresaForm()
    return render(request, "core/cadastro_empresa.html", {"form": form})


@login_required
def minhas_propagandas(request):
    """Área do anunciante para gerenciar suas propagandas."""
    if request.user.tipo not in ("empresa", "fornecedor"):
        return HttpResponseForbidden("Acesso restrito a empresas e fornecedores.")

    propagandas = Propaganda.objects.filter(anunciante=request.user).order_by("-criado_em")
    return render(request, "core/minhas_propagandas.html", {"propagandas": propagandas})


@login_required
def criar_propaganda(request):
    """Criar nova propaganda."""
    if request.user.tipo not in ("empresa", "fornecedor"):
        return HttpResponseForbidden("Acesso restrito a empresas e fornecedores.")

    if request.user.bloqueado_para("propagandas"):
        susp = request.user.suspensao_ativa
        prazo = f"ate {susp.fim:%d/%m/%Y}" if susp.fim else "por tempo indeterminado"
        messages.error(
            request,
            f"Voce esta suspenso de criar propagandas {prazo}. Motivo: {susp.motivo}"
        )
        return redirect("core:minhas_propagandas")

    if request.method == "POST":
        form = PropagandaForm(request.POST, request.FILES)
        if form.is_valid():
            propaganda = form.save(commit=False)
            propaganda.anunciante = request.user
            propaganda.status = "pendente"
            propaganda.save()
            messages.success(request, "Propaganda enviada com sucesso! Aguarde aprovação da administração.")
            return redirect("core:minhas_propagandas")
    else:
        form = PropagandaForm()
    return render(request, "core/criar_propaganda.html", {"form": form})


@login_required
def editar_propaganda(request, pk):
    """Editar propaganda existente."""
    propaganda = get_object_or_404(Propaganda, pk=pk, anunciante=request.user)

    if request.method == "POST":
        form = PropagandaForm(request.POST, request.FILES, instance=propaganda)
        if form.is_valid():
            propaganda = form.save(commit=False)
            propaganda.status = "pendente"
            propaganda.save()
            messages.success(request, "Propaganda atualizada! Aguarde nova aprovação.")
            return redirect("core:minhas_propagandas")
    else:
        form = PropagandaForm(instance=propaganda)
    return render(request, "core/criar_propaganda.html", {"form": form, "editando": True})


@login_required
def pausar_propaganda(request, pk):
    """Pausar ou reativar propaganda."""
    propaganda = get_object_or_404(Propaganda, pk=pk, anunciante=request.user)
    if request.method == "POST":
        propaganda.ativo = not propaganda.ativo
        propaganda.save()
        estado = "ativada" if propaganda.ativo else "pausada"
        messages.success(request, f"Propaganda '{propaganda.titulo}' {estado}.")
    return redirect("core:minhas_propagandas")


@login_required
def excluir_propaganda(request, pk):
    """Excluir propaganda."""
    propaganda = get_object_or_404(Propaganda, pk=pk, anunciante=request.user)
    if request.method == "POST":
        propaganda.delete()
        messages.success(request, "Propaganda excluída com sucesso.")
    return redirect("core:minhas_propagandas")
