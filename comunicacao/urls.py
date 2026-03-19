from django.urls import path
from . import views

app_name = "comunicacao"

urlpatterns = [
    path("mural/", views.mural, name="mural"),
    path("mural/<int:pk>/", views.detalhe_post, name="detalhe_post"),
    path("mural/<int:pk>/editar/", views.editar_post, name="editar_post"),
    path("mural/<int:pk>/excluir/", views.excluir_post, name="excluir_post"),
    path("mensagem/", views.mensagem_administracao, name="mensagem_adm"),
]
