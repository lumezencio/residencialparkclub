from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ("morador", "Morador"),
        ("proprietario", "Proprietário"),
        ("moderador", "Moderador"),
        ("admin", "Administrador"),
        ("empresa", "Empresa"),
        ("fornecedor", "Fornecedor"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="morador")
    cpf = models.CharField("CPF/CNPJ", max_length=18, unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True)
    bloco = models.CharField("Bloco", max_length=10, blank=True)
    apartamento = models.CharField("Apartamento", max_length=10, blank=True)
    foto_perfil = models.ImageField(upload_to="perfis/", blank=True, null=True)
    aprovado = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    # Campos para empresa/fornecedor
    nome_empresa = models.CharField("Nome da Empresa", max_length=200, blank=True)
    ramo_atividade = models.CharField("Ramo de Atividade", max_length=200, blank=True)
    instagram = models.CharField("Instagram", max_length=200, blank=True, help_text="Ex: @suaempresa")

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.get_full_name()} - Bloco {self.bloco} Apt {self.apartamento}"


class Propaganda(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
    ]

    anunciante = models.ForeignKey(
        "Usuario", on_delete=models.CASCADE, related_name="propagandas"
    )
    titulo = models.CharField("Título", max_length=200)
    descricao = models.TextField("Descrição", blank=True)
    imagem = models.ImageField("Imagem do Anúncio", upload_to="propagandas/")
    instagram = models.CharField(
        "Link do Instagram", max_length=300, blank=True,
        help_text="Ex: https://instagram.com/suaempresa"
    )
    telefone = models.CharField("Telefone/WhatsApp", max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pendente")
    ativo = models.BooleanField(default=True)
    data_inicio = models.DateField("Início da Veiculação", null=True, blank=True)
    data_fim = models.DateField("Fim da Veiculação", null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Propaganda"
        verbose_name_plural = "Propagandas"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.titulo} - {self.anunciante.nome_empresa or self.anunciante.get_full_name()}"


class MidiaCondominio(models.Model):
    TIPO_CHOICES = [
        ("foto", "Foto"),
        ("video", "Vídeo"),
    ]

    CATEGORIA_CHOICES = [
        ("condominio", "Condomínio Atual"),
        ("projetos_futuros", "Projetos Futuros"),
    ]

    titulo = models.CharField(max_length=200, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="condominio")
    arquivo = models.FileField(upload_to="condominio/")
    descricao = models.TextField(blank=True)
    destaque = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mídia do Condomínio"
        verbose_name_plural = "Mídias do Condomínio"
        ordering = ["-destaque", "ordem", "-criado_em"]

    def __str__(self):
        return self.titulo or f"{self.tipo} - {self.criado_em:%d/%m/%Y}"


class VisitaSite(models.Model):
    data = models.DateField(auto_now_add=True)
    ip = models.GenericIPAddressField()
    pagina = models.CharField(max_length=500)
    usuario = models.ForeignKey(
        "Usuario", on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Visita"
        verbose_name_plural = "Visitas"

    def __str__(self):
        return f"{self.ip} - {self.pagina} - {self.data}"


class Informacao(models.Model):
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    icone = models.CharField(max_length=50, blank=True, help_text="Nome do ícone Lucide")
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Informação"
        verbose_name_plural = "Informações"
        ordering = ["ordem"]

    def __str__(self):
        return self.titulo
