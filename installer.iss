; NWGrabio Installer Script (Inno Setup)
; Developed by Nethum Welikada, Dalhousie University
;
; This script builds a normal Windows "Setup.exe" installer wizard for
; NWGrabio: choose install folder, create Start Menu and Desktop shortcuts,
; register in Add/Remove Programs, and provide a clean uninstaller.
;
; Requires the free Inno Setup compiler (ISCC.exe) to build.
; Download: https://jrsoftware.org/isdl.php
; build.bat runs this automatically if Inno Setup is installed.

#define MyAppName "NWGrabio"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Nethum Welikada"
#define MyAppURL "https://github.com/NethumWelikada"
#define MyAppExeName "NWGrabio.exe"

[Setup]
AppId={{9F2C6E2B-6C6E-4C4A-9E1E-NWGRABIO001}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=NWGrabio-Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
