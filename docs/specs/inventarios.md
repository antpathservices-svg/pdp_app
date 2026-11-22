# Inventarios y Compras

Spec funcional del módulo para la sucursal piloto (Guanajuato · Río Bravo, `idempresa` 1). Describe lo que el prototipo y DPZ-UX-02 **hacen**, no cómo construirlo en Power Apps.

| | |
|---|---|
| Módulo | `inventarios` · «Inventarios y Compras», grupo Operaciones (UX01, bloque «Datos del menú») |
| Pantallas | `scrInventarios` y 6 sub-pantallas: `scrInventarios_General`, `_ControlMasa`, `_Transferencia`, `_Conteo`, `_ConteoRevision`, `_ConteoCierre` (más el diálogo de orden de compra) |
| Fuente principal | DPZ-UX-02 v1.4 (23 oct 2026) |
| Fuente de comportamiento | Sub-app Inventarios del prototipo (`sub_INV.html`) donde la spec no dice |
| Datos | `sharepoint/productos.json`, traducción en `mapeo-listas.md` |
| Estado | Borrador para revisión por supervisor-evaluador |

## Convenciones de cita

- **UX02 §00–§04**: DPZ-UX-02. §00 Resumen, §01 Widgets nuevos, §02 Pantallas (con «Comportamiento» y «árbol de controles» por pantalla), §03 Power Fx (se cita por el título del bloque de código), §04 Checklist (`#n` = posición del ítem).
- **UX01**: DPZ-UX-01 (tokens, G01–G07, convención de nombres).
- **PROTO**: sub-app Inventarios del prototipo, por función o tarjeta. Solo se usa donde la spec no dice o para marcar una diferencia.
- **decisiones.md D1 a D5**: listas del Marketplace, Operador = Colaborador, una sola sucursal, inventarios y compras se capturan en la app, contraparte de transferencias desde `raw_app_sucursal`.

## 0. Decisiones aplicadas

- **D1.** Toda lista de la spec se traduce a una `raw_*` (ver `mapeo-listas.md`). Lo que no tiene equivalente es una brecha B-nn y la pantalla que depende de ella queda bloqueada para guardar.
- **D2.** Donde la spec dice «Operador» se lee **Colaborador** (`col`); «Supervisor de turno» se lee **Supervisor** (`sup`). Los cinco roles son `col`, `ger` (Gerente de sucursal), `sup`, `gop` (Gerente de operaciones) y `adm` (Administrador corporativo). La spec de inventarios solo menciona cuatro roles (Operador, Supervisor de turno, Gerente, Administrador corporativo); para `gop` se aplica el comportamiento del prototipo y se marca.
- **D3.** Una sola sucursal. No hay selector de sucursal, «Todas las sucursales» ni comparativos. Las columnas `Sucursal` de las listas de la spec se omiten (cada sitio tiene sus listas).
- **D4.** Existencias, compras, movimientos, conteos físicos, órdenes, transferencias y mezclas se capturan en la plataforma: todas las `raw_inv_*` son de **captura** y la app las escribe. Recibir una orden suma a `raw_inv_insumo.existencia` y registra el movimiento en `raw_inv_movimiento`. Esto sustituye la lectura «publicada desde el POS» de UX02 §03 «Fuentes» (resuelve P-7 y B-13).
- **D5.** En Transferencias la sucursal propia es fija (Río Bravo) y la contraparte se elige de `raw_app_sucursal`; es un dato de la solicitud, no un selector de contexto (resuelve P-1).
- **D6 (Marketplace v1.5).** Las brechas B-01 a B-08 quedaron cerradas con columnas y listas nuevas (`raw_inv_masa_mezcla`, `raw_inv_conteo_semanal_historial`, columnas nuevas en conteo, traspaso, orden de compra, insumo y sucursal). Detalle en `mapeo-listas.md`. Falta desplegar v1.5 en el sitio.
- **Regla del líder.** El Colaborador no ve costos.

## 1. Pantallas y navegación

```
scrMenu
  └─ scrInventarios                       (portada: 3 KPIs + 5 accesos)
       ├─ [Nueva orden de compra]   → diálogo G15 «Orden de compra» (se abre encima de la pantalla actual)
       ├─ [Inventario general]      → scrInventarios_General (G03: Existencias | Compras | Movimientos | Conteos)
       │                                  ├─ Existencias: [Ordenar] → diálogo de orden · [Recibir]
       │                                  ├─ Movimientos: [Nueva transferencia] → scrInventarios_Transferencia
       │                                  └─ Conteos: [Hacer inventario] → scrInventarios_Conteo
       ├─ [Control de Masa]         → scrInventarios_ControlMasa
       ├─ [Transferencia de Mercancías] → scrInventarios_Transferencia → (al enviar) General › Movimientos
       └─ [Conteo semanal]          → scrInventarios_Conteo
                                          ├─ [Revisar y enviar] → scrInventarios_ConteoRevision
                                          └─ [Revisar y cerrar] (Por revisar, sup o ger) → scrInventarios_ConteoCierre
```

Fuente: UX02 §03 «galInv_Accesos» (btnCard_Toque.OnSelect), «scrInventarios_General · Filtros…» (OnVolver), «btnTrf_Enviar.OnSelect», UX02 §02 Comportamiento «conteos» y «conteo»; PROTO acción `cie` (solo si `puedeCerrar`).

Retornos (botón de regreso del encabezado G01): `scrInventarios` → `scrMenu`; `scrInventarios_General` → `scrInventarios`; `_ControlMasa`, `_Transferencia`, `_Conteo` → `scrInventarios`; `_ConteoRevision` y `_ConteoCierre` → `scrInventarios_Conteo` (UX02 §02 maqueta, rótulo del header: «Conteo semanal»; PROTO `data-nav`).

Todas las navegaciones entre pantallas del módulo usan `ScreenTransition.None` (UX02 §03).

## 2. Pantallas

### 2.1 `scrInventarios` (portada)

Propósito: resumen de stock y accesos al módulo. Fuente: UX02 §02 árbol «inicio».

| Control | Contenido | Fuente |
|---|---|---|
| `cmpInv_Header` (G01 Módulo) | Logo, «Pizza Deprizza», botón de regreso | UX02 §02 árbol «inicio» |
| `cmpInv_Titulo` (G02, izquierda) | «Inventarios y Compras» / «Gestión de stock y proveedores» | UX02 §02 maqueta «inicio» |
| `galInv_Kpis` (G09, 3 por fila en tablet y escritorio, 2 en teléfono) | Stock crítico · Stock bajo · Órdenes por recibir | UX02 §03 «galInv_Kpis.Items» |
| `galInv_Accesos` (G04 Fila, 1 columna en teléfono, 2 en tablet y escritorio, alto 100) | 5 accesos | UX02 §03 «galInv_Accesos» |

- **Estados:** ninguno propio.
- **Cálculos:** los tres indicadores (ver 4.1).
- **Roles:** `ger`, `sup`, `gop`, `adm` ven todo. El Colaborador (PROTO): no ve los tres indicadores ni los accesos Nueva orden de compra, Control de Masa y Transferencia; ve Inventario general (pestañas limitadas) y Conteo semanal. Spec silente; decisión pendiente (pregunta P-3).
- **Datos:** `raw_inv_insumo` (lectura), `raw_inv_orden_compra` y `raw_inv_orden_compra_partida` (lectura de las Pendiente).
- **Widgets:** G01, G02, G04, G05, G09.

### 2.2 `scrInventarios_General`

Propósito: consulta del inventario en cuatro pestañas. Estructura común: G01 («Inventarios», regreso a `scrInventarios`), G02 («Inventario general», subtítulo «N insumos · K órdenes por recibir»), G03 con las cuatro pestañas (UX02 §03 «scrInventarios_General · Filtros…»; §02 árbol «general»).

#### Pestaña Existencias

| Control | Contenido | Fuente |
|---|---|---|
| `conExist_Atencion` (G10) + `galExist_Atencion` (G14) | Insumos Crítico o Bajo; botón Ordenar / En la orden / En pedido | UX02 §03 «scrInventarios · Carga…» |
| `conInvGeneral_Filtros` (G08) | `txtGen_Buscar` («Nombre del insumo»), `cbGen_Categoria`, `cbGen_Almacen`, `cbGen_Estado`, `btnGen_Limpiar` | UX02 §02 árbol «general» |
| `conInvGeneral_Ordenes` (G10) + `galInvGeneral_Ordenes` (G14, botón Recibir) | Órdenes Pendiente. Subtítulo «Captura de la plataforma · al recibir, la existencia sube» | UX02 §02 maqueta «general» |
| `conInvGeneral_Existencias` (G10) + tabla | Insumo, Categoría, Almacén, Existencia, Mín., Máx., Costo prom., Valor, Estado; subtítulo «N insumos · valor $X» | UX02 §02 maqueta «general» |
| `conInvGeneral_Harina` (G10) | Ajuste de rendimiento de harina (4 datos + nota + etiqueta «Ejemplo · pendiente de captura») | UX02 §03 «Ajuste de rendimiento de harina» |

- **Validaciones:** ninguna de captura. Recibir solo aplica a órdenes Pendiente.
- **Estados del insumo (G13):** Crítico, Bajo, En pedido, OK, Sobre máximo (ver 3.1).
- **Cálculos:** estado, cantidad sugerida, valor (existencia × costo promedio), ajuste de harina (4.1 a 4.4).
- **Roles:** Colaborador (PROTO): ve la pestaña Existencias sin columnas Costo prom. ni Valor, sin indicador de valor en el subtítulo y sin la tarjeta Órdenes por recibir. `ger`, `sup`, `gop`, `adm`: todo.
- **Datos:** `raw_inv_insumo`, `raw_inv_insumo_categoria`, `raw_inv_almacen`, `raw_inv_unidad` (lectura); `raw_inv_orden_compra`, `raw_inv_orden_compra_partida` (captura: Recibir escribe `estado`, `recibida`, `recibidaPor`); `raw_inv_insumo` (captura: Recibir suma `existencia`); `raw_inv_movimiento` (captura: movimiento CMP al recibir); `raw_inv_masa_semana` (lectura, ajuste de harina, BRECHA B-10).

#### Pestaña Compras

- Tres indicadores G09: «Compras en el punto de venta» (total histórico, detalle «Registro histórico»), «Comprado en octubre/en el mes» (suma de totales no cancelados, «N compras aplicadas») y «Proveedores» («Con compras en el mes»).
- Filtros G08: Proveedor (span 2) y Estado (Todas, Aplicadas, Canceladas).
- Tabla «Compras del punto de venta» (Folio, Fecha, Proveedor, Factura, Partidas, Subtotal, IVA, Total, Estado), «Toca una compra para ver sus partidas».
- Tabla «Partidas de la compra N» (Insumo, Cantidad, Costo, IVA, Importe, Almacén) con fila Total.
- **Estados:** Aplicada, Cancelada (G13).
- **Roles:** todos menos `col` (el Colaborador no ve esta pestaña según PROTO y no ve costos).
- **Datos (lectura):** `raw_inv_compra`, `raw_inv_proveedor`, `raw_inv_compra_partida`, `raw_inv_insumo`.
- Fuente: UX02 §02 maqueta y Comportamiento «compras»; §03 «Compras, movimientos y conteos».

#### Pestaña Movimientos

- Tarjeta «Transferencias de mercancía» (G10) con botón «Nueva transferencia» (Contorno S), tabla con Folio, Fecha, Envía → Recibe, Partidas, Total, Estado, Acción. La acción es el botón en línea «Confirmar envío» o «Confirmar recepción» (Primario S, con icono check) o el texto «Espera …».
- Filtros G08: buscar insumo (span 2), Concepto, Almacén.
- Tabla «Movimientos de inventario» (Fecha · hora, Insumo, Concepto, Cantidad con signo, Valor, Almacén, Referencia): ventas, compras, traspasos, mermas y ajustes, últimos 7 días.
- **Estados de transferencia:** Solicitada, Enviada, Recibida (G13).
- **Roles:** botones de transferencia solo para `sup` y `ger`; los demás ven el estado sin acción. Valor y costos ocultos al Colaborador (que además no ve esta pestaña, PROTO).
- **Datos:** `raw_inv_movimiento_concepto`, `raw_inv_insumo` (lectura); `raw_inv_movimiento` (lectura de los últimos 7 días y captura: salida TRS y entrada TRE al confirmar una transferencia); `raw_inv_insumo.existencia` (captura al confirmar); `raw_inv_traspaso`, `raw_inv_traspaso_partida` (captura).
- Fuente: UX02 §02 maqueta y Comportamiento «movs»; §03 «transferencias.fx».

#### Pestaña Conteos

- Botón primario M «Hacer inventario» (ícono clipboard-list), único elemento antes de la lista.
- Tabla «Inventarios físicos» (Folio, Fecha, Teórico, Físico, Diferencia, % del teórico, Insumos), «Toca un conteo para ver la diferencia por insumo».
- Tabla «Conteo N · fecha» (Insumo, Teórica, Física, Diferencia, Valor), «Existencia teórica del sistema contra el conteo físico».
- **Roles:** `col` ve la pestaña (PROTO) pero sin valores monetarios (regla del líder; PROTO no los oculta aquí, ver riesgo R-03 y pregunta P-4).
- **Datos (lectura):** `raw_inv_conteo_fisico`, `raw_inv_conteo_fisico_partida`, `raw_inv_insumo`.
- Fuente: UX02 §02 maqueta y Comportamiento «conteos».

### 2.3 Diálogo «Orden de compra» (G15 Formulario)

Se abre desde «Nueva orden de compra» (scrInventarios) o desde «Ordenar» / «En la orden» (General › Existencias). Panel blanco centrado, ancho `Resp(ancho − 2·Gutter, 720, 720)`, radio 16, sobre fondo `RGBA(45, 27, 0, 0.5)`.

| Control | Contenido | Fuente |
|---|---|---|
| `lblDialogo_Titulo` | Icono shopping-cart + «Orden de compra» (Bold 20/28) | UX02 §02 árbol «orden» |
| `lblDialogo_Descripcion` | «Los insumos que agregas con “Ordenar” se suman aquí. La orden queda pendiente hasta recibirla en Inventario general.» | UX02 §02 maqueta «orden» |
| `drpOrden_Proveedor` | Un proveedor por orden; solo nombre | UX02 §03 «Orden de compra…» |
| `galOrden_Lineas` | Por renglón: `drpOrdenLinea_Insumo`, `txtOrdenLinea_Cantidad` (Number, sufijo de unidad), `btnOrdenLinea_Quitar` (40 × 40), `lblOrdenLinea_Sugerida` | UX02 §02 árbol «orden» |
| `btnOrden_Agregar` | G06 Fantasma «Agregar insumo» | Ídem |
| `lblOrden_Error` | Tema.Error | Ídem |
| `conDialogo_Acciones` | `btnOrden_Cerrar` (Contorno), `btnOrden_Crear` (Primario, check), mitad y mitad | Ídem |

- **Validaciones:** ver INV-19 a INV-24 (proveedor, ≥ 1 renglón, insumo y cantidad > 0, insumo no repetido).
- **Estados de la orden:** Pendiente al crear; Recibida al recibir (UX02 §03 «OrdenesCompra»). El prototipo agrega Por aprobar y Rechazada (sección 9).
- **Roles:** la spec no restringe quién crea órdenes. PROTO oculta el acceso al Colaborador (pregunta P-3).
- **Datos (captura):** `raw_inv_orden_compra`, `raw_inv_orden_compra_partida`; (lectura) `raw_inv_proveedor`, `raw_inv_insumo`.
- **Widgets:** G15, G06 (Primario, Contorno, Fantasma), G08 no.

### 2.4 `scrInventarios_ControlMasa`

Propósito: registrar cuántas bolitas de masa salieron de cada mezcla. Fuente: UX02 §02 maqueta, árbol y Comportamiento «masa».

| Control | Contenido |
|---|---|
| `cmpMasa_Header` (G01 «Inventarios»), `cmpMasa_Titulo` (G02) | «Control de Masa» / «Bolitas obtenidas por mezcla · <fecha>» |
| `conMasa_Registro` (G10) | «Registro de mezclas», «10 mezclas · bolitas por tamaño»; ayuda «Anota cuántas bolitas de cada tamaño salieron de cada mezcla. Solo números enteros.» |
| `galMasa_Mezclas` | Galería tabla: encabezado Mezcla · 17 oz · 10 oz · 5 oz; 10 filas con `txtMasa_17`, `txtMasa_10`, `txtMasa_5` (Number); fila Total |
| `lblMasa_Error` | Tema.Error |
| `conMasa_Acciones` | `btnMasa_Limpiar` (Contorno, icono x), `btnMasa_Guardar` (Primario, icono check) |

- **Validaciones:** enteros ≥ 0; vacío válido (INV-33 a INV-36).
- **Cálculos:** Total por columna = suma de valores válidos.
- **Roles:** `col`, `ger`, `sup` capturan; `adm` solo lectura; `gop` solo lectura según PROTO (spec silente).
- **Datos:** captura en `raw_inv_masa_mezcla` (`fecha`, `mezcla`, `oz17`, `oz10`, `oz5`, `capturadoPor`, `capturadoEl`; llave `fecha` + `mezcla`; B-01 cerrada por D6). Al abrir se cargan las 10 filas vacías o las del día si ya se guardaron.
- **Notas:** el prototipo habla de «testales» y de un registro por captura con hora y usuario (tabla «Mezclas de hoy», sección 9); la spec habla de «bolitas» y de un registro por mezcla. [C] pendiente de la spec: un registro por día o por turno, y si una mezcla equivale a un bulto de harina.
- **Widgets:** G01, G02, G10, G06.

### 2.5 `scrInventarios_Transferencia`

Propósito: solicitar el envío de mercancía entre dos sucursales. Fuente: UX02 §02 maqueta, árbol y Comportamiento «trf».

| Control | Contenido |
|---|---|
| `conTrf_Sucursales` (G10) | «Sucursales»: la sucursal propia (Río Bravo) aparece fija; un indicador `Sentido` («Esta sucursal envía» / «Esta sucursal recibe») y un solo selector `drpTrf_Contraparte` con las sucursales de `raw_app_sucursal` (sin la propia). Sustituye a `drpTrf_Envia` y `drpTrf_Recibe` de UX02 (INV-37, D5) |
| `conTrf_Mercancia` (G10) | «Mercancía», «Total por renglón = cantidad × precio»; `btnTrf_Agregar` («Agregar renglón») |
| `galTrf_Partidas` | Tabla en tablet y escritorio (Cantidad, Unidad, Descripción, Precio individual, Total, quitar) o renglón apilado en teléfono; `txtTrf_Cantidad`, `drpTrf_Unidad`, `cmbTrf_Descripcion`, `txtTrf_Precio`, `lblTrf_Total`, `btnTrf_Quitar` |
| `lblTrf_TotalGeneral` | «Total de la transferencia» = suma de cantidad × precio |
| `conTrf_Enviar` (G10) | `lblTrf_Ayuda` («Es una solicitud: la sucursal que envía confirma el envío y la que recibe confirma la recepción.»), `lblTrf_Error`, `btnTrf_Cancelar`, `btnTrf_Enviar` («Enviar solicitud», icono send) |

- **Validaciones:** INV-37 a INV-41.
- **Estados:** la solicitud nace Solicitada; avanza a Enviada y Recibida desde General › Movimientos (3.3).
- **Roles:** `sup` y `ger` registran; `col` y `adm` solo lectura; `gop` solo lectura (PROTO).
- **Datos:** captura `raw_inv_traspaso`, `raw_inv_traspaso_partida`; lectura `raw_app_sucursal`, `raw_inv_insumo`, `raw_inv_unidad`.
- **Alcance (D3, D5):** la sucursal propia es fija y la contraparte se elige de `raw_app_sucursal`. Es un dato de la solicitud; no hay comparativos ni vistas entre sucursales. `raw_app_sucursal` trae `razonSocial`, `entidad` y `activa` (B-06 cerrada por D6): el selector de contraparte usa solo `activa` = Sí. Las filas de `raw_inv_traspaso_partida` se numeran con `renglon` y pueden llevar `idinsumo` (B-03 cerrada).
- **Notas del prototipo, no en la spec:** la otra sucursal recibe una notificación (Power Automate) al enviar, confirmar envío y confirmar recepción; la recepción pide folio de factura o remisión, fecha, quién recibió, evidencia fotográfica, partidas recibidas y comentarios (sección 9).
- **Widgets:** G01, G02, G10, G06.

### 2.6 `scrInventarios_Conteo` (resumen y captura por categorías)

Propósito: capturar el conteo físico semanal. Fuente: UX02 §02 maqueta, árbol y Comportamiento «conteo»; §03 «scrInventarios_Conteo…».

| Control | Contenido |
|---|---|
| `cmpCnt_Header` (G01 «Inventarios»), `cmpCnt_Titulo` (G02) | «Conteo semanal» / «Conteo físico por categorías» |
| `conCnt_Avance` (G10) con `cmpConteo_Estado` (G13) | «Avance del conteo», «Capturado por <nombre>»; `lblCnt_Avance` («34 de 89 insumos contados», número Bold 22/28); `conCnt_Barra` (fondo Tema.Grid, avance Tema.Marca, alto 8, radio 4); `lblCnt_Ayuda`; `conCnt_Acciones`: `btnCnt_Revisar` («Revisar y enviar», Contorno) y `btnCnt_Continuar` («Continuar», Primario, chevron-right), o `btnCnt_Cerrar` |
| `conCnt_Categorias` (G10) | «Categorías», «Mismo orden que el catálogo de insumos del corporativo»; `lblCnt_Aviso`; `galCnt_Categorias` |
| `btnCategoria` (G14 desplegable) | Nombre, «N de M insumos · K alertas», chevron |
| `galCategoria_Insumos` (G16) | Por insumo: `lblFilaConteo_Insumo`, `lblFilaConteo_Unidad` («Se cuenta en <unidad>»), `galFilaConteo_Alertas` (G13), `lblFilaConteo_Mensaje`, `txtFilaConteo_Cantidad` (con abreviatura), `btnFilaConteo_SinExistencia` |
| `conCnt_Dialogo` (G15 Confirmación) | «Confirma la cantidad» (alerta) o confirmación de «Sin existencia»; sin campo de nota |

- **Validaciones:** INV-47 a INV-51.
- **Estados del conteo:** Borrador, Por revisar, Cerrado, Corregido (3.2). **Estados de línea (G13):** Variación grande, Cero inusual, Posible error de dedo, Excede lo disponible, Resuelta, Sin existencia (3.4).
- **Cálculos:** avance, alertas y disponible (4.5, 4.6).
- **Roles:** ver 5.
- **Datos:** captura `raw_inv_conteo_semanal`, `raw_inv_conteo_semanal_linea` (con `conteoId` y `periodo`, B-02 cerrada por D6); lectura `raw_inv_insumo`, `raw_inv_insumo_categoria`, `raw_inv_unidad`; datos de referencia `colRef` derivados (BRECHA B-09).
- **Widgets:** G01, G02, G10, G13, G14, G15, G16, G06.

### 2.7 `scrInventarios_ConteoRevision`

Propósito: revisar lo que falta y enviar a revisión. Fuente: UX02 §02 maqueta, árbol y Comportamiento «conteoRev».

| Control | Contenido |
|---|---|
| G02 | «Revisión y envío» / «N de M insumos contados» |
| `conCntRev_Falta` (G10) + `galCntRev_Falta` (G14) | «Falta contar», «K insumos vacíos en J categorías»; una fila por categoría con faltantes; botón «Ir a la categoría» (Contorno) |
| `conCntRev_Alertas` (G10) + `galCntRev_Alertas` (G14) | «Alertas», «N líneas · se revisan al cerrar»; botón «Editar» |
| `conCntRev_Enviar` (G10) | `txtCntRev_Comentario` (multilínea, «Comentario final (opcional)», placeholder «Algo que deba saber quien revisa el conteo»), `lblCntRev_Ayuda`, `btnCntRev_Enviar` («Enviar a revisión», icono send) |

- **Validaciones:** el envío siempre está disponible mientras el rol pueda enviar y el conteo esté en Borrador; no exige conteo completo.
- **Estados:** Borrador → Por revisar.
- **Roles:** `col`, `ger`, `sup` envían; `gop` y `adm` leen.
- **Datos:** `raw_inv_conteo_semanal` y `raw_inv_conteo_semanal_linea` (captura), `raw_inv_insumo` (lectura).
- **Widgets:** G01, G02, G10, G13, G14, G15, G06.

### 2.8 `scrInventarios_ConteoCierre`

Propósito: resolver alertas, cerrar y corregir el conteo. Fuente: UX02 §02 maqueta, árbol y Comportamiento «conteoCie».

| Control | Contenido |
|---|---|
| G02 | «Cierre del conteo» / «Enviado el <fecha>, <hora>» |
| `galCntCie_Kpis` (G09) | «Insumos contados» (`86 de 89`, «3 quedaron vacíos»), «Valor del conteo» (`$`, «Cantidad × costo promedio»), «Alertas por resolver» (Tema.Error, «Bloquean el cierre») |
| `conCntCie_Alertas` (G10) + `galCntCie_Alertas` (G14 con dos acciones y líneas extra) | Por línea pendiente: estado G13, «Contado N u · semana pasada M u», cuenta «Disponible D u = inicial + compras + entradas − salidas»; botones Corregir, Aceptar o Registrar entrada. Resueltas: «Aceptada por <rol>» |
| `conCntCie_Comentario` (G10) | «Comentario del conteo», «Lo escribe quien envía el conteo» |
| `conCntCie_Estado` (G10) con `cmpConteo_Estado` | `lblCntCie_Ayuda`, `btnCntCie_Cerrar` («Cerrar conteo», icono lock, deshabilitado si hay pendientes), `btnCntCie_Corregir` («Corregir conteo») |
| `conCntCie_Historial` (G10) | «Historial de correcciones», «Cada corrección crea una versión nueva»; visible solo si hay versiones |
| `conCnt_Dialogo` (G15) | Corregir cantidad, Registrar entrada (tipo, cantidad, referencia), Corregir conteo cerrado (insumo, cantidad, motivo obligatorio) |

- **Validaciones:** INV-58 a INV-60.
- **Estados:** Por revisar → Cerrado → Corregido (3.2).
- **Roles:** edición solo `sup` y `ger`. «Registrar entrada» escribe `raw_inv_movimiento` (CMP o TRE) y `raw_inv_insumo.existencia` (D4; el ajuste de existencia es supuesto, P-10). Valor del conteo es un valor monetario: el Colaborador no lo ve (y no llega a esta pantalla, PROTO).
- **Datos:** `raw_inv_conteo_semanal`, `raw_inv_conteo_semanal_historial`, `raw_inv_conteo_semanal_linea` (captura); `raw_inv_insumo`, `raw_inv_compra_partida`, `raw_inv_movimiento` (lectura, para el disponible, BRECHA B-09); `raw_inv_movimiento` y `raw_inv_insumo.existencia` (captura al «Registrar entrada», D4; el ajuste de `existencia` es supuesto, P-10).
- **Widgets:** G01, G02, G09, G10, G13, G14, G15, G06.

## 3. Estados

### 3.1 Estado de un insumo (G13)

| Id | Etiqueta | Color del punto | Regla | Prioridad en la lista de atención |
|---|---|---|---|---|
| `critico` | Crítico | Tema.Error | existencia ≤ mínimo × 0.4 | 1 |
| `bajo` | Bajo | Tema.Aviso | existencia < mínimo | 2 |
| `pedido` | En pedido | Tema.Marca | cantidad por recibir > 0; se muestra **además** del estado de existencia | 3 |
| `ok` | OK | Tema.Exito | los demás | 4 |
| `exceso` | Sobre máximo | Tema.TextoSuave | existencia > máximo | 5 |

Fuente: UX02 §03 «Estados y reglas de inventario» (EstadosInventario, EstadoInsumo). Extensión del prototipo no definida en la spec: «Sin umbral» (mínimo, ideal y máximo en 0) y «Existencia negativa» (PROTO `estado`).

### 3.2 Conteo semanal

| Estado | Entra por | Quién edita líneas | Salidas |
|---|---|---|---|
| Borrador | Al abrir la pantalla de Conteo si no hay conteo de la semana y el rol captura | `col`, `ger`, `sup` | «Enviar a revisión» → Por revisar |
| Por revisar | `btnCntRev_Enviar` (guarda EnviadoEl, comentario) | `ger`, `sup` | «Cerrar conteo» (sin pendientes) → Cerrado |
| Cerrado | `btnCntCie_Cerrar` (guarda CerradoPor, CerradoEl, rol) | Nadie | «Corregir conteo» (`ger`, `sup`) → Corregido |
| Corregido | Corrección con motivo; versión + 1; fila en `raw_inv_conteo_semanal_historial` | Nadie (corrige `ger`, `sup`) | Otra corrección mantiene Corregido |

Fuente: UX02 §03 «Reglas de conteo…» (EstadosConteo, PuedeCapturar, PuedeEnviar, PuedeCerrar, PuedeCorregir) y «Revisión, cierre y corrección». Un solo conteo por semana (`Periodo` = año × 100 + semana ISO).

### 3.3 Transferencia

| Estado | Entra por | Acción siguiente | Quién la hace |
|---|---|---|---|
| Solicitada | `btnTrf_Enviar` | «Confirmar envío» → Enviada (registra la salida) | `sup`, `ger` de la sucursal que **envía** |
| Enviada | Confirmar envío (guarda EnviadaPor, EnviadaEl) | «Confirmar recepción» → Recibida (registra la entrada) | `sup`, `ger` de la sucursal que **recibe** |
| Recibida | Confirmar recepción (guarda RecibidaPor, RecibidaEl) | Ninguna | n/a |

Fuente: UX02 §03 «transferencias.fx» (btnTrf_Confirmar, lblTrf_Espera). La contraparte se elige de `raw_app_sucursal` (D5); su sucursal no necesita usar esta app para que la solicitud exista.

### 3.4 Línea de conteo (alertas, G13)

| Id | Etiqueta | Cuándo |
|---|---|---|
| `variacion` | Variación grande | |cantidad − semana pasada| / semana pasada > 30 % y diferencia ≥ 1 |
| `dedo` | Posible error de dedo | cantidad ≥ 10 × semana pasada o ≤ semana pasada / 10 |
| `cero` (G13 «Cero inusual») | Cero inusual | Sin existencia o cantidad 0, con semana pasada > 0 y promedio 4 semanas ≥ 1 |
| `disp` | Excede lo disponible | cantidad > disponible (calculado; no se guarda) |
| `resuelta` | Resuelta | El revisor la aceptó o corrigió |

Fuente: UX02 §03 «Reglas de conteo…» (UmbralVariacion = 0.30, FactorDedo = 10, AlertaConteo, EstadosLineaConteo). Umbrales por validar [C].

### 3.5 Orden de compra

Pendiente (al crear) → Recibida (al recibir). Fuente: UX02 §03 «Orden de compra…» y «scrInventarios_General · Filtros, recepción y tabla». Estados adicionales del prototipo (Por aprobar, Rechazada): sección 9.

## 4. Cálculos

### 4.1 Indicadores de scrInventarios

- Stock crítico = cantidad de insumos con estado `critico`.
- Stock bajo = cantidad de insumos con estado `bajo`.
- Órdenes por recibir = cantidad de órdenes con estado Pendiente.

### 4.2 Estado de un insumo

```
EstadoInsumo(existencia, minimo, maximo) =
  si existencia <= minimo * 0.4  -> critico
  si existencia <  minimo        -> bajo
  si existencia >  maximo        -> exceso
  si no                          -> ok
```

### 4.3 Cantidad sugerida

`sugerida = Max(stockideal − existencia − porRecibir, stockminimo)`. `porRecibir` = suma de `cantidad` de las líneas de órdenes Pendiente del insumo. [C] confirmar contra RN-21 (pedido sugerido con consumo proyectado) cuando haya consumo (UX02 §03 «CantidadSugerida»).

### 4.4 Ajuste de rendimiento de harina

```
pos  = existencia de la harina
desc = TestalesSemana / 33            (el POS descuenta 1 bulto por cada 33 testales)
real = TestalesSemana / RendimientoReal
corregida = pos + desc − real
```

Todos en bultos con un decimal. «Existencia corregida» en Tema.Error. Si `RendimientoReal` está vacío se muestra «Ejemplo · pendiente de captura». [C] origen de `TestalesSemana` (`RendimientoReal` se deriva de `raw_inv_masa_mezcla`) (UX02 §03 «Ajuste de rendimiento de harina»; BRECHA B-10).

### 4.5 Conteo

- Avance = líneas guardadas ÷ insumos activos del catálogo (89 en la semana 1).
- Disponible = semana pasada + compras + entradas − salidas (UX02 §03 «Disponible»).
- Valor del conteo = Σ cantidad × costo promedio (UX02 §02 maqueta «conteoCie»: «Cantidad × costo promedio»).
- Pendientes de cierre = líneas con alerta sin resolver, más líneas no «sin existencia» con cantidad > disponible (UX02 §03 «colPendientes»).

### 4.6 Validación de cantidad (ValidarCantidad)

Normaliza coma a punto. En orden: vacío; negativo; no numérico; más de dos decimales; decimales en unidad entera (según `raw_inv_unidad.dec`); > 99,999. Devuelve el mensaje o vacío si es válida (UX02 §03 «Reglas de conteo, masa y transferencias»).

### 4.7 Compras, movimientos y conteos físicos

- Comprado en el mes = Σ `total` de compras no canceladas del mes.
- Proveedores = proveedores distintos con compras no canceladas del mes.
- Cantidad de movimiento: signo y color por `cantidad` (< 0 Tema.Error, > 0 Tema.Exito).
- Diferencia de conteo físico = físico − teórico; % del teórico = diferencia ÷ teórico; valor = diferencia × costo (UX02 §02 maqueta «conteos»).

### 4.8 Transferencia

Total de renglón = cantidad × precio; total = suma de renglones (UX02 §03 «lblTrf_Total», «lblTrf_TotalGeneral»).

## 5. Qué ve cada rol

Leyenda: **E** captura o edita; **L** solo lectura; **—** no lo ve. Donde la spec no dice se anota PROTO (prototipo) y queda como pregunta abierta.

| Capacidad | `col` | `ger` | `sup` | `gop` | `adm` | Fuente |
|---|---|---|---|---|---|---|
| Indicadores y accesos de scrInventarios | — (PROTO) | L | L | L | L | PROTO CSS `col` |
| Ver los accesos «Nueva orden de compra», «Control de Masa» y «Transferencia» | — (PROTO) | sí | sí | sí | sí | PROTO CSS `col`; spec silente |
| Inventario general: Existencias y Conteos | L | L | L | L | L | PROTO `_tabsRol` |
| Inventario general: Compras y Movimientos | — (PROTO) | L | L | L | L | PROTO `_tabsRol` |
| Costos y valores (Costo prom., Valor, costos de compra, Valor del conteo, precios de transferencia) | — | L | L | L | L | Líder; PROTO |
| Crear orden de compra | — (PROTO) | E | E | E | E | Spec no restringe; PROTO |
| Recibir orden de compra | — | E | E | pendiente | pendiente | Spec no define rol (P-3) |
| Control de Masa: capturar | E | E | E | L (PROTO) | L | UX02 §00, §04 #25; PROTO `masaEd` |
| Transferencia: registrar y confirmar | L | E | E | L (PROTO) | L | UX02 §02 «trf»; PROTO `trfEd` |
| Conteo: capturar y enviar | E | E | E | L (PROTO) | L | UX02 §00, §03 «PuedeCapturar» |
| Conteo en Por revisar | L | E | E | L | L | UX02 §02 «conteo» |
| Conteo: resolver alertas, cerrar, corregir (scrInventarios_ConteoCierre) | — | E | E | L | L | UX02 §03 «PuedeCerrar», «PuedeCorregir»; acceso de lectura de `gop`/`adm` no definido (P-5) |

## 6. Datos por pantalla

Tipo: **Lectura** (en esa pantalla la app solo lee; por D4 la lista sigue siendo de captura y la escribe la app en otra pantalla o la carga el corporativo) o **Captura** (la escribe esa pantalla). Delegación: indica si el filtro principal es delegable contra SharePoint.

| Pantalla | Lista | Tipo | Filtro principal y delegación |
|---|---|---|---|
| scrInventarios y General › Existencias | `raw_inv_insumo` | Lectura; captura de `existencia` al Recibir (D4) | Sin filtro (≈ 89 filas) |
| | `raw_inv_movimiento` | Captura (movimiento CMP al Recibir) | Solo escritura |
| | `raw_inv_insumo_categoria`, `raw_inv_almacen`, `raw_inv_unidad` | Lectura | Sin filtro, catálogos pequeños |
| | `raw_inv_orden_compra` | Captura | `estado = "Pendiente"`: delegable; `estado` indexado (`idx`, D6) |
| | `raw_inv_orden_compra_partida` | Captura | Líneas de órdenes Pendiente (`id_orden in …`): **no delegable** [C] de la spec, aceptable con pocas órdenes abiertas |
| | `raw_inv_masa_semana` | Lectura | Última semana; BRECHA B-10 |
| Diálogo de orden | `raw_inv_orden_compra`, `raw_inv_orden_compra_partida` | Captura | Escribe 1 + N filas |
| | `raw_inv_proveedor` | Lectura | Sin filtro |
| General › Compras | `raw_inv_compra` | Lectura | `fechaaplicacion >= primer día del mes`: delegable; columna indexada (`idx`, D6) |
| | `raw_inv_compra_partida` | Lectura | `idcompra = …`: delegable; indexada (llave) |
| General › Movimientos | `raw_inv_movimiento` | Lectura y captura (TRS/TRE al confirmar transferencia, D4) | `fecha >= hoy − 7`: delegable; indexada (llave) |
| | `raw_inv_movimiento_concepto` | Lectura | Sin filtro |
| | `raw_inv_traspaso`, `raw_inv_traspaso_partida` | Captura | `envia`/`recibe` de la sucursal: delegable con `=`; `estado`, `envia`, `recibe` y `creada` indexadas (`idx`, D6); partida con llave (`id_traspaso`, `renglon`) |
| General › Conteos | `raw_inv_conteo_fisico`, `raw_inv_conteo_fisico_partida` | Lectura | `folio = …`: delegable, indexada; la lista de conteos sin filtro (`fecha` indexada, `idx`, D6) |
| scrInventarios_ControlMasa | `raw_inv_masa_mezcla` | Captura | `fecha = hoy`: delegable (llave); una escritura por mezcla |
| scrInventarios_Transferencia | `raw_inv_traspaso`, `raw_inv_traspaso_partida` | Captura | Escribe 1 + N filas |
| | `raw_app_sucursal` | Lectura | `activa = true`: delegable, indexada (`idx`) |
| scrInventarios_Conteo | `raw_inv_conteo_semanal` | Captura | `id_raw = "CS-<año>-<semana>"`: delegable, indexada |
| | `raw_inv_conteo_semanal_linea` | Captura | `conteoId = …`: delegable, llave (`conteoId`, `idinsumo`); `periodo` indexado; una escritura por cambio |
| | `raw_inv_insumo`, `raw_inv_insumo_categoria`, `raw_inv_unidad` | Lectura | Catálogo completo; `ordenConteo` y `activo` (B-05 cerrada); `activo` indexado |
| scrInventarios_ConteoCierre | `raw_inv_movimiento`, `raw_inv_insumo` | Captura (Registrar entrada: CMP o TRE; suma `existencia`: supuesto, P-10; D4) | Solo escritura |
| | `colRef` (SemanaPasada, Promedio4, Compras, Entradas, Salidas) | Lectura, derivada | **BRECHA B-09** |
| scrInventarios_ConteoRevision | `raw_inv_conteo_semanal` | Captura | Una fila: actualiza estado, comentario, enviadoEl |
| scrInventarios_ConteoCierre | `raw_inv_conteo_semanal`, `raw_inv_conteo_semanal_historial`, `raw_inv_conteo_semanal_linea` | Captura | Una fila de conteo; líneas y bitácora por `conteoId` |

Mapeo columna por columna y brechas: `mapeo-listas.md`.

## 7. Diseño

### 7.1 Tokens DPZ-UX-01

Fuente UX01 bloque «Tokens globales». Todos como `Tema.*`; ningún control con color o tamaño literal.

| Uso en Inventarios | Token |
|---|---|
| Fondo de pantalla | `Tema.Fondo` |
| Tarjetas, paneles, filas | `Tema.Superficie`, borde 2 px `Tema.Borde`, radio 12 (filas) o 16 (tarjetas) |
| Botón primario, avance de barra, «En pedido» | `Tema.Marca` |
| Texto naranja (títulos de diálogo, etiquetas de marca) | `Tema.TextoMarca` |
| Texto | `Tema.Texto`, `Tema.TextoSuave` |
| Fondo suave (botón presionado de Sin existencia, etiquetas «Ejemplo») | `Tema.SuperficieSuave`; hover `Tema.SuperficieHover`; presionado `Tema.SuperficiePresion` |
| Estados: Crítico, error, negativo | `Tema.Error` |
| Estados: Bajo, alertas de conteo | `Tema.Aviso` |
| Estados: OK, Recibida, Cerrado, positivo | `Tema.Exito` |
| Sobre máximo, Corregido | `Tema.TextoSuave` |
| Barra de avance (fondo) | `Tema.Grid` (nombre usado en UX02 §02 árbol «conteo»; no aparece en la lista de tokens de UX01: discrepancia, ver riesgos abiertos) |
| Fondo del diálogo | `RGBA(45, 27, 0, 0.5)` |
| Layout | `Gutter` = Resp(16, 24, 32); `MitadHueco` = Resp(6, 12, 16); `AnchoMax` 1024 |
| Tipografía | Segoe UI; TY-01 a TY-08 |

Tamaños de las maquetas (UX02 §02, 390 · 768 · 1366): encabezado G01 56 · 64 · 64; G03 60 · 76 · 84; relleno del cuerpo 24 · 40 · 48; indicador G09 118 · 136 · 136 (2 · 3 · 3 columnas); fila de acceso G04 100; tabla: encabezado 36, fila 40; G13 alto 24; G16: columna de cantidad 104 · 160 · 160 y de «Sin existencia» 48 · 166 · 166, campo 96 · 140; botones G06 S 32, M 40, L 48. Ancho útil del cuerpo = `Min(ancho − 2·Gutter, 1024)`.

### 7.2 Widgets por pantalla

G01–G07 vienen de UX01; G08 FilterBar, G09 KpiTile y G10 ChartCard vienen de DPZ-UX-05; G13 StatusBadge, G14 ListRow, G15 Dialog y G16 CountRow son nuevos de UX02 §01.

| Pantalla | Widgets |
|---|---|
| scrInventarios | G01, G02, G04 (Fila), G05, G09 |
| scrInventarios_General | G01, G02, G03, G05 (en KPIs), G06, G08, G09 (Compras), G10, G13, G14 (atención y órdenes), G15 (orden de compra) |
| Diálogo de orden | G15 (Formulario), G06 |
| scrInventarios_ControlMasa | G01, G02, G06, G10 |
| scrInventarios_Transferencia | G01, G02, G06, G10 |
| scrInventarios_Conteo | G01, G02, G06, G10, G13, G14 (categoría desplegable), G15 (Confirmación), G16 |
| scrInventarios_ConteoRevision | G01, G02, G06, G10, G13, G14, G15 |
| scrInventarios_ConteoCierre | G01, G02, G06, G09, G10, G13, G14, G15 |

`G07 UserChip` aparece dentro de G01 (UX01). G11 y G12 (Ventas) no se usan en este módulo.

Iconos nuevos de UX02 que hay que agregar a `IconosDpz`: `search`, `shopping-cart`, `clipboard-list`, `message-square`, `ban`, `send` (UX02 §03 «App › Formulas · Estados y reglas de inventario»).

## 8. Criterios de aceptación

Cada criterio es comprobable por el supervisor. «Lista» está en `trazabilidad.md`.

Los criterios marcados «[Condicionado a P-n]» o con BRECHA B-nn no se pueden dar por construidos hasta que se resuelva la pregunta o la brecha (estado «bloqueado» en `trazabilidad.md`).

### scrInventarios

| ID | Criterio | Fuente |
|---|---|---|
| INV-01 | Al abrir scrInventarios se cargan los insumos y las órdenes Pendiente y se calculan los tres indicadores. | UX02 §02 Comportamiento «inicio» (Abrir el módulo); §03 «scrInventarios · Carga…» (OnVisible) |
| INV-02 | Hay tres indicadores G09 en este orden: Stock crítico (detalle «En o bajo el 40 % del mínimo»), Stock bajo («Bajo el mínimo») y Órdenes por recibir («Pendientes de recepción»). Cada valor es el conteo de insumos en ese estado o de órdenes Pendiente. | UX02 §03 «galInv_Kpis.Items»; §02 árbol «inicio» (galInv_Kpis, 3 indicadores) |
| INV-03 | Hay cinco accesos G04 variante Fila, en este orden y con estos textos: Nueva orden de compra, Inventario general, Control de Masa, Transferencia de Mercancías y Conteo semanal. No hay ninguna otra tarjeta. | UX02 §03 «Estados y reglas de inventario» (AccesosInventario); §04 #13 |
| INV-04 | Nueva orden de compra abre el diálogo de orden (vacío o con lo ya agregado). Inventario general, Control de Masa, Transferencia de Mercancías y Conteo semanal navegan a su pantalla sin transición. El botón de regreso del encabezado (G01) lleva a scrMenu. Discrepancia de la spec registrada (R-G): btnCard_Toque usa locDlg = «crear» pero el diálogo se muestra con locDlg = «orden». | UX02 §03 «galInv_Accesos» (btnCard_Toque.OnSelect); §02 árbol «inicio» (cmpInv_Header.OnVolver) |
| INV-05 | scrInventarios no muestra la lista de insumos que requieren atención; esa lista vive en Inventario general › Existencias. | UX02 §02 árbol «inicio» (última línea); §04 #17 |

### scrInventarios_General › Existencias

| ID | Criterio | Fuente |
|---|---|---|
| INV-06 | Un insumo con existencia sobre el máximo muestra «Sobre máximo» y no entra en Insumos que requieren atención. | UX02 §02 Comportamiento «general»; §04 #10 |
| INV-07 | Si el insumo no tiene umbrales (mínimo, ideal y máximo en 0), el estado es «Sin umbral»; si además su existencia es negativa, «Existencia negativa» (cuenta como crítico). Regla del prototipo; la spec no la define. Condicionado a P-8 (decisión pendiente del líder). | PROTO funciones `sinUmbral` y `estado`; UX02 no la cubre |
| INV-08 | Inventario general tiene un encabezado G01 con retorno a scrInventarios, un título G02 y un G03 de cuatro pestañas: Existencias, Compras, Movimientos, Conteos. Tocar una pestaña solo cambia el contenido debajo del G03. | UX02 §03 «scrInventarios_General · Filtros…» (cmpInvGeneral_Pestanas); §02 Comportamiento «general»; §04 #9 |
| INV-09 | Insumos que requieren atención lista los insumos Crítico o Bajo, críticos primero y luego bajos, cada grupo por descripción. Cada fila muestra título, estado (G13), «En pedido» si tiene orden Pendiente, y «Existencia N u · mínimo M u». | UX02 §03 «galExist_Atencion.Items», «lblFila_Detalle»; §02 Comportamiento «general» |
| INV-10 | El botón de cada fila de atención tiene tres estados: «En pedido» (deshabilitado) si hay cantidad por recibir; «En la orden» si el insumo ya está en el borrador; «Ordenar» en los demás casos. | UX02 §03 «btnFila_Accion.Text / DisplayMode»; §04 #3 |
| INV-11 | Ordenar suma el insumo, con su cantidad sugerida, a la orden en curso, abre el diálogo y cambia el botón de esa fila a «En la orden». Tocar «En la orden» abre el diálogo para revisar. | UX02 §03 «btnFila_Accion.OnSelect»; §02 Comportamiento «orden»; §04 #17 |
| INV-12 | Cantidad sugerida = Max(stock ideal − existencia − por recibir, stock mínimo). Nunca es menor que el mínimo. | UX02 §03 «CantidadSugerida» ([C] confirmar contra RN-21); §04 #4 |
| INV-13 | Si no hay insumos Crítico ni Bajo, se muestra el mensaje de lista vacía (lblExist_SinPendientes) en lugar de la tarjeta de filas. | UX02 §03 «Lista vacía» |
| INV-14 | La tarjeta Órdenes por recibir solo se ve si hay órdenes Pendiente. Cada fila muestra «OC-nnnn · Proveedor», estado «En pedido», sus insumos con cantidad y unidad y «creada el d mmm», de la más antigua a la más reciente, con el botón Recibir. | UX02 §03 «scrInventarios_General · Filtros, recepción y tabla»; §02 Comportamiento «general» (Sin órdenes pendientes) |
| INV-15 | Recibir marca la orden como Recibida (`estado`, `recibida` con fecha y hora, `recibidaPor`) y, por cada renglón, suma la cantidad a `raw_inv_insumo.existencia` y registra en `raw_inv_movimiento` una entrada de concepto CMP (cantidad positiva, costo = costo promedio del insumo, almacén del insumo, referencia «Recepción OC-nnnn · proveedor»). Resta lo mismo de «por recibir», recalcula el estado del insumo y muestra un aviso de éxito «Recibida la orden OC-nnnn». | UX02 §03 «btnFila_Accion.OnSelect» (Recibir); §04 #6, #18; decisiones.md D4 (la app escribe existencia y movimientos); PROTO recepción de orden (movimiento `idconcepto` CMP) (columnas `recibida` y `recibidaPor`: B-04 cerrada por D6) |
| INV-16 | La tabla de existencias se filtra al instante y en memoria por: texto en el nombre, Categoría, Almacén y Estado (selección múltiple). La lista de Estado no incluye «En pedido». Limpiar filtros restablece los cuatro controles. El filtro usa G08. | UX02 §03 «galInvGeneral_Existencias.Items», «cbGen_Estado.Items», «btnGen_Limpiar»; §02 Comportamiento «general» |
| INV-17 | La tabla de existencias muestra Insumo, Categoría, Almacén, Existencia con unidad, Mín., Máx., Costo prom., Valor y Estado (G13), ordenada por descripción. Almacén, Mín. y Valor aparecen desde tablet; Categoría, Máx. y Costo prom. solo en escritorio. Debajo, la línea «Fuente: …». | UX02 §03 «Columnas por tamaño»; §02 maqueta «general» (conInvGeneral_Existencias, lblTabla_Fuente); §04 #8, #9 |
| INV-18 | La tarjeta Ajuste de rendimiento de harina muestra cuatro datos en bultos: Existencia en el POS = existencia de la harina; Descontado por el POS = testales de la semana ÷ 33; Consumo real = testales ÷ rendimiento real; Existencia corregida = existencia POS + descontado − consumo real (en Tema.Error). Mientras no exista el rendimiento real muestra la etiqueta «Ejemplo · pendiente de captura». | UX02 §03 «Ajuste de rendimiento de harina»; §04 #12; PROTO «Ajuste de rendimiento de harina» (regla del cliente: 1 bulto cada 33 testales) |

### Diálogo Orden de compra

| ID | Criterio | Fuente |
|---|---|---|
| INV-19 | El diálogo de orden se abre desde Nueva orden de compra o desde Ordenar. Muestra título «Orden de compra», un solo proveedor por orden, renglones (insumo y cantidad con unidad) y los botones Cerrar y Crear orden. Cada renglón muestra «Sugerida N u · existencia E · ideal I». | UX02 §02 Comportamiento «orden», árbol «orden»; §03 «Orden de compra con varios insumos (G15)» |
| INV-20 | Agregar insumo agrega un renglón vacío; al elegir el insumo propone la cantidad sugerida; un insumo no se puede repetir (aviso «Ese insumo ya está en la orden.»); Quitar elimina el renglón. | UX02 §03 «drpOrdenLinea_Insumo.OnChange», «btnOrden_Agregar», «btnOrdenLinea_Quitar»; §02 Comportamiento «orden» |
| INV-21 | El selector de proveedor muestra solo el nombre del proveedor, ordenado por nombre. No se muestra RFC, cuenta bancaria ni datos de pago. | UX02 §03 «drpOrden_Proveedor.Items»; §04 #7 |
| INV-22 | Crear orden no guarda y muestra el error en lblOrden_Error (Tema.Error) cuando: no hay proveedor («Selecciona un proveedor.»); no hay renglones («Agrega al menos un insumo.»); algún renglón no tiene insumo o su cantidad es ≤ 0 («Revisa los renglones: insumo y cantidad mayor a 0.»). Se valida en ese orden. | UX02 §03 «btnOrden_Crear.OnSelect»; §04 #5 |
| INV-23 | Crear orden válida guarda la orden con estado Pendiente (proveedor, creación y usuario) y un renglón por insumo (insumo, cantidad, unidad), vacía el borrador, recarga indicadores y órdenes, cierra el diálogo y muestra «Orden creada». | UX02 §03 «btnOrden_Crear.OnSelect»; §02 Comportamiento «orden»; §04 #18 |
| INV-24 | Cerrar o tocar el fondo cierra el diálogo y conserva la orden en curso (colOrdenBorrador). | UX02 §02 Comportamiento «orden»; §03 «btnOrden_Cerrar.OnSelect»; §04 #18 |

### scrInventarios_General › Compras

| ID | Criterio | Fuente |
|---|---|---|
| INV-25 | Al abrir Compras se muestran las compras del mes en curso y queda seleccionada la más reciente no cancelada. Tres indicadores G09: Compras en el punto de venta (total histórico), Comprado en el mes (suma de totales no cancelados) y Proveedores (distintos con compras en el mes). | UX02 §03 «Compras, movimientos y conteos»; §02 Comportamiento «compras» |
| INV-26 | Los filtros Proveedor y Estado (Todas, Aplicadas, Canceladas) filtran la tabla. Las compras canceladas solo se ven al elegir Canceladas o Todas. | UX02 §02 Comportamiento «compras» (Elegir Proveedor o Estado); §03 «galCompras_Lista.Items» |
| INV-27 | Tocar una compra carga sus partidas en la tarjeta «Partidas de la compra N» (insumo, cantidad, costo, IVA, importe, almacén) con una fila Total. Debajo de cada tabla se cita su fuente. | UX02 §02 Comportamiento «compras», maqueta «compras»; §03 «galCompras_Partidas.Items»; §04 #9 |

### scrInventarios_General › Movimientos (incluye transferencias abiertas)

| ID | Criterio | Fuente |
|---|---|---|
| INV-28 | Movimientos muestra los movimientos de los últimos 7 días, más recientes primero, con filtros de búsqueda de insumo, Concepto y Almacén. La cantidad lleva signo: + en Tema.Exito y − en Tema.Error, con unidad. | UX02 §03 «Movimientos de los últimos 7 días», «lblMov_Cantidad»; §02 Comportamiento «movs» |
| INV-29 | La tarjeta Transferencias de mercancía lista las transferencias de la sucursal (folio, fecha, Envía → Recibe, partidas, total, estado G13, acción) con el botón «Nueva transferencia». Una transferencia que espera a la otra sucursal muestra «Espera el envío de …» o «Espera la recepción en …», sin botón. Tocar una transferencia despliega sus partidas y las fechas de solicitud, envío y recepción. | UX02 §02 Comportamiento «movs»; §03 «lblTrf_Espera»; maqueta «movs» |
| INV-30 | En Movimientos, el botón en línea de una transferencia dice «Confirmar envío» y pasa Solicitada → Enviada si la sucursal piloto es la que envía; dice «Confirmar recepción» y pasa Enviada → Recibida si es la que recibe. Cada confirmación guarda quién y cuándo (`enviadaPor`/`enviada` o `recibidaPor`/`recibida`) y, por cada partida, registra en `raw_inv_movimiento` la salida (concepto TRS, cantidad negativa) al confirmar el envío o la entrada (concepto TRE, cantidad positiva) al confirmar la recepción, con costo = precio de la partida y referencia «Transferencia T-nnnn · a <sucursal>» o «· de <sucursal>», y ajusta `raw_inv_insumo.existencia` en el mismo sentido (supuesto, P-10: D4 lo dice solo para Recibir orden). | UX02 §02 Comportamiento «movs»; §03 «btnTrf_Confirmar»; maqueta «movs»; decisiones.md D4; PROTO confirmación de transferencia (`idconcepto` TRS/TRE) |

### scrInventarios_General › Conteos

| ID | Criterio | Fuente |
|---|---|---|
| INV-31 | Conteos lista los inventarios físicos (folio, fecha, teórico, físico, diferencia = físico − teórico, % del teórico, insumos); el más reciente queda seleccionado. Tocar un conteo carga la diferencia por insumo (teórica, física, diferencia, valor = diferencia × costo), ordenada por valor, la mayor pérdida primero. La fuente se cita bajo cada tabla. | UX02 §02 Comportamiento «conteos»; §03 «galConteos_Detalle.Items» (orden Valor ascendente; el texto de Comportamiento dice «de mayor a menor valor») |
| INV-32 | Antes de la lista, Conteos solo muestra el botón primario «Hacer inventario». No muestra la semana ni el estado del conteo semanal. El botón navega a scrInventarios_Conteo y al volver regresa a esta pestaña. | UX02 §02 Comportamiento «conteos»; §04 #19 |

### scrInventarios_ControlMasa

| ID | Criterio | Fuente |
|---|---|---|
| INV-33 | Control de Masa muestra una tabla con 10 filas de mezcla (1 a 10) y columnas 17 oz, 10 oz y 5 oz, y una fila Total que suma cada columna con los valores válidos. Subtítulo «Bolitas obtenidas por mezcla» con la fecha. | UX02 §02 maqueta «masa»; §03 «scrInventarios_ControlMasa» (lblMasa_Total17); §04 #23 |
| INV-34 | Cada celda acepta solo enteros ≥ 0; vacío es válido. Al salir de una celda inválida se marca con borde Tema.Error y debajo aparece «Mezcla N · X oz: solo números enteros.» (o «no puede ser negativo»). | UX02 §02 Comportamiento «masa»; §03 «ValidarEntero», «lblMasa_Error» |
| INV-35 | Guardar no guarda y avisa si hay celdas inválidas («Corrige las celdas marcadas en rojo.») o si no hay ninguna mezcla capturada («Captura al menos una mezcla.»). Si pasa, guarda en `raw_inv_masa_mezcla` una fila por mezcla capturada (`fecha` de hoy, `mezcla`, `oz17`, `oz10`, `oz5`, `capturadoPor`, `capturadoEl`; llave `fecha` + `mezcla`, un registro por día según C-8) y muestra «Control de Masa guardado». Limpiar vacía las 10 filas sin guardar. | UX02 §02 Comportamiento «masa»; §03 «btnMasa_Guardar.OnSelect» |
| INV-36 | Roles: Colaborador, Supervisor y Gerente de sucursal capturan; Administrador corporativo solo lee. Gerente de operaciones: la spec no lo dice; el prototipo le da solo lectura. | UX02 §00 Resumen, §04 #25; PROTO `masaEd = !CORP(rol)` |

### scrInventarios_Transferencia

| ID | Criterio | Fuente |
|---|---|---|
| INV-37 | Transferencia fija la sucursal propia (Guanajuato · Río Bravo) como uno de los dos extremos: el usuario indica con un indicador si la propia envía o recibe, y hay un solo selector, el de la contraparte, que se llena de `raw_app_sucursal` (solo `activa` = Sí, sin incluir la propia). La contraparte es un dato de la solicitud, no un selector de contexto ni un comparativo. Envía y Recibe se guardan como texto en la transferencia. | UX02 §02 Comportamiento «trf»; §03 «btnTrf_Enviar.OnSelect»; decisiones.md D3, D5 |
| INV-38 | En cada renglón (cantidad, unidad, descripción, precio individual, total, quitar), elegir una descripción del catálogo llena la unidad con la presentación y propone el precio con el costo promedio de la sucursal; ambos se pueden cambiar. Agregar renglón añade uno vacío con unidad «Pieza». | UX02 §02 Comportamiento «trf»; §03 «cmbTrf_Descripcion.OnChange» |
| INV-39 | El total del renglón = cantidad × precio y el total de la transferencia = suma de los renglones; ambos se actualizan al escribir. | UX02 §02 Comportamiento «trf»; §03 «lblTrf_Total», «lblTrf_TotalGeneral»; §04 #24 |
| INV-40 | Enviar solicitud valida que la contraparte esté elegida («Elige la sucursal que envía y la que recibe.»), que sea distinta de la propia («Deben ser sucursales distintas.») y que haya al menos un renglón; «Una de las dos debe ser tu sucursal» se cumple por construcción. Si pasa, crea la transferencia en estado Solicitada (`creadaPor`, `creada`) con sus renglones (`renglon` 1 a n, `idinsumo` si el artículo viene del catálogo) y lleva a General › Movimientos. | UX02 §03 «btnTrf_Enviar.OnSelect»; §02 Comportamiento «trf» |
| INV-41 | Solo el Supervisor y el Gerente de sucursal registran y confirman transferencias. Colaborador y Administrador corporativo las ven en solo lectura (botón deshabilitado). Gerente de operaciones: la spec no lo dice; el prototipo le da solo lectura. | UX02 §02 Comportamiento «trf» (gobernanza §5), §03 «PuedeTransferir»; PROTO `trfEd` |

### scrInventarios_Conteo

| ID | Criterio | Fuente |
|---|---|---|
| INV-42 | Al abrir Conteo se busca el conteo de la semana ISO en curso. Si no existe y el rol puede capturar, se crea en estado Borrador, versión 1 (`capturadoPersona`, `capturadoPor` con el rol, `versionCatalogo`). Si no puede capturar y no existe, no se crea. | UX02 §02 Comportamiento «conteo»; §03 «scrInventarios_Conteo · Categorías desplegables y G16» (OnVisible) |
| INV-43 | La tarjeta Avance del conteo muestra la etiqueta de estado (G13), «N de M insumos contados» (N = líneas guardadas, M = insumos del catálogo con `activo` = Sí), una barra de avance (alto 8, radio 4) y «Quedan K insumos vacíos. Puedes enviar el conteo aunque falten.» o «Todo contado.». No hay indicadores Contado, En curso ni Pendiente: la línea vacía es la que falta. | UX02 §02 maqueta y árbol «conteo»; §03 «lblCnt_Ayuda»; §04 #16, #21 |
| INV-44 | Hay una fila tocable por categoría, en el orden del catálogo (`raw_inv_insumo_categoria.orden`; insumos por `ordenConteo`), con «N de M insumos» y el número de alertas. Tocarla despliega debajo la tabla de sus insumos; tocarla otra vez la cierra; solo una está abierta a la vez. No hay pantalla por sección ni botón «Abrir». | UX02 §03 «galCnt_Categorias.Items», «btnCategoria.OnSelect»; §02 Comportamiento «conteo»; §04 #14, #15 |
| INV-45 | Continuar abre la primera categoría que tenga insumos vacíos y lleva el foco al primer insumo vacío. | UX02 §03 «btnCnt_Continuar.OnSelect»; §02 Comportamiento «conteo» |
| INV-46 | Cada fila de insumo (G16) muestra el nombre del catálogo (no editable), «Se cuenta en <unidad>», un campo de cantidad con la abreviatura de la unidad y el botón «Sin existencia». Nunca muestra la existencia del sistema ni el consumo esperado. | UX02 §01 G16 CountRow; §03 «G16 · fila de la tabla» |
| INV-47 | Al salir del campo se valida. No guarda y marca la fila en Tema.Error con el mensaje bajo el insumo si la cantidad: está vacía («Escribe la cantidad o toca Sin existencia.»), es negativa («La cantidad no puede ser negativa.»), no es número («Escribe solo números.»), tiene más de dos decimales («Usa máximo dos decimales.»), tiene decimales en una unidad entera («Se cuenta en enteros, sin decimales.») o supera 99,999 («La cantidad no es válida.»). La coma decimal se acepta como punto. | UX02 §03 «ValidarCantidad»; §02 Comportamiento «conteo»; §04 #20 |
| INV-48 | Una cantidad válida sin alerta se guarda sola al salir del campo (una fila de `raw_inv_conteo_semanal_linea` por insumo y conteo: `conteoId`, `periodo`, `idinsumo`, `cantidad`, `sinExistencia`, `alerta`, `resuelta` = No, `capturadoPor` con el rol y `capturadoPersona`); Enter pasa al siguiente insumo. | UX02 §02 Comportamiento «conteo»; §03 «txtFilaConteo_Cantidad.OnChange», «btnCnt_Guardar» |
| INV-49 | Si hay alerta se abre un diálogo G15 «Confirma la cantidad» sin campo de nota: Corregir regresa al campo; Confirmar guarda con la alerta. Alertas: «dedo» si la cantidad es ≥ 10× o ≤ 1/10 de la semana pasada (con semana pasada > 0); «variacion» si la diferencia con la semana pasada es > 30 % y ≥ 1 unidad; «cero» si la cantidad es 0 y el insumo tuvo semana pasada > 0 y promedio de 4 semanas ≥ 1. Umbrales por validar [C]. | UX02 §03 «AlertaConteo», «UmbralVariacion», «FactorDedo»; §02 Comportamiento «conteo»; §04 #20 |
| INV-50 | Sin existencia siempre abre G15 de confirmación, sin justificación. Si el insumo normalmente tiene existencia, lo dice y guarda la alerta «Cero inusual». Con el cero confirmado el botón queda presionado; tocarlo otra vez borra la línea y deja el insumo vacío. | UX02 §02 Comportamiento «conteo»; §03 «btnFilaConteo_SinExistencia.OnSelect»; §01 G16 |
| INV-51 | Una cantidad mayor a lo disponible (disponible = semana pasada + compras + entradas − salidas) se guarda y muestra «Excede lo disponible» (G13 en Tema.Error). No bloquea el envío; el Supervisor la resuelve al cerrar. No se guarda en la línea: se calcula. | UX02 §03 «Disponible», «EstadosLineaConteo»; §02 Comportamiento «conteo»; §04 #22 |
| INV-52 | Con el conteo en Por revisar, el Colaborador lo ve en solo lectura; el Supervisor y el Gerente ven «Revisar y cerrar». Administrador corporativo siempre lee. En Cerrado o Corregido nadie captura. | UX02 §02 Comportamiento «conteo»; §03 «PuedeCapturar» |
| INV-53 | Matriz de roles del conteo: Colaborador captura y envía; Supervisor y Gerente de sucursal capturan, revisan, cierran y corrigen; Administrador corporativo solo lee. Gerente de operaciones: la spec no lo menciona; el prototipo le da solo lectura (igual que a Administrador corporativo). | UX02 §00 Resumen; §03 «Permisos»; §04 #25; PROTO `puedeCapturar`, `esRevisor` |

### scrInventarios_ConteoRevision

| ID | Criterio | Fuente |
|---|---|---|
| INV-54 | Revisión y envío muestra «N de M insumos contados» y la tarjeta Falta contar: una fila por categoría con faltantes («Faltan K: tres nombres…») y el botón «Ir a la categoría». El envío sigue disponible aunque falten. | UX02 §02 Comportamiento «conteoRev»; maqueta «conteoRev»; §04 #21 |
| INV-55 | La tarjeta Alertas lista las líneas con alerta (insumo, estado G13, categoría y «Contado N u» o «Sin existencia») con el botón Editar; las alertas se resuelven al cerrar. | UX02 §02 maqueta «conteoRev» (conCntRev_Alertas) |
| INV-56 | Hay un solo comentario final, opcional, encima del botón «Enviar a revisión». Enviar pide confirmación G15 que indica cuántos insumos quedan vacíos; el botón solo está activo si el rol puede enviar. Al confirmar, el conteo pasa a Por revisar y se guardan quién (`enviadoPor`), cuándo (`enviadoEl`) y el comentario. Desde ahí el Colaborador no puede editarlo. | UX02 §02 Comportamiento «conteoRev»; §03 «btnCntRev_Enviar», «PuedeEnviar»; §04 #21; columnas `enviadoPor`, `enviadoEl` (B-07 cerrada por D6) |

### scrInventarios_ConteoCierre

| ID | Criterio | Fuente |
|---|---|---|
| INV-57 | Cierre del conteo muestra tres indicadores G09: Insumos contados («86 de 89», «3 quedaron vacíos»), Valor del conteo (cantidad × costo promedio) y Alertas por resolver («Bloquean el cierre»). Muestra además el comentario del conteo («Sin comentario.» si no hay) y la fecha y hora del envío. | UX02 §02 maqueta «conteoCie»; §03 «lblCntCie_Comentario» |
| INV-58 | Una línea es pendiente si tiene alerta sin resolver, o si no es «sin existencia» y su cantidad excede lo disponible. Las alertas de variación, cero o error de dedo tienen «Aceptar» (la marca resuelta con «Aceptada por <rol>» y `resueltaPor`) y «Corregir» (pide la cantidad correcta). La línea que excede lo disponible tiene «Registrar entrada» (captura la transferencia o la compra faltante con referencia) y «Corregir»; se resuelve cuando deja de exceder. Cada fila muestra la cuenta del disponible. «Registrar entrada» pide tipo (Transferencia de entrada o Compra sin orden previa), cantidad > 0 y referencia obligatoria (folio de la transferencia o de la factura); escribe en `raw_inv_movimiento` una entrada de concepto TRE (transferencia) o CMP (compra) y suma la cantidad a `raw_inv_insumo.existencia` (supuesto, P-10). | UX02 §02 Comportamiento «conteoCie»; §03 «colPendientes», «btnCntCie_Aceptar», «btnCntCie_Entrada» ; decisiones.md D4; PROTO «Registrar entrada faltante» (tipos traspaso y compra) (BRECHA B-09) |
| INV-59 | Cerrar conteo está activo solo si el rol es Supervisor o Gerente de sucursal, el conteo está Por revisar y no hay pendientes. Los insumos vacíos no bloquean y quedan como no contados. Al cerrar pasa a Cerrado y guarda quién (`cerradoPor`), cuándo (`cerradoEl`) y con qué rol (`rolCierre`). Sin pendientes dice «Todo resuelto.»; con pendientes «Resuelve N alertas para cerrar.». | UX02 §02 Comportamiento «conteoCie»; §03 «btnCntCie_Cerrar», «PuedeCerrar»; maqueta «conteoCie»; columna `rolCierre` (B-07 cerrada por D6) |
| INV-60 | Corregir conteo, en un conteo Cerrado o Corregido y solo para Supervisor y Gerente de sucursal, pide insumo, cantidad y motivo obligatorio («El motivo es obligatorio.»). Crea una versión nueva (versión + 1), pasa el conteo a Corregido y agrega una fila a `raw_inv_conteo_semanal_historial` (`conteoId`, `version`, `idinsumo`, `antes`, `despues`, `motivo`, `por`, `el`, `rol`). El historial se muestra solo si hay versiones. | UX02 §02 Comportamiento «conteoCie»; §03 «btnDlg_GuardarCorreccion.OnSelect», «PuedeCorregir»; §04 #26; lista `raw_inv_conteo_semanal_historial` (B-08 cerrada por D6) |

### Transversales (todas las pantallas)

| ID | Criterio | Fuente |
|---|---|---|
| INV-61 | El estado de un insumo se calcula así: Crítico si existencia ≤ mínimo × 0.4; Bajo si existencia < mínimo; Sobre máximo si existencia > máximo; OK en los demás casos. Se evalúa en ese orden. | UX02 §03 «Estados y reglas de inventario» (EstadoInsumo, UmbralCritico); §04 #1 |
| INV-62 | Los totales de Stock crítico y Stock bajo coinciden con el número de filas de cada estado en la lista de existencias. | UX02 §04 #1 |
| INV-63 | El Colaborador no ve costos ni valores en ninguna pantalla de Inventarios: ni Costo prom. ni Valor en Existencias, ni indicadores de valor, ni costos de compras, ni Valor del conteo, ni precios de transferencia. En el prototipo el Colaborador tampoco ve los indicadores de scrInventarios, las órdenes por recibir ni los accesos Nueva orden de compra, Control de Masa ni Transferencia. Decisión del líder; ver R-03. | Instrucción del líder; PROTO CSS `body[data-dpzrol="col"]` (líneas 288–292) y `_tabsRol` |
| INV-64 | Todo color, tamaño y fuente sale de los tokens `Tema.*`, `Resp()`, `Gutter`, `MitadHueco`, `AnchoMax` (1024) y los estilos TY-01 a TY-08 de DPZ-UX-01. Ningún control lleva color o tamaño escrito a mano. Fuente Segoe UI. | UX01 bloque «Tokens globales»; UX01 checklist (tokens pegados en App › Formulas) |
| INV-65 | El G13 muestra un punto de 8 px en el color del estado y el texto en Tema.Texto; nunca el texto en el color del estado. Alto 24, radio 12. | UX02 §01 G13 StatusBadge; §04 #2 |
| INV-66 | Cada pantalla se comprueba a 390, 768 y 1366 px: filas G14 apiladas en teléfono (botón debajo, ancho completo), columnas de tabla ocultas por tamaño y sin scroll horizontal. Nombres de controles con la convención prefijo + Pantalla + _ + Elemento. | UX02 §04 #8; UX01 sección 04 (convención de nombres) |
| INV-67 | Ninguna pantalla de Inventarios tiene selector de sucursal ni comparativos entre sucursales; todo se limita a Guanajuato · Río Bravo. La contraparte de una transferencia (D5) es un dato de la solicitud elegido de `raw_app_sucursal`, no un selector de contexto ni un comparativo. | decisiones.md D3 |
| INV-68 | Todas las lecturas y escrituras usan solo las listas raw_* del Marketplace (ver mapeo-listas.md). Compras y movimientos se filtran por fecha antes de cualquier filtro en memoria. | decisiones.md D1; UX02 §04 #11 |

## 9. Prototipo frente a DPZ-UX-02: lo que la spec no cubre

Esto **no** son criterios de esta entrega. Se registra para que el líder decida alcance.

| Tema | Qué hace el prototipo | Dónde | Efecto |
|---|---|---|---|
| Pestañas | Tablero, Existencias, Sugerida, Compras, Movimientos, Mezclas, Mermas, Conteos, Recetas, Catálogos (la spec define cuatro: Existencias, Compras, Movimientos, Conteos) | PROTO `TABS_ALL` | Alcance |
| Aprobación de órdenes | La orden nace «Por aprobar»; `sup`, `gop` y `adm` aprueban («Aprobar y enviar», por correo al contacto del proveedor) o rechazan; Pendiente solo después de aprobar. KPI «Órdenes por aprobar» y aviso | PROTO `APRUEBAN`, `pintarAprob` (SCRUM-287/288) | La spec tiene Pendiente → Recibida; B-04, B-12 |
| Datos de la orden | Fecha de entrega solicitada (obligatoria, no anterior al pedido), elaboró, comentarios, total estimado a costo promedio | PROTO `#oCrear` | Columnas existen en `raw_inv_orden_compra` |
| Recepción de la orden | Diálogo con folio de factura o remisión, fecha, quién recibió, evidencia fotográfica, partidas recibidas, comentarios; la existencia sube con lo realmente recibido | PROTO `dlgRec` | B-04 |
| Orden sugerida | Pestaña con consumo de 15 días − conteo − órdenes en camino, ajuste ±10 %, crea orden con la sugerencia | PROTO «Orden de compra sugerida» | La spec usa `CantidadSugerida` simple |
| Mermas | Formulario (tipo insumo o producto, insumo, cantidad, motivo, valor estimado, comentario, foto) | PROTO «Registro de mermas» | Fuera de UX02 |
| Mezclas | Captura por mezcla con hora y usuario, «Mezclas de hoy», testales por semana, proyección de masas de la semana (ventas de 8 semanas × receta) | PROTO «Monitoreo de Insumos» | B-01, B-10 |
| Recetas, factores de conversión, proveedores aprobados | Catálogos editables por el corporativo | PROTO v3 | Fuera de UX02 |
| Consumo teórico vs real | Tabla con tolerancia ±2.5 % | PROTO `pintarCosto` | Fuera de UX02 |
| Recepción de transferencia | Folio de factura o remisión, evidencia, notificación a la otra sucursal | PROTO `#dlgRec` | B-03 |
| Nombre de pantalla | «Monitoreo de Insumos» donde la spec dice «Inventario general» | PROTO | Nomenclatura |
| Rótulos | «testales» (PROTO) frente a «bolitas» (UX02) | PROTO, UX02 | Nomenclatura |

## 10. Riesgos abiertos y preguntas

### Pendientes [C] de la spec (registrados, no resueltos)

| # | Pendiente | Dónde |
|---|---|---|
| C-1 | Retención de cada lista de captura (por ejemplo, cuántos días de movimientos se conservan; la spec dice 90). Por D4 ya no hay corte de publicación desde el POS | UX02 §03 «Fuentes» |
| C-2 | `CantidadSugerida`: confirmar contra RN-21 (pedido sugerido con consumo proyectado) | UX02 §03 «Estados y reglas de inventario» |
| C-3 | `CountRows(raw_inv_compra)` no delega. Se acepta mientras la lista tenga menos de 2,000 filas; si crece, alternativa: mostrar solo el conteo del mes o guardar un contador | UX02 §03 «Compras, movimientos y conteos» |
| C-4 | `TestalesSemana` y `RendimientoReal`: confirmar origen (ventas publicadas y captura de masas) | UX02 §03 «Ajuste de rendimiento de harina» |
| C-5 | Decimales por unidad (criterio inicial: kg, L, galón, medio galón, bulto y lata) y unidades por validar con la sucursal: Chile seco (Sobre), Bladoza, Bolsa de basura (kg) y Harina (bulto) | UX02 §03 «Listas de captura»; §02 datos del catálogo |
| C-6 | Cargar el Excel real del directorio de sucursales (`CatSucursales`) | UX02 §03 «Listas de captura» |
| C-7 | Umbrales de alerta (30 %, ×10): propuesta de AntPath por validar con el corporativo | UX02 §03 «Reglas de conteo…» |
| C-8 | Control de Masa: registro por día o por turno (la llave de `raw_inv_masa_mezcla` asume por día; si es por turno se agrega `turno`), y si una mezcla equivale a un bulto de harina | UX02 §03 «Listas de captura» |
| C-9 | Transferencias entre sucursales: sitio común con permisos por elemento (A) o Power Automate que copia y sincroniza (B), decidir antes de F2 | UX02 §03 «Listas de captura» |
| C-10 | Límite diario de escrituras del conteo (~90–120 por semana y sucursal) | UX02 §03 «scrInventarios_Conteo…» |
| C-11 | `in` sobre `colOrdenes.ID` no delega: pocas órdenes abiertas | UX02 §03 «scrInventarios · Carga…» |

### Brechas de datos

Ver `mapeo-listas.md`, sección 4 (B-01 a B-13; B-13 resuelta por D4). Tras D6, B-01 a B-08 están cerradas. Abiertas: B-09 (derivación de `colRef`; bloquea alertas y «excede lo disponible»), B-10 (testales de la harina, [C]) y B-11 (pregunta P-11); B-12 fuera de alcance. B-13 quedó resuelta por D4.

### Riesgos

| # | Riesgo | Fuente |
|---|---|---|
| R-A | **Licencia.** No hay conector premium en lo que la spec usa (SharePoint, Notify). Las notificaciones del prototipo (aprobación de orden, transferencia) exigen Power Automate con conectores estándar; confirmar que el aviso por correo no usa HTTP ni conector premium | PROTO; CLAUDE.md |
| R-B | **Costos visibles por permiso de lista.** Ocultar costos al Colaborador es visual; el dato viaja en las mismas listas (`mapeo-listas.md` R-03) | Líder |
| R-C | **Token `Tema.Grid`.** UX02 lo usa en la barra de avance y el prototipo en `C.grid`, pero UX01 «Tokens globales» no lo define | UX02 §02 árbol «conteo»; UX01 |
| R-D | **Diferencia entre texto y fórmula** en el orden del detalle de conteos físicos (texto «de mayor a menor valor», fórmula ascendente por `Valor`). Se tomó la fórmula | UX02 §02 «conteos» frente a §03 |
| R-E | **Volumen.** `raw_inv_conteo_semanal_linea` ≈ 4,600 filas al año, bajo el umbral de 5,000; la llave (`conteoId`, `idinsumo`) y el índice `periodo` (D6) permiten filtrar por conteo | UX02 §03 «Listas de captura»; `sharepoint/README.md` |
| R-F | **Id del estado de alerta de conteo.** UX02 usa `cerou` en `EstadosLineaConteo` y `cero` en `AlertaConteo` y `InvConteoLinea.Alerta`. Se usa `cero` en esta spec | UX02 §03 |
| R-G | **Variable del diálogo de orden.** UX02 pone `locDlg = "crear"` en `btnCard_Toque` pero el diálogo se muestra con `locDlg = "orden"` | UX02 §03 «galInv_Accesos» frente a «dialogo-orden.fx» |
| R-H | **Actualizaciones concurrentes de existencia.** Recibir, confirmar transferencias y «Registrar entrada» modifican `raw_inv_insumo.existencia` desde sesiones distintas; escribir con el valor leído al abrir la pantalla pierde cambios. Regla: leer la fila fresca con `LookUp` delegable por `idinsumo` justo antes del `Patch`, y sumar sobre ese valor. Debe resolverse antes de desbloquear INV-15, INV-30 e INV-58 | D4; CLAUDE.md (regla Power Fx) |

### Preguntas para el líder

| # | Pregunta |
|---|---|
| P-1 | **Cerrada por D5.** Sucursal propia fija; contraparte desde `raw_app_sucursal` |
| P-2 | Control de Masa y Conteo: las listas ya están definidas (D6, v1.5) pero no desplegadas en el sitio. ¿Se construye ya contra el esquema o se espera al despliegue? Hoy bloquea el guardado de Control de Masa (INV-35, junto con C-8) |
| P-11 | B-11: en el piloto cada insumo tiene un solo `idalmacen`. ¿Se acepta un almacén por insumo, o se necesita existencia por insumo y almacén? |
| P-3 | ¿El Colaborador puede ordenar (botón «Ordenar») y recibir órdenes? La spec no restringe; PROTO le oculta los accesos pero deja «Ordenar» visible en la lista de atención. ¿Quién recibe? |
| P-4 | ¿El Colaborador ve valores monetarios en la pestaña Conteos (PROTO no los oculta)? La regla del líder dice que no |
| P-5 | ¿`gop` y `adm` entran a scrInventarios_ConteoCierre en solo lectura? La spec dice que `adm` «L» en el conteo; PROTO no muestra el botón a quien no puede cerrar |
| P-6 | ¿Se incorpora la aprobación de órdenes del prototipo (Por aprobar, Rechazada) o se sigue la spec (Pendiente → Recibida)? |
| P-7 | **Cerrada por D4.** Todas las `raw_inv_*` son de captura y la app las escribe |
| P-10 | ¿Confirmar el envío o la recepción de una transferencia y «Registrar entrada» ajustan `raw_inv_insumo.existencia`? D4 lo dice solo para Recibir una orden; la spec lo deja implícito (supuesto) |
| P-9 | Con D4 las compras y los conteos físicos se capturan en la app, pero DPZ-UX-02 solo los lee. ¿Recibir una orden debe además crear `raw_inv_compra` y `raw_inv_compra_partida` (folio de factura, importes)? ¿Cerrar el conteo semanal debe crear `raw_inv_conteo_fisico` y su partida y ajustar `existencia`? |
| P-8 | ¿Se adoptan las extensiones del prototipo «Sin umbral» y «Existencia negativa» (INV-07)? |
