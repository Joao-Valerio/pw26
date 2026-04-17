from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView
from django.views.generic.edit import FormView

from .forms import (
    CadastroForm,
    ContatoForm,
    GastoForm,
    LoginForm,
    MetaFinanceiraForm,
    RelatorioFiltroForm,
)
from .models import Gasto, Meta
from .services import build_dashboard_context


class AuthPageMixin(LoginRequiredMixin):
    login_url = reverse_lazy("login")


class BasePageMixin:
    page_title = "Painel financeiro"
    page_subtitle = "Acompanhe indicadores, metas e gastos em um unico fluxo."
    show_sidebar = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("page_title", self.page_title)
        context.setdefault("page_subtitle", self.page_subtitle)
        context.setdefault("show_sidebar", self.show_sidebar)
        return context


class DashboardView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/dashboard.html"
    page_title = "Dashboard"
    page_subtitle = "Visao geral da sua saude financeira com cards, tabela e graficos."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        return context


class GastosView(AuthPageMixin, BasePageMixin, TemplateView):
    template_name = "website/gastos.html"
    page_title = "Gastos"
    page_subtitle = "Tabela com os principais lancamentos e distribuicao por categoria."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
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


class ContatoView(BasePageMixin, FormView):
    template_name = "website/contato.html"
    form_class = ContatoForm
    success_url = reverse_lazy("contato")
    page_title = "Contato"
    page_subtitle = "Use o formulario para enviar duvidas, feedbacks ou pedidos de suporte."

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Mensagem enviada com sucesso.")
        return super().form_valid(form)


class UsuarioLoginView(BasePageMixin, DjangoLoginView):
    template_name = "website/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True
    page_title = "Login"
    page_subtitle = "Entre para acessar o painel financeiro."
    show_sidebar = False


class CadastroView(BasePageMixin, FormView):
    template_name = "website/singup.html"
    form_class = CadastroForm
    success_url = reverse_lazy("dashboard")
    page_title = "Criar conta"
    page_subtitle = "Cadastre-se para começar a registrar gastos, metas e relatorios."
    show_sidebar = False

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Conta criada com sucesso.")
        return super().form_valid(form)


class UsuarioLogoutView(DjangoLogoutView):
    next_page = reverse_lazy("login")


class GastoUserMixin(AuthPageMixin):
    model = Gasto

    def get_queryset(self):
        return Gasto.objects.filter(usuario=self.request.user)


class GastoCreateView(AuthPageMixin, BasePageMixin, CreateView):
    model = Gasto
    form_class = GastoForm
    template_name = "website/gasto_form.html"
    page_title = "Novo gasto"
    page_subtitle = "Registre um lancamento para acompanhar no painel."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Gasto registrado com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("gastos")


class GastoUpdateView(GastoUserMixin, BasePageMixin, UpdateView):
    form_class = GastoForm
    template_name = "website/gasto_form.html"
    page_title = "Editar gasto"
    page_subtitle = "Atualize os dados deste lancamento."

    def form_valid(self, form):
        messages.success(self.request, "Gasto atualizado com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("gastos")


class GastoDeleteView(GastoUserMixin, BasePageMixin, DeleteView):
    template_name = "website/gasto_confirm_delete.html"
    page_title = "Excluir gasto"
    page_subtitle = "Confirme para remover o lancamento permanentemente."
    context_object_name = "gasto"
    success_url = reverse_lazy("gastos")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Gasto excluido com sucesso.")
        return super().delete(request, *args, **kwargs)


class MetaUserMixin(AuthPageMixin):
    model = Meta

    def get_queryset(self):
        return Meta.objects.filter(usuario=self.request.user)


class MetaCreateView(AuthPageMixin, BasePageMixin, CreateView):
    model = Meta
    form_class = MetaFinanceiraForm
    template_name = "website/meta_form.html"
    page_title = "Nova meta"
    page_subtitle = "Defina um objetivo financeiro e acompanhe o progresso."

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        messages.success(self.request, "Meta criada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("metas")


class MetaUpdateView(MetaUserMixin, BasePageMixin, UpdateView):
    form_class = MetaFinanceiraForm
    template_name = "website/meta_form.html"
    page_title = "Editar meta"
    page_subtitle = "Atualize titulo, valores ou prazo desta meta."

    def form_valid(self, form):
        messages.success(self.request, "Meta atualizada com sucesso.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("metas")


class MetaDeleteView(MetaUserMixin, BasePageMixin, DeleteView):
    template_name = "website/meta_confirm_delete.html"
    page_title = "Excluir meta"
    page_subtitle = "Confirme para remover esta meta permanentemente."
    context_object_name = "meta"
    success_url = reverse_lazy("metas")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Meta excluida com sucesso.")
        return super().delete(request, *args, **kwargs)
