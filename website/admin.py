from django.contrib import admin

from .models import MensagemContato, Meta, Movimentacao, Saldo


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "categoria", "valor", "data", "usuario")
    list_filter = ("tipo", "categoria", "data")
    search_fields = ("titulo", "observacao")


@admin.register(Meta)
class MetaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "valor_alvo", "valor_atual", "prazo")
    search_fields = ("titulo", "descricao")


@admin.register(MensagemContato)
class MensagemContatoAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "assunto", "lida", "created_at")
    list_filter = ("lida", "created_at")
    search_fields = ("nome", "email", "assunto")


@admin.register(Saldo)
class SaldoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "valor", "updated_at")
    search_fields = ("usuario__username", "usuario__first_name", "usuario__last_name")
