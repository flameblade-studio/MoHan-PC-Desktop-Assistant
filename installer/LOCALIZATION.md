# Installer localization policy

MoHan ships two installer formats with deliberately different localization
contracts.

## Interactive EXE installer

The Inno Setup EXE is the normal interactive installer. It detects the Windows
user language and offers these four choices before installation:

- Taiwan Traditional Chinese (`zh-TW`, LCID 1028)
- Simplified Chinese (`zh-CN`, LCID 2052)
- English (`en-US`, LCID 1033)
- Japanese (`ja-JP`, LCID 1041)

The selected language affects only the installer and uninstaller interface.
MoHan's own first-run wizard remains the authority for the application UI
language.

## MSI package

The MSI remains a Taiwan Traditional Chinese base package (`Language=1028`).
It is intended primarily for silent installation and managed deployment, so it
does not display a custom language picker. Keeping one stable base MSI also
avoids publishing several packages that Windows Installer could treat as
different products.

The build creates three language transforms from the same payload and product
identity:

- `MoHan-Desktop-Assistant-<tag>-en-US.mst` (`1033`)
- `MoHan-Desktop-Assistant-<tag>-zh-CN.mst` (`2052`)
- `MoHan-Desktop-Assistant-<tag>-ja-JP.mst` (`1041`)

The transforms must preserve the base MSI's product identity, component GUIDs,
install location, upgrade code, and payload. Administrators will apply one with
the standard Windows Installer command, for example:

```powershell
msiexec /i MoHan-Desktop-Assistant-vX.Y.Z-Windows-x64.msi `
  TRANSFORMS=MoHan-Desktop-Assistant-vX.Y.Z-ja-JP.mst /qn
```

Windows CI installs, runs the packaged self-test, and uninstalls the base MSI
and every transform. A transform must never be published if any variant fails.
The transforms affect Windows Installer messages only. MoHan's first-run wizard
still controls the application's Traditional Chinese, Simplified Chinese,
English, or Japanese interface and reply language.
