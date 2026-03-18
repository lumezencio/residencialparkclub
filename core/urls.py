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
    path("moderacao/aprovar/<str:tipo>/<int:pk>/", views.moderar_item, name="moderar_item"),
    path("galeria/excluir/<int:pk>/", views.excluir_midia, name="excluir_midia"),
]
