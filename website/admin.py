from django.contrib import admin

from .models import Gasto, MensagemContato, Meta


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "valor", "data", "recorrente")
    list_filter = ("categoria", "recorrente", "data")
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
