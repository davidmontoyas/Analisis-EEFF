# Homologación de cuentas a la estructura estándar

Este archivo explica cómo llevar cualquier insumo (balance de prueba PUC o
estados financieros NIIF ya presentados) a una **estructura estándar única**.
Los indicadores (`indicadores.md`) y los scripts solo leen esa estructura.

Hay dos caminos, según lo que entregue el usuario:

- **Camino A**: balance de prueba por cuentas PUC (sección 3).
- **Camino B**: ESF y ERI ya presentados bajo NIIF, con nombres de rubro libres (sección 4).

En ambos casos el resultado es `datos_homologados.json` (sección 5).

---

## 1. Estructura estándar

### Estado de Situación Financiera (ESF)

| Campo | Nombre (ES) | Name (EN) | Obligatorio |
|---|---|---|---|
| `efectivo` | Efectivo y equivalentes al efectivo | Cash and cash equivalents | Sí |
| `inversiones_cp` | Inversiones de corto plazo | Short-term investments | No |
| `deudores_comerciales` | Deudores comerciales (neto de deterioro) | Trade receivables, net | Sí |
| `otras_cuentas_por_cobrar_cp` | Otras cuentas por cobrar corrientes | Other current receivables | No |
| `activos_por_impuestos_cp` | Activos por impuestos corrientes | Current tax assets | No |
| `inventarios` | Inventarios (neto de deterioro) | Inventories, net | Sí* |
| `otros_activos_cp` | Otros activos corrientes | Other current assets | No |
| **`activo_corriente`** | **Total activo corriente** | **Total current assets** | **Sí** |
| `ppe` | Propiedades, planta y equipo (neto) | Property, plant and equipment, net | No |
| `intangibles` | Intangibles (neto) | Intangible assets, net | No |
| `inversiones_lp` | Inversiones de largo plazo | Long-term investments | No |
| `otros_activos_lp` | Otros activos no corrientes | Other non-current assets | No |
| **`activo_no_corriente`** | **Total activo no corriente** | **Total non-current assets** | **Sí** |
| **`activo_total`** | **Total activo** | **Total assets** | **Sí** |
| `obligaciones_financieras_cp` | Obligaciones financieras corrientes | Current borrowings | Sí* |
| `proveedores` | Proveedores | Trade payables | Sí* |
| `otras_cuentas_por_pagar_cp` | Otras cuentas por pagar | Other payables | No |
| `pasivos_por_impuestos_cp` | Pasivos por impuestos corrientes | Current tax liabilities | No |
| `obligaciones_laborales` | Beneficios a empleados | Employee benefits | No |
| `otros_pasivos_cp` | Otros pasivos corrientes | Other current liabilities | No |
| **`pasivo_corriente`** | **Total pasivo corriente** | **Total current liabilities** | **Sí** |
| `obligaciones_financieras_lp` | Obligaciones financieras no corrientes | Non-current borrowings | Sí* |
| `otros_pasivos_lp` | Otros pasivos no corrientes | Other non-current liabilities | No |
| **`pasivo_no_corriente`** | **Total pasivo no corriente** | **Total non-current liabilities** | **Sí** |
| **`pasivo_total`** | **Total pasivo** | **Total liabilities** | **Sí** |
| `capital` | Capital social | Share capital | No |
| `reservas` | Reservas | Reserves | No |
| `resultado_ejercicio` | Resultado del ejercicio | Profit (loss) for the year | Sí |
| `resultados_acumulados` | Resultados de ejercicios anteriores | Retained earnings | No |
| `otro_patrimonio` | Otras partidas del patrimonio | Other equity | No |
| **`patrimonio`** | **Total patrimonio** | **Total equity** | **Sí** |

### Estado de Resultados Integral (ERI)

| Campo | Nombre (ES) | Name (EN) | Obligatorio |
|---|---|---|---|
| **`ingresos_operacionales`** | **Ingresos de actividades ordinarias (netos)** | **Revenue** | **Sí** |
| `costo_ventas` | Costo de ventas | Cost of sales | Sí* |
| **`utilidad_bruta`** | **Utilidad bruta** | **Gross profit** | **Sí** |
| `gastos_administracion` | Gastos de administración | Administrative expenses | Sí |
| `gastos_ventas` | Gastos de ventas | Selling expenses | Sí |
| **`utilidad_operacional`** | **Utilidad operacional** | **Operating profit** | **Sí** |
| `otros_ingresos` | Otros ingresos | Other income | No |
| `ingresos_financieros` | Ingresos financieros | Finance income | No |
| `gastos_financieros` | Gastos financieros: **solo intereses** | Finance costs (interest) | Sí* |
| `otros_gastos_financieros` | Comisiones, gastos bancarios, GMF, diferencia en cambio | Other finance costs | No |
| `otros_gastos` | Otros gastos | Other expenses | No |
| **`utilidad_antes_impuestos`** | **Utilidad antes de impuestos** | **Profit before tax** | **Sí** |
| `impuesto_renta` | Gasto por impuesto de renta | Income tax expense | Sí |
| **`utilidad_neta`** | **Utilidad neta** | **Profit for the year** | **Sí** |

\* Obligatorio si existe en la empresa. Si es cero, regístralo como `0` y
confirma con el usuario que es real (empresa de servicios sin inventario,
empresa sin deuda financiera, etc.). Si no hay dato, regístralo como `null`.

### Reglas de signo

- **Todos los valores van en positivo** según su naturaleza: un gasto de
  $100 se registra como `100`, no como `-100`.
- Las únicas partidas que pueden ser negativas son los **resultados**
  (`utilidad_*`, `resultado_ejercicio`, `resultados_acumulados`) y el `patrimonio`.
- Las cuentas **correctoras** (deterioro, depreciación y amortización
  acumuladas, devoluciones en ventas) restan de su cuenta principal; nunca
  aparecen como un campo propio.

### Cuadres que deben cumplirse

```
activo_total            = activo_corriente + activo_no_corriente
pasivo_total            = pasivo_corriente + pasivo_no_corriente
activo_total            = pasivo_total + patrimonio                  (tolerancia 0,5%)
utilidad_bruta          = ingresos_operacionales - costo_ventas
utilidad_operacional    = utilidad_bruta - gastos_administracion - gastos_ventas
utilidad_antes_impuestos = utilidad_operacional + otros_ingresos + ingresos_financieros
                           - gastos_financieros - otros_gastos_financieros - otros_gastos
utilidad_neta           = utilidad_antes_impuestos - impuesto_renta
utilidad_neta           = resultado_ejercicio                         (tolerancia 0,5%)
```

Si un subtotal reportado por el cliente no coincide con la suma de sus
partes, **usa la suma de las partes** y anota la diferencia para el usuario.

---

## 2. Antes de empezar: qué preguntar

Pregunta en un solo mensaje, si no está claro en el insumo:

1. **Unidades** (pesos, miles, millones).
2. **Fecha de corte** y si el periodo es anual. Si es un corte intermedio
   (ej. junio), las rotaciones en días deben anualizar los ingresos y costos:
   adviértelo y ajusta `dias_periodo` en el JSON.
3. Solo Camino A: **porción de largo plazo** de las obligaciones financieras
   (cuenta 21) y de otras cuentas que el PUC no separa (sección 3.3).

---

## 3. Camino A: balance de prueba PUC

El PUC de referencia es el del Decreto 2650 de 1993. Aunque las empresas
reportan bajo NIIF, la mayoría sigue usando su catálogo como plan de cuentas,
con subcuentas propias. Trabaja con **cuentas de 4 dígitos** y baja a 6
dígitos solo donde esta tabla lo indica.

### 3.1 Preparar el balance de prueba

1. Usa el **saldo final** de cada cuenta, no los movimientos.
2. Usa un solo nivel: si el archivo trae grupos, cuentas y subcuentas, toma
   el nivel de 4 dígitos para no sumar dos veces.
3. Normaliza los signos según la naturaleza: clases 1, 5, 6 y 7 son débito;
   clases 2, 3 y 4 son crédito. Muchos programas exportan los créditos con
   signo negativo: conviértelos a positivo.
4. **Cierre del ejercicio**: si las clases 4, 5 y 6 ya están en cero porque
   el periodo fue cerrado, pide el balance de prueba **antes del cierre** o el
   ERI por separado. Sin eso no se puede construir el ERI.

### 3.2 Activo (clase 1)

| Cuentas PUC | Campo | Notas |
|---|---|---|
| 11 | `efectivo` | Caja, bancos, cuentas de ahorro, fondos |
| 1225 (CDT), 1295 | `inversiones_cp` | Inversiones temporales |
| 1205, 1210, 1215, 1220, 1230–1290 | `inversiones_lp` | Acciones, cuotas, bonos de largo plazo. Si el usuario indica que son temporales, pásalas a `inversiones_cp` |
| 1305, 1310 − 139905 | `deudores_comerciales` | Clientes y cuentas corrientes comerciales, neto del deterioro de clientes |
| 1315, 1320, 1325, 1330, 1345, 1365, 1370, 1380 − resto de 1399 | `otras_cuentas_por_cobrar_cp` | Vinculados, socios, anticipos, trabajadores, préstamos, deudores varios. **No** entran al KTNO |
| 1355 | `activos_por_impuestos_cp` | Anticipos y saldos a favor de impuestos |
| 1335, 1340, 1350, 1360, 1385 | `otras_cuentas_por_cobrar_cp` | Depósitos, promesas, retenciones, reclamaciones |
| 1390 | `otros_activos_lp` | Deudas de difícil cobro (neto de su deterioro) |
| 14 − 1499 | `inventarios` | Neto de deterioro |
| 1705 | `otros_activos_cp` | Gastos pagados por anticipado |
| 15 − 1592 − 1597 | `ppe` | Neto de depreciación y deterioro |
| 16 − 1698 | `intangibles` | Neto de amortización |
| 1710–1798 (excepto 1705) | `otros_activos_lp` | Cargos diferidos, impuesto diferido activo |
| 18 | `otros_activos_lp` | Otros activos |
| 19 | **No se incluye** | Valorizaciones: no existen bajo NIIF (ver 3.6) |

### 3.3 Pasivo (clase 2)

| Cuentas PUC | Campo | Notas |
|---|---|---|
| 21 | `obligaciones_financieras_cp` / `obligaciones_financieras_lp` | **Pregunta la porción de largo plazo.** Si el usuario no la sabe, déjala toda como corriente y adviértelo en el informe (subestima la liquidez) |
| 22 | `proveedores` | Proveedores nacionales y del exterior |
| 2305–2360, 2380–2395 | `otras_cuentas_por_pagar_cp` | Vinculados, costos y gastos por pagar, dividendos, acreedores varios |
| 2365, 2367, 2368, 2370 | `pasivos_por_impuestos_cp` | Retenciones y aportes de nómina por pagar |
| 24 | `pasivos_por_impuestos_cp` | Renta, IVA, ICA, otros impuestos |
| 25 | `obligaciones_laborales` | Salarios, cesantías, intereses, primas, vacaciones |
| 26 | `otros_pasivos_cp` | Pasivos estimados y provisiones. Si el usuario indica que son de largo plazo (ej. litigios), pásalos a `otros_pasivos_lp` |
| 2705, 2710, 2715 | `otros_pasivos_cp` | Ingresos recibidos por anticipado |
| 2725 y resto de 27 | `otros_pasivos_lp` | Impuesto diferido pasivo y otros diferidos |
| 2805, 2810, 2815 | `otros_pasivos_cp` | Anticipos de clientes, depósitos, ingresos para terceros |
| Resto de 28 | `otros_pasivos_cp` | |
| 29 | `obligaciones_financieras_lp` | Bonos y papeles comerciales (separa la porción corriente si se conoce) |

### 3.4 Patrimonio (clase 3)

| Cuentas PUC | Campo |
|---|---|
| 31, 32 | `capital` (capital social y superávit de capital) |
| 33 | `reservas` |
| 3605 − 3610 | `resultado_ejercicio` (utilidad menos pérdida) |
| 3705 − 3710 | `resultados_acumulados` |
| 34, 35, 38 y otras | `otro_patrimonio` (incluye ajustes por adopción NIIF por primera vez) |

### 3.5 Ingresos, gastos y costos (clases 4, 5, 6 y 7)

| Cuentas PUC | Campo | Notas |
|---|---|---|
| 41 − 4175 | `ingresos_operacionales` | Neto de devoluciones, rebajas y descuentos |
| 6105–6199 | `costo_ventas` | Costo de ventas y de prestación de servicios |
| 51 | `gastos_administracion` | |
| 52 | `gastos_ventas` | |
| 4210 | `ingresos_financieros` | Intereses, diferencia en cambio y descuentos financieros recibidos |
| Resto de 42 | `otros_ingresos` | Arrendamientos, utilidad en venta de activos, recuperaciones, indemnizaciones, etc. |
| 530520 | `gastos_financieros` | **Solo intereses**, incluidos los de leasing financiero |
| Resto de 5305 | `otros_gastos_financieros` | Gastos bancarios, comisiones, diferencia en cambio |
| 5310–5395 | `otros_gastos` | Pérdida en venta de activos, gastos extraordinarios, diversos |
| 54 | `impuesto_renta` | Impuesto de renta y complementarios (corriente y diferido) |

Casos especiales:

- **GMF (4×1000)**: según la empresa puede estar en 5115, 5305 u otra
  cuenta. Si está discriminado, déjalo fuera de `gastos_financieros`
  (llévalo a `otros_gastos_financieros` o déjalo en el gasto donde esté).
- **Clase 7 (costos de producción)**: normalmente se traslada a inventario y
  luego a la 61. Si la clase 7 tiene saldo y la 61 está vacía, pregunta cómo
  maneja la empresa el costeo antes de usar la clase 7 como costo de ventas.
  **Nunca sumes 61 y 7**: es doble conteo.
- **Clase 62 (compras)**: en sistema de inventario periódico, el costo de
  ventas es `inventario inicial + compras (62) − inventario final`. Calcúlalo
  así si la 61 está vacía y la 62 tiene saldo, y explícalo al usuario.
- **Subcuentas de 6 dígitos**: si el balance no trae 530520 por separado, usa
  la cuenta 5305 completa como `gastos_financieros` y adviértelo, porque la
  cobertura de intereses quedará subestimada.

### 3.6 Cuentas que no existen bajo NIIF

Las cuentas **19 (valorizaciones), 38 (superávit por valorizaciones),
34 (revalorización del patrimonio) y 47 (ajustes por inflación)** vienen de la
norma anterior al marco NIIF. Si alguna tiene saldo:

1. No incluyas 19 en el activo ni 38 en el patrimonio.
2. Recalcula los totales y verifica que la ecuación contable siga cuadrando.
3. Avísale al usuario: puede ser un saldo que quedó sin depurar en la
   adopción por primera vez, y vale la pena revisarlo.

La 34 sí se conserva en `otro_patrimonio` si tiene saldo, porque muchas
empresas la mantuvieron en el patrimonio al adoptar NIIF.

---

## 4. Camino B: estados financieros NIIF presentados

Cuando el usuario entrega el ESF y el ERI ya armados, identifica cada rubro
por su nombre. Estas son las equivalencias más comunes:

| Rubro en los estados financieros (o similar) | Campo |
|---|---|
| Efectivo y equivalentes al efectivo · Disponible | `efectivo` |
| Inversiones · Activos financieros corrientes | `inversiones_cp` |
| Deudores comerciales y otras cuentas por cobrar · Cuentas comerciales por cobrar · Clientes | `deudores_comerciales` (ver nota 1) |
| Activos por impuestos corrientes · Anticipo de impuestos | `activos_por_impuestos_cp` |
| Inventarios · Existencias | `inventarios` |
| Gastos pagados por anticipado · Otros activos no financieros | `otros_activos_cp` |
| Propiedades, planta y equipo · Activos por derecho de uso | `ppe` |
| Propiedades de inversión · Inversiones en subsidiarias o asociadas | `inversiones_lp` |
| Activos intangibles · Plusvalía | `intangibles` |
| Activo por impuesto diferido | `otros_activos_lp` |
| Obligaciones financieras · Préstamos · Pasivos por arrendamiento | `obligaciones_financieras_cp` / `_lp` según la sección |
| Acreedores comerciales y otras cuentas por pagar · Proveedores | `proveedores` (ver nota 1) |
| Pasivos por impuestos corrientes · Impuestos por pagar | `pasivos_por_impuestos_cp` |
| Beneficios a empleados · Obligaciones laborales | `obligaciones_laborales` |
| Provisiones · Pasivos estimados | `otros_pasivos_cp` / `otros_pasivos_lp` según la sección |
| Pasivo por impuesto diferido | `otros_pasivos_lp` |
| Ingresos de actividades ordinarias · Ingresos operacionales · Ventas | `ingresos_operacionales` |
| Costo de ventas · Costo de la prestación del servicio | `costo_ventas` |
| Gastos de administración | `gastos_administracion` |
| Gastos de ventas · Gastos de distribución | `gastos_ventas` |
| Otros ingresos | `otros_ingresos` |
| Ingresos financieros | `ingresos_financieros` |
| Costos financieros · Gastos financieros | `gastos_financieros` (ver nota 2) |
| Otros gastos | `otros_gastos` |
| Gasto por impuesto a las ganancias · Impuesto de renta | `impuesto_renta` |
| Resultado del periodo · Utilidad (pérdida) neta | `utilidad_neta` |

Si los estados vienen en inglés, usa las equivalencias de la columna
*Name (EN)* de la sección 1.

**Nota 1: rubros que mezclan lo comercial con lo no comercial.** Bajo NIIF es
común presentar "Deudores comerciales **y otras** cuentas por cobrar" en una
sola línea, y lo mismo con las cuentas por pagar. Si las **notas** a los
estados financieros traen el detalle, separa la parte comercial (clientes,
proveedores) y lleva el resto a `otras_cuentas_por_cobrar_cp` u
`otras_cuentas_por_pagar_cp`. Si no hay detalle, usa el rubro completo y
adviértelo, porque el KTNO y los días de cartera y proveedores quedarán
sobreestimados.

**Nota 2: costos financieros.** Bajo NIIF suelen incluir intereses,
comisiones y diferencia en cambio. Si las notas traen el detalle, deja solo
los intereses en `gastos_financieros` y el resto en `otros_gastos_financieros`.
Si no, usa el total y adviértelo.

**Nota 3: rubros que no reconozcas.** No los fuerces a un campo. Llévalos a
`otros_activos_*`, `otros_pasivos_*`, `otro_patrimonio`, `otros_ingresos` u
`otros_gastos` según corresponda, y muéstrale al usuario la lista de lo que
clasificaste así para que lo confirme.

---

## 5. Formato de salida: `datos_homologados.json`

Un objeto por periodo, ordenados del más antiguo al más reciente:

```json
{
  "empresa": "Comercializadora Ejemplo S.A.S.",
  "nit": "900123456-7",
  "ciiu": "4711",
  "marco": "NIIF Pymes",
  "unidades": "miles",
  "moneda": "COP",
  "camino": "A",
  "periodos": [
    {
      "fecha_corte": "2024-12-31",
      "dias_periodo": 360,
      "esf": {
        "efectivo": 120500,
        "deudores_comerciales": 340200,
        "inventarios": 410000,
        "activo_corriente": 905300,
        "activo_total": 1650000,
        "obligaciones_financieras_cp": 150000,
        "proveedores": 280000,
        "pasivo_corriente": 560000,
        "obligaciones_financieras_lp": 300000,
        "pasivo_total": 920000,
        "resultado_ejercicio": 95000,
        "patrimonio": 730000
      },
      "eri": {
        "ingresos_operacionales": 2800000,
        "costo_ventas": 2016000,
        "utilidad_bruta": 784000,
        "gastos_administracion": 310000,
        "gastos_ventas": 290000,
        "utilidad_operacional": 184000,
        "gastos_financieros": 42000,
        "utilidad_antes_impuestos": 142000,
        "impuesto_renta": 47000,
        "utilidad_neta": 95000
      }
    }
  ],
  "advertencias": [
    "La cuenta 21 no discrimina el largo plazo; el usuario indicó $300.000 de porción no corriente.",
    "La cuenta 19 tenía saldo de $45.000 y se excluyó del activo."
  ]
}
```

- Incluye **todos** los campos de la sección 1; el ejemplo muestra solo una
  parte para que sea legible. Los que no apliquen van en `0` o `null` según
  la regla de la sección 1.
- `advertencias` recoge todo lo que el informe debe mencionar: supuestos,
  rubros sin detalle, cuentas excluidas, diferencias de cuadre.
- Datos ficticios en el ejemplo. Nunca guardes este archivo con datos reales
  dentro del repositorio.
