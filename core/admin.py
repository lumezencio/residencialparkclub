from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Usuario, MidiaCondominio, Informacao, Propaganda, SuspensaoMorador


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "bloco", "apartamento", "tipo", "aprovado"]
    list_filter = ["tipo", "aprovado", "bloco"]
    list_editable = ["aprovado"]
    search_fields = ["username", "first_name", "last_name", "email", "bloco", "apartamento"]
    fieldsets = UserAdmin.fieldsets + (
        ("Dados do Condomínio", {
            "fields": ("tipo", "cpf", "telefone", "bloco", "apartamento", "foto_perfil", "aprovado"),
        }),
    )


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
            return format_html('<span style="color:#c00;font-weight:bold;">EM VIGOR</span>')
        return format_html('<span style="color:#888;">encerrada</span>')
    em_vigor_badge.short_description = "Status"

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.aplicada_por_id:
            obj.aplicada_por = request.user
        super().save_model(request, obj, form, change)
