#define MyAppName "MoHan Desktop Assistant"
#ifndef MyVersion
  #define MyVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\MoHan-Desktop-Assistant-dev"
#endif
#ifndef ExecutableName
  #define ExecutableName "MoHan-Desktop-Assistant-dev.exe"
#endif
#ifndef OutputDir
  #define OutputDir "..\release-artifacts"
#endif
#ifndef IconPath
  #define IconPath "..\assets\mohan-halfbody.ico"
#endif

[Setup]
#ifndef TraditionalChineseMessages
  #define TraditionalChineseMessages SourcePath + "\languages\ChineseTraditional.isl"
#endif
#ifndef SimplifiedChineseMessages
  #define SimplifiedChineseMessages SourcePath + "\languages\ChineseSimplified.isl"
#endif

AppId={{E1F22A47-1B50-4B6C-AF43-543FE68370C7}
AppName={#MyAppName}
AppVersion={#MyVersion}
AppVerName={#MyAppName} {#MyVersion}
AppPublisher=CHOU MING HUA
AppPublisherURL=https://www.flamebladestudio.com.tw
AppSupportURL=https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/issues
AppUpdatesURL=https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant/releases
DefaultDirName={localappdata}\Programs\MoHan Desktop Assistant
DefaultGroupName=MoHan Desktop Assistant
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=MoHan-Desktop-Assistant-v{#MyVersion}-Windows-x64-Setup
SetupIconFile={#IconPath}
UninstallDisplayIcon={app}\{#ExecutableName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no

[Languages]
Name: "chinesetraditional"; MessagesFile: "{#TraditionalChineseMessages}"
Name: "chinesesimplified"; MessagesFile: "{#SimplifiedChineseMessages}"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑 / Create a desktop shortcut"; GroupDescription: "捷徑 / Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MoHan Desktop Assistant"; Filename: "{app}\{#ExecutableName}"; WorkingDir: "{app}"
Name: "{autodesktop}\MoHan Desktop Assistant"; Filename: "{app}\{#ExecutableName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExecutableName}"; Description: "啟動墨寒 / Launch MoHan"; Flags: nowait postinstall skipifsilent
