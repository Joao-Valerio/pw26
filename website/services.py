from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.utils import OperationalError, ProgrammingError

from .models import Gasto, Meta

_MESES_ABREV = (
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
)


@dataclass(frozen=True)
class ChartDataItem:
    label: str
    value: float


@dataclass(frozen=True)
class ChartDataGasto:
    categoria: str
    total: Decimal
    percentual: int
    cor: str


PALETA = ["#1A6B72", "#2A8A93", "#F0C040", "#E57A44", "#7C5CFC", "#2D9C5B"]


def _safe_list(queryset):
    try:
        return list(queryset)
    except (OperationalError, ProgrammingError):
        return []


def _last_n_calendar_months(today, n=6):
    res = []
    y, m = today.year, today.month
    for _ in range(n):
        res.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(res))


def get_gastos(user, *, desde=None, categoria=None):
    if not user.is_authenticated:
        return []
    qs = Gasto.objects.filter(usuario=user).order_by("-data")
    if desde is not None:
        qs = qs.filter(data__gte=desde)
    if categoria:
        qs = qs.filter(categoria=categoria)
    return _safe_list(qs)


def get_metas(user):
    if not user.is_authenticated:
        return []
    return _safe_list(Meta.objects.filter(usuario=user).order_by("prazo"))


def _monthly_series(gastos, today=None):
    today = today or date.today()
    months_keys = _last_n_calendar_months(today, 6)
    totals = {key: Decimal("0") for key in months_keys}
    for gasto in gastos:
        key = (gasto.data.year, gasto.data.month)
        if key in totals:
            totals[key] += gasto.valor

    return [
        ChartDataItem(
            label=_MESES_ABREV[m - 1].capitalize(),
            value=float(totals[key]),
        )
        for key in months_keys
        for y, m in [key]
    ]


def _weekly_series(gastos, today=None):
    today = today or date.today()
    items = []
    for w in range(3, -1, -1):
        newest = today - timedelta(days=7 * w)
        oldest = today - timedelta(days=7 * (w + 1) - 1)
        total = sum(float(g.valor) for g in gastos if oldest <= g.data <= newest)
        items.append(ChartDataItem(label=f"Sem {4 - w}", value=total))
    return items


def _category_breakdown(gastos):
    totais = {}
    for gasto in gastos:
        label = gasto.get_categoria_display()
        totais[label] = totais.get(label, Decimal("0.00")) + gasto.valor

    total_geral = sum(totais.values(), Decimal("0.00")) or Decimal("1.00")
    itens = []
    for index, (categoria, total) in enumerate(totais.items()):
        percentual = int((total / total_geral) * 100)
        itens.append(
            ChartDataGasto(
                categoria=categoria,
                total=total,
                percentual=percentual,
                cor=PALETA[index % len(PALETA)],
            )
        )
    return sorted(itens, key=lambda item: item.total, reverse=True)


def build_chart_points(items, width=420, height=180):
    if not items:
        return ""

    max_value = max(item.value for item in items) or 1
    if len(items) == 1:
        return f"0,{height}"

    step_x = width / (len(items) - 1)
    points = []
    for index, item in enumerate(items):
        x = round(index * step_x, 2)
        y = round(height - ((item.value / max_value) * (height - 20)), 2)
        points.append(f"{x},{y}")
    return " ".join(points)


def build_area_fill(points, width=420, height=180):
    if not points:
        return ""
    return f"0,{height} {points} {width},{height}"


def build_dashboard_context(user, *, periodo_dias=None, categoria=None):
    desde = None
    if periodo_dias is not None:
        desde = date.today() - timedelta(days=int(periodo_dias))

    gastos = get_gastos(user, desde=desde, categoria=categoria or None)
    metas = get_metas(user)

    total_gastos = sum(gasto.valor for gasto in gastos)
    gasto_medio = total_gastos / Decimal(len(gastos) or 1)
    total_metas = sum(meta.valor_alvo for meta in metas)
    total_guardado = sum(meta.valor_atual for meta in metas)
    recorrentes_count = sum(1 for gasto in gastos if gasto.recorrente)

    area_items = _monthly_series(gastos)
    line_items = _weekly_series(gastos)

    return {
        "gastos": gastos,
        "metas": metas,
        "ultimos_gastos": gastos[:5],
        "categorias_gasto": _category_breakdown(gastos),
        "total_gastos": total_gastos,
        "gasto_medio": gasto_medio,
        "total_metas": total_metas,
        "total_guardado": total_guardado,
        "percentual_guardado": int((total_guardado / (total_metas or Decimal("1.00"))) * 100),
        "recorrentes_count": recorrentes_count,
        "area_chart_items": area_items,
        "area_chart_points": build_chart_points(area_items),
        "area_chart_fill": build_area_fill(build_chart_points(area_items)),
        "line_chart_items": line_items,
        "line_chart_points": build_chart_points(line_items, width=320, height=150),
    }
