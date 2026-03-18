from django.db import models
from django.conf import settings


class Anuncio(models.Model):
    TIPO_CHOICES = [
        ("venda", "Venda"),
        ("aluguel", "Aluguel"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovado", "Aprovado"),
        ("rejeitado", "Rejeitado"),
        ("vendido", "Vendido/Alugado"),
    ]

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="anuncios",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    bloco = models.CharField("Bloco", max_length=10)
    apartamento = models.CharField("Apartamento", max_length=10)
    quartos = models.IntegerField("Quartos", default=2)
    area = models.DecimalField("Área (m²)", max_digits=8, decimal_places=2, blank=True, null=True)
    mobiliado = models.BooleanField("Mobiliado", default=False)
    aceita_pet = models.BooleanField("Aceita Pet", default=False)
    garagem = models.IntegerField("Vagas Garagem", default=1)
    contato_telefone = models.CharField("Telefone de Contato", max_length=20)
    contato_email = models.EmailField("E-mail de Contato", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    destaque = models.BooleanField(default=False)
    visualizacoes = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Anúncio"
        verbose_name_plural = "Anúncios"
        ordering = ["-destaque", "-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"


class FotoAnuncio(models.Model):
    anuncio = models.ForeignKey(Anuncio, on_delete=models.CASCADE, related_name="fotos")
    imagem = models.ImageField(upload_to="anuncios/")
    principal = models.BooleanField(default=False)
    ordem = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Foto do Anúncio"
        verbose_name_plural = "Fotos do Anúncio"
        ordering = ["-principal", "ordem"]

    def __str__(self):
        return f"Foto {self.ordem} - {self.anuncio.titulo}"
