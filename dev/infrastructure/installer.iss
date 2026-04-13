; RMS Transcribe Desktop - Inno Setup Script
#define MyAppName "RMS Transcribe Desktop"
#define MyAppVersion "1.0.2"
#define MyAppPublisher "RMS Team"
#define MyAppURL "https://github.com/rexo-null/RMS-Transcribe"
#define MyAppExeName "RMS-Transcribe.exe"
#define MyAppIconName "icon.ico"
#define HF_TOKEN ""  ; Optional: pre-fill Hugging Face token

[Setup]
AppId=RMS-Transcribe-v{#MyAppVersion}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\RMS-Transcribe
DisableProgramGroupPage=yes
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=.
OutputBaseFilename=RMS-Transcribe-Setup-v{#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "RMS-Transcribe-Windows-v{#MyAppVersion}\app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "RMS-Transcribe-Windows-v{#MyAppVersion}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "RMS-Transcribe-Windows-v{#MyAppVersion}\SETUP.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "RMS-Transcribe-Windows-v{#MyAppVersion}\app\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Dirs]
Name: "{app}\models"; Permissions: users-full
Name: "{app}\results"; Permissions: users-full

[UninstallDelete]
Type: filesandordirs; Name: "{app}\results"
Type: dirifempty; Name: "{app}"
