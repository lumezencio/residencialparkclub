from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("perfil/", views.perfil, name="perfil"),
    path("sobre/", views.sobre, name="sobre"),
    path("galeria/", views.galeria, name="galeria"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("moderacao/", views.moderacao, name="moderacao"),
    path("moderacao/criar-usuario/", views.criar_usuario, name="criar_usuario"),
    path("moderacao/aprovar/<str:tipo>/<int:pk>/", views.moderar_item, name="moderar_item"),
    path("moderacao/suspender/<int:pk>/", views.suspender_morador, name="suspender_morador"),
    path("moderacao/remover-suspensao/<int:pk>/", views.remover_suspensao_morador, name="remover_suspensao_morador"),
    path("galeria/excluir/<int:pk>/", views.excluir_midia, name="excluir_midia"),
    # Empresas e Fornecedores
    path("cadastro/empresa/", views.cadastro_empresa, name="cadastro_empresa"),
    path("propagandas/", views.minhas_propagandas, name="minhas_propagandas"),
    path("propagandas/criar/", views.criar_propaganda, name="criar_propaganda"),
    path("propagandas/editar/<int:pk>/", views.editar_propaganda, name="editar_propaganda"),
    path("propagandas/pausar/<int:pk>/", views.pausar_propaganda, name="pausar_propaganda"),
    path("propagandas/excluir/<int:pk>/", views.excluir_propaganda, name="excluir_propaganda"),
]
