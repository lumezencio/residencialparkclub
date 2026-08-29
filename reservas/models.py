from datetime import datetime, timedelta, time as time_cls
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils import timezone


def semana_de(data):
    """Intervalo da semana de CALENDARIO (segunda a domingo) que contem `data`."""
    inicio = data - timedelta(days=data.weekday())  # weekday(): segunda=0
    return inicio, inicio + timedelta(days=6)


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
    max_reservas_por_semana_por_usuario = models.PositiveIntegerField(
        "Maximo de reservas por semana por usuario", default=2,
        help_text=(
            "Quantas reservas o mesmo morador pode fazer por semana (segunda a domingo). "
            "Padrao: 2. Pode ser ajustado individualmente em Moderacao > Limite de reservas."
        )
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

    def limite_semanal_para(self, usuario):
        """Limite semanal que vale para ESTE usuario neste espaco.

        Retorna a excecao individual (LimiteReservaUsuario) quando existir,
        senao o padrao do espaco.
        """
        limite = LimiteReservaUsuario.objects.filter(
            usuario=usuario, espaco=self,
        ).values_list("max_por_semana", flat=True).first()
        if limite is None:
            return self.max_reservas_por_semana_por_usuario, False
        return limite, True

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


class LimiteReservaUsuario(models.Model):
    """Excecao individual do limite semanal, definida pelo moderador.

    Sem registro aqui, vale o padrao do espaco. Com registro, este numero
    substitui o padrao para esse morador naquele espaco (0 = nao pode reservar).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="limites_reserva",
    )
    espaco = models.ForeignKey(Espaco, on_delete=models.CASCADE, related_name="limites_usuarios")
    max_por_semana = models.PositiveIntegerField(
        "Maximo de reservas por semana",
        help_text="Quantas reservas por semana (segunda a domingo) este morador pode fazer. 0 = nenhuma.",
    )
    motivo = models.CharField("Motivo", max_length=200, blank=True)
    definido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="limites_reserva_definidos",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Limite de reservas do morador"
        verbose_name_plural = "Limites de reservas dos moradores"
        ordering = ["usuario__bloco", "usuario__apartamento"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "espaco"],
                name="unique_limite_por_usuario_espaco",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.espaco.nome}: {self.max_por_semana}/semana"


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
        from .permissions import eh_moderador
        if eh_moderador(usuario):
            return not self.passou
        if usuario != self.usuario:
            return False
        limite = self.inicio_dt - timedelta(hours=self.espaco.cancelamento_min_horas)
        return timezone.now() <= limite

    @property
    def convidados_exibicao(self):
        """Convidados para exibir nas telas.

        Usa os registros com nome e CPF. Reservas antigas, feitas quando os
        convidados eram so um texto livre, caem no campo antigo (sem CPF), para
        que nada suma do historico.
        """
        registros = list(self.convidados_lista.all())
        if registros:
            return registros
        return [
            Convidado(reserva=self, nome=linha.strip()[:120], cpf="")
            for linha in (self.convidados or "").splitlines()
            if linha.strip()
        ]

    @property
    def tem_convidados(self):
        return self.convidados_lista.exists() or bool((self.convidados or "").strip())

    @property
    def kit_info(self):
        """KitJogo desta reserva, ou None se o kit nunca foi retirado."""
        try:
            return self.kit
        except ObjectDoesNotExist:
            return None

    @property
    def kit_estado(self):
        """'livre' (na portaria), 'retirado' (com o morador) ou 'devolvido'."""
        kit = self.kit_info
        if kit is None:
            return "livre"
        return "devolvido" if kit.devolvido else "retirado"

    def clean(self):
        if self.hora_inicio and self.hora_fim and self.hora_inicio >= self.hora_fim:
            raise ValidationError("Hora de inicio deve ser antes da hora de fim.")


class Convidado(models.Model):
    """Convidado de uma reserva, com nome e CPF para conferencia na portaria."""

    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name="convidados_lista")
    nome = models.CharField("Nome completo", max_length=120)
    cpf = models.CharField(
        "CPF", max_length=14, blank=True,
        help_text="Opcional, mas agiliza a liberacao na portaria.")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Convidado"
        verbose_name_plural = "Convidados"
        ordering = ["id"]
        indexes = [models.Index(fields=["reserva"])]

    def __str__(self):
        return f"{self.nome} ({self.cpf})" if self.cpf else self.nome


class KitJogo(models.Model):
    """Controle de entrega e devolucao do kit de jogo (raquetes + bolinhas).

    Preenchido na portaria: quem levou o kit e, depois, quem devolveu.
    Um kit por reserva.
    """

    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name="kit")

    retirado_por = models.CharField("Retirado por", max_length=120)
    retirado_em = models.DateTimeField("Retirado em", default=timezone.now)
    raquetes = models.PositiveSmallIntegerField("Raquetes", default=2)
    bolinhas = models.PositiveSmallIntegerField("Bolinhas", default=3)
    retirada_registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kits_entregues",
    )

    devolvido_por = models.CharField("Devolvido por", max_length=120, blank=True)
    devolvido_em = models.DateTimeField("Devolvido em", null=True, blank=True)
    devolucao_registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="kits_recebidos",
    )
    observacao = models.TextField(
        "Observacao", blank=True,
        help_text="Alguma avaria, item faltando ou aviso sobre a devolucao.",
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kit de jogo"
        verbose_name_plural = "Kits de jogo"
        ordering = ["-retirado_em"]
        indexes = [models.Index(fields=["devolvido_em"])]

    def __str__(self):
        estado = "devolvido" if self.devolvido else "em uso"
        return f"Kit {self.reserva} - {estado}"

    @property
    def devolvido(self):
        return self.devolvido_em is not None

    @staticmethod
    def _nome(usuario):
        if not usuario:
            return ""
        return usuario.get_full_name() or usuario.username

    @property
    def entregue_por_nome(self):
        """Vigia/moderador que entregou o kit (vazio se nao registrado)."""
        return self._nome(self.retirada_registrada_por)

    @property
    def recebido_por_nome(self):
        """Vigia/moderador que recebeu o kit de volta."""
        return self._nome(self.devolucao_registrada_por)


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
        if self.data_inicio and self.data_fim and self.data_inicio >= self.data_fim:
            raise ValidationError("Data de inicio deve ser antes da data de fim.")
