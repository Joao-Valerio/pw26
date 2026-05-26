from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView

from .forms import (
    CadastroForm,
    ContatoForm,
    DELETE_META,
    DELETE_MOVIMENTACAO,
    DeleteShellContextMixin,
    FormShellContextMixin,
    LoginForm,
    MetaAdicionarValorForm,
    MetaFinanceiraForm,
    MovimentacaoForm,
    RelatorioFiltroForm,
    SHELL_CADASTRO,
    SHELL_CONTATO,
    SHELL_LOGIN,
    SHELL_META_ADD_VALOR,
    SHELL_META_CREATE,
    SHELL_META_UPDATE,
    SHELL_MOVIMENTACAO_CREATE,
    SHELL_MOVIMENTACAO_UPDATE,
    TEMPLATE_CONFIRM_DELETE,
    TEMPLATE_FORM_SHELL,
)
from .models import Meta, Movimentacao, Saldo
from .services import build_dashboard_context


class AuthPageMixin(LoginRequiredMixin):
    login_url = reverse_lazy("login")


class BasePageMixin:
    page_title = "Painel financeiro"
    page_subtitle = "Acompanhe indicadores, metas e movimentacoes em um unico fluxo."
    show_sidebar = True
    skip_auth_wrapper = False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.page_title)
        context.setdefault("page_subtitle", self.page_subtitle)
        context.setdefault("show_sidebar", self.show_sidebar)
        context.setdefault("skip_auth_wrapper", self.skip_auth_wrapper)
        return context


class DashboardView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/dashboard.html"
    page_title = "Dashboard"
    page_subtitle = "Visao geral da sua saude financeira com cards, tabela e graficos."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        return context


class MovimentacoesView(AuthPageMixin, BasePageMixin, ListView):
    model = Movimentacao
    template_name = "website/movimentacoes.html"
    context_object_name = "movimentacoes"
    page_title = "Movimentacoes"
    page_subtitle = "Entradas e saidas registradas para acompanhar seu saldo."

    def get_queryset(self):
        return Movimentacao.objects.filter(usuario=self.request.user).order_by("-data", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        movimentacoes = context["object_list"]
        context["movimentacoes"] = movimentacoes
        entradas = [m for m in movimentacoes if m.tipo == Movimentacao.Tipo.ENTRADA]
        saidas = [m for m in movimentacoes if m.tipo == Movimentacao.Tipo.SAIDA]
        context["total_entradas"] = sum(m.valor for m in entradas)
        context["total_saidas"] = sum(m.valor for m in saidas)
        context["saldo"] = Saldo.objects.filter(usuario=self.request.user).first()
        dashboard_ctx = build_dashboard_context(self.request.user)
        context["categorias_gasto"] = dashboard_ctx.get("categorias_gasto", [])
        return context


class MetasView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/metas.html"
    page_title = "Metas"
    page_subtitle = "Metas financeiras com progresso, prazo e valor restante."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        return context


class RelatoriosView(AuthPageMixin, BasePageMixin, FormView):
    template_name = "website/relatorios.html"
    form_class = RelatorioFiltroForm
    success_url = reverse_lazy("relatorios")
    page_title = "Relatorios"
    page_subtitle = "Filtros, indicadores e comparativos para apoiar suas decisoes."

    def get_initial(self):
        return {"periodo": "90", "categoria": ""}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET" and self.request.GET:
            initial = self.get_initial()
            data = self.request.GET.copy()
            if "periodo" not in data:
                data["periodo"] = initial.get("periodo", "90")
            if "categoria" not in data:
                data["categoria"] = initial.get("categoria", "")
            kwargs["data"] = data
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_form()
        initial = self.get_initial()
        periodo_dias = int(initial.get("periodo", "90"))
        categoria = initial.get("categoria") or None
        if categoria == "":
            categoria = None

        if form.is_bound and form.is_valid():
            periodo_dias = int(form.cleaned_data["periodo"])
            categoria = form.cleaned_data.get("categoria") or None
            if categoria == "":
                categoria = None

        context.update(
            build_dashboard_context(
                self.request.user,
                periodo_dias=periodo_dias,
                categoria=categoria,
            )
        )
        return context


class RecursosView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/recursos.html"
    page_title = "Recursos"
    page_subtitle = "Biblioteca de funcionalidades inspirada nos componentes do diagrama."


class SobreView(BasePageMixin, TemplateView):
    template_name = "website/sobre.html"
    page_title = "Arquitetura da plataforma"
    page_subtitle = "Resumo de como os modulos Django foram organizados a partir do diagrama."


class ContatoView(FormShellContextMixin, BasePageMixin, FormView):
    template_name = TEMPLATE_FORM_SHELL
    form_class = ContatoForm
    form_shell_config = SHELL_CONTATO
    success_url = reverse_lazy("contato")

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Mensagem enviada com sucesso.")
        return super().form_valid(form)


class UsuarioLoginView(FormShellContextMixin, BasePageMixin, DjangoLoginView):
    template_name = TEMPLATE_FORM_SHELL
    form_class = LoginForm
    form_shell_config = SHELL_LOGIN
    redirect_authenticated_user = True
    show_sidebar = False


class CadastroView(FormShellContextMixin, BasePageMixin, FormView):
    template_name = TEMPLATE_FORM_SHELL
    form_class = CadastroForm
    form_shell_config = SHELL_CADASTRO
    success_url = reverse_lazy("dashboard")
    show_sidebar = False

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Conta criada com sucesso.")
        return super().form_valid(form)


class UsuarioLogoutView(DjangoLogoutView):
    next_page = reverse_lazy("login")


# --- Movimentacao ---

class MovimentacaoUserMixin(AuthPageMixin):
    model = Movimentacao

    def get_queryset(self):
        return Movimentacao.objects.filter(usuario=self.request.user)


class MovimentacaoCreateView(FormShellContextMixin, AuthPageMixin, BasePageMixin, CreateView):
    model = Movimentacao
    form_class = MovimentacaoForm
    template_name = TEMPLATE_FORM_SHELL
    form_shell_config = SHELL_MOVIMENTACAO_CREATE

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Movimentacao registrada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("movimentacoes")


class MovimentacaoUpdateView(FormShellContextMixin, MovimentacaoUserMixin, BasePageMixin, UpdateView):
    form_class = MovimentacaoForm
    template_name = TEMPLATE_FORM_SHELL
    form_shell_config = SHELL_MOVIMENTACAO_UPDATE

    def form_valid(self, form):
        messages.success(self.request, "Movimentacao atualizada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("movimentacoes")


class MovimentacaoDeleteView(DeleteShellContextMixin, MovimentacaoUserMixin, BasePageMixin, DeleteView):
    template_name = TEMPLATE_CONFIRM_DELETE
    delete_shell_config = DELETE_MOVIMENTACAO
    context_object_name = "movimentacao"
    success_url = reverse_lazy("movimentacoes")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Movimentacao excluida com sucesso.")
        return super().delete(request, *args, **kwargs)


class MovimentacaoDetailView(MovimentacaoUserMixin, BasePageMixin, DetailView):
    template_name = "website/movimentacao_detail.html"
    context_object_name = "movimentacao"
    page_title = "Detalhe da movimentacao"
    page_subtitle = "Consulte os dados deste lancamento."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        m = self.object
        context["page_title"] = m.titulo
        tipo_label = m.get_tipo_display()
        data_label = m.data.strftime("%d/%m/%Y")
        if m.tipo == Movimentacao.Tipo.SAIDA and m.categoria:
            context["page_subtitle"] = f"{tipo_label} · {m.get_categoria_display()} · {data_label}"
        else:
            context["page_subtitle"] = f"{tipo_label} · {data_label}"
        return context


# --- Metas ---

class MetaUserMixin(AuthPageMixin):
    model = Meta

    def get_queryset(self):
        return Meta.objects.filter(usuario=self.request.user)


class MetaCreateView(FormShellContextMixin, AuthPageMixin, BasePageMixin, CreateView):
    model = Meta
    form_class = MetaFinanceiraForm
    template_name = TEMPLATE_FORM_SHELL
    form_shell_config = SHELL_META_CREATE

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Meta criada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("metas")


class MetaUpdateView(FormShellContextMixin, MetaUserMixin, BasePageMixin, UpdateView):
    form_class = MetaFinanceiraForm
    template_name = TEMPLATE_FORM_SHELL
    form_shell_config = SHELL_META_UPDATE

    def form_valid(self, form):
        messages.success(self.request, "Meta atualizada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("metas")


class MetaAdicionarValorView(FormShellContextMixin, MetaUserMixin, BasePageMixin, SingleObjectMixin, FormView):
    form_class = MetaAdicionarValorForm
    template_name = TEMPLATE_FORM_SHELL
    form_shell_config = SHELL_META_ADD_VALOR
    context_object_name = "meta"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta"] = self.object
        return context

    def form_valid(self, form):
        self.object.valor_atual += form.cleaned_data["valor_adicional"]
        self.object.save(update_fields=["valor_atual", "updated_at"])
        messages.success(self.request, "Valor adicionado a meta com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("metas")


class MetaDeleteView(DeleteShellContextMixin, MetaUserMixin, BasePageMixin, DeleteView):
    template_name = TEMPLATE_CONFIRM_DELETE
    delete_shell_config = DELETE_META
    context_object_name = "meta"
    success_url = reverse_lazy("metas")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Meta excluida com sucesso.")
        return super().delete(request, *args, **kwargs)


# --- Saldo (somente leitura — calculado automaticamente pelas movimentações) ---

class SaldoView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/saldo.html"
    page_title = "Saldo"
    page_subtitle = "Saldo calculado automaticamente a partir das suas movimentacoes."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        saldo = Saldo.objects.filter(usuario=self.request.user).first()
        context["saldo"] = saldo
        movimentacoes = Movimentacao.objects.filter(usuario=self.request.user).order_by("-data", "-created_at")
        entradas = movimentacoes.filter(tipo=Movimentacao.Tipo.ENTRADA)
        saidas = movimentacoes.filter(tipo=Movimentacao.Tipo.SAIDA)
        from django.db.models import Sum
        context["total_entradas"] = entradas.aggregate(t=Sum("valor"))["t"] or 0
        context["total_saidas"] = saidas.aggregate(t=Sum("valor"))["t"] or 0
        context["ultimas_movimentacoes"] = movimentacoes[:10]
        return context


class InicioView(BasePageMixin, TemplateView):
    template_name = "website/inicio.html"
    page_title = "Início"
    page_subtitle = ""
    show_sidebar = False
    skip_auth_wrapper = True
