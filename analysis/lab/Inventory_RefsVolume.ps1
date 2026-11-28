# ============================================================================
#  Inventory_RefsVolume.ps1 v2 (2026-11-01) - the ground truth of a volume, taken by Windows
#
#  The one script to run at the end of every lab and before every acquisition:
#    .\Inventory_RefsVolume.ps1 -Drive L -Label labL
#    .\Inventory_RefsVolume.ps1 -Drive X -Label blindaudit2 -Journal -Security -Snapshots
#
#  Run it in an ELEVATED Windows PowerShell 5.1 console, as the LAST step before the image:
#  after it, take the disk offline and image it, with nothing in between.
#
#  Output: <OutRoot>\<Label>_<yyyyMMdd_HHmmss>\   (never on the inventoried volume unless -CopyToVolume)
#    inventory.csv  one row per entry, the root included as '.':
#                   RelPath, Kind, Size, Allocation, Created, Modified, Changed, Accessed
#                   (UTC, 100 ns, the form 2026-05-16T16:55:20.9805996Z), Attributes, ReparseTag,
#                   FileId (32 hex digits, as fsutil prints it), FileIdHi, FileIdLo, VolumeSerial,
#                   Links, AdsCount, SHA256, Error (the Win32 error of a failed query, else empty)
#    streams.csv    every named data stream of a file or directory: RelPath, Stream, Length, SHA256
#    hardlinks.csv  every name of every multi-link file (fsutil hardlink list)
#    reparse.txt    fsutil reparsepoint query for every entry with a reparse tag
#    snapshots.csv  refsutil streamsnapshot /l "*" per file                  (-Snapshots, slow)
#    security.csv   owner and SDDL of every entry                             (-Security)
#    journal.csv    Windows' own decode of the change journal                 (-Journal)
#    volume.txt     host, Windows build, refs.sys version + SHA-256, time zone, disk and partition
#                   geometry, refsinfo, volumeinfo, queryjournal, last-access policy, BitLocker state
#    errors.txt     everything that could not be read
#    transcript.txt the console transcript; SHA256SUMS.txt over every output file
#
#  Order: metadata of every entry first (pass 1), then the journal, then content (pass 2), because
#  reading content can touch LastAccess. Directory reparse points (junctions, directory symlinks) are
#  listed, never entered. Encrypted files hash only for a user who holds the key (else: errors.txt).
#
#  Changes from v1 (kept as Inventory_RefsVolume_v1.ps1): the reparse tag is read with the right
#  information class (9, FileAttributeTagInfo; v1 asked class 35, so the column was always empty);
#  snapshots use the syntax T21 recorded (/l "*"); streams of directories; reparse targets; the root
#  entry; no descent into directory reparse points; long paths; the tool's time form; the journal,
#  security and geometry outputs; the output folder is never reused.
#  v2.1 (2026-11-06): volume.txt records the volume's BitLocker state (manage-bde -status), and the script warns
#  (console and errors.txt) when the volume is encrypted or being encrypted -- an image of it will be encrypted. It
#  never stops for it.
#  Pure ASCII for Windows PowerShell 5.1.
# ============================================================================
param(
    [Parameter(Mandatory=$true)][string]$Drive,
    [string]$Label = "",
    [string]$OutRoot = "C:\testrefs\inventory",
    [string[]]$ExcludeDir = @(),
    [switch]$Journal,
    [switch]$Security,
    [switch]$Snapshots,
    [switch]$CopyToVolume
)
$ErrorActionPreference = 'Continue'
$Drive = $Drive.TrimEnd(':', '\')
$root  = "$Drive`:\"

# --- refusals before anything is written
$me = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'run this in an ELEVATED console' }
$vol = Get-Volume -DriveLetter $Drive -ErrorAction SilentlyContinue
if (-not $vol) { throw "no volume with the letter $Drive`:" }
if ($vol.FileSystem -ne 'ReFS') { Write-Warning "$Drive`: is $($vol.FileSystem), not ReFS: the inventory is taken anyway" }
if (-not $Label) { $Label = "vol$Drive" }
$stamp = Get-Date -Format yyyyMMdd_HHmmss
$out   = Join-Path $OutRoot "${Label}_$stamp"
if (Test-Path -LiteralPath $out) { throw "$out exists already: stop" }
if ($out.ToUpper().StartsWith($root.ToUpper())) { throw 'OutRoot is on the inventoried volume: choose another drive' }
New-Item -ItemType Directory -Path $out -Force | Out-Null
Start-Transcript -Path (Join-Path $out "transcript.txt") | Out-Null
$errFile = Join-Path $out "errors.txt"
function Write-Err([string]$m) { Add-Content -LiteralPath $errFile ((Get-Date -Format o) + "  " + $m) }

# --- Win32 file information: times incl. ChangeTime, attributes, sizes, links, 128-bit id, reparse tag
if (-not ('RefsInv2' -as [type])) {
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class RefsInv2 {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr CreateFileW(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool GetFileInformationByHandleEx(IntPtr h, int cls, IntPtr buf, uint size);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr h);
    public class Info {
        public long Creation, LastAccess, LastWrite, Change; public uint Attributes;
        public long Allocation, EndOfFile; public uint Links; public bool IsDir;
        public ulong VolSerial, IdLo, IdHi; public uint ReparseTag; public int Error;
    }
    public static Info Get(string path) {
        Info i = new Info();
        // FILE_READ_ATTRIBUTES, share all, OPEN_EXISTING, BACKUP_SEMANTICS | OPEN_REPARSE_POINT
        IntPtr h = CreateFileW(@"\\?\" + path, 0x80, 7, IntPtr.Zero, 3, 0x02000000 | 0x00200000, IntPtr.Zero);
        if (h == new IntPtr(-1)) { i.Error = Marshal.GetLastWin32Error(); return i; }
        IntPtr b = Marshal.AllocHGlobal(64);
        try {
            if (GetFileInformationByHandleEx(h, 0, b, 40)) {            // FileBasicInfo
                i.Creation = Marshal.ReadInt64(b, 0);  i.LastAccess = Marshal.ReadInt64(b, 8);
                i.LastWrite = Marshal.ReadInt64(b, 16); i.Change = Marshal.ReadInt64(b, 24);
                i.Attributes = (uint)Marshal.ReadInt32(b, 32);
            } else if (i.Error == 0) i.Error = Marshal.GetLastWin32Error();
            if (GetFileInformationByHandleEx(h, 1, b, 24)) {            // FileStandardInfo
                i.Allocation = Marshal.ReadInt64(b, 0); i.EndOfFile = Marshal.ReadInt64(b, 8);
                i.Links = (uint)Marshal.ReadInt32(b, 16); i.IsDir = Marshal.ReadByte(b, 21) != 0;
            } else if (i.Error == 0) i.Error = Marshal.GetLastWin32Error();
            if (GetFileInformationByHandleEx(h, 18, b, 24)) {           // FileIdInfo
                i.VolSerial = (ulong)Marshal.ReadInt64(b, 0);
                i.IdLo = (ulong)Marshal.ReadInt64(b, 8); i.IdHi = (ulong)Marshal.ReadInt64(b, 16);
            } else if (i.Error == 0) i.Error = Marshal.GetLastWin32Error();
            if (GetFileInformationByHandleEx(h, 9, b, 8)) {             // FileAttributeTagInfo
                i.ReparseTag = (uint)Marshal.ReadInt32(b, 4);
            } else if (i.Error == 0) i.Error = Marshal.GetLastWin32Error();
        } finally { Marshal.FreeHGlobal(b); CloseHandle(h); }
        return i;
    }
}
"@
}

function ToIso([long]$ft) {
    if ($ft -le 0) { return "" }
    return [DateTime]::FromFileTimeUtc($ft).ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff'Z'", [Globalization.CultureInfo]::InvariantCulture)
}
# The long-path prefix for .NET calls. Some .NET Framework set-ups refuse '\\?\' paths; then plain paths are
# used and errors.txt says so (the Win32 query above always uses the prefix).
$LP = '\\?\'
try { [void][IO.Directory]::GetFileSystemEntries($LP + $root) }
catch { $LP = ''; Write-Err ("the long-path prefix is refused by .NET here (" + $_.Exception.Message + "): plain paths used") }
function Get-Sha256File([string]$path) {
    $sha = [Security.Cryptography.SHA256]::Create()
    $fs = [IO.File]::Open($LP + $path, 'Open', 'Read', 'ReadWrite')
    try { return ([BitConverter]::ToString($sha.ComputeHash($fs)) -replace '-', '').ToLower() }
    finally { $fs.Close(); $sha.Dispose() }
}
function Get-Sha256Ads([string]$path, [string]$stream) {
    $bytes = Get-Content -LiteralPath $path -Stream $stream -Encoding Byte -ReadCount 0
    if ($null -eq $bytes) { $bytes = [byte[]]@() }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([byte[]]$bytes)) -replace '-', '').ToLower() }
    finally { $sha.Dispose() }
}
function Q([string]$s) { return '"' + ($s -replace '"', '""') + '"' }
function Rel([string]$p) { if ($p.TrimEnd('\') -eq $root.TrimEnd('\')) { return '.' } else { return $p.Substring($root.Length) } }
function Add-Cmd([string]$file, [string]$title, [scriptblock]$sb) {
    Add-Content -LiteralPath $file ("`n--- " + $title)
    try { Add-Content -LiteralPath $file ((& $sb 2>&1) | Out-String) } catch { Add-Content -LiteralPath $file ("ERROR: " + $_.Exception.Message) }
}

# --- the host and the volume
$params = (($PSBoundParameters.GetEnumerator() | ForEach-Object { $_.Key + '=' + $_.Value }) -join '; ')
$vt = Join-Path $out "volume.txt"
Set-Content -LiteralPath $vt ("inventory of $root  label=$Label  taken=" + (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff'Z'", [Globalization.CultureInfo]::InvariantCulture) + "  host=$env:COMPUTERNAME  user=$env:USERNAME")
Add-Cmd $vt "script" { "$PSCommandPath  sha256=" + (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash; "parameters: " + $params }
Add-Cmd $vt "windows" { cmd /c ver; Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Format-List ProductName, EditionID, DisplayVersion, CurrentBuild, UBR }
Add-Cmd $vt "refs.sys" { $f = "$env:SystemRoot\System32\drivers\refs.sys"; (Get-Item $f).VersionInfo.FileVersionRaw.ToString(); (Get-FileHash $f -Algorithm SHA256).Hash }
Add-Cmd $vt "time zone" { Get-TimeZone | Format-List Id, BaseUtcOffset }
Add-Cmd $vt "volume" { Get-Volume -DriveLetter $Drive | Format-List * }
Add-Cmd $vt "partition and disk" { $p = Get-Partition -DriveLetter $Drive; $p | Format-List *; Get-Disk -Number $p.DiskNumber | Format-List * }
Add-Cmd $vt "fsutil fsinfo refsinfo" { fsutil fsinfo refsinfo "$Drive`:" }
Add-Cmd $vt "fsutil fsinfo volumeinfo" { fsutil fsinfo volumeinfo "$Drive`:" }
Add-Cmd $vt "fsutil usn queryjournal" { fsutil usn queryjournal "$Drive`:" }
Add-Cmd $vt "fsutil behavior query disablelastaccess" { fsutil behavior query disablelastaccess }
Add-Cmd $vt "bitlocker (manage-bde -status)" { manage-bde -status "$Drive`:" }
$blv = $null
if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
    try { $blv = Get-BitLockerVolume -MountPoint "$Drive`:" -ErrorAction Stop } catch { $blv = $null }
}
if ($blv -and (($blv.VolumeStatus -ne 'FullyDecrypted') -or ($blv.EncryptionPercentage -gt 0))) {
    $blm = "BitLocker is active on $Drive`: (status " + $blv.VolumeStatus + ", " + $blv.EncryptionPercentage + "% encrypted, protection " + $blv.ProtectionStatus + "): an image of this disk will be encrypted. The inventory goes on."
    Write-Warning $blm
    Write-Err $blm
}

# --- pass 0: the walk (directory reparse points are listed, not entered)
$excl = @()
foreach ($d in $ExcludeDir) { $excl += (Join-Path $root $d).TrimEnd('\').ToLower() }
$paths = New-Object System.Collections.Generic.List[string]
$paths.Add($root)
$stack = New-Object System.Collections.Stack
$stack.Push($root)
while ($stack.Count -gt 0) {
    $d = $stack.Pop()
    $entries = @()
    try { $entries = [IO.Directory]::GetFileSystemEntries($LP + $d) } catch { Write-Err ("list: $d : " + $_.Exception.Message); continue }
    foreach ($e in $entries) {
        $p = $e.Substring($LP.Length)
        $pl = $p.ToLower(); $skip = $false
        foreach ($x in $excl) { if ($pl -eq $x -or $pl.StartsWith($x + '\')) { $skip = $true; break } }
        if ($skip) { continue }
        $paths.Add($p)
        try {
            $a = [IO.File]::GetAttributes($e)
            if (($a -band [IO.FileAttributes]::Directory) -and -not ($a -band [IO.FileAttributes]::ReparsePoint)) { $stack.Push($p) }
        } catch { Write-Err ("attributes: $p : " + $_.Exception.Message) }
    }
}
"entries: $($paths.Count)   (pass 1: metadata)"

# --- pass 1: metadata only
$rows = New-Object System.Collections.Generic.List[object]
$n = 0
foreach ($p in $paths) {
    $n++; if ($n % 1000 -eq 0) { "  metadata $n / $($paths.Count)" }
    $i = [RefsInv2]::Get($p)
    if ($i.Error -ne 0) { Write-Err ("info: $p : win32 error " + $i.Error) }
    $kind = "file"; if ($i.IsDir -or ($i.Attributes -band 0x10)) { $kind = "dir" }
    $tag = ""; if ($i.ReparseTag -ne 0) { $tag = "0x{0:x}" -f $i.ReparseTag }
    $rows.Add((New-Object PSObject -Property @{
        Path = $p; RelPath = (Rel $p); Kind = $kind; Size = $i.EndOfFile; Allocation = $i.Allocation
        Created = (ToIso $i.Creation); Modified = (ToIso $i.LastWrite); Changed = (ToIso $i.Change); Accessed = (ToIso $i.LastAccess)
        Attributes = ("0x{0:x}" -f $i.Attributes); ReparseTag = $tag
        FileId = ("0x{0:x16}{1:x16}" -f $i.IdHi, $i.IdLo); FileIdHi = ("0x{0:x}" -f $i.IdHi); FileIdLo = ("0x{0:x}" -f $i.IdLo)
        VolumeSerial = ("0x{0:x}" -f $i.VolSerial); Links = $i.Links; AdsCount = 0; SHA256 = ""
        Error = $(if ($i.Error -ne 0) { [string]$i.Error } else { "" })
    }))
}

# --- the change journal (Windows' decode), before any content is read
if ($Journal) {
    "journal export"
    try { & fsutil usn readjournal "$Drive`:" csv | Out-File -FilePath (Join-Path $out "journal.csv") -Encoding utf8 }
    catch { Write-Err ("journal: " + $_.Exception.Message) }
}

# --- pass 2: content hashes, streams, links, reparse targets, snapshots, security
"pass 2: content"
$sf = Join-Path $out "streams.csv";   Set-Content -LiteralPath $sf "RelPath,Stream,Length,SHA256"
$hf = Join-Path $out "hardlinks.csv"; Set-Content -LiteralPath $hf "RelPath,Links,Names"
$rf = Join-Path $out "reparse.txt";   Set-Content -LiteralPath $rf "fsutil reparsepoint query, one block per entry"
if ($Snapshots) { $nf = Join-Path $out "snapshots.csv"; Set-Content -LiteralPath $nf "RelPath,RefsutilList" }
if ($Security)  { $cf = Join-Path $out "security.csv";  Set-Content -LiteralPath $cf "RelPath,Owner,Sddl" }
$n = 0
foreach ($r in $rows) {
    $n++; if ($n % 1000 -eq 0) { "  content $n / $($rows.Count)" }
    $p = $r.Path
    if ($r.Kind -eq "file" -and -not $r.ReparseTag) {
        try { $r.SHA256 = Get-Sha256File $p } catch { Write-Err ("hash: $p : " + $_.Exception.Message) }
    }
    $ads = @()
    try { $ads = @(Get-Item -LiteralPath $p -Stream * -Force -ErrorAction Stop | Where-Object { $_.Stream -ne ':$DATA' }) } catch { Write-Err ("streams: $p : " + $_.Exception.Message) }
    $r.AdsCount = $ads.Count
    foreach ($s in $ads) {
        $h = "ERR"
        try { $h = Get-Sha256Ads $p $s.Stream } catch { Write-Err ("stream: $p`:$($s.Stream) : " + $_.Exception.Message) }
        Add-Content -LiteralPath $sf ((Q $r.RelPath) + "," + (Q $s.Stream) + "," + $s.Length + "," + $h)
    }
    if ($r.Kind -eq "file" -and $r.Links -gt 1) {
        $names = ((& fsutil hardlink list $p 2>&1) | Out-String) -replace "`r?`n", " | "
        Add-Content -LiteralPath $hf ((Q $r.RelPath) + "," + $r.Links + "," + (Q $names))
    }
    if ($r.ReparseTag) {
        Add-Content -LiteralPath $rf ("`n--- " + $r.RelPath + "  tag " + $r.ReparseTag)
        Add-Content -LiteralPath $rf ((& fsutil reparsepoint query $p 2>&1) | Out-String)
    }
    if ($Snapshots -and $r.Kind -eq "file") {
        $lst = ((& refsutil streamsnapshot /l "*" $p 2>&1) | Out-String) -replace "`r?`n", " | "
        Add-Content -LiteralPath $nf ((Q $r.RelPath) + "," + (Q $lst))
    }
    if ($Security) {
        try { $acl = Get-Acl -LiteralPath $p -ErrorAction Stop; Add-Content -LiteralPath $cf ((Q $r.RelPath) + "," + (Q $acl.Owner) + "," + (Q $acl.Sddl)) }
        catch { Write-Err ("security: $p : " + $_.Exception.Message) }
    }
}

# --- write
$inv = Join-Path $out "inventory.csv"
$rows | Select-Object RelPath, Kind, Size, Allocation, Created, Modified, Changed, Accessed, Attributes, ReparseTag, FileId, FileIdHi, FileIdLo, VolumeSerial, Links, AdsCount, SHA256, Error |
    Export-Csv -LiteralPath $inv -NoTypeInformation -Encoding UTF8
$nfiles = @($rows | Where-Object { $_.Kind -eq "file" }).Count
$errs = 0; if (Test-Path -LiteralPath $errFile) { $errs = @(Get-Content -LiteralPath $errFile).Count }
"written: $out"
"  entries $($rows.Count) (root included)  files $nfiles  dirs $($rows.Count - $nfiles)  streams $(@(Get-Content -LiteralPath $sf).Count - 1)  multilink $(@(Get-Content -LiteralPath $hf).Count - 1)  errors $errs"
Stop-Transcript | Out-Null
$sums = Join-Path $out "SHA256SUMS.txt"
$lines = @()
foreach ($f in (Get-ChildItem -LiteralPath $out -File | Where-Object { $_.Name -ne "SHA256SUMS.txt" })) { $lines += ((Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLower() + "  " + $f.Name) }
Set-Content -LiteralPath $sums $lines -Encoding ascii

if ($CopyToVolume) {
    $dst = Join-Path $root ("inventory_" + $Label + "_" + $stamp)
    Copy-Item -LiteralPath $out -Destination $dst -Recurse -Force
    "copied to $dst -- this CHANGES the volume after the inventory (never for an audit image)"
}
"next: take the disk offline and image it, with nothing in between"
