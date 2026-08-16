from __future__ import annotations

lazy import base64
lazy import os
lazy import subprocess
lazy import tempfile
lazy from pathlib import Path

lazy from domain.safe_error import sanitize_error
lazy from domain.service_status_localization import ServiceStatus, service_status
lazy from integrations.speech_audio import (
    _SpeechCancelled,
)

CREATE_NO_WINDOW = 0x08000000

__all__ = ("WindowsSpeechSynthesisMethods",)


class WindowsSpeechSynthesisMethods:
    def _run_sapi(
        self,
        text: str,
        voice_name: str,
        rate: int,
        generation: int,
    ) -> None:
        fd, name = tempfile.mkstemp(prefix="mohan-sapi-", suffix=".wav")
        os.close(fd)
        audio_path = Path(name)
        audio_path.unlink(missing_ok=True)
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice_encoded = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        path_encoded = base64.b64encode(str(audio_path).encode("utf-8")).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$n=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_encoded}'));"
            "if($n){$s.SelectVoice($n)}else{"
            "$v=$s.GetInstalledVoices()|?{$_.VoiceInfo.Culture.Name -like 'zh-*'}|select -First 1;"
            "if($v){$s.SelectVoice($v.VoiceInfo.Name)}};"
            f"$s.Rate={max(-10, min(10, rate))};"
            f"$t=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'));"
            f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_encoded}'));"
            "$s.SetOutputToWaveFile($p);$s.Speak($t);$s.Dispose()"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            self._synthesize_with_powershell(
                command,
                audio_path,
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_WINDOWS_LEGACY_FAILED,
                ),
                240,
            )
            self._play_wave_bytes(
                audio_path.read_bytes(),
                generation,
            )
        finally:
            audio_path.unlink(missing_ok=True)

    def _run_onecore(
        self,
        text: str,
        voice_name: str,
        generation: int,
    ) -> None:
        fd, name = tempfile.mkstemp(prefix="mohan-onecore-", suffix=".wav")
        os.close(fd)
        audio_path = Path(name)
        audio_path.unlink(missing_ok=True)
        text_encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        voice_encoded = base64.b64encode(voice_name.encode("utf-8")).decode("ascii")
        path_encoded = base64.b64encode(str(audio_path).encode("utf-8")).decode("ascii")
        missing_voice_encoded = base64.b64encode(
            service_status(
                self.language,
                ServiceStatus.SPEECH_ONECORE_VOICE_MISSING,
                voice=voice_name,
            ).encode("utf-8")
        ).decode("ascii")
        script = (
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
            "$null=[Windows.Media.SpeechSynthesis.SpeechSynthesizer,"
            "Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime];"
            "$null=[Windows.Storage.Streams.DataReader,"
            "Windows.Storage.Streams,ContentType=WindowsRuntime];"
            "function Await($Operation,$ResultType){"
            "$method=[System.WindowsRuntimeSystemExtensions].GetMethods()|"
            "Where-Object{$_.Name -eq 'AsTask' -and $_.IsGenericMethod -and "
            "$_.GetGenericArguments().Count -eq 1 -and "
            "$_.GetParameters().Count -eq 1}|Select-Object -First 1;"
            "$task=$method.MakeGenericMethod($ResultType).Invoke($null,@($Operation));"
            "$task.Wait();$task.Result};"
            f"$text=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_encoded}'));"
            f"$voiceName=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_encoded}'));"
            f"$path=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_encoded}'));"
            f"$missingVoice=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{missing_voice_encoded}'));"
            "$synth=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::new();"
            "$voice=[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices|"
            "Where-Object{$_.DisplayName -eq $voiceName -or $_.Id -like ('*'+$voiceName+'*')}|"
            "Select-Object -First 1;"
            "if(-not $voice){throw $missingVoice};"
            "$synth.Voice=$voice;"
            "$stream=Await ($synth.SynthesizeTextToStreamAsync($text)) "
            "([Windows.Media.SpeechSynthesis.SpeechSynthesisStream]);"
            "$reader=[Windows.Storage.Streams.DataReader]::new($stream);"
            "$null=Await ($reader.LoadAsync([uint32]$stream.Size)) ([uint32]);"
            "$bytes=New-Object byte[] ([int]$stream.Size);"
            "$reader.ReadBytes($bytes);"
            "[IO.File]::WriteAllBytes($path,$bytes);"
            "$reader.Dispose();$stream.Dispose();$synth.Dispose();"
        )
        command = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            self._synthesize_with_powershell(
                command,
                audio_path,
                generation,
                service_status(
                    self.language,
                    ServiceStatus.SPEECH_ONECORE_FAILED,
                ),
                3000,
            )
            self._play_wave_bytes(
                audio_path.read_bytes(),
                generation,
            )
        finally:
            audio_path.unlink(missing_ok=True)

    def _synthesize_with_powershell(
        self,
        command: str,
        audio_path: Path,
        generation: int,
        failure_message: str,
        detail_limit: int,
    ) -> None:
        self._ensure_current(generation)
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-EncodedCommand", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
        if not self._register_process(generation, process):
            self._terminate_process(process)
            raise _SpeechCancelled
        try:
            try:
                _stdout, stderr = process.communicate(timeout=120)
            except subprocess.TimeoutExpired as exc:
                self._terminate_process(process)
                process.communicate()
                self._ensure_current(generation)
                raise RuntimeError(
                    service_status(
                        self.language,
                        ServiceStatus.SPEECH_WINDOWS_SYNTHESIS_TIMEOUT,
                    )
                ) from exc
        finally:
            self._release_process(process)
        self._ensure_current(generation)
        if process.returncode or not audio_path.exists():
            detail = stderr.decode("utf-8", errors="replace")[:detail_limit]
            raise RuntimeError(
                str(sanitize_error(detail)) if detail else failure_message
            )
