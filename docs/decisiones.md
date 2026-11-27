# Decisiones del proyecto

Registro de decisiones que cambian cómo se interpretan las fuentes. Más reciente arriba.

## 2026-11-23 · Carga inicial

### D8 · Reglas de la carga inicial (detalla D7)

- **Corte:** se carga el volcado tal cual (último dato 2026-10-28). Los días posteriores se cubren después con cargas incrementales o un volcado nuevo.
- **Columnas y llaves:** antes de cargar se amplían por D6 `raw_inv_movimiento`, `raw_inv_conteo_fisico`, `raw_inv_conteo_fisico_partida`, `raw_inv_compra` y `raw_inv_compra_partida` con las columnas del POS que faltan, y sus llaves para que identifiquen una fila (Marketplace v1.6).
- **Insumos:** `raw_inv_insumo` se carga solo como catálogo básico (`idinsumo`, `descripcion`, `presentacion` ← `unidad`, `idcategoria` ← `idgruposi`); existencias, costos y umbrales los captura la app. Conceptos, unidades y categorías (`gruposi` → `raw_inv_insumo_categoria`) se cargan con los códigos del POS, sin traducir.
- **Zona horaria:** las horas del POS se interpretan como hora fronteriza (`America/Matamoros`, con horario de verano) al convertirlas a UTC.
- **Nulos:** SharePoint no distingue `NULL` de vacío ni de `0` en Sí/No; el Parquet raw local conserva la diferencia.
- **Sin cargar:** `empresas` (datos cifrados) y las tablas del POS sin lista.

### D7 · Carga inicial completa desde el snapshot del POS (matiza D4)

Para arrancar, se carga a las listas de DEPRITAM **todo** el snapshot bronze de Soft Restaurant (`resultado contrato bronze.txt`, 36 tablas): las listas `raw_pos_*` (ventas completas, sin recorte de fechas) y, como **saldo inicial**, las `raw_inv_*` con catálogos (insumos, almacenes, conceptos, proveedores, unidades) e historial (compras, movimientos, conteos físicos). Es una carga única: a partir de ella, inventarios y compras se siguen capturando en la app (D4 sigue vigente para la operación). La carga se hace con el equipo ETL POS y queda documentada con su fecha de corte.

## 2026-11-22 · Inventarios

### D6 · Se puede ampliar el Marketplace para cerrar brechas

Autorizado por el líder: para cerrar las brechas de `docs/specs/mapeo-listas.md` se pueden **agregar columnas** a listas `raw_*` existentes y **crear listas nuevas** (por ejemplo, la captura diaria de Control de Masa). Los cambios se hacen en `sharepoint/productos.json` (fuente de verdad) y se despliegan con `Deploy-Listas.ps1`; cada lista o columna nueva cita la brecha que cierra. Excepción a D1 limitada a brechas documentadas: cualquier otra lista sigue necesitando aprobación.

### D4 · Inventarios y compras se capturan en la app (resuelve P-7)

Existencias, compras, movimientos, conteos físicos, órdenes, transferencias y mezclas se **capturan en la plataforma**, como dice `CLAUDE.md`; no se leen del punto de venta aunque DPZ-UX-02 los presente como datos del POS. Las listas `raw_inv_*` son de **captura**: la app las escribe (por ejemplo, Recibir una orden suma a `raw_inv_insumo.existencia` y registra el movimiento en `raw_inv_movimiento`). Del POS solo se leen ventas, cortes de caja y catálogo de productos.

### D5 · Contraparte de transferencias desde el catálogo de sucursales (resuelve P-1)

En Transferencias, la sucursal propia queda fija (Río Bravo) y la contraparte se elige de `raw_app_sucursal`. Es un dato de la solicitud, no un selector de contexto: sigue sin haber comparativos ni vistas entre sucursales (D3).

## 2026-11-21 · Fuentes, listas y roles

### Fuentes de referencia

| Fuente | Qué define | URL |
|---|---|---|
| Prototipo (Plataforma de Gestión Operativa) | Comportamiento de la app | https://claude.ai/artifact/7bCm5CjKA8wK3v1groHQmn |
| Marketplace de datos | Productos de datos y **listas de SharePoint** | https://claude.ai/artifact/6byjoadbFyvZVJZW3PTRkK |
| DPZ-UX-01 · Menú principal (v1.2) | Base global: tipografía, paleta `Tema.*`, iconos, widgets G01–G07, convención de nombres | https://claude.ai/artifact/A8UFZtvqfcVrzMNy5u4DQM |
| DPZ-UX-02 · Inventarios y Compras (v1.4) | Pantallas, widgets G13–G16, Power Fx | https://claude.ai/artifact/LivjBPyNkjjgERYorNnTHW |
| DPZ-UX-05 · Ventas, Reportes y Proyecciones (v1.0) | Pantallas, widgets G08–G12, Power Fx | https://claude.ai/artifact/NY8Qz6L9aMtuSbbtoNZ2aR |
| DPZ-UX-06 · Franquicias y Cumplimiento (v1.0) | Pantallas, widgets G17–G21, Power Fx | https://claude.ai/artifact/D2FSJWSsCWDUrjBGUZurJQ |
| DPZ-UX-08 · Análisis ejecutivo (v1.0) | Pantallas, widget G22, Power Fx | https://claude.ai/artifact/5xPf289a5xafa3giP6iTHv |

Las specs DPZ-UX mandan en pantallas, medidas, widgets y fórmulas; el prototipo, en comportamiento cuando la spec no lo cubre.

### D1 · Las listas de SharePoint son las del Marketplace

Se usan las listas generadas desde el Marketplace de datos: `sharepoint/productos.json` (40 productos `raw_pos_*`, `raw_inv_*`, `raw_app_*`) y `sharepoint/Deploy-Listas.ps1`.

Las specs DPZ-UX nombran otras listas (`pubVentaDiaHora`, `OrdenesCompra`, `InvConteo`, `CatSucursales`…). Al construir una pantalla, cada lista de la spec se **traduce** a la lista del Marketplace que contiene esos datos, y las fórmulas Power Fx de la spec se adaptan a los nombres y columnas de esa lista. La traducción se documenta en `docs/specs/mapeo-listas.md`. Si una spec necesita un dato que ninguna lista del Marketplace tiene, se marca como brecha y se decide aparte; no se crean listas fuera del Marketplace sin aprobación.

### D2 · Operador = Colaborador

Donde las specs dicen **Operador**, se entiende el rol **Colaborador** (`col`). Los cinco roles siguen siendo: Colaborador · Gerente de sucursal · Supervisor · Gerente de operaciones · Administrador corporativo. El "Supervisor de turno" de las specs se trata como **Supervisor** (`sup`) mientras no se indique otra cosa.

### D3 · Sin multi-franquicia por ahora

Se ignora el número de franquicias o sucursales: se construye para la sucursal piloto (Guanajuato · Río Bravo, `idempresa` 1). Comparativos entre sucursales, selector de sucursal y cortes por franquicia quedan fuera hasta nueva indicación.
