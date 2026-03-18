from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, MidiaCondominio, Informacao


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


@admin.register(Informacao)
class InformacaoAdmin(admin.ModelAdmin):
    list_display = ["titulo", "ordem", "ativo"]
    list_editable = ["ordem", "ativo"]
