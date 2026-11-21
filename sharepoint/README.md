# SharePoint · listas como código

Las listas de la capa raw se definen en [`productos.json`](productos.json) y se crean con [`Deploy-Listas.ps1`](Deploy-Listas.ps1).

## Archivos

| Archivo | Qué es |
|---|---|
| `productos.json` | Los 40 productos de datos raw del Marketplace de datos (14 del punto de venta, 19 de inventario y 7 propios de la app): llave, columna incremental y atributos con su tipo. Es la fuente de verdad: para cambiar una lista, cambia este archivo. |
| `Deploy-Listas.ps1` | Crea en un sitio las listas y columnas que falten. Se puede correr varias veces: lo que ya existe no se toca. |

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

Un atributo cuyo nombre choca con un nombre reservado de SharePoint (`ID`, `Title`, `Version`, `Order`…) se crea con el sufijo `_raw` en el nombre interno; el nombre visible no cambia. Las columnas de la llave y de carga incremental quedan indexadas.

## Uso

Requiere PowerShell 7.4+ y el módulo PnP.PowerShell (`Install-Module PnP.PowerShell -Scope CurrentUser`).

Ver qué se crearía, sin conectarse:

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
| 2026-11-21 | `https://franquiciasab.sharepoint.com/sites/DEPRITAM` | 40 listas, 234 columnas y 57 índices, verificados contra `productos.json`. Tardó unos 60 minutos (cada columna es una llamada). |

Nota: SharePoint guardó la columna `c` de `raw_app_receta_producto` con nombre interno `_x0063_` (el nombre visible sigue siendo `c`). Power Apps la ve como `c`; por Microsoft Graph se escribe como `_x0063_`.

## Pendiente

- `raw_pos_venta_cuenta` y `raw_pos_venta_partida` superan las 5,000 filas del umbral de vista: las galerías de Power Apps deben filtrar por columnas indexadas y de forma delegable.
- Algunas llaves no identifican una fila de forma única (`raw_inv_conteo_semanal_linea` solo tiene `idinsumo`; `raw_inv_traspaso_partida` solo `id_traspaso`). Revisar antes de usarlas para actualizar filas.
