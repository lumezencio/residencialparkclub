from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    TIPO_CHOICES = [
        ("morador", "Morador"),
        ("proprietario", "Proprietário"),
        ("admin", "Administrador"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="morador")
    cpf = models.CharField("CPF", max_length=14, unique=True, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True)
    bloco = models.CharField("Bloco", max_length=10, blank=True)
    apartamento = models.CharField("Apartamento", max_length=10, blank=True)
    foto_perfil = models.ImageField(upload_to="perfis/", blank=True, null=True)
    aprovado = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self):
        return f"{self.get_full_name()} - Bloco {self.bloco} Apt {self.apartamento}"


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
