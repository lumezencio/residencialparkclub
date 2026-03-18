from django.contrib import admin
from .models import Anuncio, FotoAnuncio


class FotoAnuncioInline(admin.TabularInline):
    model = FotoAnuncio
    extra = 1


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ["titulo", "tipo", "autor", "bloco", "apartamento", "valor", "status", "destaque", "criado_em"]
    list_filter = ["tipo", "status", "destaque"]
    list_editable = ["status", "destaque"]
    search_fields = ["titulo", "descricao", "bloco", "apartamento"]
    inlines = [FotoAnuncioInline]
    readonly_fields = ["visualizacoes"]
