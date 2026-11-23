<#
.SYNOPSIS
    Carga inicial (D7/D8): data/carga/<lista>.jsonl -> listas raw_* de SharePoint (PnP.PowerShell, lotes).

.DESCRIPTION
    Requiere PowerShell 7.5+ y PnP.PowerShell 3.x. Config en .env (ver .env.example): SITE_URL, CLIENT_ID,
    RUTA_CARGA, TAMANO_LOTE, PAUSA_ENTRE_LOTES. Sin secretos: el inicio de sesion es interactivo.

    Hay que indicar un modo:
      -DryRun    No escribe nada. Lee los jsonl, valida columnas (contra el sitio si hay sesion o si se pide
                 -Conectar; si no, contra productos.json) y estima el tiempo. No modifica estado.json.
      -Ejecutar  Carga de verdad. Sin ninguno de los dos, el script se niega.

    Orden: el de orden_carga de mapeo_listas.json (catalogos pequenos primero; cheques, cheqdet,
    movsinv e invfisicomovtos al final).
    Guarda previa: una lista con ItemCount > 0 y sin estado previo se salta (no se duplica).
    Reanudacion: estado.json guarda por lista el ultimo ordinal confirmado; se continua desde ahi.
    Throttling: 429/503 -> espera Retry-After (o retroceso exponencial); con 429 repetido el lote se parte a la mitad.
    Cualquier otro error de lote deja la lista en 'incierto' (puede haber filas aplicadas): hay que verificar
    el ItemCount antes de reanudar (ver docs/carga-inicial.md).
    Cierre: al completar todas las listas del mapeo se marca corrida_cerrada; otra corrida exige -Forzar.
    -Forzar solo levanta esa marca; no salta la guarda previa ni vuelve a cargar listas completas.

.EXAMPLE
    pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -DryRun
    pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -DryRun -Conectar -Piloto
    pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -Ejecutar -Piloto
    pwsh ./pipelines/carga_inicial/cargar_sharepoint.ps1 -Ejecutar
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Ejecutar,
    [switch]$Conectar,
    [switch]$Piloto,
    [string[]]$Listas,
    [switch]$Forzar,
    [string]$EnvPath,
    [string]$SiteUrl,
    [string]$ClientId,
    [int]$TamanoLote,
    [double]$PausaEntreLotes = -1,
    [double]$SegundosPorFila = 0.15
)

$ErrorActionPreference = 'Stop'
if ($Listas) { $Listas = @($Listas | ForEach-Object { $_ -split ',' } | Where-Object { $_ }) }
[System.Threading.Thread]::CurrentThread.CurrentCulture = [System.Globalization.CultureInfo]::InvariantCulture
$Inv = [System.Globalization.CultureInfo]::InvariantCulture

if ($DryRun -and $Ejecutar) { throw 'Use -DryRun o -Ejecutar, no ambos.' }
if (-not $DryRun -and -not $Ejecutar) { throw 'Indique el modo: -DryRun (no escribe) o -Ejecutar (carga).' }

# ---------- configuracion ----------
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot '..' '..')).Path
$cfg = @{ SITE_URL = ''; CLIENT_ID = ''; RUTA_CARGA = 'data/carga'; TAMANO_LOTE = '100'; PAUSA_ENTRE_LOTES = '1' }
$envFile = if ($EnvPath) { $EnvPath } else { Join-Path $Raiz '.env' }
if (Test-Path $envFile) {
    foreach ($l in Get-Content $envFile -Encoding UTF8) {
        $l = $l.Trim()
        if (-not $l -or $l.StartsWith('#') -or -not $l.Contains('=')) { continue }
        $k, $v = $l.Split('=', 2)
        $v = $v.Trim().Trim('"').Trim("'")
        $cfg[$k.Trim()] = $v
    }
}
foreach ($k in @($cfg.Keys)) { $e = [Environment]::GetEnvironmentVariable($k); if ($e) { $cfg[$k] = $e } }
if ($SiteUrl) { $cfg.SITE_URL = $SiteUrl }
if ($ClientId) { $cfg.CLIENT_ID = $ClientId }
$lote = if ($TamanoLote) { $TamanoLote } else { [int]$cfg.TAMANO_LOTE }
$pausa = if ($PausaEntreLotes -ge 0) { $PausaEntreLotes } else { [double]::Parse($cfg.PAUSA_ENTRE_LOTES, $Inv) }
if ($lote -lt 10 -or $lote -gt 1000) { throw "TamanoLote fuera de rango: $lote" }
$dirCarga = if ([System.IO.Path]::IsPathRooted($cfg.RUTA_CARGA)) { $cfg.RUTA_CARGA } else { Join-Path $Raiz $cfg.RUTA_CARGA }
$rutaEstado = Join-Path $dirCarga 'estado.json'
$rutaLock = Join-Path $dirCarga '.carga.lock'

$mapeo = Get-Content (Join-Path $PSScriptRoot 'mapeo_listas.json') -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
$productos = Get-Content (Join-Path $Raiz 'sharepoint/productos.json') -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
$def = @{}   # lista -> @{ attr = tipo }
foreach ($p in $productos.productos) {
    $t = [ordered]@{}
    foreach ($e in $p.ent) { foreach ($a in $e.a) { $t[$a[0]] = $a[1] } }
    $def[$p.id] = $t
}

# ---------- listas a procesar ----------
$limites = @{}
if ($Piloto) {
    $sel = @($mapeo.piloto.listas)
    foreach ($k in $mapeo.piloto.limite_filas.Keys) { $limites[$k] = [int]$mapeo.piloto.limite_filas[$k] }
} else {
    $sel = @($mapeo.orden_carga)
}
if ($Listas) { $sel = @($sel | Where-Object { $n = $_; $Listas | Where-Object { $n -like $_ } }) }
$sel = @($mapeo.orden_carga | Where-Object { $sel -contains $_ })
if (-not $sel) { throw 'Ninguna lista seleccionada.' }

# ---------- nombres internos ----------
$Reservados = 'id', 'title', 'version', 'order', 'created', 'modified', 'author', 'editor',
              'contenttype', 'attachments', 'edit', 'linktitle', 'docicon', 'path'
function Get-InternoEsperado([string]$attr) {
    if ($Reservados -contains $attr.ToLower()) { return "${attr}_raw" } else { return $attr }
}
function Resolve-CamposSitio([string]$lista, [string[]]$attrs) {
    # attr -> @{ Interno; Tipo }. Los _raw y los codificados (_x0063_) se leen del sitio.
    $campos = Get-PnPField -List $lista
    $res = @{}
    foreach ($a in $attrs) {
        $esp = Get-InternoEsperado $a
        $f = $campos | Where-Object { $_.StaticName -ceq $esp } | Select-Object -First 1
        if (-not $f) { $f = $campos | Where-Object { $_.InternalName -ceq $esp } | Select-Object -First 1 }
        if (-not $f) {
            $f = $campos | Where-Object { $_.Title -ceq $a -and -not $_.Hidden -and -not $_.ReadOnlyField -and
                    $Reservados -notcontains $_.InternalName.ToLower() } | Select-Object -First 1
        }
        if ($f) { $res[$a] = @{ Interno = $f.InternalName; Tipo = $f.TypeAsString } }
    }
    return $res
}
$tipoSitioOk = @{
    'texto' = 'Text', 'Note'; 'lista' = 'Note', 'Text'; 'entero' = 'Number', 'Integer'; 'decimal' = 'Number', 'Currency'
    'fecha' = 'DateTime'; 'fecha-hora' = 'DateTime'; 'booleano' = 'Boolean'
}

# ---------- estado ----------
function Get-Estado {
    if (Test-Path $rutaEstado) { return Get-Content $rutaEstado -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable }
    return @{ version = 1; corrida_cerrada = $false; cerrada_utc = $null; listas = @{} }
}
function Save-Estado($est) {
    $tmp = "$rutaEstado.tmp"
    $est | ConvertTo-Json -Depth 8 | Set-Content $tmp -Encoding UTF8
    Move-Item $tmp $rutaEstado -Force
}
$estado = Get-Estado

# ---------- sesion ----------
$sesion = $false
if ($Ejecutar -or $Conectar) {
    if (-not $cfg.SITE_URL -or -not $cfg.CLIENT_ID) { throw 'Faltan SITE_URL / CLIENT_ID (.env o parametros).' }
    Connect-PnPOnline -Url $cfg.SITE_URL -ClientId $cfg.CLIENT_ID -Interactive
    $sesion = $true
} else {
    try { $null = Get-PnPConnection -ErrorAction Stop; $sesion = $true } catch { $sesion = $false }
}
$modoValida = if ($sesion) { 'sitio' } else { 'productos.json' }
Write-Host ("Modo: {0} | validacion contra: {1} | lote: {2} | pausa: {3}s | listas: {4}{5}" -f
    ($(if ($DryRun) { 'DRY-RUN (no escribe)' } else { 'EJECUTAR' })), $modoValida, $lote, $pausa, $sel.Count, ($(if ($Piloto) { ' | PILOTO' } else { '' })))

# ---------- lectura y conversion ----------
function Read-Jsonl([string]$lista, [int]$limite) {
    $ruta = Join-Path $dirCarga "$lista.jsonl"
    if (-not (Test-Path $ruta)) { throw "Falta $ruta (corra transformar.py)." }
    $filas = [System.Collections.Generic.List[object]]::new()
    foreach ($linea in [System.IO.File]::ReadLines($ruta, [System.Text.Encoding]::UTF8)) {
        if (-not $linea) { continue }
        $filas.Add(($linea | ConvertFrom-Json -AsHashtable -DateKind String))
        if ($limite -gt 0 -and $filas.Count -ge $limite) { break }
    }
    return , $filas
}
function ConvertTo-Valor($v, [string]$tipo) {
    if ($tipo -eq 'fecha-hora') {
        return [datetime]::Parse([string]$v, $Inv, [System.Globalization.DateTimeStyles]::AdjustToUniversal -bor [System.Globalization.DateTimeStyles]::AssumeUniversal)
    }
    return $v
}

# ---------- lote con throttling ----------
function Get-RetryAfter([string]$msg) {
    if ($msg -match 'Retry-After[^\d]*(\d+)') { return [int]$Matches[1] }
    return 0
}
function Test-Throttle([string]$msg) {
    return ($msg -match '\b429\b|\b503\b|throttl|Too Many Requests|temporarily unavailable|TooManyRequests')
}
function Send-Lote($nombre, $filasLote, $tipos, $mapaInterno) {
    $b = New-PnPBatch
    foreach ($f in $filasLote) {
        $vals = @{}
        foreach ($k in $f.v.Keys) { $vals[$mapaInterno[$k].Interno] = ConvertTo-Valor $f.v[$k] $tipos[$k] }
        $null = Add-PnPListItem -List $nombre -Values $vals -Batch $b
    }
    Invoke-PnPBatch -Batch $b -StopOnException
}

function Invoke-ListaCarga($nombre, $filas, $tipos, $mapaInterno, $total) {
    $e = $estado.listas[$nombre]
    $i = [int]$e.filas_cargadas
    $tam = $lote
    $throttlesSeguidos = 0
    $e.estado = 'en_curso'; Save-Estado $estado
    while ($i -lt $filas.Count) {
        $n = [Math]::Min($tam, $filas.Count - $i)
        $grupo = $filas.GetRange($i, $n)
        $rec = @{ desde = $grupo[0]._ord; hasta = $grupo[$n - 1]._ord; resultado = ''; segundos = 0; reintentos = 0; throttles = 0 }
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $hecho = $false
        while (-not $hecho) {
            try {
                Send-Lote $nombre $grupo $tipos $mapaInterno
                $hecho = $true; $rec.resultado = 'ok'; $throttlesSeguidos = 0
            } catch {
                $msg = $_.Exception.Message
                if (Test-Throttle $msg) {
                    $rec.throttles++; $rec.reintentos++; $throttlesSeguidos++
                    $esp = Get-RetryAfter $msg
                    if ($esp -le 0) { $esp = [Math]::Min(300, 15 * [Math]::Pow(2, $throttlesSeguidos - 1)) }
                    Write-Warning "[$nombre] 429/503 en filas $($rec.desde)-$($rec.hasta): espera ${esp}s (seguidos: $throttlesSeguidos)"
                    Start-Sleep -Seconds $esp
                    if ($throttlesSeguidos -ge 2 -and $n -gt 10) {
                        $tam = [Math]::Max(10, [int][Math]::Floor($n / 2)); $n = $tam
                        $grupo = $filas.GetRange($i, $n); $rec.hasta = $grupo[$n - 1]._ord
                        Write-Warning "[$nombre] lote reducido a $n"
                    }
                    if ($rec.reintentos -gt 8) { $rec.resultado = 'error: demasiados reintentos'; break }
                } else {
                    $rec.resultado = "error: $msg"; break
                }
            }
        }
        $sw.Stop(); $rec.segundos = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
        $null = $e.lotes.Add($rec)
        if (-not $hecho) {
            # 429/503 agotados: no se aplico nada. Otro error: puede haber filas aplicadas.
            $e.estado = if ($rec.resultado -like '*reintentos*') { 'error' } else { 'incierto' }
            Save-Estado $estado
            Write-Error "[$nombre] $($rec.resultado). Estado: $($e.estado). Verifique ItemCount antes de reanudar."
            return $false
        }
        $i += $n; $e.filas_cargadas = $grupo[$n - 1]._ord
        $e.segundos_acumulados = [Math]::Round(([double]$e.segundos_acumulados + $sw.Elapsed.TotalSeconds), 1)
        Save-Estado $estado
        Write-Host ("  [{0}] {1}/{2} ({3}s)" -f $nombre, $e.filas_cargadas, $total, $rec.segundos)
        if ($pausa -gt 0) { Start-Sleep -Milliseconds ([int]($pausa * 1000)) }
        if ($tam -lt $lote -and $throttlesSeguidos -eq 0) { $tam = [Math]::Min($lote, $tam * 2) }
    }
    return $true
}

# ---------- guarda de corrida cerrada y bloqueo ----------
if ($Ejecutar) {
    if ($estado.corrida_cerrada -and -not $Forzar) {
        throw "La carga inicial ya se cerro ($($estado.cerrada_utc)). Otra corrida exige -Forzar (ver docs/carga-inicial.md)."
    }
    if (Test-Path $rutaLock) { throw "Hay otra corrida en curso o interrumpida: $rutaLock (revise y borre el archivo si no hay otra)." }
    Set-Content $rutaLock "$PID $(Get-Date -Format o)"
}

# ---------- proceso por lista ----------
$reporte = [System.Collections.Generic.List[object]]::new()
$fallos = 0
try {
    foreach ($nombre in $sel) {
        $m = $mapeo.listas[$nombre]
        $tipos = $def[$nombre]
        $fila = [ordered]@{ lista = $nombre; filas = 0; columnas = 0; problemas = @(); estimado_s = 0; accion = '' }
        if (-not $tipos) { $fila.problemas += 'lista no existe en productos.json'; $reporte.Add($fila); $fallos++; continue }
        $limite = if ($limites.ContainsKey($nombre)) { $limites[$nombre] } else { 0 }
        $filas = Read-Jsonl $nombre $limite
        $fila.filas = $filas.Count
        $totalLista = if ($limite -gt 0) { @([System.IO.File]::ReadLines((Join-Path $dirCarga "$nombre.jsonl"))).Count } else { $filas.Count }

        # columnas usadas en el jsonl + coherencia con el mapeo
        $usadas = [System.Collections.Generic.HashSet[string]]::new()
        foreach ($f in $filas) { foreach ($k in $f.v.Keys) { $null = $usadas.Add($k) } }
        $fila.columnas = $usadas.Count
        foreach ($k in $usadas) {
            if (-not $tipos.Contains($k)) { $fila.problemas += "columna '$k' del jsonl no existe en la lista (productos.json)" }
            elseif ($tipos[$k].Length -eq 0) { $fila.problemas += "columna '$k' sin tipo" }
            if ($k.Length -gt 32) { $fila.problemas += "nombre interno de '$k' supera 32 caracteres" }
            if ($k -notmatch '^[A-Za-z][A-Za-z0-9_]*$') { $fila.problemas += "'$k' tiene caracteres que SharePoint codifica; el nombre interno debe leerse del sitio" }
        }
        # ordenes y ordinales
        $ords = $filas | ForEach-Object { $_._ord }
        if ($filas.Count -gt 0 -and ($ords[0] -ne 1 -or $ords[-1] -ne $filas.Count)) { $fila.problemas += 'ordinales no consecutivos desde 1' }
        if ($m.ordinal -and $filas.Count -gt 0 -and $filas[0].v[$m.ordinal] -ne 1) { $fila.problemas += "ordinal '$($m.ordinal)' no coincide con _ord" }

        # validacion contra el sitio
        $mapaInterno = @{}
        $itemCount = $null
        if ($sesion) {
            $lst = Get-PnPList -Identity $nombre -ErrorAction SilentlyContinue
            if (-not $lst) { $fila.problemas += 'la lista no existe en el sitio (Deploy-Listas.ps1)' }
            else {
                $itemCount = [int]$lst.ItemCount
                $mapaInterno = Resolve-CamposSitio $nombre ([string[]]$usadas)
                foreach ($k in $usadas) {
                    if (-not $mapaInterno.ContainsKey($k)) { $fila.problemas += "columna '$k' no existe en la lista del sitio" }
                    elseif ($tipos.Contains($k) -and ($tipoSitioOk[$tipos[$k]] -notcontains $mapaInterno[$k].Tipo)) {
                        $fila.problemas += "columna '$k': tipo del sitio $($mapaInterno[$k].Tipo) != $($tipos[$k])"
                    }
                }
            }
        } else {
            foreach ($k in $usadas) { $mapaInterno[$k] = @{ Interno = (Get-InternoEsperado $k); Tipo = '' } }
        }

        # estimado
        $spf = $SegundosPorFila
        $ant = $estado.listas[$nombre]
        $nLotes = [Math]::Ceiling($filas.Count / [double]$lote)
        $fila.estimado_s = [Math]::Round($filas.Count * $spf + $nLotes * $pausa, 0)

        # estado previo / guarda
        $desde = 0
        if ($ant) { $desde = [int]$ant.filas_cargadas }
        if ($ant -and $ant.estado -in 'incierto', 'error') { $fila.accion = "estado '$($ant.estado)': verificar ItemCount y editar estado.json"; if ($Ejecutar) { $fila.problemas += $fila.accion } }
        elseif ($ant -and $desde -ge $filas.Count) { $fila.accion = 'ya cubierta (se omite)'; $fila.estimado_s = 0 }
        elseif ($sesion -and $null -ne $itemCount -and -not $ant -and $itemCount -gt 0) {
            $fila.accion = "BLOQUEADA: ItemCount=$itemCount sin estado previo"
            $fila.problemas += $fila.accion
        }
        elseif ($sesion -and $null -ne $itemCount -and $ant -and $itemCount -ne $desde) {
            $fila.accion = "BLOQUEADA: ItemCount=$itemCount != filas_cargadas=$desde"
            $fila.problemas += $fila.accion
        }
        elseif ($desde -gt 0) { $fila.accion = "reanudar desde fila $($desde + 1)"; $fila.estimado_s = [Math]::Round(($filas.Count - $desde) * $spf, 0) }
        else { $fila.accion = 'cargar' }
        $reporte.Add($fila)

        if ($Ejecutar) {
            if ($fila.problemas.Count -gt 0) { $fallos++; Write-Warning "[$nombre] se omite: $($fila.problemas -join '; ')"; continue }
            if ($fila.accion -like 'ya cubierta*') { continue }
            if (-not $ant) {
                $estado.listas[$nombre] = @{ estado = 'pendiente'; filas_total = $totalLista; filas_cargadas = 0; piloto = [bool]$Piloto
                    segundos_acumulados = 0; lotes = @(); inicio_utc = (Get-Date).ToUniversalTime().ToString('o') }
            } else { $estado.listas[$nombre].filas_total = $totalLista }
            $estado.listas[$nombre].lotes = [System.Collections.ArrayList]@($estado.listas[$nombre].lotes)
            $ok = Invoke-ListaCarga $nombre $filas $tipos $mapaInterno $totalLista
            if (-not $ok) { $fallos++; break }
            $e = $estado.listas[$nombre]
            $e.item_count_final = [int](Get-PnPList -Identity $nombre).ItemCount
            if ([int]$e.filas_cargadas -ge $totalLista) {
                $e.estado = 'completa'; $e.fin_utc = (Get-Date).ToUniversalTime().ToString('o')
                if ($e.item_count_final -ne $totalLista) { $e.aviso = "ItemCount=$($e.item_count_final) != $totalLista (puede ser retraso del indice de SharePoint: reverifique)" ; Write-Warning "[$nombre] $($e.aviso)" }
            } else { $e.estado = 'parcial' }
            Save-Estado $estado
        }
    }
    if ($Ejecutar -and $fallos -eq 0 -and -not $Piloto -and -not $Listas) {
        $todas = @($mapeo.orden_carga | Where-Object { $estado.listas[$_] -and $estado.listas[$_].estado -eq 'completa' })
        if ($todas.Count -eq $mapeo.orden_carga.Count) {
            $estado.corrida_cerrada = $true; $estado.cerrada_utc = (Get-Date).ToUniversalTime().ToString('o')
            Save-Estado $estado
            Write-Host 'Carga inicial cerrada (corrida_cerrada = true).'
        }
    }
} finally {
    if ($Ejecutar -and (Test-Path $rutaLock)) { Remove-Item $rutaLock -Force }
}

# ---------- reporte ----------
Write-Host ''
Write-Host ('{0,-42}{1,8}{2,6}{3,10}  {4}' -f 'lista', 'filas', 'cols', 'est(s)', 'accion / problemas')
foreach ($r in $reporte) {
    Write-Host ('{0,-42}{1,8}{2,6}{3,10}  {4}' -f $r.lista, $r.filas, $r.columnas, $r.estimado_s, $r.accion)
    foreach ($p in $r.problemas) { Write-Host "    PROBLEMA: $p" -ForegroundColor Yellow }
}
$totFilas = 0; $totSeg = 0; $nProb = 0
foreach ($r in $reporte) { $totFilas += $r.filas; $totSeg += $r.estimado_s; $nProb += $r.problemas.Count }
Write-Host ''
Write-Host ("Total: {0} filas, {1} problemas, estimado {2} min (supuesto {3} s/fila + pausa; calibrar con -Piloto)." -f $totFilas, $nProb, [Math]::Round($totSeg / 60, 1), $SegundosPorFila)
if ($DryRun) {
    $salida = Join-Path $dirCarga 'dryrun.json'
    [ordered]@{ generado_utc = (Get-Date).ToUniversalTime().ToString('o'); validado_contra = $modoValida; lote = $lote
        piloto = [bool]$Piloto; total_filas = $totFilas; problemas = $nProb; listas = $reporte } | ConvertTo-Json -Depth 6 | Set-Content $salida -Encoding UTF8
    Write-Host "DRY-RUN: no se escribio nada en SharePoint ni en estado.json. Detalle: $salida"
}
if ($nProb -gt 0 -or $fallos -gt 0) { exit 1 }
