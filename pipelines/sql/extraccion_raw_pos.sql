/* ==========================================================================
   Pizza Deprizza · Plataforma de Gestión Operativa v1.4 · EN DESARROLLO
   Capa RAW · extracción del punto de venta Soft Restaurant 10 (softrestaurant10)
   Alcance POS: ventas, cortes de caja y catálogo de productos.
   Reglas raw: solo las columnas documentadas en los .txt de muestra, sin uniones,
   sin conversiones, sin TRIM y sin columnas calculadas. Un SELECT por tabla.
   Compras, proveedores, recetas e inventarios NO se leen del POS.
   ========================================================================== */
USE softrestaurant10;
SET NOCOUNT ON;
SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

/* Carga incremental opcional: descomenta el WHERE de las tablas transaccionales. */
DECLARE @desde datetime = '2026-10-01';   -- inclusivo
DECLARE @hasta datetime = '2026-10-29';   -- exclusivo

/* ---------- 01. raw_pos_venta_cuenta · dbo.cheques · muestra: dbo.cheques.txt ---------- */
SELECT
    folio,
    idempresa,
    numcheque,
    fecha,
    cierre,
    idturno,
    tipodeservicio,
    idarearestaurant,
    nopersonas,
    pagado,
    cancelado,
    idmotivocancela,
    idtipodescuento,
    totalarticulos,
    subtotal,
    descuentoimporte,
    totalcortesias,
    total
FROM dbo.cheques
-- WHERE cierre >= @desde AND cierre < @hasta
ORDER BY cierre DESC;

/* ---------- 02. raw_pos_venta_partida · dbo.cheqdet · muestra: dbo.cheqdet.txt ---------- */
SELECT
    foliodet,
    movimiento,
    idproducto,
    cantidad,
    precio,
    preciosinimpuestos,
    preciocatalogo,
    descuento,
    idtipodescuento,
    idcortesia,
    modificador,
    mitad,
    idproductocompuesto,
    productocompuestoprincipal,
    hora,
    idturno_cierre
FROM dbo.cheqdet
-- WHERE hora >= @desde AND hora < @hasta
ORDER BY foliodet DESC, movimiento;

/* ---------- 03. raw_pos_venta_cancelacion · dbo.cancela · muestra: dbo.motivoscancelacion.txt (bloque 31) ---------- */
SELECT
    cancelaid,
    foliocheque,
    clave,
    cantidad,
    precio,
    fecha,
    idmotivocancela,
    idturno_cierre
FROM dbo.cancela
-- WHERE fecha >= @desde AND fecha < @hasta
ORDER BY fecha DESC;

/* ---------- 04. raw_pos_venta_motivo_cancelacion · dbo.motivoscancelacion · muestra: dbo.motivoscancelacion.txt (bloque 32) ---------- */
SELECT
    idmotivocancela,
    descripcion,
    genera_desperdicio
FROM dbo.motivoscancelacion;

/* ---------- 05. raw_pos_venta_tipo_descuento · dbo.tipodescuento · muestra: dbo.tipodescuento.txt (bloque 35) ---------- */
SELECT
    idtipodescuento,
    desc_tipodescuento,
    descuento
FROM dbo.tipodescuento;

/* ---------- 06. raw_pos_venta_area · dbo.areasrestaurant · muestra: dbo.areasrestaurant.txt (bloque 34) ---------- */
SELECT
    idarearestaurant,
    descripcion,
    idtiposervicio
FROM dbo.areasrestaurant;

/* ---------- 07. raw_pos_corte_turno · dbo.turnos · muestra: dbo.areasrestaurant.txt (bloque 33) ---------- */
SELECT
    idturnointerno,
    idturno,
    idempresa,
    idestacion,
    apertura,
    cierre
FROM dbo.turnos
-- WHERE apertura >= @desde AND apertura < @hasta
ORDER BY apertura DESC;

/* ---------- 08. raw_pos_producto · dbo.productos · muestra: dbo.productos.txt ---------- */
SELECT
    idproducto,
    descripcion,
    nombrecorto,
    idgrupo,
    plu,
    usarcomedor,
    usardomicilio,
    usarrapido
FROM dbo.productos
ORDER BY idproducto;

/* ---------- 09. raw_pos_producto_precio · dbo.productosdetalle · muestra: dbo.productosdetalle.txt ---------- */
SELECT
    idproducto,
    idempresa,
    precio,
    preciosinimpuestos,
    bloqueado
FROM dbo.productosdetalle
ORDER BY idproducto;

/* ---------- 10. raw_pos_producto_grupo · dbo.grupos · muestra: dbo.grupos.txt ---------- */
SELECT
    idgrupo,
    descripcion,
    clasificacion
FROM dbo.grupos
ORDER BY idgrupo;

/* ---------- 11. raw_pos_producto_subgrupo · dbo.subgrupos · muestra: dbo.subgrupos.txt ---------- */
SELECT
    idsubgrupo,
    descripcion
FROM dbo.subgrupos
ORDER BY idsubgrupo;

/* ---------- 12. raw_pos_producto_grupo_subgrupo · dbo.grupossubgrupos · muestra: dbo.grupossubgrupos.txt ---------- */
SELECT
    idgrupo,
    idsubgrupo
FROM dbo.grupossubgrupos
ORDER BY idgrupo, idsubgrupo;

/* ---------- 13. raw_pos_producto_subgrupo_producto · dbo.subgruposproductos · muestra: dbo.subgruposproductos.txt ---------- */
SELECT
    idsubgrupo,
    idproducto
FROM dbo.subgruposproductos
ORDER BY idsubgrupo, idproducto;

/* ---------- 14. raw_pos_producto_paquete · dbo.paquetes · muestra: pq.idproductopaquete.txt ---------- */
SELECT
    idproductopaquete,
    idproducto,
    cantidad,
    idempresa
FROM dbo.paquetes
ORDER BY idproductopaquete;
