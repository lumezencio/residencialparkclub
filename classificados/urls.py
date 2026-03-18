from django.urls import path
from . import views

app_name = "classificados"

urlpatterns = [
    path("", views.lista_anuncios, name="lista"),
    path("<int:pk>/", views.detalhe_anuncio, name="detalhe"),
    path("criar/", views.criar_anuncio, name="criar"),
    path("meus/", views.meus_anuncios, name="meus"),
]
