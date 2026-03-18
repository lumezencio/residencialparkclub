from django.db import models
from django.conf import settings


class MuralPost(models.Model):
    CATEGORIA_CHOICES = [
        ("geral", "Geral"),
        ("evento", "Evento"),
        ("aviso", "Aviso"),
        ("sugestao", "Sugestão"),
        ("achados", "Achados e Perdidos"),
    ]

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts_mural",
    )
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default="geral")
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    imagem = models.ImageField(upload_to="mural/", blank=True, null=True)
    aprovado = models.BooleanField(default=False)
    fixado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Post do Mural"
        verbose_name_plural = "Posts do Mural"
        ordering = ["-fixado", "-criado_em"]

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    post = models.ForeignKey(MuralPost, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comentarios",
    )
    conteudo = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"
        ordering = ["criado_em"]

    def __str__(self):
        return f"Comentário de {self.autor} em {self.post}"


class MensagemAdministracao(models.Model):
    STATUS_CHOICES = [
        ("nova", "Nova"),
        ("lida", "Lida"),
        ("respondida", "Respondida"),
    ]

    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mensagens_enviadas",
    )
    assunto = models.CharField(max_length=200)
    mensagem = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="nova")
    resposta = models.TextField(blank=True)
    respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensagens_respondidas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    respondido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Mensagem à Administração"
        verbose_name_plural = "Mensagens à Administração"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.assunto} - {self.remetente}"
