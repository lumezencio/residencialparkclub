from django.urls import path
from . import views

app_name = "comunicacao"

urlpatterns = [
    path("mural/", views.mural, name="mural"),
    path("mural/<int:pk>/", views.detalhe_post, name="detalhe_post"),
    path("mensagem/", views.mensagem_administracao, name="mensagem_adm"),
]
