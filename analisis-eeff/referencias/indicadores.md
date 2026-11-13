# Indicadores financieros: fórmulas, dirección e interpretación

Este archivo es la **fuente única** de las fórmulas. `calcular_indicadores.py`,
el CSV de rangos sectoriales y los informes usan los mismos `id` que aparecen
aquí. Si cambias una fórmula, cámbiala aquí y en el script al mismo tiempo, y
recalcula los rangos.

## Convenciones generales

- **Campos**: las fórmulas usan los nombres de la estructura homologada
  (`homologacion-puc.md`), en `formato_snake_case`.
- **Promedio**: `prom(x) = (x del periodo anterior + x del periodo actual) / 2`.
  Si solo hay un periodo, usa el saldo final y marca el indicador con
  `base_saldo_final = true` para que el informe lo advierta.
- **Días**: base **360**.
- **Resultado no calculable**: `n.a.` (división por cero, denominador
  negativo donde no tiene sentido, o dato faltante). Nunca 0 ni infinito.
- **Dirección**: `más` = un valor más alto es mejor; `menos` = un valor más
  bajo es mejor; `ninguna` = no lleva semáforo sectorial.
- **Formato**: `veces` con 2 decimales; `%` con 1 decimal; `días` sin
  decimales; `COP` sin decimales, en las unidades del insumo.

## Resumen (tabla de control)

| id | Nombre (ES) | Name (EN) | Unidad | Dirección | Grupo |
|---|---|---|---|---|---|
| `razon_corriente` | Razón corriente | Current ratio | veces | más | Liquidez |
| `prueba_acida` | Prueba ácida | Quick ratio | veces | más | Liquidez |
| `capital_trabajo_neto` | Capital de trabajo neto | Net working capital | COP | ninguna | Liquidez |
| `ktno` | Capital de trabajo neto operativo (KTNO) | Net operating working capital | COP | ninguna | Liquidez |
| `nivel_endeudamiento` | Nivel de endeudamiento | Debt ratio | % | menos | Endeudamiento |
| `concentracion_cp` | Concentración de la deuda a corto plazo | Short-term debt concentration | % | menos | Endeudamiento |
| `apalancamiento_total` | Apalancamiento total | Total leverage | veces | menos | Endeudamiento |
| `apalancamiento_financiero` | Apalancamiento financiero | Financial leverage | veces | menos | Endeudamiento |
| `cobertura_intereses` | Cobertura de intereses | Interest coverage | veces | más | Endeudamiento |
| `margen_bruto` | Margen bruto | Gross margin | % | más | Rentabilidad |
| `margen_operacional` | Margen operacional | Operating margin | % | más | Rentabilidad |
| `margen_neto` | Margen neto | Net margin | % | más | Rentabilidad |
| `roa` | Rentabilidad del activo (ROA) | Return on assets (ROA) | % | más | Rentabilidad |
| `roe` | Rentabilidad del patrimonio (ROE) | Return on equity (ROE) | % | más | Rentabilidad |
| `dias_cartera` | Rotación de cartera | Days sales outstanding | días | menos | Actividad |
| `dias_inventario` | Rotación de inventarios | Days inventory outstanding | días | menos | Actividad |
| `dias_proveedores` | Rotación de proveedores | Days payables outstanding | días | ninguna | Actividad |
| `ciclo_efectivo` | Ciclo de conversión de efectivo | Cash conversion cycle | días | menos | Actividad |
| `rotacion_activos` | Rotación de activos | Asset turnover | veces | más | Actividad |

---

## 1. Liquidez

Responde: **¿puede la empresa pagar lo que debe en el corto plazo?**

### `razon_corriente`: Razón corriente

```
activo_corriente / pasivo_corriente
```

- **Interpretación**: por cada peso de deuda de corto plazo, cuántos pesos
  de activos corrientes tiene la empresa.
- **Plantilla**: "Por cada $1 que la empresa debe a menos de un año, tiene
  ${valor} en activos que puede convertir en efectivo en ese plazo; la empresa
  típica del sector tiene ${p50}."
- **Matices**:
  - Menor a 1: el activo corriente no alcanza para cubrir el pasivo
    corriente. Revisa el ciclo de efectivo antes de concluir que hay crisis:
    algunos negocios (comercio con caja diaria) operan bien así.
  - Muy por encima de P75: puede ser efectivo ocioso, cartera difícil de
    cobrar o inventario lento. Contrástalo con `dias_cartera` y `dias_inventario`.
- `n.a.` si `pasivo_corriente = 0`.

### `prueba_acida`: Prueba ácida

```
(activo_corriente - inventarios) / pasivo_corriente
```

- **Interpretación**: la capacidad de pago de corto plazo **sin depender de
  vender el inventario**.
- **Plantilla**: "Sin contar el inventario, la empresa tiene ${valor} por cada
  $1 de deuda de corto plazo (sector: ${p50})."
- **Matices**: si es muy inferior a la razón corriente, la liquidez depende
  del inventario; revisa `dias_inventario`. En empresas de servicios sin
  inventario, es igual a la razón corriente: dilo y no lo repitas como hallazgo.
- `n.a.` si `pasivo_corriente = 0`.

### `capital_trabajo_neto`: Capital de trabajo neto

```
activo_corriente - pasivo_corriente
```

- **Interpretación**: el excedente (o faltante) de recursos de corto plazo
  después de cubrir las deudas de corto plazo.
- **Sin semáforo sectorial**: es un valor absoluto, no se puede comparar entre
  empresas de distinto tamaño. Se analiza su variación entre periodos.
- **Plantilla**: "Después de cubrir sus deudas de corto plazo, a la empresa le
  quedan ${valor} en recursos corrientes ({variación} frente a {año anterior})."
- Si es negativo, dilo claramente: "a la empresa le faltan ${valor}…".

### `ktno`: Capital de trabajo neto operativo

```
deudores_comerciales + inventarios - proveedores
```

- **Interpretación**: los recursos que la operación tiene "atrapados" en
  cartera e inventario y que no financian los proveedores. Es la plata que la
  empresa necesita para operar.
- **Sin semáforo sectorial** (valor absoluto). Se analiza su variación frente
  a la variación de los ingresos:
  - Si el KTNO crece **más rápido** que los ingresos, la operación consume
    cada vez más caja por cada peso vendido. Es una alerta.
  - Si crece **más despacio**, la empresa está siendo más eficiente con su
    capital de trabajo.
- Solo partidas **comerciales**: excluye cuentas por cobrar a socios,
  anticipos de impuestos y préstamos a terceros.

---

## 2. Endeudamiento

Responde: **¿quién financia a la empresa y qué tanto riesgo implica?**

### `nivel_endeudamiento`: Nivel de endeudamiento

```
pasivo_total / activo_total
```

- **Interpretación**: qué porcentaje de los activos está financiado por
  terceros (acreedores) y no por los socios.
- **Plantilla**: "El {valor}% de los activos de la empresa está financiado con
  deuda; en el sector típico es el {p50}%."
- **Matices**: mayor al 100% significa patrimonio negativo. Repórtalo como
  hallazgo principal, no solo como un indicador en rojo: es una señal fuerte
  de posible incumplimiento de la **hipótesis de negocio en marcha**, que
  desde la Ley 2069 de 2020 (art. 4) es causal de disolución y que los
  administradores deben evaluar y reportar al máximo órgano social.
- `n.a.` si `activo_total = 0`.

### `concentracion_cp`: Concentración de la deuda a corto plazo

```
pasivo_corriente / pasivo_total
```

- **Interpretación**: qué parte de la deuda vence en menos de un año.
- **Plantilla**: "El {valor}% de las deudas de la empresa vence en menos de un
  año (sector: {p50}%)."
- **Matices**: una concentración alta no es mala si la deuda es con
  proveedores (deuda operativa, normalmente sin costo). Es más riesgosa si es
  financiera: revisa `obligaciones_financieras_cp`.
- `n.a.` si `pasivo_total = 0`.

### `apalancamiento_total`: Apalancamiento total

```
pasivo_total / patrimonio
```

- **Interpretación**: cuántos pesos de deuda tiene la empresa por cada peso
  aportado o reinvertido por los socios.
- **Plantilla**: "Por cada $1 de los socios, la empresa tiene ${valor} de
  deuda con terceros (sector: ${p50})."
- `n.a.` si `patrimonio <= 0`; en ese caso remite al hallazgo de patrimonio negativo.

### `apalancamiento_financiero`: Apalancamiento financiero

```
(obligaciones_financieras_cp + obligaciones_financieras_lp) / patrimonio
```

- **Interpretación**: igual que el apalancamiento total, pero solo con la
  deuda **con costo** (bancos, leasing financiero, otras entidades financieras).
- **Plantilla**: "Por cada $1 de los socios, la empresa debe ${valor} a
  entidades financieras (sector: ${p50})."
- **Matices**: si es 0, la empresa no tiene deuda financiera. Dilo como dato,
  no como hallazgo positivo automático; puede estar desaprovechando
  financiación para crecer.
- `n.a.` si `patrimonio <= 0`.

### `cobertura_intereses`: Cobertura de intereses

```
utilidad_operacional / gastos_financieros
```

- **Interpretación**: cuántas veces la utilidad de la operación alcanza para
  pagar los intereses.
- **Plantilla**: "La utilidad operacional alcanza para pagar {valor} veces los
  intereses del periodo (sector: {p50} veces)."
- **Matices**:
  - Menor a 1: la operación no genera lo suficiente para pagar los
    intereses. Es una alerta crítica aunque el semáforo sectorial diga otra cosa.
  - `gastos_financieros` debe incluir **solo intereses y costos de deuda**.
    Excluye comisiones bancarias, GMF (4×1000) y diferencia en cambio cuando
    estén discriminados, y adviértelo si no lo están.
- `n.a.` si `gastos_financieros = 0`: la empresa no tiene gasto por intereses.
  Si la utilidad operacional es negativa, reporta el valor negativo y explícalo.

---

## 3. Rentabilidad

Responde: **¿la empresa gana dinero y qué tan bien usa sus recursos para ganarlo?**

### `margen_bruto`: Margen bruto

```
utilidad_bruta / ingresos_operacionales
```

- **Interpretación**: de cada peso vendido, cuánto queda después de pagar el
  costo directo de lo vendido.
- **Plantilla**: "De cada $100 que vende, a la empresa le quedan ${valor}
  después de cubrir el costo de lo vendido (sector: ${p50})."
- **Matices**: en empresas de servicios que no separan costo de ventas, el
  margen bruto es 100% o no es comparable. Si es así, márcalo `n.a.` y explícalo.

### `margen_operacional`: Margen operacional

```
utilidad_operacional / ingresos_operacionales
```

- **Interpretación**: lo que queda de cada peso vendido después de los costos
  y los gastos de administración y ventas. Muestra la rentabilidad **del
  negocio**, antes de financiación e impuestos.
- **Plantilla**: "Después de cubrir costos y gastos de operación, la empresa
  gana ${valor} por cada $100 vendidos (sector: ${p50})."
- **Matices**: si el margen bruto está bien pero el operacional está en rojo,
  el problema está en los gastos de administración o ventas, no en el precio
  ni en el costo.

### `margen_neto`: Margen neto

```
utilidad_neta / ingresos_operacionales
```

- **Interpretación**: lo que queda para los socios de cada peso vendido,
  después de todo (costos, gastos, intereses, otros ingresos y gastos, e impuestos).
- **Plantilla**: "Al final, a los socios les quedan ${valor} por cada $100
  vendidos (sector: ${p50})."
- **Matices**: si el margen neto es muy superior al operacional, la utilidad
  viene de **otros ingresos** (venta de activos, recuperaciones, dividendos),
  no de la operación. Señálalo, porque probablemente no se repetirá.

### `roa`: Rentabilidad del activo

```
utilidad_neta / prom(activo_total)
```

- **Interpretación**: cuánta utilidad genera cada peso invertido en activos.
- **Plantilla**: "Por cada $100 invertidos en activos, la empresa generó
  ${valor} de utilidad (sector: ${p50})."
- **Nota**: se usa utilidad neta (no operacional) para que sea comparable con
  los rangos calculados con datos de Supersociedades.

### `roe`: Rentabilidad del patrimonio

```
utilidad_neta / prom(patrimonio)
```

- **Interpretación**: cuánto ganaron los socios por cada peso que tienen
  invertido en la empresa.
- **Plantilla**: "Los socios obtuvieron una rentabilidad del {valor}% sobre su
  inversión (sector: {p50}%)."
- **Matices**:
  - `n.a.` si el patrimonio (final o promedio) es `<= 0`. Remite al hallazgo
    de patrimonio negativo: un ROE "positivo" con pérdida y patrimonio
    negativo es engañoso.
  - Compáralo con la tasa de un CDT o del costo de la deuda: si el ROE es
    menor, los socios estarían ganando más con una inversión sin riesgo.
    Menciónalo solo como referencia, sin cifras de tasas que no tengas.

---

## 4. Actividad

Responde: **¿qué tan rápido convierte la empresa su operación en efectivo?**

### `dias_cartera`: Rotación de cartera

```
prom(deudores_comerciales) / ingresos_operacionales × 360
```

- **Interpretación**: en promedio, cuántos días tardan los clientes en pagar.
- **Plantilla**: "Los clientes pagan, en promedio, a {valor} días (sector: {p50} días)."
- **Matices**:
  - Compáralo con el plazo de crédito que la empresa otorga, si el usuario
    lo conoce; es más útil que el sector.
  - Si los ingresos incluyen ventas de contado relevantes, el indicador
    subestima el plazo real de los clientes a crédito. Adviértelo si lo sabes.
- `n.a.` si `ingresos_operacionales = 0`.

### `dias_inventario`: Rotación de inventarios

```
prom(inventarios) / costo_ventas × 360
```

- **Interpretación**: cuántos días permanece el inventario en bodega antes de venderse.
- **Plantilla**: "El inventario tarda, en promedio, {valor} días en venderse
  (sector: {p50} días)."
- **Matices**: en manufactura, el inventario incluye materias primas, producto
  en proceso y terminado; si hay detalle, menciona cuál pesa más.
- `n.a.` si `costo_ventas = 0` o si la empresa no maneja inventarios
  (servicios). En ese caso no lo menciones como hallazgo.

### `dias_proveedores`: Rotación de proveedores

```
prom(proveedores) / costo_ventas × 360
```

- **Interpretación**: en promedio, cuántos días se toma la empresa para pagar
  a sus proveedores.
- **Sin semáforo sectorial**: pagar más tarde ayuda a la caja, pero puede
  indicar dificultades de pago o deteriorar la relación con proveedores. Se
  interpreta junto con la liquidez:
  - Días altos + liquidez en verde: buena negociación con proveedores.
  - Días altos + liquidez en rojo: probable atraso en pagos. Es una alerta.
- **Nota**: lo ideal sería usar compras en lugar de costo de ventas, pero
  rara vez están disponibles. Si el usuario entrega las compras del periodo,
  úsalas y anótalo.
- `n.a.` si `costo_ventas = 0`.

### `ciclo_efectivo`: Ciclo de conversión de efectivo

```
dias_cartera + dias_inventario - dias_proveedores
```

- **Interpretación**: cuántos días pasan desde que la empresa paga a sus
  proveedores hasta que cobra a sus clientes. Son los días que la empresa
  debe financiar con recursos propios o con deuda.
- **Plantilla**: "La empresa tarda {valor} días en recuperar el dinero que
  invierte en su operación (sector: {p50} días)."
- **Matices**: un ciclo negativo significa que los proveedores financian la
  operación (común en supermercados y comercio masivo). No es una alerta en
  sí misma.
- Si `dias_inventario` es `n.a.` por ser empresa de servicios, trátalo como 0
  y anótalo. Si es `n.a.` por falta de datos, el ciclo también es `n.a.`.

### `rotacion_activos`: Rotación de activos

```
ingresos_operacionales / prom(activo_total)
```

- **Interpretación**: cuántos pesos de ventas genera cada peso invertido en activos.
- **Plantilla**: "Por cada $1 invertido en activos, la empresa vendió ${valor}
  en el año (sector: ${p50})."
- **Matices**: depende mucho del tipo de negocio (comercio rota alto;
  inmobiliarias y generadoras de energía rotan bajo). Por eso la comparación
  sectorial es especialmente importante aquí.

---

## 5. Lecturas combinadas

Los hallazgos más valiosos salen de **cruzar indicadores**. Revisa estas
combinaciones y, si alguna aplica, preséntala como hallazgo en lugar de los
indicadores por separado:

| Patrón | Lectura probable | Qué sugerir revisar |
|---|---|---|
| Ingresos ↑, utilidad neta ↓ | Crecimiento sin rentabilidad: costos o gastos crecen más que las ventas | Análisis vertical del ERI; política de precios |
| Margen bruto 🟢, margen operacional 🔴 | Gastos de administración o ventas muy altos | Detalle de gastos operacionales; nómina administrativa |
| Margen operacional 🟢, margen neto 🔴 | La carga financiera o tributaria se come la utilidad | `cobertura_intereses`; tasa efectiva de impuesto |
| Margen neto > margen operacional | Utilidad sostenida por ingresos no operacionales | Composición de otros ingresos; recurrencia |
| Razón corriente 🟢, `dias_cartera` 🔴 | Liquidez "en el papel": cartera que no se convierte en efectivo | Edades de cartera; deterioro de cartera |
| Razón corriente 🟢, `dias_inventario` 🔴 | Liquidez sostenida por inventario lento | Inventario obsoleto o de baja rotación |
| `ktno` crece más que los ingresos | La operación consume cada vez más caja | Políticas de crédito, compras e inventario |
| Endeudamiento ↑ y `cobertura_intereses` ↓ | Deuda creciente con menor capacidad de pago | Perfil de vencimientos; posible reestructuración |
| `dias_proveedores` ↑ y liquidez 🔴 | Probable atraso en pagos a proveedores | Cartera vencida con proveedores |
| ROE 🟢 con endeudamiento 🔴 | Rentabilidad para los socios impulsada por la deuda, con más riesgo | Sostenibilidad de la deuda |
| Patrimonio ≤ 0 | Posible incumplimiento de la hipótesis de negocio en marcha (Ley 2069 de 2020, art. 4) | **Hallazgo principal del informe**; evaluación de negocio en marcha por los administradores |

Usa ↑/↓ para variaciones entre periodos y 🟢/🔴 para la comparación sectorial.
Si solo hay un periodo, aplica únicamente las combinaciones sectoriales.

---

## 6. Prioridad de los hallazgos

Para escoger los 5 hallazgos del resumen, ordena así:

1. Patrimonio negativo o `cobertura_intereses` < 1 (siempre van primero si aplican).
2. Lecturas combinadas de la sección 5.
3. Indicadores en 🔴, empezando por liquidez y endeudamiento.
4. Variaciones relevantes entre periodos (más de 20% en un indicador).
5. Fortalezas claras (🟢 muy por encima de P50), para que el informe no sea
   solo de problemas.

Incluye siempre **al menos una fortaleza**, si la hay.
