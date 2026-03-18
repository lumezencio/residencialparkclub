from django.contrib import admin
from .models import MuralPost, Comentario, MensagemAdministracao


@admin.register(MuralPost)
class MuralPostAdmin(admin.ModelAdmin):
    list_display = ["titulo", "autor", "categoria", "aprovado", "fixado", "criado_em"]
    list_filter = ["categoria", "aprovado", "fixado"]
    list_editable = ["aprovado", "fixado"]
    search_fields = ["titulo", "conteudo"]


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ["post", "autor", "criado_em"]
    search_fields = ["conteudo"]


@admin.register(MensagemAdministracao)
class MensagemAdministracaoAdmin(admin.ModelAdmin):
    list_display = ["assunto", "remetente", "status", "criado_em", "respondido_em"]
    list_filter = ["status"]
    list_editable = ["status"]
    search_fields = ["assunto", "mensagem"]
