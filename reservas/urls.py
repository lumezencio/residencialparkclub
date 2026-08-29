from django.urls import path

from . import views

app_name = "reservas"

urlpatterns = [
    path("", views.lista_espacos, name="lista"),
    path("minhas/", views.minhas_reservas, name="minhas"),
    path("painel/", views.painel_moderador, name="painel"),
    path("portaria/", views.painel_portaria, name="portaria"),
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/csv/", views.exportar_csv, name="exportar_csv"),
    path("bloqueio/criar/", views.criar_bloqueio, name="criar_bloqueio"),
    path("bloqueio/<int:pk>/remover/", views.remover_bloqueio, name="remover_bloqueio"),
    path("suspensao/criar/", views.criar_suspensao, name="criar_suspensao"),
    path("suspensao/<int:pk>/remover/", views.remover_suspensao, name="remover_suspensao"),
    path("historico/<int:pk>/", views.historico_usuario, name="historico_usuario"),
    path("kit/<int:pk>/retirada/", views.registrar_retirada_kit, name="kit_retirada"),
    path("kit/<int:pk>/devolucao/", views.registrar_devolucao_kit, name="kit_devolucao"),
    path("cancelar/<int:pk>/", views.cancelar_reserva, name="cancelar"),
    path("<slug:slug>/", views.calendario, name="calendario"),
    path("<slug:slug>/reservar/", views.criar_reserva, name="criar"),
]
