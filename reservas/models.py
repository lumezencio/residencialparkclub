from datetime import datetime, timedelta, time as time_cls
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Espaco(models.Model):
    """Espaco reservavel do condominio: quadra, churrasqueira, salao de festas, etc."""

    nome = models.CharField("Nome", max_length=100)
    slug = models.SlugField(unique=True, help_text="Identificador da URL, ex: quadra-beach-tennis")
    descricao = models.TextField("Descricao", blank=True)
    foto = models.ImageField("Foto", upload_to="reservas/espacos/", blank=True, null=True)

    horario_abertura = models.TimeField("Horario de abertura", default=time_cls(6, 0))
    horario_fechamento = models.TimeField("Horario de fechamento", default=time_cls(22, 0))
    duracao_slot_min = models.PositiveIntegerField(
        "Duracao de cada slot (minutos)", default=60,
        help_text="Tempo de cada reserva em minutos. Ex: 60 = 1 hora."
    )

    max_reservas_futuras_por_usuario = models.PositiveIntegerField(
        "Maximo de reservas futuras por usuario", default=3
    )
    max_reservas_por_dia_por_usuario = models.PositiveIntegerField(
        "Maximo de reservas no mesmo dia por usuario", default=1,
        help_text="Quantas reservas o mesmo morador pode ter em um unico dia. Padrao: 1."
    )
    antecedencia_min_horas = models.PositiveIntegerField(
        "Antecedencia minima para reservar (horas)", default=1
    )
    antecedencia_max_dias = models.PositiveIntegerField(
        "Antecedencia maxima para reservar (dias)", default=7
    )
    cancelamento_min_horas = models.PositiveIntegerField(
        "Cancelar ate quantas horas antes", default=2
    )

    ativo = models.BooleanField("Ativo", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Espaco"
        verbose_name_plural = "Espacos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def gerar_slots(self, data):
        """Lista todos os slots possiveis em uma data (objetos time)."""
        slots = []
        inicio = datetime.combine(data, self.horario_abertura)
        fim = datetime.combine(data, self.horario_fechamento)
        delta = timedelta(minutes=self.duracao_slot_min)
        atual = inicio
        while atual + delta <= fim:
            slots.append((atual.time(), (atual + delta).time()))
            atual += delta
        return slots


class Reserva(models.Model):
    STATUS_CHOICES = [
        ("confirmada", "Confirmada"),
        ("cancelada", "Cancelada"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservas",
    )
    espaco = models.ForeignKey(Espaco, on_delete=models.PROTECT, related_name="reservas")
    data = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    convidados = models.TextField(
        "Convidados", blank=True,
        help_text="Nomes dos convidados (um por linha), se houver."
    )
    observacao = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="confirmada")

    # Auditoria
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reservas_canceladas",
    )
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-data", "-hora_inicio"]
        # Garantia em banco: no maximo 1 reserva CONFIRMADA por slot
        constraints = [
            models.UniqueConstraint(
                fields=["espaco", "data", "hora_inicio"],
                condition=models.Q(status="confirmada"),
                name="unique_reserva_confirmada_por_slot",
            ),
        ]
        indexes = [
            models.Index(fields=["espaco", "data"]),
            models.Index(fields=["usuario", "status"]),
        ]

    def __str__(self):
        return f"{self.espaco.nome} {self.data:%d/%m} {self.hora_inicio:%H:%M}-{self.hora_fim:%H:%M} ({self.usuario.username})"

    @property
    def inicio_dt(self):
        return timezone.make_aware(datetime.combine(self.data, self.hora_inicio))

    @property
    def fim_dt(self):
        return timezone.make_aware(datetime.combine(self.data, self.hora_fim))

    @property
    def passou(self):
        return self.fim_dt < timezone.now()

    def pode_cancelar(self, usuario):
        """Regra de cancelamento: dono pode ate X horas antes; staff/moderador sempre."""
        if self.status != "confirmada":
            return False
        if usuario.is_staff or usuario.tipo in ("moderador", "admin"):
            return not self.passou
        if usuario != self.usuario:
            return False
        limite = self.inicio_dt - timedelta(hours=self.espaco.cancelamento_min_horas)
        return timezone.now() <= limite

    def clean(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValidationError("Hora de inicio deve ser antes da hora de fim.")


class BloqueioEspaco(models.Model):
    """Bloqueio de horario feito pelo moderador (manutencao, evento privado, etc.)"""

    espaco = models.ForeignKey(Espaco, on_delete=models.CASCADE, related_name="bloqueios")
    data_inicio = models.DateTimeField("Inicio")
    data_fim = models.DateTimeField("Fim")
    motivo = models.CharField("Motivo", max_length=200)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bloqueios_criados",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bloqueio de espaco"
        verbose_name_plural = "Bloqueios de espacos"
        ordering = ["-data_inicio"]
        indexes = [models.Index(fields=["espaco", "data_inicio", "data_fim"])]

    def __str__(self):
        return f"{self.espaco.nome} {self.data_inicio:%d/%m %H:%M} ate {self.data_fim:%d/%m %H:%M} - {self.motivo}"

    def clean(self):
        if self.data_inicio >= self.data_fim:
            raise ValidationError("Data de inicio deve ser antes da data de fim.")
