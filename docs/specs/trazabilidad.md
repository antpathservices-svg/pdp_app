# Trazabilidad de criterios

Criterio → pantalla → lista raw → estado. Estados: pendiente, construido, aprobado, y «bloqueado (B-nn / P-n)» cuando el criterio depende de una brecha de datos (`mapeo-listas.md`, sección 4) o de una pregunta abierta (`inventarios.md`, sección 10). Los criterios de cada módulo se definen en su archivo (`docs/specs/<modulo>.md`). Lo actualizan quienes construyen (pendiente → construido) y supervisor-evaluador (construido → aprobado); un criterio bloqueado vuelve a pendiente cuando se resuelve su dependencia.

Las listas se escriben con el nombre `raw_*` de `sharepoint/productos.json`. Entre paréntesis, las brechas (B-nn) y preguntas (P-n) de las que depende el criterio.

## Inventarios y Compras (`inventarios.md`)

| Criterio | Pantalla | Lista raw | Estado |
|---|---|---|---|
| INV-01 | scrInventarios | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-02 | scrInventarios | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-03 | scrInventarios | (constante AccesosInventario) | pendiente |
| INV-04 | scrInventarios | (navegación) | pendiente |
| INV-05 | scrInventarios | — | pendiente |
| INV-06 | scrInventarios_General › Existencias | raw_inv_insumo | pendiente |
| INV-07 | scrInventarios_General › Existencias | raw_inv_insumo (P-8) | bloqueado (P-8) |
| INV-08 | scrInventarios_General › Existencias | — | pendiente |
| INV-09 | scrInventarios_General › Existencias | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-10 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-11 | scrInventarios_General › Existencias | raw_inv_insumo | pendiente |
| INV-12 | scrInventarios_General › Existencias | raw_inv_insumo | pendiente |
| INV-13 | scrInventarios_General › Existencias | — | pendiente |
| INV-14 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-15 | scrInventarios_General › Existencias | raw_inv_orden_compra, raw_inv_orden_compra_partida; raw_inv_insumo; raw_inv_movimiento (B-04, P-9) | bloqueado (B-04, P-9) |
| INV-16 | scrInventarios_General › Existencias | raw_inv_insumo; raw_inv_insumo_categoria; raw_inv_almacen | pendiente |
| INV-17 | scrInventarios_General › Existencias | raw_inv_insumo | pendiente |
| INV-18 | scrInventarios_General › Existencias | raw_inv_masa_semana (parcial) (B-10, B-01) | bloqueado (B-10, B-01) |
| INV-19 | Diálogo Orden de compra (scrInventarios_General) | raw_inv_orden_compra, raw_inv_orden_compra_partida; raw_inv_proveedor | pendiente |
| INV-20 | Diálogo Orden de compra (scrInventarios_General) | raw_inv_insumo; raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-21 | Diálogo Orden de compra (scrInventarios_General) | raw_inv_proveedor | pendiente |
| INV-22 | Diálogo Orden de compra (scrInventarios_General) | raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-23 | Diálogo Orden de compra (scrInventarios_General) | raw_inv_orden_compra, raw_inv_orden_compra_partida | pendiente |
| INV-24 | Diálogo Orden de compra (scrInventarios_General) | (borrador en memoria) | pendiente |
| INV-25 | scrInventarios_General › Compras | raw_inv_compra; raw_inv_proveedor (P-9) | pendiente |
| INV-26 | scrInventarios_General › Compras | raw_inv_compra; raw_inv_proveedor (P-9) | pendiente |
| INV-27 | scrInventarios_General › Compras | raw_inv_compra_partida; raw_inv_insumo (P-9) | pendiente |
| INV-28 | scrInventarios_General › Movimientos | raw_inv_movimiento; raw_inv_movimiento_concepto; raw_inv_insumo | pendiente |
| INV-29 | scrInventarios_General › Movimientos | raw_inv_traspaso; raw_inv_traspaso_partida | pendiente |
| INV-30 | scrInventarios_General › Movimientos | raw_inv_traspaso; raw_inv_movimiento; raw_inv_insumo (B-03, P-10) | bloqueado (B-03, P-10) |
| INV-31 | scrInventarios_General › Conteos | raw_inv_conteo_fisico; raw_inv_conteo_fisico_partida; raw_inv_insumo (P-9) | pendiente |
| INV-32 | scrInventarios_General › Conteos | — | pendiente |
| INV-33 | scrInventarios_ControlMasa | sin lista (B-01, P-2) | bloqueado (B-01, P-2) |
| INV-34 | scrInventarios_ControlMasa | sin lista (B-01, P-2) | bloqueado (B-01, P-2) |
| INV-35 | scrInventarios_ControlMasa | sin lista (B-01, P-2) | bloqueado (B-01, P-2) |
| INV-36 | scrInventarios_ControlMasa | sin lista (B-01, P-2) | bloqueado (B-01, P-2) |
| INV-37 | scrInventarios_Transferencia | raw_app_sucursal; raw_inv_traspaso (B-06) | pendiente (B-06: sin filtro de activas) |
| INV-38 | scrInventarios_Transferencia | raw_inv_insumo; raw_inv_traspaso_partida | pendiente |
| INV-39 | scrInventarios_Transferencia | raw_inv_traspaso_partida | pendiente |
| INV-40 | scrInventarios_Transferencia | raw_inv_traspaso; raw_inv_traspaso_partida (B-03) | bloqueado (B-03) |
| INV-41 | scrInventarios_Transferencia | — | pendiente |
| INV-42 | scrInventarios_Conteo | raw_inv_conteo_semanal (B-02) | bloqueado (B-02) |
| INV-43 | scrInventarios_Conteo | raw_inv_conteo_semanal; raw_inv_conteo_semanal_linea; raw_inv_insumo (B-02) | bloqueado (B-02) |
| INV-44 | scrInventarios_Conteo | raw_inv_insumo; raw_inv_insumo_categoria (B-02) | bloqueado (B-02) |
| INV-45 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-46 | scrInventarios_Conteo | raw_inv_insumo; raw_inv_unidad | pendiente |
| INV-47 | scrInventarios_Conteo | raw_inv_unidad | pendiente |
| INV-48 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-49 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-02, B-09) | bloqueado (B-02, B-09) |
| INV-50 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-51 | scrInventarios_Conteo | raw_inv_conteo_semanal_linea (B-02, B-09) | bloqueado (B-02, B-09) |
| INV-52 | scrInventarios_Conteo | raw_inv_conteo_semanal (B-02) | bloqueado (B-02) |
| INV-53 | scrInventarios_Conteo | raw_inv_conteo_semanal | pendiente |
| INV-54 | scrInventarios_ConteoRevision | raw_inv_insumo; raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-55 | scrInventarios_ConteoRevision | raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-56 | scrInventarios_ConteoRevision | raw_inv_conteo_semanal (B-07) | bloqueado (B-07) |
| INV-57 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal; raw_inv_conteo_semanal_linea (B-02) | bloqueado (B-02) |
| INV-58 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal_linea; raw_inv_movimiento; raw_inv_insumo (B-02, B-09, P-10) | bloqueado (B-02, B-09, P-10) |
| INV-59 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal (B-07, B-02, P-9) | bloqueado (B-07, B-02, P-9) |
| INV-60 | scrInventarios_ConteoCierre | raw_inv_conteo_semanal (historial); raw_inv_conteo_semanal_linea (B-08, B-02) | bloqueado (B-08, B-02) |
| INV-61 | Todas | raw_inv_insumo | pendiente |
| INV-62 | Todas | raw_inv_insumo | pendiente |
| INV-63 | Todas | raw_inv_insumo; raw_inv_compra_partida; raw_inv_conteo_fisico_partida; raw_inv_traspaso_partida | pendiente |
| INV-64 | Todas | — | pendiente |
| INV-65 | Todas | — | pendiente |
| INV-66 | Todas | — | pendiente |
| INV-67 | Todas | — | pendiente |
| INV-68 | Todas | raw_inv_* | pendiente |
