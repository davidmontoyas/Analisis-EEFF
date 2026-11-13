# Cómo contribuir

¡Gracias por querer mejorar Analisis-EEFF!

## Reportar un error o proponer una mejora

Abre un *issue* indicando:

- Qué esperabas que pasara y qué pasó.
- El indicador, la cuenta PUC o el sector CIIU involucrado, si aplica.
- Un ejemplo con **datos ficticios**. Nunca subas estados financieros reales
  de clientes.

## Proponer cambios

1. Haz un *fork* del repositorio y crea una rama para tu cambio.
2. Si cambias una fórmula, actualiza al mismo tiempo
   `analisis-eeff/referencias/indicadores.md` y `scripts/calcular_indicadores.py`.
3. Si agregas un indicador, incluye su `id`, nombre en español e inglés,
   unidad, dirección e interpretación, siguiendo el formato de `indicadores.md`.
4. Envía un *pull request* explicando qué cambiaste y por qué.

## Criterios

- Lenguaje claro, pensado para contadores y para sus clientes.
- Referencias normativas colombianas citadas con número de norma y artículo.
- Términos en inglés tomados de `referencias/glosario-es-en.md`.
