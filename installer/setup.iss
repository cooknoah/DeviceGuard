; DeviceGuard Inno Setup script.
; Build the app first (python build.py), then compile this with Inno Setup 6:
;   iscc installer\setup.iss
; Output: installer\output\DeviceGuard-Setup-<version>.exe

#define MyAppName "DeviceGuard"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Noah Cook"
#define MyAppExeName "DeviceGuard.exe"

[Setup]
AppId={{B7E61A52-9C44-4D2B-A1F0-3D5E8C7A2F91}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=DeviceGuard-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; App writes all user data to %LOCALAPPDATA%\DeviceGuard, so Program Files is fine.
PrivilegesRequired=admin
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; Flags: unchecked

[Files]
Source: "..\dist\DeviceGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove the per-user startup registry entry the app manages.
Filename: "reg"; Parameters: "delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v DeviceGuard /f"; Flags: runhidden; RunOnceId: "RemoveStartup"
