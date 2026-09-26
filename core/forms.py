from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Usuario, MidiaCondominio, Propaganda


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


class MultipleFileField(forms.FileField):
    """Campo que aceita a LISTA devolvida pelo MultipleFileWidget.

    O FileField comum valida um arquivo so: ao receber a lista do widget ele
    respondia "Nenhum arquivo enviado" e o formulario nunca passava, deixando o
    envio de midias sem efeito. Aqui cada arquivo e validado separadamente.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileWidget())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if isinstance(data, (list, tuple)):
            arquivos = [f for f in data if f]
        elif data:
            arquivos = [data]
        else:
            arquivos = []

        if not arquivos:
            if self.required:
                raise ValidationError(self.error_messages["required"], code="required")
            return []

        validar_um = super().clean
        return [validar_um(arquivo, initial) for arquivo in arquivos]


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
        label="CPF/CNPJ",
        max_length=18,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "000.000.000-00 ou 00.000.000/0000-00"}),
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


class PerfilForm(forms.ModelForm):
    """Formulário para edição do perfil do usuário."""
    first_name = forms.CharField(
        label="Nome",
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        widget=forms.TextInput(attrs={"class": "form-input"}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "form-input"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefone"]


class CriarUsuarioForm(forms.ModelForm):
    """Formulário para o superadmin criar usuários diretamente."""
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Senha do usuário"}),
    )
    first_name = forms.CharField(
        label="Nome",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Nome"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Sobrenome"}),
    )
    email = forms.EmailField(
        label="E-mail",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "email@exemplo.com"}),
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "000.000.000-00"}),
    )
    telefone = forms.CharField(
        label="Telefone",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
    )
    bloco = forms.CharField(
        label="Bloco",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: A"}),
    )
    apartamento = forms.CharField(
        label="Apartamento",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: 101"}),
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        choices=Usuario.TIPO_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )

    class Meta:
        model = Usuario
        fields = ["username", "first_name", "last_name", "email", "cpf", "telefone", "bloco", "apartamento", "tipo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-input", "placeholder": "Nome de usuário (login)"})


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
    arquivos = MultipleFileField(
        widget=MultipleFileWidget(attrs={"class": "form-input", "accept": "image/*,video/*", "id": "id_arquivos"}),
        label="Fotos / Vídeos",
        help_text="Selecione uma ou mais fotos e vídeos.",
        required=True,
    )


class EditarMoradorForm(forms.ModelForm):
    """Correcao do cadastro de um morador pela moderacao.

    De proposito NAO inclui tipo, is_staff, aprovado nem senha: cada um desses
    tem fluxo proprio (promover, aprovar, gerar nova senha) e deixa rastro no
    historico. Aqui e so o dado de contato e de unidade.
    """

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "cpf", "telefone",
                  "bloco", "apartamento", "foto_perfil"]
        labels = {
            "first_name": "Nome", "last_name": "Sobrenome", "email": "E-mail",
            "cpf": "CPF/CNPJ", "telefone": "Telefone", "bloco": "Bloco",
            "apartamento": "Apartamento", "foto_perfil": "Foto de perfil",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            css = campo.widget.attrs.get("class", "")
            campo.widget.attrs["class"] = (css + " form-input").strip()
        self.fields["first_name"].required = True

    def clean_cpf(self):
        """CPF em branco vira None: o campo e unico e nao aceita varios ''."""
        cpf = (self.cleaned_data.get("cpf") or "").strip()
        return cpf or None


class CadastroEmpresaForm(UserCreationForm):
    """Formulário de cadastro para empresas e fornecedores."""
    TIPO_CHOICES = [
        ("empresa", "Empresa"),
        ("fornecedor", "Fornecedor"),
    ]

    tipo = forms.ChoiceField(
        label="Tipo de Cadastro",
        choices=TIPO_CHOICES,
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    first_name = forms.CharField(
        label="Nome do Responsável",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Seu nome"}),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Seu sobrenome"}),
    )
    nome_empresa = forms.CharField(
        label="Nome da Empresa",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Nome da sua empresa"}),
    )
    ramo_atividade = forms.CharField(
        label="Ramo de Atividade",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Elétrica, Pintura, Encanamento..."}),
    )
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "empresa@email.com"}),
    )
    telefone = forms.CharField(
        label="Telefone/WhatsApp",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
    )
    instagram = forms.CharField(
        label="Instagram",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "@suaempresa"}),
    )
    cpf = forms.CharField(
        label="CPF/CNPJ",
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "CPF ou CNPJ"}),
    )

    class Meta:
        model = Usuario
        fields = [
            "username", "first_name", "last_name", "nome_empresa",
            "ramo_atividade", "email", "telefone", "instagram", "cpf",
            "tipo", "password1", "password2",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-input", "placeholder": "Nome de usuário (login)"})
        self.fields["password1"].widget.attrs.update({"class": "form-input", "placeholder": "Senha"})
        self.fields["password2"].widget.attrs.update({"class": "form-input", "placeholder": "Confirme a senha"})


class PropagandaForm(forms.ModelForm):
    """Formulário para criação/edição de propaganda."""

    class Meta:
        model = Propaganda
        fields = ["titulo", "descricao", "imagem", "instagram", "telefone"]
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-input", "placeholder": "Título do anúncio"}),
            "descricao": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Descreva seu produto ou serviço..."}),
            "imagem": forms.FileInput(attrs={"class": "form-input", "accept": "image/*"}),
            "instagram": forms.TextInput(attrs={"class": "form-input", "placeholder": "https://instagram.com/suaempresa"}),
            "telefone": forms.TextInput(attrs={"class": "form-input", "placeholder": "(00) 00000-0000"}),
        }
