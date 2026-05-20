from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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

    @property
    def suspensao_ativa(self):
        """Retorna a SuspensaoMorador ativa no momento (ou None)."""
        agora = timezone.now()
        return self.suspensoes.filter(
            ativa=True,
            inicio__lte=agora,
        ).filter(
            models.Q(fim__isnull=True) | models.Q(fim__gt=agora)
        ).order_by("-inicio").first()

    @property
    def esta_suspenso(self):
        return self.suspensao_ativa is not None

    def bloqueado_para(self, modulo):
        """Verifica se o usuario tem suspensao ativa que bloqueia o modulo informado.
        Modulos validos: 'reservas', 'propagandas', 'mural', 'classificados', 'galeria'."""
        susp = self.suspensao_ativa
        if not susp:
            return False
        return getattr(susp, f"bloqueia_{modulo}", False)


class SuspensaoMorador(models.Model):
    """Suspensao aplicada pelo moderador conforme Regimento Interno.
    Enquanto ativa, o morador NAO pode fazer novas reservas."""

    usuario = models.ForeignKey(
        "Usuario", on_delete=models.CASCADE, related_name="suspensoes",
    )
    inicio = models.DateTimeField("Inicio", default=timezone.now)
    fim = models.DateTimeField(
        "Fim", null=True, blank=True,
        help_text="Deixe em branco para suspensao por tempo indeterminado.",
    )
    motivo = models.TextField("Motivo")
    aplicada_por = models.ForeignKey(
        "Usuario", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="suspensoes_aplicadas",
    )
    ativa = models.BooleanField(
        "Ativa", default=True,
        help_text="Desmarque (ou clique em remover) para encerrar a suspensao. O historico fica preservado.",
    )

    # Modulos bloqueados (moderador escolhe na hora de aplicar)
    bloqueia_reservas = models.BooleanField("Bloquear reservas", default=True)
    bloqueia_propagandas = models.BooleanField("Bloquear propagandas", default=False)
    bloqueia_mural = models.BooleanField("Bloquear mural/comunidade", default=False)
    bloqueia_classificados = models.BooleanField("Bloquear classificados", default=False)
    bloqueia_galeria = models.BooleanField("Bloquear upload galeria", default=False)

    criada_em = models.DateTimeField(auto_now_add=True)
    encerrada_em = models.DateTimeField(null=True, blank=True)
    encerrada_por = models.ForeignKey(
        "Usuario", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="suspensoes_encerradas",
    )

    class Meta:
        verbose_name = "Suspensao de morador"
        verbose_name_plural = "Suspensoes de moradores"
        ordering = ["-inicio"]
        indexes = [
            models.Index(fields=["usuario", "ativa"]),
        ]

    MODULOS = (
        ("reservas", "Reservas"),
        ("propagandas", "Propagandas"),
        ("mural", "Mural / Comunidade"),
        ("classificados", "Classificados"),
        ("galeria", "Galeria"),
    )

    def __str__(self):
        prazo = f"ate {self.fim:%d/%m/%Y}" if self.fim else "indeterminada"
        return f"{self.usuario} - {prazo} - {self.motivo[:40]}"

    @property
    def em_vigor(self):
        if not self.ativa:
            return False
        agora = timezone.now()
        if self.inicio > agora:
            return False
        if self.fim and self.fim <= agora:
            return False
        return True

    @property
    def modulos_bloqueados(self):
        out = []
        for key, label in self.MODULOS:
            if getattr(self, f"bloqueia_{key}", False):
                out.append((key, label))
        return out


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
