# make_patch.ps1
# Створює xdelta-патч UA-локалізації SH:SM PS2 та оновлює HASHES.txt.
# Викликається з make_patch.bat. Кладіть SHSM_clean.iso і SHSM_UA.iso
# поруч з цим скриптом, далі двічі клік по make_patch.bat.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# === НАЛАШТУВАННЯ ===
$CleanIso   = 'SHSM_clean.iso'
$UaIso      = 'SHSM_UA.iso'
$PatchName  = 'Shattered Memories UA v.0.1'
$Version    = 'v0.1'
$Xdelta     = 'xdelta3.exe'
$HashesFile = 'HASHES.txt'

# Рівень компресії xdelta3. xdelta3 однопоточний за архітектурою —
# багатопоточності НЕМАЄ навіть на потужному CPU. Єдина ручка
# швидкість/розмір — це рівень. Орієнтири на 1.4 ГБ ISO:
#   9 — найкращий розмір, ~60-120 с (для фінального релізу)
#   6 — ~30-60 с,  +5%  до розміру патчу (рекомендовано для ітерацій)
#   3 — ~15-30 с,  +30% до розміру патчу (швидкий тест)
#   1 — ~5-10 с,   +60% до розміру патчу (мегашвидко)
$CompressionLevel = 9

Set-Location -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)

# === ДОПОМІЖНІ ФУНКЦІЇ ===

function Get-Sha256WithProgress {
    param([string]$Path, [string]$Activity)
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try {
            $total      = $stream.Length
            $bufSize    = 4MB
            $buffer     = New-Object byte[] $bufSize
            $done       = 0
            $sw         = [System.Diagnostics.Stopwatch]::StartNew()
            $lastUpdate = -1000
            while ($true) {
                $read = $stream.Read($buffer, 0, $bufSize)
                if ($read -eq 0) { break }
                [void]$sha.TransformBlock($buffer, 0, $read, $null, 0)
                $done += $read
                if (($sw.ElapsedMilliseconds - $lastUpdate) -gt 150) {
                    $pct = if ($total -gt 0) { [int](($done * 100) / $total) } else { 0 }
                    $mb_done  = [int]($done  / 1MB)
                    $mb_total = [int]($total / 1MB)
                    Write-Progress -Activity $Activity -Status "$mb_done / $mb_total MB" -PercentComplete $pct
                    $lastUpdate = $sw.ElapsedMilliseconds
                }
            }
            [void]$sha.TransformFinalBlock($buffer, 0, 0)
            Write-Progress -Activity $Activity -Completed
            $hex = New-Object System.Text.StringBuilder
            foreach ($b in $sha.Hash) { [void]$hex.Append($b.ToString('X2')) }
            return $hex.ToString()
        } finally { $sha.Dispose() }
    } finally { $stream.Dispose() }
}

function Invoke-WithProgress {
    param(
        [string]$Exe,
        [string[]]$ArgList,
        [string]$Activity,
        [string]$WatchFile = $null,
        [long]$ExpectedSize = 0
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $proc = Start-Process -FilePath $Exe -ArgumentList $ArgList `
        -NoNewWindow -PassThru `
        -RedirectStandardOutput ([System.IO.Path]::GetTempFileName()) `
        -RedirectStandardError  ([System.IO.Path]::GetTempFileName())
    while (-not $proc.HasExited) {
        $sec = [int]$sw.Elapsed.TotalSeconds
        $status = "Виконується... $sec с"
        $pct = -1
        if ($WatchFile -and (Test-Path -LiteralPath $WatchFile)) {
            try {
                $written = (Get-Item -LiteralPath $WatchFile -ErrorAction SilentlyContinue).Length
                $mb_written = [int]($written / 1MB)
                if ($ExpectedSize -gt 0) {
                    $mb_total = [int]($ExpectedSize / 1MB)
                    $pct = [int](($written * 100) / $ExpectedSize)
                    if ($pct -gt 100) { $pct = 100 }
                    $status = "$mb_written / $mb_total MB  [$sec с]"
                } else {
                    $status = "Записано: $mb_written MB  [$sec с]"
                }
            } catch {}
        }
        if ($pct -ge 0) {
            Write-Progress -Activity $Activity -Status $status -PercentComplete $pct
        } else {
            Write-Progress -Activity $Activity -Status $status
        }
        Start-Sleep -Milliseconds 400
    }
    Write-Progress -Activity $Activity -Completed
    return $proc.ExitCode
}

# === ПЕРЕВІРКИ ===
if (-not (Test-Path -LiteralPath $Xdelta)) {
    Write-Host "[ПОМИЛКА] Не знайдено $Xdelta поруч з цим скриптом." -ForegroundColor Red
    Write-Host 'Скачайте Windows-збірку: https://github.com/jmacd/xdelta-gpl/releases'
    exit 1
}
if (-not (Test-Path -LiteralPath $CleanIso)) {
    Write-Host "[ПОМИЛКА] Не знайдено чистий ISO: $CleanIso" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $UaIso)) {
    Write-Host "[ПОМИЛКА] Не знайдено український ISO: $UaIso" -ForegroundColor Red
    exit 1
}

Write-Host '================================================================'
Write-Host " Створення xdelta-патчу UA-локалізації SH:SM PS2 [$Version]"
Write-Host '================================================================'
Write-Host "Чистий ISO: $CleanIso"
Write-Host "UA ISO:     $UaIso"
Write-Host "Патч:       $PatchName"
Write-Host ''

# === СТВОРЕННЯ ПАТЧУ ===
Write-Host "[1/3] Створюю патч [xdelta3 -e -$CompressionLevel -S djw] ..."
$code = Invoke-WithProgress -Exe ".\$Xdelta" `
    -ArgList @("-e","-$CompressionLevel","-S","djw","-f","-s", $CleanIso, $UaIso, $PatchName) `
    -Activity 'xdelta3 encode' `
    -WatchFile $PatchName
if ($code -ne 0) {
    Write-Host "[ПОМИЛКА] xdelta3 завершився з кодом $code." -ForegroundColor Red
    exit 1
}
Write-Host '  Готово.'

# === ОБЧИСЛЕННЯ SHA256 ===
Write-Host '[2/3] Обчислюю SHA256 ...'
$CleanHash = Get-Sha256WithProgress -Path $CleanIso  -Activity "SHA256: $CleanIso"
Write-Host "  $CleanIso : $CleanHash"
$UaHash    = Get-Sha256WithProgress -Path $UaIso     -Activity "SHA256: $UaIso"
Write-Host "  $UaIso : $UaHash"
$PatchHash = Get-Sha256WithProgress -Path $PatchName -Activity "SHA256: $PatchName"
Write-Host "  $PatchName : $PatchHash"

$PatchSize = (Get-Item -LiteralPath $PatchName).Length

# === ЗАПИС HASHES.txt ===
Write-Host '[3/3] Оновлюю HASHES.txt ...'
$now = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$hashes = @"
Silent Hill: Shattered Memories - UA-локалізація PS2
Версія патчу: $Version
Дата створення: $now

Чистий ISO [вхід]:     $CleanIso
  SHA256: $CleanHash

UA ISO [результат]:    $UaIso
  SHA256: $UaHash

xdelta-патч:           $PatchName
  SHA256: $PatchHash
  Розмір: $PatchSize байтів
"@
[System.IO.File]::WriteAllText(
    (Join-Path -Path (Get-Location) -ChildPath $HashesFile),
    $hashes,
    (New-Object System.Text.UTF8Encoding $false)
)

Write-Host ''
Write-Host '================================================================'
Write-Host " Готово! Патч: $PatchName [$PatchSize байтів]"
Write-Host " Контрольні суми: $HashesFile"
Write-Host '================================================================'
Write-Host ''
Write-Host 'Підставте у PATCH_UA.ps1 такі рядки:'
Write-Host ''
Write-Host "  `$ExpectedSha256       = '$CleanHash'"
Write-Host "  `$ExpectedOutputSha256 = '$UaHash'"
Write-Host ''
