# PATCH_UA.ps1
# Застосовує xdelta-патч UA-локалізації до користувацького чистого ISO.
# Викликається з PATCH_UA.bat. Перший аргумент — шлях до ISO.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# === НАЛАШТУВАННЯ [заповнюється розробником із HASHES.txt] ===
$ExpectedSha256       = 'ВСТАВИТИ_SHA256_ЧИСТОГО_ISO'
$ExpectedOutputSha256 = 'ВСТАВИТИ_SHA256_ГОТОВОГО_UA_ISO'

$PatchName    = 'LittleBit_SHSM_PS2_UA_v0.8.xdelta'
$Xdelta       = 'xdelta3.exe'
$OutputSuffix = '_UA'

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

# === БЕЗ АРГУМЕНТУ — ІНСТРУКЦІЯ ===
if ($args.Count -eq 0 -or [string]::IsNullOrWhiteSpace($args[0])) {
    Write-Host '================================================================'
    Write-Host ' Українська локалізація Silent Hill: Shattered Memories [PS2]'
    Write-Host '================================================================'
    Write-Host ''
    Write-Host 'Цей патч НЕ містить файлів гри.'
    Write-Host 'Потрібен ваш ВЛАСНИЙ чистий ISO [NTSC-U, SLUS-21899],'
    Write-Host 'здамплений з оригінального диску.'
    Write-Host ''
    Write-Host 'ЯК ВИКОРИСТОВУВАТИ:'
    Write-Host '  1. Перетягніть ваш ISO мишкою на цей файл [PATCH_UA.bat].'
    Write-Host '     АБО з командного рядка:'
    Write-Host '        PATCH_UA.bat "C:\шлях\до\вашого.iso"'
    Write-Host ''
    Write-Host '  2. Зачекайте 1-2 хвилини.'
    Write-Host ''
    Write-Host "  3. Поруч із вашим ISO з'явиться файл з суфіксом _UA."
    Write-Host '     Це ваша українська версія.'
    Write-Host ''
    Write-Host 'Перед патчингом BAT перевіряє SHA256 вашого ISO,'
    Write-Host 'щоб упевнитись, що це правильний регіон/версія.'
    Write-Host 'Деталі — у README_UA.txt.'
    Write-Host ''
    exit 0
}

$InputIso = $args[0]

# === ПЕРЕВІРКА ФАЙЛІВ ===
if (-not (Test-Path -LiteralPath $InputIso)) {
    Write-Host '[ПОМИЛКА] Файл не знайдено:' -ForegroundColor Red
    Write-Host "  $InputIso"
    exit 1
}
if (-not (Test-Path -LiteralPath $Xdelta)) {
    Write-Host "[ПОМИЛКА] Не знайдено $Xdelta." -ForegroundColor Red
    Write-Host 'Тримайте його поруч з PATCH_UA.bat у тій самій папці.'
    exit 1
}
if (-not (Test-Path -LiteralPath $PatchName)) {
    Write-Host "[ПОМИЛКА] Не знайдено патч: $PatchName" -ForegroundColor Red
    Write-Host 'Тримайте його поруч з PATCH_UA.bat у тій самій папці.'
    exit 1
}

Write-Host '================================================================'
Write-Host ' Українська локалізація Silent Hill: Shattered Memories [PS2]'
Write-Host '================================================================'
Write-Host "Ваш ISO: $InputIso"
Write-Host "Патч:    $PatchName"
Write-Host ''

# === ПЕРЕВІРКА SHA256 ВХІДНОГО ISO ===
Write-Host '[1/3] Перевіряю SHA256 вашого ISO ...'
$InputHash = Get-Sha256WithProgress -Path $InputIso -Activity "SHA256: $(Split-Path -Leaf $InputIso)"
Write-Host "  Ваш ISO:    $InputHash"
Write-Host "  Очікується: $ExpectedSha256"

if ($InputHash -ine $ExpectedSha256) {
    Write-Host ''
    Write-Host '================================================================' -ForegroundColor Red
    Write-Host ' [ПОМИЛКА] Це не той ISO.' -ForegroundColor Red
    Write-Host ' Потрібен чистий образ потрібного регіону/версії' -ForegroundColor Red
    Write-Host ' [NTSC-U, SLUS-21899].' -ForegroundColor Red
    Write-Host '================================================================' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Можливі причини:'
    Write-Host '  - інший регіон [PAL замість NTSC-U];'
    Write-Host '  - інша версія гри [Greatest Hits, демо тощо];'
    Write-Host '  - ваш ISO вже модифікований;'
    Write-Host '  - ISO пошкоджений або неповний.'
    Write-Host ''
    exit 1
}

Write-Host '  SHA256 збігається.' -ForegroundColor Green
Write-Host ''

# === ВИЗНАЧЕННЯ ВИХІДНОГО ФАЙЛУ ===
$InputItem = Get-Item -LiteralPath $InputIso
$OutputIso = Join-Path `
    -Path $InputItem.DirectoryName `
    -ChildPath ($InputItem.BaseName + $OutputSuffix + $InputItem.Extension)

# === ЗАСТОСУВАННЯ ПАТЧУ ===
Write-Host '[2/3] Застосовую патч ...'
$InputSize = (Get-Item -LiteralPath $InputIso).Length
$code = Invoke-WithProgress -Exe ".\$Xdelta" `
    -ArgList @('-d','-f','-s', $InputIso, $PatchName, $OutputIso) `
    -Activity 'xdelta3 decode' `
    -WatchFile $OutputIso `
    -ExpectedSize $InputSize
if ($code -ne 0) {
    Write-Host "[ПОМИЛКА] xdelta3 завершився з кодом $code." -ForegroundColor Red
    Write-Host 'Можливо: пошкоджений патч або вхідний ISO змінили під час обробки.'
    exit 1
}
if (-not (Test-Path -LiteralPath $OutputIso)) {
    Write-Host '[ПОМИЛКА] Вихідний файл не створено.' -ForegroundColor Red
    exit 1
}
Write-Host '  Готово.'

# === ПЕРЕВІРКА SHA256 ВИХІДНОГО ISO ===
Write-Host '[3/3] Перевіряю готовий ISO ...'

$skipOutCheck = (
    [string]::IsNullOrWhiteSpace($ExpectedOutputSha256) -or
    $ExpectedOutputSha256 -eq 'ВСТАВИТИ_SHA256_ГОТОВОГО_UA_ISO'
)

if ($skipOutCheck) {
    Write-Host '  [перевірка пропущена — $ExpectedOutputSha256 не задано]'
} else {
    $OutputHash = Get-Sha256WithProgress -Path $OutputIso -Activity "SHA256: $(Split-Path -Leaf $OutputIso)"
    if ($OutputHash -ine $ExpectedOutputSha256) {
        Write-Host ''
        Write-Host '[УВАГА] SHA256 готового файлу не збігається з очікуваним.' -ForegroundColor Yellow
        Write-Host "  Готовий:    $OutputHash"
        Write-Host "  Очікується: $ExpectedOutputSha256"
        Write-Host 'Можлива причина: пошкоджений патч.'
        exit 1
    }
    Write-Host '  SHA256 збігається.' -ForegroundColor Green
}

Write-Host ''
Write-Host '================================================================'
Write-Host ' Готово!'
Write-Host " Українська версія: $OutputIso"
Write-Host '================================================================'
Write-Host ''
Write-Host 'Записуйте на диск або запускайте у PCSX2.'
Write-Host ''
exit 0
