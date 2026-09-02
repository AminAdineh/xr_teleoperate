; ============================================================================
;  Unitree XR Teleoperate — Inno Setup Installer Script
;  Produces: UnitreeXRTeleoperateSetup.exe
;
;  Prerequisites:
;    - PyInstaller build already completed (dist\UnitreeXRTeleoperate\ exists)
;    - Inno Setup 6 (ISCC) installed
;
;  Build:
;    iscc packaging\installer\unitree_xr_teleoperate.iss
;
;  Output:
;    dist\installer\UnitreeXRTeleoperateSetup.exe
; ============================================================================
#define MyAppName          "Unitree XR Teleoperate"
#define MyAppVersion       "1.0.0"
#define MyAppPublisher     "UnitreeRobotics"
#define MyAppExeName       "UnitreeXRTeleoperate.exe"
#define MyAppURL          "https://github.com/AminAdineh/xr_teleoperate"

; Stable AppId — do NOT change between versions (controls upgrade behaviour)
#define MyAppId            "{{8F4D56D8-E800-43CF-96B0-0235B7FB008C}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\UnitreeXRTeleoperate
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=UnitreeXRTeleoperateSetup
SetupIconFile=..\windows\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
; Show license agreement page
LicenseFile=..\..\LICENSE
; Version info embedded in the installer exe
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:; Flags: unchecked
Name: "firewall"; Description: "Configure Windows &Firewall rules (required for robot/XR networking)"; GroupDescription: "Additional tasks:; Flags: checkonce

[Files]
; The entire PyInstaller bundle — all DLLs, Python runtime, Qt, deps, data
Source: "..\dist\UnitreeXRTeleoperate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Documentation
Source: "..\..\docs\WINDOWS.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{group}\Documentation"; Filename: "{app}\docs\WINDOWS.md"
; Optional Desktop shortcut
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
; Configure firewall rules after install
Filename: "{app}\{#MyAppExeName}"; Parameters: "--firewall"; Tasks: firewall; Flags: runhidden waituntilterminated; StatusMsg: "Configuring firewall rules..."
; Offer to launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove firewall rules on uninstall
Filename: "{app}\{#MyAppExeName}"; Parameters: "--firewall-remove"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveFirewall"

[UninstallDelete]
; Clean up bundled app data on uninstall
Type: filesandordirs; Name: "{app}"
