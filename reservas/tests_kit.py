"""Testes do controle do kit de jogo (raquetes + bolinhas) na portaria."""
from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Usuario
from reservas.models import Espaco, KitJogo, Reserva


class KitBaseTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(nome="Quadra Teste", slug="quadra-teste")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="30", first_name="Portaria")
        self.moderador = Usuario.objects.create_user(
            username="mod1", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="31", first_name="Mod")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="32", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")
        self.reserva = Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco, data=timezone.localdate(),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="confirmada")

    def url_retirada(self, r=None):
        return reverse("reservas:kit_retirada", args=[(r or self.reserva).pk])

    def url_devolucao(self, r=None):
        return reverse("reservas:kit_devolucao", args=[(r or self.reserva).pk])


class KitFluxoTest(KitBaseTest):
    def test_portaria_registra_retirada(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {
            "retirado_por": "Zeca Silva", "raquetes": 2, "bolinhas": 3,
            "voltar": "portaria"}, follow=True)
        kit = KitJogo.objects.get(reserva=self.reserva)
        self.assertEqual(kit.retirado_por, "Zeca Silva")
        self.assertEqual(kit.raquetes, 2)
        self.assertEqual(kit.bolinhas, 3)
        self.assertEqual(kit.retirada_registrada_por, self.portaria)
        self.assertFalse(kit.devolvido)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.kit_estado, "retirado")

    def test_portaria_registra_devolucao(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca", "voltar": "portaria"})
        self.client.post(self.url_devolucao(), {
            "devolvido_por": "Maria Souza", "observacao": "faltou 1 bolinha",
            "voltar": "portaria"}, follow=True)
        kit = KitJogo.objects.get(reserva=self.reserva)
        self.assertTrue(kit.devolvido)
        self.assertEqual(kit.devolvido_por, "Maria Souza")
        self.assertEqual(kit.observacao, "faltou 1 bolinha")
        self.assertEqual(kit.devolucao_registrada_por, self.portaria)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.kit_estado, "devolvido")

    def test_quem_devolve_pode_ser_outra_pessoa(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca Silva"})
        self.client.post(self.url_devolucao(), {"devolvido_por": "Joao Lima"})
        kit = KitJogo.objects.get(reserva=self.reserva)
        self.assertEqual(kit.retirado_por, "Zeca Silva")
        self.assertEqual(kit.devolvido_por, "Joao Lima")

    def test_moderador_tambem_registra(self):
        self.client.force_login(self.moderador)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca", "voltar": "painel"})
        self.assertTrue(KitJogo.objects.filter(reserva=self.reserva).exists())

    def test_sem_kit_o_estado_e_livre(self):
        self.assertEqual(self.reserva.kit_estado, "livre")
        self.assertIsNone(self.reserva.kit_info)


class KitValidacaoTest(KitBaseTest):
    def test_nome_vazio_na_retirada_e_recusado(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "   "}, follow=True)
        self.assertFalse(KitJogo.objects.exists())

    def test_nome_vazio_na_devolucao_e_recusado(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca"})
        self.client.post(self.url_devolucao(), {"devolvido_por": ""}, follow=True)
        self.assertFalse(KitJogo.objects.get(reserva=self.reserva).devolvido)

    def test_nao_retira_duas_vezes(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca"})
        self.client.post(self.url_retirada(), {"retirado_por": "Outro"}, follow=True)
        self.assertEqual(KitJogo.objects.count(), 1)
        self.assertEqual(KitJogo.objects.get().retirado_por, "Zeca")

    def test_nao_devolve_duas_vezes(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca"})
        self.client.post(self.url_devolucao(), {"devolvido_por": "Primeiro"})
        primeiro = KitJogo.objects.get().devolvido_em
        self.client.post(self.url_devolucao(), {"devolvido_por": "Segundo"}, follow=True)
        kit = KitJogo.objects.get()
        self.assertEqual(kit.devolvido_por, "Primeiro")
        self.assertEqual(kit.devolvido_em, primeiro)

    def test_devolucao_sem_retirada_e_recusada(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_devolucao(), {"devolvido_por": "Zeca"}, follow=True)
        self.assertFalse(KitJogo.objects.exists())

    def test_reserva_cancelada_nao_entrega_kit(self):
        self.reserva.status = "cancelada"
        self.reserva.save()
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "Zeca"}, follow=True)
        self.assertFalse(KitJogo.objects.exists())

    def test_quantidades_absurdas_sao_limitadas(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {
            "retirado_por": "Zeca", "raquetes": 9999, "bolinhas": -5})
        kit = KitJogo.objects.get()
        self.assertEqual(kit.raquetes, 20)  # teto
        self.assertEqual(kit.bolinhas, 0)   # piso

    def test_quantidade_nao_numerica_usa_o_padrao(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {
            "retirado_por": "Zeca", "raquetes": "duas", "bolinhas": ""})
        kit = KitJogo.objects.get()
        self.assertEqual(kit.raquetes, 2)
        self.assertEqual(kit.bolinhas, 3)

    def test_nome_gigante_e_truncado(self):
        self.client.force_login(self.portaria)
        self.client.post(self.url_retirada(), {"retirado_por": "N" * 500})
        self.assertEqual(len(KitJogo.objects.get().retirado_por), 120)


class KitSegurancaTest(KitBaseTest):
    def test_morador_nao_registra_kit(self):
        self.client.force_login(self.morador)
        r = self.client.post(self.url_retirada(), {"retirado_por": "Zeca"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(KitJogo.objects.exists())

    def test_anonimo_nao_registra_kit(self):
        r = self.client.post(self.url_retirada(), {"retirado_por": "Zeca"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])
        self.assertFalse(KitJogo.objects.exists())

    def test_get_nao_altera_nada(self):
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(self.url_retirada()).status_code, 405)
        self.assertEqual(self.client.get(self.url_devolucao()).status_code, 405)
        self.assertFalse(KitJogo.objects.exists())

    def test_redirect_aberto_e_ignorado(self):
        """O campo `voltar` so aceita telas conhecidas."""
        self.client.force_login(self.portaria)
        r = self.client.post(self.url_retirada(), {
            "retirado_por": "Zeca", "voltar": "https://site-malicioso.example/"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("reservas:portaria"))

    def test_voltar_para_o_painel_quando_veio_do_painel(self):
        self.client.force_login(self.moderador)
        r = self.client.post(self.url_retirada(), {"retirado_por": "Zeca", "voltar": "painel"})
        self.assertEqual(r["Location"], reverse("reservas:painel"))

    def test_portaria_continua_sem_cancelar_reserva(self):
        self.client.force_login(self.portaria)
        self.client.post(reverse("reservas:cancelar", args=[self.reserva.pk]), follow=True)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.status, "confirmada")

    def test_reserva_inexistente_da_404(self):
        self.client.force_login(self.portaria)
        r = self.client.post(reverse("reservas:kit_retirada", args=[99999]),
                             {"retirado_por": "Zeca"})
        self.assertEqual(r.status_code, 404)


class KitTelasTest(KitBaseTest):
    def test_painel_da_portaria_mostra_o_controle(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertContains(r, "abrirModalKit")
        self.assertContains(r, "entregar kit")
        self.assertContains(r, "kitFormRetirada")

    def test_portaria_mostra_kit_com_o_morador(self):
        KitJogo.objects.create(reserva=self.reserva, retirado_por="Zeca Silva")
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertContains(r, "KIT COM O MORADOR")
        self.assertContains(r, "Zeca Silva")
        self.assertEqual(r.context["kits_em_uso"], 1)

    def test_portaria_mostra_kit_devolvido(self):
        KitJogo.objects.create(
            reserva=self.reserva, retirado_por="Zeca",
            devolvido_por="Maria", devolvido_em=timezone.now())
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertContains(r, "KIT DEVOLVIDO")
        self.assertEqual(r.context["kits_em_uso"], 0)

    def test_painel_do_moderador_tem_a_coluna_do_kit(self):
        futura = Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco,
            data=timezone.localdate() + timedelta(days=1),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="confirmada")
        self.client.force_login(self.moderador)
        r = self.client.get(reverse("reservas:painel"))
        self.assertContains(r, "Kit de jogo")
        self.assertContains(r, "abrirModalKit")
        self.assertContains(r, 'data-kit-pk="%s"' % futura.pk)
