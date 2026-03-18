from django import forms
from .models import Anuncio, FotoAnuncio


class AnuncioForm(forms.ModelForm):
    class Meta:
        model = Anuncio
        fields = [
            "tipo", "titulo", "descricao", "valor",
            "bloco", "apartamento", "quartos", "area",
            "mobiliado", "aceita_pet", "garagem",
            "contato_telefone", "contato_email",
        ]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-input"}),
            "titulo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Título do anúncio"}),
            "descricao": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Descreva o imóvel..."}),
            "valor": forms.NumberInput(attrs={"class": "form-input", "placeholder": "0,00"}),
            "bloco": forms.TextInput(attrs={"class": "form-input", "placeholder": "Bloco"}),
            "apartamento": forms.TextInput(attrs={"class": "form-input", "placeholder": "Apt"}),
            "quartos": forms.NumberInput(attrs={"class": "form-input"}),
            "area": forms.NumberInput(attrs={"class": "form-input", "placeholder": "m²"}),
            "garagem": forms.NumberInput(attrs={"class": "form-input"}),
            "contato_telefone": forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
            "contato_email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "seu@email.com"}),
        }


class FotoAnuncioForm(forms.ModelForm):
    class Meta:
        model = FotoAnuncio
        fields = ["imagem", "principal"]
        widgets = {
            "imagem": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }
