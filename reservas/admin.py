from django.contrib import admin
from django.utils.html import format_html

from .models import BloqueioEspaco, Espaco, Reserva


@admin.register(Espaco)
class EspacoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo", "horario_abertura", "horario_fechamento",
                    "duracao_slot_min", "max_reservas_futuras_por_usuario")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    prepopulated_fields = {"slug": ("nome",)}
    fieldsets = (
        ("Identificacao", {"fields": ("nome", "slug", "descricao", "foto", "ativo")}),
        ("Horario de funcionamento", {
            "fields": ("horario_abertura", "horario_fechamento", "duracao_slot_min"),
        }),
        ("Regras de reserva", {
            "fields": (
                "max_reservas_futuras_por_usuario",
                "antecedencia_min_horas",
                "antecedencia_max_dias",
                "cancelamento_min_horas",
            ),
        }),
    )


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("data", "hora_inicio", "hora_fim", "espaco", "usuario_info",
                    "status", "tem_convidados", "criado_em")
    list_filter = ("status", "espaco", "data")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name",
                     "usuario__bloco", "usuario__apartamento", "convidados")
    date_hierarchy = "data"
    readonly_fields = ("criado_em", "atualizado_em", "cancelada_em", "cancelada_por")
    autocomplete_fields = ("usuario",)
    fieldsets = (
        (None, {"fields": ("espaco", "usuario", "data", "hora_inicio", "hora_fim",
                           "convidados", "observacao", "status")}),
        ("Cancelamento", {
            "fields": ("cancelada_por", "cancelada_em", "motivo_cancelamento"),
            "classes": ("collapse",),
        }),
        ("Auditoria", {"fields": ("criado_em", "atualizado_em"), "classes": ("collapse",)}),
    )

    def usuario_info(self, obj):
        nome = obj.usuario.get_full_name() or obj.usuario.username
        bloco = obj.usuario.bloco or "?"
        apt = obj.usuario.apartamento or "?"
        return f"{nome} (Bl {bloco} Apt {apt})"
    usuario_info.short_description = "Morador"

    def tem_convidados(self, obj):
        return bool(obj.convidados.strip()) if obj.convidados else False
    tem_convidados.boolean = True
    tem_convidados.short_description = "Convidados"


@admin.register(BloqueioEspaco)
class BloqueioEspacoAdmin(admin.ModelAdmin):
    list_display = ("espaco", "data_inicio", "data_fim", "motivo", "criado_por", "criado_em")
    list_filter = ("espaco",)
    search_fields = ("motivo",)
    autocomplete_fields = ("criado_por",)
    readonly_fields = ("criado_em",)

    def save_model(self, request, obj, form, change):
        if not obj.criado_por_id:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)
