"""Testes da redefinicao de senha pelo moderador (rodam em sqlite in-memory)."""
from django.test import TestCase
from django.urls import reverse
from core.models import Usuario


class RedefinirSenhaTest(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1")
        self.mod = Usuario.objects.create_user(
            username="mod1", password="ModSenha123!", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Mod", bloco="A", apartamento="1")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="SenhaAntiga123!", tipo="morador",
            aprovado=True, cpf="3", first_name="Zeca", bloco="B", apartamento="202")
        self.outro_mod = Usuario.objects.create_user(
            username="mod2", password="ModSenha123!", tipo="moderador",
            is_staff=True, aprovado=True, cpf="4", first_name="Outro")

    def url(self, u):
        return reverse("core:redefinir_senha_usuario", args=[u.pk])

    def test_moderador_gera_senha_automatica(self):
        self.client.force_login(self.mod)
        r = self.client.post(self.url(self.morador), follow=True)
        self.assertEqual(r.status_code, 200)
        self.morador.refresh_from_db()
        self.assertFalse(self.morador.check_password("SenhaAntiga123!"))
        senha = r.context["senha_redefinida"]["senha"]
        self.assertEqual(len(senha), 12)
        self.assertTrue(self.morador.check_password(senha))
        self.assertContains(r, senha)
        # senha some da sessao apos exibida uma vez
        r2 = self.client.get(reverse("core:moderacao"))
        self.assertIsNone(r2.context["senha_redefinida"])

    def test_senha_manual_valida(self):
        self.client.force_login(self.mod)
        self.client.post(self.url(self.morador), {"nova_senha": "ChaveDoZeca#2026"})
        self.morador.refresh_from_db()
        self.assertTrue(self.morador.check_password("ChaveDoZeca#2026"))

    def test_senha_manual_fraca_rejeitada(self):
        self.client.force_login(self.mod)
        self.client.post(self.url(self.morador), {"nova_senha": "123"}, follow=True)
        self.morador.refresh_from_db()
        self.assertTrue(self.morador.check_password("SenhaAntiga123!"))

    def test_moderador_nao_redefine_senha_de_outro_moderador(self):
        self.client.force_login(self.mod)
        self.client.post(self.url(self.outro_mod), follow=True)
        self.outro_mod.refresh_from_db()
        self.assertTrue(self.outro_mod.check_password("ModSenha123!"))

    def test_moderador_nao_redefine_senha_do_superadmin(self):
        self.client.force_login(self.mod)
        self.client.post(self.url(self.admin), follow=True)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("AdminSenha123!"))

    def test_superadmin_redefine_senha_de_moderador(self):
        self.client.force_login(self.admin)
        r = self.client.post(self.url(self.outro_mod), follow=True)
        self.outro_mod.refresh_from_db()
        self.assertTrue(self.outro_mod.check_password(r.context["senha_redefinida"]["senha"]))

    def test_nao_redefine_a_propria_senha(self):
        self.client.force_login(self.mod)
        self.client.post(self.url(self.mod), follow=True)
        self.mod.refresh_from_db()
        self.assertTrue(self.mod.check_password("ModSenha123!"))

    def test_morador_comum_recebe_403(self):
        self.client.force_login(self.morador)
        r = self.client.post(self.url(self.outro_mod))
        self.assertEqual(r.status_code, 403)

    def test_get_nao_altera_senha(self):
        self.client.force_login(self.mod)
        r = self.client.get(self.url(self.morador))
        self.assertEqual(r.status_code, 405)
        self.morador.refresh_from_db()
        self.assertTrue(self.morador.check_password("SenhaAntiga123!"))

    def test_anonimo_redirecionado_para_login(self):
        r = self.client.post(self.url(self.morador))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_painel_do_moderador_lista_moradores_com_botao(self):
        self.client.force_login(self.mod)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "Moradores cadastrados")
        self.assertContains(r, "Gerar nova senha")
        self.assertContains(r, "abrirModalSenha")
        # moderador comum NAO ve a gestao de moderadores
        self.assertNotContains(r, "Gerenciar Moderadores")
        self.assertNotContains(r, "promover_moderador")

    def test_painel_do_superadmin_mantem_gestao_de_moderadores(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "Gerenciar Moderadores")
        self.assertContains(r, "promover_moderador")
        self.assertContains(r, "Moradores cadastrados")

    def test_sessao_antiga_do_morador_e_invalidada(self):
        c_morador = self.client.__class__()
        c_morador.force_login(self.morador)
        self.assertEqual(c_morador.get(reverse("core:perfil")).status_code, 200)
        self.client.force_login(self.mod)
        self.client.post(self.url(self.morador))
        r = c_morador.get(reverse("core:perfil"))
        self.assertEqual(r.status_code, 302)  # deslogado
