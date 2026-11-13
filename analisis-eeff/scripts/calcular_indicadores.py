#!/usr/bin/env python3
"""Calcula indicadores financieros y los compara con el sector.

Lee `datos_homologados.json` (formato definido en
`referencias/homologacion-puc.md`), valida los cuadres, calcula el análisis
vertical y horizontal, los 19 indicadores de `referencias/indicadores.md` y,
si hay rangos sectoriales, asigna el semáforo.

Uso:
    python calcular_indicadores.py datos_homologados.json
    python calcular_indicadores.py datos.json --salida resultados.json
    python calcular_indicadores.py datos.json --rangos otra_ruta.csv
    python calcular_indicadores.py datos.json --forzar

Códigos de salida:
    0  cálculo completo
    1  error en el archivo de entrada
    2  la ecuación contable no cuadra (usa --forzar para calcular de todas formas)

Convenciones de la salida:
    - Los indicadores en "%" se guardan como fracción (0.125 = 12,5%).
    - Los valores no calculables tienen "valor": null y "estado": "n.a.".
    - Solo usa la biblioteca estándar de Python.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

DIAS_BASE = 360
TOLERANCIA = 0.005
MIN_EMPRESAS_DIVISION = 30
RUTA_RANGOS = Path(__file__).resolve().parent.parent / "datos" / "rangos_sectoriales.csv"

# id: (grupo, unidad, dirección). El orden es el de presentación.
INDICADORES: dict[str, tuple[str, str, str]] = {
    "razon_corriente": ("liquidez", "veces", "mas"),
    "prueba_acida": ("liquidez", "veces", "mas"),
    "capital_trabajo_neto": ("liquidez", "COP", "ninguna"),
    "ktno": ("liquidez", "COP", "ninguna"),
    "nivel_endeudamiento": ("endeudamiento", "%", "menos"),
    "concentracion_cp": ("endeudamiento", "%", "menos"),
    "apalancamiento_total": ("endeudamiento", "veces", "menos"),
    "apalancamiento_financiero": ("endeudamiento", "veces", "menos"),
    "cobertura_intereses": ("endeudamiento", "veces", "mas"),
    "margen_bruto": ("rentabilidad", "%", "mas"),
    "margen_operacional": ("rentabilidad", "%", "mas"),
    "margen_neto": ("rentabilidad", "%", "mas"),
    "roa": ("rentabilidad", "%", "mas"),
    "roe": ("rentabilidad", "%", "mas"),
    "dias_cartera": ("actividad", "dias", "menos"),
    "dias_inventario": ("actividad", "dias", "menos"),
    "dias_proveedores": ("actividad", "dias", "ninguna"),
    "ciclo_efectivo": ("actividad", "dias", "menos"),
    "rotacion_activos": ("actividad", "veces", "mas"),
}

# Secciones CIIU Rev. 4 A.C. por rango de divisiones (2 dígitos).
SECCIONES_CIIU = [
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39),
    ("F", 41, 43), ("G", 45, 47), ("H", 49, 53), ("I", 55, 56), ("J", 58, 63),
    ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82), ("O", 84, 84),
    ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98),
    ("U", 99, 99),
]


class ErrorEntrada(Exception):
    """El archivo de entrada no tiene el formato esperado."""


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def ok(valor: float, base_saldo_final: bool = False) -> dict:
    return {"valor": round(valor, 6), "estado": "ok", "base_saldo_final": base_saldo_final}


def na(motivo: str, tipo: str = "sin_dato") -> dict:
    """tipo: 'sin_dato' (falta información) o 'no_aplica' (la empresa no tiene la partida)."""
    return {"valor": None, "estado": "n.a.", "tipo": tipo, "motivo": motivo}


def dato(periodo: dict, seccion: str, campo: str) -> float | None:
    valor = periodo.get(seccion, {}).get(campo)
    if valor is None:
        return None
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        raise ErrorEntrada(f"{seccion}.{campo} debe ser numérico o null, no {valor!r}")
    return float(valor)


def promedio(periodos: list[dict], i: int, seccion: str, campo: str) -> tuple[float | None, bool]:
    """Saldo promedio (anterior + actual) / 2. Devuelve (valor, se_uso_saldo_final)."""
    actual = dato(periodos[i], seccion, campo)
    if actual is None:
        return None, False
    if i > 0:
        anterior = dato(periodos[i - 1], seccion, campo)
        if anterior is not None:
            return (anterior + actual) / 2, False
    return actual, True


def seccion_ciiu(ciiu: str | None) -> str | None:
    if not ciiu or len(ciiu) < 2 or not ciiu[:2].isdigit():
        return None
    division = int(ciiu[:2])
    for letra, desde, hasta in SECCIONES_CIIU:
        if desde <= division <= hasta:
            return letra
    return None


# --------------------------------------------------------------------------
# Validaciones (cuadres de homologacion-puc.md, sección 1)
# --------------------------------------------------------------------------

def _regla(nombre: str, esperado: float, calculado: float, base: float, critica: bool = False) -> dict:
    diferencia = calculado - esperado
    referencia = max(abs(base), 1.0)
    return {
        "regla": nombre,
        "esperado": round(esperado, 2),
        "calculado": round(calculado, 2),
        "diferencia": round(diferencia, 2),
        "diferencia_relativa": round(abs(diferencia) / referencia, 6),
        "ok": abs(diferencia) / referencia <= TOLERANCIA,
        "critica": critica,
    }


def validar(periodo: dict) -> list[dict]:
    e = lambda c: dato(periodo, "esf", c)  # noqa: E731
    r = lambda c: dato(periodo, "eri", c)  # noqa: E731
    o = lambda s, c: dato(periodo, s, c) or 0.0  # noqa: E731  campos opcionales
    reglas = []
    at = e("activo_total")

    if None not in (at, e("activo_corriente"), e("activo_no_corriente")):
        reglas.append(_regla("activo_total = activo_corriente + activo_no_corriente",
                             at, e("activo_corriente") + e("activo_no_corriente"), at))
    if None not in (e("pasivo_total"), e("pasivo_corriente"), e("pasivo_no_corriente")):
        reglas.append(_regla("pasivo_total = pasivo_corriente + pasivo_no_corriente",
                             e("pasivo_total"), e("pasivo_corriente") + e("pasivo_no_corriente"), at or 0))
    if None not in (at, e("pasivo_total"), e("patrimonio")):
        reglas.append(_regla("activo_total = pasivo_total + patrimonio",
                             at, e("pasivo_total") + e("patrimonio"), at, critica=True))
    if None not in (r("utilidad_bruta"), r("ingresos_operacionales")):
        reglas.append(_regla("utilidad_bruta = ingresos_operacionales - costo_ventas",
                             r("utilidad_bruta"), r("ingresos_operacionales") - o("eri", "costo_ventas"),
                             r("ingresos_operacionales")))
    if None not in (r("utilidad_operacional"), r("utilidad_bruta")):
        reglas.append(_regla("utilidad_operacional = utilidad_bruta - gastos_administracion - gastos_ventas",
                             r("utilidad_operacional"),
                             r("utilidad_bruta") - o("eri", "gastos_administracion") - o("eri", "gastos_ventas"),
                             r("ingresos_operacionales") or 0))
    if None not in (r("utilidad_antes_impuestos"), r("utilidad_operacional")):
        calculada = (r("utilidad_operacional") + o("eri", "otros_ingresos") + o("eri", "ingresos_financieros")
                     - o("eri", "gastos_financieros") - o("eri", "otros_gastos_financieros")
                     - o("eri", "otros_gastos"))
        reglas.append(_regla("utilidad_antes_impuestos = utilidad_operacional + otros ingresos - otros gastos",
                             r("utilidad_antes_impuestos"), calculada, r("ingresos_operacionales") or 0))
    if None not in (r("utilidad_neta"), r("utilidad_antes_impuestos")):
        reglas.append(_regla("utilidad_neta = utilidad_antes_impuestos - impuesto_renta",
                             r("utilidad_neta"), r("utilidad_antes_impuestos") - o("eri", "impuesto_renta"),
                             r("ingresos_operacionales") or 0))
    if None not in (r("utilidad_neta"), e("resultado_ejercicio")):
        reglas.append(_regla("utilidad_neta (ERI) = resultado_ejercicio (ESF)",
                             e("resultado_ejercicio"), r("utilidad_neta"), at or 0))
    return reglas


# --------------------------------------------------------------------------
# Análisis vertical y horizontal
# --------------------------------------------------------------------------

def vertical(periodo: dict) -> dict:
    at = dato(periodo, "esf", "activo_total")
    ing = dato(periodo, "eri", "ingresos_operacionales")
    salida = {"esf": {}, "eri": {}}
    for seccion, base in (("esf", at), ("eri", ing)):
        for campo, valor in periodo.get(seccion, {}).items():
            if valor is None or not base:
                salida[seccion][campo] = None
            else:
                salida[seccion][campo] = round(valor / base, 6)
    return salida


def horizontal(anterior: dict, actual: dict) -> dict:
    salida = {"desde": anterior["fecha_corte"], "hasta": actual["fecha_corte"], "esf": {}, "eri": {}}
    for seccion in ("esf", "eri"):
        for campo in actual.get(seccion, {}):
            a, b = dato(anterior, seccion, campo), dato(actual, seccion, campo)
            if a is None or b is None:
                salida[seccion][campo] = {"absoluta": None, "relativa": None}
                continue
            relativa = round((b - a) / a, 6) if a > 0 else None
            salida[seccion][campo] = {"absoluta": round(b - a, 2), "relativa": relativa}
    return salida


# --------------------------------------------------------------------------
# Indicadores (fórmulas de indicadores.md)
# --------------------------------------------------------------------------

def _cociente(numerador: float | None, denominador: float | None, motivo_cero: str,
              base_saldo_final: bool = False, factor: float = 1.0) -> dict:
    if numerador is None or denominador is None:
        return na("Falta un dato para el cálculo")
    if denominador == 0:
        return na(motivo_cero)
    return ok(numerador / denominador * factor, base_saldo_final)


def calcular_periodo(periodos: list[dict], i: int) -> dict[str, dict]:
    p = periodos[i]
    e = lambda c: dato(p, "esf", c)  # noqa: E731
    r = lambda c: dato(p, "eri", c)  # noqa: E731
    dias = float(p.get("dias_periodo") or DIAS_BASE)
    res: dict[str, dict] = {}

    ac, pc = e("activo_corriente"), e("pasivo_corriente")
    inv, deud, prov = e("inventarios"), e("deudores_comerciales"), e("proveedores")
    at, pt, pat = e("activo_total"), e("pasivo_total"), e("patrimonio")
    ing, costo = r("ingresos_operacionales"), r("costo_ventas")
    uo, un, gf = r("utilidad_operacional"), r("utilidad_neta"), r("gastos_financieros")
    patrimonio_no_positivo = pat is not None and pat <= 0
    motivo_patrimonio = "Patrimonio negativo o cero: ver hallazgo de negocio en marcha"

    # Liquidez
    res["razon_corriente"] = _cociente(ac, pc, "Pasivo corriente igual a cero")
    res["prueba_acida"] = (_cociente(ac - inv, pc, "Pasivo corriente igual a cero")
                           if ac is not None and inv is not None else na("Falta un dato para el cálculo"))
    res["capital_trabajo_neto"] = ok(ac - pc) if None not in (ac, pc) else na("Falta un dato para el cálculo")
    res["ktno"] = (ok(deud + inv - prov) if None not in (deud, inv, prov)
                   else na("Falta un dato para el cálculo"))

    # Endeudamiento
    res["nivel_endeudamiento"] = _cociente(pt, at, "Activo total igual a cero")
    res["concentracion_cp"] = _cociente(pc, pt, "La empresa no tiene pasivos")
    if patrimonio_no_positivo:
        res["apalancamiento_total"] = na(motivo_patrimonio)
        res["apalancamiento_financiero"] = na(motivo_patrimonio)
    else:
        res["apalancamiento_total"] = _cociente(pt, pat, "Patrimonio igual a cero")
        ofcp, oflp = e("obligaciones_financieras_cp"), e("obligaciones_financieras_lp")
        deuda = ofcp + oflp if None not in (ofcp, oflp) else None
        res["apalancamiento_financiero"] = _cociente(deuda, pat, "Patrimonio igual a cero")
    if gf == 0:
        res["cobertura_intereses"] = na("La empresa no registra gastos por intereses", "no_aplica")
    else:
        res["cobertura_intereses"] = _cociente(uo, gf, "Sin gastos por intereses")

    # Rentabilidad
    if costo in (None, 0):
        res["margen_bruto"] = na("La empresa no separa el costo de ventas; el margen bruto no es comparable",
                                 "no_aplica")
    else:
        res["margen_bruto"] = _cociente(r("utilidad_bruta"), ing, "Ingresos operacionales iguales a cero")
    res["margen_operacional"] = _cociente(uo, ing, "Ingresos operacionales iguales a cero")
    res["margen_neto"] = _cociente(un, ing, "Ingresos operacionales iguales a cero")
    at_prom, at_final = promedio(periodos, i, "esf", "activo_total")
    res["roa"] = _cociente(un, at_prom, "Activo total igual a cero", at_final)
    pat_prom, pat_final = promedio(periodos, i, "esf", "patrimonio")
    if patrimonio_no_positivo or (pat_prom is not None and pat_prom <= 0):
        res["roe"] = na(motivo_patrimonio)
    else:
        res["roe"] = _cociente(un, pat_prom, "Patrimonio igual a cero", pat_final)

    # Actividad
    deud_prom, deud_final = promedio(periodos, i, "esf", "deudores_comerciales")
    res["dias_cartera"] = _cociente(deud_prom, ing, "Ingresos operacionales iguales a cero",
                                    deud_final, dias)
    inv_prom, inv_final = promedio(periodos, i, "esf", "inventarios")
    if inv_prom == 0:
        res["dias_inventario"] = na("La empresa no maneja inventarios", "no_aplica")
    elif costo == 0:
        res["dias_inventario"] = na("Costo de ventas igual a cero")
    else:
        res["dias_inventario"] = _cociente(inv_prom, costo, "Costo de ventas igual a cero", inv_final, dias)
    prov_prom, prov_final = promedio(periodos, i, "esf", "proveedores")
    if costo == 0 and prov_prom is not None:
        res["dias_proveedores"] = na("La empresa no registra costo de ventas", "no_aplica")
    else:
        res["dias_proveedores"] = _cociente(prov_prom, costo, "Costo de ventas igual a cero", prov_final, dias)

    componentes = [res["dias_cartera"], res["dias_inventario"], res["dias_proveedores"]]
    if any(c["estado"] == "n.a." and c["tipo"] == "sin_dato" for c in componentes):
        res["ciclo_efectivo"] = na("Falta un componente del ciclo")
    else:
        valor = lambda c: c["valor"] if c["estado"] == "ok" else 0.0  # noqa: E731
        ciclo = valor(componentes[0]) + valor(componentes[1]) - valor(componentes[2])
        res["ciclo_efectivo"] = ok(ciclo, any(c.get("base_saldo_final") for c in componentes))
        if any(c["estado"] == "n.a." for c in componentes):
            res["ciclo_efectivo"]["nota"] = "Componentes que no aplican se tomaron como 0"
    res["rotacion_activos"] = _cociente(ing, at_prom, "Activo total igual a cero", at_final)
    return res


# --------------------------------------------------------------------------
# Comparación sectorial
# --------------------------------------------------------------------------

def cargar_rangos(ruta: Path) -> list[dict]:
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        filas = []
        for fila in csv.DictReader(f):
            filas.append({
                "anio": int(fila["anio"]),
                "nivel": fila["nivel"].strip(),
                "codigo": fila["codigo"].strip(),
                "indicador": fila["indicador"].strip(),
                "p25": float(fila["p25"]),
                "p50": float(fila["p50"]),
                "p75": float(fila["p75"]),
                "n_empresas": int(fila["n_empresas"]),
            })
    return filas


def buscar_rango(rangos: list[dict], indicador: str, ciiu: str | None) -> dict | None:
    """División CIIU (si n >= 30) → sección CIIU → nacional, en el año más reciente."""
    filas = [f for f in rangos if f["indicador"] == indicador]
    if not filas:
        return None
    anio = max(f["anio"] for f in filas)
    filas = [f for f in filas if f["anio"] == anio]
    candidatos = []
    if ciiu and len(ciiu) >= 2:
        candidatos.append(("division", ciiu[:2]))
    seccion = seccion_ciiu(ciiu)
    if seccion:
        candidatos.append(("seccion", seccion))
    candidatos.append(("nacional", "TOTAL"))
    for nivel, codigo in candidatos:
        for f in filas:
            if f["nivel"] == nivel and f["codigo"] == codigo:
                if nivel != "nacional" and f["n_empresas"] < MIN_EMPRESAS_DIVISION:
                    break
                return dict(f)
    return None


def semaforo(valor: float, direccion: str, p25: float, p50: float, p75: float) -> str:
    if direccion == "mas":
        return "verde" if valor >= p50 else "amarillo" if valor >= p25 else "rojo"
    return "verde" if valor <= p50 else "amarillo" if valor <= p75 else "rojo"


# --------------------------------------------------------------------------
# Lecturas combinadas (indicadores.md, sección 5)
# --------------------------------------------------------------------------

def lecturas_combinadas(ind: dict, periodos: list[dict]) -> list[dict]:
    actual = periodos[-1]
    anterior = periodos[-2] if len(periodos) > 1 else None
    fecha = actual["fecha_corte"]

    def v(i: str, fecha_corte: str = fecha) -> float | None:
        return ind[i]["periodos"][fecha_corte]["valor"]

    def s(i: str) -> str | None:
        return ind[i].get("semaforo")

    def crece(seccion: str, campo: str) -> float | None:
        if anterior is None:
            return None
        a, b = dato(anterior, seccion, campo), dato(actual, seccion, campo)
        return (b - a) / a if a not in (None, 0) and b is not None and a > 0 else None

    hallazgos = []

    def agregar(id_: str, descripcion: str) -> None:
        hallazgos.append({"id": id_, "descripcion": descripcion})

    pat = dato(actual, "esf", "patrimonio")
    if pat is not None and pat <= 0:
        agregar("patrimonio_negativo", "Patrimonio negativo o cero: posible incumplimiento de la "
                "hipótesis de negocio en marcha (Ley 2069 de 2020, art. 4)")
    cob = v("cobertura_intereses")
    if cob is not None and cob < 1:
        agregar("cobertura_menor_a_1", "La utilidad operacional no alcanza para pagar los intereses")
    if s("margen_bruto") == "verde" and s("margen_operacional") == "rojo":
        agregar("gastos_operacionales_altos", "Margen bruto favorable pero margen operacional crítico: "
                "gastos de administración o ventas altos")
    if s("margen_operacional") == "verde" and s("margen_neto") == "rojo":
        agregar("carga_financiera_o_tributaria", "Margen operacional favorable pero margen neto crítico: "
                "la carga financiera o tributaria se come la utilidad")
    mo, mn = v("margen_operacional"), v("margen_neto")
    if mo is not None and mn is not None and mn > mo:
        agregar("utilidad_no_operacional", "El margen neto supera al operacional: la utilidad se "
                "sostiene en ingresos no operacionales")
    if s("razon_corriente") == "verde" and s("dias_cartera") == "rojo":
        agregar("liquidez_en_cartera", "Liquidez favorable pero cartera lenta: liquidez \"en el papel\"")
    if s("razon_corriente") == "verde" and s("dias_inventario") == "rojo":
        agregar("liquidez_en_inventario", "Liquidez favorable sostenida por inventario lento")
    if s("roe") == "verde" and s("nivel_endeudamiento") == "rojo":
        agregar("roe_por_deuda", "ROE favorable impulsado por un endeudamiento alto")

    if anterior is not None:
        f_ant = anterior["fecha_corte"]
        g_ing, g_un = crece("eri", "ingresos_operacionales"), crece("eri", "utilidad_neta")
        un_a, un_b = dato(anterior, "eri", "utilidad_neta"), dato(actual, "eri", "utilidad_neta")
        if g_ing is not None and g_ing > 0 and None not in (un_a, un_b) and un_b < un_a:
            agregar("crecimiento_sin_rentabilidad", "Los ingresos crecen pero la utilidad neta cae")
        k_a, k_b = v("ktno", f_ant), v("ktno")
        if g_ing is not None and None not in (k_a, k_b) and k_a > 0 and (k_b - k_a) / k_a > g_ing:
            agregar("ktno_crece_mas_que_ingresos", "El KTNO crece más rápido que los ingresos: la operación "
                    "consume cada vez más caja")
        e_a, e_b = v("nivel_endeudamiento", f_ant), v("nivel_endeudamiento")
        c_a, c_b = v("cobertura_intereses", f_ant), v("cobertura_intereses")
        if None not in (e_a, e_b, c_a, c_b) and e_b > e_a and c_b < c_a:
            agregar("deuda_creciente_menor_cobertura", "El endeudamiento sube mientras la cobertura de "
                    "intereses baja")
        d_a, d_b = v("dias_proveedores", f_ant), v("dias_proveedores")
        if None not in (d_a, d_b) and d_b > d_a and s("razon_corriente") == "rojo":
            agregar("posible_atraso_proveedores", "Los días de proveedores suben con liquidez crítica: "
                    "posible atraso en pagos")
    return hallazgos


# --------------------------------------------------------------------------
# Proceso principal
# --------------------------------------------------------------------------

def cargar_datos(ruta: Path) -> dict:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ErrorEntrada(f"No existe el archivo {ruta}") from exc
    except json.JSONDecodeError as exc:
        raise ErrorEntrada(f"El archivo no es un JSON válido: {exc}") from exc
    periodos = datos.get("periodos")
    if not isinstance(periodos, list) or not periodos:
        raise ErrorEntrada("El JSON debe tener una lista 'periodos' con al menos un periodo")
    for p in periodos:
        if "fecha_corte" not in p or "esf" not in p or "eri" not in p:
            raise ErrorEntrada("Cada periodo debe tener 'fecha_corte', 'esf' y 'eri'")
    datos["periodos"] = sorted(periodos, key=lambda p: p["fecha_corte"])
    return datos


def analizar(datos: dict, rangos: list[dict] | None) -> dict:
    periodos = datos["periodos"]
    ciiu = str(datos.get("ciiu") or "").strip() or None
    advertencias = list(datos.get("advertencias", []))

    validaciones = [{"fecha_corte": p["fecha_corte"], "reglas": validar(p)} for p in periodos]
    por_periodo = {p["fecha_corte"]: calcular_periodo(periodos, i) for i, p in enumerate(periodos)}
    ultima = periodos[-1]["fecha_corte"]
    anterior = periodos[-2]["fecha_corte"] if len(periodos) > 1 else None

    if len(periodos) == 1:
        advertencias.append("Solo hay un periodo: las rotaciones y rentabilidades usan saldos finales "
                            "y no hay análisis horizontal.")
    if rangos is None:
        advertencias.append("No se encontraron rangos sectoriales: los indicadores no tienen semáforo.")
    elif not ciiu:
        advertencias.append("Sin código CIIU: la comparación se hizo contra el total nacional.")

    indicadores = {}
    for id_, (grupo, unidad, direccion) in INDICADORES.items():
        info = {
            "grupo": grupo,
            "unidad": unidad,
            "direccion": direccion,
            "periodos": {fecha: por_periodo[fecha][id_] for fecha in por_periodo},
            "variacion": None,
            "sector": None,
            "semaforo": None,
        }
        actual = info["periodos"][ultima]["valor"]
        if anterior and actual is not None and info["periodos"][anterior]["valor"] is not None:
            info["variacion"] = round(actual - info["periodos"][anterior]["valor"], 6)
        if rangos is not None and direccion != "ninguna":
            rango = buscar_rango(rangos, id_, ciiu)
            if rango:
                info["sector"] = {k: rango[k] for k in ("anio", "nivel", "codigo", "n_empresas", "p25", "p50", "p75")}
                if actual is not None:
                    info["semaforo"] = semaforo(actual, direccion, rango["p25"], rango["p50"], rango["p75"])
        indicadores[id_] = info

    niveles = {i["sector"]["nivel"] for i in indicadores.values() if i["sector"]}
    if ciiu and niveles - {"division"}:
        advertencias.append("Algunos indicadores se compararon a nivel de sección CIIU o nacional por "
                            "insuficiencia de datos en la división.")

    return {
        "empresa": datos.get("empresa"),
        "nit": datos.get("nit"),
        "ciiu": ciiu,
        "seccion_ciiu": seccion_ciiu(ciiu),
        "marco": datos.get("marco"),
        "unidades": datos.get("unidades"),
        "moneda": datos.get("moneda", "COP"),
        "fecha_corte": ultima,
        "periodos": [p["fecha_corte"] for p in periodos],
        "validaciones": validaciones,
        "vertical": {p["fecha_corte"]: vertical(p) for p in periodos},
        "horizontal": [horizontal(periodos[i - 1], periodos[i]) for i in range(1, len(periodos))],
        "indicadores": indicadores,
        "lecturas_combinadas": lecturas_combinadas(indicadores, periodos),
        "advertencias": advertencias,
    }


def formatear(valor: float | None, unidad: str) -> str:
    if valor is None:
        return "n.a."
    if unidad == "%":
        return f"{valor * 100:.1f}%"
    if unidad == "veces":
        return f"{valor:.2f}"
    return f"{valor:,.0f}"


def imprimir_resumen(resultado: dict) -> None:
    simbolos = {"verde": "[VERDE]", "amarillo": "[AMARILLO]", "rojo": "[ROJO]", None: ""}
    print(f"{resultado['empresa'] or 'Empresa'} | CIIU {resultado['ciiu'] or 'n.d.'} | "
          f"corte {resultado['fecha_corte']}")
    fallas = [r for v in resultado["validaciones"] for r in v["reglas"] if not r["ok"]]
    print(f"Validaciones: {'todas cuadran' if not fallas else f'{len(fallas)} con diferencias'}")
    for id_, info in resultado["indicadores"].items():
        actual = info["periodos"][resultado["fecha_corte"]]["valor"]
        sector = info["sector"]
        p50 = f" | sector P50 {formatear(sector['p50'], info['unidad'])}" if sector else ""
        print(f"  {id_:<27} {formatear(actual, info['unidad']):>14}{p50} {simbolos[info['semaforo']]}")
    for lectura in resultado["lecturas_combinadas"]:
        print(f"  * {lectura['descripcion']}")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Calcula indicadores financieros y semáforo sectorial.")
    parser.add_argument("entrada", type=Path, help="datos_homologados.json")
    parser.add_argument("--salida", type=Path, help="Ruta del JSON de resultados "
                        "(por defecto: resultados_indicadores.json junto a la entrada)")
    parser.add_argument("--rangos", type=Path, default=RUTA_RANGOS, help="CSV de rangos sectoriales")
    parser.add_argument("--forzar", action="store_true",
                        help="Calcular aunque la ecuación contable no cuadre")
    args = parser.parse_args(argv)

    try:
        datos = cargar_datos(args.entrada)
        rangos = cargar_rangos(args.rangos) if args.rangos.exists() else None
        resultado = analizar(datos, rangos)
    except (ErrorEntrada, KeyError, ValueError) as exc:
        print(f"Error en la entrada: {exc}", file=sys.stderr)
        return 1

    criticas = [r for v in resultado["validaciones"] for r in v["reglas"] if r["critica"] and not r["ok"]]
    if criticas and not args.forzar:
        for r in criticas:
            print(f"La ecuación contable no cuadra: activo {r['esperado']:,.0f} vs pasivo + patrimonio "
                  f"{r['calculado']:,.0f} (diferencia {r['diferencia']:,.0f}).", file=sys.stderr)
        print("Revisa la homologación o usa --forzar.", file=sys.stderr)
        return 2

    salida = args.salida or args.entrada.with_name("resultados_indicadores.json")
    salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    imprimir_resumen(resultado)
    print(f"Resultados guardados en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
