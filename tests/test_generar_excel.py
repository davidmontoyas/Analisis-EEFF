"""Pruebas de generar_excel.py (estructura del libro).

Los valores de las fórmulas no se pueden calcular sin Excel; la comparación
contra calcular_indicadores.py se hizo abriendo los archivos en Excel. Estas
pruebas revisan que el libro tenga la estructura de plantilla-informe.md.

Ejecutar desde la raíz del repositorio:
    python -m unittest discover -s tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "analisis-eeff" / "scripts"))
sys.path.insert(0, str(RAIZ / "tests"))

try:
    import openpyxl
    import generar_excel as ge
except ImportError:  # openpyxl no instalado
    openpyxl = None

import calcular_indicadores as ci  # noqa: E402
from test_calcular_indicadores import EJEMPLO, rangos_ficticios  # noqa: E402


@unittest.skipIf(openpyxl is None, "openpyxl no está instalado")
class TestGenerarExcel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        carpeta = Path(cls.tmp.name)
        datos = ci.cargar_datos(EJEMPLO)
        cls.res = ci.analizar(datos, rangos_ficticios())
        textos = {"conclusion": "Prueba", "hallazgos": [{"semaforo": "rojo", "titulo": "T", "detalle": "D"}]}
        cls.rutas = {idioma: ge.generar(datos, cls.res, idioma, textos, carpeta=carpeta) for idioma in ("es", "en")}
        cls.libros = {idioma: openpyxl.load_workbook(ruta) for idioma, ruta in cls.rutas.items()}

    @classmethod
    def tearDownClass(cls):
        for wb in cls.libros.values():
            wb.close()
        cls.tmp.cleanup()

    def test_nombres_de_archivo(self):
        self.assertEqual(self.rutas["es"].name, "Analisis_EEFF_Comercializadora_Ejemplo_2025_ES.xlsx")
        self.assertEqual(self.rutas["en"].name, "Financial_Analysis_Comercializadora_Ejemplo_2025_EN.xlsx")

    def test_ocho_hojas_por_idioma(self):
        self.assertEqual(self.libros["es"].sheetnames, ge.T["es"]["hojas"])
        self.assertEqual(self.libros["en"].sheetnames, ge.T["en"]["hojas"])

    def test_nombres_definidos(self):
        nombres = set(self.libros["es"].defined_names.keys())
        for campo in ("activo_corriente", "pasivo_corriente", "utilidad_neta", "dias_periodo"):
            self.assertIn(f"{campo}_2024", nombres)
            self.assertIn(f"{campo}_2025", nombres)

    def test_indicadores_son_formulas(self):
        ws = self.libros["es"]["Indicadores"]
        formulas = [c.value for fila in ws.iter_rows(min_row=5, min_col=4, max_col=5) for c in fila
                    if isinstance(c.value, str) and c.value.startswith("=")]
        self.assertEqual(len(formulas), 2 * len(ci.INDICADORES))
        self.assertTrue(all("None" not in f for f in formulas))

    def test_totales_son_formulas_y_entradas_desbloqueadas(self):
        ws = self.libros["es"]["Datos"]
        por_campo = {ws.cell(row=r, column=1).value: r for r in range(1, ws.max_row + 1)}
        self.assertTrue(str(ws.cell(row=por_campo["activo_total"], column=4).value).startswith("="))
        entrada = ws.cell(row=por_campo["efectivo"], column=4)
        self.assertEqual(entrada.value, 120500)
        self.assertFalse(entrada.protection.locked)
        self.assertTrue(ws.protection.sheet)

    def test_semaforo_en_ingles(self):
        ws = self.libros["en"]["Ratios"]
        textos = " ".join(str(c.value) for fila in ws.iter_rows() for c in fila if c.value)
        self.assertIn("Watch", textos)
        self.assertNotIn("Atención", textos)

    def test_seis_graficas(self):
        # openpyxl no lee gráficas de un archivo existente: se revisa el libro antes de guardarlo.
        datos = ci.cargar_datos(EJEMPLO)
        wb = ge.Libro(datos, self.res, {}, "es").construir()
        self.assertEqual(len(wb["Gráficas"]._charts), 6)


if __name__ == "__main__":
    unittest.main()
