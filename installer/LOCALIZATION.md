# Installer localization policy

MoHan ships two installer formats with deliberately different localization
contracts.

## Interactive EXE installer

The Inno Setup EXE is the normal interactive installer. It detects the Windows
user language and offers these three choices before installation:

- Taiwan Traditional Chinese (`zh-TW`, LCID 1028)
- Simplified Chinese (`zh-CN`, LCID 2052)
- English (`en-US`, LCID 1033)

The selected language affects only the installer and uninstaller interface.
MoHan's own first-run wizard remains the authority for the application UI
language.

## MSI package

The MSI remains a Taiwan Traditional Chinese base package (`Language=1028`).
It is intended primarily for silent installation and managed deployment, so it
does not display a custom language picker. Keeping one stable base MSI also
avoids publishing several packages that Windows Installer could treat as
different products.

English and Simplified Chinese MSI interfaces will be added as language
transforms after their dialogs, validation messages, upgrade behavior, silent
install, repair, and uninstall paths have been tested on clean Windows images:

- `MoHan-Desktop-Assistant-en-US.mst` (`1033`)
- `MoHan-Desktop-Assistant-zh-CN.mst` (`2052`)

The transforms must preserve the base MSI's product identity, component GUIDs,
install location, upgrade code, and payload. Administrators will apply one with
the standard Windows Installer command, for example:

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-en-US.mst /qn
```

Do not advertise or publish either transform until CI installs, self-tests,
repairs, upgrades, and uninstalls every language variant successfully.
