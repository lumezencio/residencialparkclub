"""Testes do ajuste individual de cota semanal pelo painel de moderacao."""
from django.test import TestCase
from django.urls import reverse

from core.models import Usuario
from reservas.models import Espaco, LimiteReservaUsuario


class DefinirLimiteReservasTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(
            nome="Quadra Teste", slug="quadra-teste",
            max_reservas_por_semana_por_usuario=2)
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1")
        self.mod = Usuario.objects.create_user(
            username="mod1", password="ModSenha123!", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Mod")
        self.outro_mod = Usuario.objects.create_user(
            username="mod2", password="ModSenha123!", tipo="moderador",
            is_staff=True, aprovado=True, cpf="3", first_name="Outro")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="SenhaMorador123!", tipo="morador",
            aprovado=True, cpf="4", first_name="Zeca", bloco="B", apartamento="202")

    def url(self, u):
        return reverse("core:definir_limite_reservas", args=[u.pk])

    def post(self, alvo, **dados):
        dados.setdefault("espaco", self.espaco.pk)
        return self.client.post(self.url(alvo), dados, follow=True)

    def test_moderador_define_limite_maior(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=5, motivo="Autorizado pelo sindico")
        lim = LimiteReservaUsuario.objects.get(usuario=self.morador, espaco=self.espaco)
        self.assertEqual(lim.max_por_semana, 5)
        self.assertEqual(lim.motivo, "Autorizado pelo sindico")
        self.assertEqual(lim.definido_por, self.mod)

    def test_moderador_define_limite_menor(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=1)
        self.assertEqual(
            LimiteReservaUsuario.objects.get(usuario=self.morador).max_por_semana, 1)

    def test_zero_e_aceito_e_impede_reservas(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=0)
        self.assertEqual(
            LimiteReservaUsuario.objects.get(usuario=self.morador).max_por_semana, 0)
        self.assertEqual(self.espaco.limite_semanal_para(self.morador), (0, True))

    def test_redefinir_atualiza_em_vez_de_duplicar(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=5)
        self.post(self.morador, max_por_semana=3)
        self.assertEqual(LimiteReservaUsuario.objects.count(), 1)
        self.assertEqual(
            LimiteReservaUsuario.objects.get(usuario=self.morador).max_por_semana, 3)

    def test_voltar_ao_padrao_remove_a_excecao(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=5)
        self.post(self.morador, acao="padrao")
        self.assertFalse(LimiteReservaUsuario.objects.exists())
        self.assertEqual(self.espaco.limite_semanal_para(self.morador), (2, False))

    def test_valor_negativo_e_rejeitado(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=-1)
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_valor_absurdo_e_rejeitado(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana=999999)
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_valor_nao_numerico_e_rejeitado(self):
        self.client.force_login(self.mod)
        self.post(self.morador, max_por_semana="muitas")
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_espaco_inexistente_da_404(self):
        self.client.force_login(self.mod)
        r = self.client.post(self.url(self.morador), {"espaco": 99999, "max_por_semana": 3})
        self.assertEqual(r.status_code, 404)

    def test_moderador_nao_altera_limite_de_outro_moderador(self):
        self.client.force_login(self.mod)
        self.post(self.outro_mod, max_por_semana=9)
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_superadmin_altera_limite_de_moderador(self):
        self.client.force_login(self.admin)
        self.post(self.outro_mod, max_por_semana=9)
        self.assertEqual(
            LimiteReservaUsuario.objects.get(usuario=self.outro_mod).max_por_semana, 9)

    def test_morador_comum_recebe_403(self):
        self.client.force_login(self.morador)
        r = self.client.post(self.url(self.morador), {"espaco": self.espaco.pk,
                                                      "max_por_semana": 99})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_get_nao_altera_nada(self):
        self.client.force_login(self.mod)
        r = self.client.get(self.url(self.morador))
        self.assertEqual(r.status_code, 405)
        self.assertFalse(LimiteReservaUsuario.objects.exists())

    def test_anonimo_vai_para_o_login(self):
        r = self.client.post(self.url(self.morador), {"espaco": self.espaco.pk,
                                                      "max_por_semana": 3})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_painel_mostra_botao_e_limite_vigente(self):
        LimiteReservaUsuario.objects.create(
            usuario=self.morador, espaco=self.espaco, max_por_semana=4)
        self.client.force_login(self.mod)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "Limite de reservas")
        self.assertContains(r, "abrirModalLimite")
        self.assertContains(r, "4/semana")
