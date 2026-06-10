// Default DeviceGuard rules — conservative detections for classic
// USB-borne attack patterns. Add your own rules in rules/custom/.

rule Autorun_Launches_Executable
{
    meta:
        description = "autorun.inf configured to launch an executable on insert"
        severity = "high"
    strings:
        $open = /open\s*=\s*[^\r\n]{0,200}\.(exe|bat|cmd|scr|pif|com)/ nocase
        $shellexec = /shellexecute\s*=\s*[^\r\n]{1,200}/ nocase
        $shell_cmd = /shell\\[^\r\n]{0,50}\\command\s*=/ nocase
    condition:
        filesize < 100KB and any of them
}

rule LNK_Invokes_PowerShell
{
    meta:
        description = "Windows shortcut that invokes PowerShell (common USB lure)"
        severity = "medium"
    strings:
        $lnk_magic = { 4C 00 00 00 01 14 02 00 }
        $ps1 = "powershell" nocase wide ascii
        $ps2 = "-encodedcommand" nocase wide ascii
        $ps3 = "-windowstyle hidden" nocase wide ascii
    condition:
        $lnk_magic at 0 and $ps1 and ($ps2 or $ps3)
}

rule Script_Hidden_Window_Dropper
{
    meta:
        description = "Script that downloads and runs a payload with a hidden window"
        severity = "medium"
    strings:
        $dl1 = "DownloadFile" nocase
        $dl2 = "Invoke-WebRequest" nocase
        $dl3 = "URLDownloadToFile" nocase
        $run1 = "WScript.Shell" nocase
        $run2 = "Start-Process" nocase
        $hide = /-w(indowstyle)?\s+hidden/ nocase
    condition:
        filesize < 1MB and (any of ($dl*)) and (any of ($run*)) and $hide
}
