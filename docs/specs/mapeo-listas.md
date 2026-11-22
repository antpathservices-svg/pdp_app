# Mapeo de listas · Inventarios y Compras

Traduce cada lista o colección que nombran DPZ-UX-02 (Inventarios y Compras v1.4) y las globales de DPZ-UX-01 (Menú v1.2) a la lista `raw_*` del Marketplace (`sharepoint/productos.json`). Regla de origen: `docs/decisiones.md` D1.

Alcance de esta versión: solo el módulo Inventarios y Compras. Las listas de Ventas, Franquicias y Análisis se mapean en sus propias entregas.

## Fuentes citadas

| Clave | Fuente |
|---|---|
| UX02 | DPZ-UX-02 Inventarios y Compras v1.4. Secciones: 00 Resumen, 01 Widgets nuevos, 02 Pantallas (maquetas, árbol de controles, tabla Comportamiento), 03 Power Fx (se cita por el título del bloque de código), 04 Checklist (se cita `#n`, n = posición en la lista) |
| UX01 | DPZ-UX-01 Menú principal v1.2. Bloques «Tokens globales» y «Datos del menú», sección 04 (convención de nombres) |
| PROTO | Sub-app Inventarios del prototipo (`sub_INV.html`), citada por función o tarjeta |
| JSON | `sharepoint/productos.json` |

## Convenciones

- **Una lista por sucursal.** Ninguna lista `raw_inv_*` tiene columna `Sucursal` ni `idempresa` (sí existen en otros dominios: `raw_pos_*.idempresa`, `raw_app_auditoria*.sucursal`). El kit de activación crea las mismas listas en el sitio de cada sucursal (UX02 §03, bloque «Listas de captura en SharePoint»). Por eso se omite el filtro `Sucursal = varSucursal` de las fórmulas de la spec (decisión D3: una sola sucursal, Guanajuato · Río Bravo).
- **Nombres internos.** Atributos reservados de SharePoint llevan sufijo `_raw` (`Deploy-Listas.ps1`, lista `$Reservados`). En este módulo: `id` → `id_raw` (en `raw_inv_insumo_categoria`, `raw_inv_conteo_semanal`, `raw_inv_orden_compra`, `raw_inv_traspaso`) y `version` → `version_raw` (en `raw_inv_conteo_semanal`). El nombre visible no cambia. En `raw_app_receta_producto` la columna `c` se guardó como `_x0063_` (`sharepoint/README.md`, sección Despliegues).
- **Tipos.** Todo texto es una línea de 255 caracteres salvo `referencia`, `comentarios`, `comentario`, `historial` y `resolucion` (varias líneas). `estado` y `alerta` son texto, no columnas de elección: la validación de valores la hace la app.
- **Captura / lectura / publicación.** CLAUDE.md: una lista es de captura (la escribe la app) o de publicación (la escribe Python por Graph), nunca de las dos. La columna «Uso» de cada tabla indica cómo la usa esta app. **Origen (D4):** todas las `raw_inv_*` son de captura y la app las escribe (existencia, compras, movimientos, conteos físicos, órdenes, transferencias, mezclas); del POS solo se leen ventas, cortes y catálogo de productos. UX02 §03 «Fuentes» las presenta como publicación del POS: esa parte de la spec se sustituye (tabla 1.1). La columna «Uso» de cada tabla indica solo lo que **esta spec** hace con la lista. El JSON no declara si una lista es de captura o de publicación: lo que sigue sale de la spec y del prototipo y debe confirmarlo backend-dev.
- **Derivado.** Columna que la spec trae calculada o por unión y que `raw_*` no guarda (CLAUDE.md: raw es copia fiel, sin columnas calculadas). La app la calcula. Delegación: `LookUp(lista, columna = valor)` y `Filter` con `=`/`>=` sí delegan contra SharePoint; no delegan `AddColumns`, el `LookUp` anidado por fila ni `in`. Esas uniones se evalúan en memoria y son aceptables solo con los volúmenes pequeños indicados.
- **Índices.** `Deploy-Listas.ps1` indexa solo las columnas de la llave (`pk`) y la de carga incremental (`inc`, vacía en todas las listas de inventario). Una columna de fecha que no es llave no está indexada. Ver Riesgos R-01.

## 1. Resumen

| Lista en la spec | Lista `raw_*` que la sustituye | Uso en esta app | Cobertura |
|---|---|---|---|
| `pubCatInsumos` | `raw_inv_insumo` + `raw_inv_insumo_categoria` | Lectura | Parcial (B-05) |
| `CatUnidades` | `raw_inv_unidad` | Lectura | Completa |
| `CatSucursales` | `raw_app_sucursal` | Lectura | Parcial (B-06) |
| `pubInvExistencia` | `raw_inv_insumo` + `raw_inv_almacen` | Lectura y captura de `existencia` (D4) | Parcial (B-11) |
| `pubInvCompra` | `raw_inv_compra` + `raw_inv_proveedor` | Lectura | Completa |
| `pubInvCompraDetalle` | `raw_inv_compra_partida` | Lectura | Completa |
| `pubInvMovimiento` | `raw_inv_movimiento` + `raw_inv_movimiento_concepto` | Lectura y captura (D4) | Completa |
| `pubInvConteo` | `raw_inv_conteo_fisico` | Lectura | Completa (con derivados) |
| `pubInvConteoDetalle` | `raw_inv_conteo_fisico_partida` | Lectura | Completa (con derivados) |
| `ProveedoresSucursal` | `raw_inv_proveedor` | Lectura | Completa (solo nombre, UX02 §04 #7) |
| `OrdenesCompra` | `raw_inv_orden_compra` | Captura | Parcial (B-04) |
| `OrdenesCompraLinea` | `raw_inv_orden_compra_partida` | Captura | Completa |
| `InvConteo` | `raw_inv_conteo_semanal` | Captura | Parcial (B-07) |
| `InvConteoLinea` | `raw_inv_conteo_semanal_linea` | Captura | Parcial (B-02) |
| `InvConteoHistorial` | `raw_inv_conteo_semanal.historial` (columna JSON) | Captura | Parcial (B-08) |
| `InvControlMasa` | Ninguna | Captura | **BRECHA** (B-01) |
| `InvTransferencia` | `raw_inv_traspaso` | Captura | Parcial (B-03) |
| `InvTransferenciaLinea` | `raw_inv_traspaso_partida` | Captura | Parcial (B-03) |
| `colRef` (SemanaPasada, Promedio4, Compras, Entradas, Salidas) | Ninguna (derivada) | Lectura | **BRECHA** (B-09) |
| `TestalesSemana`, `RendimientoReal` (ajuste de harina) | `raw_inv_masa_semana` (parcial) | Lectura | **BRECHA** (B-10) |
| `EstadosInventario`, `EstadosLineaConteo`, `EstadosConteo`, `EstadosTransferencia`, `AccesosInventario`, `GruposMenu`, `ModulosDpz`, `IconosDpz` | No son listas: constantes de `App › Formulas` | n/a | Sin lista (sección 3) |

### 1.1 Origen de cada lista (D4)

UX02 §03 «Fuentes» describe `pubInv*` como publicación del pipeline desde Soft Restaurant (`acumuladoinsumos`, `compras`, `movsinv`, `invfisico`). CLAUDE.md dice que del POS solo se leen ventas, cortes de caja y catálogo de productos, y que insumos, inventarios y compras se capturan en la plataforma; el JSON marca `origen` = `inv`. `docs/decisiones.md` D4 resuelve la contradicción (P-7 cerrada): todas las `raw_inv_*` son de **captura** y la app las escribe. Regla de CLAUDE.md: una lista es de captura o de publicación, nunca de las dos; por D4 ninguna `raw_inv_*` es de publicación.

| Listas | Según UX02 | Origen (D4) | Qué escribe esta spec |
|---|---|---|---|
| `raw_inv_insumo` | Catálogo y existencia publicados | Captura | `existencia` (Recibir orden, Registrar entrada, confirmar transferencia) |
| `raw_inv_insumo_categoria`, `raw_inv_almacen`, `raw_inv_unidad`, `raw_inv_proveedor` | Catálogos del corporativo | Captura | Nada (solo lectura en esta spec) |
| `raw_inv_movimiento`, `raw_inv_movimiento_concepto` | Publicación desde el POS | Captura | Movimientos (ver abajo) |
| `raw_inv_compra`, `raw_inv_compra_partida`, `raw_inv_conteo_fisico`, `raw_inv_conteo_fisico_partida` | Publicación desde el POS | Captura | Nada en las pantallas de la spec (P-9) |
| `raw_inv_orden_compra*`, `raw_inv_conteo_semanal*`, `raw_inv_traspaso*`, `raw_inv_masa_semana` | Captura de la app | Captura | Ver sección 2 |

Escrituras sobre `raw_inv_movimiento` (B-13, resuelta por D4). Los `idconcepto` son los del JSON y del prototipo; las columnas son las de la lista (`fecha`, `idconcepto`, `idinsumo`, `cantidad` con signo, `costo`, `idalmacen`, `referencia`):

| Evento | `idconcepto` | Signo | `costo` | `referencia` | Fuente |
|---|---|---|---|---|---|
| Recibir una orden de compra (INV-15) | CMP (Entrada por compra) | + | costo promedio del insumo | «Recepción OC-nnnn · proveedor» | D4; PROTO recepción de orden |
| Confirmar envío de transferencia (INV-30) | TRS (Salida por traspaso) | − | precio de la partida | «Transferencia T-nnnn · a <sucursal>» | UX02 §03 «transferencias.fx» (comentario final); PROTO confirmación |
| Confirmar recepción de transferencia (INV-30) | TRE (Entrada por traspaso) | + | precio de la partida | «Transferencia T-nnnn · de <sucursal>» | Ídem |
| «Registrar entrada» tipo transferencia (INV-58) | TRE | + | costo promedio del insumo | folio capturado | PROTO «Registrar entrada faltante» |
| «Registrar entrada» tipo compra sin orden (INV-58) | CMP | + | costo promedio del insumo | folio capturado | Ídem |

Cada una de estas escrituras también suma o resta `raw_inv_insumo.existencia`. D4 lo dice solo para Recibir; para transferencias y «Registrar entrada» es un supuesto que debe confirmar el líder.

## 2. Detalle por lista

En cada tabla, «Spec» es la columna tal como la escribe UX02 §03 y «Raw» es el nombre visible en `raw_*`. «Interno» solo se muestra si difiere.

### 2.1 `pubCatInsumos` → `raw_inv_insumo` + `raw_inv_insumo_categoria`

Uso: lectura. Fuente de la spec: UX02 §03 «Listas de captura en SharePoint» (catálogo, lectura, lo publica el corporativo, versionado). Cantidad esperada: 89 insumos en 9 categorías (UX02 §00).

| Spec | Raw | Nota |
|---|---|---|
| `idinsumo` | `raw_inv_insumo.idinsumo` | Llave |
| `descripcion` | `raw_inv_insumo.descripcion` | |
| `presentacion` | `raw_inv_insumo.presentacion` | Es la unidad de conteo; enlaza con `raw_inv_unidad.unidad` |
| `Categoria` | `raw_inv_insumo_categoria.nombre` vía `raw_inv_insumo.idcategoria` = `raw_inv_insumo_categoria.id_raw` | Derivado por unión |
| `OrdenCategoria` | `raw_inv_insumo_categoria.orden` | Orden de despliegue |
| `OrdenConteo` | — | **BRECHA** B-05 |
| `Activo` | — | **BRECHA** B-05 |
| `AplicaA` | — | **BRECHA** B-05 |
| `VersionCatalogo` | — | **BRECHA** B-05 |

Nota: la spec dice que el catálogo no lleva costo (el costo es por sucursal, `insumosdetalle.costopromedio`). En el Marketplace `raw_inv_insumo` junta catálogo, existencia, umbrales y `costopromedio` en una sola lista. El Colaborador no debe ver costos (instrucción del líder; PROTO oculta Costo prom. y Valor para `col`), así que el ocultamiento queda en la app, no en el dato. Ver Riesgos R-03.

### 2.2 `CatUnidades` → `raw_inv_unidad`

Uso: lectura. Fuente: UX02 §03 «Listas de captura en SharePoint».

| Spec | Raw | Nota |
|---|---|---|
| `Unidad` (= presentación) | `unidad` | Llave |
| `Etiqueta` | `n` | «Nombre en plural» (por ejemplo «bultos», «kg») |
| `Abreviatura` | `ab` | |
| `PermiteDecimales` | `dec` | Booleano |

### 2.3 `CatSucursales` → `raw_app_sucursal`

Uso: lectura. Fuente: UX02 §03 y pantalla Transferencia (UX02 §03 «Transferencias»).

| Spec | Raw | Nota |
|---|---|---|
| `Sucursal` | `nombre` | Llave |
| `RazonSocial` | — | **BRECHA** B-06 |
| `Estado` | — | **BRECHA** B-06 |
| `Activa` | — | **BRECHA** B-06 |

Por D3 el selector de sucursales no se construye (ver B-03 y la pregunta abierta de `inventarios.md`).

### 2.4 `pubInvExistencia` → `raw_inv_insumo` + `raw_inv_almacen`

Uso: lectura, y escritura de `existencia` (D4, ver 1.1). UX02 §03 «Fuentes» la presenta como lista de publicación; por D4 es de captura. La spec define una fila por insumo y almacén, que se reemplaza en cada corte.

| Spec | Raw | Nota |
|---|---|---|
| `idinsumo` | `raw_inv_insumo.idinsumo` | |
| `descripcion` | `raw_inv_insumo.descripcion` | |
| `categoria` | `raw_inv_insumo_categoria.nombre` | Derivado (2.1) |
| `unidad` | `raw_inv_insumo.presentacion` | La spec usa la presentación como unidad |
| `idalmacen` | `raw_inv_insumo.idalmacen` | Un solo almacén por insumo (B-11) |
| `almacen` | `raw_inv_almacen.nombre` | Derivado por unión con `idalmacen` |
| `existencia` | `raw_inv_insumo.existencia` | |
| `stockminimo` | `raw_inv_insumo.stockminimo` | |
| `stockideal` | `raw_inv_insumo.stockideal` | |
| `stockmaximo` | `raw_inv_insumo.stockmaximo` | |
| `costopromedio` | `raw_inv_insumo.costopromedio` | Oculto al Colaborador |
| `PorRecibir`, `Valor`, `Estado` (columnas de `colInvVista`) | — | Derivados en la app (UX02 §03 «scrInventarios · Carga…»): `PorRecibir` = suma de cantidades de las líneas de órdenes Pendiente; `Valor` = existencia × costopromedio; `Estado` = `EstadoInsumo` |

PROTO agrega dos casos que la spec no tiene: umbrales en 0 («Sin umbral») y existencia negativa («Existencia negativa»), ver `inventarios.md` INV-07.

### 2.5 `pubInvCompra` → `raw_inv_compra` + `raw_inv_proveedor`

Uso: lectura. Fuente: UX02 §03 «Fuentes» y «Compras, movimientos y conteos».

| Spec | Raw | Nota |
|---|---|---|
| `idcompra` | `idcompra` | Llave |
| `folio` | `folio` | |
| `Fecha` (fechaaplicacion) | `fechaaplicacion` | No está indexada (R-01) |
| `proveedor` | `raw_inv_proveedor.nombre` vía `raw_inv_compra.idproveedor` | Derivado por unión |
| `foliofactura` | `foliofactura` | |
| `cancelado` | `cancelado` | |
| `subtotal` | `subtotal` | |
| `impuesto1` | `impuesto1` | |
| `total` | `total` | |

### 2.6 `pubInvCompraDetalle` → `raw_inv_compra_partida`

Uso: lectura. Todas las columnas coinciden por nombre: `idcompra`, `idinsumo`, `cantidad`, `costo`, `impuesto1`, `importesinimpuestos`, `importeconimpuestos`, `idalmacen`. La pantalla muestra además el nombre del insumo y la unidad (`raw_inv_insumo`, derivado). `Sucursal` no existe (convención). El costo y el importe se ocultan al Colaborador (PROTO: el Colaborador no ve la pestaña Compras).

### 2.7 `pubInvMovimiento` → `raw_inv_movimiento` + `raw_inv_movimiento_concepto`

Uso: lectura. La spec publica solo los últimos 90 días y la pantalla filtra los últimos 7 (UX02 §03 «Compras, movimientos y conteos»).

| Spec | Raw | Nota |
|---|---|---|
| `Fecha` | `raw_inv_movimiento.fecha` | Fecha-hora, indexada (parte de la llave) |
| `idconcepto` | `idconcepto` | |
| `concepto` | `raw_inv_movimiento_concepto.descripcion` | Derivado |
| `tipo` | `raw_inv_movimiento_concepto.tipo` | 1 entrada, 2 salida |
| `idinsumo` | `idinsumo` | |
| `cantidad` (con signo) | `cantidad` | «Cantidad con signo» |
| `costo` | `costo` | |
| `idalmacen` | `idalmacen` | |
| `referencia` | `referencia` | «Motivo, comentario o folio» |
| `descripcion`, `unidad` (usadas por la pantalla) | `raw_inv_insumo.descripcion`, `.presentacion` | Derivados por unión con `idinsumo` |

Conceptos conocidos (JSON, descripción de `idconcepto`): CMP, TRE, TRS, SPV, MER, EPP, SPP. PROTO usa también `SPD` y `SPM` para mermas; no aparecen en el JSON (confirmar en `raw_inv_movimiento_concepto`).

### 2.8 `pubInvConteo` → `raw_inv_conteo_fisico`

Uso: lectura (inventarios físicos del POS).

| Spec | Raw | Nota |
|---|---|---|
| `folio` | `folio` | Llave |
| `Fecha` | `fecha` | No indexada (R-01) |
| `inventarioteorico` | `inventarioteorico1` | Sufijo 1 = almacén 1 |
| `inventariofisico` | `inventariofisico1` | |
| `diferencia` | — | Derivado: físico − teórico |
| (no está en la spec) | `idalmacen1`, `idalmacen2` | Almacenes contados |

### 2.9 `pubInvConteoDetalle` → `raw_inv_conteo_fisico_partida`

Uso: lectura.

| Spec | Raw | Nota |
|---|---|---|
| `folio` | `folio` | |
| `idinsumo` | `idinsumo` | |
| `existenciaalmacen` | `existenciaalmacen1` | |
| `fisicoalmacen` | `fisicoalmacen1` | |
| `diferenciaalmacen` | — | Derivado: `fisicoalmacen1` − `existenciaalmacen1` |
| `costo` | `costo` | Oculto al Colaborador; el valor de la diferencia = diferencia × costo |

### 2.10 `ProveedoresSucursal` → `raw_inv_proveedor`

Uso: lectura. Spec: «solo el nombre. Sin RFC, cuenta bancaria ni datos de pago» (UX02 §03 «Fuentes», UX02 §04 #7). Columnas: `idproveedor`, `nombre`, `giro`. La app usa `nombre`. En `raw_inv_orden_compra.proveedor` se guarda el nombre (texto), no `idproveedor`.

### 2.11 `OrdenesCompra` → `raw_inv_orden_compra`

Uso: **captura** (la escribe la app; la lista está vacía en el snapshot). Fuente: UX02 §03 «Orden de compra con varios insumos».

| Spec | Raw | Interno | Nota |
|---|---|---|---|
| `Title` («OC-0007») | `id` | `id_raw` | Formato OC-0000 |
| `Proveedor` | `proveedor` | | Nombre del proveedor |
| `Sucursal` | — | | No aplica (una lista por sucursal) |
| `Estado` (Pendiente, Recibida) | `estado` | | La spec solo usa Pendiente y Recibida. PROTO usa además Por aprobar y Rechazada (B-04) |
| `Creada` (Now()) | `creada` | | El raw es solo fecha, sin hora |
| `CreadaPor` (User().Email) | `creo` | | Texto |
| `Recibida` | — | | **BRECHA** B-04 |
| `RecibidaPor` | — | | **BRECHA** B-04 |
| (no está en la spec) | `entrega`, `elaboro`, `comentarios`, `origen`, `ajuste` | | Vienen de PROTO v2 (`Crear orden`): fecha de entrega solicitada, quién elaboró, comentarios, origen (manual o sugerida), ajuste % de la sugerida |

### 2.12 `OrdenesCompraLinea` → `raw_inv_orden_compra_partida`

Uso: captura.

| Spec | Raw | Nota |
|---|---|---|
| `OrdenId` | `id_orden` | Referencia a `raw_inv_orden_compra.id_raw` (texto «OC-0007»); la spec usa el ID numérico de SharePoint |
| `IdInsumo` | `idinsumo` | |
| `Insumo` | — | Derivado: `raw_inv_insumo.descripcion` |
| `Cantidad` | `cantidad` | |
| `Unidad` | `unidad` | |

La llave del JSON es (`id_orden`, `idinsumo`): coincide con la regla de la spec «un insumo no se repite» en una orden (UX02 §02 Comportamiento, Orden de compra).

### 2.13 `InvConteo` → `raw_inv_conteo_semanal`

Uso: **captura**. Fuente: UX02 §03 «Listas de captura en SharePoint».

| Spec | Raw | Interno | Nota |
|---|---|---|---|
| `Title` («CS-2026-43») | `id` | `id_raw` | Formato CS-AAAA-SS |
| `Periodo` (202643, único) | — | | Derivado: `anio` × 100 + `semana`. Ninguna columna es única (Deploy-Listas) |
| `Semana` | `semana` | | |
| `Del`, `Al` (fecha) | `del`, `al` | | El raw los guarda como **texto**, no fecha (en PROTO, «19 oct») |
| `Estado` | `estado` | | Texto: Borrador, Por revisar, Cerrado, Corregido |
| `Version` | `version` | `version_raw` | |
| `VersionCatalogo` | — | | **BRECHA** B-07 |
| `Comentario` | `comentario` | | |
| `CapturadoPor` | `capturadoPor` | | El raw dice «Rol que capturó»; la spec guarda la persona (B-07) |
| `EnviadoPor` | — | | **BRECHA** B-07 |
| `EnviadoEl` | `enviadoEl` | | |
| `CerradoPor` | `cerradoPor` | | |
| `CerradoEl` | `cerradoEl` | | |
| `RolCierre` | — | | **BRECHA** B-07 |
| (no está en la spec) | `historial` | | Columna `lista` (JSON): ver 2.15 |

### 2.14 `InvConteoLinea` → `raw_inv_conteo_semanal_linea`

Uso: **captura**.

| Spec | Raw | Nota |
|---|---|---|
| `ConteoId` | — | **BRECHA** B-02 |
| `Periodo` | — | **BRECHA** B-02 |
| `IdInsumo` | `idinsumo` | La única columna de llave del JSON |
| `Categoria` | — | Derivado: `raw_inv_insumo.idcategoria` |
| `Cantidad` | `cantidad` | |
| `SinExistencia` | `sinExistencia` | |
| `Alerta` (variacion, cero, dedo, vacío) | `alerta` | Texto |
| `Resuelta` | `resuelta` | |
| `Resolucion` | `resolucion` | |
| `ResueltaPor` | — | Sin columna (B-07) |
| `CapturadoPor` (persona) | `capturadoPor` | El raw dice «Rol que capturó» |
| `CapturadoComo` (rol) | `capturadoPor` | Mismo campo: solo hay uno |

«Excede lo disponible» se calcula, no se guarda (UX02 §03).

### 2.15 `InvConteoHistorial` → `raw_inv_conteo_semanal.historial`

Uso: captura. La spec tiene una lista aparte con una fila por corrección: `ConteoId, Version, IdInsumo, Antes, Despues, Motivo, Por, El, Rol`. El Marketplace solo tiene la columna `historial` («Bitácora», tipo `lista`: varias líneas con JSON) dentro del encabezado. PROTO la usa con la forma `{version, insumo, antes, despues, motivo, por, el}` (función de corrección, `CS.historial.unshift`). Faltan `IdInsumo` (queda el nombre) y `Rol`. Ver B-08.

### 2.16 `InvControlMasa` → ninguna

Uso: captura. Spec: una fila por mezcla con `Fecha`, `Mezcla` (1 a 10), `Oz17`, `Oz10`, `Oz5` (enteros ≥ 0), `CapturadoPor`, `CapturadoEl` (UX02 §03). La única lista de masa del Marketplace es `raw_inv_masa_semana` (`s` fecha del lunes, `cajas`, `bol`; descripción del JSON: «Cajas y bolsas de masa capturadas por semana»): es captura con grano **semanal**, no diaria por mezcla ni por tamaño. **BRECHA** B-01.

### 2.17 `InvTransferencia` → `raw_inv_traspaso`

Uso: captura.

| Spec | Raw | Interno | Nota |
|---|---|---|---|
| `Title` («T-0007») | `id` | `id_raw` | |
| `Envia` | `envia` | | Texto |
| `Recibe` | `recibe` | | Texto |
| `Estado` | `estado` | | Solicitada, Enviada, Recibida |
| `Total` | — | | Derivado: suma de cantidad × precio de las partidas |
| `CreadaPor`, `EnviadaPor`, `RecibidaPor` | — | | **BRECHA** B-03 |
| `CreadaEl` | `creada` | | Solo fecha |
| `EnviadaEl` | `enviada` | | Solo fecha |
| `RecibidaEl` | `recibida` | | Solo fecha |
| (no está en la spec) | `notificada` | | Fecha de la notificación a la otra sucursal (PROTO: aviso por Power Automate) |

### 2.18 `InvTransferenciaLinea` → `raw_inv_traspaso_partida`

Uso: captura.

| Spec | Raw | Nota |
|---|---|---|
| `TransferenciaId` | `id_traspaso` | Referencia a `raw_inv_traspaso.id_raw`. Es la única columna de llave del JSON (B-03) |
| `Cantidad` | `cantidad` | |
| `Unidad` | `unidad` | |
| `Descripcion` | `descripcion` | «Artículo» |
| `IdInsumo` (si viene del catálogo) | — | **BRECHA** B-03 |
| `Precio` | `precio` | Oculto al Colaborador |
| `Total` | — | Derivado: cantidad × precio |

## 3. Constantes de app (no son listas)

La spec define estas tablas en `App › Formulas`. No se crean listas para ellas.

| Nombre | Contenido | Fuente |
|---|---|---|
| `EstadosInventario` | critico, bajo, pedido, ok, exceso (etiqueta, color, orden) | UX02 §03 «Estados y reglas de inventario» |
| `EstadosLineaConteo` | variacion, cero (la spec escribe `cerou` aquí y `cero` en `AlertaConteo`; ver R-06), dedo, disp, resuelta | UX02 §03 «Reglas de conteo, masa y transferencias» |
| `EstadosConteo` | Borrador, Por revisar, Cerrado, Corregido | Ídem |
| `EstadosTransferencia` | Solicitada, Enviada, Recibida | Ídem |
| `AccesosInventario` | Los 5 accesos de scrInventarios | UX02 §03 «Estados y reglas de inventario» |
| `GruposMenu`, `ModulosDpz`, `IconosDpz`, `Tema` | Menú y tokens globales | UX01 bloques «Tokens globales», «Datos del menú» |

## 4. Brechas

| ID | Lista(s) de la spec | Qué falta | Impacto | Pantalla afectada |
|---|---|---|---|---|
| B-01 | `InvControlMasa` | No hay lista de captura de mezclas (Fecha, Mezcla 1–10, Oz17, Oz10, Oz5, CapturadoPor/El). `raw_inv_masa_semana` es captura de grano semanal (`cajas`, `bol`) | Bloquea guardar | scrInventarios_ControlMasa |
| B-02 | `InvConteoLinea` | `raw_inv_conteo_semanal_linea` no tiene `ConteoId` ni `Periodo`; su llave es solo `idinsumo` (también lo advierte `sharepoint/README.md`, Pendiente). No se pueden separar las líneas de un conteo de las de otro, ni leer «semana pasada» | Bloquea guardar y leer líneas | Conteo, Revisión, Cierre |
| B-03 | `InvTransferencia`, `InvTransferenciaLinea` | Sin `CreadaPor`, `EnviadaPor`, `RecibidaPor`; sin `Total`; fechas sin hora; línea sin `IdInsumo`; llave de partida solo `id_traspaso`. Además la spec deja abierto dónde vive la lista cuando la ven dos sucursales (UX02 §03: opción A o B, [C]) | Parcial: se guarda sin actores | Transferencia, General › Movimientos |
| B-04 | `OrdenesCompra` | Sin `Recibida`, `RecibidaPor`. PROTO v2 agrega aprobación (Por aprobar, Rechazada, quién aprobó), correo de envío y recepción con folio de factura, fecha, quién recibió, evidencia y cantidades recibidas; ninguno tiene columna | Bloquea «Recibir» con auditoría | Diálogo orden, General › Existencias |
| B-05 | `pubCatInsumos` | Sin `OrdenConteo`, `Activo`, `AplicaA`, `VersionCatalogo` | El orden del conteo y la versión de catálogo no se pueden leer | Conteo |
| B-06 | `CatSucursales` | Solo `nombre`; faltan `RazonSocial`, `Estado`, `Activa` | Bajo (D3) | Transferencia |
| B-07 | `InvConteo`, `InvConteoLinea` | Sin `VersionCatalogo`, `EnviadoPor`, `RolCierre`, `ResueltaPor`; `capturadoPor` es el rol, no la persona; `del`/`al` son texto | Parcial: se pierde quién envió y con qué rol cerró | Revisión, Cierre |
| B-08 | `InvConteoHistorial` | Solo la columna JSON `historial`; sin `IdInsumo` ni `Rol` | Parcial | Cierre |
| B-09 | `colRef` | `SemanaPasada`, `Promedio4`, `Compras`, `Entradas`, `Salidas` por insumo no existen como lista. Se derivan de conteos cerrados anteriores (requiere B-02), de `raw_inv_compra_partida` y de `raw_inv_movimiento` por concepto. La spec no dice de dónde salen (UX02 §03: «ver Listas») | Bloquea alertas y «Excede lo disponible» | Conteo, Cierre |
| B-10 | Ajuste de harina | `TestalesSemana` y `RendimientoReal` marcados [C] por la spec. `raw_inv_masa_semana.bol` es el candidato para testales (PROTO lo muestra como «Testales 17 oz»; el JSON lo describe como «Bolsas»). `RendimientoReal` depende de B-01 | La tarjeta queda como «Ejemplo» | General › Existencias |
| B-11 | `pubInvExistencia` | La spec es una fila por insumo y almacén; `raw_inv_insumo` tiene un solo `idalmacen` por insumo | Medio: un insumo en dos almacenes no se representa | General › Existencias |
| B-12 | Orden de compra (PROTO v2) | `raw_inv_proveedor` no tiene correo de contacto; PROTO lo necesita para enviar la orden al aprobarla | Fuera de la spec; ver sección 6 | Fuera de UX02 |
| B-13 | `pubInvExistencia`, `pubInvMovimiento` (escritura) | **Resuelta por D4.** Recibir suma a `raw_inv_insumo.existencia` y registra CMP en `raw_inv_movimiento`; confirmar una transferencia registra TRS/TRE; «Registrar entrada» registra TRE o CMP y suma a la existencia (tabla 1.1). Queda como supuesto que transferencias y «Registrar entrada» también ajusten la existencia | Ninguno | Existencias, Movimientos, Conteo › Cierre |

Total: 13 brechas, 1 resuelta (B-13) y 12 abiertas.

## 5. Riesgos de datos y licencia

| ID | Riesgo | Fuente |
|---|---|---|
| R-01 | Las columnas de fecha que se filtran (`raw_inv_compra.fechaaplicacion`, `raw_inv_conteo_fisico.fecha`) no son llave ni `inc`, así que no están indexadas. UX02 §03 asume filtros delegables `Fecha >=` e índices. Con pocas filas por sucursal es tolerable; verificar antes de crecer. **Solicitud a backend-dev** (CLAUDE.md, reglas de listas, pide índices en sucursal, fecha operativa y estado): `estado` no está indexado en `raw_inv_orden_compra`, `raw_inv_conteo_semanal` ni `raw_inv_traspaso`, y tampoco `envia`/`recibe` ni `fechaaplicacion`/`fecha`; indexarlos | UX02 §03 «Fuentes»; `Deploy-Listas.ps1` líneas 53–54 |
| R-02 | Lista de pendientes [C] de la spec, tal cual y sin resolver: frecuencia del corte y retención por lista; confirmar fórmula de sugerida contra RN-21; unidades con decimales (criterio inicial) y las que quedan por validar con la sucursal (Chile seco, Bladoza, Bolsa de basura, Harina); cargar el Excel real de sucursales; umbrales de conteo (30 % y ×10) por validar con el corporativo; registro de masa por día o por turno y si una mezcla equivale a un bulto; opción A o B para transferencias entre sitios; origen de `TestalesSemana` y `RendimientoReal`; límite diario de escrituras (~90–120 por semana y sucursal) | UX02 §03 (comentarios `[C]` de cada bloque) |
| R-03 | El costo viaja en el mismo registro que el catálogo (`raw_inv_insumo.costopromedio`, `raw_inv_compra_partida.costo`, `raw_inv_conteo_fisico_partida.costo`, `raw_inv_traspaso_partida.precio`). Ocultarlo al Colaborador es solo visual: un usuario con permiso de lectura a la lista lo ve. Decisión de permisos de SharePoint pendiente | PROTO (CSS `data-dpzrol="col"`); instrucción del líder |
| R-04 | Licencia: no se detecta un conector premium en lo que usa DPZ-UX-02 (SharePoint y Notify). El aviso a la otra sucursal y a quien aprueba (PROTO, «en Power Automate») requiere Power Automate con conectores estándar (SharePoint, Outlook). Verificar que no pase por HTTP ni por conector premium. El sitio común con permisos por elemento (opción A de transferencias) funciona sin Dataverse | UX02 §03; PROTO «Enviar solicitud»; CLAUDE.md |
| R-05 | Los filtros con `in` (`OrdenId in colOrdenes.ID`) y los `LookUp`/`AddColumns` entre listas no son delegables. La spec lo declara [C] y se acepta con pocas órdenes abiertas y 89 insumos. No lo es sobre `raw_inv_movimiento` ni `raw_inv_compra_partida` sin filtrar primero por fecha o por `idcompra` | UX02 §03 «scrInventarios · Carga…»; CLAUDE.md (regla Power Fx) |
| R-06 | UX02 escribe `cerou` en `EstadosLineaConteo` (G13) y `cero` en `AlertaConteo`, en `InvConteoLinea.Alerta` y en el prototipo. Esta spec usa `cero` como valor guardado y como id del estado; la etiqueta visible es «Cero inusual» | UX02 §03 «Reglas de conteo…» y «Listas de captura»; PROTO `EST` |
| R-07 | UX02 §03 «galInv_Accesos» abre el diálogo con `locDlg = "crear"` pero el diálogo es visible con `locDlg = "orden"` (§03 «dialogo-orden»). Discrepancia de la spec; no se resuelve aquí | UX02 §03 |

## 6. Datos que usa el prototipo y que DPZ-UX-02 no cubre

PROTO tiene más pestañas que la spec: Tablero, Sugerida, Mezclas, Mermas, Recetas y Catálogos (`TABS_ALL`, líneas 747 y 1577–1578). Son comportamiento que la spec no define. Se registran aquí para decidir el alcance; `inventarios.md` no los especifica.

| Función del prototipo | Lista `raw_*` más cercana | Observación |
|---|---|---|
| Registro de mermas de insumo | `raw_inv_movimiento` (concepto MER, motivo en `referencia`) | Sin columna de evidencia (foto) |
| Registro de mermas de producto terminado | `raw_inv_merma_producto` (`fecha`, `producto`, `cantidad`, `referencia`) | Motivo y fotos van en `referencia` |
| Recetas y proveedores aprobados | `raw_app_receta_producto`, `raw_app_receta_ingrediente`, `raw_inv_proveedor` | Columna `c` = `_x0063_` |
| Orden sugerida (consumo de 15 días − conteo − órdenes en camino, ajuste ±10 %) | `raw_inv_insumo`, `raw_inv_orden_compra` (`origen`, `ajuste`), ventas del POS | No está en DPZ-UX-02 |
| Consumo teórico vs real (tolerancia ±2.5 %) | Ninguna definida | Fuera de la spec |
| Aprobación de órdenes (Por aprobar → Pendiente o Rechazada) | `raw_inv_orden_compra.estado` | Ver B-04 |
