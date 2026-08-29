"""Testes do acesso da portaria: ve agendamentos e nada mais."""
from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Usuario
from reservas.models import Espaco, Reserva
from reservas.permissions import eh_moderador, eh_portaria, pode_reservar


class PortariaAcessoTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(
            nome="Quadra Teste", slug="quadra-teste", antecedencia_max_dias=30)
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="10", first_name="Portaria")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="11", first_name="Zeca", bloco="B", apartamento="202")
        self.moderador = Usuario.objects.create_user(
            username="mod1", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="12", first_name="Mod")

    def test_portaria_acessa_o_proprio_painel(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Agendamentos em tempo real")

    def test_moderador_tambem_acessa_o_painel_da_portaria(self):
        self.client.force_login(self.moderador)
        self.assertEqual(self.client.get(reverse("reservas:portaria")).status_code, 200)

    def test_morador_comum_nao_acessa_o_painel_da_portaria(self):
        self.client.force_login(self.morador)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertEqual(r.status_code, 302)

    def test_anonimo_vai_para_o_login(self):
        r = self.client.get(reverse("reservas:portaria"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_portaria_nao_acessa_painel_do_moderador(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:painel"))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("/reservas/painel", r["Location"])

    def test_portaria_nao_acessa_relatorios_nem_csv(self):
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(reverse("reservas:relatorios")).status_code, 302)
        self.assertEqual(self.client.get(reverse("reservas:exportar_csv")).status_code, 302)

    def test_portaria_nao_acessa_moderacao(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("core:moderacao"))
        self.assertEqual(r.status_code, 403)

    def test_portaria_nao_redefine_senha_de_ninguem(self):
        self.client.force_login(self.portaria)
        r = self.client.post(
            reverse("core:redefinir_senha_usuario", args=[self.morador.pk]))
        self.assertEqual(r.status_code, 403)
        self.morador.refresh_from_db()
        self.assertTrue(self.morador.check_password("Senha123!Forte"))

    def test_portaria_nao_altera_limite_de_reservas(self):
        self.client.force_login(self.portaria)
        r = self.client.post(
            reverse("core:definir_limite_reservas", args=[self.morador.pk]),
            {"espaco": self.espaco.pk, "max_por_semana": 9})
        self.assertEqual(r.status_code, 403)

    def test_portaria_nao_reserva_nem_ve_a_lista_de_espacos(self):
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(reverse("reservas:lista")).status_code, 302)
        amanha = timezone.localdate() + timedelta(days=2)
        self.client.post(
            reverse("reservas:criar", args=[self.espaco.slug]),
            {"data": amanha.isoformat(), "hora_inicio": "10:00"}, follow=True)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_portaria_com_is_staff_por_engano_continua_sem_poder_moderar(self):
        """Trava de seguranca: marcar is_staff nao promove a portaria a moderador."""
        self.portaria.is_staff = True
        self.portaria.save()
        self.assertFalse(eh_moderador(self.portaria))
        self.assertFalse(pode_reservar(self.portaria))
        self.assertTrue(eh_portaria(self.portaria))
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(reverse("core:moderacao")).status_code, 403)
        self.assertEqual(self.client.get(reverse("reservas:painel")).status_code, 302)
        self.assertEqual(self.client.get(reverse("reservas:relatorios")).status_code, 302)

    def corpo(self, html):
        """So o conteudo da pagina (fora do layout do site)."""
        return html.split("<main>")[1].split("</main>")[0]

    def menu(self, html):
        """So o menu de navegacao."""
        return html.split('class="nav-menu"')[1].split("</ul>")[0]

    def test_painel_nao_oferece_nenhuma_acao_de_escrita(self):
        self.client.force_login(self.portaria)
        html = self.client.get(reverse("reservas:portaria")).content.decode()
        corpo = self.corpo(html)
        self.assertNotIn("<form", corpo)
        self.assertNotIn("<button", corpo)
        for rota in ["/reservas/cancelar/", "/reservas/bloqueio/", "/reservas/suspensao/",
                     "/moderacao/"]:
            self.assertNotIn(rota, html)

    def test_menu_da_portaria_so_mostra_o_painel_dela(self):
        self.client.force_login(self.portaria)
        menu = self.menu(self.client.get(reverse("reservas:portaria")).content.decode())
        self.assertIn("Painel da Portaria", menu)
        self.assertNotIn("Moderação", menu)
        self.assertNotIn(">Galeria<", menu)
        self.assertNotIn(">Comunidade<", menu)
        self.assertNotIn(">Classificados<", menu)
        self.assertNotIn(">Reservas<", menu)
        self.assertNotIn("Relatorios", menu)


class PortariaConteudoTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(nome="Quadra Teste", slug="quadra-teste")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="20", first_name="Portaria")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="21", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")

    def test_mostra_a_reserva_de_hoje_com_morador_e_convidados(self):
        hoje = timezone.localdate()
        Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco, data=hoje,
            hora_inicio=time(9, 0), hora_fim=time(10, 0),
            convidados="Maria Souza\nJoao Lima", status="confirmada")
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertContains(r, "Zeca Silva")
        self.assertContains(r, "202")
        self.assertContains(r, "Maria Souza")
        self.assertContains(r, "Joao Lima")
        self.assertEqual(r.context["total_hoje"], 1)

    def test_reserva_cancelada_nao_aparece(self):
        Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco, data=timezone.localdate(),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="cancelada")
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertEqual(r.context["total_hoje"], 0)

    def test_situacao_do_espaco_sem_reserva_e_livre(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        situacao = r.context["situacao"][0]
        self.assertIsNone(situacao["atual"])
        self.assertContains(r, "LIVRE")
