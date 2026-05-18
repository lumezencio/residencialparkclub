from django.urls import path

from . import views

app_name = "reservas"

urlpatterns = [
    path("", views.lista_espacos, name="lista"),
    path("minhas/", views.minhas_reservas, name="minhas"),
    path("painel/", views.painel_moderador, name="painel"),
    path("bloqueio/criar/", views.criar_bloqueio, name="criar_bloqueio"),
    path("bloqueio/<int:pk>/remover/", views.remover_bloqueio, name="remover_bloqueio"),
    path("cancelar/<int:pk>/", views.cancelar_reserva, name="cancelar"),
    path("<slug:slug>/", views.calendario, name="calendario"),
    path("<slug:slug>/reservar/", views.criar_reserva, name="criar"),
]
