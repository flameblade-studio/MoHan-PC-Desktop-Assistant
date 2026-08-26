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
#ifndef WizardImagePath
  #define WizardImagePath SourcePath + "\artwork\wizard-hero.png"
#endif
#ifndef WizardSmallImagePath
  #define WizardSmallImagePath SourcePath + "\artwork\wizard-small.png"
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
AppSupportURL=https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/issues
AppUpdatesURL=https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant/releases
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
DisableWelcomePage=no
WizardImageFile={#WizardImagePath}
WizardSmallImageFile={#WizardSmallImagePath}
WizardImageBackColor=$EDF3F7
WizardSmallImageBackColor=$EDF3F7
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no

[Languages]
Name: "chinesetraditional"; MessagesFile: "{#TraditionalChineseMessages}"
Name: "chinesesimplified"; MessagesFile: "{#SimplifiedChineseMessages}"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
chinesetraditional.CreateDesktopIcon=建立桌面捷徑
chinesetraditional.Shortcuts=捷徑：
chinesetraditional.LaunchMoHan=啟動墨寒
chinesesimplified.CreateDesktopIcon=创建桌面快捷方式
chinesesimplified.Shortcuts=快捷方式：
chinesesimplified.LaunchMoHan=启动墨寒

english.CreateDesktopIcon=Create a desktop shortcut
english.Shortcuts=Shortcuts:
english.LaunchMoHan=Launch MoHan
japanese.CreateDesktopIcon=デスクトップにショートカットを作成
japanese.Shortcuts=ショートカット：
japanese.LaunchMoHan=墨寒を起動


[InstallDelete]
Type: files; Name: "{app}\MoHan-Desktop-Assistant-*.exe"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:Shortcuts}"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MoHan Desktop Assistant"; Filename: "{app}\{#ExecutableName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#ExecutableName}"; AppUserModelID: "FlamebladeStudio.MoHanDesktopAssistant"
Name: "{autodesktop}\MoHan Desktop Assistant"; Filename: "{app}\{#ExecutableName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#ExecutableName}"; AppUserModelID: "FlamebladeStudio.MoHanDesktopAssistant"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExecutableName}"; Description: "{cm:LaunchMoHan}"; Flags: nowait postinstall skipifsilent
