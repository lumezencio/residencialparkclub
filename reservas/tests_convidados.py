"""Testes dos convidados (nome + CPF) e do historico por morador."""
from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Usuario
from reservas.models import Convidado, Espaco, KitJogo, Reserva
from reservas.validators import cpf_valido, formatar_cpf, limpar_cpf

# CPFs sinteticos com digitos verificadores validos
CPF_OK = "529.982.247-25"
CPF_OK2 = "111.444.777-35"


class ValidadorCpfTest(TestCase):
    def test_aceita_cpf_valido_com_e_sem_mascara(self):
        self.assertTrue(cpf_valido(CPF_OK))
        self.assertTrue(cpf_valido("52998224725"))

    def test_recusa_digito_verificador_errado(self):
        self.assertFalse(cpf_valido("529.982.247-26"))

    def test_recusa_repetidos_e_tamanho_errado(self):
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertFalse(cpf_valido("00000000000"))
        self.assertFalse(cpf_valido("123"))
        self.assertFalse(cpf_valido(""))
        self.assertFalse(cpf_valido(None))

    def test_formatacao_e_limpeza(self):
        self.assertEqual(formatar_cpf("52998224725"), CPF_OK)
        self.assertEqual(limpar_cpf(CPF_OK), "52998224725")


class ConvidadosNaReservaTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(
            nome="Quadra Teste", slug="quadra-teste",
            antecedencia_max_dias=30, max_reservas_por_semana_por_usuario=5)
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="40", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")
        self.dia = timezone.localdate() + timedelta(days=2)

    def reservar(self, **extra):
        dados = {"data": self.dia.isoformat(), "hora_inicio": "10:00"}
        dados.update(extra)
        self.client.force_login(self.morador)
        return self.client.post(
            reverse("reservas:criar", args=[self.espaco.slug]), dados, follow=True)

    def test_grava_nome_e_cpf(self):
        self.reservar(convidado_nome=["Maria Souza"], convidado_cpf=[CPF_OK])
        c = Convidado.objects.get()
        self.assertEqual(c.nome, "MARIA SOUZA")  # tudo em maiusculo
        self.assertEqual(c.cpf, CPF_OK)

    def test_normaliza_cpf_sem_mascara(self):
        self.reservar(convidado_nome=["Maria"], convidado_cpf=["52998224725"])
        self.assertEqual(Convidado.objects.get().cpf, CPF_OK)

    def test_varios_convidados(self):
        self.reservar(convidado_nome=["Maria Souza", "Joao Lima"],
                      convidado_cpf=[CPF_OK, CPF_OK2])
        self.assertEqual(Convidado.objects.count(), 2)
        self.assertEqual(
            list(Convidado.objects.values_list("nome", flat=True)),
            ["MARIA SOUZA", "JOAO LIMA"])

    def test_cpf_e_obrigatorio(self):
        self.reservar(convidado_nome=["Maria Souza"], convidado_cpf=[""])
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(Convidado.objects.count(), 0)

    def test_cpf_so_com_espacos_e_recusado(self):
        self.reservar(convidado_nome=["Maria Souza"], convidado_cpf=["   "])
        self.assertEqual(Reserva.objects.count(), 0)

    def test_um_convidado_sem_cpf_derruba_a_reserva_toda(self):
        self.reservar(convidado_nome=["Maria Souza", "Joao Lima"],
                      convidado_cpf=[CPF_OK, ""])
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(Convidado.objects.count(), 0)

    def test_cpf_invalido_derruba_a_reserva_inteira(self):
        self.reservar(convidado_nome=["Maria"], convidado_cpf=["529.982.247-26"])
        self.assertEqual(Reserva.objects.count(), 0)
        self.assertEqual(Convidado.objects.count(), 0)

    def test_cpf_sem_nome_e_recusado(self):
        self.reservar(convidado_nome=[""], convidado_cpf=[CPF_OK])
        self.assertEqual(Reserva.objects.count(), 0)

    def test_linhas_em_branco_sao_ignoradas(self):
        """Linha totalmente vazia nao conta como convidado."""
        self.reservar(convidado_nome=["Maria", "", "  "], convidado_cpf=[CPF_OK, "", ""])
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(Convidado.objects.count(), 1)

    def test_excesso_de_convidados_e_recusado(self):
        self.reservar(convidado_nome=["Convidado %d" % i for i in range(25)],
                      convidado_cpf=[CPF_OK] * 25)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_reserva_sem_convidados_continua_funcionando(self):
        self.reservar()
        self.assertEqual(Reserva.objects.count(), 1)
        self.assertEqual(Convidado.objects.count(), 0)

    def test_campo_texto_antigo_fica_sincronizado(self):
        self.reservar(convidado_nome=["Maria Souza", "Joao Lima"],
                      convidado_cpf=[CPF_OK, CPF_OK2])
        self.assertEqual(Reserva.objects.get().convidados, "MARIA SOUZA\nJOAO LIMA")

    def test_convidado_sai_junto_com_a_reserva(self):
        self.reservar(convidado_nome=["Maria"], convidado_cpf=[CPF_OK])
        Reserva.objects.get().delete()
        self.assertEqual(Convidado.objects.count(), 0)


class FormularioConvidadosTest(TestCase):
    """A tela de reserva precisa deixar claro que o CPF e obrigatorio."""

    def setUp(self):
        self.espaco = Espaco.objects.create(nome="Quadra Teste", slug="quadra-teste")
        self.morador = Usuario.objects.create_user(
            username="morador9", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="99", first_name="Zeca")

    def test_nome_do_convidado_e_digitado_em_maiusculo(self):
        self.client.force_login(self.morador)
        r = self.client.get(reverse("reservas:calendario", args=[self.espaco.slug]))
        self.assertContains(r, "conv-maiusculo")
        self.assertContains(r, "toUpperCase")

    def test_calendario_avisa_que_cpf_e_obrigatorio(self):
        self.client.force_login(self.morador)
        r = self.client.get(reverse("reservas:calendario", args=[self.espaco.slug]))
        self.assertContains(r, "CPF sao obrigatorios")
        self.assertContains(r, "CPF (obrigatorio)")


class ConvidadosNasTelasTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(nome="Quadra Teste", slug="quadra-teste")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="50", first_name="Vigia", last_name="Noturno")
        self.moderador = Usuario.objects.create_user(
            username="mod1", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="51", first_name="Mod")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="52", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")
        self.reserva = Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco,
            data=timezone.localdate() + timedelta(days=1),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="confirmada")
        Convidado.objects.create(reserva=self.reserva, nome="Maria Souza", cpf=CPF_OK)

    def test_portaria_ve_nome_e_cpf(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:portaria"))
        self.assertContains(r, "Maria Souza")
        self.assertContains(r, CPF_OK)

    def test_painel_do_moderador_ve_nome_e_cpf(self):
        self.client.force_login(self.moderador)
        r = self.client.get(reverse("reservas:painel"))
        self.assertContains(r, "Maria Souza")
        self.assertContains(r, CPF_OK)

    def test_csv_traz_o_cpf(self):
        self.client.force_login(self.moderador)
        r = self.client.get(reverse("reservas:exportar_csv"))
        self.assertIn(CPF_OK, r.content.decode("utf-8"))


class HistoricoUsuarioTest(TestCase):
    def setUp(self):
        self.espaco = Espaco.objects.create(
            nome="Quadra Teste", slug="quadra-teste",
            max_reservas_por_semana_por_usuario=2)
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="60", first_name="Vigia", last_name="Noturno")
        self.moderador = Usuario.objects.create_user(
            username="mod1", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="61", first_name="Mod", last_name="Geral")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="62", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202", telefone="(35) 99999-0000")
        self.reserva = Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco, data=timezone.localdate(),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="confirmada")

    def url(self):
        return reverse("reservas:historico_usuario", args=[self.morador.pk])

    def test_portaria_e_moderador_acessam(self):
        for u in (self.portaria, self.moderador):
            self.client.force_login(u)
            r = self.client.get(self.url())
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "Zeca Silva")

    def test_morador_comum_nao_acessa_ficha_de_ninguem(self):
        self.client.force_login(self.morador)
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_anonimo_vai_para_login(self):
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_mostra_dados_do_morador_e_contadores(self):
        Reserva.objects.create(
            usuario=self.morador, espaco=self.espaco,
            data=timezone.localdate() - timedelta(days=10),
            hora_inicio=time(8, 0), hora_fim=time(9, 0), status="cancelada")
        self.client.force_login(self.portaria)
        r = self.client.get(self.url())
        self.assertEqual(r.context["total"], 2)
        self.assertEqual(r.context["total_confirmadas"], 1)
        self.assertEqual(r.context["total_canceladas"], 1)
        self.assertContains(r, "Apt 202")
        self.assertContains(r, "(35) 99999-0000")

    def test_historico_registra_quem_retirou_e_quem_entregou(self):
        self.client.force_login(self.portaria)
        self.client.post(reverse("reservas:kit_retirada", args=[self.reserva.pk]),
                         {"retirado_por": "Zeca Silva",
                          "entregue_por_vigia": "Joao da Guarita"})
        self.client.force_login(self.moderador)
        self.client.post(reverse("reservas:kit_devolucao", args=[self.reserva.pk]),
                         {"devolvido_por": "Maria Souza",
                          "recebido_por_vigia": "Pedro do Plantao",
                          "observacao": "tudo certo"})
        r = self.client.get(self.url())
        corpo = r.content.decode()
        self.assertIn("ZECA SILVA", corpo)          # quem retirou
        self.assertIn("MARIA SOUZA", corpo)         # quem devolveu
        self.assertIn("JOAO DA GUARITA", corpo)     # vigilante que entregou
        self.assertIn("PEDRO DO PLANTAO", corpo)    # vigilante que recebeu
        self.assertIn("conta Vigia Noturno", corpo)  # login usado na entrega
        self.assertIn("TUDO CERTO", corpo)
        self.assertEqual(r.context["total_kits"], 1)
        self.assertEqual(len(r.context["kits_pendentes"]), 0)

    def test_kit_sem_devolucao_aparece_como_pendente(self):
        KitJogo.objects.create(reserva=self.reserva, retirado_por="Zeca",
                               retirada_registrada_por=self.portaria)
        self.client.force_login(self.portaria)
        r = self.client.get(self.url())
        self.assertEqual(len(r.context["kits_pendentes"]), 1)
        self.assertContains(r, "sem devolucao registrada")

    def test_mostra_a_cota_da_semana(self):
        self.client.force_login(self.moderador)
        r = self.client.get(self.url())
        cota = r.context["cotas"][0]
        self.assertEqual(cota["limite"], 2)
        self.assertEqual(cota["usadas"], 1)
        self.assertEqual(cota["restantes"], 1)

    def test_convidados_aparecem_na_ficha(self):
        Convidado.objects.create(reserva=self.reserva, nome="Maria Souza", cpf=CPF_OK)
        self.client.force_login(self.portaria)
        r = self.client.get(self.url())
        self.assertContains(r, "Maria Souza")
        self.assertContains(r, CPF_OK)

    def test_paineis_linkam_para_a_ficha(self):
        self.client.force_login(self.portaria)
        self.assertContains(self.client.get(reverse("reservas:portaria")), self.url())
        self.client.force_login(self.moderador)
        self.assertContains(self.client.get(reverse("reservas:painel")), self.url())

    def test_usuario_inexistente_da_404(self):
        self.client.force_login(self.portaria)
        r = self.client.get(reverse("reservas:historico_usuario", args=[99999]))
        self.assertEqual(r.status_code, 404)
