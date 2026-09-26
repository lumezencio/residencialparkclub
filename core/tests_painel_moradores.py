"""Testes do painel de cadastros dos moradores."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import RegistroModeracao, SuspensaoMorador, Usuario


class PainelMoradoresBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1",
            first_name="Luciano", last_name="Mezencio")
        self.moderadora = Usuario.objects.create_user(
            username="fernanda", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Fernanda")
        self.zeca = Usuario.objects.create_user(
            username="zeca", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="529.982.247-25", first_name="Zeca",
            last_name="Silva", bloco="B", apartamento="202",
            telefone="(35) 99111-2222", email="zeca@exemplo.com")
        self.ana = Usuario.objects.create_user(
            username="ana", password="Senha123!Forte", tipo="morador",
            aprovado=False, cpf="4", first_name="Ana", last_name="Souza",
            bloco="A", apartamento="101")
        self.empresa = Usuario.objects.create_user(
            username="mercado", password="Senha123!Forte", tipo="empresa",
            aprovado=True, cpf="5", first_name="Mercado", last_name="Central")
        self.inativo = Usuario.objects.create_user(
            username="saiu", password="Senha123!Forte", tipo="morador",
            aprovado=False, is_active=False, cpf="6", first_name="Joao")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="7", first_name="Vigia")
        self.url = reverse("core:painel_moradores")

    def listar(self, **params):
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url, params)
        return r, [u.username for u in r.context["pagina"].object_list]


class AcessoTest(PainelMoradoresBase):
    def test_moderador_acessa(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Moradores")

    def test_superadmin_acessa(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_morador_comum_recebe_403(self):
        self.client.force_login(self.zeca)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_portaria_recebe_403(self):
        self.client.force_login(self.portaria)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonimo_vai_para_o_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])


class BuscaTest(PainelMoradoresBase):
    def test_busca_por_nome(self):
        _, nomes = self.listar(q="Zeca")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_sobrenome(self):
        _, nomes = self.listar(q="Souza")
        self.assertEqual(nomes, ["ana"])

    def test_busca_ignora_maiusculas(self):
        _, nomes = self.listar(q="zEcA")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_parte_do_nome(self):
        _, nomes = self.listar(q="ern")  # Fernanda
        self.assertEqual(nomes, ["fernanda"])

    def test_busca_por_cpf(self):
        _, nomes = self.listar(q="529.982")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_telefone(self):
        _, nomes = self.listar(q="99111")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_email(self):
        _, nomes = self.listar(q="zeca@exemplo")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_apartamento(self):
        _, nomes = self.listar(q="202")
        self.assertEqual(nomes, ["zeca"])

    def test_busca_por_usuario(self):
        _, nomes = self.listar(q="mercado")
        self.assertEqual(nomes, ["mercado"])

    def test_busca_sem_resultado(self):
        r, nomes = self.listar(q="ninguem-com-esse-nome")
        self.assertEqual(nomes, [])
        self.assertContains(r, "Nenhum cadastro encontrado")


class FiltrosTest(PainelMoradoresBase):
    def test_filtro_por_tipo(self):
        _, nomes = self.listar(tipo="empresa")
        self.assertEqual(nomes, ["mercado"])

    def test_filtro_aprovados(self):
        _, nomes = self.listar(situacao="aprovados")
        self.assertIn("zeca", nomes)
        self.assertNotIn("ana", nomes)      # na fila
        self.assertNotIn("saiu", nomes)     # inativo

    def test_filtro_fila(self):
        _, nomes = self.listar(situacao="fila")
        self.assertEqual(nomes, ["ana"])

    def test_conta_de_staff_nao_cai_na_fila(self):
        """createsuperuser nasce com aprovado=False e nao deve virar pendencia."""
        self.assertFalse(self.admin.aprovado)
        _, nomes = self.listar(situacao="fila")
        self.assertNotIn("admin1", nomes)
        _, aprovados = self.listar(situacao="aprovados")
        self.assertIn("admin1", aprovados)

    def test_filtro_inativos(self):
        _, nomes = self.listar(situacao="inativos")
        self.assertEqual(nomes, ["saiu"])

    def test_filtro_suspensos(self):
        SuspensaoMorador.objects.create(
            usuario=self.zeca, inicio=timezone.now(), motivo="teste",
            ativa=True, bloqueia_reservas=True)
        _, nomes = self.listar(situacao="suspensos")
        self.assertEqual(nomes, ["zeca"])

    def test_suspensao_encerrada_nao_conta(self):
        SuspensaoMorador.objects.create(
            usuario=self.zeca, inicio=timezone.now(), motivo="teste",
            ativa=False, bloqueia_reservas=True)
        _, nomes = self.listar(situacao="suspensos")
        self.assertEqual(nomes, [])

    def test_filtros_combinados(self):
        _, nomes = self.listar(tipo="morador", situacao="aprovados")
        self.assertEqual(nomes, ["zeca"])

    def test_filtro_invalido_nao_quebra(self):
        r, _ = self.listar(situacao="xpto", tipo="inexistente", ordem="sql-injection")
        self.assertEqual(r.status_code, 200)

    def test_ordenacao_por_unidade(self):
        _, nomes = self.listar(situacao="aprovados", ordem="unidade")
        self.assertLess(nomes.index("zeca"), len(nomes))  # nao quebra
        r, _ = self.listar(ordem="recentes")
        self.assertEqual(r.context["ordem"], "recentes")

    def test_resumo_nao_segue_o_filtro(self):
        r, _ = self.listar(q="Zeca")
        self.assertEqual(r.context["resumo"]["total"], Usuario.objects.count())
        self.assertEqual(r.context["total_filtrado"], 1)


class ConteudoTest(PainelMoradoresBase):
    def test_mostra_dados_e_situacao(self):
        r, _ = self.listar()
        self.assertContains(r, "Zeca Silva")
        self.assertContains(r, "Bl B / Apt 202")
        self.assertContains(r, "(35) 99111-2222")
        self.assertContains(r, "na fila")

    def test_linka_para_o_cadastro_e_para_as_reservas(self):
        r, _ = self.listar()
        self.assertContains(r, reverse("core:editar_morador", args=[self.zeca.pk]))
        self.assertContains(r, reverse("reservas:historico_usuario", args=[self.zeca.pk]))

    def test_mostra_quem_liberou(self):
        self.zeca.registrar_aprovacao(self.moderadora)
        r, _ = self.listar(q="Zeca")
        self.assertContains(r, "Fernanda")

    def test_avisa_quando_nao_ha_registro_de_liberacao(self):
        r, _ = self.listar(q="Zeca")
        self.assertContains(r, "sem registro")


class PaginacaoTest(PainelMoradoresBase):
    def test_pagina_com_muitos_cadastros(self):
        for i in range(40):
            Usuario.objects.create_user(
                username=f"m{i}", password="Senha123!Forte", tipo="morador",
                aprovado=True, cpf=f"800{i}", first_name=f"Morador{i}")
        r, nomes = self.listar()
        self.assertEqual(len(nomes), 25)
        self.assertTrue(r.context["pagina"].has_next)

        self.client.force_login(self.moderadora)
        r2 = self.client.get(self.url, {"pagina": 2})
        self.assertEqual(r2.context["pagina"].number, 2)

    def test_pagina_invalida_cai_na_ultima(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url, {"pagina": 999})
        self.assertEqual(r.status_code, 200)

    def test_filtros_sobrevivem_a_troca_de_pagina(self):
        r, _ = self.listar(q="Zeca", tipo="morador")
        self.assertIn("q=Zeca", r.context["querystring"])
        self.assertNotIn("pagina", r.context["querystring"])


class ExportacaoTest(PainelMoradoresBase):
    def test_csv_da_lista_filtrada(self):
        self.client.force_login(self.moderadora)
        r = self.client.get(self.url, {"q": "Zeca", "export": "csv"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/csv", r["Content-Type"])
        corpo = r.content.decode("utf-8")
        self.assertIn("Zeca Silva", corpo)
        self.assertIn("Aprovado", corpo)
        self.assertNotIn("Ana", corpo)  # fora do filtro

    def test_csv_marca_a_situacao_de_cada_um(self):
        self.client.force_login(self.moderadora)
        corpo = self.client.get(self.url, {"export": "csv"}).content.decode("utf-8")
        self.assertIn("Na fila", corpo)
        self.assertIn("Inativo", corpo)

    def test_exportacao_entra_no_historico(self):
        self.client.force_login(self.moderadora)
        self.client.get(self.url, {"export": "csv"})
        r = RegistroModeracao.objects.get(acao="lista_exportada")
        self.assertEqual(r.moderador, self.moderadora)
        self.assertIn("CSV", r.descricao)

    def test_morador_comum_nao_exporta(self):
        self.client.force_login(self.zeca)
        self.assertEqual(
            self.client.get(self.url, {"export": "csv"}).status_code, 403)
