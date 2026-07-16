; ============================================================
; KO'ZGU — Inno Setup installer script
;
; Compile on Windows with: iscc installer\windows\kozgu.iss
; (Inno Setup 6.x: https://jrsoftware.org/isdl.php)
;
; Expects PyInstaller to have produced  dist\kozgu\  first.
; ============================================================

#define MyAppName "KO'ZGU"
#define MyAppVersion "1.9.11"
#define MyAppPublisher "Elyorbek"
#define MyAppExeName "kozgu.exe"
#define MyAppURL "https://t.me/visio_eye"

[Setup]
AppId={{C9E0F4D2-7B23-4F89-A6F1-KOZGU-2C3D4E5F}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\KO'ZGU
DefaultGroupName=KO'ZGU
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=KOZGU-{#MyAppVersion}-setup
SetupIconFile=..\..\assets\img\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
Compression=lzma2/ultra
SolidCompression=yes
; Accept both x64 and x86 Windows.  64-bit install mode activates
; automatically on x64 hosts; on 32-bit hosts the installer runs in
; native 32-bit mode.  The actual .exe bitness is determined by which
; Python interpreter PyInstaller was run against.
ArchitecturesAllowed=x86 x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
MinVersion=6.1sp1

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; \
    GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; \
    GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; PyInstaller produces a folder dist\kozgu\ — copy the entire tree.
Source: "..\..\dist\kozgu\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; FFmpeg + ffprobe — bundled by build_windows.bat from gyan.dev,
; installed to {app}\ffmpeg\.  The app adds this dir to PATH via
; ffmpeg_bootstrap.ffmpeg_binary() lookup.
Source: "ffmpeg\ffmpeg.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion skipifsourcedoesntexist
Source: "ffmpeg\ffprobe.exe"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion skipifsourcedoesntexist
; Visual C++ 2015-2022 Redistributable (x64) — also bundled by
; build_windows.bat so the installer works on offline machines.
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; \
    Flags: deleteafterinstall skipifsourcedoesntexist

[Run]
; Auto-install VC++ Redistributable if Python's runtime DLL fails to
; load (Windows shows error 0xc000007b / "MSVCP140.dll missing").
; The /quiet flag skips the UI so it stays seamless.
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; \
    Flags: skipifdoesntexist runhidden waituntilterminated; \
    StatusMsg: "Installing Microsoft Visual C++ Redistributable…"; \
    Check: NeedsVCRedist
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    IconFilename: "{app}\assets\img\logo.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    IconFilename: "{app}\assets\img\logo.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; \
    IconFilename: "{app}\assets\img\logo.ico"; Tasks: quicklaunchicon

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\KOZGU"

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
      'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
      'Path', OrigPath) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

function NeedsVCRedist: Boolean;
var
  Installed: Cardinal;
begin
  // VC++ 2015-2022 Redistributable installs this key when present.
  if RegQueryDWordValue(HKEY_LOCAL_MACHINE,
      'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
      'Installed', Installed) then
    Result := (Installed = 0)
  else
    Result := True;
end;

// vc_redist.x64.exe is bundled by build_windows.bat into the
// installer payload, so we don't download anything at install time.
