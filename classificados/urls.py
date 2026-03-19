from django.urls import path
from . import views

app_name = "classificados"

urlpatterns = [
    path("", views.lista_anuncios, name="lista"),
    path("<int:pk>/", views.detalhe_anuncio, name="detalhe"),
    path("criar/", views.criar_anuncio, name="criar"),
    path("meus/", views.meus_anuncios, name="meus"),
    path("<int:pk>/editar/", views.editar_anuncio, name="editar"),
    path("<int:pk>/toggle-status/", views.toggle_status_anuncio, name="toggle_status"),
    path("<int:pk>/excluir/", views.excluir_anuncio, name="excluir"),
    path("foto/<int:pk>/excluir/", views.excluir_foto, name="excluir_foto"),
]
