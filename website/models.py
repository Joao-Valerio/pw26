from decimal import Decimal
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone


def validar_extensao_e_tamanho_imagem(file):
    """
    Valida se o arquivo enviado possui extensão de imagem permitida (.jpg, .jpeg, .png, .webp)
    e limita o tamanho a no máximo 5MB.
    """
    ext = os.path.splitext(file.name)[1].lower()
    extensoes_validas = ['.jpg', '.jpeg', '.png', '.webp']
    if ext not in extensoes_validas:
        raise ValidationError(f"Extensão não suportada. Envie uma imagem nos formatos: {', '.join(extensoes_validas)}.")
    
    tamanho_maximo_bytes = 5 * 1024 * 1024  # 5 MB
    if file.size > tamanho_maximo_bytes:
        raise ValidationError("O tamanho máximo da imagem é de 5MB.")


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
        on_delete=models.CASCADE,
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
        on_delete=models.CASCADE,
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


class FotoGaleria(TimeStampedModel):
    """
    Modelo para a Galeria de Fotos / Comprovantes.
    Permite armazenar imagens de recibos e notas vinculados unicamente ao usuário autenticado.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fotos_galeria",
    )
    titulo = models.CharField(max_length=120, verbose_name="Título do comprovante / foto")
    descricao = models.TextField(blank=True, verbose_name="Descrição ou observação")
    imagem = models.ImageField(
        upload_to="galeria/%Y/%m/",
        validators=[validar_extensao_e_tamanho_imagem],
        verbose_name="Arquivo de imagem",
    )
    data_registro = models.DateField(default=timezone.now, verbose_name="Data do registro")

    class Meta:
        ordering = ["-data_registro", "-created_at"]
        verbose_name = "Foto da Galeria"
        verbose_name_plural = "Fotos da Galeria"

    def __str__(self):
        return f"{self.titulo} ({self.usuario.username})"


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

