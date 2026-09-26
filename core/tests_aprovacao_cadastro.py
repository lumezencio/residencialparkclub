"""Testes da trilha de quem liberou o cadastro do morador."""
from django.contrib.admin.sites import AdminSite
from django.db import connection
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.admin import UsuarioAdmin
from core.models import Usuario


class AprovacaoBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1",
            first_name="Luciano", last_name="Mezencio")
        self.moderadora = Usuario.objects.create_user(
            username="fernanda", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Fernanda")
        self.pendente = Usuario.objects.create_user(
            username="novato", password="Senha123!Forte", tipo="morador",
            aprovado=False, cpf="3", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")

    def aprovar(self, alvo=None):
        alvo = alvo or self.pendente
        return self.client.post(
            reverse("core:moderar_item", args=["usuario", alvo.pk]),
            {"acao": "aprovar"}, follow=True)


class RegistroDeQuemLiberouTest(AprovacaoBase):
    def test_moderadora_que_aprova_fica_registrada(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        self.pendente.refresh_from_db()
        self.assertTrue(self.pendente.aprovado)
        self.assertEqual(self.pendente.aprovado_por, self.moderadora)
        self.assertIsNotNone(self.pendente.aprovado_em)
        self.assertEqual(self.pendente.aprovado_por_nome, "Fernanda")

    def test_mensagem_diz_quem_aprovou(self):
        self.client.force_login(self.moderadora)
        r = self.aprovar()
        self.assertContains(r, "aprovado por Fernanda")

    def test_administrador_tambem_fica_registrado(self):
        self.client.force_login(self.admin)
        self.aprovar()
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.aprovado_por, self.admin)
        self.assertEqual(self.pendente.aprovado_por_nome, "Luciano Mezencio")

    def test_relacao_inversa_lista_os_cadastros_que_liberou(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        self.assertEqual(
            list(self.moderadora.cadastros_aprovados.all()), [self.pendente])

    def test_cadastro_criado_pelo_administrador_ja_nasce_com_a_trilha(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("core:criar_usuario"), {
            "username": "novo", "first_name": "Maria", "last_name": "Souza",
            "email": "", "cpf": "", "telefone": "", "bloco": "C",
            "apartamento": "101", "tipo": "morador", "password": "SenhaForte123!",
        }, follow=True)
        novo = Usuario.objects.get(username="novo")
        self.assertTrue(novo.aprovado)
        self.assertEqual(novo.aprovado_por, self.admin)
        self.assertIsNotNone(novo.aprovado_em)

    def test_rejeitar_limpa_a_trilha(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        self.client.post(reverse("core:moderar_item", args=["usuario", self.pendente.pk]),
                         {"acao": "rejeitar"}, follow=True)
        self.pendente.refresh_from_db()
        self.assertFalse(self.pendente.is_active)
        self.assertFalse(self.pendente.aprovado)
        self.assertIsNone(self.pendente.aprovado_por)
        self.assertIsNone(self.pendente.aprovado_em)

    def test_reaprovacao_grava_o_segundo_moderador(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        self.client.post(reverse("core:moderar_item", args=["usuario", self.pendente.pk]),
                         {"acao": "rejeitar"}, follow=True)
        self.client.force_login(self.admin)
        self.aprovar()
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.aprovado_por, self.admin)

    def test_quem_esta_na_fila_nao_tem_trilha(self):
        self.assertEqual(self.pendente.aprovado_por_nome, "")
        self.assertIsNone(self.pendente.aprovado_em)

    def test_cadastro_antigo_sem_registro_nao_quebra(self):
        """Quem foi aprovado antes deste controle fica sem trilha, e tudo bem."""
        antigo = Usuario.objects.create_user(
            username="antigo", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="9", first_name="Joao")
        self.assertIsNone(antigo.aprovado_por)
        self.assertEqual(antigo.aprovado_por_nome, "")

    def test_moderadora_removida_nao_apaga_o_morador(self):
        """SET_NULL: sai o moderador, fica o morador (sem a trilha)."""
        self.client.force_login(self.moderadora)
        self.aprovar()
        self.moderadora.delete()
        self.pendente.refresh_from_db()
        self.assertTrue(self.pendente.aprovado)
        self.assertIsNone(self.pendente.aprovado_por)


class SegurancaAprovacaoTest(AprovacaoBase):
    def test_morador_comum_nao_aprova_ninguem(self):
        outro = Usuario.objects.create_user(
            username="comum", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="4")
        self.client.force_login(outro)
        r = self.aprovar()
        self.assertEqual(r.status_code, 403)
        self.pendente.refresh_from_db()
        self.assertFalse(self.pendente.aprovado)

    def test_portaria_nao_aprova_ninguem(self):
        port = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="5")
        self.client.force_login(port)
        r = self.aprovar()
        self.assertEqual(r.status_code, 403)
        self.pendente.refresh_from_db()
        self.assertIsNone(self.pendente.aprovado_por)

    def test_anonimo_vai_para_o_login(self):
        r = self.aprovar()
        self.assertEqual(r.status_code, 200)  # follow ate a tela de login
        self.pendente.refresh_from_db()
        self.assertFalse(self.pendente.aprovado)


class AdminDjangoTest(AprovacaoBase):
    """O atalho de marcar `aprovado` na listagem do admin tambem grava a trilha."""

    def setUp(self):
        super().setUp()
        self.ma = UsuarioAdmin(Usuario, AdminSite())
        self.req = RequestFactory().post("/admin/")
        self.req.user = self.admin

    def test_save_model_preenche_quem_liberou(self):
        self.pendente.aprovado = True
        self.ma.save_model(self.req, self.pendente, None, True)
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.aprovado_por, self.admin)
        self.assertIsNotNone(self.pendente.aprovado_em)

    def test_save_model_limpa_ao_desmarcar(self):
        self.pendente.registrar_aprovacao(self.moderadora)
        self.pendente.aprovado = False
        self.ma.save_model(self.req, self.pendente, None, True)
        self.pendente.refresh_from_db()
        self.assertIsNone(self.pendente.aprovado_por)
        self.assertIsNone(self.pendente.aprovado_em)

    def test_save_model_nao_sobrescreve_registro_existente(self):
        self.pendente.registrar_aprovacao(self.moderadora)
        self.ma.save_model(self.req, self.pendente, None, True)
        self.pendente.refresh_from_db()
        self.assertEqual(self.pendente.aprovado_por, self.moderadora)

    def test_colunas_html_do_admin_nao_quebram(self):
        """Regressao: format_html sem argumento estoura no Django 6."""
        from django.contrib.admin.sites import site as admin_site
        from core.models import SuspensaoMorador
        from reservas.models import KitJogo

        susp = SuspensaoMorador(usuario=self.pendente, inicio=None, ativa=False)
        self.assertIn("encerrada", admin_site._registry[SuspensaoMorador].em_vigor_badge(susp))
        kit = KitJogo(retirado_por="ZECA")
        self.assertIn("EM USO", admin_site._registry[KitJogo].situacao(kit))
        kit.devolvido_em = self.pendente.date_joined
        self.assertIn("DEVOLVIDO", admin_site._registry[KitJogo].situacao(kit))

    def test_coluna_da_listagem(self):
        self.assertIn("nao registrado", self.ma.liberado_por(
            Usuario(aprovado=True)))
        self.pendente.registrar_aprovacao(self.moderadora)
        self.assertIn("Fernanda", self.ma.liberado_por(self.pendente))


class TelasTest(AprovacaoBase):
    def test_painel_de_moderacao_mostra_quem_liberou(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "Liberado por")
        self.assertContains(r, "Fernanda")

    def test_painel_avisa_quando_nao_ha_registro(self):
        Usuario.objects.create_user(
            username="antigo", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="9", first_name="Joao")
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "sem registro")

    def test_ficha_do_morador_mostra_quem_liberou(self):
        self.client.force_login(self.moderadora)
        self.aprovar()
        r = self.client.get(
            reverse("reservas:historico_usuario", args=[self.pendente.pk]))
        self.assertContains(r, "Cadastro liberado por Fernanda")

    def criar_moradores(self, quantos, inicio=0):
        for i in range(inicio, inicio + quantos):
            u = Usuario.objects.create_user(
                username=f"m{i}", password="Senha123!Forte", tipo="morador",
                aprovado=True, cpf=f"90{i}", first_name=f"Morador{i}")
            u.registrar_aprovacao(self.moderadora)

    def test_quem_liberou_nao_gera_uma_consulta_por_morador(self):
        """select_related: o custo do painel nao cresce com a lista."""
        self.client.force_login(self.moderadora)
        self.criar_moradores(2)
        with CaptureQueriesContext(connection) as poucos:
            self.client.get(reverse("core:moderacao"))
        self.criar_moradores(10, inicio=100)
        with CaptureQueriesContext(connection) as muitos:
            r = self.client.get(reverse("core:moderacao"))

        # 5 moradores a mais nao podem custar 5 consultas a mais
        self.assertLessEqual(len(muitos), len(poucos) + 1)
        self.assertGreaterEqual(r.content.decode().count("Liberado por"), 12)
