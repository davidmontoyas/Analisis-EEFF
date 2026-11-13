#!/usr/bin/env python3
"""Genera el libro de Excel del análisis financiero (ES o EN).

Sigue la estructura de `referencias/plantilla-informe.md`, sección 3: 8 hojas,
fórmulas vivas sobre la hoja `Datos`, semáforo con fórmula y gráficas nativas
de Excel.

Uso:
    python generar_excel.py datos_homologados.json resultados_indicadores.json --idioma es
    python generar_excel.py datos.json resultados.json --idioma en --textos textos_en.json
    python generar_excel.py datos.json resultados.json --idioma es --salida mi_archivo.xlsx

Entradas:
    datos_homologados.json      formato de `referencias/homologacion-puc.md`
    resultados_indicadores.json salida de `calcular_indicadores.py`
    textos_<idioma>.json        opcional, redactado por Claude:
        {
          "conclusion": "…",
          "hallazgos": [{"semaforo": "verde|amarillo|rojo", "titulo": "…", "detalle": "…"}],
          "interpretaciones": {"razon_corriente": "…", …},
          "recomendaciones": ["…"],
          "titulos_graficas": {"liquidez": "…", "endeudamiento": "…", "rentabilidad": "…",
                               "actividad": "…", "activo": "…", "financiacion": "…"},
          "preparado_por": "…"
        }

Requiere: openpyxl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

# --------------------------------------------------------------------------
# Estilo (plantilla-informe.md)
# --------------------------------------------------------------------------

AZUL = "1F3A5F"
GRIS = "5F6B7A"
GRIS_SECTOR = "A0AAB4"
AMARILLO_ENTRADA = "FFF8E1"
VERDE, AMBAR, ROJO = "2E7D32", "F9A825", "C62828"

F_TITULO = Font(name="Arial", size=14, bold=True, color=AZUL)
F_SUBTITULO = Font(name="Arial", size=11, bold=True, color=AZUL)
F_ENCABEZADO = Font(name="Arial", size=10, bold=True, color="FFFFFF")
F_NORMAL = Font(name="Arial", size=10)
F_TOTAL = Font(name="Arial", size=10, bold=True)
F_NOTA = Font(name="Arial", size=8, color=GRIS)
RELLENO_ENC = PatternFill("solid", fgColor=AZUL)
RELLENO_ENTRADA = PatternFill("solid", fgColor=AMARILLO_ENTRADA)
RELLENO_SECCION = PatternFill("solid", fgColor="E8EDF3")
BORDE_TOTAL = Border(top=Side(style="thin", color=AZUL))
AJUSTE = Alignment(wrap_text=True, vertical="top")

FMT_COP = '#,##0;(#,##0);"-"'
FMT_PCT = '0.0%;(0.0%)'
FMT_VECES = '0.00'
FMT_DIAS = '0'
FORMATOS = {"COP": FMT_COP, "%": FMT_PCT, "veces": FMT_VECES, "dias": FMT_DIAS}

# --------------------------------------------------------------------------
# Textos por idioma (glosario-es-en.md)
# --------------------------------------------------------------------------

T = {
    "es": {
        "hojas": ["Resumen", "Datos", "Vertical", "Horizontal", "Indicadores", "Sector", "Gráficas", "Notas"],
        "titulo": "Análisis de Estados Financieros",
        "na": "n.a.",
        "empresa": "Empresa", "nit": "NIT", "ciiu": "Sector (CIIU)", "corte": "Fecha de corte",
        "unidades": "Unidades", "marco": "Marco normativo", "preparado": "Preparado por",
        "fecha_elab": "Fecha de elaboración",
        "conclusion": "Conclusión general", "hallazgos": "Hallazgos principales",
        "tabla_semaforo": "Semáforo de indicadores", "recomendaciones": "Recomendaciones",
        "concepto": "Concepto", "campo": "Campo", "esf": "Estado de Situación Financiera",
        "eri": "Estado de Resultados Integral", "dias_periodo": "Días del periodo",
        "nota_datos": "Las celdas amarillas son las únicas que se digitan. Al cambiarlas, todo el libro se recalcula.",
        "pct_activo": "% del activo total / % de los ingresos",
        "var_abs": "Variación absoluta", "var_rel": "Variación %",
        "col_ind": ["Grupo", "Indicador", "Fórmula"], "variacion": "Variación",
        "p25": "Sector P25", "p50": "Sector P50", "p75": "Sector P75", "direccion": "Dirección",
        "semaforo": "Semáforo", "interpretacion": "Interpretación",
        "col_sector": ["Indicador", "Nivel CIIU", "Código", "Año", "N.º empresas", "P25", "P50", "P75"],
        "niveles": {"division": "División", "seccion": "Sección", "nacional": "Nacional"},
        "dir": {"mas": "Más es mejor", "menos": "Menos es mejor", "ninguna": "Sin semáforo"},
        "sem": {"verde": "🟢 Favorable", "amarillo": "🟡 Atención", "rojo": "🔴 Crítico"},
        "grupos": {"liquidez": "Liquidez", "endeudamiento": "Endeudamiento",
                   "rentabilidad": "Rentabilidad", "actividad": "Actividad"},
        "empresa_serie": "Empresa", "sector_serie": "Sector (P50)",
        "graf": {"liquidez": "Liquidez: empresa vs. sector", "endeudamiento": "Endeudamiento: empresa vs. sector",
                 "rentabilidad": "Márgenes de rentabilidad", "actividad": "Actividad (días): empresa vs. sector",
                 "activo": "Composición del activo", "financiacion": "Composición de la financiación"},
        "fuente_graf": "Fuente: estados financieros de la empresa y Supersociedades ({anio}).",
        "notas": "Notas", "advertencias": "Advertencias", "metodologia": "Metodología",
        "met": [
            "Rotaciones en días con base de {dias} días.",
            "Rotaciones y rentabilidades con saldos promedio (inicial + final) / 2 cuando hay dos periodos; "
            "con un solo periodo, saldos finales.",
            "Semáforo: indicadores donde más es mejor → verde ≥ P50, amarillo entre P25 y P50, rojo < P25. "
            "Donde menos es mejor → verde ≤ P50, amarillo entre P50 y P75, rojo > P75.",
            "Rangos sectoriales: Superintendencia de Sociedades, por división CIIU; sección CIIU o total "
            "nacional cuando la división tiene menos de 30 empresas.",
            "Los formatos numéricos siguen la configuración regional de Excel de quien abre el archivo.",
        ],
        "aclaracion": "Este documento es un análisis financiero y no constituye una opinión de auditoría "
                      "ni un dictamen de revisoría fiscal.",
        "cifras_por": "Las cifras fueron suministradas por la administración de la empresa.",
        "unidades_txt": {"pesos": "Pesos colombianos (COP)", "miles": "Miles de pesos colombianos",
                         "millones": "Millones de pesos colombianos"},
        "archivo": "Analisis_EEFF_{empresa}_{anio}_ES.xlsx",
    },
    "en": {
        "hojas": ["Summary", "Data", "Vertical", "Horizontal", "Ratios", "Industry", "Charts", "Notes"],
        "titulo": "Financial Statement Analysis",
        "na": "n/a",
        "empresa": "Company", "nit": "Tax ID number (NIT)", "ciiu": "Industry (ISIC code)",
        "corte": "Reporting date", "unidades": "Units", "marco": "Reporting framework",
        "preparado": "Prepared by", "fecha_elab": "Date of preparation",
        "conclusion": "Overall conclusion", "hallazgos": "Key findings",
        "tabla_semaforo": "Ratio traffic-light rating", "recomendaciones": "Recommendations",
        "concepto": "Line item", "campo": "Field", "esf": "Statement of Financial Position",
        "eri": "Statement of Comprehensive Income", "dias_periodo": "Days in period",
        "nota_datos": "Yellow cells are the only input cells. When you change them, the whole workbook recalculates.",
        "pct_activo": "% of total assets / % of revenue",
        "var_abs": "Absolute change", "var_rel": "Percentage change",
        "col_ind": ["Group", "Ratio", "Formula"], "variacion": "Change",
        "p25": "Industry P25", "p50": "Industry P50", "p75": "Industry P75", "direccion": "Direction",
        "semaforo": "Rating", "interpretacion": "Interpretation",
        "col_sector": ["Ratio", "ISIC level", "Code", "Year", "No. of companies", "P25", "P50", "P75"],
        "niveles": {"division": "Division", "seccion": "Section", "nacional": "National"},
        "dir": {"mas": "Higher is better", "menos": "Lower is better", "ninguna": "No rating"},
        "sem": {"verde": "🟢 Favorable", "amarillo": "🟡 Watch", "rojo": "🔴 Critical"},
        "grupos": {"liquidez": "Liquidity", "endeudamiento": "Leverage",
                   "rentabilidad": "Profitability", "actividad": "Activity"},
        "empresa_serie": "Company", "sector_serie": "Industry (P50)",
        "graf": {"liquidez": "Liquidity: company vs. industry", "endeudamiento": "Leverage: company vs. industry",
                 "rentabilidad": "Profitability margins", "actividad": "Activity (days): company vs. industry",
                 "activo": "Asset structure", "financiacion": "Funding structure"},
        "fuente_graf": "Source: company financial statements and Supersociedades ({anio}).",
        "notas": "Notes", "advertencias": "Warnings", "metodologia": "Methodology",
        "met": [
            "Days ratios calculated on a {dias}-day basis.",
            "Turnover and return ratios use average balances (opening + closing) / 2 when two periods are "
            "available; with a single period, closing balances.",
            "Rating: where higher is better → green ≥ P50, amber between P25 and P50, red < P25. "
            "Where lower is better → green ≤ P50, amber between P50 and P75, red > P75.",
            "Industry ranges: Superintendence of Companies (Supersociedades), by ISIC division; ISIC section "
            "or national total when the division has fewer than 30 companies.",
            "Number formats follow the regional settings of the Excel installation that opens the file.",
        ],
        "aclaracion": "This document is a financial analysis and does not constitute an audit opinion "
                      "or a statutory auditor's report.",
        "cifras_por": "Figures were provided by the company's management.",
        "unidades_txt": {"pesos": "Colombian pesos (COP)", "miles": "Thousands of Colombian pesos (COP thousands)",
                         "millones": "Millions of Colombian pesos (COP millions)"},
        "archivo": "Financial_Analysis_{empresa}_{anio}_EN.xlsx",
    },
}

# (id, ES, EN, es_total)
CAMPOS_ESF = [
    ("efectivo", "Efectivo y equivalentes al efectivo", "Cash and cash equivalents", False),
    ("inversiones_cp", "Inversiones de corto plazo", "Short-term investments", False),
    ("deudores_comerciales", "Deudores comerciales", "Trade receivables", False),
    ("otras_cuentas_por_cobrar_cp", "Otras cuentas por cobrar", "Other receivables", False),
    ("activos_por_impuestos_cp", "Activos por impuestos corrientes", "Current tax assets", False),
    ("inventarios", "Inventarios", "Inventories", False),
    ("otros_activos_cp", "Otros activos corrientes", "Other current assets", False),
    ("activo_corriente", "Total activo corriente", "Total current assets", True),
    ("ppe", "Propiedades, planta y equipo", "Property, plant and equipment", False),
    ("intangibles", "Activos intangibles", "Intangible assets", False),
    ("inversiones_lp", "Inversiones de largo plazo", "Long-term investments", False),
    ("otros_activos_lp", "Otros activos no corrientes", "Other non-current assets", False),
    ("activo_no_corriente", "Total activo no corriente", "Total non-current assets", True),
    ("activo_total", "Total activo", "Total assets", True),
    ("obligaciones_financieras_cp", "Obligaciones financieras corrientes", "Current borrowings", False),
    ("proveedores", "Proveedores", "Trade payables", False),
    ("otras_cuentas_por_pagar_cp", "Otras cuentas por pagar", "Other payables", False),
    ("pasivos_por_impuestos_cp", "Pasivos por impuestos corrientes", "Current tax liabilities", False),
    ("obligaciones_laborales", "Beneficios a empleados", "Employee benefits", False),
    ("otros_pasivos_cp", "Otros pasivos corrientes", "Other current liabilities", False),
    ("pasivo_corriente", "Total pasivo corriente", "Total current liabilities", True),
    ("obligaciones_financieras_lp", "Obligaciones financieras no corrientes", "Non-current borrowings", False),
    ("otros_pasivos_lp", "Otros pasivos no corrientes", "Other non-current liabilities", False),
    ("pasivo_no_corriente", "Total pasivo no corriente", "Total non-current liabilities", True),
    ("pasivo_total", "Total pasivo", "Total liabilities", True),
    ("capital", "Capital social", "Share capital", False),
    ("reservas", "Reservas", "Reserves", False),
    ("resultado_ejercicio", "Resultado del ejercicio", "Profit (loss) for the year", False),
    ("resultados_acumulados", "Resultados de ejercicios anteriores", "Retained earnings", False),
    ("otro_patrimonio", "Otras partidas del patrimonio", "Other equity", False),
    ("patrimonio", "Total patrimonio", "Total equity", True),
]
CAMPOS_ERI = [
    ("ingresos_operacionales", "Ingresos de actividades ordinarias", "Revenue", True),
    ("costo_ventas", "Costo de ventas", "Cost of sales", False),
    ("utilidad_bruta", "Utilidad bruta", "Gross profit", True),
    ("gastos_administracion", "Gastos de administración", "Administrative expenses", False),
    ("gastos_ventas", "Gastos de ventas", "Selling expenses", False),
    ("utilidad_operacional", "Utilidad operacional", "Operating profit", True),
    ("otros_ingresos", "Otros ingresos", "Other income", False),
    ("ingresos_financieros", "Ingresos financieros", "Finance income", False),
    ("gastos_financieros", "Gastos financieros (intereses)", "Finance costs (interest)", False),
    ("otros_gastos_financieros", "Otros gastos financieros", "Other finance costs", False),
    ("otros_gastos", "Otros gastos", "Other expenses", False),
    ("utilidad_antes_impuestos", "Utilidad antes de impuestos", "Profit before tax", True),
    ("impuesto_renta", "Impuesto de renta", "Income tax expense", False),
    ("utilidad_neta", "Utilidad neta", "Profit for the year", True),
]

# Totales que se escriben como fórmula si todos sus componentes tienen dato.
# Cada componente es (signo, campo).
TOTALES = {
    "activo_corriente": [(1, c) for c in ("efectivo", "inversiones_cp", "deudores_comerciales",
                                          "otras_cuentas_por_cobrar_cp", "activos_por_impuestos_cp",
                                          "inventarios", "otros_activos_cp")],
    "activo_no_corriente": [(1, c) for c in ("ppe", "intangibles", "inversiones_lp", "otros_activos_lp")],
    "activo_total": [(1, "activo_corriente"), (1, "activo_no_corriente")],
    "pasivo_corriente": [(1, c) for c in ("obligaciones_financieras_cp", "proveedores",
                                          "otras_cuentas_por_pagar_cp", "pasivos_por_impuestos_cp",
                                          "obligaciones_laborales", "otros_pasivos_cp")],
    "pasivo_no_corriente": [(1, "obligaciones_financieras_lp"), (1, "otros_pasivos_lp")],
    "pasivo_total": [(1, "pasivo_corriente"), (1, "pasivo_no_corriente")],
    "patrimonio": [(1, c) for c in ("capital", "reservas", "resultado_ejercicio",
                                    "resultados_acumulados", "otro_patrimonio")],
    "utilidad_bruta": [(1, "ingresos_operacionales"), (-1, "costo_ventas")],
    "utilidad_operacional": [(1, "utilidad_bruta"), (-1, "gastos_administracion"), (-1, "gastos_ventas")],
    "utilidad_antes_impuestos": [(1, "utilidad_operacional"), (1, "otros_ingresos"),
                                 (1, "ingresos_financieros"), (-1, "gastos_financieros"),
                                 (-1, "otros_gastos_financieros"), (-1, "otros_gastos")],
    "utilidad_neta": [(1, "utilidad_antes_impuestos"), (-1, "impuesto_renta")],
}

# id: (ES, EN, fórmula ES, fórmula EN)
NOMBRES_IND = {
    "razon_corriente": ("Razón corriente", "Current ratio",
                        "Activo corriente / Pasivo corriente", "Current assets / Current liabilities"),
    "prueba_acida": ("Prueba ácida", "Quick ratio", "(Activo corriente − Inventarios) / Pasivo corriente",
                     "(Current assets − Inventories) / Current liabilities"),
    "capital_trabajo_neto": ("Capital de trabajo neto", "Net working capital",
                             "Activo corriente − Pasivo corriente", "Current assets − Current liabilities"),
    "ktno": ("KTNO", "Net operating working capital (NOWC)",
             "Deudores comerciales + Inventarios − Proveedores",
             "Trade receivables + Inventories − Trade payables"),
    "nivel_endeudamiento": ("Nivel de endeudamiento", "Debt ratio",
                            "Pasivo total / Activo total", "Total liabilities / Total assets"),
    "concentracion_cp": ("Concentración de la deuda a corto plazo", "Short-term debt concentration",
                         "Pasivo corriente / Pasivo total", "Current liabilities / Total liabilities"),
    "apalancamiento_total": ("Apalancamiento total", "Total leverage",
                             "Pasivo total / Patrimonio", "Total liabilities / Total equity"),
    "apalancamiento_financiero": ("Apalancamiento financiero", "Financial leverage",
                                  "Obligaciones financieras / Patrimonio", "Borrowings / Total equity"),
    "cobertura_intereses": ("Cobertura de intereses", "Interest coverage",
                            "Utilidad operacional / Gastos financieros", "Operating profit / Finance costs"),
    "margen_bruto": ("Margen bruto", "Gross margin", "Utilidad bruta / Ingresos", "Gross profit / Revenue"),
    "margen_operacional": ("Margen operacional", "Operating margin",
                           "Utilidad operacional / Ingresos", "Operating profit / Revenue"),
    "margen_neto": ("Margen neto", "Net margin", "Utilidad neta / Ingresos", "Profit for the year / Revenue"),
    "roa": ("ROA", "Return on assets (ROA)", "Utilidad neta / Activo total promedio",
            "Profit for the year / Average total assets"),
    "roe": ("ROE", "Return on equity (ROE)", "Utilidad neta / Patrimonio promedio",
            "Profit for the year / Average total equity"),
    "dias_cartera": ("Rotación de cartera (días)", "Days sales outstanding (DSO)",
                     "Deudores comerciales promedio / Ingresos × días", "Average trade receivables / Revenue × days"),
    "dias_inventario": ("Rotación de inventarios (días)", "Days inventory outstanding (DIO)",
                        "Inventarios promedio / Costo de ventas × días", "Average inventories / Cost of sales × days"),
    "dias_proveedores": ("Rotación de proveedores (días)", "Days payables outstanding (DPO)",
                         "Proveedores promedio / Costo de ventas × días", "Average trade payables / Cost of sales × days"),
    "ciclo_efectivo": ("Ciclo de conversión de efectivo", "Cash conversion cycle (CCC)",
                       "Días cartera + Días inventario − Días proveedores", "DSO + DIO − DPO"),
    "rotacion_activos": ("Rotación de activos", "Asset turnover",
                         "Ingresos / Activo total promedio", "Revenue / Average total assets"),
}


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "Empresa").encode("ascii", "ignore").decode()
    texto = re.sub(r"\b(S\.?A\.?S|S\.?A|LTDA)\.?$", "", texto.strip(), flags=re.I)
    return re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_") or "Empresa"


def ref(hoja: str, celda: str) -> str:
    return f"'{hoja}'!{celda}"


def encabezado(ws, fila: int, valores: list, desde_col: int = 1) -> None:
    for j, v in enumerate(valores):
        c = ws.cell(row=fila, column=desde_col + j, value=v)
        c.font, c.fill = F_ENCABEZADO, RELLENO_ENC
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def anchos(ws, anchos_col: dict[int, float]) -> None:
    for col, ancho in anchos_col.items():
        ws.column_dimensions[get_column_letter(col)].width = ancho


class Libro:
    def __init__(self, datos: dict, resultados: dict, textos: dict, idioma: str):
        self.d, self.r, self.tx, self.l = datos, resultados, textos, idioma
        self.t = T[idioma]
        self.na = self.t["na"]
        self.periodos = datos["periodos"]
        anios = [p["fecha_corte"][:4] for p in self.periodos]
        self.sufijos = anios if len(set(anios)) == len(anios) else [f"p{i + 1}" for i in range(len(anios))]
        self.wb = Workbook()
        self.hojas = {}
        nombres = self.t["hojas"]
        claves = ["resumen", "datos", "vertical", "horizontal", "indicadores", "sector", "graficas", "notas"]
        self.wb.active.title = nombres[0]
        self.hojas["resumen"] = self.wb.active
        for clave, nombre in zip(claves[1:], nombres[1:]):
            self.hojas[clave] = self.wb.create_sheet(nombre)
        self.nombre = dict(zip(claves, nombres))
        self.fila_ind: dict[str, int] = {}
        self.col_periodo_ind: list[int] = []
        self.anio_sector = None

    # ---- nombres definidos -------------------------------------------------
    def n(self, campo: str, i: int) -> str:
        return f"{campo}_{self.sufijos[i]}"

    def prom(self, campo: str, i: int) -> str:
        if i > 0 and self.periodos[i - 1]["esf"].get(campo) is not None:
            return f"(({self.n(campo, i - 1)}+{self.n(campo, i)})/2)"
        return self.n(campo, i)

    # ---- hoja Datos ---------------------------------------------------------
    def hoja_datos(self) -> None:
        ws, t = self.hojas["datos"], self.t
        ws["A1"], ws["A1"].font = t["titulo"], F_TITULO
        ws["A2"], ws["A2"].font = t["nota_datos"], F_NOTA
        fila = 4
        encabezado(ws, fila, [t["campo"], t["concepto"]] + [p["fecha_corte"] for p in self.periodos])
        self.fila_campo: dict[str, int] = {}
        fila += 1
        for seccion, campos in (("esf", CAMPOS_ESF), ("eri", CAMPOS_ERI)):
            c = ws.cell(row=fila, column=2, value=t[seccion])
            c.font, c.fill = F_SUBTITULO, RELLENO_SECCION
            fila += 1
            for campo, es, en, total in campos:
                self.fila_campo[campo] = fila
                ws.cell(row=fila, column=1, value=campo).font = F_NOTA
                ws.cell(row=fila, column=2, value=es if self.l == "es" else en).font = F_TOTAL if total else F_NORMAL
                fila += 1
            fila += 1
        self.fila_campo["dias_periodo"] = fila
        ws.cell(row=fila, column=1, value="dias_periodo").font = F_NOTA
        ws.cell(row=fila, column=2, value=t["dias_periodo"]).font = F_NORMAL

        for i, p in enumerate(self.periodos):
            col = 3 + i
            letra = get_column_letter(col)
            for seccion, campos in (("esf", CAMPOS_ESF), ("eri", CAMPOS_ERI)):
                for campo, _, _, total in campos:
                    f = self.fila_campo[campo]
                    celda = ws.cell(row=f, column=col)
                    comps = TOTALES.get(campo)
                    if comps and all(self._tiene(p, c) for _, c in comps):
                        partes = "".join(("+" if s > 0 else "-") + f"{letra}{self.fila_campo[c]}" for s, c in comps)
                        celda.value = "=" + partes.lstrip("+")
                    else:
                        celda.value = p[seccion].get(campo)
                        celda.fill = RELLENO_ENTRADA
                        celda.protection = Protection(locked=False)
                    celda.number_format = FMT_COP
                    celda.font = F_TOTAL if total else F_NORMAL
                    if total:
                        celda.border = BORDE_TOTAL
                    self._nombrar(self.n(campo, i), ws.title, f"${letra}${f}")
            f = self.fila_campo["dias_periodo"]
            celda = ws.cell(row=f, column=col, value=p.get("dias_periodo") or 360)
            celda.fill = RELLENO_ENTRADA
            celda.protection = Protection(locked=False)
            self._nombrar(self.n("dias_periodo", i), ws.title, f"${letra}${f}")
        ws.freeze_panes = "C5"
        ws.column_dimensions["A"].hidden = True
        anchos(ws, {1: 26, 2: 42, **{3 + i: 16 for i in range(len(self.periodos))}})

    def _tiene(self, periodo: dict, campo: str) -> bool:
        if campo in TOTALES:
            return all(self._tiene(periodo, c) for _, c in TOTALES[campo])
        return periodo["esf"].get(campo, periodo["eri"].get(campo)) is not None

    def _nombrar(self, nombre: str, hoja: str, celda: str) -> None:
        self.wb.defined_names[nombre] = DefinedName(nombre, attr_text=f"'{hoja}'!{celda}")

    # ---- Vertical y Horizontal ---------------------------------------------
    def hoja_vertical(self) -> None:
        ws, t = self.hojas["vertical"], self.t
        ws["A1"], ws["A1"].font = t["pct_activo"], F_TITULO
        encabezado(ws, 3, [t["concepto"]] + [p["fecha_corte"] for p in self.periodos])
        fila = 4
        for seccion, campos, base in (("esf", CAMPOS_ESF, "activo_total"), ("eri", CAMPOS_ERI, "ingresos_operacionales")):
            c = ws.cell(row=fila, column=1, value=t[seccion])
            c.font, c.fill = F_SUBTITULO, RELLENO_SECCION
            fila += 1
            for campo, es, en, total in campos:
                ws.cell(row=fila, column=1, value=es if self.l == "es" else en).font = F_TOTAL if total else F_NORMAL
                for i in range(len(self.periodos)):
                    c = ws.cell(row=fila, column=2 + i,
                                value=f'=IFERROR({self.n(campo, i)}/{self.n(base, i)},"{self.na}")')
                    c.number_format, c.font = FMT_PCT, F_TOTAL if total else F_NORMAL
                fila += 1
            fila += 1
        ws.freeze_panes = "B4"
        anchos(ws, {1: 42, **{2 + i: 14 for i in range(len(self.periodos))}})

    def hoja_horizontal(self) -> None:
        ws, t = self.hojas["horizontal"], self.t
        ws["A1"], ws["A1"].font = t["var_abs"] + " / " + t["var_rel"], F_TITULO
        pares = list(range(1, len(self.periodos)))
        cab = [t["concepto"]]
        for i in pares:
            rango = f"{self.periodos[i - 1]['fecha_corte'][:4]}→{self.periodos[i]['fecha_corte'][:4]}"
            cab += [f"{t['var_abs']} {rango}", f"{t['var_rel']} {rango}"]
        encabezado(ws, 3, cab)
        fila = 4
        if not pares:
            ws.cell(row=fila, column=1, value=self.na).font = F_NOTA
        for seccion, campos in (("esf", CAMPOS_ESF), ("eri", CAMPOS_ERI)):
            if not pares:
                break
            c = ws.cell(row=fila, column=1, value=t[seccion])
            c.font, c.fill = F_SUBTITULO, RELLENO_SECCION
            fila += 1
            for campo, es, en, total in campos:
                ws.cell(row=fila, column=1, value=es if self.l == "es" else en).font = F_TOTAL if total else F_NORMAL
                for k, i in enumerate(pares):
                    a, b = self.n(campo, i - 1), self.n(campo, i)
                    c1 = ws.cell(row=fila, column=2 + 2 * k, value=f'=IFERROR({b}-{a},"{self.na}")')
                    c2 = ws.cell(row=fila, column=3 + 2 * k, value=f'=IFERROR(IF({a}>0,({b}-{a})/{a},"{self.na}"),"{self.na}")')
                    c1.number_format, c2.number_format = FMT_COP, FMT_PCT
                    c1.font = c2.font = F_TOTAL if total else F_NORMAL
                fila += 1
            fila += 1
        ws.freeze_panes = "B4"
        anchos(ws, {1: 42, **{2 + j: 18 for j in range(2 * len(pares))}})

    # ---- Sector ----------------------------------------------------------------
    def hoja_sector(self) -> None:
        ws, t = self.hojas["sector"], self.t
        ws["A1"], ws["A1"].font = t["col_sector"][0] + " / " + t["ciiu"], F_TITULO
        encabezado(ws, 3, t["col_sector"])
        self.fila_sector: dict[str, int] = {}
        fila = 4
        for id_, info in self.r["indicadores"].items():
            if info["direccion"] == "ninguna":
                continue
            self.fila_sector[id_] = fila
            ws.cell(row=fila, column=1, value=NOMBRES_IND[id_][0 if self.l == "es" else 1]).font = F_NORMAL
            s = info.get("sector")
            if s:
                self.anio_sector = s["anio"]
                valores = [t["niveles"].get(s["nivel"], s["nivel"]), s["codigo"], s["anio"], s["n_empresas"],
                           s["p25"], s["p50"], s["p75"]]
                for j, v in enumerate(valores):
                    c = ws.cell(row=fila, column=2 + j, value=v)
                    c.font = F_NORMAL
                    if j >= 4:
                        c.number_format = FORMATOS.get(info["unidad"], FMT_VECES)
            fila += 1
        ws.freeze_panes = "B4"
        anchos(ws, {1: 40, 2: 14, 3: 10, 4: 8, 5: 14, 6: 12, 7: 12, 8: 12})

    # ---- Indicadores ---------------------------------------------------------
    def formula(self, id_: str, i: int, fila: int, col: int) -> str:
        n, na, p = self.n, f'"{self.na}"', self.prom
        dias = n("dias_periodo", i)
        f = {
            "razon_corriente": f"IF({n('pasivo_corriente', i)}=0,{na},{n('activo_corriente', i)}/{n('pasivo_corriente', i)})",
            "prueba_acida": f"IF({n('pasivo_corriente', i)}=0,{na},({n('activo_corriente', i)}-{n('inventarios', i)})/{n('pasivo_corriente', i)})",
            "capital_trabajo_neto": f"{n('activo_corriente', i)}-{n('pasivo_corriente', i)}",
            "ktno": f"{n('deudores_comerciales', i)}+{n('inventarios', i)}-{n('proveedores', i)}",
            "nivel_endeudamiento": f"IF({n('activo_total', i)}=0,{na},{n('pasivo_total', i)}/{n('activo_total', i)})",
            "concentracion_cp": f"IF({n('pasivo_total', i)}=0,{na},{n('pasivo_corriente', i)}/{n('pasivo_total', i)})",
            "apalancamiento_total": f"IF({n('patrimonio', i)}<=0,{na},{n('pasivo_total', i)}/{n('patrimonio', i)})",
            "apalancamiento_financiero": f"IF({n('patrimonio', i)}<=0,{na},({n('obligaciones_financieras_cp', i)}+{n('obligaciones_financieras_lp', i)})/{n('patrimonio', i)})",
            "cobertura_intereses": f"IF({n('gastos_financieros', i)}=0,{na},{n('utilidad_operacional', i)}/{n('gastos_financieros', i)})",
            "margen_bruto": f"IF(OR({n('costo_ventas', i)}=0,{n('ingresos_operacionales', i)}=0),{na},{n('utilidad_bruta', i)}/{n('ingresos_operacionales', i)})",
            "margen_operacional": f"IF({n('ingresos_operacionales', i)}=0,{na},{n('utilidad_operacional', i)}/{n('ingresos_operacionales', i)})",
            "margen_neto": f"IF({n('ingresos_operacionales', i)}=0,{na},{n('utilidad_neta', i)}/{n('ingresos_operacionales', i)})",
            "roa": f"IF({p('activo_total', i)}=0,{na},{n('utilidad_neta', i)}/{p('activo_total', i)})",
            "roe": f"IF(OR({n('patrimonio', i)}<=0,{p('patrimonio', i)}<=0),{na},{n('utilidad_neta', i)}/{p('patrimonio', i)})",
            "dias_cartera": f"IF({n('ingresos_operacionales', i)}=0,{na},{p('deudores_comerciales', i)}/{n('ingresos_operacionales', i)}*{dias})",
            "dias_inventario": f"IF(OR({p('inventarios', i)}=0,{n('costo_ventas', i)}=0),{na},{p('inventarios', i)}/{n('costo_ventas', i)}*{dias})",
            "dias_proveedores": f"IF({n('costo_ventas', i)}=0,{na},{p('proveedores', i)}/{n('costo_ventas', i)}*{dias})",
            "rotacion_activos": f"IF({p('activo_total', i)}=0,{na},{n('ingresos_operacionales', i)}/{p('activo_total', i)})",
        }
        if id_ == "ciclo_efectivo":
            letra = get_column_letter(col)
            dc, di, dp = (f"{letra}{self.fila_ind[k]}" for k in ("dias_cartera", "dias_inventario", "dias_proveedores"))
            return (f"=IF(ISNUMBER({dc}),{dc}+IF(ISNUMBER({di}),{di},0)-IF(ISNUMBER({dp}),{dp},0),{na})")
        return f"=IFERROR({f[id_]},{na})"

    def hoja_indicadores(self) -> None:
        ws, t = self.hojas["indicadores"], self.t
        ws["A1"], ws["A1"].font = t["titulo"], F_TITULO
        ws["A2"] = f"{self.d.get('empresa', '')} · {t['unidades']}: {self._unidades()}"
        ws["A2"].font = F_NOTA
        n_p = len(self.periodos)
        cab = t["col_ind"] + [p["fecha_corte"][:4] for p in self.periodos] + \
            [t["variacion"], t["p25"], t["p50"], t["p75"], t["direccion"], t["semaforo"], t["interpretacion"]]
        encabezado(ws, 4, cab)
        col_var = 4 + n_p
        col_p25, col_p50, col_p75 = col_var + 1, col_var + 2, col_var + 3
        col_dir, col_sem, col_int = col_var + 4, col_var + 5, col_var + 6
        self.col_periodo_ind = [4 + i for i in range(n_p)]
        self.col_sem = col_sem

        ids = list(self.r["indicadores"].keys())
        fila = 5
        grupo_actual = None
        for id_ in ids:
            grupo = self.r["indicadores"][id_]["grupo"]
            if grupo != grupo_actual:
                c = ws.cell(row=fila, column=1, value=t["grupos"][grupo])
                c.font, c.fill = F_SUBTITULO, RELLENO_SECCION
                grupo_actual = grupo
                fila += 1
            self.fila_ind[id_] = fila
            fila += 1

        sector = self.nombre["sector"]
        interpretaciones = self.tx.get("interpretaciones", {})
        for id_ in ids:
            info, f = self.r["indicadores"][id_], self.fila_ind[id_]
            es, en, f_es, f_en = NOMBRES_IND[id_]
            fmt = FORMATOS[info["unidad"]]
            ws.cell(row=f, column=1, value=t["grupos"][info["grupo"]]).font = F_NOTA
            ws.cell(row=f, column=2, value=es if self.l == "es" else en).font = F_TOTAL
            ws.cell(row=f, column=3, value=f_es if self.l == "es" else f_en).font = F_NOTA
            for i, col in enumerate(self.col_periodo_ind):
                c = ws.cell(row=f, column=col, value=self.formula(id_, i, f, col))
                c.number_format, c.font = fmt, F_NORMAL
            if n_p > 1:
                a, b = (f"{get_column_letter(self.col_periodo_ind[k])}{f}" for k in (-2, -1))
                c = ws.cell(row=f, column=col_var, value=f'=IF(AND(ISNUMBER({a}),ISNUMBER({b})),{b}-{a},"{self.na}")')
                c.number_format = fmt
            ws.cell(row=f, column=col_dir, value=t["dir"][info["direccion"]]).font = F_NOTA
            if info["direccion"] != "ninguna" and id_ in self.fila_sector:
                fs = self.fila_sector[id_]
                for col, letra_sector in ((col_p25, "F"), (col_p50, "G"), (col_p75, "H")):
                    c = ws.cell(row=f, column=col, value=f'=IF(ISNUMBER({ref(sector, letra_sector + str(fs))}),'
                                                         f'{ref(sector, letra_sector + str(fs))},"")')
                    c.number_format = fmt
                v = f"{get_column_letter(self.col_periodo_ind[-1])}{f}"
                p25, p50, p75 = (f"{get_column_letter(c)}{f}" for c in (col_p25, col_p50, col_p75))
                s = t["sem"]
                if info["direccion"] == "mas":
                    regla = f'IF({v}>={p50},"{s["verde"]}",IF({v}>={p25},"{s["amarillo"]}","{s["rojo"]}"))'
                else:
                    regla = f'IF({v}<={p50},"{s["verde"]}",IF({v}<={p75},"{s["amarillo"]}","{s["rojo"]}"))'
                ws.cell(row=f, column=col_sem, value=f'=IF(AND(ISNUMBER({v}),ISNUMBER({p50})),{regla},"")')
            c = ws.cell(row=f, column=col_int, value=interpretaciones.get(id_, ""))
            c.font, c.alignment = F_NORMAL, AJUSTE

        rango = f"{get_column_letter(col_sem)}5:{get_column_letter(col_sem)}{fila}"
        self._formato_semaforo(ws, rango)
        ws.freeze_panes = "D5"
        anchos(ws, {1: 14, 2: 34, 3: 40, **{c: 13 for c in self.col_periodo_ind},
                    col_var: 12, col_p25: 12, col_p50: 12, col_p75: 12, col_dir: 16, col_sem: 16, col_int: 60})

    def _formato_semaforo(self, ws, rango: str) -> None:
        primera = rango.split(":")[0]
        for clave, color in (("verde", VERDE), ("amarillo", AMBAR), ("rojo", ROJO)):
            palabra = self.t["sem"][clave].split(" ", 1)[1]
            ws.conditional_formatting.add(rango, FormulaRule(
                formula=[f'ISNUMBER(SEARCH("{palabra}",{primera}))'],
                font=Font(name="Arial", size=10, bold=True, color=color)))

    # ---- Resumen ---------------------------------------------------------------
    def _unidades(self) -> str:
        u = self.d.get("unidades", "pesos")
        return self.t["unidades_txt"].get(u, u)

    def hoja_resumen(self) -> None:
        ws, t, d = self.hojas["resumen"], self.t, self.d
        ws["A1"], ws["A1"].font = t["titulo"], F_TITULO
        info = [
            (t["empresa"], d.get("empresa")), (t["nit"], d.get("nit")),
            (t["ciiu"], d.get("ciiu")), (t["corte"], self.periodos[-1]["fecha_corte"]),
            (t["unidades"], self._unidades()), (t["marco"], d.get("marco")),
            (t["preparado"], self.tx.get("preparado_por", "")), (t["fecha_elab"], date.today().isoformat()),
        ]
        fila = 3
        for etiqueta, valor in info:
            ws.cell(row=fila, column=1, value=etiqueta).font = F_TOTAL
            ws.cell(row=fila, column=2, value=valor).font = F_NORMAL
            fila += 1

        fila += 1
        ws.cell(row=fila, column=1, value=t["conclusion"]).font = F_SUBTITULO
        fila += 1
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
        c = ws.cell(row=fila, column=1, value=self.tx.get("conclusion", ""))
        c.font, c.alignment = F_NORMAL, AJUSTE
        ws.row_dimensions[fila].height = max(30, 15 * (1 + len(self.tx.get("conclusion", "")) // 110))
        fila += 2

        hallazgos = self.tx.get("hallazgos", [])
        if hallazgos:
            ws.cell(row=fila, column=1, value=t["hallazgos"]).font = F_SUBTITULO
            fila += 1
            inicio = fila
            for h in hallazgos[:5]:
                c = ws.cell(row=fila, column=1, value=t["sem"].get(h.get("semaforo"), ""))
                c.font, c.alignment = F_TOTAL, AJUSTE
                c = ws.cell(row=fila, column=2, value=h.get("titulo", ""))
                c.font, c.alignment = F_TOTAL, AJUSTE
                ws.merge_cells(start_row=fila, start_column=3, end_row=fila, end_column=6)
                c = ws.cell(row=fila, column=3, value=h.get("detalle", ""))
                c.font = F_NORMAL
                c.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
                ws.row_dimensions[fila].height = max(30, 15 * (1 + len(h.get("detalle", "")) // 70))
                fila += 1
            self._formato_semaforo(ws, f"A{inicio}:A{fila - 1}")
            fila += 1

        ws.cell(row=fila, column=1, value=t["tabla_semaforo"]).font = F_SUBTITULO
        fila += 1
        ind = self.nombre["indicadores"]
        cols = [get_column_letter(c) for c in self.col_periodo_ind[-2:]]
        cab = [t["col_ind"][1]] + [self.periodos[-len(cols) + k]["fecha_corte"][:4] for k in range(len(cols))] + \
            [t["p50"], t["semaforo"]]
        encabezado(ws, fila, cab)
        fila += 1
        inicio = fila
        col_p50 = get_column_letter(self.col_sem - 3)
        col_sem = get_column_letter(self.col_sem)
        for id_, info_i in self.r["indicadores"].items():
            if info_i["direccion"] == "ninguna":
                continue
            fi = self.fila_ind[id_]
            ws.cell(row=fila, column=1, value=NOMBRES_IND[id_][0 if self.l == "es" else 1]).font = F_NORMAL
            for k, letra in enumerate(cols):
                c = ws.cell(row=fila, column=2 + k, value=f"={ref(ind, letra + str(fi))}")
                c.number_format = FORMATOS[info_i["unidad"]]
            c = ws.cell(row=fila, column=2 + len(cols), value=f"={ref(ind, col_p50 + str(fi))}")
            c.number_format = FORMATOS[info_i["unidad"]]
            ws.cell(row=fila, column=3 + len(cols), value=f"={ref(ind, col_sem + str(fi))}")
            fila += 1
        letra_sem = get_column_letter(3 + len(cols))
        self._formato_semaforo(ws, f"{letra_sem}{inicio}:{letra_sem}{fila - 1}")

        recomendaciones = self.tx.get("recomendaciones", [])
        if recomendaciones:
            fila += 1
            ws.cell(row=fila, column=1, value=t["recomendaciones"]).font = F_SUBTITULO
            fila += 1
            for k, rec in enumerate(recomendaciones, 1):
                ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=6)
                c = ws.cell(row=fila, column=1, value=f"{k}. {rec}")
                c.font, c.alignment = F_NORMAL, AJUSTE
                ws.row_dimensions[fila].height = 30
                fila += 1
        anchos(ws, {1: 36, 2: 24, 3: 12, 4: 12, 5: 16, 6: 16})

    # ---- Gráficas -------------------------------------------------------------
    def hoja_graficas(self) -> None:
        ws, t = self.hojas["graficas"], self.t
        ind = self.nombre["indicadores"]
        ws["A1"], ws["A1"].font = t["titulo"], F_TITULO
        ultima = get_column_letter(self.col_periodo_ind[-1])
        col_p50 = get_column_letter(self.col_sem - 3)
        titulos = {**t["graf"], **self.tx.get("titulos_graficas", {})}
        fila = 3
        fila_grafica = 3

        def tabla(ids: list[str]) -> tuple[int, int]:
            nonlocal fila
            encabezado(ws, fila, ["", t["empresa_serie"], t["sector_serie"]])
            inicio = fila
            for id_ in ids:
                fila += 1
                fi = self.fila_ind[id_]
                ws.cell(row=fila, column=1, value=NOMBRES_IND[id_][0 if self.l == "es" else 1])
                tiene_sector = bool(self.r["indicadores"][id_].get("sector"))
                for col, letra in ((2, ultima), (3, col_p50)):
                    if col == 3 and not tiene_sector:
                        continue  # celda vacía: Excel no dibuja la barra ni muestra "#N/A"
                    r = ref(ind, f"{letra}{fi}")
                    c = ws.cell(row=fila, column=col, value=f"=IF(ISNUMBER({r}),{r},NA())")
                    c.number_format = FORMATOS[self.r["indicadores"][id_]["unidad"]]
            fila += 2
            return inicio, fila - 2

        def barras(clave: str, inicio: int, fin: int, fmt: str, horizontal: bool = False) -> None:
            nonlocal fila_grafica
            ch = BarChart()
            ch.type = "bar" if horizontal else "col"
            if horizontal:
                ch.x_axis.scaling.orientation = "maxMin"  # mismo orden de arriba a abajo que la tabla
            ch.title = titulos[clave]
            ch.add_data(Reference(ws, min_col=2, max_col=3, min_row=inicio, max_row=fin), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=inicio + 1, max_row=fin))
            self._estilo_grafica(ch, fmt)
            ws.add_chart(ch, f"F{fila_grafica}")
            fila_grafica += 18

        a, b = tabla(["razon_corriente", "prueba_acida"])
        barras("liquidez", a, b, "0.00")
        a, b = tabla(["nivel_endeudamiento", "concentracion_cp"])
        barras("endeudamiento", a, b, "0%")

        if len(self.periodos) > 1:
            encabezado(ws, fila, [""] + [NOMBRES_IND[k][0 if self.l == "es" else 1]
                                         for k in ("margen_bruto", "margen_operacional", "margen_neto")])
            inicio = fila
            for i, col in enumerate(self.col_periodo_ind):
                fila += 1
                ws.cell(row=fila, column=1, value=self.periodos[i]["fecha_corte"][:4])
                for j, k in enumerate(("margen_bruto", "margen_operacional", "margen_neto")):
                    r = ref(ind, f"{get_column_letter(col)}{self.fila_ind[k]}")
                    c = ws.cell(row=fila, column=2 + j, value=f"=IF(ISNUMBER({r}),{r},NA())")
                    c.number_format = FMT_PCT
            fin = fila
            fila += 2
            ch = LineChart()
            ch.title = titulos["rentabilidad"]
            ch.add_data(Reference(ws, min_col=2, max_col=4, min_row=inicio, max_row=fin), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=inicio + 1, max_row=fin))
            colores = [AZUL, "4A7AB0", GRIS_SECTOR]
            for serie, color in zip(ch.series, colores):
                serie.graphicalProperties.line.solidFill = color
                serie.graphicalProperties.line.width = 28000
                serie.smooth = False
            self._estilo_grafica(ch, "0%", series_color=False)
            for serie in ch.series:
                serie.dLbls.position = "t"
            ws.add_chart(ch, f"F{fila_grafica}")
            fila_grafica += 18
        else:
            a, b = tabla(["margen_bruto", "margen_operacional", "margen_neto"])
            barras("rentabilidad", a, b, "0%")

        a, b = tabla(["dias_cartera", "dias_inventario", "dias_proveedores", "ciclo_efectivo"])
        barras("actividad", a, b, "0", horizontal=True)

        for clave, partes in (("activo", ["activo_corriente", "activo_no_corriente"]),
                              ("financiacion", ["pasivo_corriente", "pasivo_no_corriente", "patrimonio"])):
            nombres = {c: (es if self.l == "es" else en) for c, es, en, _ in CAMPOS_ESF}
            encabezado(ws, fila, [""] + [nombres[c] for c in partes])
            inicio = fila
            for i in range(len(self.periodos)):
                fila += 1
                ws.cell(row=fila, column=1, value=self.periodos[i]["fecha_corte"][:4])
                # Participación de cada parte en el total (las partes negativas cuentan como 0).
                total = "+".join(f"MAX({self.n(c, i)},0)" for c in partes)
                for j, campo in enumerate(partes):
                    c = ws.cell(row=fila, column=2 + j,
                                value=f"=IFERROR(MAX({self.n(campo, i)},0)/({total}),NA())")
                    c.number_format = FMT_PCT
            fin = fila
            fila += 2
            ch = BarChart()
            ch.type, ch.grouping, ch.overlap = "col", "stacked", 100
            ch.y_axis.scaling.max = 1
            ch.title = titulos[clave]
            ch.add_data(Reference(ws, min_col=2, max_col=1 + len(partes), min_row=inicio, max_row=fin),
                        titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=1, min_row=inicio + 1, max_row=fin))
            for serie, color in zip(ch.series, [AZUL, "4A7AB0", GRIS_SECTOR]):
                serie.graphicalProperties.solidFill = color
                serie.graphicalProperties.line.solidFill = color
            self._estilo_grafica(ch, "0%", series_color=False)
            ws.add_chart(ch, f"F{fila_grafica}")
            fila_grafica += 18

        nota = t["fuente_graf"].format(anio=self.anio_sector or "n.d.")
        ws.cell(row=fila, column=1, value=nota).font = F_NOTA
        anchos(ws, {1: 36, 2: 18, 3: 18, 4: 18})

    def _estilo_grafica(self, ch, fmt: str, series_color: bool = True) -> None:
        ch.height, ch.width = 8.5, 16
        ch.legend.position = "b"
        ch.legend.overlay = False
        if ch.title is not None:
            ch.title.overlay = False
        ch.y_axis.majorGridlines = None
        ch.y_axis.number_format = fmt
        ch.y_axis.delete = False
        ch.x_axis.delete = False
        if series_color:
            for serie, color in zip(ch.series, [AZUL, GRIS_SECTOR]):
                serie.graphicalProperties.solidFill = color
                serie.graphicalProperties.line.solidFill = color
        for serie in ch.series:
            serie.dLbls = DataLabelList()
            serie.dLbls.showVal = True
            serie.dLbls.numFmt = fmt
            for attr in ("showSerName", "showCatName", "showLegendKey", "showPercent"):
                setattr(serie.dLbls, attr, False)

    # ---- Notas -----------------------------------------------------------------
    def hoja_notas(self) -> None:
        ws, t = self.hojas["notas"], self.t
        ws["A1"], ws["A1"].font = t["notas"], F_TITULO
        fila = 3
        bloques = [
            (t["advertencias"], self.r.get("advertencias", [])),
            (t["metodologia"], [m.format(dias=self.periodos[-1].get("dias_periodo") or 360) for m in t["met"]]),
        ]
        for titulo, lineas in bloques:
            ws.cell(row=fila, column=1, value=titulo).font = F_SUBTITULO
            fila += 1
            for linea in lineas:
                c = ws.cell(row=fila, column=1, value=f"• {linea}")
                c.font, c.alignment = F_NORMAL, AJUSTE
                fila += 1
            fila += 1
        for linea in (t["cifras_por"], t["aclaracion"]):
            c = ws.cell(row=fila, column=1, value=linea)
            c.font, c.alignment = Font(name="Arial", size=10, italic=True), AJUSTE
            fila += 1
        anchos(ws, {1: 120})

    # ---- Ensamblaje --------------------------------------------------------------
    def construir(self) -> Workbook:
        self.hoja_datos()
        self.hoja_vertical()
        self.hoja_horizontal()
        self.hoja_sector()
        self.hoja_indicadores()
        self.hoja_resumen()
        self.hoja_graficas()
        self.hoja_notas()
        for clave, ws in self.hojas.items():
            ws.sheet_view.showGridLines = False
            ws.protection.sheet = True
            ws.protection.formatColumns = False
            ws.protection.formatRows = False
            ws.sheet_properties.tabColor = "F9A825" if clave == "datos" else AZUL
            # Impresión: tamaño carta, todo el ancho en una página.
            ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
            ws.page_setup.orientation = "landscape" if clave in ("indicadores", "graficas") else "portrait"
            ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
        self.wb.calculation.fullCalcOnLoad = True
        return self.wb


def nombre_archivo(datos: dict, idioma: str) -> str:
    anio = datos["periodos"][-1]["fecha_corte"][:4]
    return T[idioma]["archivo"].format(empresa=slug(datos.get("empresa", "")), anio=anio)


def generar(datos: dict, resultados: dict, idioma: str, textos: dict | None = None,
            salida: Path | None = None, carpeta: Path | None = None) -> Path:
    datos = {**datos, "periodos": sorted(datos["periodos"], key=lambda p: p["fecha_corte"])}
    wb = Libro(datos, resultados, textos or {}, idioma).construir()
    destino = salida or (carpeta or Path.cwd()) / nombre_archivo(datos, idioma)
    wb.save(destino)
    return destino


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Genera el libro de Excel del análisis financiero.")
    parser.add_argument("datos", type=Path, help="datos_homologados.json")
    parser.add_argument("resultados", type=Path, help="resultados_indicadores.json")
    parser.add_argument("--idioma", choices=["es", "en"], required=True)
    parser.add_argument("--textos", type=Path, help="JSON con conclusión, hallazgos e interpretaciones")
    parser.add_argument("--salida", type=Path, help="Ruta del archivo .xlsx")
    args = parser.parse_args(argv)
    try:
        datos = json.loads(args.datos.read_text(encoding="utf-8-sig"))
        resultados = json.loads(args.resultados.read_text(encoding="utf-8-sig"))
        textos = json.loads(args.textos.read_text(encoding="utf-8-sig")) if args.textos else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error leyendo las entradas: {exc}", file=sys.stderr)
        return 1
    destino = generar(datos, resultados, args.idioma, textos, args.salida, args.datos.parent)
    print(f"Excel generado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
