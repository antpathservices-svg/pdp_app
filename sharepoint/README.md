# SharePoint · listas como código

Las listas de la capa raw se definen en [`productos.json`](productos.json) y se crean con [`Deploy-Listas.ps1`](Deploy-Listas.ps1).

## Archivos

| Archivo | Qué es |
|---|---|
| `productos.json` | Los 42 productos de datos raw del Marketplace de datos (14 del punto de venta, 21 de inventario y 7 propios de la app): llave (`pk`), columna incremental (`inc`), índices adicionales (`idx`) y atributos con su tipo. Es la fuente de verdad: para cambiar una lista, cambia este archivo. |
| `Deploy-Listas.ps1` | Crea en un sitio las listas, columnas e índices que falten. Se puede correr varias veces: lo que ya existe no se toca. |

## Mapeo de tipos

| Atributo | Columna de SharePoint |
|---|---|
| `texto` | Una línea de texto (255). Referencias, comentarios y bitácoras van como varias líneas. |
| `entero` | Número, 0 decimales |
| `decimal` | Número |
| `fecha` | Fecha (solo fecha) |
| `fecha-hora` | Fecha y hora |
| `booleano` | Sí/No |
| `lista` | Varias líneas de texto (JSON tal cual) |

Un atributo cuyo nombre choca con un nombre reservado de SharePoint (`ID`, `Title`, `Version`, `Order`…) se crea con el sufijo `_raw` en el nombre interno; el nombre visible no cambia. Quedan indexadas las columnas de la llave (`pk`), la de carga incremental (`inc`) y las del campo `idx`.

## Índices (`idx`)

Cada producto puede llevar `"idx": ["estado", "creada"]`: columnas adicionales a indexar además de `pk` e `inc` (estado, fechas operativas, `envia`/`recibe`; R-01 de `docs/specs/mapeo-listas.md`). Si el campo no existe, no hay índices adicionales.

- Los nombres de `idx` son nombres de atributo (el nombre visible, no el interno `_raw`) y deben existir en el producto; si no, el script falla.
- Una columna de varias líneas (`lista` o de texto largo) no se puede indexar: si está en `idx`, el script falla.
- El script indexa también las columnas que ya existen en la lista sin índice (idempotente: si ya lo tienen, no hace nada).
- SharePoint permite máximo 20 columnas indexadas por lista. El script lo valida contra la definición (también con `-Plan`) y, al desplegar, contra los índices que ya tiene la lista; si se excede, falla antes de cambiar nada en esa lista.
- Los índices solo ayudan a filtros delegables y a mantenerse bajo el umbral de vista de 5,000 filas; no sustituyen un filtro por sucursal o fecha en la galería.

## Uso

Requiere PowerShell 7.4+ y el módulo PnP.PowerShell (`Install-Module PnP.PowerShell -Scope CurrentUser`).

Ver qué se crearía en un sitio vacío, sin conectarse (columnas, cuáles quedan indexadas y por qué, y el conteo de índices por lista):

```powershell
pwsh ./sharepoint/Deploy-Listas.ps1 -Plan
```

Desplegar en un sitio (todas las listas, o las que coincidan con `-Productos`):

```powershell
pwsh ./sharepoint/Deploy-Listas.ps1 -SiteUrl https://<tenant>.sharepoint.com/sites/<sitio> -ClientId <client-id> -Productos 'raw_inv_*'
```

`-ClientId` es el registro de aplicación en Entra ID que PnP.PowerShell usa para iniciar sesión. Se crea una sola vez por tenant con `Register-PnPEntraIDAppForInteractiveLogin`.

## Despliegues

| Fecha | Sitio | Resultado |
|---|---|---|
| 2026-11-21 | `https://franquiciasab.sharepoint.com/sites/DEPRITAM` | v1.4: 40 listas, 234 columnas y 57 índices, verificados contra `productos.json`. Tardó unos 60 minutos (cada columna es una llamada). |
| 2026-11-22 | `https://franquiciasab.sharepoint.com/sites/DEPRITAM` | v1.5: primero de prueba `raw_inv_conteo_semanal*` y `raw_inv_masa_mezcla`, luego completo. Resultado verificado: 42 listas, 277 columnas y 78 índices, sin duplicadas ni advertencias de tipo. Las `raw_inv_*` estaban vacías antes de cambiar las llaves. |

Nota: SharePoint guardó la columna `c` de `raw_app_receta_producto` con nombre interno `_x0063_` (el nombre visible sigue siendo `c`). Power Apps la ve como `c`; por Microsoft Graph se escribe como `_x0063_`.

## Cambios

### v1.5 (Marketplace 1.3) · 2026-11-22 · cierre de brechas de Inventarios (D6)

Brechas de `docs/specs/mapeo-listas.md`; cada columna y lista nueva cita su brecha en la descripción y en `nota`. Sin desplegar: falta correr `Deploy-Listas.ps1` en el sitio.

| Brecha | Cambio |
|---|---|
| B-01 | Lista nueva `raw_inv_masa_mezcla` (captura): `fecha`, `mezcla`, `oz17`, `oz10`, `oz5`, `capturadoPor`, `capturadoEl`. Llave `fecha, mezcla` (un registro por día; C-8 por día o por turno sigue abierto, si es por turno se agrega `turno` a la llave) |
| B-02 | `raw_inv_conteo_semanal_linea`: `conteoId`, `periodo`. Llave ahora `conteoId, idinsumo`; índice `periodo` |
| B-03 | `raw_inv_traspaso`: `creadaPor`, `enviadaPor`, `recibidaPor`. `raw_inv_traspaso_partida`: `renglon`, `idinsumo`; llave ahora `id_traspaso, renglon` |
| B-04 | `raw_inv_orden_compra`: `recibida`, `recibidaPor`, `aprobadaPor`, `aprobadaEl`, `foliofactura`, `evidencia`. `raw_inv_orden_compra_partida`: `cantidadRecibida` |
| B-05 | `raw_inv_insumo`: `ordenConteo`, `activo`, `aplicaA`, `versionCatalogo` |
| B-06 | `raw_app_sucursal`: `razonSocial`, `entidad` (estado de la república), `activa` |
| B-07 | `raw_inv_conteo_semanal`: `versionCatalogo`, `enviadoPor`, `rolCierre`, `capturadoPersona`. `raw_inv_conteo_semanal_linea`: `resueltaPor`, `capturadoPersona`. `capturadoPor` conserva el rol |
| B-08 | Lista nueva `raw_inv_conteo_semanal_historial` (captura): `conteoId`, `version`, `idinsumo`, `antes`, `despues`, `motivo`, `por`, `el`, `rol`. La bitácora que manda es esta lista; `raw_inv_conteo_semanal.historial` ya no se escribe |
| R-01 | Campo `idx` nuevo. Índices adicionales: `raw_inv_orden_compra` (`estado`, `creada`), `raw_inv_conteo_semanal` (`estado`, `anio`, `semana`), `raw_inv_traspaso` (`estado`, `envia`, `recibe`, `creada`), `raw_inv_compra` (`fechaaplicacion`), `raw_inv_conteo_fisico` (`fecha`), `raw_inv_conteo_semanal_linea` (`periodo`), `raw_inv_insumo` (`activo`), `raw_app_sucursal` (`activa`) |

B-11 queda abierta (pregunta al líder: en el piloto cada insumo tiene un solo `idalmacen`). Sin cambios de columnas: B-09 (`colRef` se deriva de conteos cerrados, compras y movimientos; lo calcula la app), B-10 (`RendimientoReal` es derivado y `TestalesSemana` está por definir [C]), B-12 (fuera de la spec) y B-13 (resuelta por D4). Tampoco se cambió el tipo de `del`/`al` (texto) ni de las fechas de traspaso (sin hora) de B-03/B-07: cambiar el tipo de una columna ya desplegada requiere migración.

`Deploy-Listas.ps1`: soporta `idx`, indexa columnas existentes que no lo estén, valida el máximo de 20 índices por lista y `-Plan` muestra por columna si queda indexada (`pk/inc` o `idx`) y el conteo por lista.

## Pendiente

- `raw_pos_venta_cuenta` y `raw_pos_venta_partida` superan las 5,000 filas del umbral de vista: las galerías de Power Apps deben filtrar por columnas indexadas y de forma delegable.
- Las llaves de `raw_inv_conteo_semanal_linea` y `raw_inv_traspaso_partida` ya identifican una fila (v1.5), pero las filas que ya existan en un sitio con la llave anterior deben revisarse. SharePoint no impone unicidad: la garantiza la app.
