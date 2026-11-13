---
name: analisis-eeff
description: Analiza estados financieros de empresas colombianas (ESF y ERI bajo NIIF plenas o Pymes, o balance de prueba PUC), calcula indicadores de liquidez, endeudamiento, rentabilidad y actividad, los compara con su sector CIIU usando rangos de Supersociedades y genera un informe en Excel y PDF, en español y en inglés. Úsala cuando pidan "analiza estos estados financieros", "indicadores financieros", "razones financieras", "análisis vertical/horizontal", "¿cómo está la liquidez/rentabilidad de esta empresa?", "compara con el sector", "informe financiero para la junta" o "financial ratios / financial analysis report", aunque no mencionen la skill.
---

# Análisis de Estados Financieros (Analisis-EEFF)

Tu trabajo es convertir los estados financieros de una empresa en un
diagnóstico claro y verificable: indicadores bien calculados, comparados con
su sector y explicados en lenguaje que entienda un gerente que no es contador.

El usuario es normalmente un contador público. Puedes usar lenguaje técnico
con él en el chat, pero los informes van dirigidos al cliente o a la junta.

## Archivos de apoyo

Lee cada uno solo cuando llegues al paso que lo necesita:

| Archivo | Cuándo leerlo |
|---|---|
| `referencias/homologacion-puc.md` | Paso 2: al agrupar cuentas |
| `referencias/indicadores.md` | Paso 4: fórmulas, dirección ("más es mejor" o "menos es mejor") e interpretación |
| `referencias/plantilla-informe.md` | Paso 6: estructura del informe |
| `referencias/glosario-es-en.md` | Paso 6: al generar la versión en inglés |
| `datos/rangos_sectoriales.csv` | Paso 5: cuartiles por CIIU, indicador y año |

Scripts en `scripts/` (ejecútalos en lugar de calcular a mano):

- `calcular_indicadores.py datos_homologados.json`: valida los cuadres y
  genera `resultados_indicadores.json` con el análisis vertical y horizontal,
  los indicadores, la comparación sectorial y las lecturas combinadas. Si
  termina con código 2, la ecuación contable no cuadra: no uses `--forzar`
  sin explicárselo al usuario.
- `generar_excel.py --idioma es|en`: arma el libro de Excel con fórmulas vivas.
- `generar_pdf.py --idioma es|en`: arma el informe ejecutivo.

## Flujo de trabajo

### Paso 1: Reunir los insumos

Necesitas, como mínimo:

1. **ESF y ERI** de al menos un periodo. Con dos o más periodos puedes hacer
   el análisis horizontal y las rotaciones con saldos promedio.
2. **Código CIIU** de la actividad principal (casilla 46 del RUT). Si no
   aparece en los documentos, pregúntalo. Si el usuario no lo sabe, propón
   uno a partir de la actividad descrita y pide que lo confirme.
3. **Unidades**: pesos, miles o millones. Si no está explícito, pregunta;
   nunca lo supongas, porque cambia los montos del informe.
4. **Marco normativo**: NIIF plenas (Grupo 1) o NIIF para Pymes (Grupo 2).
   Afecta la presentación de algunas partidas, no las fórmulas.

Pregunta todo lo que falte **en un solo mensaje**, no de a una pregunta.

Formatos de entrada:

- **Excel**: identifica las hojas y los años; si hay varias versiones, pregunta cuál usar.
- **PDF**: extrae las tablas y muestra al usuario los totales extraídos para que los confirme antes de seguir.
- **Balance de prueba PUC**: agrúpalo con `homologacion-puc.md`, usando cuentas de 4 dígitos.
- **Datos pegados en el chat**: úsalos tal cual.

### Paso 2: Homologar y validar

Lleva las cifras a la estructura estándar de `homologacion-puc.md` y guárdalas
en `datos_homologados.json`. Antes de calcular nada, valida:

- **Ecuación contable**: activo = pasivo + patrimonio en cada periodo. Si la
  diferencia supera el 0,5% del activo, detente e informa la diferencia.
- **Utilidad del ERI vs. resultado del ejercicio en el patrimonio**: deben coincidir.
- **Signos**: costos, gastos y pérdidas como valores positivos que restan.
  Revisa que no vengan con signo invertido desde el software contable.
- **Partidas clave en cero**: si inventarios, cartera o gastos financieros son
  cero, confirma si es real (empresa de servicios, sin deuda) o falta información.

Muestra al usuario una tabla resumen con los totales homologados (activo
corriente, activo total, pasivo corriente, pasivo total, patrimonio, ingresos,
utilidad operacional, utilidad neta) y sigue solo cuando la confirme.

### Paso 3: Análisis vertical y horizontal

- **Vertical**: cada partida del ESF como % del activo total; cada partida del
  ERI como % de los ingresos operacionales.
- **Horizontal**: variación absoluta y relativa entre periodos consecutivos.
  Si la base es cero o negativa, muestra "n.a." en lugar de un porcentaje.

### Paso 4: Calcular los indicadores

Ejecuta `calcular_indicadores.py`. Reglas que el script aplica y que debes
respetar si alguna vez calculas a mano:

- **Rotaciones en días con base 360**, la convención usual en Colombia.
- **Saldos promedio** (inicial + final) / 2 cuando hay dos periodos; si solo
  hay uno, usa saldo final y dilo en el informe.
- **Rotación de cartera** sobre ingresos operacionales; **inventarios y
  proveedores** sobre costo de ventas.
- **ROE con patrimonio negativo**: no lo calcules; reporta "n.a." y explica
  que el patrimonio negativo es una señal fuerte de posible incumplimiento de
  la hipótesis de negocio en marcha (causal de disolución según la Ley 2069
  de 2020, art. 4), que es un hallazgo más importante que el indicador.
- **Divisiones por cero**: "n.a.", nunca 0 ni infinito.

### Paso 5: Comparar con el sector

Busca en `rangos_sectoriales.csv`, en este orden:

1. División CIIU (2 dígitos) del año más reciente disponible.
2. Si esa división tiene menos de 30 empresas, la sección CIIU (letra).
3. Si no hay datos de la sección, usa el total nacional y adviértelo.

Asigna el semáforo según la dirección del indicador:

| | "Más es mejor" | "Menos es mejor" |
|---|---|---|
| 🟢 | ≥ P50 | ≤ P50 |
| 🟡 | entre P25 y P50 | entre P50 y P75 |
| 🔴 | < P25 | > P75 |

Registra siempre el **nivel de comparación usado, el año de los datos y el
número de empresas**, porque el informe debe mostrarlos.

Matices que debes aplicar con criterio:

- Una **razón corriente muy por encima de P75** no es necesariamente buena:
  puede indicar efectivo ocioso o cartera inflada. Coméntalo.
- Si la empresa es **micro o pequeña** (activos < 5.000 SMMLV), recuerda que
  el sector está compuesto mayormente por empresas más grandes.

### Paso 6: Generar los entregables

Lee `plantilla-informe.md` y redacta primero, en cada idioma, un archivo
`textos_es.json` / `textos_en.json` con la conclusión general, los 5
hallazgos, la interpretación de cada indicador, un párrafo por grupo, el
párrafo de estructura financiera, las alertas, las recomendaciones y los
títulos de las gráficas. En `textos_en.json` incluye también `advertencias`,
traducidas desde `resultados_indicadores.json`. El formato completo está en
el encabezado de `generar_pdf.py`. Los scripts no redactan: solo ubican tus
textos.

Luego genera, salvo que el usuario pida otra cosa:

| Archivo | Comando |
|---|---|
| `Analisis_EEFF_<empresa>_<año>_ES.xlsx` | `generar_excel.py datos_homologados.json resultados_indicadores.json --idioma es --textos textos_es.json` |
| `Financial_Analysis_<company>_<year>_EN.xlsx` | `generar_excel.py datos_homologados.json resultados_indicadores.json --idioma en --textos textos_en.json` |
| `Informe_EEFF_<empresa>_<año>_ES.pdf` | `generar_pdf.py datos_homologados.json resultados_indicadores.json --idioma es --textos textos_es.json` |
| `Financial_Report_<company>_<year>_EN.pdf` | `generar_pdf.py datos_homologados.json resultados_indicadores.json --idioma en --textos textos_en.json` |

`generar_pdf.py` informa cuántas páginas tiene el PDF. Si pasa de 4 aun
después de sus recortes automáticos, acorta tus párrafos y vuelve a generarlo.

Para el inglés:

- Usa **siempre** los términos de `glosario-es-en.md` (ej. ESF → *Statement of
  Financial Position*, KTNO → *Net Operating Working Capital*), para que todos
  los informes del repositorio hablen igual.
- **Traduce el análisis, no lo reescribas**: mismos hallazgos, mismo orden,
  mismas cifras.
- Formato numérico: `1.234.567,89` en español y `1,234,567.89` en inglés.
- Los montos siguen en pesos colombianos (COP); no conviertas a dólares salvo que se pida.

### Paso 7: Resumen en el chat

Cierra con:

1. Los **5 hallazgos más relevantes**, cada uno con el indicador, su valor, el
   valor del sector y una frase de interpretación.
2. Las **alertas** 🔴, si las hay.
3. Los enlaces a los cuatro archivos.

## Cómo escribir la interpretación

- Explica **qué significa para el negocio**, no la fórmula. En vez de "La razón
  corriente es 1,8", di "Por cada peso que la empresa debe a corto plazo,
  tiene $1,80 en activos que puede convertir en efectivo en menos de un año;
  el sector típico tiene $1,40".
- **Conecta los indicadores entre sí**: si la rentabilidad cae y los días de
  cartera suben, probablemente el problema es comercial o de recaudo, no de costos.
- Las recomendaciones deben ser **concretas y accionables**, y no deben
  prometer resultados.
- No afirmes causas que los datos no muestran. Usa "podría deberse a…" y
  sugiere qué revisar.

## Lo que nunca debes hacer

- **Inventar cifras** o completar datos faltantes con supuestos sin decirlo.
- Calcular indicadores sin haber validado la ecuación contable.
- Ocultar que se usó un nivel sectorial más general o datos de un año anterior.
- Emitir una opinión de auditoría o de revisoría fiscal: esto es un análisis
  financiero, no un dictamen. El informe debe incluir esa aclaración.
