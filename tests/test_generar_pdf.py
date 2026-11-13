"""Pruebas de generar_pdf.py.

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
    import generar_pdf as gp
except ImportError:  # reportlab o matplotlib no instalados
    gp = None

import calcular_indicadores as ci  # noqa: E402
from test_calcular_indicadores import EJEMPLO, rangos_ficticios  # noqa: E402

TEXTOS = {
    "conclusion": "Conclusión de prueba.",
    "hallazgos": [{"semaforo": s, "titulo": f"Hallazgo {s}", "detalle": "Detalle de prueba."}
                  for s in ("rojo", "amarillo", "verde")],
    "grupos": {g: "Párrafo de prueba." for g in ("liquidez", "endeudamiento", "rentabilidad", "actividad")},
    "recomendaciones": ["Recomendación de prueba."],
}


@unittest.skipIf(gp is None, "reportlab o matplotlib no están instalados")
class TestGenerarPdf(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.datos = ci.cargar_datos(EJEMPLO)

    def tearDown(self):
        self.tmp.cleanup()

    def test_formato_numerico(self):
        self.assertEqual(gp.fmt(1234567.89, "COP", "es", "n.a."), "1.234.568")
        self.assertEqual(gp.fmt(1234567.89, "COP", "en", "n/a"), "1,234,568")
        self.assertEqual(gp.fmt(-120000, "COP", "es", "n.a."), "(120.000)")
        self.assertEqual(gp.fmt(0.125, "%", "es", "n.a."), "12,5%")
        self.assertEqual(gp.fmt(1.854, "veces", "en", "n/a"), "1.85x")
        self.assertEqual(gp.fmt(None, "dias", "es", "n.a."), "n.a.")

    def test_fecha_larga(self):
        self.assertEqual(gp.fecha_larga("2025-12-31", "es"), "31 de diciembre de 2025")
        self.assertEqual(gp.fecha_larga("2025-12-31", "en"), "December 31, 2025")

    def test_genera_pdf_entre_2_y_4_paginas_en_ambos_idiomas(self):
        res = ci.analizar(self.datos, rangos_ficticios())
        for idioma, nombre in (("es", "Informe_EEFF_Comercializadora_Ejemplo_2025_ES.pdf"),
                               ("en", "Financial_Report_Comercializadora_Ejemplo_2025_EN.pdf")):
            ruta, paginas = gp.generar(self.datos, res, idioma, TEXTOS, carpeta=self.dir)
            self.assertEqual(ruta.name, nombre)
            self.assertTrue(ruta.read_bytes().startswith(b"%PDF"))
            self.assertGreaterEqual(paginas, 2)
            self.assertLessEqual(paginas, gp.MAX_PAGINAS)

    def test_sin_rangos_ni_textos(self):
        res = ci.analizar(self.datos, None)
        ruta, paginas = gp.generar(self.datos, res, "es", {}, carpeta=self.dir)
        self.assertTrue(ruta.exists())
        self.assertLessEqual(paginas, gp.MAX_PAGINAS)

    def test_un_solo_periodo(self):
        datos = {**self.datos, "periodos": self.datos["periodos"][-1:]}
        res = ci.analizar(datos, rangos_ficticios())
        ruta, _ = gp.generar(datos, res, "en", TEXTOS, carpeta=self.dir)
        self.assertTrue(ruta.exists())


if __name__ == "__main__":
    unittest.main()
