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


def pode_reservar(user):
    if not user.is_authenticated:
        return False
    if not getattr(user, "aprovado", False):
        return False
    return getattr(user, "tipo", "") in TIPOS_PERMITIDOS


def eh_moderador(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return getattr(user, "tipo", "") in TIPOS_MODERADOR


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
