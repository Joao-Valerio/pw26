import django_filters
from django import forms
from .models import Movimentacao, FotoGaleria


class MovimentacaoFilter(django_filters.FilterSet):
    """
    Filtro dinâmico com Django Filter para o modelo Movimentacao.
    
    EXPLICAÇÃO ACADÊMICA / TÉCNICA:
    O Django Filter resolve o problema de boilerplate e acoplamento na filtragem de QuerySets.
    Sem ele, o desenvolvedor precisa extrair cada parâmetro da requisição (`request.GET.get('tipo')`),
    validar manualmente o tipo de dado e encadear múltiplos `.filter()` condicionais.
    
    Com o FilterSet:
    1. Declaramos os tipos de filtro (CharFilter, ChoiceFilter, DateFilter) de forma legível.
    2. O Django Filter lida com a leitura do querystring, conversão de tipos e sanitização.
    3. A filtragem é segura e integrável diretamente com ListView e paginação.
    """

    titulo = django_filters.CharFilter(
        field_name="titulo",
        lookup_expr="icontains",
        label="Título contendo",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Mercado, Salário..."}),
    )
    tipo = django_filters.ChoiceFilter(
        choices=Movimentacao.Tipo.choices,
        empty_label="Todos os tipos",
        label="Tipo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    categoria = django_filters.ChoiceFilter(
        choices=Movimentacao.Categoria.choices,
        empty_label="Todas as categorias",
        label="Categoria",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    data_inicio = django_filters.DateFilter(
        field_name="data",
        lookup_expr="gte",
        label="Data a partir de",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    data_fim = django_filters.DateFilter(
        field_name="data",
        lookup_expr="lte",
        label="Data até",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = Movimentacao
        fields = ["titulo", "tipo", "categoria", "data_inicio", "data_fim"]


class FotoGaleriaFilter(django_filters.FilterSet):
    """
    Filtro declarativo para os comprovantes e fotos da galeria.
    """
    titulo = django_filters.CharFilter(
        field_name="titulo",
        lookup_expr="icontains",
        label="Buscar título",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Buscar comprovante..."}),
    )

    class Meta:
        model = FotoGaleria
        fields = ["titulo"]
