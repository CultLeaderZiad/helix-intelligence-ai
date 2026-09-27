$ErrorActionPreference = 'Stop'
$enc = New-Object System.Text.UTF8Encoding($false)

# 1. main.py — keep leadgen include, drop the two higgsfield mounts
$p = 'backend\app\main.py'
$l = [System.Collections.Generic.List[string]]([System.IO.File]::ReadAllLines($p, [System.Text.Encoding]::UTF8))
# delete higgsfield mount lines
for ($i = $l.Count - 1; $i -ge 0; $i--) {
    if ($l[$i] -match 'include_router\(higgsfield\.router') { $l.RemoveAt($i) }
}
# remove conflict markers, keeping both valid sides (HEAD = leadgen include)
for ($i = $l.Count - 1; $i -ge 0; $i--) {
    if ($l[$i].Trim() -eq '<<<<<<< HEAD' -or $l[$i].Trim() -eq '=======' -or $l[$i].StartsWith('>>>>>>>')) {
        $l.RemoveAt($i)
    }
}
[System.IO.File]::WriteAllLines($p, $l, $enc)
Write-Output 'main.py resolved'

# 2. .env.example — keep BOTH blocks (SCRAPLING + PUBLIC_API_BASE_URL)
$e = '.env.example'
$l2 = [System.Collections.Generic.List[string]]([System.IO.File]::ReadAllLines($e, [System.Text.Encoding]::UTF8))
for ($i = $l2.Count - 1; $i -ge 0; $i--) {
    if ($l2[$i].Trim() -eq '<<<<<<< HEAD' -or $l2[$i].Trim() -eq '=======' -or $l2[$i].StartsWith('>>>>>>>')) {
        $l2.RemoveAt($i)
    }
}
[System.IO.File]::WriteAllLines($e, $l2, $enc)
Write-Output '.env.example resolved'

# verify: no markers left, both contents present
$check1 = (Select-String -Path $p -Pattern '^<{7}|^={7}|^>{7}' | Measure-Object).Count
$check2 = (Select-String -Path $e -Pattern '^<{7}|^={7}|^>{7}' | Measure-Object).Count
$hasLeadgen = [bool](Select-String -Path $p -Pattern 'leadgen\.router')
$hasHf = [bool](Select-String -Path $p -Pattern 'higgsfield\.router')
$hasScrap = [bool](Select-String -Path $e -Pattern 'SCRAPLING_WORKER_ENABLED')
$hasPub = [bool](Select-String -Path $e -Pattern 'PUBLIC_API_BASE_URL=')
Write-Output "markers: main=$check1 env=$check2 | main leadgen=$hasLeadgen higgsfield=$hasHf | env scrapling=$hasScrap public_base=$hasPub"
