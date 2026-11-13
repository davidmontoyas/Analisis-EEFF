"""Pruebas de calcular_indicadores.py.

Ejecutar desde la raíz del repositorio:
    python -m unittest discover -s tests -v
"""

import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analisis-eeff" / "scripts"))

import calcular_indicadores as ci  # noqa: E402

EJEMPLO = RAIZ / "analisis-eeff" / "ejemplos" / "empresa-ejemplo.json"


def rangos_ficticios() -> list[dict]:
    """Rangos inventados para probar la lógica, no son datos reales."""
    filas = []
    for indicador, (_, _, direccion) in ci.INDICADORES.items():
        if direccion == "ninguna":
            continue
        for nivel, codigo, n in (("division", "47", 180), ("seccion", "G", 900), ("nacional", "TOTAL", 9000)):
            filas.append({"anio": 2024, "nivel": nivel, "codigo": codigo, "indicador": indicador,
                          "p25": 1.0, "p50": 2.0, "p75": 3.0, "n_empresas": n})
    # La división 47 tiene pocas empresas para días de inventario: debe usar la sección G.
    for f in filas:
        if f["indicador"] == "dias_inventario" and f["nivel"] == "division":
            f["n_empresas"] = 12
        if f["indicador"] == "dias_inventario" and f["nivel"] == "seccion":
            f.update(p25=40.0, p50=60.0, p75=90.0)
    # Un año anterior que no debe usarse.
    filas.append({"anio": 2023, "nivel": "division", "codigo": "47", "indicador": "razon_corriente",
                  "p25": 9.0, "p50": 9.5, "p75": 10.0, "n_empresas": 500})
    return filas


def cargar_ejemplo() -> dict:
    return ci.cargar_datos(EJEMPLO)


def valor(resultado: dict, indicador: str, fecha: str = "2025-12-31"):
    return resultado["indicadores"][indicador]["periodos"][fecha]


class TestEjemplo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = ci.analizar(cargar_ejemplo(), rangos_ficticios())

    def test_validaciones_cuadran(self):
        for periodo in self.r["validaciones"]:
            for regla in periodo["reglas"]:
                self.assertTrue(regla["ok"], regla)

    def test_liquidez(self):
        self.assertAlmostEqual(valor(self.r, "razon_corriente")["valor"], 1000300 / 585000, places=6)
        self.assertAlmostEqual(valor(self.r, "prueba_acida")["valor"], (1000300 - 410000) / 585000, places=6)
        self.assertEqual(valor(self.r, "capital_trabajo_neto")["valor"], 415300)
        self.assertEqual(valor(self.r, "ktno")["valor"], 405000 + 410000 - 275000)

    def test_endeudamiento(self):
        self.assertAlmostEqual(valor(self.r, "nivel_endeudamiento")["valor"], 930000 / 1650000, places=6)
        self.assertAlmostEqual(valor(self.r, "apalancamiento_financiero")["valor"], 495000 / 720000, places=6)
        self.assertAlmostEqual(valor(self.r, "cobertura_intereses")["valor"], 184000 / 42000, places=6)

    def test_rentabilidad_usa_promedios(self):
        self.assertAlmostEqual(valor(self.r, "roa")["valor"], 95000 / 1575000, places=6)
        self.assertAlmostEqual(valor(self.r, "roe")["valor"], 95000 / 665000, places=6)
        self.assertFalse(valor(self.r, "roe")["base_saldo_final"])
        self.assertTrue(valor(self.r, "roe", "2024-12-31")["base_saldo_final"])

    def test_actividad_base_360(self):
        dc = (310000 + 405000) / 2 / 2800000 * 360
        di = (380000 + 410000) / 2 / 2016000 * 360
        dp = (260000 + 275000) / 2 / 2016000 * 360
        self.assertAlmostEqual(valor(self.r, "dias_cartera")["valor"], dc, places=4)
        self.assertAlmostEqual(valor(self.r, "ciclo_efectivo")["valor"], dc + di - dp, places=4)

    def test_sector_usa_anio_mas_reciente_y_division(self):
        sector = self.r["indicadores"]["razon_corriente"]["sector"]
        self.assertEqual((sector["anio"], sector["nivel"], sector["codigo"]), (2024, "division", "47"))

    def test_sector_baja_a_seccion_si_division_pequena(self):
        info = self.r["indicadores"]["dias_inventario"]
        self.assertEqual((info["sector"]["nivel"], info["sector"]["codigo"]), ("seccion", "G"))
        self.assertEqual(info["semaforo"], "amarillo")  # ~71 días: entre P50 = 60 y P75 = 90

    def test_sin_semaforo_para_valores_absolutos(self):
        self.assertIsNone(self.r["indicadores"]["ktno"]["semaforo"])
        self.assertIsNone(self.r["indicadores"]["dias_proveedores"]["sector"])

    def test_horizontal(self):
        h = self.r["horizontal"][0]["eri"]["ingresos_operacionales"]
        self.assertEqual(h["absoluta"], 300000)
        self.assertAlmostEqual(h["relativa"], 0.12, places=6)

    def test_json_serializable(self):
        json.dumps(self.r, ensure_ascii=False)


class TestSemaforo(unittest.TestCase):
    def test_mas_es_mejor(self):
        self.assertEqual(ci.semaforo(2.0, "mas", 1, 2, 3), "verde")
        self.assertEqual(ci.semaforo(1.5, "mas", 1, 2, 3), "amarillo")
        self.assertEqual(ci.semaforo(0.9, "mas", 1, 2, 3), "rojo")

    def test_menos_es_mejor(self):
        self.assertEqual(ci.semaforo(2.0, "menos", 1, 2, 3), "verde")
        self.assertEqual(ci.semaforo(2.5, "menos", 1, 2, 3), "amarillo")
        self.assertEqual(ci.semaforo(3.1, "menos", 1, 2, 3), "rojo")


class TestCasosEspeciales(unittest.TestCase):
    def test_patrimonio_negativo(self):
        datos = cargar_ejemplo()
        p = datos["periodos"][-1]["esf"]
        p["patrimonio"] = -50000
        p["pasivo_total"] = 1700000
        r = ci.analizar(datos, None)
        self.assertEqual(valor(r, "roe")["estado"], "n.a.")
        self.assertEqual(valor(r, "apalancamiento_total")["estado"], "n.a.")
        self.assertIn("patrimonio_negativo", [l["id"] for l in r["lecturas_combinadas"]])

    def test_empresa_de_servicios_sin_inventario(self):
        datos = cargar_ejemplo()
        for p in datos["periodos"]:
            p["esf"]["inventarios"] = 0
        r = ci.analizar(datos, None)
        di = valor(r, "dias_inventario")
        self.assertEqual((di["estado"], di["tipo"]), ("n.a.", "no_aplica"))
        self.assertEqual(valor(r, "ciclo_efectivo")["estado"], "ok")

    def test_sin_gastos_financieros(self):
        datos = cargar_ejemplo()
        datos["periodos"][-1]["eri"]["gastos_financieros"] = 0
        r = ci.analizar(datos, None)
        self.assertEqual(valor(r, "cobertura_intereses")["tipo"], "no_aplica")

    def test_division_por_cero_no_rompe(self):
        datos = cargar_ejemplo()
        datos["periodos"][-1]["esf"]["pasivo_corriente"] = 0
        r = ci.analizar(datos, None)
        self.assertEqual(valor(r, "razon_corriente")["estado"], "n.a.")

    def test_sin_rangos_avisa(self):
        r = ci.analizar(cargar_ejemplo(), None)
        self.assertTrue(any("rangos sectoriales" in a for a in r["advertencias"]))

    def test_seccion_ciiu(self):
        self.assertEqual(ci.seccion_ciiu("4711"), "G")
        self.assertEqual(ci.seccion_ciiu("1011"), "C")
        self.assertEqual(ci.seccion_ciiu("6201"), "J")
        self.assertIsNone(ci.seccion_ciiu(None))


class TestLineaDeComandos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.rangos = self.dir / "rangos.csv"
        with self.rangos.open("w", encoding="utf-8", newline="") as f:
            filas = rangos_ficticios()
            w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)

    def tearDown(self):
        self.tmp.cleanup()

    def test_ejecucion_completa(self):
        salida = self.dir / "resultados.json"
        codigo = ci.main([str(EJEMPLO), "--rangos", str(self.rangos), "--salida", str(salida)])
        self.assertEqual(codigo, 0)
        self.assertIn("indicadores", json.loads(salida.read_text(encoding="utf-8")))

    def test_ecuacion_contable_descuadrada(self):
        datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
        datos["periodos"][-1]["esf"]["activo_total"] = 1800000
        entrada = self.dir / "descuadrado.json"
        entrada.write_text(json.dumps(datos), encoding="utf-8")
        self.assertEqual(ci.main([str(entrada), "--rangos", str(self.rangos)]), 2)
        self.assertEqual(ci.main([str(entrada), "--rangos", str(self.rangos), "--forzar"]), 0)

    def test_entrada_invalida(self):
        entrada = self.dir / "malo.json"
        entrada.write_text("{\"periodos\": []}", encoding="utf-8")
        self.assertEqual(ci.main([str(entrada)]), 1)


if __name__ == "__main__":
    unittest.main()
