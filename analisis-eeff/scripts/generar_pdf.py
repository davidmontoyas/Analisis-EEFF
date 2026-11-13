#!/usr/bin/env python3
"""Genera el informe ejecutivo en PDF (ES o EN), de 2 a 4 páginas.

Sigue `referencias/plantilla-informe.md`, sección 2: resumen en la página 1,
análisis por grupo con gráficas, estructura financiera, recomendaciones,
metodología y aclaración final.

Uso:
    python generar_pdf.py datos_homologados.json resultados_indicadores.json --idioma es --textos textos_es.json
    python generar_pdf.py datos.json resultados.json --idioma en --textos textos_en.json --salida informe.pdf

Los textos los redacta Claude en `textos_<idioma>.json`. Es el mismo archivo
que usa `generar_excel.py`, con dos claves adicionales para el PDF:
    {
      "conclusion": "…",
      "hallazgos": [{"semaforo": "verde|amarillo|rojo", "titulo": "…", "detalle": "…"}],
      "grupos": {"liquidez": "…", "endeudamiento": "…", "rentabilidad": "…", "actividad": "…"},
      "estructura": "…",
      "alertas": ["…"],
      "advertencias": ["…"],   # opcional: las de resultados_indicadores.json, traducidas si el idioma es "en"
      "recomendaciones": ["…"],
      "titulos_graficas": {"liquidez": "…", "endeudamiento": "…", "rentabilidad": "…",
                           "actividad": "…", "financiacion": "…"},
      "preparado_por": "…"
    }

Requiere: reportlab, matplotlib
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import LETTER  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402
from reportlab.platypus import (Flowable, Image, KeepTogether, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_excel import CAMPOS_ERI, CAMPOS_ESF, NOMBRES_IND, slug  # noqa: E402

AZUL, AZUL_MEDIO, GRIS, GRIS_SECTOR = "#1F3A5F", "#4A7AB0", "#5F6B7A", "#A0AAB4"
COLOR_SEM = {"verde": "#2E7D32", "amarillo": "#F9A825", "rojo": "#C62828"}
# El ámbar sobre fondo blanco se lee mal en texto: la palabra va en un tono más oscuro.
COLOR_TEXTO_SEM = {"verde": "#2E7D32", "amarillo": "#A86B00", "rojo": "#C62828"}

_disponibles = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = next((f for f in ("Arial", "Helvetica", "Liberation Sans") if f in _disponibles),
                                   "DejaVu Sans")
MAX_PAGINAS = 4

T = {
    "es": {
        "titulo": "Análisis de Estados Financieros",
        "na": "n.a.",
        "nit": "NIT", "sector": "Sector CIIU", "corte": "Fecha de corte", "unidades": "Cifras en",
        "preparado": "Preparado por", "fecha_elab": "Fecha de elaboración",
        "conclusion": "Conclusión general", "hallazgos": "Hallazgos principales",
        "tabla_semaforo": "Semáforo de indicadores",
        "col": ["Indicador", "Sector (P50)", "Semáforo"],
        "sem": {"verde": "Favorable", "amarillo": "Atención", "rojo": "Crítico"},
        "grupos": {"liquidez": "Liquidez", "endeudamiento": "Endeudamiento",
                   "rentabilidad": "Rentabilidad", "actividad": "Actividad"},
        "sin_semaforo": "Indicadores sin semáforo sectorial",
        "estructura": "Estructura financiera",
        "col_estr": ["Partida", "Variación", "Variación %", "% del activo"],
        "recomendaciones": "Recomendaciones", "alertas": "Alertas",
        "metodologia": "Metodología y fuentes",
        "met": [
            "Rotaciones en días con base de {dias} días.",
            "Rotaciones y rentabilidades con saldos promedio (inicial + final) / 2 cuando hay dos periodos; "
            "con un solo periodo, saldos finales.",
            "Semáforo: donde más es mejor, verde desde la mediana del sector (P50), amarillo entre P25 y P50, "
            "rojo bajo P25; donde menos es mejor, verde hasta P50, amarillo entre P50 y P75, rojo sobre P75.",
        ],
        "fuente": "Fuente de los datos sectoriales: Superintendencia de Sociedades, año {anio}, {n} empresas ({nivel}).",
        "sin_fuente": "No se contó con rangos sectoriales; los indicadores no tienen semáforo.",
        "niveles": {"division": "división CIIU {c}", "seccion": "sección CIIU {c}", "nacional": "total nacional"},
        "aclaracion": "Este documento es un análisis financiero y no constituye una opinión de auditoría "
                      "ni un dictamen de revisoría fiscal.",
        "cifras_por": "Las cifras fueron suministradas por la administración de la empresa.",
        "unidades_txt": {"pesos": "pesos colombianos", "miles": "miles de pesos colombianos",
                         "millones": "millones de pesos colombianos"},
        "pagina": "Página {p} de {t}",
        "empresa_serie": "Empresa", "sector_serie": "Sector (P50)",
        "graf": {"liquidez": "Liquidez: empresa vs. sector", "endeudamiento": "Endeudamiento: empresa vs. sector",
                 "rentabilidad": "Márgenes de rentabilidad", "actividad": "Actividad (días): empresa vs. sector",
                 "financiacion": "Composición de la financiación"},
        "fuente_graf": "Fuente: estados financieros de la empresa y Supersociedades ({anio}).",
        "meses": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                  "septiembre", "octubre", "noviembre", "diciembre"],
        "archivo": "Informe_EEFF_{empresa}_{anio}_ES.pdf",
    },
    "en": {
        "titulo": "Financial Statement Analysis",
        "na": "n/a",
        "nit": "Tax ID (NIT)", "sector": "ISIC code", "corte": "Reporting date", "unidades": "Figures in",
        "preparado": "Prepared by", "fecha_elab": "Date of preparation",
        "conclusion": "Overall conclusion", "hallazgos": "Key findings",
        "tabla_semaforo": "Ratio traffic-light rating",
        "col": ["Ratio", "Industry (P50)", "Rating"],
        "sem": {"verde": "Favorable", "amarillo": "Watch", "rojo": "Critical"},
        "grupos": {"liquidez": "Liquidity", "endeudamiento": "Leverage",
                   "rentabilidad": "Profitability", "actividad": "Activity"},
        "sin_semaforo": "Ratios without industry rating",
        "estructura": "Financial structure",
        "col_estr": ["Line item", "Change", "Change %", "% of total assets"],
        "recomendaciones": "Recommendations", "alertas": "Warnings",
        "metodologia": "Methodology and sources",
        "met": [
            "Days ratios calculated on a {dias}-day basis.",
            "Turnover and return ratios use average balances (opening + closing) / 2 when two periods are "
            "available; with a single period, closing balances.",
            "Rating: where higher is better, green from the industry median (P50), amber between P25 and P50, "
            "red below P25; where lower is better, green up to P50, amber between P50 and P75, red above P75.",
        ],
        "fuente": "Industry data source: Supersociedades, year {anio}, {n} companies ({nivel}).",
        "sin_fuente": "No industry ranges were available; ratios have no rating.",
        "niveles": {"division": "ISIC division {c}", "seccion": "ISIC section {c}", "nacional": "national total"},
        "aclaracion": "This document is a financial analysis and does not constitute an audit opinion "
                      "or a statutory auditor's report.",
        "cifras_por": "Figures were provided by the company's management.",
        "unidades_txt": {"pesos": "Colombian pesos (COP)", "miles": "thousands of Colombian pesos (COP thousands)",
                         "millones": "millions of Colombian pesos (COP millions)"},
        "pagina": "Page {p} of {t}",
        "empresa_serie": "Company", "sector_serie": "Industry (P50)",
        "graf": {"liquidez": "Liquidity: company vs. industry", "endeudamiento": "Leverage: company vs. industry",
                 "rentabilidad": "Profitability margins", "actividad": "Activity (days): company vs. industry",
                 "financiacion": "Funding structure"},
        "fuente_graf": "Source: company financial statements and Supersociedades ({anio}).",
        "meses": ["January", "February", "March", "April", "May", "June", "July", "August",
                  "September", "October", "November", "December"],
        "archivo": "Financial_Report_{empresa}_{anio}_EN.pdf",
    },
}

GRUPOS = {
    "liquidez": ["razon_corriente", "prueba_acida"],
    "endeudamiento": ["nivel_endeudamiento", "concentracion_cp"],
    "rentabilidad": ["margen_bruto", "margen_operacional", "margen_neto"],
    "actividad": ["dias_cartera", "dias_inventario", "dias_proveedores", "ciclo_efectivo"],
}


# --------------------------------------------------------------------------
# Formato numérico (glosario-es-en.md, sección 8)
# --------------------------------------------------------------------------

def _local(texto: str, idioma: str) -> str:
    if idioma == "es":
        return texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return texto


def fmt(valor: float | None, unidad: str, idioma: str, na: str) -> str:
    if valor is None:
        return na
    if unidad == "%":
        texto = f"{valor * 100:,.1f}%"
    elif unidad == "veces":
        texto = f"{valor:,.2f}" + ("x" if idioma == "en" else "")
    elif unidad == "dias":
        texto = f"{valor:,.0f}"
    else:
        texto = f"{abs(valor):,.0f}"
        if valor < 0:
            texto = f"({texto})"
    return _local(texto, idioma)


def fecha_larga(iso: str, idioma: str) -> str:
    a, m, d = (int(x) for x in iso[:10].split("-"))
    mes = T[idioma]["meses"][m - 1]
    return f"{d} de {mes} de {a}" if idioma == "es" else f"{mes} {d}, {a}"


# --------------------------------------------------------------------------
# Estilos
# --------------------------------------------------------------------------

def estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=13.5, alignment=TA_LEFT)
    return {
        "base": base,
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22,
                                 textColor=colors.HexColor(AZUL), spaceAfter=4),
        "empresa": ParagraphStyle("empresa", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=15),
        "meta": ParagraphStyle("meta", parent=base, fontSize=8.5, leading=11, textColor=colors.HexColor(GRIS)),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                             textColor=colors.HexColor(AZUL), spaceBefore=10, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                             textColor=colors.HexColor(AZUL), spaceBefore=6, spaceAfter=2),
        "celda": ParagraphStyle("celda", parent=base, fontSize=8.5, leading=10.5),
        "celda_b": ParagraphStyle("celda_b", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=10.5),
        "nota": ParagraphStyle("nota", parent=base, fontSize=8, leading=10.5, textColor=colors.HexColor(GRIS)),
        "aclaracion": ParagraphStyle("aclaracion", parent=base, fontName="Helvetica-Oblique", fontSize=8.5,
                                     leading=11),
    }


def esc(texto: str) -> str:
    return (texto or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Semaforo(Flowable):
    """Círculo de color + palabra: legible impreso en blanco y negro y para personas con daltonismo."""

    def __init__(self, clave: str | None, idioma: str, tamano: float = 8.5):
        super().__init__()
        self.clave, self.texto, self.tamano = clave, T[idioma]["sem"].get(clave, "") if clave else "", tamano
        self.width, self.height = 2.6 * cm, tamano * 1.25

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        if not self.clave:
            return
        c = self.canv
        radio = self.tamano * 0.38
        c.setFillColor(colors.HexColor(COLOR_SEM[self.clave]))
        c.circle(radio, self.height / 2 - 0.5, radio, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(COLOR_TEXTO_SEM[self.clave]))
        c.setFont("Helvetica-Bold", self.tamano)
        c.drawString(radio * 2 + 3, self.height / 2 - self.tamano * 0.35, self.texto)


# --------------------------------------------------------------------------
# Gráficas (plantilla-informe.md, sección 4)
# --------------------------------------------------------------------------

def _figura(ancho_cm: float = 16.5, alto_cm: float = 4.8):
    fig, ax = plt.subplots(figsize=(ancho_cm / 2.54, alto_cm / 2.54), dpi=200)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#C8CED6")
    ax.tick_params(colors="#333333", labelsize=7.5)
    return fig, ax


def _a_imagen(fig, ancho_cm: float = 16.5, alto_cm: float = 4.8) -> Image:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=ancho_cm * cm, height=alto_cm * cm)


def grafica_barras(ids: list[str], res: dict, idioma: str, titulo: str, horizontal: bool = False) -> Image:
    t, na = T[idioma], T[idioma]["na"]
    ind, corte = res["indicadores"], res["fecha_corte"]
    nombres = [NOMBRES_IND[i][0 if idioma == "es" else 1] for i in ids]
    empresa = [ind[i]["periodos"][corte]["valor"] for i in ids]
    sector = [(ind[i]["sector"] or {}).get("p50") for i in ids]
    unidad = ind[ids[0]]["unidad"]
    escala = 100 if unidad == "%" else 1
    fig, ax = _figura()
    pos = list(range(len(ids)))
    ancho = 0.36
    hay_sector = any(s is not None for s in sector)
    series = [(t["empresa_serie"], empresa, AZUL, -ancho / 2 if hay_sector else 0)]
    if hay_sector:
        series.append((t["sector_serie"], sector, GRIS_SECTOR, ancho / 2))
    for nombre, valores, color, desp in series:
        xs = [p + desp for p, v in zip(pos, valores) if v is not None]
        vs = [v * escala for v in valores if v is not None]
        barras = (ax.barh if horizontal else ax.bar)(xs, vs, ancho, color=color, label=nombre)
        etiquetas = [fmt(v, unidad, idioma, na) for v in valores if v is not None]
        ax.bar_label(barras, labels=etiquetas, padding=2, fontsize=7.5, color="#333333")
    if horizontal:
        ax.set_yticks(pos, nombres)
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        ax.margins(x=0.15)
    else:
        ax.set_xticks(pos, nombres)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)
        ax.margins(y=0.2)
        if ids[0] == "razon_corriente":
            ax.axhline(1.0, color=GRIS, linestyle="--", linewidth=0.7, zorder=0)
    ax.set_title(titulo, fontsize=9.5, color=AZUL, fontweight="bold", loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    return _a_imagen(fig)


def grafica_margenes(res: dict, idioma: str, titulo: str) -> Image:
    na = T[idioma]["na"]
    ind, periodos = res["indicadores"], res["periodos"]
    fig, ax = _figura()
    anios = [p[:4] for p in periodos]
    for k, color in zip(GRUPOS["rentabilidad"], (AZUL, AZUL_MEDIO, GRIS_SECTOR)):
        valores = [ind[k]["periodos"][p]["valor"] for p in periodos]
        xs = [a for a, v in zip(anios, valores) if v is not None]
        ys = [v * 100 for v in valores if v is not None]
        ax.plot(xs, ys, marker="o", color=color, linewidth=2, label=NOMBRES_IND[k][0 if idioma == "es" else 1])
        # El margen neto (normalmente el más bajo) lleva la etiqueta debajo para no chocar con el operacional.
        abajo = k == "margen_neto"
        for x, v in zip(xs, [v for v in valores if v is not None]):
            ax.annotate(fmt(v, "%", idioma, na), (x, v * 100), textcoords="offset points",
                        xytext=(0, -10 if abajo else 5), va="top" if abajo else "bottom",
                        ha="center", fontsize=7.5, color="#333333")
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.margins(y=0.45, x=0.15)  # espacio para la etiqueta del margen neto sobre el eje
    ax.set_title(titulo, fontsize=9.5, color=AZUL, fontweight="bold", loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    return _a_imagen(fig)


def grafica_financiacion(datos: dict, idioma: str, titulo: str) -> Image:
    partes = ["pasivo_corriente", "pasivo_no_corriente", "patrimonio"]
    nombres = {c: (es if idioma == "es" else en) for c, es, en, _ in CAMPOS_ESF}
    fig, ax = _figura(alto_cm=3.6)
    anios = [p["fecha_corte"][:4] for p in datos["periodos"]]
    izquierda = [0.0] * len(anios)
    for campo, color in zip(partes, (AZUL, AZUL_MEDIO, GRIS_SECTOR)):
        pct = []
        for p in datos["periodos"]:
            valores = [max(p["esf"].get(c) or 0, 0) for c in partes]
            total = sum(valores)
            pct.append(max(p["esf"].get(campo) or 0, 0) / total if total else 0)
        barras = ax.barh(anios, pct, left=izquierda, color=color, label=nombres[campo].replace("Total ", "").capitalize())
        ax.bar_label(barras, labels=[fmt(v, "%", idioma, "") if v >= 0.06 else "" for v in pct],
                     label_type="center", fontsize=7.5, color="white")
        izquierda = [a + b for a, b in zip(izquierda, pct)]
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_xlim(0, 1)
    ax.spines["bottom"].set_visible(False)
    ax.set_title(titulo, fontsize=9.5, color=AZUL, fontweight="bold", loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
    return _a_imagen(fig, alto_cm=3.6)


# --------------------------------------------------------------------------
# Informe
# --------------------------------------------------------------------------

class Informe:
    def __init__(self, datos: dict, res: dict, textos: dict, idioma: str):
        self.d, self.r, self.tx, self.l = datos, res, textos, idioma
        self.t, self.e = T[idioma], estilos()
        self.na = self.t["na"]
        self.corte = res["fecha_corte"]
        self.titulos = {**self.t["graf"], **textos.get("titulos_graficas", {})}
        anios = [s["anio"] for s in (i.get("sector") for i in res["indicadores"].values()) if s]
        self.anio_sector = max(anios) if anios else None

    def nombre_ind(self, id_: str) -> str:
        return NOMBRES_IND[id_][0 if self.l == "es" else 1]

    def valor(self, id_: str, fecha: str | None = None) -> str:
        info = self.r["indicadores"][id_]
        return fmt(info["periodos"][fecha or self.corte]["valor"], info["unidad"], self.l, self.na)

    # ---- Página 1 -------------------------------------------------------------
    def encabezado(self) -> list:
        t, d, e = self.t, self.d, self.e
        unidades = t["unidades_txt"].get(d.get("unidades", "pesos"), d.get("unidades", ""))
        partes = [f"{t['nit']}: {esc(d.get('nit') or '')}", f"{t['sector']}: {esc(self.r.get('ciiu') or '')}",
                  f"{t['corte']}: {fecha_larga(self.corte, self.l)}", f"{t['unidades']} {unidades}"]
        firma = [f"{t['fecha_elab']}: {fecha_larga(date.today().isoformat(), self.l)}"]
        if self.tx.get("preparado_por"):
            firma.insert(0, f"{t['preparado']}: {esc(self.tx['preparado_por'])}")
        return [Paragraph(t["titulo"], e["titulo"]), Paragraph(esc(d.get("empresa") or ""), e["empresa"]),
                Paragraph(" · ".join(partes), e["meta"]), Paragraph(" · ".join(firma), e["meta"]),
                Spacer(1, 4)]

    def resumen(self) -> list:
        t, e = self.t, self.e
        flujo = []
        if self.tx.get("conclusion"):
            flujo += [Paragraph(t["conclusion"], e["h1"]), Paragraph(esc(self.tx["conclusion"]), e["base"])]
        hallazgos = self.tx.get("hallazgos", [])[:5]
        if hallazgos:
            flujo.append(Paragraph(t["hallazgos"], e["h1"]))
            filas = [[Semaforo(h.get("semaforo"), self.l),
                      Paragraph(f"<b>{esc(h.get('titulo', ''))}</b><br/>{esc(h.get('detalle', ''))}", e["celda"])]
                     for h in hallazgos]
            tabla = Table(filas, colWidths=[2.6 * cm, 14.9 * cm])
            tabla.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#DDE2E8")),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ]))
            flujo.append(tabla)
        flujo += [Paragraph(t["tabla_semaforo"], e["h1"]), self.tabla_semaforo()]
        return flujo

    def tabla_semaforo(self) -> Table:
        t, e = self.t, self.e
        periodos = self.r["periodos"][-2:]
        cab = [t["col"][0]] + [p[:4] for p in periodos] + t["col"][1:]
        filas = [[Paragraph(f"<b>{c}</b>", ParagraphStyle("cab", parent=e["celda_b"], textColor=colors.white))
                  for c in cab]]
        der = ParagraphStyle("der", parent=e["celda"], alignment=2)
        for id_, info in self.r["indicadores"].items():
            if info["direccion"] == "ninguna":
                continue
            s = info.get("sector")
            filas.append([Paragraph(self.nombre_ind(id_), e["celda"])] +
                         [Paragraph(self.valor(id_, p), der) for p in periodos] +
                         [Paragraph(fmt(s["p50"], info["unidad"], self.l, self.na) if s else self.na, der),
                          Semaforo(info.get("semaforo"), self.l)])
        anchos = [6.6 * cm] + [2.2 * cm] * len(periodos) + [2.6 * cm, 3.0 * cm]
        tabla = Table(filas, colWidths=anchos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL)),
            ("ALIGN", (1, 0), (-2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ]
        for k in range(2, len(filas), 2):
            estilo.append(("BACKGROUND", (0, k), (-1, k), colors.HexColor("#F3F5F8")))
        tabla.setStyle(TableStyle(estilo))
        return tabla

    # ---- Análisis por grupo -----------------------------------------------------------
    def grupos(self, con_actividad_grafica: bool = True) -> list:
        t, e = self.t, self.e
        flujo = []
        parrafos = self.tx.get("grupos", {})
        for grupo, ids in GRUPOS.items():
            bloque = [Paragraph(t["grupos"][grupo], e["h1"])]
            if parrafos.get(grupo):
                bloque.append(Paragraph(esc(parrafos[grupo]), e["base"]))
                bloque.append(Spacer(1, 4))
            if grupo == "rentabilidad" and len(self.r["periodos"]) > 1:
                bloque.append(grafica_margenes(self.r, self.l, self.titulos["rentabilidad"]))
            elif grupo != "actividad" or con_actividad_grafica:
                bloque.append(grafica_barras(ids, self.r, self.l, self.titulos[grupo],
                                             horizontal=grupo == "actividad"))
            sin = [i for i, info in self.r["indicadores"].items()
                   if info["grupo"] == grupo and info["direccion"] == "ninguna"]
            if sin:
                bloque.append(self.tabla_sin_semaforo(sin))
            flujo.append(KeepTogether(bloque))
        return flujo

    def tabla_sin_semaforo(self, ids: list[str]) -> Table:
        e = self.e
        periodos = self.r["periodos"][-2:]
        filas = [[Paragraph(f"<i>{self.t['sin_semaforo']}</i>", e["nota"])] + [Paragraph(p[:4], e["nota"]) for p in periodos]]
        for id_ in ids:
            filas.append([Paragraph(self.nombre_ind(id_), e["celda"])] +
                         [Paragraph(self.valor(id_, p), ParagraphStyle("d", parent=e["celda"], alignment=2))
                          for p in periodos])
        tabla = Table(filas, colWidths=[8 * cm] + [2.6 * cm] * len(periodos), hAlign="LEFT")
        tabla.setStyle(TableStyle([("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                                   ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#C8CED6")),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
        return tabla

    # ---- Estructura financiera ---------------------------------------------------------
    def estructura(self, n_partidas: int = 5) -> list:
        t, e = self.t, self.e
        flujo = [Paragraph(t["estructura"], e["h1"])]
        if self.tx.get("estructura"):
            flujo += [Paragraph(esc(self.tx["estructura"]), e["base"]), Spacer(1, 4)]
        flujo.append(grafica_financiacion(self.d, self.l, self.titulos["financiacion"]))
        if not self.r["horizontal"]:
            return [KeepTogether(flujo)]
        h = self.r["horizontal"][-1]
        vert = self.r["vertical"][self.corte]
        etiquetas = {c: (es if self.l == "es" else en) for c, es, en, tot in CAMPOS_ESF + CAMPOS_ERI if not tot}
        candidatas = []
        for seccion in ("esf",):  # solo el balance: la estructura financiera
            for campo, v in h[seccion].items():
                if campo in etiquetas and v["absoluta"] is not None and campo != "resultado_ejercicio":
                    candidatas.append((abs(v["absoluta"]), seccion, campo, v))
        candidatas.sort(reverse=True)
        filas = [[Paragraph(f"<b>{c}</b>", ParagraphStyle("c", parent=e["celda_b"], textColor=colors.white))
                  for c in t["col_estr"]]]
        for _, seccion, campo, v in candidatas[:n_partidas]:
            filas.append([Paragraph(etiquetas[campo], e["celda"]),
                          Paragraph(fmt(v["absoluta"], "COP", self.l, self.na), ParagraphStyle("d", parent=e["celda"], alignment=2)),
                          Paragraph(fmt(v["relativa"], "%", self.l, self.na), ParagraphStyle("d", parent=e["celda"], alignment=2)),
                          Paragraph(fmt(vert[seccion].get(campo), "%", self.l, self.na), ParagraphStyle("d", parent=e["celda"], alignment=2))])
        tabla = Table(filas, colWidths=[7.5 * cm, 3.4 * cm, 3.0 * cm, 3.0 * cm], hAlign="LEFT")
        tabla.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AZUL)),
                                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        flujo += [Spacer(1, 4), tabla]
        return [KeepTogether(flujo)]

    # ---- Cierre ------------------------------------------------------------------------
    def cierre(self) -> list:
        t, e = self.t, self.e
        flujo = []
        if self.tx.get("recomendaciones"):
            flujo.append(Paragraph(t["recomendaciones"], e["h1"]))
            for k, rec in enumerate(self.tx["recomendaciones"], 1):
                flujo.append(Paragraph(f"<b>{k}.</b> {esc(rec)}", e["base"]))
                flujo.append(Spacer(1, 3))
        if self.tx.get("alertas"):
            flujo.append(Paragraph(t["alertas"], e["h1"]))
            for alerta in self.tx["alertas"]:
                flujo.append(Paragraph(f'<font color="{COLOR_SEM["rojo"]}"><b>!</b></font> {esc(alerta)}', e["base"]))
        # Metodología y aclaración van juntas: la aclaración nunca queda sola en una página.
        metodologia = [Paragraph(t["metodologia"], e["h2"])]
        dias = self.d["periodos"][-1].get("dias_periodo") or 360
        # Las advertencias de calcular_indicadores.py están en español; para otro idioma, Claude las traduce en textos.
        advertencias = self.tx.get("advertencias", self.r.get("advertencias", []))
        lineas = [m.format(dias=dias) for m in t["met"]] + [self.fuente()] + list(advertencias)
        for linea in lineas:
            metodologia.append(Paragraph(f"• {esc(linea)}", e["nota"]))
        metodologia += [Spacer(1, 8), Paragraph(t["cifras_por"], e["aclaracion"]),
                        Paragraph(t["aclaracion"], e["aclaracion"])]
        flujo.append(KeepTogether(metodologia))
        return flujo

    def fuente(self) -> str:
        sectores = [i["sector"] for i in self.r["indicadores"].values() if i.get("sector")]
        if not sectores:
            return self.t["sin_fuente"]
        niveles = []
        for s in sectores:
            texto = self.t["niveles"][s["nivel"]].format(c=s["codigo"])
            if texto not in niveles:
                niveles.append(texto)
        ns = sorted({s["n_empresas"] for s in sectores})
        n = str(ns[0]) if len(ns) == 1 else f"{ns[0]}–{ns[-1]}"
        return self.t["fuente"].format(anio=self.anio_sector, n=n, nivel=", ".join(niveles))

    # ---- Construcción ----------------------------------------------------------------
    def historia(self, n_partidas: int = 5, actividad: bool = True) -> list:
        return (self.encabezado() + self.resumen() + [PageBreak()] + self.grupos(actividad) +
                self.estructura(n_partidas) + self.cierre())

    def construir(self, destino: Path) -> int:
        """Genera el PDF; si pasa de 4 páginas, recorta según plantilla-informe.md. Devuelve las páginas."""
        pie = f"{self.d.get('empresa') or ''} · {fecha_larga(self.corte, self.l)}"
        paginas = 0
        for n_partidas, actividad in ((5, True), (3, True), (3, False)):
            paginas = self._construir(destino, pie, self.historia(n_partidas, actividad))
            if paginas <= MAX_PAGINAS:
                break
        return paginas

    def _construir(self, destino: Path, pie: str, historia: list) -> int:
        total = {"n": 0}
        texto_pagina = self.t["pagina"]

        class Lienzo(rl_canvas.Canvas):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self._paginas = []

            def showPage(self):
                self._paginas.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                total["n"] = len(self._paginas)
                for estado in self._paginas:
                    self.__dict__.update(estado)
                    self.setFont("Helvetica", 7.5)
                    self.setFillColor(colors.HexColor(GRIS))
                    self.drawString(2 * cm, 1.2 * cm, pie)
                    self.drawRightString(LETTER[0] - 2 * cm, 1.2 * cm,
                                         texto_pagina.format(p=self._pageNumber, t=total["n"]))
                    super().showPage()
                super().save()

        doc = SimpleDocTemplate(str(destino), pagesize=LETTER, leftMargin=2 * cm, rightMargin=2 * cm,
                                topMargin=2 * cm, bottomMargin=2 * cm, title=self.t["titulo"],
                                author=self.tx.get("preparado_por", ""))
        doc.build(historia, canvasmaker=Lienzo)
        return total["n"]


def nombre_archivo(datos: dict, idioma: str) -> str:
    anio = sorted(p["fecha_corte"] for p in datos["periodos"])[-1][:4]
    return T[idioma]["archivo"].format(empresa=slug(datos.get("empresa", "")), anio=anio)


def generar(datos: dict, resultados: dict, idioma: str, textos: dict | None = None,
            salida: Path | None = None, carpeta: Path | None = None) -> tuple[Path, int]:
    datos = {**datos, "periodos": sorted(datos["periodos"], key=lambda p: p["fecha_corte"])}
    destino = salida or (carpeta or Path.cwd()) / nombre_archivo(datos, idioma)
    paginas = Informe(datos, resultados, textos or {}, idioma).construir(destino)
    return destino, paginas


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Genera el informe ejecutivo en PDF.")
    parser.add_argument("datos", type=Path, help="datos_homologados.json")
    parser.add_argument("resultados", type=Path, help="resultados_indicadores.json")
    parser.add_argument("--idioma", choices=["es", "en"], required=True)
    parser.add_argument("--textos", type=Path, help="JSON con conclusión, hallazgos, párrafos y recomendaciones")
    parser.add_argument("--salida", type=Path, help="Ruta del archivo .pdf")
    args = parser.parse_args(argv)
    try:
        datos = json.loads(args.datos.read_text(encoding="utf-8-sig"))
        resultados = json.loads(args.resultados.read_text(encoding="utf-8-sig"))
        textos = json.loads(args.textos.read_text(encoding="utf-8-sig")) if args.textos else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error leyendo las entradas: {exc}", file=sys.stderr)
        return 1
    if not textos:
        print("Aviso: sin --textos el informe no tendrá conclusión, hallazgos ni recomendaciones.", file=sys.stderr)
    destino, paginas = generar(datos, resultados, args.idioma, textos, args.salida, args.datos.parent)
    print(f"PDF generado: {destino} ({paginas} páginas)")
    if paginas > MAX_PAGINAS:
        print(f"Aviso: el informe tiene {paginas} páginas; acorta los textos para dejarlo en {MAX_PAGINAS}.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
