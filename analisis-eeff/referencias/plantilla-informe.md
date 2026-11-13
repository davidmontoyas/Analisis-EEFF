# Plantilla de los entregables

Define el contenido y la forma del **informe ejecutivo en PDF** y del **libro
de Excel**, en español y en inglés. `generar_pdf.py` y `generar_excel.py`
siguen esta estructura; Claude redacta los textos.

Para la versión en inglés, todos los títulos, rótulos y frases salen de
`glosario-es-en.md`. Las cifras y el orden de los hallazgos son idénticos en
ambos idiomas.

---

## 1. Principios

- **Lector**: gerente, socio o junta directiva, no necesariamente contador.
  Debe entender la situación de la empresa leyendo solo la primera página.
- **Primero la conclusión, después el detalle**: hallazgos → semáforo →
  análisis por grupo → metodología.
- **Cada cifra con contexto**: valor de la empresa, valor del sector y qué
  significa. Nunca un indicador suelto.
- **Breve**: el PDF tiene entre 2 y 4 páginas. El detalle completo va en el Excel.
- **El semáforo nunca depende solo del color**: siempre lleva también el
  símbolo y la palabra (🟢 Favorable), para que se entienda impreso en blanco
  y negro y por personas con daltonismo.

---

## 2. Informe ejecutivo (PDF)

### Formato

| Elemento | Valor |
|---|---|
| Tamaño | Carta (21,59 × 27,94 cm), vertical |
| Márgenes | 2 cm |
| Fuente | Sans serif (Inter, Source Sans o Arial); 10 pt para texto, 8 pt para notas |
| Colores | Azul oscuro `#1F3A5F` para títulos; gris `#5F6B7A` para notas |
| Semáforo | 🟢 `#2E7D32` · 🟡 `#F9A825` · 🔴 `#C62828` |
| Pie de página | Nombre de la empresa · fecha de corte · número de página "1 de 4" |

### Estructura

#### Página 1: Resumen

1. **Encabezado**
   - Título: *Análisis de Estados Financieros* / *Financial Statement Analysis*
   - Empresa, NIT, sector (código CIIU y descripción), fecha de corte, unidades
   - "Preparado por {nombre}" y fecha de elaboración. Pregunta al usuario
     cómo quiere firmar el informe; no uses su nombre sin confirmar.

2. **Conclusión general** (3 a 4 líneas)
   Un párrafo que responda: ¿cómo está la empresa frente a su sector y cuál es
   el tema más importante? Ejemplo:

   > La empresa muestra una rentabilidad superior a la de su sector, pero su
   > liquidez está en riesgo: los clientes pagan a 98 días, el doble que la
   > empresa típica del sector, y eso obliga a financiar la operación con
   > deuda de corto plazo.

3. **5 hallazgos principales**
   Elegidos según la sección 6 de `indicadores.md`. Cada uno con:
   - Símbolo y palabra del semáforo
   - Título corto (máximo 8 palabras)
   - Una o dos frases con el valor de la empresa, el valor del sector y la
     interpretación

4. **Tabla de semáforo** (todos los indicadores con semáforo, en una sola tabla)

   | Indicador | {año ant.} | {año} | Sector (P50) | Semáforo |
   |---|---|---|---|---|
   | Razón corriente | 1,62 | 1,45 | 1,38 | 🟢 Favorable |

   Si hay un solo periodo, omite la columna del año anterior.

#### Páginas 2 y 3: Análisis por grupo

Una sección por grupo, en este orden: **Liquidez, Endeudamiento,
Rentabilidad, Actividad**. Cada sección tiene:

- Un párrafo de 3 a 5 líneas que explique el grupo como un todo, usando las
  lecturas combinadas de `indicadores.md` cuando apliquen.
- Una gráfica (sección 4).
- Los indicadores sin semáforo (capital de trabajo neto, KTNO, días de
  proveedores) con su variación entre periodos.

Después, una sección **Estructura financiera** con el análisis vertical y
horizontal: solo las 3 a 5 partidas que más cambiaron o que más pesan. El
resto queda en el Excel.

#### Página final: Recomendaciones y metodología

1. **Recomendaciones** (3 a 5)
   - Concretas y accionables: "Revisar la política de crédito a clientes con
     plazos superiores a 60 días", no "mejorar la cartera".
   - Cada una ligada a un hallazgo.
   - Sin promesas de resultados ni cifras inventadas.

2. **Alertas**, si aplican. Patrimonio negativo o cobertura de intereses
   menor a 1 van aquí destacados, además de en los hallazgos.

3. **Metodología y fuentes** (en 8 pt)
   - Fuente de los datos sectoriales: Supersociedades, año, nivel CIIU usado y
     número de empresas.
   - Base de 360 días; saldos promedio o finales.
   - Todas las `advertencias` de `datos_homologados.json`.

4. **Aclaración final** (frase fija de `glosario-es-en.md`):
   *"Este documento es un análisis financiero y no constituye una opinión de
   auditoría ni un dictamen de revisoría fiscal."*

### Si el informe se pasa de 4 páginas

Recorta en este orden, sin eliminar nunca la página 1 ni la aclaración final:

1. Reduce el análisis vertical y horizontal a 3 partidas.
2. Quita la gráfica de Actividad.
3. Acorta los párrafos de cada grupo a 3 líneas.

---

## 3. Libro de Excel

### Hojas

| # | Hoja (ES) | Hoja (EN) | Contenido |
|---|---|---|---|
| 1 | `Resumen` | `Summary` | Datos de la empresa, conclusión general, 5 hallazgos y tabla de semáforo |
| 2 | `Datos` | `Data` | Estructura homologada (ESF y ERI) por periodo. **Única hoja con cifras digitadas** |
| 3 | `Vertical` | `Vertical` | Análisis vertical con fórmulas sobre `Datos` |
| 4 | `Horizontal` | `Horizontal` | Variación absoluta y relativa con fórmulas sobre `Datos` |
| 5 | `Indicadores` | `Ratios` | Los 19 indicadores con fórmulas sobre `Datos` |
| 6 | `Sector` | `Industry` | P25, P50 y P75 de cada indicador, nivel CIIU, año y número de empresas |
| 7 | `Gráficas` | `Charts` | Las gráficas de la sección 4 |
| 8 | `Notas` | `Notes` | Advertencias, metodología, fórmulas en texto y aclaración final |

### Reglas del libro

- **Fórmulas vivas**: todo lo que se calcula es fórmula de Excel, no un valor
  pegado. Si el usuario corrige una cifra en `Datos`, todo el libro se
  recalcula, incluido el semáforo.
- **Semáforo con fórmula**: en `Indicadores`, la columna de semáforo compara
  contra `Sector` según la dirección del indicador y devuelve el texto
  ("🟢 Favorable"). El color se aplica con formato condicional sobre ese texto.
- **`n.a.` con fórmula**: usa `SI.ERROR` / `IFERROR` y las reglas de
  `indicadores.md` para que nunca aparezca `#¡DIV/0!`.
- **Nombres definidos** para los campos de `Datos` (ej. `activo_corriente_2025`),
  para que las fórmulas se puedan leer: `=activo_corriente_2025/pasivo_corriente_2025`.
- **Celdas de entrada** (solo en `Datos`) con fondo amarillo claro `#FFF8E1`;
  el resto, protegido sin contraseña, para evitar cambios accidentales.
- **Formato numérico**: separadores según el idioma (ver `glosario-es-en.md`),
  negativos entre paréntesis, porcentajes con 1 decimal, veces con 2.
- **Columna de fórmula en texto** en `Indicadores`, para que el lector vea
  cómo se calculó cada valor sin tener que abrir la celda.
- Inmovilizar la primera fila y la primera columna en cada hoja de tablas.
- Ancho de columnas ajustado; nada de `#####` por columnas angostas.

### Hoja `Indicadores`: columnas

| Columna (ES) | Columna (EN) |
|---|---|
| Grupo | Group |
| Indicador | Ratio |
| Fórmula | Formula |
| {año ant.} | {prior year} |
| {año} | {year} |
| Variación | Change |
| Sector P25 | Industry P25 |
| Sector P50 | Industry P50 |
| Sector P75 | Industry P75 |
| Dirección | Direction |
| Semáforo | Rating |
| Interpretación | Interpretation |

---

## 4. Gráficas

Las mismas en el PDF y en el Excel. Máximo **una por grupo**, más la de
estructura financiera.

| Grupo | Gráfica | Detalle |
|---|---|---|
| Liquidez | Barras agrupadas: razón corriente y prueba ácida, empresa vs. sector (P50) | Línea punteada en 1,0 |
| Endeudamiento | Barras: nivel de endeudamiento y concentración a corto plazo, empresa vs. sector | Eje en % |
| Rentabilidad | Con 2+ periodos: líneas de margen bruto, operacional y neto por año. Con 1 periodo: barras empresa vs. sector | Eje en % |
| Actividad | Barras horizontales: días de cartera, inventario y proveedores, y ciclo de efectivo, empresa vs. sector | Eje en días |
| Estructura | Barras apiladas al 100%: composición del activo (corriente / no corriente) y del financiamiento (pasivo corriente / no corriente / patrimonio) | Una barra por periodo |

Reglas:

- **Empresa** en azul oscuro `#1F3A5F`; **sector** en gris `#A0AAB4`. Nunca uses
  los colores del semáforo en las gráficas.
- Título que diga la conclusión, no solo el tema: *"La cartera tarda el doble
  que en el sector"*, no *"Rotación de cartera"*.
- Etiquetas de datos en cada barra; sin cuadrícula de fondo.
- Fuente al pie: "Fuente: estados financieros de la empresa y Supersociedades ({año})".
- Si un indicador es `n.a.`, no lo dibujes en la gráfica y menciónalo en la nota.

---

## 5. Resumen en el chat

Después de generar los archivos, en el chat (en el idioma del usuario):

1. Conclusión general en una o dos frases.
2. Los 5 hallazgos, en una tabla corta: semáforo, indicador, empresa, sector.
3. Alertas, si hay.
4. Enlaces a los 4 archivos.
5. Las advertencias más importantes de la homologación (máximo 3), para que
   el contador sepa qué revisar antes de entregar el informe al cliente.
