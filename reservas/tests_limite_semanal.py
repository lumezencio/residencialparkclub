"""Testes do limite semanal de reservas e da excecao individual por morador."""
from datetime import date, timedelta

from django.contrib.admin.sites import site as admin_site
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Usuario
from reservas.models import Espaco, LimiteReservaUsuario, Reserva, semana_de


class SemanaDeTest(TestCase):
    """A semana e de CALENDARIO: segunda a domingo."""

    def test_segunda_e_o_primeiro_dia(self):
        ini, fim = semana_de(date(2026, 8, 26))  # quarta-feira
        self.assertEqual(ini, date(2026, 8, 24))  # segunda
        self.assertEqual(fim, date(2026, 8, 30))  # domingo

    def test_domingo_fecha_a_semana(self):
        ini, fim = semana_de(date(2026, 8, 30))  # domingo
        self.assertEqual(ini, date(2026, 8, 24))
        self.assertEqual(fim, date(2026, 8, 30))

    def test_segunda_seguinte_abre_semana_nova(self):
        _, fim_a = semana_de(date(2026, 8, 30))   # domingo
        ini_b, _ = semana_de(date(2026, 8, 31))   # segunda seguinte
        self.assertEqual(ini_b, fim_a + timedelta(days=1))


class LimiteSemanalTest(TestCase):
    def setUp(self):
        # Espaco de teste folgado nas OUTRAS regras, para isolar a semanal
        self.espaco = Espaco.objects.create(
            nome="Quadra Teste", slug="quadra-teste",
            max_reservas_por_semana_por_usuario=2,
            max_reservas_por_dia_por_usuario=1,
            max_reservas_futuras_por_usuario=10,
            antecedencia_min_horas=1,
            antecedencia_max_dias=30,
        )
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="1", first_name="Zeca", bloco="B", apartamento="202")
        # Segunda da proxima semana: sempre no futuro e dentro dos 30 dias
        hoje = timezone.localdate()
        self.seg = hoje - timedelta(days=hoje.weekday()) + timedelta(days=7)

    def reservar(self, dia, hora="10:00"):
        return self.client.post(
            reverse("reservas:criar", args=[self.espaco.slug]),
            {"data": dia.isoformat(), "hora_inicio": hora},
            follow=True,
        )

    def criar_direto(self, dia, hora=8):
        from datetime import time as t
        return Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco, data=dia,
            hora_inicio=t(hora, 0), hora_fim=t(hora + 1, 0), status="confirmada")

    def test_terceira_reserva_da_semana_e_bloqueada(self):
        self.criar_direto(self.seg, 8)
        self.criar_direto(self.seg + timedelta(days=1), 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=2))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 2)

    def test_dentro_da_cota_reserva_normalmente(self):
        self.criar_direto(self.seg, 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=1))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 2)

    def test_cota_zera_na_segunda_seguinte(self):
        self.criar_direto(self.seg, 8)
        self.criar_direto(self.seg + timedelta(days=1), 8)
        self.client.force_login(self.morador)
        # Domingo da mesma semana: bloqueado
        self.reservar(self.seg + timedelta(days=6))
        self.assertEqual(Reserva.objects.filter(status="confirmada").count(), 2)
        # Segunda da semana seguinte: liberado
        self.reservar(self.seg + timedelta(days=7))
        self.assertEqual(Reserva.objects.filter(status="confirmada").count(), 3)

    def test_reserva_cancelada_nao_consome_cota(self):
        r = self.criar_direto(self.seg, 8)
        r.status = "cancelada"
        r.save()
        self.criar_direto(self.seg + timedelta(days=1), 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=2))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 2)

    def test_excecao_individual_aumenta_o_limite(self):
        LimiteReservaUsuario.objects.create(
            usuario=self.morador, espaco=self.espaco, max_por_semana=4)
        self.criar_direto(self.seg, 8)
        self.criar_direto(self.seg + timedelta(days=1), 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=2))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 3)

    def test_excecao_individual_reduz_o_limite(self):
        LimiteReservaUsuario.objects.create(
            usuario=self.morador, espaco=self.espaco, max_por_semana=1)
        self.criar_direto(self.seg, 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=1))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 1)

    def test_excecao_zero_impede_qualquer_reserva(self):
        LimiteReservaUsuario.objects.create(
            usuario=self.morador, espaco=self.espaco, max_por_semana=0)
        self.client.force_login(self.morador)
        self.reservar(self.seg)
        self.assertEqual(Reserva.objects.filter(status="confirmada").count(), 0)

    def test_excecao_nao_vaza_para_outro_morador(self):
        outro = Usuario.objects.create_user(
            username="morador2", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="9", first_name="Ana")
        LimiteReservaUsuario.objects.create(
            usuario=outro, espaco=self.espaco, max_por_semana=9)
        self.criar_direto(self.seg, 8)
        self.criar_direto(self.seg + timedelta(days=1), 8)
        self.client.force_login(self.morador)
        self.reservar(self.seg + timedelta(days=2))
        self.assertEqual(
            Reserva.objects.filter(usuario=self.morador, status="confirmada").count(), 2)

    def test_calendario_mostra_a_cota_da_semana(self):
        ini, _ = semana_de(timezone.localdate())
        self.criar_direto(ini, 8)  # pode ja ter passado: continua consumindo a cota
        self.client.force_login(self.morador)
        r = self.client.get(reverse("reservas:calendario", args=[self.espaco.slug]))
        self.assertEqual(r.context["minhas_na_semana"], 1)
        self.assertEqual(r.context["limite_semana"], 2)
        self.assertFalse(r.context["limite_personalizado"])
        self.assertContains(r, "Semana de")

    def test_calendario_sinaliza_limite_personalizado(self):
        LimiteReservaUsuario.objects.create(
            usuario=self.morador, espaco=self.espaco, max_por_semana=5)
        self.client.force_login(self.morador)
        r = self.client.get(reverse("reservas:calendario", args=[self.espaco.slug]))
        self.assertEqual(r.context["limite_semana"], 5)
        self.assertTrue(r.context["limite_personalizado"])


class EspacoAdminTest(TestCase):
    """Regressao: os limites por dia e por semana precisam ser editaveis no admin."""

    def test_limites_aparecem_no_formulario_do_admin(self):
        campos = []
        for _, opcoes in admin_site._registry[Espaco].fieldsets:
            campos.extend(opcoes["fields"])
        self.assertIn("max_reservas_por_semana_por_usuario", campos)
        self.assertIn("max_reservas_por_dia_por_usuario", campos)
        self.assertIn("max_reservas_futuras_por_usuario", campos)
