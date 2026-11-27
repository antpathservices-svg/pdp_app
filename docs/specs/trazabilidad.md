# Trazabilidad de criterios

Criterio → pantalla → lista raw → estado. Estados: pendiente, construido, aprobado, y «bloqueado (B-nn / P-n / C-n / R-n)» cuando el criterio depende de una brecha de datos (`mapeo-listas.md`, sección 4) o de una pregunta abierta (`inventarios.md`, sección 10). Los criterios de cada módulo se definen en su archivo (`docs/specs/<modulo>.md`). Lo actualizan quienes construyen (pendiente → construido) y supervisor-evaluador (construido → aprobado); un criterio bloqueado vuelve a pendiente cuando se resuelve su dependencia.

Las listas se escriben con el nombre `raw_*` de `sharepoint/productos.json`. Entre paréntesis, las brechas (B-nn) y preguntas (P-n) de las que depende el criterio.

## Inventarios y Compras (`inventarios.md`)

| Criterio | Pantalla | Lista raw | Estado |
|---|---|---|---|
| INV-01 | scrInventarios | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-02 | scrInventarios | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-03 | scrInventarios | (constante AccesosInventario) | construido |
| INV-04 | scrInventarios | (navegación) | construido |
| INV-05 | scrInventarios | — | construido |
| INV-06 | scrInventarios_General › Existencias | raw_inv_insumo | construido |
| INV-07 | scrInventarios_General › Existencias | raw_inv_insumo (P-8) | bloqueado (P-8) |
| INV-08 | scrInventarios_General › Existencias | — | construido |
| INV-09 | scrInventarios_General › Existencias | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-10 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-11 | scrInventarios_General › Existencias | raw_inv_insumo | construido |
| INV-12 | scrInventarios_General › Existencias | raw_inv_insumo | construido |
| INV-13 | scrInventarios_General › Existencias | — | construido |
| INV-14 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-15 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida; raw_inv_insumo; raw_inv_movimiento (P-3, P-9, R-H) | bloqueado (P-3, P-9, R-H) |
| INV-16 | scrInventarios_General › Existencias | raw_inv_insumo; raw_inv_insumo_categoria; raw_inv_almacen | construido |
| INV-17 | scrInventarios_General › Existencias | raw_inv_insumo | construido |
| INV-18 | scrInventarios_General › Existencias | raw_inv_masa_semana (testales, por confirmar); raw_inv_masa_mezcla (rendimiento) (B-10) | bloqueado (B-10) |
| INV-19 | Diálogo Orden de compra (scrInventarios_Orden) | raw_inv_orden_compra, raw_inv_orden_compra_partida; raw_inv_proveedor | construido |
| INV-20 | Diálogo Orden de compra (scrInventarios_Orden) | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-21 | Diálogo Orden de compra (scrInventarios_Orden) | raw_inv_proveedor | construido |
| INV-22 | Diálogo Orden de compra (scrInventarios_Orden) | raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-23 | Diálogo Orden de compra (scrInventarios_Orden) | raw_inv_orden_compra, raw_inv_orden_compra_partida | construido |
| INV-24 | Diálogo Orden de compra (scrInventarios_Orden) | (borrador en memoria) | construido |
| INV-25 | scrInventarios_General › Compras | raw_inv_compra; raw_inv_proveedor (P-9) | construido |
| INV-26 | scrInventarios_General › Compras | raw_inv_compra; raw_inv_proveedor (P-9) | construido |
| INV-27 | scrInventarios_General › Compras | raw_inv_compra_partida; raw_inv_insumo (P-9) | construido |
| INV-28 | scrInventarios_General › Movimientos | raw_inv_movimiento; raw_inv_movimiento_concepto; raw_inv_insumo | construido |
| INV-29 | scrInventarios_General › Movimientos | raw_inv_traspaso; raw_inv_traspaso_partida | construido |
| INV-30 | scrInventarios_General › Movimientos | raw_inv_traspaso; raw_inv_movimiento; raw_inv_insumo (P-10, R-H) | bloqueado (P-10, R-H) |
| INV-31 | scrInventarios_General › Conteos | raw_inv_conteo_fisico; raw_inv_conteo_fisico_partida; raw_inv_insumo (P-9) | construido |
| INV-32 | scrInventarios_General › Conteos | — | construido |
| INV-33 | scrInventarios_ControlMasa | raw_inv_masa_mezcla | construido |
| INV-34 | scrInventarios_ControlMasa | raw_inv_masa_mezcla | construido |
| INV-35 | scrInventarios_ControlMasa | raw_inv_masa_mezcla (C-8, P-2) | bloqueado (C-8, P-2) |
| INV-36 | scrInventarios_ControlMasa | raw_inv_masa_mezcla | construido |
| INV-37 | scrInventarios_Transferencia | raw_app_sucursal; raw_inv_traspaso | construido |
| INV-38 | scrInventarios_Transferencia | raw_inv_insumo; raw_inv_traspaso_partida | construido |
| INV-39 | scrInventarios_Transferencia | raw_inv_traspaso_partida | construido |
| INV-40 | scrInventarios_Transferencia | raw_inv_traspaso; raw_inv_traspaso_partida | construido |
| INV-41 | scrInventarios_Transferencia | — | construido |
| INV-42 | scrInventarios_Conteo | raw_inv_conteo_semanal | construido |
| INV-43 | scrInventarios_Conteo | raw_inv_conteo_semanal; raw_inv_conteo_semanal_linea; raw_inv_insumo | construido |
| INV-44 | scrInventarios_Conteo | raw_inv_insumo; raw_inv_insumo_categoria | construido |
| INV-45 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea | construido (abre la categoría; sin foco automático en el primer vacío) |
| INV-46 | scrInventarios_Conteo | raw_inv_insumo; raw_inv_unidad | construido |
| INV-47 | scrInventarios_Conteo | raw_inv_unidad | construido |
| INV-48 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea | construido |
| INV-49 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-09) | bloqueado (B-09) |
| INV-50 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-09) | bloqueado (B-09) |
| INV-51 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-09) | bloqueado (B-09) |
| INV-52 | scrInventarios_Conteo | raw_inv_conteo_semanal | construido |
| INV-53 | scrInventarios_Conteo | raw_inv_conteo_semanal (P-5) | bloqueado (P-5) |
| INV-54 | scrInventarios_ConteoRevision | raw_inv_insumo; raw_inv_conteo_semanal_linea | construido |
| INV-55 | scrInventarios_ConteoRevision | raw_inv_conteo_semanal_linea | construido |
| INV-56 | scrInventarios_ConteoRevision | raw_inv_conteo_semanal | construido |
| INV-57 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal; raw_inv_conteo_semanal_linea (B-09) | bloqueado (B-09) |
| INV-58 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal_linea; raw_inv_movimiento; raw_inv_insumo (B-09, P-10, R-H) | bloqueado (B-09, P-10, R-H) |
| INV-59 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal (B-09, P-9) | bloqueado (B-09, P-9) |
| INV-60 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal; raw_inv_conteo_semanal_historial; raw_inv_conteo_semanal_linea | construido |
| INV-61 | Todas | raw_inv_insumo | construido |
| INV-62 | Todas | raw_inv_insumo | construido |
| INV-63 | Todas | raw_inv_insumo; raw_inv_compra_partida; raw_inv_conteo_fisico_partida; raw_inv_traspaso_partida | construido |
| INV-64 | Todas | — | construido |
| INV-65 | Todas | — | construido |
| INV-66 | Todas | — | pendiente |
| INV-67 | Todas | — | construido |
| INV-68 | Todas | raw_inv_* | construido |
