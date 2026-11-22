#Requires -Version 7.4
<#
.SYNOPSIS
    Crea o actualiza las listas de SharePoint de la capa raw a partir de sharepoint/productos.json.

.DESCRIPTION
    Una lista por producto de datos y una columna por atributo, con el mismo mapeo de tipos que el
    Marketplace de datos. Es idempotente: si la lista, la columna o el índice ya existen, no los vuelve a crear,
    así que se puede correr varias veces y en cada sucursal.

    - Atributo con nombre reservado de SharePoint (ID, Title, Version, Order…): el nombre interno
      lleva el sufijo _raw y el nombre visible se conserva.
    - Columnas de la llave (pk), de carga incremental (inc) y del campo idx: indexadas (salvo las de varias líneas).
      idx es una lista de columnas adicionales a indexar (estado, fechas, envia/recibe). Si la columna ya existe
      sin índice, se indexa. Máximo 20 columnas indexadas por lista (límite de SharePoint): si se excede, falla.
    - Capa raw: ninguna columna se fuerza obligatoria ni única; Title deja de ser obligatoria.

.PARAMETER SiteUrl
    URL del sitio, por ejemplo https://<tenant>.sharepoint.com/sites/<sitio>.

.PARAMETER ClientId
    Client ID del registro de aplicación en Entra ID usado por PnP.PowerShell para iniciar sesión.

.PARAMETER Productos
    Ids de productos a desplegar (admite comodines). Por omisión, todos.

.PARAMETER Plan
    No se conecta a SharePoint: muestra las listas, columnas e índices que crearía en un sitio vacío
    (y valida el límite de 20 índices por lista).

.EXAMPLE
    ./Deploy-Listas.ps1 -Plan
.EXAMPLE
    ./Deploy-Listas.ps1 -SiteUrl https://contoso.sharepoint.com/sites/dpz -ClientId 00000000-0000-0000-0000-000000000000 -Productos 'raw_inv_*'
#>
[CmdletBinding(DefaultParameterSetName = 'Deploy')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Deploy')][string]$SiteUrl,
    [Parameter(Mandatory, ParameterSetName = 'Deploy')][string]$ClientId,
    [string[]]$Productos = @('*'),
    [Parameter(Mandatory, ParameterSetName = 'Plan')][switch]$Plan,
    [string]$Definicion = (Join-Path $PSScriptRoot 'productos.json')
)

$ErrorActionPreference = 'Stop'

$Reservados = 'id', 'title', 'version', 'order', 'created', 'modified', 'author', 'editor',
              'contenttype', 'attachments', 'edit', 'linktitle', 'docicon', 'path'
$MaxIndices = 20
$Largos     = 'referencia', 'motivo', 'evidencia', 'comentarios', 'comentario', 'historial', 'firma', 'comprobante',
              'accion', 'reactivo', 'resolucion'

function Get-Columna {
    param($Producto, $Atributo)
    $nombre, $tipo = $Atributo[0], $Atributo[1]
    $interno = if ($Reservados -contains $nombre.ToLower()) { "${nombre}_raw" } else { $nombre }
    $llave   = $Producto.pk -split ',' | ForEach-Object Trim
    $adicional = @($Producto.idx) -contains $nombre
    $porLlave  = ($llave -contains $nombre) -or ($nombre -eq $Producto.inc)
    $indexar   = $porLlave -or $adicional
    $base    = "Name=`"$interno`" StaticName=`"$interno`" DisplayName=`"$nombre`""

    $xml = switch ($tipo) {
        'entero'     { "<Field Type=`"Number`" $base Decimals=`"0`"" }
        'decimal'    { "<Field Type=`"Number`" $base" }
        'fecha'      { "<Field Type=`"DateTime`" $base Format=`"DateOnly`"" }
        'fecha-hora' { "<Field Type=`"DateTime`" $base Format=`"DateTime`"" }
        'booleano'   { "<Field Type=`"Boolean`" $base" }
        default {
            if ($tipo -eq 'lista' -or $Largos -contains $nombre) { "<Field Type=`"Note`" $base NumLines=`"6`" RichText=`"FALSE`"" }
            else { "<Field Type=`"Text`" $base MaxLength=`"255`"" }
        }
    }
    $indexable = $xml -notmatch 'Type="Note"'
    if ($adicional -and -not $indexable) { throw "$($Producto.id): la columna '$nombre' es de varias líneas y SharePoint no la puede indexar (idx)." }
    $indexar = $indexar -and $indexable
    if ($indexar) { $xml += ' Indexed="TRUE"' }
    [pscustomobject]@{ Atributo = $nombre; Interno = $interno; Tipo = $tipo; TipoSP = ($xml -replace '^<Field Type="(\w+)".*$','$1'); Indexada = $indexar; Motivo = $(if ($porLlave) { 'pk/inc' } elseif ($adicional) { 'idx' } else { '' }); Xml = "$xml />" }
}

function Get-ColumnasIndexadas {
    # Valida idx contra los atributos y el tope de índices; devuelve las columnas de un producto.
    param($Producto)
    $cols = @($Producto.ent[0].a | ForEach-Object { Get-Columna $Producto $_ })
    foreach ($i in @($Producto.idx)) {
        if ($i -and -not ($cols.Atributo -contains $i)) { throw "$($Producto.id): idx menciona '$i', que no es un atributo del producto." }
    }
    $n = @($cols | Where-Object Indexada).Count
    if ($n -gt $MaxIndices) { throw "$($Producto.id): $n columnas indexadas en la definición; SharePoint permite máximo $MaxIndices por lista. Quita columnas de idx." }
    , $cols
}

$Productos = $Productos -split ',' | ForEach-Object Trim | Where-Object { $_ }   # pwsh -File pasa 'a,b' como un solo texto
$def = Get-Content $Definicion -Raw -Encoding utf8 | ConvertFrom-Json
$seleccion = $def.productos | Where-Object { $id = $_.id; $Productos | Where-Object { $id -like $_ } }
if (-not $seleccion) { throw "Ningún producto coincide con: $($Productos -join ', ')" }

Write-Host "Definición $($def.version.version) · $(@($seleccion).Count) listas" -ForegroundColor Cyan

if ($Plan) {
    foreach ($p in $seleccion) {
        $cols = Get-ColumnasIndexadas $p
        $nIdx = @($cols | Where-Object Indexada).Count
        Write-Host "`n$($p.id)  ($($p.origen) · llave: $($p.pk) · idx: $(@($p.idx) -join ', ') · $($cols.Count) columnas, $nIdx/$MaxIndices indexadas)" -ForegroundColor Yellow
        $cols | Format-Table Atributo, Interno, Tipo, Indexada, Motivo -AutoSize | Out-String | Write-Host
    }
    return
}

if (-not (Get-Module -ListAvailable PnP.PowerShell)) { throw 'Falta el módulo PnP.PowerShell: Install-Module PnP.PowerShell -Scope CurrentUser' }
Connect-PnPOnline -Url $SiteUrl -ClientId $ClientId -Interactive

foreach ($p in $seleccion) {
    $cols = Get-ColumnasIndexadas $p
    $lista = Get-PnPList -Identity "Lists/$($p.id)" -ErrorAction SilentlyContinue
    if (-not $lista) {
        Write-Host "+ lista $($p.id)" -ForegroundColor Green
        $lista = New-PnPList -Title $p.id -Template GenericList -Url "Lists/$($p.id)"
        Set-PnPField -List $p.id -Identity 'Title' -Values @{ Required = $false } | Out-Null
    } else {
        Write-Host "= lista $($p.id)"
    }

    # SharePoint puede codificar el nombre interno (p. ej. 'c' queda como '_x0063_'); StaticName conserva el original.
    $campos     = @(Get-PnPField -List $p.id -Includes Indexed)
    $existentes = $campos | ForEach-Object { $_.InternalName; $_.StaticName }
    $nuevas     = @($cols | Where-Object { $existentes -notcontains $_.Interno })

    # Columnas que ya existen y deben quedar indexadas pero no lo están.
    $porIndexar = @()
    foreach ($c in @($cols | Where-Object { $_.Indexada -and $existentes -contains $_.Interno })) {
        $campo = $campos | Where-Object { $_.InternalName -eq $c.Interno -or $_.StaticName -eq $c.Interno } | Select-Object -First 1
        if (-not $campo.Indexed) { $porIndexar += [pscustomobject]@{ Columna = $c; Campo = $campo } }
    }

    # Tope de SharePoint: indexadas actuales + columnas nuevas indexadas + índices por agregar.
    $total = @($campos | Where-Object Indexed).Count + @($nuevas | Where-Object Indexada).Count + $porIndexar.Count
    if ($total -gt $MaxIndices) { throw "$($p.id): quedarían $total columnas indexadas; SharePoint permite máximo $MaxIndices por lista. Revisa idx en productos.json o los índices que ya tiene la lista." }

    foreach ($c in @($cols | Where-Object { $existentes -contains $_.Interno })) {
        $campo = $campos | Where-Object { $_.InternalName -eq $c.Interno -or $_.StaticName -eq $c.Interno } | Select-Object -First 1
        if ($campo.TypeAsString -ne $c.TipoSP) { Write-Warning "$($p.id).$($c.Interno): la columna existente es $($campo.TypeAsString) y la definición pide $($c.TipoSP). No se cambia." }
    }
    foreach ($c in $nuevas) {
        Write-Host "  + columna $($c.Interno) ($($c.Tipo)$(if ($c.Indexada) { ', indexada' }))" -ForegroundColor Green
        Add-PnPFieldFromXml -List $p.id -FieldXml $c.Xml | Out-Null
    }
    foreach ($x in $porIndexar) {
        Write-Host "  + índice $($x.Columna.Interno)" -ForegroundColor Green
        Set-PnPField -List $p.id -Identity $x.Campo.InternalName -Values @{ Indexed = $true } | Out-Null
    }

    if ($p.filas -gt 5000) {
        Write-Warning "$($p.id): $($p.filas) filas en la muestra, más que el umbral de vista de 5,000. Filtra vistas y galerías por columnas indexadas."
    }

    $vista = Get-PnPView -List $p.id | Where-Object DefaultView
    Set-PnPView -List $p.id -Identity $vista.Id -Fields @($cols.Interno) | Out-Null
}

Write-Host "`nListo." -ForegroundColor Cyan
