from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from .models import Meta, Movimentacao, Saldo
from .views import GroupRequiredMixin


class ContaViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="conta_user",
            password="senha123forte",
            email="conta@example.com",
            first_name="Maria",
            last_name="Silva",
        )
        self.client.force_login(self.user)

    def test_pagina_conta_requer_login(self):
        client = Client()
        response = client.get(reverse("conta"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('conta')}")

    def test_exibe_painel_da_conta(self):
        response = self.client.get(reverse("conta"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dados pessoais")
        self.assertContains(response, "Alterar senha")
        self.assertContains(response, "conta_user")

    def test_atualiza_dados_pessoais(self):
        response = self.client.post(
            reverse("conta"),
            {
                "form_type": "perfil",
                "first_name": "Ana",
                "last_name": "Costa",
                "email": "ana@example.com",
            },
        )
        self.assertRedirects(response, reverse("conta"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ana")
        self.assertEqual(self.user.last_name, "Costa")
        self.assertEqual(self.user.email, "ana@example.com")

    def test_atualiza_senha(self):
        response = self.client.post(
            reverse("conta"),
            {
                "form_type": "senha",
                "old_password": "senha123forte",
                "new_password1": "novaSenha456!",
                "new_password2": "novaSenha456!",
            },
        )
        self.assertRedirects(response, reverse("conta"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("novaSenha456!"))


class ContaExcluirViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="delete_user",
            password="senha123forte",
        )
        self.client.force_login(self.user)
        self.meta = Meta.objects.create(
            usuario=self.user,
            titulo="Reserva",
            valor_alvo="1000.00",
            valor_atual="100.00",
            prazo="2026-12-31",
        )
        Movimentacao.objects.create(
            usuario=self.user,
            titulo="Salario",
            valor="500.00",
            data="2026-01-10",
            tipo=Movimentacao.Tipo.ENTRADA,
        )

    def test_exclui_conta_e_dados_vinculados(self):
        response = self.client.post(
            reverse("conta_excluir"),
            {
                "password": "senha123forte",
                "confirmacao": "delete_user",
            },
        )
        self.assertRedirects(response, reverse("inicio"))
        self.assertFalse(User.objects.filter(username="delete_user").exists())
        self.assertFalse(Meta.objects.filter(titulo="Reserva").exists())
        self.assertFalse(Movimentacao.objects.filter(titulo="Salario").exists())


class SaldoViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="teste",
            password="senha123forte",
        )
        self.client.force_login(self.user)

    def test_exibe_saldo_cadastrado_na_pagina(self):
        Saldo.objects.create(usuario=self.user, valor=Decimal("2500.00"))

        response = self.client.get(reverse("saldo"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2.500,00")


class MetaAdicionarValorViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="meta_user",
            password="senha123forte",
        )
        self.client.force_login(self.user)
        self.meta = Meta.objects.create(
            usuario=self.user,
            titulo="Reserva de emergencia",
            valor_alvo=Decimal("5000.00"),
            valor_atual=Decimal("1000.00"),
            prazo="2026-12-31",
        )

    def test_adiciona_valor_sem_editar_meta_completa(self):
        response = self.client.post(
            reverse("meta_adicionar_valor", args=[self.meta.pk]),
            {"valor_adicional": "250.50"},
        )

        self.assertRedirects(response, reverse("metas"))
        self.meta.refresh_from_db()
        self.assertEqual(self.meta.valor_atual, Decimal("1250.50"))


class GroupRequiredMixinTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Gerentes")
        self.user_in_group = User.objects.create_user("user_in_group", "senha123")
        self.user_in_group.groups.add(self.group)
        self.user_out_of_group = User.objects.create_user("user_out_of_group", "senha123")

    def test_permissao_grupo_sucesso(self):
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user_in_group

        mixin = GroupRequiredMixin()
        mixin.request = request
        mixin.group_required = "Gerentes"

        self.assertTrue(mixin.test_func())

    def test_permissao_grupo_negada(self):
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user_out_of_group

        mixin = GroupRequiredMixin()
        mixin.request = request
        mixin.group_required = "Gerentes"

        self.assertFalse(mixin.test_func())


class PaginasViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="teste_paginas",
            password="senha123forte",
        )

    def test_paginas_publicas(self):
        client = Client()
        for url_name in ["inicio", "sobre", "contato", "login", "cadastro"]:
            with self.subTest(url_name=url_name):
                response = client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_paginas_autenticadas(self):
        self.client.force_login(self.user)
        for url_name in [
            "dashboard",
            "movimentacoes",
            "movimentacao_nova",
            "metas",
            "meta_nova",
            "saldo",
            "relatorios",
            "recursos",
            "conta",
        ]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)

    def test_paginacao_movimentacoes(self):
        self.client.force_login(self.user)
        for i in range(15):
            Movimentacao.objects.create(
                usuario=self.user,
                titulo=f"Movimentacao {i}",
                valor=Decimal("10.00"),
                data="2026-01-01",
                tipo=Movimentacao.Tipo.SAIDA,
            )
        response = self.client.get(reverse("movimentacoes"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["movimentacoes"]), 10)

        response_page2 = self.client.get(reverse("movimentacoes") + "?page=2")
        self.assertEqual(response_page2.status_code, 200)
        self.assertEqual(len(response_page2.context["movimentacoes"]), 5)


