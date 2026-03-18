from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, MidiaCondominio


class MultipleFileWidget(forms.FileInput):
    """Widget que permite múltiplos arquivos sem usar o bloqueio do Django 6."""
    def __init__(self, attrs=None):
        # Chamamos Widget.__init__ diretamente para evitar a validação de FileInput
        forms.Widget.__init__(self, attrs)
        self.input_type = "file"
        if self.attrs is None:
            self.attrs = {}
        self.attrs["multiple"] = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, "getlist"):
            return files.getlist(name)
        return files.get(name)


class CadastroForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nome",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Seu nome"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Seu sobrenome"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "seu@email.com"}),
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "000.000.000-00"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
    )
    bloco = forms.CharField(
        label="Bloco",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: A"}),
    )
    apartamento = forms.CharField(
        label="Apartamento",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: 101"}),
    )

    class Meta:
        model = Usuario
        fields = [
            "username", "first_name", "last_name", "email",
            "cpf", "telefone", "bloco", "apartamento",
            "password1", "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-input", "placeholder": "Nome de usuário"})
        self.fields["password1"].widget.attrs.update({"class": "form-input", "placeholder": "Senha"})
        self.fields["password2"].widget.attrs.update({"class": "form-input", "placeholder": "Confirme a senha"})


class UploadMidiaForm(forms.Form):
    """Formulário para upload múltiplo de fotos/vídeos do condomínio."""
    CATEGORIA_CHOICES = MidiaCondominio.CATEGORIA_CHOICES

    categoria = forms.ChoiceField(
        choices=CATEGORIA_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
        label="Categoria",
    )
    titulo = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Título (opcional)"}),
        label="Título",
    )
    descricao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Descrição (opcional)"}),
        label="Descrição",
    )
    arquivos = forms.FileField(
        widget=MultipleFileWidget(attrs={"class": "form-input", "accept": "image/*,video/*", "id": "id_arquivos"}),
        label="Fotos / Vídeos",
        help_text="Selecione uma ou mais fotos e vídeos.",
        required=True,
    )
