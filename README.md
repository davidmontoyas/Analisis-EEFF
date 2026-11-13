# 📊 Analisis-EEFF

> 🚧 **En construcción.** La skill todavía no funciona completa: faltan los
> rangos sectoriales y el script que genera el PDF. Ya están disponibles
> `SKILL.md`, las cuatro referencias, `calcular_indicadores.py` y
> `generar_excel.py` (con pruebas automáticas).
> Puedes seguir el avance en la
> sección **Hoja de ruta**, al final de este documento.

Skill para Claude que analiza el Estado de Situación Financiera (ESF) y el
Estado de Resultados Integral (ERI) de una empresa, calcula los principales
indicadores financieros, **los compara con su sector económico usando
información de la Superintendencia de Sociedades** y entrega un informe
interpretado, listo para presentar al cliente o a la gerencia.

Pensada para contadores públicos, revisores fiscales y asesores financieros
que trabajan con empresas colombianas bajo NIIF (plenas o para Pymes).

---

## ✨ ¿Qué hace?

1. **Lee los estados financieros** que le entregues (Excel, PDF o datos pegados en el chat).
2. **Homologa las cuentas** a una estructura estándar (activo corriente, pasivo
   corriente, ingresos operacionales, etc.), aunque vengan con nombres distintos.
3. **Identifica el sector** de la empresa por su código CIIU (del RUT).
4. **Calcula los indicadores** de uno o varios periodos (análisis vertical,
   horizontal y razones financieras).
5. **Compara contra el sector** y asigna un semáforo 🟢🟡🔴 según la posición
   de la empresa frente a sus pares.
6. **Genera el informe** en Excel y PDF, cada uno en español y en inglés.

---

## 📐 Indicadores incluidos

| Grupo | Indicadores |
|---|---|
| **Liquidez** | Razón corriente · Prueba ácida · Capital de trabajo neto · KTNO |
| **Endeudamiento** | Nivel de endeudamiento · Concentración de deuda a corto plazo · Apalancamiento total y financiero · Cobertura de intereses (utilidad operacional / gastos financieros) |
| **Rentabilidad** | Margen bruto · Margen operacional · Margen neto · ROA · ROE |
| **Actividad** | Rotación de cartera (días) · Rotación de inventarios (días) · Rotación de proveedores (días) · Ciclo de conversión de efectivo · Rotación de activos |
| **Análisis estructural** | Análisis vertical · Análisis horizontal (variación absoluta y relativa) |

Cada indicador incluye fórmula, resultado, valor del sector, interpretación y semáforo.

---

## 🚦 Semáforo sectorial

Los rangos **no son genéricos**: se calculan a partir de los estados
financieros que las sociedades reportan a la **Superintendencia de Sociedades**
(datos abiertos del SIIS), agrupados por sección y división CIIU.

Para cada indicador y sector se guardan los cuartiles del sector:

| Semáforo | Indicadores donde "más es mejor" (ej. ROE, razón corriente) | Indicadores donde "menos es mejor" (ej. endeudamiento, días de cartera) |
|---|---|---|
| 🟢 Favorable | Igual o por encima de la mediana (P50) | Igual o por debajo de la mediana (P50) |
| 🟡 Atención | Entre P25 y P50 | Entre P50 y P75 |
| 🔴 Crítico | Por debajo de P25 | Por encima de P75 |

- El informe indica siempre **el sector, el año de corte y el número de
  empresas** que se usaron para calcular los rangos.
- Si no se conoce el CIIU, o el sector tiene muy pocas empresas, la skill usa
  los rangos de la **sección CIIU** (nivel más general) y lo advierte.
- **Los rangos ya vienen calculados** en `datos/rangos_sectoriales.csv`: la
  skill funciona apenas se instala, sin descargar nada ni correr scripts.
- El encargado del repositorio los actualiza una vez al año (ver
  [Actualizar los rangos sectoriales](#-actualizar-los-rangos-sectoriales)).

---

## 📥 Insumos que acepta

- Archivo **Excel** con ESF y ERI (una o varias hojas, uno o varios años).
- **PDF** de estados financieros firmados o reportados a Supersociedades.
- **Balance de prueba** por cuentas PUC (la skill lo agrupa automáticamente).
- Datos **pegados directamente** en el chat.
- **Código CIIU** de la actividad principal (si no lo das, la skill lo pregunta).

> 💡 Para análisis horizontal y de tendencias se recomiendan **al menos 2 periodos**.

---

## 📤 Qué entrega

| Archivo | Idioma | Contenido |
|---|---|---|
| 📗 `Analisis_EEFF_<empresa>_<año>_ES.xlsx` | Español | Datos homologados, indicadores con fórmulas vivas, comparación sectorial, análisis vertical/horizontal y gráficas |
| 📗 `Financial_Analysis_<company>_<year>_EN.xlsx` | Inglés | El mismo libro, con hojas, rótulos, notas y gráficas en inglés |
| 📄 `Informe_EEFF_<empresa>_<año>_ES.pdf` | Español | Informe ejecutivo (2 a 4 páginas): hallazgos, alertas y recomendaciones |
| 📄 `Financial_Report_<company>_<year>_EN.pdf` | Inglés | El mismo informe, para casas matrices, bancos o inversionistas extranjeros |

Las cifras son idénticas en ambos idiomas. Solo cambian los textos y el
formato numérico (separador decimal `,` en español y `.` en inglés).

Por defecto se generan los cuatro archivos. Puedes pedir solo un idioma:
*"solo en español"* o *"only in English"*.

Además, en el chat se muestra un resumen con los 5 hallazgos más relevantes.

---

## 🚀 Instalación

### En Claude Code
```bash
git clone https://github.com/davidmontoyas/Analisis-EEFF.git
cp -r Analisis-EEFF/analisis-eeff ~/.claude/skills/
```

En Windows, la carpeta de destino es `%USERPROFILE%\.claude\skills\`.

Los scripts necesitan **Python 3.10 o superior** y estas librerías:

```bash
pip install -r Analisis-EEFF/requirements.txt
```

### En Claude.ai / Claude Desktop
1. Descarga la carpeta `analisis-eeff` como `.zip`.
2. Ve a **Configuración → Capacidades → Skills** y súbela.

---

## 💬 Ejemplos de uso

- *"Analiza los estados financieros de este Excel y dame los indicadores 2024 vs 2025."*
- *"¿Cómo está la liquidez de esta empresa frente a su sector? CIIU 4711."*
- *"Prepárame el informe para la junta, en español y en inglés."*
- *"Te adjunto el balance de prueba; compara la rentabilidad con el promedio del sector."*

---

## 🗂️ Estructura del repositorio

```
Analisis-EEFF/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── requirements.txt                # Librerías de Python para los scripts
├── tests/                          # Pruebas automáticas de los scripts
└── analisis-eeff/                  # ← la skill (esta es la carpeta que se instala)
    ├── SKILL.md                    # Instrucciones principales para Claude
    ├── referencias/
    │   ├── indicadores.md          # Fórmulas, interpretación y dirección (más/menos es mejor)
    │   ├── homologacion-puc.md     # Mapeo de cuentas PUC a la estructura estándar
    │   ├── glosario-es-en.md       # Terminología financiera español ↔ inglés
    │   └── plantilla-informe.md    # Estructura del informe ejecutivo
    ├── datos/
    │   └── rangos_sectoriales.csv  # Cuartiles ya calculados por CIIU, indicador y año (fuente: Supersociedades)
    ├── scripts/
    │   ├── calcular_indicadores.py
    │   ├── generar_excel.py
    │   ├── generar_pdf.py
    │   └── actualizar_rangos.py    # Recalcula los rangos con datos nuevos de Supersociedades
    └── ejemplos/
        └── empresa-ejemplo.json    # Datos ficticios ya homologados, para probar
```

---

## 🔄 Actualizar los rangos sectoriales

> 👥 **Los usuarios de la skill no tienen que hacer nada aquí.** Esta sección
> es para quien mantiene el repositorio.

Supersociedades publica cada año los estados financieros de las sociedades
que vigila. Una vez al año, después de la temporada de reporte:

```bash
python analisis-eeff/scripts/actualizar_rangos.py --anio 2025
```

El script descarga los datos abiertos, calcula los indicadores de cada
empresa, descarta valores atípicos y guarda en `datos/rangos_sectoriales.csv`
**solo los cuartiles por sector** (no los datos de cada empresa), de modo que
el archivo se mantiene liviano. Luego se publica una nueva versión del
repositorio y los colegas actualizan con `git pull`.

El CSV conserva los años anteriores, lo que permite comparar la evolución de
un sector en el tiempo.

---

## ⚠️ Limitaciones y advertencias

- Los rangos sectoriales provienen de **sociedades vigiladas por
  Supersociedades**, que suelen ser medianas y grandes. Para microempresas,
  la comparación es solo orientativa.
- Los datos sectoriales tienen **rezago de al menos un año** frente al
  periodo que se analiza.
- La skill **no reemplaza el juicio profesional** del contador.
- Verifica siempre las cifras de origen: el análisis es tan bueno como los datos.
- No subas información confidencial de clientes a repositorios públicos.

---

## 🛣️ Hoja de ruta

- [ ] **v1.0:** indicadores, semáforo sectorial con rangos incluidos, Excel + PDF en ES/EN
- [ ] **v1.1:** indicadores de valor (EBITDA, margen EBITDA, productividad del
      KTNO, palanca de crecimiento, sistema DuPont)
- [ ] **v1.2:** comparación entre varias empresas del mismo grupo o cartera de clientes

---

## 🧪 Pruebas

Desde la raíz del repositorio:

```bash
python -m unittest discover -s tests -v
```

Para ver el cálculo con la empresa de ejemplo:

```bash
python analisis-eeff/scripts/calcular_indicadores.py analisis-eeff/ejemplos/empresa-ejemplo.json
```

---

## 🤝 Contribuciones

¿Tienes un indicador, una mejora a la homologación PUC o encontraste un error
en los rangos? Abre un *issue* o envía un *pull request*. Ver `CONTRIBUTING.md`.

---

## 📄 Licencia

MIT. Libre para usar, modificar y compartir.

---

**Hecho por contadores, para contadores.** 🇨🇴
