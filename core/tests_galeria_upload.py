"""Testes do envio de fotos e videos da galeria (exclusivo da moderacao)."""
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import MidiaCondominio, Usuario


def foto(nome="quadra.jpg", tamanho=64):
    return SimpleUploadedFile(nome, b"x" * tamanho, content_type="image/jpeg")


def video(nome="festa.mp4", tamanho=64):
    return SimpleUploadedFile(nome, b"x" * tamanho, content_type="video/mp4")


class GaleriaUploadBase(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            username="admin1", password="AdminSenha123!", tipo="admin", cpf="1")
        self.moderador = Usuario.objects.create_user(
            username="mod1", password="Senha123!Forte", tipo="moderador",
            is_staff=True, aprovado=True, cpf="2", first_name="Mod")
        self.morador = Usuario.objects.create_user(
            username="morador1", password="Senha123!Forte", tipo="morador",
            aprovado=True, cpf="3", first_name="Zeca")
        self.portaria = Usuario.objects.create_user(
            username="portaria1", password="Senha123!Forte", tipo="portaria",
            aprovado=True, cpf="4", first_name="Vigia")

    def enviar(self, arquivos=None, categoria="condominio", **extra):
        dados = {"categoria": categoria, "titulo": "", "descricao": ""}
        dados.update(extra)
        dados["arquivos"] = arquivos if arquivos is not None else [foto()]
        return self.client.post(reverse("core:galeria"), dados, follow=True)


class UploadMidiaFormTest(TestCase):
    """Regressao: o formulario rejeitava a lista do widget e nada era enviado."""

    def test_form_aceita_varios_arquivos(self):
        from core.forms import UploadMidiaForm
        form = UploadMidiaForm(
            {"categoria": "condominio", "titulo": "", "descricao": ""},
            {"arquivos": [foto("a.jpg"), foto("b.jpg")]},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["arquivos"]), 2)

    def test_form_aceita_um_arquivo_so(self):
        from core.forms import UploadMidiaForm
        form = UploadMidiaForm(
            {"categoria": "condominio"}, {"arquivos": [foto()]})
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_exige_pelo_menos_um_arquivo(self):
        from core.forms import UploadMidiaForm
        form = UploadMidiaForm({"categoria": "condominio"}, {})
        self.assertFalse(form.is_valid())
        self.assertIn("arquivos", form.errors)


class QuemPodeEnviarTest(GaleriaUploadBase):
    def test_moderador_ve_o_formulario(self):
        self.client.force_login(self.moderador)
        r = self.client.get(reverse("core:galeria"))
        self.assertTrue(r.context["pode_enviar"])
        self.assertContains(r, "Enviar Fotos")
        self.assertContains(r, "plano de fundo")

    def test_superadmin_ve_o_formulario(self):
        self.client.force_login(self.admin)
        self.assertTrue(self.client.get(reverse("core:galeria")).context["pode_enviar"])

    def test_morador_comum_nao_ve_o_formulario(self):
        self.client.force_login(self.morador)
        r = self.client.get(reverse("core:galeria"))
        self.assertFalse(r.context["pode_enviar"])
        self.assertNotContains(r, "Enviar Fotos")
        self.assertNotContains(r, "upload-dropzone")

    def test_portaria_nao_ve_o_formulario(self):
        self.client.force_login(self.portaria)
        self.assertFalse(self.client.get(reverse("core:galeria")).context["pode_enviar"])

    def test_morador_comum_recebe_403_ao_forcar_o_envio(self):
        self.client.force_login(self.morador)
        r = self.client.post(reverse("core:galeria"),
                             {"categoria": "condominio", "arquivos": [foto()]})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(MidiaCondominio.objects.count(), 0)

    def test_portaria_recebe_403_ao_forcar_o_envio(self):
        self.client.force_login(self.portaria)
        r = self.client.post(reverse("core:galeria"),
                             {"categoria": "condominio", "arquivos": [foto()]})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(MidiaCondominio.objects.count(), 0)

    def test_anonimo_vai_para_o_login(self):
        r = self.client.post(reverse("core:galeria"),
                             {"categoria": "condominio", "arquivos": [foto()]})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])
        self.assertEqual(MidiaCondominio.objects.count(), 0)


class EnvioDeMidiasTest(GaleriaUploadBase):
    def test_foto_entra_ativa_na_hora(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("piscina.jpg")])
        m = MidiaCondominio.objects.get()
        self.assertEqual(m.tipo, "foto")
        self.assertEqual(m.categoria, "condominio")
        self.assertTrue(m.ativo)  # sem fila de aprovacao

    def test_video_tambem_e_aceito(self):
        self.client.force_login(self.moderador)
        self.enviar([video("drone.mp4")])
        self.assertEqual(MidiaCondominio.objects.get().tipo, "video")

    def test_varios_arquivos_de_uma_vez(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("a.jpg"), foto("b.png"), video("c.mp4")])
        self.assertEqual(MidiaCondominio.objects.count(), 3)

    def test_categoria_projetos_futuros(self):
        self.client.force_login(self.moderador)
        self.enviar([foto()], categoria="projetos_futuros")
        self.assertEqual(MidiaCondominio.objects.get().categoria, "projetos_futuros")

    def test_titulo_e_descricao_sao_guardados(self):
        self.client.force_login(self.moderador)
        self.enviar([foto()], titulo="Area de lazer", descricao="Reforma 2026")
        m = MidiaCondominio.objects.get()
        self.assertEqual(m.titulo, "Area de lazer")
        self.assertEqual(m.descricao, "Reforma 2026")

    def test_formato_nao_aceito_e_recusado(self):
        self.client.force_login(self.moderador)
        r = self.enviar([SimpleUploadedFile("planilha.xlsx", b"x", content_type="app/x")])
        self.assertEqual(MidiaCondominio.objects.count(), 0)
        self.assertContains(r, "formato nao aceito")

    def test_executavel_disfarcado_nao_passa(self):
        self.client.force_login(self.moderador)
        self.enviar([SimpleUploadedFile("virus.exe", b"MZ", content_type="image/jpeg")])
        self.assertEqual(MidiaCondominio.objects.count(), 0)

    @patch("core.views.LIMITE_FOTO_MB", 1)
    def test_foto_acima_do_limite_e_recusada(self):
        self.client.force_login(self.moderador)
        grande = foto("enorme.jpg", tamanho=1024 * 1024 + 10)
        r = self.enviar([grande])
        self.assertEqual(MidiaCondominio.objects.count(), 0)
        self.assertContains(r, "passa de 1 MB")

    @patch("core.views.LIMITE_FOTO_MB", 1)
    def test_arquivo_grande_nao_impede_os_demais(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("ok.jpg"), foto("enorme.jpg", tamanho=1024 * 1024 + 10)])
        self.assertEqual(MidiaCondominio.objects.count(), 1)

    @patch("core.views.MAX_ARQUIVOS_POR_ENVIO", 3)
    def test_respeita_o_maximo_por_envio(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("%d.jpg" % i) for i in range(6)])
        self.assertEqual(MidiaCondominio.objects.count(), 3)

    def test_envio_sem_arquivo_nao_cria_nada(self):
        self.client.force_login(self.moderador)
        self.client.post(reverse("core:galeria"),
                         {"categoria": "condominio"}, follow=True)
        self.assertEqual(MidiaCondominio.objects.count(), 0)


class MidiaNovaApareceTest(GaleriaUploadBase):
    """A midia enviada tem que entrar na galeria e no sorteio do plano de fundo."""

    def test_aparece_na_galeria_para_todo_morador(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("nova.jpg")], titulo="Quadra nova")
        self.client.force_login(self.morador)
        r = self.client.get(reverse("core:galeria"))
        self.assertIn(MidiaCondominio.objects.get(), list(r.context["fotos_cond"]))

    def test_entra_no_sorteio_do_plano_de_fundo(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("fundo.jpg")])
        midia = MidiaCondominio.objects.get()
        r = self.client.get(reverse("core:home"))
        self.assertIn(midia, list(r.context["hero_midias"]))
        self.assertIn(midia, list(r.context["todas_midias"]))

    def test_projetos_futuros_nao_vao_para_o_plano_de_fundo(self):
        self.client.force_login(self.moderador)
        self.enviar([foto("obra.jpg")], categoria="projetos_futuros")
        midia = MidiaCondominio.objects.get()
        r = self.client.get(reverse("core:home"))
        self.assertNotIn(midia, list(r.context["hero_midias"]))
        self.assertIn(midia, list(r.context["midias_futuro"]))

    def test_soma_as_midias_que_ja_existiam(self):
        antiga = MidiaCondominio.objects.create(
            titulo="Antiga", tipo="foto", categoria="condominio",
            arquivo="condominio/antiga.jpg", ativo=True)
        self.client.force_login(self.moderador)
        self.enviar([foto("nova.jpg")])
        r = self.client.get(reverse("core:home"))
        nova = MidiaCondominio.objects.exclude(pk=antiga.pk).get()
        self.assertEqual(len(r.context["todas_midias"]), 2)
        self.assertIn(antiga, list(r.context["todas_midias"]))
        self.assertIn(nova, list(r.context["todas_midias"]))


class ExclusaoDeMidiaTest(GaleriaUploadBase):
    def setUp(self):
        super().setUp()
        self.midia = MidiaCondominio.objects.create(
            titulo="Foto", tipo="foto", categoria="condominio",
            arquivo="condominio/foto.jpg", ativo=True)

    def test_moderador_exclui(self):
        self.client.force_login(self.moderador)
        self.client.post(reverse("core:excluir_midia", args=[self.midia.pk]), follow=True)
        self.assertEqual(MidiaCondominio.objects.count(), 0)

    def test_morador_comum_nao_exclui(self):
        self.client.force_login(self.morador)
        r = self.client.post(reverse("core:excluir_midia", args=[self.midia.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(MidiaCondominio.objects.count(), 1)

    def test_portaria_nao_exclui(self):
        self.client.force_login(self.portaria)
        r = self.client.post(reverse("core:excluir_midia", args=[self.midia.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(MidiaCondominio.objects.count(), 1)

    def test_botao_de_excluir_so_para_a_moderacao(self):
        self.client.force_login(self.morador)
        self.assertNotContains(self.client.get(reverse("core:galeria")), "gallery-delete")
        self.client.force_login(self.moderador)
        self.assertContains(self.client.get(reverse("core:galeria")), "gallery-delete")
