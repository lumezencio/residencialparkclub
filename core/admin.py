from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    Usuario, MidiaCondominio, Informacao, Propaganda, RegistroModeracao,
    SuspensaoMorador,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "bloco", "apartamento", "tipo",
                    "aprovado", "liberado_por"]
    list_filter = ["tipo", "aprovado", "bloco"]
    list_editable = ["aprovado"]
    search_fields = ["username", "first_name", "last_name", "email", "bloco", "apartamento"]
    # Trilha de auditoria: preenchida pelo sistema, nao na mao.
    readonly_fields = ("aprovado_por", "aprovado_em")
    fieldsets = UserAdmin.fieldsets + (
        ("Dados do Condomínio", {
            "fields": ("tipo", "cpf", "telefone", "bloco", "apartamento", "foto_perfil", "aprovado"),
        }),
        ("Liberação do cadastro", {
            "fields": ("aprovado_por", "aprovado_em"),
            "description": "Quem liberou este cadastro. Preenchido automaticamente ao aprovar.",
        }),
    )

    def liberado_por(self, obj):
        if obj.aprovado_por_nome:
            return format_html(
                '{} <span style="color:#888;">{}</span>',
                obj.aprovado_por_nome,
                obj.aprovado_em.strftime("%d/%m/%Y") if obj.aprovado_em else "",
            )
        if obj.aprovado:
            return mark_safe('<span style="color:#888;">nao registrado</span>')
        return mark_safe('<span style="color:#888;">&mdash;</span>')
    liberado_por.short_description = "Liberado por"

    def save_model(self, request, obj, form, change):
        """Mantem a trilha coerente tambem quando a aprovacao vem do admin.

        Cobre o formulario de edicao e o atalho de marcar `aprovado` direto na
        listagem, que tambem passa por aqui.
        """
        if obj.aprovado and obj.aprovado_por_id is None:
            obj.aprovado_por = request.user
            obj.aprovado_em = timezone.now()
        elif not obj.aprovado:
            obj.aprovado_por = None
            obj.aprovado_em = None
        super().save_model(request, obj, form, change)


@admin.register(MidiaCondominio)
class MidiaCondominioAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "categoria", "destaque", "ativo", "ordem", "criado_em"]
    list_filter = ["tipo", "categoria", "destaque", "ativo"]
    list_editable = ["destaque", "ativo", "ordem"]
    search_fields = ["titulo", "descricao"]


@admin.register(Propaganda)
class PropagandaAdmin(admin.ModelAdmin):
    list_display = ["titulo", "anunciante", "status", "ativo", "criado_em"]
    list_filter = ["status", "ativo"]
    list_editable = ["status", "ativo"]
    search_fields = ["titulo", "anunciante__nome_empresa"]


@admin.register(Informacao)
class InformacaoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "ordem", "ativo"]
    list_editable = ["ordem", "ativo"]


@admin.register(SuspensaoMorador)
class SuspensaoMoradorAdmin(admin.ModelAdmin):
    list_display = ["usuario", "inicio", "fim", "motivo_curto", "ativa", "em_vigor_badge",
                    "aplicada_por", "criada_em"]
    list_filter = ["ativa"]
    search_fields = ["usuario__username", "usuario__first_name", "usuario__last_name",
                     "motivo"]
    autocomplete_fields = ["usuario", "aplicada_por", "encerrada_por"]
    readonly_fields = ["criada_em", "encerrada_em", "encerrada_por"]
    date_hierarchy = "inicio"

    def motivo_curto(self, obj):
        return (obj.motivo[:60] + "...") if len(obj.motivo) > 60 else obj.motivo
    motivo_curto.short_description = "Motivo"

    def em_vigor_badge(self, obj):
        if obj.em_vigor:
            return mark_safe('<span style="color:#c00;font-weight:bold;">EM VIGOR</span>')
        return mark_safe('<span style="color:#888;">encerrada</span>')
    em_vigor_badge.short_description = "Status"

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.aplicada_por_id:
            obj.aplicada_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(RegistroModeracao)
class RegistroModeracaoAdmin(admin.ModelAdmin):
    """Auditoria: so leitura, nem o superadmin edita o historico."""

    list_display = ("criado_em", "acao", "alvo_nome", "moderador_nome", "descricao")
    list_filter = ("acao", "criado_em")
    search_fields = ("alvo_nome", "moderador_nome", "descricao")
    date_hierarchy = "criado_em"
    readonly_fields = ("acao", "moderador", "moderador_nome", "alvo_usuario",
                       "alvo_nome", "descricao", "criado_em")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
