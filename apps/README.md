# Apps de lienzo

Una carpeta por app (`apps/<app>/src/*.pa.yaml`). Se editan con el **Canvas Authoring MCP** mientras la app está abierta en Power Apps Studio con la coautoría activa.

## Canvas Authoring MCP

Registrado en `.mcp.json` como `canvas-authoring`. Es el mismo comando que usa el plugin `canvas-apps@power-platform-skills` de Microsoft:

```
dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes
```

Requiere el SDK de .NET 10 (`dotnet --list-sdks`). La primera vez, `dnx` descarga el paquete de nuget.org.

### Conectar a una sesión de Studio

1. Abre la app en Studio y activa **Configuración → Actualizaciones → Coauthoring**.
2. Deja la pestaña de Studio abierta toda la sesión: el MCP trabaja sobre esa sesión de coautoría.
3. Llama a la herramienta `connect` del servidor `canvas-authoring` con los datos de la URL de Studio:
   - `environment_id`: el segmento después de `/e/` (p. ej. `Default-<guid>`).
   - `app_id`: el último segmento del parámetro `app-id` ya decodificado.
   - `environment_category`: `prod` para `make.powerapps.com`.
4. Si `connect` responde 404, suele ser otra cuenta: reintenta con `force_account_select: true` y, si sigue fallando, con `auth_flow: "browser"`.

El MCP no agrega orígenes de datos: las listas de SharePoint se conectan en Studio desde el panel **Datos**.

## Apps

| App | Entorno | App id | Estado |
|---|---|---|---|
| PDP Inventarios (dev) | `Default-5a7df1b6-a688-4634-b639-e2baf07e8e53` (franquiciasab) | `88495839-4776-4c23-a944-a2cb95e21ae2` | MCP conectado (2026-11-22). 42 listas de DEPRITAM conectadas como origen de datos (verificado contra `productos.json`); app en blanco, sin pantallas |

Al cerrar cada sesión de trabajo: `pac canvas download` y commit de los `.pa.yaml` en `apps/<app>/src/`.
