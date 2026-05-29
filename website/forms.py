from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe

from dataclasses import dataclass
from typing import Any, Callable

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Field, Layout, Row

from .models import MensagemContato, Meta, Movimentacao, Saldo


class ISODateInput(forms.DateInput):
    input_type = "date"


def _crispy_helper(layout: Layout) -> FormHelper:
    helper = FormHelper()
    helper.form_tag = False
    helper.disable_csrf = True
    helper.form_show_labels = True
    helper.form_show_errors = True
    helper.layout = layout
    return helper


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(Column(Field("username"), css_class="col-12")),
                Row(Column(Field("password"), css_class="col-12")),
            )
        )


class CadastroForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="E-mail")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password1"].label = "Senha"
        self.fields["password2"].label = "Confirmacao da senha"
        self.helper = _crispy_helper(
            Layout(
                Row(
                    Column(Field("first_name"), css_class="col-12 col-md-6"),
                    Column(Field("last_name"), css_class="col-12 col-md-6"),
                ),
                Row(Column(Field("username"), css_class="col-12")),
                Row(Column(Field("email"), css_class="col-12")),
                Row(
                    Column(Field("password1"), css_class="col-12 col-md-6"),
                    Column(Field("password2"), css_class="col-12 col-md-6"),
                ),
            )
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class PerfilForm(forms.ModelForm):
    form_type = forms.CharField(widget=forms.HiddenInput(), initial="perfil")

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Nome"
        self.fields["last_name"].label = "Sobrenome"
        self.fields["last_name"].required = False
        self.fields["email"].label = "E-mail"
        self.helper = _crispy_helper(
            Layout(
                Field("form_type"),
                Row(
                    Column(Field("first_name"), css_class="col-12 col-md-6"),
                    Column(Field("last_name"), css_class="col-12 col-md-6"),
                ),
                Row(Column(Field("email"), css_class="col-12")),
            )
        )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail ja esta em uso.")
        return email


class ContaSenhaForm(PasswordChangeForm):
    form_type = forms.CharField(widget=forms.HiddenInput(), initial="senha")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Senha atual"
        self.fields["new_password1"].label = "Nova senha"
        self.fields["new_password2"].label = "Confirmar nova senha"
        self.helper = _crispy_helper(
            Layout(
                Field("form_type"),
                Row(Column(Field("old_password"), css_class="col-12")),
                Row(
                    Column(Field("new_password1"), css_class="col-12 col-md-6"),
                    Column(Field("new_password2"), css_class="col-12 col-md-6"),
                ),
            )
        )


class ExcluirContaForm(forms.Form):
    password = forms.CharField(label="Senha atual", widget=forms.PasswordInput)
    confirmacao = forms.CharField(
        label="Digite seu usuario para confirmar",
        help_text="Informe exatamente o nome de usuario da sua conta.",
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(Column(Field("password"), css_class="col-12")),
                Row(Column(Field("confirmacao"), css_class="col-12")),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmacao = cleaned_data.get("confirmacao")

        if password and not self.user.check_password(password):
            self.add_error("password", "Senha incorreta.")

        if confirmacao and confirmacao != self.user.username:
            self.add_error("confirmacao", "O usuario informado nao confere.")

        return cleaned_data


class ContatoForm(forms.ModelForm):
    class Meta:
        model = MensagemContato
        fields = ("nome", "email", "assunto", "mensagem")
        widgets = {
            "mensagem": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(
                    Column(Field("nome"), css_class="col-12 col-md-6"),
                    Column(Field("email"), css_class="col-12 col-md-6"),
                ),
                Row(Column(Field("assunto"), css_class="col-12 col-md-6")),
                Row(Column(Field("mensagem"), css_class="col-12")),
            )
        )


class MovimentacaoForm(forms.ModelForm):
    data = forms.DateField(
        label="Data",
        input_formats=["%Y-%m-%d"],
        widget=ISODateInput(format="%Y-%m-%d"),
    )

    class Meta:
        model = Movimentacao
        fields = ("tipo", "titulo", "categoria", "valor", "data", "observacao")
        widgets = {
            "observacao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].required = False
        self.fields["categoria"].choices = [("", "---------")] + list(Movimentacao.Categoria.choices)
        self.helper = _crispy_helper(
            Layout(
                Row(
                    Column(Field("tipo"), css_class="col-12 col-md-6"),
                    Column(Field("valor"), css_class="col-12 col-md-6"),
                ),
                Row(Column(Field("titulo"), css_class="col-12")),
                Row(
                    Column(Field("categoria"), css_class="col-12 col-md-6", wrapper_id="wrapper_categoria"),
                    Column(Field("data"), css_class="col-12 col-md-6"),
                ),
                Row(Column(Field("observacao"), css_class="col-12")),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        categoria = cleaned_data.get("categoria")
        if tipo == Movimentacao.Tipo.SAIDA and not categoria:
            self.add_error("categoria", "Informe a categoria para uma saida.")
        return cleaned_data


class MetaFinanceiraForm(forms.ModelForm):
    prazo = forms.DateField(
        label="Prazo",
        input_formats=["%Y-%m-%d"],
        widget=ISODateInput(format="%Y-%m-%d"),
    )

    class Meta:
        model = Meta
        fields = ("titulo", "descricao", "valor_alvo", "valor_atual", "prazo")
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(Column(Field("titulo"), css_class="col-12")),
                Row(
                    Column(Field("valor_alvo"), css_class="col-12 col-md-4"),
                    Column(Field("valor_atual"), css_class="col-12 col-md-4"),
                    Column(Field("prazo"), css_class="col-12 col-md-4"),
                ),
                Row(Column(Field("descricao"), css_class="col-12")),
            )
        )


class MetaAdicionarValorForm(forms.Form):
    valor_adicional = forms.DecimalField(
        label="Valor a adicionar",
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(Column(Field("valor_adicional"), css_class="col-12 col-md-6")),
            )
        )


class RelatorioFiltroForm(forms.Form):
    periodo = forms.ChoiceField(
        label="Periodo",
        choices=(
            ("30", "Ultimos 30 dias"),
            ("90", "Ultimos 90 dias"),
            ("180", "Ultimos 6 meses"),
        ),
    )
    categoria = forms.ChoiceField(
        label="Categoria",
        required=False,
        choices=(
            ("", "Todas as categorias"),
            *Movimentacao.Categoria.choices,
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = _crispy_helper(
            Layout(
                Row(
                    Column(Field("periodo"), css_class="col-12 col-md-6"),
                    Column(Field("categoria"), css_class="col-12 col-md-6"),
                ),
            )
        )


# --- Templates genéricos (única camada HTML para formulários de página inteira) ---
TEMPLATE_FORM_SHELL = "website/form_shell.html"
TEMPLATE_CONFIRM_DELETE = "website/confirm_delete_shell.html"


def _money_br(value: Any) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f"{amount:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _movimentacao_delete_confirmation(obj: Movimentacao) -> SafeString:
    return format_html(
        "Tem certeza que deseja excluir <strong>{}</strong> (R$ {} em {})? "
        "Esta acao nao pode ser desfeita.",
        obj.titulo,
        _money_br(obj.valor),
        obj.data.strftime("%d/%m/%Y"),
    )


def _meta_delete_confirmation(obj: Meta) -> SafeString:
    return format_html(
        "Tem certeza que deseja excluir a meta <strong>{}</strong>? Esta acao nao pode ser desfeita.",
        obj.titulo,
    )


def _saldo_delete_confirmation(obj: Saldo) -> SafeString:
    return format_html(
        "Tem certeza que deseja excluir o saldo atual de <strong>R$ {}</strong>? Esta acao nao pode ser desfeita.",
        _money_br(obj.valor),
    )


@dataclass(frozen=True)
class FormShellConfig:
    """Metadados de página + formulário Crispy (centralizado)."""

    page_title: str
    page_subtitle: str
    submit_label: str = "Salvar"
    cancel_url_name: str | None = None
    page_action_url_name: str | None = None
    page_action_label: str = "Voltar"
    form_variant: str = "default"
    form_method: str = "post"
    actions_container_class: str = "d-flex flex-wrap gap-2"
    show_form_errors_alert: bool = False
    show_non_field_errors: bool = True
    submit_button_class: str = "btn-accent"
    show_actions: bool = True

    def to_context(self, request) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "page_title": self.page_title,
            "page_subtitle": self.page_subtitle,
            "submit_label": self.submit_label,
            "actions_container_class": self.actions_container_class,
            "form_method": self.form_method,
            "show_form_errors_alert": self.show_form_errors_alert,
            "show_non_field_errors": self.show_non_field_errors,
            "submit_button_class": self.submit_button_class,
            "show_actions": self.show_actions,
            "form_variant": self.form_variant,
        }
        ctx["cancel_url"] = reverse(self.cancel_url_name) if self.cancel_url_name else None
        ctx["page_action_url"] = (
            reverse(self.page_action_url_name) if self.page_action_url_name else None
        )
        ctx["page_action_label"] = self.page_action_label
        return ctx


@dataclass(frozen=True)
class DeleteShellConfig:
    page_title: str
    page_subtitle: str
    confirmation_html: Callable[[Any], SafeString | str]
    page_action_url_name: str
    page_action_label: str = "Cancelar"
    cancel_url_name: str | None = None
    cancel_label: str = "Voltar"
    submit_label: str = "Excluir"
    submit_extra_style: str = (
        "background: linear-gradient(135deg, var(--danger), #c94a38); border: none;"
    )

    def to_context(self, request, obj: Any) -> dict[str, Any]:
        ch = self.confirmation_html(obj)
        if not isinstance(ch, SafeString):
            ch = mark_safe(str(ch))
        cancel = reverse(self.cancel_url_name) if self.cancel_url_name else reverse(self.page_action_url_name)
        return {
            "page_title": self.page_title,
            "page_subtitle": self.page_subtitle,
            "confirmation_html": ch,
            "page_action_url": reverse(self.page_action_url_name),
            "page_action_label": self.page_action_label,
            "cancel_url": cancel,
            "cancel_label": self.cancel_label,
            "submit_label": self.submit_label,
            "submit_extra_style": self.submit_extra_style,
        }


class FormShellContextMixin:
    """Anexa contexto definido em form_shell_config (subclasse define o atributo)."""

    form_shell_config: FormShellConfig

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.form_shell_config.to_context(self.request))
        return context


class DeleteShellContextMixin:
    """Anexa contexto de confirmação de exclusão."""

    delete_shell_config: DeleteShellConfig

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.delete_shell_config.to_context(self.request, self.object))
        return context


# --- Instâncias usadas pelas CBVs ---

SHELL_LOGIN = FormShellConfig(
    page_title="Login",
    page_subtitle="Entre para acessar o painel financeiro.",
    submit_label="Entrar",
    actions_container_class="d-grid",
    form_variant="auth_login",
    cancel_url_name=None,
    page_action_url_name=None,
)

SHELL_CADASTRO = FormShellConfig(
    page_title="Criar conta",
    page_subtitle="Cadastre-se para começar a registrar movimentacoes, metas e relatorios.",
    submit_label="Criar conta",
    actions_container_class="d-grid",
    form_variant="auth_cadastro",
)

SHELL_MOVIMENTACAO_CREATE = FormShellConfig(
    page_title="Nova movimentacao",
    page_subtitle="Registre uma entrada ou saida para acompanhar no painel.",
    submit_label="Salvar",
    cancel_url_name="movimentacoes",
    page_action_url_name="movimentacoes",
    page_action_label="Voltar as movimentacoes",
    form_variant="movimentacao",
)

SHELL_MOVIMENTACAO_UPDATE = FormShellConfig(
    page_title="Editar movimentacao",
    page_subtitle="Atualize os dados desta movimentacao.",
    submit_label="Salvar",
    cancel_url_name="movimentacoes",
    page_action_url_name="movimentacoes",
    page_action_label="Voltar as movimentacoes",
    form_variant="movimentacao",
)

SHELL_META_CREATE = FormShellConfig(
    page_title="Nova meta",
    page_subtitle="Defina um objetivo financeiro e acompanhe o progresso.",
    submit_label="Salvar",
    cancel_url_name="metas",
    page_action_url_name="metas",
    page_action_label="Voltar as metas",
)

SHELL_META_UPDATE = FormShellConfig(
    page_title="Editar meta",
    page_subtitle="Atualize titulo, valores ou prazo desta meta.",
    submit_label="Salvar",
    cancel_url_name="metas",
    page_action_url_name="metas",
    page_action_label="Voltar as metas",
)

SHELL_META_ADD_VALOR = FormShellConfig(
    page_title="Adicionar valor a meta",
    page_subtitle="Some um novo valor ao progresso atual desta meta.",
    submit_label="Adicionar",
    cancel_url_name="metas",
    page_action_url_name="metas",
    page_action_label="Voltar as metas",
    form_variant="meta_add_value",
)

SHELL_CONTATO = FormShellConfig(
    page_title="Contato",
    page_subtitle="Use o formulario para enviar duvidas, feedbacks ou pedidos de suporte.",
    submit_label="Enviar mensagem",
    cancel_url_name=None,
    page_action_url_name=None,
    form_variant="contato",
)

SHELL_CONTA_EXCLUIR = FormShellConfig(
    page_title="Excluir conta",
    page_subtitle="Confirme sua identidade para encerrar o acesso permanentemente.",
    submit_label="Excluir conta permanentemente",
    cancel_url_name="conta",
    page_action_url_name="conta",
    page_action_label="Voltar para minha conta",
    form_variant="conta_excluir",
    submit_button_class="btn-accent",
)

DELETE_MOVIMENTACAO = DeleteShellConfig(
    page_title="Excluir movimentacao",
    page_subtitle="Confirme para remover o lancamento permanentemente.",
    confirmation_html=_movimentacao_delete_confirmation,
    page_action_url_name="movimentacoes",
    page_action_label="Cancelar",
    cancel_url_name="movimentacoes",
    cancel_label="Voltar",
)

DELETE_META = DeleteShellConfig(
    page_title="Excluir meta",
    page_subtitle="Confirme para remover esta meta permanentemente.",
    confirmation_html=_meta_delete_confirmation,
    page_action_url_name="metas",
    page_action_label="Cancelar",
    cancel_url_name="metas",
    cancel_label="Voltar",
)
