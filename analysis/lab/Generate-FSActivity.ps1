<#
.SYNOPSIS
    Generate-FSActivity.ps1 v3.20
    Simple file-system activity generator for forensic lab disk images.

.DESCRIPTION
    This script creates realistic file-system activity inside one root directory:
      - file creation
      - directory creation
      - file writes and appends
      - file deletion
      - empty directory deletion
      - file rename
      - directory rename
      - file move
      - directory move
      - file copy
      - timestamp changes
      - optional hard links
      - optional symbolic links, if allowed
      - optional alternate data streams, if supported

    It is designed to run WITHOUT Administrator rights. Normal file operations work
    as long as the current user has write permission on RootDir. Privileged or
    file-system-specific actions are skipped with a clear log message when they
    are not possible.

    Administrator rights are NOT required for the main workload.

    Optional large-file generation creates exactly one large file for each value
    provided with -LargeFileSizeMB. Large files are written with a chunked
    stream writer rather than one in-memory byte array. Example: -LargeFileSizeMB 2,2,2 creates
    three different files of exactly 2 MB.

    Directory creation is planned at about 5% of Count. Directory deletion,
    file deletion, file/directory rename, and move actions remain part of the
    normal workload. For Count greater than 100, the planner attempts to include
    almost every action type at least once.

    Optional -FileContentMarker creates exactly one marked text file. The file
    name contains "marked", its content contains the marker text, and this action
    is included in Count.

.PARAMETER RootDir
    Directory where the activity is generated. The directory is created if missing.

.PARAMETER Count
    Total number of logged actions to execute. Default: 100.
    Large files requested with -LargeFileSizeMB are included in this total.

.PARAMETER LogDir
    Directory where the CSV log, JSON replay file, and text report are written.
    
.PARAMETER Seed
    Optional deterministic seed. Use the same seed to reproduce similar choices.

.PARAMETER MaxFileSizeKB
    Maximum generated normal file size in KB. Default: 512. This limit does not apply to files selected for -LargeFileSizeMB.

.PARAMETER LargeFileSizeMB
    Optional list of exact large-file sizes in MB. One file is created for each value.
    Example: -LargeFileSizeMB 1,6 creates one 1 MB file and one 6 MB file.
    Example: -LargeFileSizeMB 2,2,2 creates three different 2 MB files.

.PARAMETER MaxDepth
    Maximum directory depth under RootDir. Default: 4.

.PARAMETER FileMarker
    Optional marker inserted in every generated file name. Example: -FileMarker xbpt creates names like xbpt_alpha_beta_123456.txt.

.PARAMETER FileContentMarker
    Optional text marker written into exactly one generated text file. The file name contains "marked".
    This marked file is included in Count. Example: -FileContentMarker "XBPT_CONTENT_MARKER".

.PARAMETER DirMarker
    Optional marker inserted in every generated directory name. Example: -DirMarker tpbx creates names like tpbx_dir_alpha_123456.

.PARAMETER SkipSymlinks
    Disable symbolic-link actions.

.PARAMETER SkipADS
    Disable alternate-data-stream actions.

.PARAMETER HeavySpcials
    Switch that enables a heavier special-artefact workload. When present, the planner schedules
    more CREATE_HARDLINK, CREATE_SYMLINK_FILE and CREATE_ADS attempts. The parameter name is
    intentionally spelled -HeavySpcials to match the lab command interface.

.PARAMETER SpecialEveryN
    Controls special artefact frequency. One full set of CREATE_HARDLINK, CREATE_SYMLINK_FILE,
    and CREATE_ADS is planned per SpecialEveryN actions. Default is 250 normally,
    25 when -HeavySpcials is used. Smaller values create more special artefact attempts.

.PARAMETER CleanRoot
    Delete RootDir contents before generating the workload. Use carefully.

.PARAMETER ReplayFile
    Replay an existing JSON replay file or CSV log produced by this script.
    With a JSON replay file, paths are remapped from the original root_dir to -RootDir when -RootDir is provided.
    With a CSV log, paths are replayed as stored unless they are already under -RootDir.

.EXAMPLE
    .\Generate-FSActivity.ps1 -RootDir C:\Users\refs\Downloads\tests -Count 1000 -LogDir C:\Users\refs\Downloads\logs

.EXAMPLE
    .\Generate-FSActivity.ps1 -RootDir E:\refs_test -Count 500 -Seed 42 -LogDir E:\logs -SkipSymlinks

.EXAMPLE
    .\Generate-FSActivity.ps1 -RootDir E:\refs_test -Count 1000 -LogDir E:\logs -FileMarker xbpt -DirMarker tpbx -CleanRoot

.EXAMPLE
    .\Generate-FSActivity.ps1 -RootDir E:\refs_specials -Count 1000 -LogDir E:\logs -HeavySpcials -SpecialEveryN 10

.EXAMPLE
    .\Generate-FSActivity.ps1 -ReplayFile E:\logs\fsactivity_20260514_184906_replay.json -RootDir F:\refs_replay -LogDir F:\logs -CleanRoot

.EXAMPLE
    .\Generate-FSActivity.ps1 -ReplayFile E:\logs\fsactivity_20260514_184906_log.csv -LogDir E:\logs_replay
#>

[CmdletBinding()]
param(
    [string] $RootDir = '',

    [int] $Count = 100,
    [string] $LogDir = '.',
    [int] $Seed = -1,
    [int] $MaxFileSizeKB = 512,
    [int[]] $LargeFileSizeMB = @(),
    [int] $MaxDepth = 4,
    [string] $FileMarker = '',
    [string] $FileContentMarker = '',
    [string] $DirMarker = '',
    [switch] $SkipSymlinks,
    [switch] $SkipADS,
    [switch] $HeavySpcials,
    [int] $SpecialEveryN = 0,
    [switch] $CleanRoot,
    [Alias('ReplayLog','LogFile')]
    [string] $ReplayFile = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertTo-SafeNamePart {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    $safe = $Value.Trim()
    $invalid = [System.IO.Path]::GetInvalidFileNameChars()
    foreach ($c in $invalid) { $safe = $safe.Replace([string]$c, '_') }
    $safe = $safe -replace '\s+', '_'
    $safe = $safe.Trim([char[]]@('_', '.', ' '))
    return $safe
}

$FileMarker = ConvertTo-SafeNamePart $FileMarker
$DirMarker = ConvertTo-SafeNamePart $DirMarker
if ($null -eq $FileContentMarker) { $FileContentMarker = '' }

if ($MaxFileSizeKB -lt 1) { throw 'MaxFileSizeKB must be at least 1.' }
if ($LargeFileSizeMB) {
    # Keep duplicates intentionally: -LargeFileSizeMB 2,2,2 means create three distinct 2 MB files.
    $LargeFileSizeMB = @($LargeFileSizeMB | Where-Object { $_ -gt 0 })
}

# -----------------------------------------------------------------------------
# Privilege / environment checks
# -----------------------------------------------------------------------------
function Test-IsAdministrator {
    try {
        $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object -TypeName System.Security.Principal.WindowsPrincipal -ArgumentList $identity
        return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch { return $false }
}

function Test-DeveloperMode {
    try {
        $path = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock'
        $value = Get-ItemPropertyValue -Path $path -Name 'AllowDevelopmentWithoutDevLicense' -ErrorAction Stop
        return ([int]$value -eq 1)
    }
    catch { return $false }
}

$Script:IsAdmin = Test-IsAdministrator
$Script:IsDeveloperMode = Test-DeveloperMode
$Script:CanCreateSymlink = ($Script:IsAdmin -or $Script:IsDeveloperMode)

if (-not $Script:IsAdmin) {
    Write-Warning 'Running without Administrator rights. Normal file and directory actions will run if permissions allow it. Some privileged actions, especially symbolic links, will be skipped.'
}

if ($SkipSymlinks -or -not $Script:CanCreateSymlink) {
    $Script:SymlinkEnabled = $false
    if (-not $SkipSymlinks) {
        Write-Warning 'Symbolic-link actions are disabled because this session is not elevated and Windows Developer Mode was not detected.'
    }
}
else {
    $Script:SymlinkEnabled = $true
}

# Hard links do not normally require Administrator rights, but the file system may refuse them.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace FsActivityNative {
    public static class Kernel32 {
        [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
        public static extern bool CreateHardLink(string lpFileName, string lpExistingFileName, IntPtr lpSecurityAttributes);
    }
}
'@ -Language CSharp

# -----------------------------------------------------------------------------
# State and utilities
# -----------------------------------------------------------------------------
$Script:Files = New-Object 'System.Collections.Generic.List[string]'
$Script:Dirs  = New-Object 'System.Collections.Generic.List[string]'
$Script:Ads   = @{}

$Words = @('alpha','beta','gamma','delta','echo','foxtrot','hotel','india','kilo','lima','mike','november','oscar','papa','quebec','romeo','sierra','tango','uniform','victor','whiskey','yankee','zulu','report','backup','config','data','temp','archive','output','cache','index','log','record','draft','sync','audit','trace')
$Exts = @('.txt','.log','.dat','.bin','.csv','.xml','.json','.tmp','.bak','.ini','.cfg','.md')

function New-RandomName {
    param([System.Random]$Rng, [string]$Extension)
    $w1 = $Words[$Rng.Next($Words.Count)]
    $w2 = $Words[$Rng.Next($Words.Count)]
    $n = $Rng.Next(100000, 999999)
    $prefix = if ([string]::IsNullOrWhiteSpace($FileMarker)) { '' } else { "$FileMarker`_" }
    return "$prefix$w1`_$w2`_$n$Extension"
}

function New-RandomDirectoryName {
    param([System.Random]$Rng)
    $w1 = $Words[$Rng.Next($Words.Count)]
    $n = $Rng.Next(100000, 999999)
    $prefix = if ([string]::IsNullOrWhiteSpace($DirMarker)) { '' } else { "$DirMarker`_" }
    return "$prefix`dir_$w1`_$n"
}

function Add-FileMarkerPrefix {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($FileMarker)) { return $Name }
    return "$FileMarker`_$Name"
}

function Add-DirMarkerPrefix {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($DirMarker)) { return $Name }
    return "$DirMarker`_$Name"
}

function New-UniquePath {
    param([string]$Directory, [string]$Name, [System.Random]$Rng)
    $path = Join-Path $Directory $Name
    while (Test-Path -LiteralPath $path) {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($Name)
        $ext = [System.IO.Path]::GetExtension($Name)
        $path = Join-Path $Directory ("$base`_$($Rng.Next(1000,9999))$ext")
    }
    return $path
}

function Get-RelativeDepth {
    param([string]$Path)
    $fullRoot = [System.IO.Path]::GetFullPath($RootDir).TrimEnd('\')
    $fullPath = [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($fullPath.Length -le $fullRoot.Length) { return 0 }
    $rel = $fullPath.Substring($fullRoot.Length).TrimStart('\')
    if ([string]::IsNullOrWhiteSpace($rel)) { return 0 }
    return ($rel -split '\\').Count
}


function Test-FSFile {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return [System.IO.File]::Exists($Path)
}

function Test-FSDirectory {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return [System.IO.Directory]::Exists($Path)
}

function Test-FSAny {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    return ([System.IO.File]::Exists($Path) -or [System.IO.Directory]::Exists($Path))
}

function Get-RandomDirectory {
    param([System.Random]$Rng, [switch]$NonRoot)
    Refresh-Inventory
    $candidates = @($Script:Dirs | Where-Object { Test-FSDirectory $_ })
    if ($NonRoot) { $candidates = @($candidates | Where-Object { $_ -ne $RootDir }) }
    $candidates = @($candidates | Where-Object { (Get-RelativeDepth $_) -lt $MaxDepth })
    if ($candidates.Count -eq 0) { return $RootDir }
    return $candidates[$Rng.Next($candidates.Count)]
}

function Get-RandomFile {
    param([System.Random]$Rng)
    Refresh-Inventory
    $candidates = @($Script:Files | Where-Object { Test-FSFile $_ })
    if ($candidates.Count -eq 0) { return $null }
    return $candidates[$Rng.Next($candidates.Count)]
}

function Get-LeafDirectory {
    param([System.Random]$Rng)
    Refresh-Inventory

    # Use a typed list instead of PowerShell +=. In Windows PowerShell 5.1,
    # += can occasionally try to call op_Addition on System.Object when the
    # left-hand value is no longer a true array. This produced:
    # "System.Object does not contain a method named op_Addition".
    $candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($dir in $Script:Dirs) {
        if ($dir -eq $RootDir) { continue }
        if (-not (Test-FSDirectory $dir)) { continue }
        $children = @(Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)
        if ($children.Count -eq 0) { $candidates.Add([string]$dir) | Out-Null }
    }
    if ($candidates.Count -eq 0) { return $null }
    return $candidates[$Rng.Next($candidates.Count)]
}

function Refresh-Inventory {
    $Script:Files.Clear()
    $Script:Dirs.Clear()
    if (Test-FSDirectory $RootDir) {
        $Script:Dirs.Add($RootDir)
        Get-ChildItem -LiteralPath $RootDir -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.PSIsContainer) { $Script:Dirs.Add($_.FullName) } else { $Script:Files.Add($_.FullName) }
        }
    }
}

function New-ContentBytes {
    param([System.Random]$Rng, [int]$MaxKB)

    $Script:LastGeneratedSizeKind = 'normal'
    $Script:LastGeneratedSizeLabel = ''

    $maxBytes = [Math]::Max(128, $MaxKB * 1024)
    $size = $Rng.Next(64, $maxBytes + 1)
    $bytes = New-Object byte[] ([int]$size)
    $Rng.NextBytes($bytes)
    return ,$bytes
}

function Write-RandomFileBytesChunked {
    param(
        [string]$Path,
        [int64]$Length,
        [System.Random]$Rng,
        [int]$ChunkSize = 1048576
    )

    Ensure-ReplayParent $Path
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
    try {
        $remaining = [int64]$Length
        $bufferLength = [Math]::Min([int64]$ChunkSize, [Math]::Max([int64]1, $remaining))
        $buffer = New-Object byte[] ([int]$bufferLength)
        while ($remaining -gt 0) {
            $toWrite = [Math]::Min([int64]$buffer.Length, $remaining)
            if ($toWrite -ne $buffer.Length) { $buffer = New-Object byte[] ([int]$toWrite) }
            $Rng.NextBytes($buffer)
            $stream.Write($buffer, 0, [int]$toWrite)
            $remaining -= $toWrite
        }
    }
    finally {
        $stream.Close()
    }
}

function Write-ReplayFileBytesChunked {
    param(
        [string]$Path,
        [int64]$Length,
        [int]$ChunkSize = 1048576
    )

    # Replay must reproduce the filesystem effect and final file size, not the
    # original random byte pattern. Earlier versions filled every replay byte in
    # PowerShell, which made large files such as 99 MB or 149 MB appear to hang
    # near the end of a 1000-action replay. Use FileStream.SetLength instead:
    # it is deterministic, fast, and still creates/rewrites the file to the
    # logged size.
    Ensure-ReplayParent $Path
    if ($Length -lt 0) { $Length = 0 }
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
    try {
        $stream.SetLength([int64]$Length)
        if ($Length -gt 0) {
            # Write a tiny replay signature at the beginning so the file is not
            # purely sparse/zero in all environments. This is intentionally small
            # and does not change the requested final size.
            $signature = [System.Text.Encoding]::ASCII.GetBytes('GFSAREPLAY')
            $toWrite = [Math]::Min([int64]$signature.Length, [int64]$Length)
            $stream.Position = 0
            $stream.Write($signature, 0, [int]$toWrite)
        }
    }
    finally {
        $stream.Close()
    }
}
function ConvertTo-CsvCell {
    param([object]$Value)
    if ($null -eq $Value) { return '' }
    $s = [string]$Value
    if ($s -match '[,"`r`n]') { return ('"{0}"' -f $s.Replace('"','""')) }
    return $s
}

function Write-CsvRow {
    param([System.IO.StreamWriter]$Writer, [hashtable]$Row)
    $cols = @('Sequence','TimestampUTC','Action','Result','SourcePath','DestPath','Details','Error')
    $Writer.WriteLine(($cols | ForEach-Object { ConvertTo-CsvCell $Row[$_] }) -join ',')
}

function New-Result {
    param(
        [int]$Sequence,
        [string]$Action,
        [string]$Result,
        [string]$Source = '',
        [string]$Dest = '',
        [string]$Details = '',
        [string]$ErrorMessage = ''
    )
    return @{
        Sequence = $Sequence
        TimestampUTC = [DateTime]::UtcNow.ToString('o')
        Action = $Action
        Result = $Result
        SourcePath = $Source
        DestPath = $Dest
        Details = $Details
        Error = $ErrorMessage
    }
}

function Get-DetailInt {
    param([string]$Details, [string]$Name, [int]$Default = 0)
    if ([string]::IsNullOrWhiteSpace($Details)) { return $Default }
    $pattern = ('{0}=([0-9]+)' -f [regex]::Escape($Name))
    $m = [regex]::Match($Details, $pattern)
    if ($m.Success) { return [int]$m.Groups[1].Value }
    return $Default
}

function Get-DetailText {
    param([string]$Details, [string]$Name, [string]$Default = '')
    if ([string]::IsNullOrWhiteSpace($Details)) { return $Default }
    $pattern = ('{0}=([^;]+)' -f [regex]::Escape($Name))
    $m = [regex]::Match($Details, $pattern)
    if ($m.Success) { return [string]$m.Groups[1].Value }
    return $Default
}

function New-ReplayBytes {
    param([int]$Length)
    if ($Length -lt 0) { $Length = 0 }
    $bytes = New-Object byte[] $Length
    # Deterministic simple pattern; enough to recreate file size and write activity.
    for ($i = 0; $i -lt $bytes.Length; $i++) { $bytes[$i] = [byte]($i % 251) }
    return ,$bytes
}

function Ensure-ReplayParent {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return }

    # Windows PowerShell 5.1 can raise "Parameter set cannot be resolved"
    # with Split-Path -LiteralPath -Parent in some contexts. Use .NET only.
    $parent = ''
    try { $parent = [System.IO.Path]::GetDirectoryName($Path) } catch { $parent = '' }

    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not [System.IO.Directory]::Exists($parent)) {
        [System.IO.Directory]::CreateDirectory($parent) | Out-Null
    }
}

function Get-RowText {
    param([object]$Row, [string]$Name, [string]$Default = '')
    try {
        if ($null -eq $Row) { return $Default }
        if ($Row -is [hashtable]) {
            if ($Row.ContainsKey($Name) -and $null -ne $Row[$Name]) { return [string]$Row[$Name] }
            return $Default
        }
        $prop = $Row.PSObject.Properties[$Name]
        if ($null -ne $prop -and $null -ne $prop.Value) { return [string]$prop.Value }
    }
    catch { }
    return $Default
}

function Get-RowInt {
    param([object]$Row, [string]$Name, [int]$Default = 0)
    $txt = Get-RowText $Row $Name ''
    $value = 0
    if ([int]::TryParse($txt, [ref]$value)) { return $value }
    return $Default
}

function Convert-ReplayPath {
    param([string]$Path, [string]$OriginalRoot, [string]$NewRoot)
    if ([string]::IsNullOrWhiteSpace($Path)) { return '' }

    # JSON replay supports remapping from the original root to a new root.
    # Be deliberately conservative and do not depend on the current directory.
    if (-not [string]::IsNullOrWhiteSpace($OriginalRoot) -and -not [string]::IsNullOrWhiteSpace($NewRoot)) {
        try {
            $oldFull = [System.IO.Path]::GetFullPath($OriginalRoot)
            $newFull = [System.IO.Path]::GetFullPath($NewRoot)
            $pathFull = [System.IO.Path]::GetFullPath($Path)

            $oldNorm = $oldFull.TrimEnd([char[]]@('\','/'))
            $pathNorm = $pathFull.TrimEnd([char[]]@('\','/'))

            if ($pathNorm.Equals($oldNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $newFull
            }

            $oldPrefix = ('{0}{1}' -f $oldNorm, [System.IO.Path]::DirectorySeparatorChar)
            if ($pathFull.StartsWith($oldPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $relative = $pathFull.Substring($oldPrefix.Length)
                return (Join-Path $newFull $relative)
            }
        }
        catch { }
    }

    return $Path
}

function New-ReplayFallbackPath {
    param([int]$Sequence, [string]$Action, [string]$NewRoot)
    $root = $NewRoot
    if ([string]::IsNullOrWhiteSpace($root)) {
        if (-not [string]::IsNullOrWhiteSpace($RootDir)) { $root = $RootDir } else { $root = (Get-Location).Path }
    }
    New-Item -Path $root -ItemType Directory -Force | Out-Null
    $safeAction = ($Action -replace '[^A-Za-z0-9_\-]', '_').ToLowerInvariant()
    $prefix = if ([string]::IsNullOrWhiteSpace($FileMarker)) { 'replay' } else { $FileMarker }
    return (Join-Path $root ("{0}_replay_{1}_{2:D6}.tmp" -f $prefix, $safeAction, $Sequence))
}

function Ensure-ReplayFileExists {
    param([string]$Path)
    Ensure-ReplayParent $Path
    if (-not (Test-FSFile $Path)) {
        Write-ReplayFileBytesChunked $Path 128
    }
}

function Ensure-ReplayDirExists {
    param([string]$Path)
    if (-not [string]::IsNullOrWhiteSpace($Path)) {
        New-Item -Path $Path -ItemType Directory -Force | Out-Null
    }
}

function Invoke-ReplayRow {
    param([object]$Row, [string]$OriginalRoot, [string]$NewRoot)

    $seq = Get-RowInt $Row 'Sequence' 0
    $action = Get-RowText $Row 'Action' ''
    $srcOriginal = Get-RowText $Row 'SourcePath' ''
    $dstOriginal = Get-RowText $Row 'DestPath' ''
    $src = Convert-ReplayPath $srcOriginal $OriginalRoot $NewRoot
    $dst = Convert-ReplayPath $dstOriginal $OriginalRoot $NewRoot
    $details = Get-RowText $Row 'Details' ''

    if ([string]::IsNullOrWhiteSpace($action)) {
        return New-Result $seq 'UNKNOWN' 'SKIP' '' '' 'replay=true;missing action name' 'Replay row has no Action field.'
    }

    try {
        switch ($action) {
            'CREATE_FILE' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayParent $src
                if (Test-FSDirectory $src) { Remove-Item -LiteralPath $src -Recurse -Force }
                $bytesLen = Get-DetailInt $details 'bytes' 128
                Write-ReplayFileBytesChunked $src ([int64]$bytesLen)
                return New-Result $seq $action 'OK' $src '' "replay=true;$details"
            }

            'CREATE_MARKED_FILE' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayParent $src
                $markerB64 = Get-DetailText $details 'marker_b64' ''
                $markerText = 'REPLAY_MARKED_CONTENT'
                if (-not [string]::IsNullOrWhiteSpace($markerB64)) {
                    try { $markerText = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($markerB64)) } catch { }
                }
                $content = @(
                    'Generate-FSActivity replayed marked content file',
                    ('Marker: {0}' -f $markerText),
                    ('ReplayedUTC: {0}' -f [DateTime]::UtcNow.ToString('o')),
                    ('Path: {0}' -f $src)
                ) -join [Environment]::NewLine
                $utf8BomLocal = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $true
                [System.IO.File]::WriteAllText($src, $content, $utf8BomLocal)
                return New-Result $seq $action 'OK' $src '' "replay=true;$details"
            }
            'CREATE_DIR' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = Join-Path $NewRoot ("replay_dir_{0:D6}" -f $seq) }
                New-Item -Path $src -ItemType Directory -Force | Out-Null
                return New-Result $seq $action 'OK' $src '' 'replay=true'
            }
            'WRITE_FILE' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayParent $src
                $bytesLen = Get-DetailInt $details 'bytes' 128
                Write-ReplayFileBytesChunked $src ([int64]$bytesLen)
                return New-Result $seq $action 'OK' $src '' "replay=true;$details"
            }
            'APPEND_FILE' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayFileExists $src
                $bytesLen = Get-DetailInt $details 'appended_bytes' 128
                if ($bytesLen -lt 0) { $bytesLen = 0 }
                $stream = [System.IO.File]::Open($src, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::Read)
                try {
                    $newLength = ([int64]$stream.Length) + ([int64]$bytesLen)
                    $stream.SetLength([int64]$newLength)
                    if ($bytesLen -gt 0) {
                        $signature = [System.Text.Encoding]::ASCII.GetBytes('GFSAPPEND')
                        $toWrite = [Math]::Min([int64]$signature.Length, [int64]$bytesLen)
                        $stream.Position = ([int64]$newLength) - ([int64]$bytesLen)
                        $stream.Write($signature, 0, [int]$toWrite)
                    }
                }
                finally { $stream.Dispose() }
                return New-Result $seq $action 'OK' $src '' "replay=true;$details"
            }
            'DELETE_FILE' {
                if (-not [string]::IsNullOrWhiteSpace($src) -and (Test-FSFile $src)) {
                    [System.IO.File]::SetAttributes($src, [System.IO.FileAttributes]::Normal)
                    [System.IO.File]::Delete($src)
                }
                return New-Result $seq $action 'OK' $src '' 'replay=true;missing source treated as already deleted'
            }
            'DELETE_DIR' {
                if (-not [string]::IsNullOrWhiteSpace($src) -and (Test-FSDirectory $src)) {
                    try { [System.IO.Directory]::Delete($src, $false) }
                    catch { return New-Result $seq $action 'SKIP' $src '' 'replay=true;directory not empty or locked' $_.Exception.Message }
                }
                return New-Result $seq $action 'OK' $src '' 'replay=true;empty directory only;missing source treated as already deleted'
            }
            { $_ -in @('RENAME_FILE','MOVE_FILE') } {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                if ([string]::IsNullOrWhiteSpace($dst)) { $dst = New-ReplayFallbackPath $seq ('{0}_dst' -f $action) $NewRoot }
                Ensure-ReplayFileExists $src
                Ensure-ReplayParent $dst
                if (Test-FSAny $dst) { Remove-Item -LiteralPath $dst -Force -Recurse }
                [System.IO.File]::Move($src, $dst)
                return New-Result $seq $action 'OK' $src $dst 'replay=true'
            }
            { $_ -in @('RENAME_DIR','MOVE_DIR') } {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = Join-Path $NewRoot ("replay_dir_src_{0:D6}" -f $seq) }
                if ([string]::IsNullOrWhiteSpace($dst)) { $dst = Join-Path $NewRoot ("replay_dir_dst_{0:D6}" -f $seq) }
                Ensure-ReplayDirExists $src
                Ensure-ReplayParent $dst
                if (Test-FSAny $dst) { Remove-Item -LiteralPath $dst -Force -Recurse }
                [System.IO.Directory]::Move($src, $dst)
                return New-Result $seq $action 'OK' $src $dst 'replay=true'
            }
            'COPY_FILE' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                if ([string]::IsNullOrWhiteSpace($dst)) { $dst = New-ReplayFallbackPath $seq ('{0}_dst' -f $action) $NewRoot }
                Ensure-ReplayFileExists $src
                Ensure-ReplayParent $dst
                [System.IO.File]::Copy($src, $dst, $true)
                return New-Result $seq $action 'OK' $src $dst 'replay=true'
            }
            'SET_TIMESTAMPS' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayFileExists $src
                $ts = [DateTime]::UtcNow
                if (-not [string]::IsNullOrWhiteSpace($details)) {
                    try { $ts = [DateTime]::Parse($details).ToUniversalTime() } catch { }
                }
                [System.IO.File]::SetCreationTimeUtc($src, $ts)
                [System.IO.File]::SetLastWriteTimeUtc($src, $ts)
                [System.IO.File]::SetLastAccessTimeUtc($src, $ts)
                return New-Result $seq $action 'OK' $src '' "replay=true;$($ts.ToString('o'))"
            }
            'CREATE_HARDLINK' {
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                if ([string]::IsNullOrWhiteSpace($dst)) { $dst = New-ReplayFallbackPath $seq ('{0}_link' -f $action) $NewRoot }
                Ensure-ReplayFileExists $src
                Ensure-ReplayParent $dst
                if (Test-FSAny $dst) { Remove-Item -LiteralPath $dst -Force }
                $ok = [FsActivityNative.Kernel32]::CreateHardLink($dst, $src, [IntPtr]::Zero)
                if (-not $ok) {
                    $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
                    $err = (New-Object -TypeName System.ComponentModel.Win32Exception -ArgumentList $code).Message
                    return New-Result $seq $action 'SKIP' $src $dst 'replay=true;hardlink unsupported or refused' $err
                }
                return New-Result $seq $action 'OK' $src $dst 'replay=true'
            }
            'CREATE_SYMLINK_FILE' {
                if (-not $Script:SymlinkEnabled) { return New-Result $seq $action 'SKIP' $src $dst 'replay=true;requires Administrator rights, Developer Mode, or SeCreateSymbolicLinkPrivilege' }
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                if ([string]::IsNullOrWhiteSpace($dst)) { $dst = New-ReplayFallbackPath $seq ('{0}_link' -f $action) $NewRoot }
                Ensure-ReplayFileExists $src
                Ensure-ReplayParent $dst
                if (Test-FSAny $dst) { Remove-Item -LiteralPath $dst -Force -Recurse }
                New-Item -ItemType SymbolicLink -Path $dst -Target $src -ErrorAction Stop | Out-Null
                return New-Result $seq $action 'OK' $src $dst 'replay=true'
            }
            'CREATE_ADS' {
                if ($SkipADS) { return New-Result $seq $action 'SKIP' $src '' 'replay=true;ADS disabled by -SkipADS' }
                if ([string]::IsNullOrWhiteSpace($src)) { $src = New-ReplayFallbackPath $seq $action $NewRoot }
                Ensure-ReplayFileExists $src
                $stream = 'replay_stream'
                $m = [regex]::Match($details, 'stream=([^;]+)')
                if ($m.Success) { $stream = $m.Groups[1].Value }
                Set-Content -LiteralPath $src -Stream $stream -Value "Replayed ADS at $([DateTime]::UtcNow.ToString('o'))" -ErrorAction Stop
                return New-Result $seq $action 'OK' $src '' "replay=true;stream=$stream"
            }
            default {
                return New-Result $seq $action 'SKIP' $src $dst 'replay=true;unknown action type'
            }
        }
    }
    catch {
        return New-Result $seq $action 'ERROR' $src $dst "replay=true;$details" $_.Exception.Message
    }
}

function Read-ReplayInput {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { throw "Replay file not found: $Path" }
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    if ($ext -eq '.json') {
        $obj = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        return [ordered]@{ OriginalRoot = [string]$obj.root_dir; Actions = @($obj.actions) }
    }
    if ($ext -eq '.csv') {
        return [ordered]@{ OriginalRoot = ''; Actions = @(Import-Csv -LiteralPath $Path) }
    }
    throw 'ReplayFile must be a .json replay file or .csv log file produced by this script.'
}

# -----------------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------------
function Invoke-CreateFile {
    param([int]$Seq, [System.Random]$Rng, [int]$LargeSizeMB = 0)
    $dir = Get-RandomDirectory $Rng
    $ext = $Exts[$Rng.Next($Exts.Count)]

    if ($LargeSizeMB -gt 0) {
        # Large files get a visible size marker in the filename, for example:
        # xbpt_large_2mb_alpha_123456.bin or xbpt_large_149mb_delta_654321.dat.
        $w1 = $Words[$Rng.Next($Words.Count)]
        $n = $Rng.Next(100000, 999999)
        $prefix = if ([string]::IsNullOrWhiteSpace($FileMarker)) { '' } else { "$FileMarker`_" }
        $largeName = ('{0}large_{1}mb_{2}_{3}{4}' -f $prefix, $LargeSizeMB, $w1, $n, $ext)
        $path = New-UniquePath $dir $largeName $Rng
    }
    else {
        $path = New-UniquePath $dir (New-RandomName $Rng $ext) $Rng
    }

    try {
        if ($LargeSizeMB -gt 0) {
            $size = [int64]$LargeSizeMB * 1024 * 1024
            $Script:LastGeneratedSizeKind = 'large'
            $Script:LastGeneratedSizeLabel = "target_mb=$LargeSizeMB;size_marker=${LargeSizeMB}mb"
            Write-RandomFileBytesChunked $path $size $Rng
            Refresh-Inventory
            return New-Result $Seq 'CREATE_FILE' 'OK' $path '' "bytes=$size;large_file=true;$($Script:LastGeneratedSizeLabel);chunked_write=true;protected_from_delete=true"
        }
        else {
            $bytes = New-ContentBytes $Rng $MaxFileSizeKB
            [System.IO.File]::WriteAllBytes($path, $bytes)
            Refresh-Inventory
            return New-Result $Seq 'CREATE_FILE' 'OK' $path '' "bytes=$($bytes.Length)"
        }
    }
    catch { return New-Result $Seq 'CREATE_FILE' 'ERROR' $path '' '' $_.Exception.Message }
}


function Invoke-CreateMarkedFile {
    param([int]$Seq, [System.Random]$Rng)

    $safeMarkerForName = ConvertTo-SafeNamePart $FileContentMarker
    if ([string]::IsNullOrWhiteSpace($safeMarkerForName)) { $safeMarkerForName = 'content' }
    if ($safeMarkerForName.Length -gt 32) { $safeMarkerForName = $safeMarkerForName.Substring(0, 32) }

    $prefix = if ([string]::IsNullOrWhiteSpace($FileMarker)) { '' } else { "$FileMarker`_" }
    $name = ('{0}marked_{1}_{2}.txt' -f $prefix, $safeMarkerForName, $Rng.Next(100000, 999999))
    $path = New-UniquePath $RootDir $name $Rng

    try {
        $content = @(
            'Generate-FSActivity marked content file',
            ('Marker: {0}' -f $FileContentMarker),
            ('CreatedUTC: {0}' -f [DateTime]::UtcNow.ToString('o')),
            ('Path: {0}' -f $path)
        ) -join [Environment]::NewLine
        $utf8BomLocal = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $true
        [System.IO.File]::WriteAllText($path, $content, $utf8BomLocal)
        Refresh-Inventory
        $bytes = [System.Text.Encoding]::UTF8.GetByteCount($content)
        $markerBytes = [System.Text.Encoding]::UTF8.GetBytes($FileContentMarker)
        $markerB64 = [Convert]::ToBase64String($markerBytes)
        return New-Result $Seq 'CREATE_MARKED_FILE' 'OK' $path '' "bytes=$bytes;marked_file=true;marker_b64=$markerB64"
    }
    catch { return New-Result $Seq 'CREATE_MARKED_FILE' 'ERROR' $path '' 'marked_file=true' $_.Exception.Message }
}

function Invoke-CreateDirectory {
    param([int]$Seq, [System.Random]$Rng)
    $parent = Get-RandomDirectory $Rng
    $path = New-UniquePath $parent (New-RandomDirectoryName $Rng) $Rng
    try {
        New-Item -Path $path -ItemType Directory -Force | Out-Null
        Refresh-Inventory
        return New-Result $Seq 'CREATE_DIR' 'OK' $path
    }
    catch { return New-Result $Seq 'CREATE_DIR' 'ERROR' $path '' '' $_.Exception.Message }
}

function Invoke-WriteFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    try {
        $bytes = New-ContentBytes $Rng $MaxFileSizeKB
        [System.IO.File]::WriteAllBytes($file, $bytes)
        $details = "bytes=$($bytes.Length)"
        if ($Script:LastGeneratedSizeKind -eq 'large') { $details = "$details;large_file=true;$($Script:LastGeneratedSizeLabel)" }
        return New-Result $Seq 'WRITE_FILE' 'OK' $file '' $details
    }
    catch { return New-Result $Seq 'WRITE_FILE' 'ERROR' $file '' '' $_.Exception.Message }
}

function Invoke-AppendFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    try {
        $bytes = New-ContentBytes $Rng ([Math]::Max(1, [int]($MaxFileSizeKB / 8)))
        $stream = [System.IO.File]::Open($file, [System.IO.FileMode]::Append, [System.IO.FileAccess]::Write)
        try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
        return New-Result $Seq 'APPEND_FILE' 'OK' $file '' "appended_bytes=$($bytes.Length)"
    }
    catch { return New-Result $Seq 'APPEND_FILE' 'ERROR' $file '' '' $_.Exception.Message }
}

function Invoke-DeleteFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    try {
        [System.IO.File]::SetAttributes($file, [System.IO.FileAttributes]::Normal)
        [System.IO.File]::Delete($file)
        Refresh-Inventory
        return New-Result $Seq 'DELETE_FILE' 'OK' $file
    }
    catch { return New-Result $Seq 'DELETE_FILE' 'ERROR' $file '' '' $_.Exception.Message }
}

function Invoke-DeleteDirectory {
    param([int]$Seq, [System.Random]$Rng)
    $dir = Get-LeafDirectory $Rng
    if (-not $dir) { return Invoke-CreateDirectory $Seq $Rng }
    try {
        [System.IO.Directory]::Delete($dir, $false)
        Refresh-Inventory
        return New-Result $Seq 'DELETE_DIR' 'OK' $dir '' 'empty directory only'
    }
    catch { return New-Result $Seq 'DELETE_DIR' 'ERROR' $dir '' '' $_.Exception.Message }
}

function Invoke-RenameFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $dir = Split-Path $file -Parent
    $ext = [System.IO.Path]::GetExtension($file)
    $dest = New-UniquePath $dir (New-RandomName $Rng $ext) $Rng
    try {
        [System.IO.File]::Move($file, $dest)
        Refresh-Inventory
        return New-Result $Seq 'RENAME_FILE' 'OK' $file $dest
    }
    catch { return New-Result $Seq 'RENAME_FILE' 'ERROR' $file $dest '' $_.Exception.Message }
}

function Invoke-RenameDirectory {
    param([int]$Seq, [System.Random]$Rng)
    $dir = Get-RandomDirectory $Rng -NonRoot
    if (-not $dir -or $dir -eq $RootDir) { return Invoke-CreateDirectory $Seq $Rng }
    $parent = Split-Path $dir -Parent
    $dest = New-UniquePath $parent (New-RandomDirectoryName $Rng) $Rng
    try {
        [System.IO.Directory]::Move($dir, $dest)
        Refresh-Inventory
        return New-Result $Seq 'RENAME_DIR' 'OK' $dir $dest
    }
    catch { return New-Result $Seq 'RENAME_DIR' 'ERROR' $dir $dest '' $_.Exception.Message }
}

function Invoke-MoveFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $targetDir = Get-RandomDirectory $Rng
    $ext = [System.IO.Path]::GetExtension($file)
    $dest = New-UniquePath $targetDir (New-RandomName $Rng $ext) $Rng
    try {
        [System.IO.File]::Move($file, $dest)
        Refresh-Inventory
        return New-Result $Seq 'MOVE_FILE' 'OK' $file $dest
    }
    catch { return New-Result $Seq 'MOVE_FILE' 'ERROR' $file $dest '' $_.Exception.Message }
}

function Invoke-MoveDirectory {
    param([int]$Seq, [System.Random]$Rng)
    $dir = Get-RandomDirectory $Rng -NonRoot
    if (-not $dir -or $dir -eq $RootDir) { return Invoke-CreateDirectory $Seq $Rng }
    $targetParent = Get-RandomDirectory $Rng
    if ($targetParent.StartsWith($dir, [System.StringComparison]::OrdinalIgnoreCase)) { $targetParent = $RootDir }
    $dest = New-UniquePath $targetParent (New-RandomDirectoryName $Rng) $Rng
    try {
        [System.IO.Directory]::Move($dir, $dest)
        Refresh-Inventory
        return New-Result $Seq 'MOVE_DIR' 'OK' $dir $dest
    }
    catch { return New-Result $Seq 'MOVE_DIR' 'ERROR' $dir $dest '' $_.Exception.Message }
}

function Invoke-CopyFile {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $targetDir = Get-RandomDirectory $Rng
    $ext = [System.IO.Path]::GetExtension($file)
    $dest = New-UniquePath $targetDir (New-RandomName $Rng $ext) $Rng
    try {
        [System.IO.File]::Copy($file, $dest, $false)
        Refresh-Inventory
        return New-Result $Seq 'COPY_FILE' 'OK' $file $dest
    }
    catch { return New-Result $Seq 'COPY_FILE' 'ERROR' $file $dest '' $_.Exception.Message }
}

function Invoke-SetTimestamps {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $days = $Rng.Next(1, 1825)
    $ts = [DateTime]::UtcNow.AddDays(-$days)
    try {
        [System.IO.File]::SetCreationTimeUtc($file, $ts)
        [System.IO.File]::SetLastWriteTimeUtc($file, $ts)
        [System.IO.File]::SetLastAccessTimeUtc($file, $ts)
        return New-Result $Seq 'SET_TIMESTAMPS' 'OK' $file '' $ts.ToString('o')
    }
    catch { return New-Result $Seq 'SET_TIMESTAMPS' 'ERROR' $file '' '' $_.Exception.Message }
}

function Invoke-CreateHardlink {
    param([int]$Seq, [System.Random]$Rng)
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $targetDir = Get-RandomDirectory $Rng
    $ext = [System.IO.Path]::GetExtension($file)
    $dest = New-UniquePath $targetDir (Add-FileMarkerPrefix "hardlink_$($Words[$Rng.Next($Words.Count)])_$($Rng.Next(100000,999999))$ext") $Rng
    try {
        $ok = [FsActivityNative.Kernel32]::CreateHardLink($dest, $file, [IntPtr]::Zero)
        if (-not $ok) {
            $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            throw (New-Object -TypeName System.ComponentModel.Win32Exception -ArgumentList $code)
        }
        Refresh-Inventory
        return New-Result $Seq 'CREATE_HARDLINK' 'OK' $file $dest
    }
    catch { return New-Result $Seq 'CREATE_HARDLINK' 'SKIP' $file $dest 'hard links may be unsupported on this file system or path' $_.Exception.Message }
}

function Invoke-CreateSymlinkFile {
    param([int]$Seq, [System.Random]$Rng)
    if (-not $Script:SymlinkEnabled) {
        return New-Result $Seq 'CREATE_SYMLINK_FILE' 'SKIP' '' '' 'requires Administrator rights, Developer Mode, or SeCreateSymbolicLinkPrivilege'
    }
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $targetDir = Get-RandomDirectory $Rng
    $dest = New-UniquePath $targetDir (Add-FileMarkerPrefix "symlink_$($Words[$Rng.Next($Words.Count)])_$($Rng.Next(100000,999999)).lnk") $Rng
    try {
        New-Item -ItemType SymbolicLink -Path $dest -Target $file -ErrorAction Stop | Out-Null
        Refresh-Inventory
        return New-Result $Seq 'CREATE_SYMLINK_FILE' 'OK' $file $dest
    }
    catch { return New-Result $Seq 'CREATE_SYMLINK_FILE' 'SKIP' $file $dest 'symbolic link creation failed' $_.Exception.Message }
}

function Invoke-CreateADS {
    param([int]$Seq, [System.Random]$Rng)
    if ($SkipADS) { return New-Result $Seq 'CREATE_ADS' 'SKIP' '' '' 'ADS disabled by -SkipADS' }
    $file = Get-RandomFile $Rng
    if (-not $file) { return Invoke-CreateFile $Seq $Rng }
    $stream = ('hidden_{0}' -f $Rng.Next(1000, 9999))
    try {
        $text = "Generated ADS at $([DateTime]::UtcNow.ToString('o'))"
        Set-Content -LiteralPath $file -Stream $stream -Value $text -ErrorAction Stop
        if (-not $Script:Ads.ContainsKey($file)) { $Script:Ads[$file] = New-Object 'System.Collections.Generic.List[string]' }
        $Script:Ads[$file].Add($stream)
        return New-Result $Seq 'CREATE_ADS' 'OK' $file '' "stream=$stream"
    }
    catch { return New-Result $Seq 'CREATE_ADS' 'SKIP' $file '' 'ADS not supported or not permitted on this file system' $_.Exception.Message }
}

function Add-FallbackCreateFileToSpecialResult {
    param([hashtable]$SpecialResult, [int]$Seq, [System.Random]$Rng)

    if ($null -eq $SpecialResult) { return Invoke-CreateFile $Seq $Rng }
    if ($SpecialResult.Result -eq 'OK') { return $SpecialResult }

    # Keep the special artefact attempt visible in the log, but perform a normal
    # CREATE_FILE as the replacement workload action when the special artefact is
    # unsupported or refused. This preserves Count while making the bypass clear.
    $fallback = Invoke-CreateFile $Seq $Rng
    $fallbackDetails = "fallback_action=CREATE_FILE;fallback_result=$($fallback.Result);fallback_path=$($fallback.SourcePath)"
    if (-not [string]::IsNullOrWhiteSpace($SpecialResult.Details)) {
        $SpecialResult.Details = "$($SpecialResult.Details);$fallbackDetails"
    }
    else {
        $SpecialResult.Details = $fallbackDetails
    }
    if (-not [string]::IsNullOrWhiteSpace($fallback.Error)) {
        if (-not [string]::IsNullOrWhiteSpace($SpecialResult.Error)) {
            $SpecialResult.Error = "$($SpecialResult.Error); fallback_error=$($fallback.Error)"
        }
        else {
            $SpecialResult.Error = "fallback_error=$($fallback.Error)"
        }
    }
    return $SpecialResult
}

function Invoke-ActionByName {
    param([string]$Name, [int]$Seq, [System.Random]$Rng)
    switch ($Name) {
        'CREATE_FILE'         { return Invoke-CreateFile $Seq $Rng }
        'CREATE_MARKED_FILE'  { return Invoke-CreateMarkedFile $Seq $Rng }
        'CREATE_DIR'          { return Invoke-CreateDirectory $Seq $Rng }
        'WRITE_FILE'          { return Invoke-WriteFile $Seq $Rng }
        'APPEND_FILE'         { return Invoke-AppendFile $Seq $Rng }
        'DELETE_FILE'         { return Invoke-DeleteFile $Seq $Rng }
        'DELETE_DIR'          { return Invoke-DeleteDirectory $Seq $Rng }
        'RENAME_FILE'         { return Invoke-RenameFile $Seq $Rng }
        'RENAME_DIR'          { return Invoke-RenameDirectory $Seq $Rng }
        'MOVE_FILE'           { return Invoke-MoveFile $Seq $Rng }
        'MOVE_DIR'            { return Invoke-MoveDirectory $Seq $Rng }
        'COPY_FILE'           { return Invoke-CopyFile $Seq $Rng }
        'SET_TIMESTAMPS'      { return Invoke-SetTimestamps $Seq $Rng }
        'CREATE_HARDLINK'     { return Add-FallbackCreateFileToSpecialResult (Invoke-CreateHardlink $Seq $Rng) $Seq $Rng }
        'CREATE_SYMLINK_FILE' { return Add-FallbackCreateFileToSpecialResult (Invoke-CreateSymlinkFile $Seq $Rng) $Seq $Rng }
        'CREATE_ADS'          { return Add-FallbackCreateFileToSpecialResult (Invoke-CreateADS $Seq $Rng) $Seq $Rng }
        default               { return Invoke-CreateFile $Seq $Rng }
    }
}

function Pick-ActionName {
    param([int]$Seq, [System.Random]$Rng)

    Refresh-Inventory

    # The first actions deliberately seed the directory with useful material.
    if ($Script:Files.Count -lt 5) { return 'CREATE_FILE' }
    if ($Script:Dirs.Count -lt 3)  { return 'CREATE_DIR' }

    # Weighted pool. Creation stays common so delete/move/rename actions always
    # have material to operate on.
    $pool = @(
        'CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE',
        'CREATE_DIR','CREATE_DIR',
        'WRITE_FILE','WRITE_FILE',
        'APPEND_FILE','APPEND_FILE',
        'DELETE_FILE','DELETE_FILE',
        'DELETE_DIR',
        'RENAME_FILE','RENAME_FILE',
        'RENAME_DIR',
        'MOVE_FILE','MOVE_FILE',
        'MOVE_DIR',
        'COPY_FILE','COPY_FILE',
        'SET_TIMESTAMPS',
        'CREATE_HARDLINK',
        'CREATE_SYMLINK_FILE',
        'CREATE_ADS'
    )

    return $pool[$Rng.Next($pool.Count)]
}


function Set-PlanActionAtOrAfter {
    param(
        [System.Collections.Generic.List[string]]$Plan,
        [int]$PreferredIndex,
        [string]$ActionName,
        [string[]]$ProtectedActions = @()
    )

    if ($Plan.Count -le 0) { return -1 }
    if ($PreferredIndex -lt 0) { $PreferredIndex = 0 }
    if ($PreferredIndex -ge $Plan.Count) { $PreferredIndex = [int]($Plan.Count - 1) }

    $protected = @{}
    foreach ($pa in @($ProtectedActions)) {
        if (-not [string]::IsNullOrWhiteSpace($pa)) { $protected[[string]$pa] = $true }
    }

    for ($offset = 0; $offset -lt $Plan.Count; $offset++) {
        $idx = [int]((([int]$PreferredIndex + [int]$offset) % [int]$Plan.Count))
        $current = [string]$Plan[$idx]
        if (-not $protected.ContainsKey($current)) {
            $Plan[$idx] = $ActionName
            return $idx
        }
    }

    $Plan[$PreferredIndex] = $ActionName
    return $PreferredIndex
}

function New-ActionPlan {
    param(
        [int]$TotalCount,
        [int[]]$LargeSizes,
        [bool]$IncludeMarkedFile,
        [System.Random]$Rng,
        [bool]$HeavySpecialMode = $false,
        [int]$EveryN = 0
    )

    $largeCount = [int](@($LargeSizes).Count)
    $markedCount = if ($IncludeMarkedFile) { 1 } else { 0 }
    $reservedTailCount = [int]($largeCount + $markedCount)
    $planCountBeforeTail = [int]($TotalCount - $reservedTailCount)
    if ($planCountBeforeTail -lt 0) {
        throw "Count must be at least $reservedTailCount for the requested large files and marked file."
    }

    # Frequency of special artefacts. Default mode keeps the baseline:
    # one full set per 250 actions. -HeavySpcials defaults to one set per
    # 25 actions. SpecialEveryN overrides both defaults when non-zero.
    $effectiveEveryN = [int]$EveryN
    if ($effectiveEveryN -le 0) {
        if ($HeavySpecialMode) { $effectiveEveryN = 25 }
        else { $effectiveEveryN = 250 }
    }
    if ($effectiveEveryN -lt 1) { $effectiveEveryN = 1 }

    $specialSetCount = [int][Math]::Floor(([double]$TotalCount) / [double]$effectiveEveryN)
    if ($TotalCount -gt 100 -and $specialSetCount -lt 1) { $specialSetCount = 1 }
    $specialActionCount = [int]($specialSetCount * 3)

    # Directory creation target: about 5% of Count in both normal and heavy-special runs.
    $directoryCreateTarget = [int][Math]::Floor(([double]$TotalCount) * 0.05)
    if ($TotalCount -gt 100 -and $directoryCreateTarget -lt 1) { $directoryCreateTarget = 1 }

    $minimumRequired = [int]($reservedTailCount + $specialActionCount + $directoryCreateTarget)
    if ($TotalCount -lt $minimumRequired) {
        throw "Count must be at least $minimumRequired for the requested workload: $largeCount large files plus $markedCount marked content file plus $specialActionCount special action attempts plus $directoryCreateTarget directory creation attempts. Increase Count or increase SpecialEveryN."
    }

    $normalCount = [int]($TotalCount - $reservedTailCount)
    $plan = New-Object 'System.Collections.Generic.List[string]'

    # Weighted pool. -HeavySpcials keeps enough normal operations to supply
    # targets, but strongly biases the plan toward special artefacts.
    if ($HeavySpecialMode) {
        $basePool = @(
            'CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE',
            'CREATE_DIR','CREATE_DIR',
            'WRITE_FILE','APPEND_FILE','COPY_FILE','SET_TIMESTAMPS',
            'RENAME_FILE','MOVE_FILE','DELETE_FILE','RENAME_DIR','MOVE_DIR','DELETE_DIR',
            'CREATE_HARDLINK','CREATE_HARDLINK','CREATE_HARDLINK','CREATE_HARDLINK',
            'CREATE_SYMLINK_FILE','CREATE_SYMLINK_FILE','CREATE_SYMLINK_FILE','CREATE_SYMLINK_FILE',
            'CREATE_ADS','CREATE_ADS','CREATE_ADS','CREATE_ADS'
        )
    }
    else {
        $basePool = @(
            'CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE',
            'WRITE_FILE','WRITE_FILE','WRITE_FILE',
            'APPEND_FILE','APPEND_FILE',
            'DELETE_FILE','DELETE_FILE',
            'DELETE_DIR',
            'RENAME_FILE','RENAME_FILE',
            'RENAME_DIR',
            'MOVE_FILE','MOVE_FILE',
            'MOVE_DIR',
            'COPY_FILE','COPY_FILE',
            'SET_TIMESTAMPS','SET_TIMESTAMPS'
        )
    }

    for ($i = 1; $i -le $normalCount; $i++) {
        [void]$plan.Add([string]$basePool[$Rng.Next($basePool.Count)])
    }

    # Ensure useful setup material at the beginning.
    $setup = @('CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_FILE','CREATE_DIR','CREATE_DIR')
    for ($s = 0; $s -lt $setup.Count -and $s -lt $plan.Count; $s++) { $plan[$s] = [string]$setup[$s] }

    # Ensure core actions appear at least once for Count > 100.
    if ($TotalCount -gt 100 -and $plan.Count -gt 0) {
        $mandatoryCore = @(
            'CREATE_FILE','WRITE_FILE','APPEND_FILE','DELETE_FILE','DELETE_DIR',
            'RENAME_FILE','RENAME_DIR','MOVE_FILE','MOVE_DIR','COPY_FILE','SET_TIMESTAMPS'
        )
        for ($m = 0; $m -lt $mandatoryCore.Count; $m++) {
            $preferred = [int][Math]::Floor((([double]($m + 1) * [double]$plan.Count) / [double]($mandatoryCore.Count + 1)))
            [void](Set-PlanActionAtOrAfter -Plan $plan -PreferredIndex $preferred -ActionName ([string]$mandatoryCore[$m]) -ProtectedActions @('CREATE_HARDLINK','CREATE_SYMLINK_FILE','CREATE_ADS'))
        }
    }

    # Force special artefact attempts according to effective frequency.
    if ($specialSetCount -gt 0 -and $plan.Count -gt 0) {
        $actionsForBlock = @('CREATE_HARDLINK','CREATE_SYMLINK_FILE','CREATE_ADS')
        for ($g = 0; $g -lt $specialSetCount; $g++) {
            $blockStart = [int]($g * $effectiveEveryN)
            if ($blockStart -ge $plan.Count) {
                $blockStart = [int][Math]::Floor((([double]($g + 1) * [double]$plan.Count) / [double]($specialSetCount + 1)))
            }
            for ($s = 0; $s -lt $actionsForBlock.Count; $s++) {
                $position = [int]($blockStart + 20 + $s)
                [void](Set-PlanActionAtOrAfter -Plan $plan -PreferredIndex $position -ActionName ([string]$actionsForBlock[$s]) -ProtectedActions @('CREATE_HARDLINK','CREATE_SYMLINK_FILE','CREATE_ADS'))
            }
        }
    }

    # Force CREATE_DIR actions. These must not overwrite mandatory specials.
    if ($directoryCreateTarget -gt 0 -and $plan.Count -gt 0) {
        for ($d = 0; $d -lt $directoryCreateTarget; $d++) {
            if ($d -eq 0) { $preferred = 5 }
            else { $preferred = [int][Math]::Floor((([double]($d + 1) * [double]$plan.Count) / [double]($directoryCreateTarget + 1))) }
            [void](Set-PlanActionAtOrAfter -Plan $plan -PreferredIndex $preferred -ActionName 'CREATE_DIR' -ProtectedActions @('CREATE_HARDLINK','CREATE_SYMLINK_FILE','CREATE_ADS','CREATE_DIR'))
        }
    }

    # Add the marked-content file near the end so later destructive actions do not
    # accidentally rename or delete it. It is still part of Count.
    if ($IncludeMarkedFile) { [void]$plan.Add('CREATE_MARKED_FILE') }

    foreach ($mb in @($LargeSizes)) { [void]$plan.Add(('CREATE_LARGE_FILE:{0}' -f $mb)) }

    if ($plan.Count -ne $TotalCount) {
        throw "Internal scheduler error: planned $($plan.Count) actions but Count is $TotalCount."
    }

    return $plan
}

function Show-FSActivityUsage {
    Write-Host ''
    Write-Host 'Generate-FSActivity.ps1 v3.20 - filesystem workload generator'
    Write-Host '============================================================='
    Write-Host ''
    Write-Host 'Required for a normal run:'
    Write-Host '  -RootDir <path>    Directory/disk location where actions are generated.'
    Write-Host '  -LogDir  <path>    Directory where CSV log, replay JSON and report are written.'
    Write-Host ''
    Write-Host 'Important options:'
    Write-Host '  -Count <n>                 Total number of logged actions. Large files and marked file are included.'
    Write-Host '  -FileMarker xbpt           Prefix added to generated file names.'
    Write-Host '  -DirMarker elvis           Prefix added to generated directory names.'
    Write-Host '  -FileContentMarker TEXT    Creates exactly one text file whose name contains "marked" and whose content contains TEXT.'
    Write-Host '  -LargeFileSizeMB 2,86,7    Creates one protected chunked large file per listed value; included in Count. Filename contains 2mb, 86mb, etc.'
    Write-Host '  -HeavySpcials              Heavy special-artefact mode: many ADS/hardlink/symlink attempts.'
    Write-Host '  -SpecialEveryN 10           One full set of hardlink/symlink/ADS per N actions. 0 = default frequency.'
    Write-Host '  -CleanRoot                 Deletes RootDir contents before the run.'
    Write-Host '  -ReplayFile <json|csv>     Replays a previous JSON replay file or CSV log; replay uses fast size-preserving writes for large files.'
    Write-Host ''
    Write-Host 'Scheduler rules:'
    Write-Host '  * About 5% of Count is planned as CREATE_DIR. Some directories may later be renamed, moved, or deleted.'
    Write-Host '  * DELETE_FILE, DELETE_DIR, RENAME_FILE, RENAME_DIR, MOVE_FILE, MOVE_DIR, COPY_FILE and timestamps remain enabled for normal files/directories.'
    Write-Host '  * Special artefact frequency is controlled by -HeavySpcials and -SpecialEveryN.'
    Write-Host '  * For Count > 100, the plan tries to include almost every action type at least once.'
    Write-Host '  * Unsupported symlink/hardlink/ADS actions are logged as SKIP with a clear reason and replaced by fallback file creation.'
    Write-Host '  * Requested large files are created at the end and are protected from later delete/rename/move actions.'
    Write-Host ''
    Write-Host 'Examples:'
    Write-Host '  .\Generate-FSActivity.ps1 -RootDir C:\test1 -Count 1000 -LogDir C:\logs -FileMarker xbpt -DirMarker elvis -FileContentMarker XBPT_MARK -LargeFileSizeMB 2,86,7,5,149 -CleanRoot'
    Write-Host '  .\Generate-FSActivity.ps1 -RootDir C:\specials -Count 1000 -LogDir C:\logs -HeavySpcials -SpecialEveryN 10 -CleanRoot'
    Write-Host '  .\Generate-FSActivity.ps1 -ReplayFile C:\logs\fsactivity_YYYYMMDD_HHMMSS_replay.json -RootDir C:\test2 -LogDir C:\logs -CleanRoot'
    Write-Host ''
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
$ReplayMode = -not [string]::IsNullOrWhiteSpace($ReplayFile)

if ($MyInvocation.BoundParameters.Count -eq 0) {
    Show-FSActivityUsage
    return
}

if (-not $ReplayMode -and [string]::IsNullOrWhiteSpace($RootDir)) {
    throw 'RootDir is required unless -ReplayFile is used.'
}

if (-not [string]::IsNullOrWhiteSpace($RootDir)) {
    $RootDir = [System.IO.Path]::GetFullPath($RootDir)
}
if ($Count -lt 1) { throw 'Count must be at least 1.' }
if ($SpecialEveryN -lt 0) { throw 'SpecialEveryN must be 0 or greater. Use 0 for the default frequency.' }
$LogDir = [System.IO.Path]::GetFullPath($LogDir)

if ($CleanRoot -and -not [string]::IsNullOrWhiteSpace($RootDir) -and (Test-Path -LiteralPath $RootDir)) {
    Remove-Item -LiteralPath $RootDir -Recurse -Force
}

if (-not [string]::IsNullOrWhiteSpace($RootDir)) {
    New-Item -Path $RootDir -ItemType Directory -Force | Out-Null
}
New-Item -Path $LogDir -ItemType Directory -Force | Out-Null


if ($ReplayMode) {
    $replayInput = Read-ReplayInput $ReplayFile
    $originalRoot = [string]$replayInput.OriginalRoot
    $newRoot = $RootDir
    if (-not [string]::IsNullOrWhiteSpace($newRoot)) { New-Item -Path $newRoot -ItemType Directory -Force | Out-Null }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $csvPath = Join-Path $LogDir "fsactivity_${timestamp}_replay_log.csv"
    $reportPath = Join-Path $LogDir "fsactivity_${timestamp}_replay_report.txt"
    $utf8Bom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $true
    $actions = New-Object 'System.Collections.Generic.List[hashtable]'
    $stats = @{}
    $firstErrors = New-Object 'System.Collections.Generic.List[string]'
    $sw = [System.Diagnostics.Stopwatch]::StartNew()

    Write-Host ''
    Write-Host '+- Generate-FSActivity v3.20 REPLAY ----------------------------------------'
    Write-Host "| Input       : $ReplayFile"
    Write-Host "| OriginalRoot: $originalRoot"
    Write-Host "| ReplayRoot  : $newRoot"
    Write-Host "| Actions     : $(@($replayInput.Actions).Count)"
    Write-Host "| Admin       : $Script:IsAdmin"
    Write-Host "| DevMode     : $Script:IsDeveloperMode"
    Write-Host "| Symlinks    : $Script:SymlinkEnabled"
    Write-Host '+----------------------------------------------------------------------------'

    $writer = New-Object -TypeName System.IO.StreamWriter -ArgumentList $csvPath, $false, $utf8Bom
    try {
        $writer.WriteLine('Sequence,TimestampUTC,Action,Result,SourcePath,DestPath,Details,Error')
        foreach ($rowIn in @($replayInput.Actions)) {
            if ([string]$rowIn.Result -and [string]$rowIn.Result -ne 'OK') {
                # The original action was already skipped or failed; keep it as SKIP in the replay log.
                $row = New-Result ([int]$rowIn.Sequence) ([string]$rowIn.Action) 'SKIP' ([string]$rowIn.SourcePath) ([string]$rowIn.DestPath) 'replay=true;original action was not OK' ([string]$rowIn.Error)
            }
            else {
                $row = Invoke-ReplayRow $rowIn $originalRoot $newRoot
            }
            Write-CsvRow $writer $row
            $actions.Add($row) | Out-Null
            $key = "$($row.Action)|$($row.Result)"
            if (-not $stats.ContainsKey($key)) {
                $stats[$key] = 1
            }
            else {
                $stats[$key] = [int]$stats[$key] + 1
            }
            if (($row.Result -eq 'ERROR' -or $row.Result -eq 'SKIP') -and -not [string]::IsNullOrWhiteSpace($row.Error) -and $firstErrors.Count -lt 10) {
                $firstErrors.Add(("#{0} {1}/{2}: {3}" -f $row.Sequence, $row.Action, $row.Result, $row.Error)) | Out-Null
            }
            if (($actions.Count % 100) -eq 0) { Write-Host ("`r  Replay progress: {0}/{1}  " -f $actions.Count, @($replayInput.Actions).Count) -NoNewline }
        }
    }
    finally {
        $writer.Flush()
        $writer.Dispose()
    }
    $sw.Stop()
    if (-not [string]::IsNullOrWhiteSpace($newRoot)) { Refresh-Inventory }

    $report = New-Object 'System.Collections.Generic.List[string]'
    $report.Add('GENERATE-FSACTIVITY v3.20 - REPLAY REPORT') | Out-Null
    $report.Add('===========================================') | Out-Null
    $report.Add("Replay input : $ReplayFile") | Out-Null
    $report.Add("OriginalRoot : $originalRoot") | Out-Null
    $report.Add("ReplayRoot   : $newRoot") | Out-Null
    $report.Add("Actions      : $($actions.Count)") | Out-Null
    $report.Add("Duration     : $($sw.Elapsed.ToString())") | Out-Null
    $report.Add("CSV log      : $csvPath") | Out-Null
    $report.Add('') | Out-Null
    $report.Add('Action statistics:') | Out-Null
    foreach ($key in ($stats.Keys | Sort-Object)) { $report.Add(("  {0,-35} {1,6}" -f $key, $stats[$key])) | Out-Null }
    if ($firstErrors.Count -gt 0) {
        $report.Add('') | Out-Null
        $report.Add('First replay errors/skips:') | Out-Null
        foreach ($e in $firstErrors) { $report.Add("  $e") | Out-Null }
    }
    $report.Add('') | Out-Null
    $report.Add('Replay note: JSON replay files support root remapping from original root_dir to -RootDir. Missing parents and missing replay sources are recreated when required, and the Error column contains the real exception for remaining failures. v3.18 uses fast replay sizing for large files with FileStream.SetLength, avoiding slow per-byte replay writes near the end of large workloads.') | Out-Null
    $report.Add('CSV log replay uses the paths stored in the CSV because the original root is not encoded separately.') | Out-Null
    $report.Add('Some privileged or filesystem-specific actions, such as symlinks or ADS, may be skipped without Administrator rights or filesystem support.') | Out-Null
    [System.IO.File]::WriteAllLines($reportPath, $report.ToArray(), $utf8Bom)

    Write-Host "`r                                                                                "
    Write-Host "Replay log   : $csvPath"
    Write-Host "Replay report: $reportPath"
    return
}

$effectiveSeed = if ($Seed -ge 0) { $Seed } else { [Environment]::TickCount -band 0x7fffffff }
$Rng = New-Object -TypeName System.Random -ArgumentList $effectiveSeed
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$csvPath = Join-Path $LogDir "fsactivity_${timestamp}_log.csv"
$jsonPath = Join-Path $LogDir "fsactivity_${timestamp}_replay.json"
$reportPath = Join-Path $LogDir "fsactivity_${timestamp}_report.txt"

Refresh-Inventory

Write-Host ''
Write-Host '+- Generate-FSActivity v3.20 -----------------------------------------------'
Write-Host "| Root        : $RootDir"
Write-Host "| Count       : $Count"
Write-Host "| Seed        : $effectiveSeed"
Write-Host "| Admin       : $Script:IsAdmin"
Write-Host "| DevMode     : $Script:IsDeveloperMode"
Write-Host "| Symlinks    : $Script:SymlinkEnabled"
Write-Host "| FileMarker  : $FileMarker"
Write-Host "| DirMarker   : $DirMarker"
Write-Host "| Normal max  : $MaxFileSizeKB KB"
Write-Host "| Large files : $(@($LargeFileSizeMB) -join ',') MB (one chunked file per listed value; included in Count)"
Write-Host "| Dir target  : about 5% CREATE_DIR actions"
Write-Host "| ContentMark : $FileContentMarker"
$displayEveryN = if ($SpecialEveryN -gt 0) { $SpecialEveryN } elseif ($HeavySpcials) { 25 } else { 250 }
Write-Host "| HeavySpcials: $HeavySpcials"
Write-Host "| Specials    : one hardlink/symlink/ADS set per $displayEveryN actions"
Write-Host '+----------------------------------------------------------------------------'

$actions = New-Object 'System.Collections.Generic.List[hashtable]'
$stats = @{}
$sw = [System.Diagnostics.Stopwatch]::StartNew()

$utf8Bom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $true
$writer = New-Object -TypeName System.IO.StreamWriter -ArgumentList $csvPath, $false, $utf8Bom
try {
    $writer.WriteLine('Sequence,TimestampUTC,Action,Result,SourcePath,DestPath,Details,Error')
    $actionPlan = New-ActionPlan -TotalCount $Count -LargeSizes @($LargeFileSizeMB) -IncludeMarkedFile (-not [string]::IsNullOrWhiteSpace($FileContentMarker)) -Rng $Rng -HeavySpecialMode ([bool]$HeavySpcials) -EveryN $SpecialEveryN

    for ($i = 1; $i -le $actionPlan.Count; $i++) {
        $planned = [string]$actionPlan[$i - 1]
        if ($planned.StartsWith('CREATE_LARGE_FILE:')) {
            $mb = [int]($planned.Substring('CREATE_LARGE_FILE:'.Length))
            $row = Invoke-CreateFile $i $Rng -LargeSizeMB $mb
        }
        else {
            $row = Invoke-ActionByName $planned $i $Rng
        }

        Write-CsvRow $writer $row
        $actions.Add($row) | Out-Null

        $key = "$($row.Action)|$($row.Result)"
        if (-not $stats.ContainsKey($key)) {
            $stats[$key] = 1
        }
        else {
            $stats[$key] = [int]$stats[$key] + 1
        }

        if (($i % 100) -eq 0) {
            Refresh-Inventory
            Write-Host ("`r  Progress: {0}/{1}  Files:{2}  Dirs:{3}  " -f $i, $Count, $Script:Files.Count, $Script:Dirs.Count) -NoNewline
        }
    }
}
finally {
    $writer.Flush()
    $writer.Dispose()
}

$sw.Stop()
Refresh-Inventory

$replayObject = [ordered]@{
    schema_version = '3.20'
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    seed = $effectiveSeed
    root_dir = $RootDir
    count = $Count
    count_semantics = 'total_logged_actions_including_large_files'
    file_marker = $FileMarker
    file_content_marker = $FileContentMarker
    dir_marker = $DirMarker
    max_file_size_kb = $MaxFileSizeKB
    large_file_size_mb = $LargeFileSizeMB
    large_file_mode = 'exactly_one_chunked_file_per_list_value'
    heavy_spcials = [bool]$HeavySpcials
    special_every_n = $SpecialEveryN
    actions = $actions.ToArray()
}
[System.IO.File]::WriteAllText($jsonPath, (ConvertTo-Json $replayObject -Depth 8), $utf8Bom)

$report = New-Object 'System.Collections.Generic.List[string]'
$report.Add('GENERATE-FSACTIVITY v3.20 - SUMMARY REPORT') | Out-Null
$report.Add('================================================') | Out-Null
$report.Add("Root        : $RootDir") | Out-Null
$report.Add("Seed        : $effectiveSeed") | Out-Null
$report.Add("Requested total actions : $Count") | Out-Null
$report.Add("Executed/logged actions : $($actions.Count)") | Out-Null
$report.Add("FileMarker  : $FileMarker") | Out-Null
$report.Add("DirMarker   : $DirMarker") | Out-Null
$report.Add("FileContentMarker : $FileContentMarker") | Out-Null
$report.Add("MaxFileSize : $MaxFileSizeKB KB normal files") | Out-Null
$report.Add("Large files : $(@($LargeFileSizeMB) -join ',') MB; exactly one protected chunked CREATE_FILE per listed value, duplicates preserved; included in Count; filename contains the size marker such as 2mb or 149mb") | Out-Null
$report.Add("HeavySpcials: $HeavySpcials") | Out-Null
$report.Add("SpecialEveryN: $SpecialEveryN (0 means default frequency)") | Out-Null
$report.Add("Specials    : CREATE_HARDLINK, CREATE_SYMLINK_FILE and CREATE_ADS frequency controlled by HeavySpcials/SpecialEveryN") | Out-Null
$report.Add("Directory target : about 5 percent CREATE_DIR actions; directories may later be renamed, moved or deleted") | Out-Null
$report.Add("Duration    : $($sw.Elapsed.ToString())") | Out-Null
$report.Add("Final files : $($Script:Files.Count)") | Out-Null
$report.Add("Final dirs  : $($Script:Dirs.Count)") | Out-Null
$report.Add("CSV log     : $csvPath") | Out-Null
$report.Add("Replay JSON : $jsonPath") | Out-Null
$report.Add('') | Out-Null
$report.Add('Important note: the final directory is not supposed to contain Count files.') | Out-Null
$report.Add('Some actions delete, rename, or move previous files/directories. The CSV log is the ground truth.') | Out-Null
$report.Add('Special artefact frequency is controlled by HeavySpcials and SpecialEveryN. Default behavior keeps one full set per 250 actions; -HeavySpcials increases the default to one full set per 25 actions, unless -SpecialEveryN is specified. Unsupported/permitted failures are logged as SKIP with the reason and a fallback CREATE_FILE is attempted in the same logged row. About 5 percent of Count is planned as CREATE_DIR, although some directories may later be renamed, moved, or deleted.') | Out-Null
$report.Add('Markers are applied to newly generated file/directory names. Use -CleanRoot if you want the final tree to contain only marker-generated names.') | Out-Null
$report.Add('') | Out-Null
$report.Add('Action statistics:') | Out-Null
foreach ($key in ($stats.Keys | Sort-Object)) {
    $report.Add(("  {0,-35} {1,6}" -f $key, $stats[$key])) | Out-Null
}
$report.Add('') | Out-Null
$report.Add('Admin / non-admin behavior:') | Out-Null
$report.Add('  Normal file creation, deletion, copy, rename, move, write and timestamp actions do not require Administrator rights.') | Out-Null
$report.Add('  Symbolic links may require Administrator rights, Windows Developer Mode, or SeCreateSymbolicLinkPrivilege.') | Out-Null
$report.Add('  Hard links and ADS may be unavailable depending on the target file system and permissions.') | Out-Null
[System.IO.File]::WriteAllLines($reportPath, $report.ToArray(), $utf8Bom)

Write-Host "`r                                                                                "
Write-Host "Files  : $($Script:Files.Count)"
Write-Host "Dirs   : $($Script:Dirs.Count)"
Write-Host "Log    : $csvPath"
Write-Host "Replay : $jsonPath"
Write-Host "Report : $reportPath"
