from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from math import cos, radians, sin

from django.db.models import Sum
from django.db.utils import OperationalError, ProgrammingError

from .models import Meta, Movimentacao, Saldo

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


PALETA = [
    "#0284c7",
    "#0ea5e9",
    "#38bdf7",
    "#7dd3fc",
    "#c4a574",
    "#0f766e",
]


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


def get_saidas(user, *, desde=None, categoria=None):
    """Retorna as saídas (gastos) do usuário para análise de despesas."""
    if not user.is_authenticated:
        return []
    qs = Movimentacao.objects.filter(
        usuario=user, tipo=Movimentacao.Tipo.SAIDA
    ).order_by("-data")
    if desde is not None:
        qs = qs.filter(data__gte=desde)
    if categoria:
        qs = qs.filter(categoria=categoria)
    return _safe_list(qs)


def get_entradas(user, *, desde=None):
    """Retorna as entradas do usuário."""
    if not user.is_authenticated:
        return []
    qs = Movimentacao.objects.filter(
        usuario=user, tipo=Movimentacao.Tipo.ENTRADA
    ).order_by("-data")
    if desde is not None:
        qs = qs.filter(data__gte=desde)
    return _safe_list(qs)


def get_metas(user):
    if not user.is_authenticated:
        return []
    return _safe_list(Meta.objects.filter(usuario=user).order_by("prazo"))


def _monthly_series(saidas, today=None):
    today = today or date.today()
    months_keys = _last_n_calendar_months(today, 6)
    totals = {key: Decimal("0") for key in months_keys}
    for saida in saidas:
        key = (saida.data.year, saida.data.month)
        if key in totals:
            totals[key] += saida.valor

    return [
        ChartDataItem(
            label=_MESES_ABREV[m - 1].capitalize(),
            value=float(totals[key]),
        )
        for key in months_keys
        for y, m in [key]
    ]


def _weekly_series(saidas, today=None):
    today = today or date.today()
    items = []
    for w in range(3, -1, -1):
        newest = today - timedelta(days=7 * w)
        oldest = today - timedelta(days=7 * (w + 1) - 1)
        total = sum(float(g.valor) for g in saidas if oldest <= g.data <= newest)
        items.append(ChartDataItem(label=f"Sem {4 - w}", value=total))
    return items


def _category_breakdown(saidas):
    totais = {}
    for saida in saidas:
        label = saida.get_categoria_display()
        totais[label] = totais.get(label, Decimal("0.00")) + saida.valor

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

    max_value = max(float(item.value) for item in items) or 1.0
    if len(items) == 1:
        y = round(height - ((float(items[0].value) / max_value) * (height - 20)), 2)
        return f"0,{y} {width},{y}"

    step_x = width / (len(items) - 1)
    points = []
    for index, item in enumerate(items):
        x = round(index * step_x, 2)
        y = round(height - ((float(item.value) / max_value) * (height - 20)), 2)
        points.append(f"{x},{y}")
    return " ".join(points)


def build_area_fill(points, width=420, height=180):
    if not points:
        return ""
    return f"0,{height} {points} {width},{height}"


def build_pie_segments(items, width=420, height=180):
    if not items:
        return []

    radius = min(width, height) / 2 - 16
    cx = width / 2
    cy = height / 2
    total = sum(max(0.0, float(item.value)) for item in items)

    if total <= 0:
        return []

    segments = []
    start_angle = 0.0
    seg_idx = 0

    for item in items:
        value = float(item.value)
        if value <= 0:
            continue

        sweep = 360 * (value / total)
        end_angle = start_angle + sweep

        if sweep >= 359.99:
            r = radius
            d_path = (
                f"M {cx:.3f} {cy:.3f} L {cx + r:.3f} {cy:.3f} "
                f"A {r:.3f} {r:.3f} 0 1 1 {cx - r:.3f} {cy:.3f} "
                f"A {r:.3f} {r:.3f} 0 1 1 {cx + r:.3f} {cy:.3f} Z"
            )
        else:
            start_x = cx + radius * cos(radians(start_angle))
            start_y = cy + radius * sin(radians(start_angle))
            end_x = cx + radius * cos(radians(end_angle))
            end_y = cy + radius * sin(radians(end_angle))
            large_arc = 1 if sweep > 180 else 0
            d_path = (
                f"M {cx:.3f} {cy:.3f} L {start_x:.3f} {start_y:.3f} "
                f"A {radius:.3f} {radius:.3f} 0 {large_arc} 1 {end_x:.3f} {end_y:.3f} Z"
            )

        segments.append(
            {
                "d": d_path,
                "color": PALETA[seg_idx % len(PALETA)],
                "label": item.label,
                "value": item.value,
            }
        )
        seg_idx += 1
        start_angle = end_angle

    return segments


def build_dashboard_context(user, *, periodo_dias=None, categoria=None):
    desde = None
    if periodo_dias is not None:
        desde = date.today() - timedelta(days=int(periodo_dias))

    saidas = get_saidas(user, desde=desde, categoria=categoria or None)
    entradas = get_entradas(user, desde=desde)
    metas = get_metas(user)

    total_saidas = sum(s.valor for s in saidas)
    total_entradas = sum(e.valor for e in entradas)
    gasto_medio = total_saidas / Decimal(len(saidas) or 1)
    total_metas = sum(meta.valor_alvo for meta in metas)
    total_guardado = sum(meta.valor_atual for meta in metas)

    area_items = _monthly_series(saidas)
    line_items = _weekly_series(saidas)
    line_pts = build_chart_points(line_items, width=320, height=150)

    try:
        saldo_obj = Saldo.objects.filter(usuario=user).first() if user.is_authenticated else None
    except (OperationalError, Exception):
        saldo_obj = None

    return {
        "gastos": saidas,
        "ultimos_gastos": saidas[:5],
        "categorias_gasto": _category_breakdown(saidas),
        "total_gastos": total_saidas,
        "total_saidas": total_saidas,
        "total_entradas": total_entradas,
        "saldo": saldo_obj,
        "gasto_medio": gasto_medio,
        "total_metas": total_metas,
        "total_guardado": total_guardado,
        "percentual_guardado": int((total_guardado / (total_metas or Decimal("1.00"))) * 100),
        "area_chart_items": area_items,
        "pie_chart_segments": build_pie_segments(
            [
                ChartDataItem(label=item.categoria, value=float(item.total))
                for item in _category_breakdown(saidas)
            ],
            width=200,
            height=200,
        ),
        "area_chart_points": build_chart_points(area_items),
        "area_chart_fill": build_area_fill(build_chart_points(area_items)),
        "line_chart_items": line_items,
        "line_chart_points": line_pts,
        "line_chart_area_polygon": (
            f"0,150 {line_pts} 320,150" if line_pts else ""
        ),
        "line_chart_legend": [
            {
                "label": item.label,
                "value": item.value,
                "color": PALETA[i % len(PALETA)],
            }
            for i, item in enumerate(line_items)
        ],
        "metas": metas,
    }
