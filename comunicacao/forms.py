from django import forms
from .models import MuralPost, Comentario, MensagemAdministracao


class MuralPostForm(forms.ModelForm):
    class Meta:
        model = MuralPost
        fields = ["categoria", "titulo", "conteudo", "imagem"]
        widgets = {
            "categoria": forms.Select(attrs={"class": "form-input"}),
            "titulo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Título da publicação"}),
            "conteudo": forms.Textarea(attrs={"class": "form-input", "rows": 4, "placeholder": "Escreva sua mensagem..."}),
            "imagem": forms.ClearableFileInput(attrs={"class": "form-input"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # Moradores comuns: só geral, sugestão e achados
            categorias_morador = [("geral", "Geral"), ("sugestao", "Sugestão"), ("achados", "Achados e Perdidos")]
            self.fields["categoria"].choices = categorias_morador


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["conteudo"]
        widgets = {
            "conteudo": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 2,
                "placeholder": "Escreva um comentário...",
            }),
        }


class MensagemAdmForm(forms.ModelForm):
    class Meta:
        model = MensagemAdministracao
        fields = ["assunto", "mensagem"]
        widgets = {
            "assunto": forms.TextInput(attrs={"class": "form-input", "placeholder": "Assunto"}),
            "mensagem": forms.Textarea(attrs={"class": "form-input", "rows": 5, "placeholder": "Sua mensagem..."}),
        }
