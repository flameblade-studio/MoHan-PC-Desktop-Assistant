param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [string]$InputPath = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

try {
    Add-Type -AssemblyName System.Speech
    $installed = [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()
    if (-not $installed -or $installed.Count -eq 0) {
        Set-Content -LiteralPath $OutputPath -Value "__ERROR__:NO_RECOGNIZER" -Encoding UTF8
        exit 1
    }
    $info = $installed | Where-Object {
        $_.Culture.Name -in @("zh-TW", "zh-CN", "zh-HK")
    } | Select-Object -First 1
    if (-not $info) { $info = $installed | Select-Object -First 1 }

    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    if ($InputPath) {
        $engine.SetInputToWaveFile($InputPath)
    } else {
        $engine.SetInputToDefaultAudioDevice()
    }
    # 短句快速收音：開始說話後約 0.6～0.85 秒靜音便結束辨識。
    $engine.InitialSilenceTimeout = [TimeSpan]::FromMilliseconds(2500)
    $engine.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(600)
    $engine.EndSilenceTimeoutAmbiguous = [TimeSpan]::FromMilliseconds(850)
    $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
    $result = $engine.Recognize([TimeSpan]::FromSeconds(7))
    if ($result -and $result.Text) {
        Set-Content -LiteralPath $OutputPath -Value $result.Text -Encoding UTF8
    } else {
        Set-Content -LiteralPath $OutputPath -Value "__EMPTY__" -Encoding UTF8
    }
} catch {
    Set-Content -LiteralPath $OutputPath -Value ("__ERROR__:" + $_.Exception.Message) -Encoding UTF8
    exit 1
}
