from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from .models import Reserva


class ReservaForm(forms.ModelForm):
    """Form simples: usuario clica num slot, esse form so coleta convidados/obs."""

    class Meta:
        model = Reserva
        fields = ("convidados", "observacao")
        widgets = {
            "convidados": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Nomes dos convidados, um por linha (opcional)",
                "class": "form-control",
            }),
            "observacao": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Alguma observacao? (opcional)",
                "class": "form-control",
            }),
        }
