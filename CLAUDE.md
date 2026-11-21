# CLAUDE.md — Plataforma de Gestión Operativa · Pizza Deprizza (AntPath)

Contexto para Claude Code en el repositorio del piloto. Registro **interno** (equipo AntPath): técnico, sin adornos.

## Proyecto

- Cliente: Pizza Deprizza. Piloto en **una** sucursal: Guanajuato · Río Bravo (FAB, `idempresa` 1, IVA 8 %). Diseño para 15 sucursales.
- Entregable real: un **estándar replicable** + kit de activación por sucursal, no "una app para una sucursal".
- Stack: Power Apps (lienzo) · SharePoint (backend) · Power Automate · pipelines Python · lago Parquet (medallón raw/silver/gold).
- Fuente POS: Soft Restaurant 10 sobre SQL Server (`softrestaurant10.dbo`), **solo lectura**, sin cambios en la base ni nuevos métodos de autenticación.
- Del POS solo se leen ventas, cortes de caja y catálogo de productos. Insumos, inventarios y compras se capturan en formularios de la plataforma.
- Roles (5): Colaborador · Gerente de sucursal · Supervisor · Gerente de operaciones · Administrador corporativo.

## Restricción dura: licencia

Microsoft 365 Business Premium **sin complementos**. Antes de proponer cualquier cosa:

- **Prohibido** usar conectores premium en Power Apps o Power Automate: SQL Server, Azure Blob Storage, HTTP, conectores personalizados y puerta de enlace local, entre otros. Si una solución los necesita, detente y avisa.
- Sin Dataverse (solo SharePoint). Sin Power Apps code apps (`pac code`): requieren Power Apps Premium.
- Power BI fuera del stack: los reportes se construyen en Power Apps.
- Consecuencia de arquitectura: Power Apps lee **solo SharePoint**. El lago lo escribe Python y la capa de publicación la escribe Python vía Microsoft Graph.

## Estructura del repositorio

```
apps/<app>/src/*.pa.yaml     # una carpeta por app de lienzo (Menú + una por submódulo; Inventarios = 2 apps)
sharepoint/                  # listas como código (PnP / CLI for Microsoft 365), plantilla de sitio
pipelines/                   # Python: polars + connectorx, escritura Parquet vía fsspec/obstore
infra/                       # aprovisionamiento del almacenamiento (Bicep o az CLI)
docs/                        # contratos raw, decisiones
```

Ramas: `main` (prd) y `dev`.

## Convenciones

- Productos de datos raw: `raw_pos_<dominio>_<entidad>` para lo que viene del punto de venta y `raw_inv_*` / `raw_app_*` para lo que viene de formularios. Copia fiel de la fuente: sin TRIM, uniones, conversiones ni columnas calculadas.
- Rutas del lago: `raw/pos/<producto>/idempresa=<x>/fecha=<aaaa-mm-dd>/`, `raw/app/<producto>/...`.
- Raw es append-only. Las correcciones se hacen en silver.
- Destino del lago **parametrizado** (URL + credencial en configuración, fuera del repo). Local: Azurite. Nube: Azure Blob (preferido, pendiente de aprobación del cliente) u OCI Object Storage.
- Las llaves del POS son `id_origen`, nunca id corporativo.

## Reglas por tipo de trabajo

- **Power Fx:** indica siempre si cada filtro es delegable contra SharePoint. Un filtro no delegable sobre una lista grande se considera defecto.
- **Listas de SharePoint:** declara columnas, tipos, índices (sucursal, fecha operativa, estado) y estrategia de partición. Una lista es de **captura** o de **publicación**, nunca de las dos. Nombres reservados (ID, Title, Version, Order…) llevan el sufijo `_raw` en el nombre interno.
- **Apps de lienzo:** edita los `.pa.yaml` a través del Canvas Authoring MCP con la app abierta en Studio y la coedición activa. Al cerrar la sesión: `pac canvas download -d` y commit.
- **Pipelines:** consultas de solo lectura sobre cuentas cerradas, con tope de tiempo y duración registrada. Corrida diaria; corte del día operativo en el turno 3, que cruza la medianoche.
- Diseño visual replicable en Power Apps. Todo cambio de diseño se refleja en las specs DPZ-UX-0X **y** en el prototipo.

## Setup de la máquina de desarrollo (Windows)

1. `winget install Microsoft.DotNet.SDK.10`
2. `dotnet tool install --global Microsoft.PowerApps.CLI.Tool`, luego `pac auth create` contra el tenant.
3. `npm i -g @pnp/cli-microsoft365`, `m365 login` y `m365 cli config set --key prompt --value false`
4. `claude mcp add m365 -- npx -y @pnp/cli-microsoft365-mcp-server@latest`
5. `Install-Module PnP.PowerShell -Scope CurrentUser` (requiere PowerShell 7.4+)
6. Marketplace **Power Platform Skills** y plugin `canvas-apps`: seguir https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/create-canvas-external-tools. Luego `/configure-canvas-mcp` con la app abierta en Studio.
7. `npm i -g azurite` para el lago local.

## Pendientes [C]

- Probar el Canvas Authoring MCP y la coedición en el entorno predeterminado del tenant (Business Premium, sin Dataverse) con una app en blanco.
- Azure vs OCI: depende de que el cliente abra la suscripción (preferente: plan de Azure por CSP). Mientras tanto, Azurite.
- Dueño de la cuenta de nube: debe ser Pizza Deprizza.
- Hora de corte del día operativo por sucursal (más allá del piloto).
