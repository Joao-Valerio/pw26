from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Movimentacao(TimeStampedModel):
    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SAIDA = "saida", "Saída"

    class Categoria(models.TextChoices):
        MORADIA = "moradia", "Moradia"
        ALIMENTACAO = "alimentacao", "Alimentacao"
        TRANSPORTE = "transporte", "Transporte"
        LAZER = "lazer", "Lazer"
        SAUDE = "saude", "Saude"
        EDUCACAO = "educacao", "Educacao"
        OUTROS = "outros", "Outros"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes",
    )
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.SAIDA,
    )
    titulo = models.CharField(max_length=120)
    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        blank=True,
        default="",
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data = models.DateField()
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ["-data", "-created_at"]
        verbose_name = "Movimentacao"
        verbose_name_plural = "Movimentacoes"

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} - R$ {self.valor}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        _recalcular_saldo(self.usuario)

    def delete(self, *args, **kwargs):
        usuario = self.usuario
        super().delete(*args, **kwargs)
        _recalcular_saldo(usuario)


def _recalcular_saldo(usuario):
    if usuario is None:
        return
    saldo, _ = Saldo.objects.get_or_create(usuario=usuario, defaults={"valor": Decimal("0")})
    total_entradas = (
        Movimentacao.objects.filter(usuario=usuario, tipo=Movimentacao.Tipo.ENTRADA)
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    total_saidas = (
        Movimentacao.objects.filter(usuario=usuario, tipo=Movimentacao.Tipo.SAIDA)
        .aggregate(total=Sum("valor"))["total"]
        or Decimal("0")
    )
    saldo.valor = total_entradas - total_saidas
    saldo.save(update_fields=["valor", "updated_at"])


class Meta(TimeStampedModel):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="metas_financeiras",
    )
    titulo = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    valor_alvo = models.DecimalField(max_digits=10, decimal_places=2)
    valor_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prazo = models.DateField()

    class Meta:
        ordering = ["prazo", "-created_at"]
        verbose_name = "Meta"
        verbose_name_plural = "Metas"

    def __str__(self):
        return self.titulo

    @property
    def percentual_concluido(self):
        if not self.valor_alvo:
            return 0

        percentual = (self.valor_atual / self.valor_alvo) * 100
        return min(round(percentual), 100)

    @property
    def valor_restante(self):
        restante = self.valor_alvo - self.valor_atual
        return max(restante, Decimal("0.00"))


class Saldo(TimeStampedModel):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saldo",
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Saldo"
        verbose_name_plural = "Saldos"

    def __str__(self):
        return f"{self.usuario} - R$ {self.valor}"


class MensagemContato(TimeStampedModel):
    nome = models.CharField(max_length=120)
    email = models.EmailField()
    assunto = models.CharField(max_length=140)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mensagem de contato"
        verbose_name_plural = "Mensagens de contato"

    def __str__(self):
        return f"{self.nome} - {self.assunto}"
