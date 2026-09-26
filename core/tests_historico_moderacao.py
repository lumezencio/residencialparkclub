"""Testes do historico da moderacao e da edicao do cadastro do morador."""
from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import MidiaCondominio, RegistroModeracao, Usuario
from reservas.models import Espaco, Reserva


class BaseModeracao(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1",
            first_name="Luciano", last_name="Mezencio")
        self.moderadora = Usuario.objects.create_user(
            username="fernanda", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Fernanda")
        self.morador = Usuario.objects.create_user(
            username="zeca", password="Senha123!Forte", tipo="morador",
            aprovado=False, cpf="3", first_name="Zeca", last_name="Silva",
            bloco="B", apartamento="202")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="4", first_name="Vigia")


class RegistroDeAcoesTest(BaseModeracao):
    def acao_usuario(self, acao, alvo=None):
        return self.client.post(
            reverse("core:moderar_item", args=["usuario", (alvo or self.morador).pk]),
            {"acao": acao}, follow=True)

    def test_aprovacao_entra_no_historico(self):
        self.client.force_login(self.moderadora)
        self.acao_usuario("aprovar")
        r = RegistroModeracao.objects.get()
        self.assertEqual(r.acao, "cadastro_aprovado")
        self.assertEqual(r.moderador, self.moderadora)
        self.assertEqual(r.moderador_nome, "Fernanda")
        self.assertEqual(r.alvo_usuario, self.morador)
        self.assertEqual(r.alvo_nome, "Zeca Silva")

    def test_rejeicao_entra_no_historico(self):
        self.client.force_login(self.moderadora)
        self.acao_usuario("rejeitar")
        self.assertEqual(RegistroModeracao.objects.get().acao, "cadastro_rejeitado")

    def test_promocao_e_rebaixamento(self):
        self.client.force_login(self.admin)
        self.acao_usuario("promover_moderador")
        self.acao_usuario("rebaixar_moderador")
        acoes = list(RegistroModeracao.objects.order_by("criado_em").values_list("acao", flat=True))
        self.assertEqual(acoes, ["promovido_moderador", "rebaixado_morador"])

    def test_senha_redefinida_entra_no_historico(self):
        self.client.force_login(self.moderadora)
        self.client.post(reverse("core:redefinir_senha_usuario", args=[self.morador.pk]),
                         follow=True)
        r = RegistroModeracao.objects.get()
        self.assertEqual(r.acao, "senha_redefinida")
        self.assertIn("gerada", r.descricao)

    def test_suspensao_e_remocao_entram_no_historico(self):
        self.client.force_login(self.moderadora)
        self.client.post(reverse("core:suspender_morador", args=[self.morador.pk]),
                         {"motivo": "Barulho excessivo", "bloq_reservas": "on"}, follow=True)
        self.client.post(reverse("core:remover_suspensao_morador", args=[self.morador.pk]),
                         follow=True)
        acoes = list(RegistroModeracao.objects.order_by("criado_em").values_list("acao", flat=True))
        self.assertEqual(acoes, ["suspensao_aplicada", "suspensao_removida"])
        aplicada = RegistroModeracao.objects.get(acao="suspensao_aplicada")
        self.assertIn("Barulho excessivo", aplicada.descricao)

    def test_limite_de_reservas_entra_no_historico(self):
        espaco = Espaco.objects.create(nome="Quadra", slug="quadra")
        self.client.force_login(self.moderadora)
        self.client.post(reverse("core:definir_limite_reservas", args=[self.morador.pk]),
                         {"espaco": espaco.pk, "max_por_semana": 5}, follow=True)
        self.client.post(reverse("core:definir_limite_reservas", args=[self.morador.pk]),
                         {"espaco": espaco.pk, "acao": "padrao"}, follow=True)
        acoes = list(RegistroModeracao.objects.order_by("criado_em").values_list("acao", flat=True))
        self.assertEqual(acoes, ["limite_definido", "limite_removido"])

    def test_criacao_de_usuario_entra_no_historico(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("core:criar_usuario"), {
            "username": "novo", "first_name": "Maria", "last_name": "", "email": "",
            "cpf": "", "telefone": "", "bloco": "C", "apartamento": "10",
            "tipo": "morador", "password": "SenhaForte123!",
        }, follow=True)
        r = RegistroModeracao.objects.get(acao="cadastro_criado")
        self.assertEqual(r.alvo_nome, "Maria")
        self.assertEqual(r.moderador, self.admin)

    def test_exclusao_de_midia_entra_no_historico(self):
        midia = MidiaCondominio.objects.create(
            titulo="Foto antiga", tipo="foto", categoria="condominio",
            arquivo="condominio/x.jpg", ativo=True)
        self.client.force_login(self.moderadora)
        self.client.post(reverse("core:excluir_midia", args=[midia.pk]), follow=True)
        r = RegistroModeracao.objects.get()
        self.assertEqual(r.acao, "midia_excluida")
        self.assertIn("Foto antiga", r.descricao)

    def test_cancelamento_de_reserva_pelo_moderador(self):
        espaco = Espaco.objects.create(nome="Quadra", slug="quadra")
        reserva = Reserva.objects.create(
            usuario=self.morador, espaco=espaco,
            data=timezone.localdate() + timedelta(days=1),
            hora_inicio=time(9, 0), hora_fim=time(10, 0), status="confirmada")
        self.client.force_login(self.moderadora)
        self.client.post(reverse("reservas:cancelar", args=[reserva.pk]),
                         {"motivo": "Manutencao"}, follow=True)
        r = RegistroModeracao.objects.get()
        self.assertEqual(r.acao, "reserva_cancelada")
        self.assertEqual(r.alvo_usuario, self.morador)
        self.assertIn("Manutencao", r.descricao)

    def test_nome_sobrevive_a_exclusao_da_conta_do_moderador(self):
        self.client.force_login(self.moderadora)
        self.acao_usuario("aprovar")
        self.moderadora.delete()
        r = RegistroModeracao.objects.get()
        self.assertIsNone(r.moderador)
        self.assertEqual(r.moderador_nome, "Fernanda")  # historico nao se perde

    def test_acoes_sensiveis_sao_marcadas(self):
        self.client.force_login(self.moderadora)
        self.acao_usuario("aprovar")
        self.assertFalse(RegistroModeracao.objects.get().sensivel)
        RegistroModeracao.objects.all().delete()
        self.acao_usuario("rejeitar")
        self.assertTrue(RegistroModeracao.objects.get().sensivel)


class TelaHistoricoTest(BaseModeracao):
    def setUp(self):
        super().setUp()
        RegistroModeracao.registrar("cadastro_aprovado", self.moderadora, self.morador)
        RegistroModeracao.registrar("senha_redefinida", self.admin, self.morador, "Senha gerada")

    def test_moderador_ve_o_historico(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:historico_moderacao"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total"], 2)
        self.assertContains(r, "Fernanda")
        self.assertContains(r, "Zeca Silva")

    def test_filtro_por_moderador(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:historico_moderacao"),
                            {"moderador": self.admin.pk})
        self.assertEqual(r.context["total"], 1)
        self.assertEqual(r.context["registros"][0].moderador, self.admin)

    def test_filtro_por_acao(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:historico_moderacao"),
                            {"acao": "senha_redefinida"})
        self.assertEqual(r.context["total"], 1)

    def test_busca_por_texto(self):
        self.client.force_login(self.moderadora)
        self.assertEqual(
            self.client.get(reverse("core:historico_moderacao"),
                            {"q": "Zeca"}).context["total"], 2)
        self.assertEqual(
            self.client.get(reverse("core:historico_moderacao"),
                            {"q": "inexistente"}).context["total"], 0)

    def test_filtro_invalido_nao_quebra(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:historico_moderacao"),
                            {"moderador": "abc", "acao": "nao_existe"})
        self.assertEqual(r.status_code, 200)

    def test_painel_mostra_as_ultimas_acoes(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, "Histórico da moderação")
        self.assertContains(r, "Senha redefinida")
        self.assertEqual(r.context["total_registros"], 2)

    def test_morador_comum_nao_acessa(self):
        outro = Usuario.objects.create_user(
            username="comum", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="7")
        self.client.force_login(outro)
        self.assertEqual(
            self.client.get(reverse("core:historico_moderacao")).status_code, 403)

    def test_portaria_nao_acessa(self):
        self.client.force_login(self.portaria)
        self.assertEqual(
            self.client.get(reverse("core:historico_moderacao")).status_code, 403)


class EditarCadastroTest(BaseModeracao):
    def url(self, alvo=None):
        return reverse("core:editar_morador", args=[(alvo or self.morador).pk])

    def dados(self, **extra):
        """Espelha o cadastro atual do morador: so muda o que o teste passar."""
        base = {"username": "zeca", "first_name": "Zeca", "last_name": "Silva",
                "email": "", "cpf": "3", "telefone": "", "bloco": "B",
                "apartamento": "202"}
        base.update(extra)
        return base

    def test_tela_mostra_o_login_da_pessoa(self):
        self.client.force_login(self.moderadora)
        html = self.client.get(self.url()).content.decode()
        self.assertIn("Entra no sistema como", html)
        self.assertIn("Nome de usuário (login)", html)
        self.assertIn('name="username"', html)
        self.assertIn("zeca", html)

    def test_moderador_corrige_o_login(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(username="zeca.silva"), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.username, "zeca.silva")

    def test_troca_de_login_entra_no_historico(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(username="zeca.silva"), follow=True)
        r = RegistroModeracao.objects.get(acao="cadastro_editado")
        self.assertIn("login", r.descricao)

    def test_login_repetido_e_recusado(self):
        Usuario.objects.create_user(
            username="ocupado", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="77")
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(username="ocupado"), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.username, "zeca")

    def test_login_vazio_e_recusado(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(username="   "), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.username, "zeca")

    def test_login_novo_funciona_para_entrar(self):
        self.client.force_login(self.moderadora)
        self.morador.set_password("SenhaDoZeca123!")
        self.morador.save()
        self.client.post(self.url(), self.dados(username="zeca.novo"), follow=True)
        self.client.logout()
        self.assertTrue(
            self.client.login(username="zeca.novo", password="SenhaDoZeca123!"))

    def test_tela_tem_saida_visivel_em_mais_de_um_ponto(self):
        """Pagina longa: precisa de volta no topo, no formulario e no fim."""
        self.client.force_login(self.moderadora)
        html = self.client.get(self.url()).content.decode()
        painel = reverse("core:painel_moradores")
        self.assertGreaterEqual(html.count(painel), 3)
        self.assertIn("Sair sem salvar", html)
        self.assertIn("Voltar ao painel de moradores", html)
        self.assertIn(reverse("core:moderacao"), html)

    def test_moderador_abre_o_cadastro(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Zeca Silva")
        self.assertContains(r, "Corrigir dados")

    def test_moderador_corrige_dados(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(
            telefone="(35) 99999-1234", apartamento="305"), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.telefone, "(35) 99999-1234")
        self.assertEqual(self.morador.apartamento, "305")

    def test_alteracao_entra_no_historico_com_os_campos(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(telefone="(35) 98888-0000"), follow=True)
        r = RegistroModeracao.objects.get(acao="cadastro_editado")
        self.assertEqual(r.moderador, self.moderadora)
        self.assertEqual(r.alvo_usuario, self.morador)
        self.assertIn("telefone", r.descricao)

    def test_salvar_sem_mudar_nada_nao_polui_o_historico(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(), follow=True)
        self.assertFalse(RegistroModeracao.objects.filter(acao="cadastro_editado").exists())

    def test_cpf_em_branco_nao_colide_entre_moradores(self):
        outro = Usuario.objects.create_user(
            username="outro", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf=None, first_name="Ana")
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(cpf=""), follow=True)
        self.morador.refresh_from_db()
        self.assertIsNone(self.morador.cpf)
        self.assertIsNone(Usuario.objects.get(pk=outro.pk).cpf)

    def test_nome_em_branco_e_recusado(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(first_name=""), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.first_name, "Zeca")

    def test_tela_mostra_o_historico_da_pessoa(self):
        RegistroModeracao.registrar("suspensao_aplicada", self.admin, self.morador,
                                    "Ate 01/01. Motivo: teste")
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url())
        self.assertContains(r, "Suspensao aplicada")
        self.assertContains(r, "Motivo: teste")
        self.assertEqual(len(r.context["historico"]), 1)

    def test_historico_da_tela_e_so_da_pessoa(self):
        outro = Usuario.objects.create_user(
            username="outro", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="8", first_name="Ana")
        RegistroModeracao.registrar("cadastro_aprovado", self.admin, outro)
        self.client.force_login(self.moderadora)
        self.assertEqual(len(self.client.get(self.url()).context["historico"]), 0)

    def test_tipo_e_aprovacao_nao_sao_editaveis_por_aqui(self):
        self.client.force_login(self.moderadora)
        self.client.post(self.url(), self.dados(
            tipo="admin", aprovado="on", is_superuser="on"), follow=True)
        self.morador.refresh_from_db()
        self.assertEqual(self.morador.tipo, "morador")
        self.assertFalse(self.morador.aprovado)
        self.assertFalse(self.morador.is_superuser)

    def test_moderador_comum_nao_edita_outro_moderador(self):
        outra_mod = Usuario.objects.create_user(
            username="mod2", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="9", first_name="Outra")
        self.client.force_login(self.moderadora)
        r = self.client.post(self.url(outra_mod),
                             self.dados(username="mod2", first_name="Hackeada",
                                        cpf="9"), follow=True)
        outra_mod.refresh_from_db()
        self.assertEqual(outra_mod.first_name, "Outra")
        self.assertContains(r, "Somente o administrador")

    def test_superadmin_edita_moderador(self):
        outra_mod = Usuario.objects.create_user(
            username="mod2", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="9", first_name="Outra")
        self.client.force_login(self.admin)
        self.client.post(self.url(outra_mod),
                         self.dados(username="mod2", first_name="Outra",
                                    last_name="", cpf="9",
                                    telefone="(35) 90000-0000"),
                         follow=True)
        outra_mod.refresh_from_db()
        self.assertEqual(outra_mod.telefone, "(35) 90000-0000")

    def test_morador_comum_nao_abre_cadastro_de_ninguem(self):
        outro = Usuario.objects.create_user(
            username="comum", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="7")
        self.client.force_login(outro)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.post(self.url(), self.dados()).status_code, 403)

    def test_portaria_nao_abre_cadastro(self):
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_anonimo_vai_para_o_login(self):
        r = self.client.get(self.url())
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_painel_linka_para_o_cadastro(self):
        self.morador.registrar_aprovacao(self.moderadora)
        self.client.force_login(self.moderadora)
        r = self.client.get(reverse("core:moderacao"))
        self.assertContains(r, self.url())
        self.assertContains(r, "Abrir cadastro")
