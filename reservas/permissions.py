"""Helpers de permissao para o app reservas.

Acesso ao app: apenas usuarios LOGADOS, com aprovado=True, e do tipo
morador/proprietario/moderador/admin. Empresas e fornecedores NAO acessam.
Visitantes anonimos NAO veem nada (nem o link no menu).
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


TIPOS_PERMITIDOS = ("morador", "proprietario", "moderador", "admin")
TIPOS_MODERADOR = ("moderador", "admin")


def eh_portaria(user):
    """Usuario de portaria: acompanha agendamentos, nao modera e nao reserva."""
    if not user.is_authenticated:
        return False
    return getattr(user, "tipo", "") == "portaria"


def pode_reservar(user):
    if not user.is_authenticated:
        return False
    if eh_portaria(user):
        return False
    if not getattr(user, "aprovado", False):
        return False
    return getattr(user, "tipo", "") in TIPOS_PERMITIDOS


def eh_moderador(user):
    if not user.is_authenticated:
        return False
    # Trava de seguranca: portaria NUNCA e moderador, mesmo que alguem marque
    # is_staff por engano no admin do Django.
    if eh_portaria(user):
        return False
    if user.is_staff or user.is_superuser:
        return True
    return getattr(user, "tipo", "") in TIPOS_MODERADOR


def pode_ver_portaria(user):
    """Quem enxerga o painel da portaria: a propria portaria e a moderacao."""
    return eh_portaria(user) or eh_moderador(user)


def residente_required(view_func):
    @wraps(view_func)
    @login_required(login_url="core:login")
    def _wrapped(request, *args, **kwargs):
        if not pode_reservar(request.user):
            messages.error(
                request,
                "Area restrita a moradores aprovados. Aguardando aprovacao do moderador?"
            )
            return redirect("core:home")
        return view_func(request, *args, **kwargs)
    return _wrapped


def moderador_required(view_func):
    @wraps(view_func)
    @login_required(login_url="core:login")
    def _wrapped(request, *args, **kwargs):
        if not eh_moderador(request.user):
            messages.error(request, "Acesso restrito ao moderador.")
            return redirect("core:home")
        return view_func(request, *args, **kwargs)
    return _wrapped


def portaria_required(view_func):
    """Painel da portaria: somente leitura, liberado a portaria e a moderacao."""
    @wraps(view_func)
    @login_required(login_url="core:login")
    def _wrapped(request, *args, **kwargs):
        if not pode_ver_portaria(request.user):
            messages.error(request, "Acesso restrito a portaria e a moderacao.")
            return redirect("core:home")
        return view_func(request, *args, **kwargs)
    return _wrapped
