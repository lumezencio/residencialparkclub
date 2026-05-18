from datetime import date, datetime, time as time_cls, timedelta

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from core.models import SuspensaoMorador, Usuario

from .forms import ReservaForm
from .models import BloqueioEspaco, Espaco, Reserva
from .permissions import (
    eh_moderador, moderador_required, residente_required,
)


# --------- VIEWS DO MORADOR ---------

@residente_required
def lista_espacos(request):
    espacos = Espaco.objects.filter(ativo=True).order_by("nome")
    return render(request, "reservas/espacos.html", {"espacos": espacos})


@residente_required
def calendario(request, slug):
    espaco = get_object_or_404(Espaco, slug=slug, ativo=True)

    # Data selecionada (GET ?data=YYYY-MM-DD), default = hoje
    data_str = request.GET.get("data")
    if data_str:
        try:
            data_sel = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data_sel = timezone.localdate()
    else:
        data_sel = timezone.localdate()

    hoje = timezone.localdate()
    max_dia = hoje + timedelta(days=espaco.antecedencia_max_dias)
    if data_sel < hoje:
        data_sel = hoje
    if data_sel > max_dia:
        data_sel = max_dia

    # Slots possiveis no dia
    slots = espaco.gerar_slots(data_sel)

    # Reservas existentes
    reservas_dia = {
        r.hora_inicio: r
        for r in Reserva.objects.filter(
            espaco=espaco, data=data_sel, status="confirmada"
        ).select_related("usuario")
    }

    # Bloqueios que tocam o dia
    inicio_dia = timezone.make_aware(datetime.combine(data_sel, time_cls(0, 0)))
    fim_dia = timezone.make_aware(datetime.combine(data_sel, time_cls(23, 59, 59)))
    bloqueios = list(BloqueioEspaco.objects.filter(
        espaco=espaco,
        data_inicio__lt=fim_dia,
        data_fim__gt=inicio_dia,
    ))

    def slot_bloqueado(h_ini, h_fim):
        s = timezone.make_aware(datetime.combine(data_sel, h_ini))
        e = timezone.make_aware(datetime.combine(data_sel, h_fim))
        for b in bloqueios:
            if b.data_inicio < e and b.data_fim > s:
                return b
        return None

    agora = timezone.now()
    antecedencia_min = timedelta(hours=espaco.antecedencia_min_horas)

    grade = []
    for h_ini, h_fim in slots:
        slot_dt = timezone.make_aware(datetime.combine(data_sel, h_ini))
        passou = slot_dt - antecedencia_min < agora
        reserva = reservas_dia.get(h_ini)
        bloqueio = slot_bloqueado(h_ini, h_fim)

        if bloqueio:
            estado = "bloqueado"
            label = bloqueio.motivo
        elif reserva:
            estado = "ocupado"
            label = f"{reserva.usuario.get_full_name() or reserva.usuario.username}"
            if reserva.usuario.bloco or reserva.usuario.apartamento:
                label += f" (Bl {reserva.usuario.bloco}/Apt {reserva.usuario.apartamento})"
        elif passou:
            estado = "vencido"
            label = "Horario indisponivel"
        else:
            estado = "livre"
            label = "Disponivel"

        grade.append({
            "hora_inicio": h_ini,
            "hora_fim": h_fim,
            "estado": estado,
            "label": label,
            "reserva": reserva,
            "bloqueio": bloqueio,
            "minha": reserva is not None and reserva.usuario_id == request.user.id,
        })

    # Lista de dias selecionaveis (proximos N dias)
    dias = [hoje + timedelta(days=i) for i in range(espaco.antecedencia_max_dias + 1)]

    minhas_futuras = Reserva.objects.filter(
        usuario=request.user, espaco=espaco, status="confirmada",
        data__gte=hoje,
    ).count()
    minhas_no_dia_sel = Reserva.objects.filter(
        usuario=request.user, espaco=espaco, status="confirmada",
        data=data_sel,
    ).count()
    bateu_limite_dia = minhas_no_dia_sel >= espaco.max_reservas_por_dia_por_usuario

    suspensao = getattr(request.user, "suspensao_ativa", None)

    return render(request, "reservas/calendario.html", {
        "espaco": espaco,
        "data_sel": data_sel,
        "dias": dias,
        "grade": grade,
        "minhas_futuras": minhas_futuras,
        "limite_futuras": espaco.max_reservas_futuras_por_usuario,
        "minhas_no_dia_sel": minhas_no_dia_sel,
        "limite_por_dia": espaco.max_reservas_por_dia_por_usuario,
        "bateu_limite_dia": bateu_limite_dia,
        "suspensao": suspensao,
    })


@residente_required
def criar_reserva(request, slug):
    espaco = get_object_or_404(Espaco, slug=slug, ativo=True)

    if request.method != "POST":
        return redirect("reservas:calendario", slug=slug)

    data_str = request.POST.get("data")
    hora_str = request.POST.get("hora_inicio")
    if not data_str or not hora_str:
        messages.error(request, "Dados invalidos.")
        return redirect("reservas:calendario", slug=slug)

    try:
        data = datetime.strptime(data_str, "%Y-%m-%d").date()
        h_ini = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        return HttpResponseBadRequest("Formato invalido")

    # Encontra o slot exato e valida
    slots = espaco.gerar_slots(data)
    par = next(((s, f) for s, f in slots if s == h_ini), None)
    if not par:
        messages.error(request, "Esse horario nao existe na grade.")
        return redirect("reservas:calendario", slug=slug)
    _, h_fim = par

    hoje = timezone.localdate()
    if data < hoje or data > hoje + timedelta(days=espaco.antecedencia_max_dias):
        messages.error(request, "Data fora do periodo permitido.")
        return redirect("reservas:calendario", slug=slug)

    inicio_dt = timezone.make_aware(datetime.combine(data, h_ini))
    if inicio_dt - timedelta(hours=espaco.antecedencia_min_horas) < timezone.now():
        messages.error(
            request,
            f"Reserva exige pelo menos {espaco.antecedencia_min_horas}h de antecedencia."
        )
        return redirect("reservas:calendario", slug=slug)

    # Limite de futuras por usuario
    minhas_futuras = Reserva.objects.filter(
        usuario=request.user, espaco=espaco, status="confirmada", data__gte=hoje,
    ).count()
    if minhas_futuras >= espaco.max_reservas_futuras_por_usuario:
        messages.error(
            request,
            f"Voce ja atingiu o limite de {espaco.max_reservas_futuras_por_usuario} reservas futuras."
        )
        return redirect("reservas:calendario", slug=slug)

    # Limite de reservas no MESMO dia (regra anti-monopolio)
    minhas_no_dia = Reserva.objects.filter(
        usuario=request.user, espaco=espaco, status="confirmada", data=data,
    ).count()
    if minhas_no_dia >= espaco.max_reservas_por_dia_por_usuario:
        limite = espaco.max_reservas_por_dia_por_usuario
        plural = "horario" if limite == 1 else "horarios"
        messages.error(
            request,
            f"Voce ja tem {minhas_no_dia} reserva(s) em {data:%d/%m}. "
            f"Cada morador pode reservar apenas {limite} {plural} por dia neste espaco."
        )
        return redirect("reservas:calendario", slug=slug)

    # Bloqueio?
    fim_dt = timezone.make_aware(datetime.combine(data, h_fim))
    if BloqueioEspaco.objects.filter(
        espaco=espaco, data_inicio__lt=fim_dt, data_fim__gt=inicio_dt
    ).exists():
        messages.error(request, "Horario indisponivel (bloqueio do moderador).")
        return redirect("reservas:calendario", slug=slug)

    # Bloqueia se usuario esta SUSPENSO
    susp = getattr(request.user, "suspensao_ativa", None)
    if susp:
        if susp.fim:
            messages.error(
                request,
                f"Voce esta suspenso ate {susp.fim:%d/%m/%Y %H:%M} e nao pode fazer "
                f"novas reservas. Motivo: {susp.motivo}"
            )
        else:
            messages.error(
                request,
                f"Voce esta suspenso por tempo indeterminado e nao pode fazer "
                f"novas reservas. Motivo: {susp.motivo}"
            )
        return redirect("reservas:calendario", slug=slug)

    convidados = request.POST.get("convidados", "").strip()
    observacao = request.POST.get("observacao", "").strip()

    reserva = Reserva(
        usuario=request.user,
        espaco=espaco,
        data=data,
        hora_inicio=h_ini,
        hora_fim=h_fim,
        convidados=convidados,
        observacao=observacao,
        status="confirmada",
    )

    try:
        with transaction.atomic():
            reserva.save()
    except IntegrityError:
        messages.error(request, "Esse horario acabou de ser reservado por outra pessoa.")
        return redirect("reservas:calendario", slug=slug)
    except Exception as e:
        messages.error(request, f"Nao foi possivel salvar: {e}")
        return redirect("reservas:calendario", slug=slug)

    messages.success(
        request,
        f"Reserva confirmada: {espaco.nome} em {data:%d/%m/%Y} as {h_ini:%H:%M}."
    )
    return redirect("reservas:minhas")


@residente_required
def minhas_reservas(request):
    hoje = timezone.localdate()
    futuras = Reserva.objects.filter(
        usuario=request.user, status="confirmada", data__gte=hoje,
    ).select_related("espaco").order_by("data", "hora_inicio")
    passadas = Reserva.objects.filter(
        usuario=request.user,
    ).exclude(data__gte=hoje).select_related("espaco").order_by("-data", "-hora_inicio")[:30]

    # Anota se pode cancelar (sem underscore - Django template bloqueia)
    futuras_list = list(futuras)
    for r in futuras_list:
        r.cancelavel = r.pode_cancelar(request.user)

    return render(request, "reservas/minhas.html", {
        "futuras": futuras_list,
        "passadas": passadas,
    })


@residente_required
def cancelar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk)
    if not reserva.pode_cancelar(request.user):
        messages.error(request, "Voce nao pode cancelar essa reserva.")
        return redirect("reservas:minhas")
    if request.method != "POST":
        return redirect("reservas:minhas")
    motivo = request.POST.get("motivo", "")
    reserva.status = "cancelada"
    reserva.cancelada_por = request.user
    reserva.cancelada_em = timezone.now()
    reserva.motivo_cancelamento = motivo[:200]
    reserva.save()
    messages.success(request, "Reserva cancelada.")
    if eh_moderador(request.user) and reserva.usuario_id != request.user.id:
        return redirect("reservas:painel")
    return redirect("reservas:minhas")


# --------- PAINEL DO MODERADOR ---------

@moderador_required
def painel_moderador(request):
    hoje = timezone.localdate()
    proximos_7 = hoje + timedelta(days=7)

    espacos = Espaco.objects.all().order_by("nome")
    filtro_espaco = request.GET.get("espaco")
    filtro_status = request.GET.get("status", "todos")

    qs = Reserva.objects.select_related("usuario", "espaco")
    if filtro_espaco:
        qs = qs.filter(espaco__slug=filtro_espaco)
    if filtro_status == "confirmadas":
        qs = qs.filter(status="confirmada")
    elif filtro_status == "canceladas":
        qs = qs.filter(status="cancelada")

    futuras = qs.filter(data__gte=hoje).order_by("data", "hora_inicio")
    canceladas_recentes = Reserva.objects.filter(
        status="cancelada", cancelada_em__isnull=False,
    ).select_related("usuario", "espaco", "cancelada_por").order_by("-cancelada_em")[:30]

    # Stats
    total_futuras = Reserva.objects.filter(status="confirmada", data__gte=hoje).count()
    total_hoje = Reserva.objects.filter(status="confirmada", data=hoje).count()
    total_canceladas_7 = Reserva.objects.filter(
        status="cancelada", cancelada_em__gte=timezone.now() - timedelta(days=7)
    ).count()

    bloqueios_ativos = BloqueioEspaco.objects.filter(
        data_fim__gte=timezone.now()
    ).select_related("espaco").order_by("data_inicio")

    # Suspensoes
    agora = timezone.now()
    suspensoes_ativas = SuspensaoMorador.objects.filter(
        ativa=True, inicio__lte=agora,
    ).filter(
        Q(fim__isnull=True) | Q(fim__gt=agora)
    ).select_related("usuario", "aplicada_por").order_by("-inicio")

    # Lista de moradores que podem ser suspensos (aprovados, nao empresa/fornecedor)
    moradores = Usuario.objects.filter(
        aprovado=True,
    ).exclude(tipo__in=["empresa", "fornecedor"]).order_by("bloco", "apartamento", "first_name")

    return render(request, "reservas/painel.html", {
        "espacos": espacos,
        "futuras": futuras,
        "canceladas_recentes": canceladas_recentes,
        "total_futuras": total_futuras,
        "total_hoje": total_hoje,
        "total_canceladas_7": total_canceladas_7,
        "bloqueios_ativos": bloqueios_ativos,
        "filtro_espaco": filtro_espaco,
        "filtro_status": filtro_status,
        "suspensoes_ativas": suspensoes_ativas,
        "moradores": moradores,
    })


@moderador_required
def criar_suspensao(request):
    if request.method != "POST":
        return redirect("reservas:painel")
    try:
        usuario = get_object_or_404(Usuario, pk=request.POST.get("usuario"))
        motivo = request.POST.get("motivo", "").strip()[:500]
        if not motivo:
            messages.error(request, "Motivo e obrigatorio.")
            return redirect("reservas:painel")
        fim_str = request.POST.get("fim", "").strip()
        fim = None
        if fim_str:
            try:
                fim = datetime.fromisoformat(fim_str)
                if timezone.is_naive(fim):
                    fim = timezone.make_aware(fim)
            except ValueError:
                messages.error(request, "Data de fim invalida.")
                return redirect("reservas:painel")
            if fim <= timezone.now():
                messages.error(request, "A data de fim deve estar no futuro.")
                return redirect("reservas:painel")

        # Verifica se ja tem suspensao ativa - desativa pra evitar duplicacao
        SuspensaoMorador.objects.filter(
            usuario=usuario, ativa=True,
        ).update(ativa=False, encerrada_em=timezone.now(), encerrada_por=request.user)

        susp = SuspensaoMorador.objects.create(
            usuario=usuario,
            inicio=timezone.now(),
            fim=fim,
            motivo=motivo,
            aplicada_por=request.user,
            ativa=True,
        )
        prazo = f"ate {fim:%d/%m/%Y %H:%M}" if fim else "por tempo indeterminado"
        messages.success(
            request,
            f"Morador {usuario.get_full_name() or usuario.username} suspenso {prazo}."
        )
    except Exception as e:
        messages.error(request, f"Nao foi possivel suspender: {e}")
    return redirect("reservas:painel")


@moderador_required
def remover_suspensao(request, pk):
    if request.method != "POST":
        return redirect("reservas:painel")
    susp = get_object_or_404(SuspensaoMorador, pk=pk)
    susp.ativa = False
    susp.encerrada_em = timezone.now()
    susp.encerrada_por = request.user
    susp.save()
    messages.success(
        request,
        f"Suspensao de {susp.usuario.get_full_name() or susp.usuario.username} removida."
    )
    return redirect("reservas:painel")


@moderador_required
def criar_bloqueio(request):
    if request.method != "POST":
        return redirect("reservas:painel")
    try:
        espaco = get_object_or_404(Espaco, pk=request.POST.get("espaco"))
        inicio = datetime.fromisoformat(request.POST.get("data_inicio"))
        fim = datetime.fromisoformat(request.POST.get("data_fim"))
        if timezone.is_naive(inicio):
            inicio = timezone.make_aware(inicio)
        if timezone.is_naive(fim):
            fim = timezone.make_aware(fim)
        motivo = request.POST.get("motivo", "")[:200]
        if inicio >= fim:
            messages.error(request, "Inicio deve ser antes do fim.")
            return redirect("reservas:painel")
        BloqueioEspaco.objects.create(
            espaco=espaco, data_inicio=inicio, data_fim=fim,
            motivo=motivo, criado_por=request.user,
        )
        messages.success(request, "Bloqueio criado.")
    except Exception as e:
        messages.error(request, f"Erro: {e}")
    return redirect("reservas:painel")


@moderador_required
def remover_bloqueio(request, pk):
    if request.method != "POST":
        return redirect("reservas:painel")
    b = get_object_or_404(BloqueioEspaco, pk=pk)
    b.delete()
    messages.success(request, "Bloqueio removido.")
    return redirect("reservas:painel")
