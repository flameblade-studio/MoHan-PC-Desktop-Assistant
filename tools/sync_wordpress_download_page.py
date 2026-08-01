from __future__ import annotations

import argparse
import base64
import html
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


START_MARKER = "<!-- MOHAN_RELEASE_START -->"
END_MARKER = "<!-- MOHAN_RELEASE_END -->"
DEFAULT_SLUG = "mohan-desktop-assistant"
REPOSITORY_URL = "https://github.com/hitoshic1982/MoHan-PC-Desktop-Assistant"
MEDIA_ROOT = (
    "https://raw.githubusercontent.com/"
    "hitoshic1982/MoHan-PC-Desktop-Assistant/main/docs/media"
)
EXPRESSION_ROOT = (
    "https://raw.githubusercontent.com/"
    "hitoshic1982/MoHan-PC-Desktop-Assistant/main/assets/expressions"
)
BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/flameblade_studio"
PAYPAL_ME_URL = "https://www.paypal.com/paypalme/flamebladestudio"


def request_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
) -> object:
    base_url = os.environ["WORDPRESS_BASE_URL"].rstrip("/")
    parsed_base = urllib.parse.urlparse(base_url)
    parsed_url = urllib.parse.urlparse(url)
    if (
        parsed_base.scheme != "https"
        or parsed_url.scheme != "https"
        or parsed_url.hostname != parsed_base.hostname
    ):
        raise RuntimeError("WordPress API must use the configured HTTPS host")
    username = os.environ["WORDPRESS_USERNAME"]
    password = os.environ["WORDPRESS_APP_PASSWORD"].replace(" ", "")
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    data = None
    headers = {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "User-Agent": "MoHan-GitHub-Release-Sync",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise RuntimeError(
            f"WordPress API returned {exc.code}: {detail}"
        ) from exc


def release_block(manifest: dict, release_url: str) -> str:
    version = html.escape(str(manifest["version"]))
    tag = html.escape(str(manifest["tag"]))
    cards = []
    for installer in manifest["installers"]:
        label = "EXE 安裝程式（建議）" if installer["kind"] == "exe" else "MSI 安裝套件"
        cards.append(
            '<article class="mohan-download-card"><a class="mohan-button mohan-button-primary" '
            'target="_blank" rel="noopener noreferrer" '
            f'href="{html.escape(installer["url"], quote=True)}">'
            f'下載 {label}<span>Download {installer["kind"].upper()}</span></a>'
            f'<small>SHA256<br><code>{html.escape(installer["sha256"])}</code></small></article>'
        )
    download_cards = "".join(cards)
    safe_release_url = html.escape(release_url, quote=True)
    return f"""{START_MARKER}
<style>
.mohan-landing{{--ink:#24324a;--muted:#65718a;color:var(--ink);font-family:"Noto Sans TC","Segoe UI",sans-serif;line-height:1.75}}
.mohan-landing *{{box-sizing:border-box}}.mohan-landing a{{text-decoration:none}}.mohan-shell{{max-width:1180px;margin:auto;padding:24px}}
.mohan-hero{{display:grid;grid-template-columns:1.08fr .92fr;align-items:center;gap:34px;padding:48px;border-radius:32px;background:linear-gradient(135deg,#eef7ff,#f5edff 52%,#fff0f5);box-shadow:0 20px 60px rgba(45,67,106,.14);overflow:hidden}}
.mohan-kicker{{font-weight:800;letter-spacing:.14em;color:#6f5aa8;text-transform:uppercase}}.mohan-hero h1{{font-family:"Noto Serif TC",serif;font-size:clamp(2.3rem,5vw,4.6rem);line-height:1.12;margin:.15em 0;color:#233b63}}
.mohan-hero h1 span{{display:block;font-family:"Segoe UI",sans-serif;font-size:.42em;font-weight:650;margin-top:12px;color:#6c6680}}.mohan-lead{{font-size:1.12rem;color:#4f5e78}}
.mohan-hero img{{width:100%;max-height:620px;object-fit:contain;filter:drop-shadow(0 20px 24px rgba(30,45,75,.22))}}.mohan-actions{{display:flex;flex-wrap:wrap;gap:12px;margin-top:24px}}
.mohan-button{{display:inline-flex;flex-direction:column;justify-content:center;align-items:center;min-height:52px;padding:11px 21px;border-radius:999px;font-weight:800;transition:.2s transform,.2s box-shadow}}
.mohan-button:hover{{transform:translateY(-2px);box-shadow:0 10px 22px rgba(35,56,91,.16)}}.mohan-button-primary{{background:#294a7a;color:#fff!important}}.mohan-button-soft{{background:#fff;color:#554777!important}}
.mohan-section{{padding:60px 0}}.mohan-section h2{{text-align:center;font-family:"Noto Serif TC",serif;font-size:clamp(1.8rem,3vw,2.7rem);margin:0 0 10px;color:#29446f}}
.mohan-sub{{text-align:center;max-width:850px;margin:0 auto 32px;color:var(--muted)}}.mohan-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.mohan-card{{padding:25px;border-radius:23px;background:#fff;box-shadow:0 12px 34px rgba(46,65,103,.1);border:1px solid rgba(70,90,130,.09)}}
.mohan-card:nth-child(3n+1){{background:linear-gradient(145deg,#fff,#edf6ff)}}.mohan-card:nth-child(3n+2){{background:linear-gradient(145deg,#fff,#f3edff)}}.mohan-card:nth-child(3n){{background:linear-gradient(145deg,#fff,#fff0f5)}}
.mohan-card h3{{margin:0 0 8px;color:#344f7c}}.mohan-card p{{margin:0;color:#5d6880}}.mohan-gallery{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}}
.mohan-gallery figure{{margin:0;background:#fff;padding:12px;border-radius:22px;box-shadow:0 10px 30px rgba(44,64,102,.1)}}.mohan-gallery img{{width:100%;border-radius:14px;display:block}}
.mohan-gallery figcaption{{text-align:center;padding:9px;color:#56637b;font-weight:700}}.mohan-theatre{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}}
.mohan-scene{{border-radius:24px;padding:22px;background:linear-gradient(145deg,#edf6ff,#fff);box-shadow:0 12px 34px rgba(45,65,100,.1);text-align:center}}
.mohan-scene:nth-child(2n){{background:linear-gradient(145deg,#f2ebff,#fff1f5)}}.mohan-scene img{{height:210px;max-width:100%;object-fit:contain}}.mohan-scene blockquote{{margin:12px 0 4px;font-weight:800;color:#3e4e70}}
.mohan-scene p{{margin:0;color:#68728a;font-size:.92rem}}.mohan-download{{padding:38px;border-radius:28px;background:linear-gradient(135deg,#e4f2ff,#f1eaff,#ffe9f1)}}
.mohan-download-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin:24px 0}}.mohan-download-card{{background:rgba(255,255,255,.84);padding:20px;border-radius:20px;text-align:center}}
.mohan-download-card .mohan-button{{width:100%}}.mohan-download-card .mohan-button span{{font-size:.8em;opacity:.82}}.mohan-download-card small{{display:block;margin-top:12px;color:#667188;word-break:break-all}}
.mohan-download-card code{{font-size:.72rem}}.mohan-trust{{text-align:center;color:#56627a}}.mohan-support{{display:grid;grid-template-columns:.8fr 1.2fr;gap:28px;align-items:center;padding:38px;border-radius:28px;background:linear-gradient(135deg,#fff3d9,#ffe9f2)}}
.mohan-support img{{width:100%;max-height:310px;object-fit:contain}}.mohan-support h2{{text-align:left}}.mohan-note{{font-size:.9rem;color:#69748a}}.mohan-footer{{text-align:center;padding:35px;color:#6a7487}}
@media(max-width:850px){{.mohan-hero,.mohan-support{{grid-template-columns:1fr}}.mohan-hero{{padding:28px}}.mohan-grid,.mohan-theatre{{grid-template-columns:1fr 1fr}}.mohan-hero img{{max-height:480px}}}}
@media(max-width:580px){{.mohan-shell{{padding:14px}}.mohan-grid,.mohan-theatre,.mohan-gallery,.mohan-download-grid{{grid-template-columns:1fr}}.mohan-section{{padding:42px 0}}.mohan-hero,.mohan-download,.mohan-support{{padding:22px;border-radius:22px}}}}
</style>
<main class="mohan-landing"><div class="mohan-shell">
<section class="mohan-hero"><div><div class="mohan-kicker">A Sword Spirit Beside Your Workflow</div>
<h1>墨寒<span>MoHan Desktop Assistant</span></h1>
<p class="mohan-lead">她是寄居於赤焰劍中的北宋千年女劍魂，也是主上身邊傲嬌而可靠的首席文膽與策士。如今，她以會眨眼、會說話、能記憶也能工作的 Windows 桌面虛擬助理之姿，陪你把靈感化為成果。</p>
<p class="mohan-lead">A thousand-year-old sword spirit from China’s Northern Song era—now reimagined as an expressive, voice-interactive Windows companion who helps you think, focus, remember, and create.</p>
<div class="mohan-actions"><a class="mohan-button mohan-button-primary" target="_blank" rel="noopener noreferrer" href="{safe_release_url}">前往 GitHub 下載<span>Download on GitHub</span></a>
<a class="mohan-button mohan-button-soft" target="_blank" rel="noopener noreferrer" href="{REPOSITORY_URL}">瀏覽開放原始碼<span>Explore the project</span></a></div></div>
<img src="{MEDIA_ROOT}/mohan-hero.png" alt="墨寒桌面語音互動虛擬助理主視覺"></section>

<section class="mohan-section"><h2>不只是會聊天的桌面角色</h2><p class="mohan-sub">More than a talking desktop character—MoHan combines companionship, productivity, memory, voice, animation, and permission-gated tools.</p>
<div class="mohan-grid">
<article class="mohan-card"><h3>自然語音對談</h3><p>Realtime 即時對話與一般語音模式並存，支援台灣繁體中文語音辨識、朗讀與回音抑制。<br>Realtime and standard voice modes with Traditional Chinese transcription and speech.</p></article>
<article class="mohan-card"><h3>電影級角色表現</h3><p>表情仲裁、眨眼、嘴型、呼吸、視差、注視與微動作共同運作。<br>Coordinated expressions, blinking, lip sync, breathing, parallax, gaze, and subtle motion.</p></article>
<article class="mohan-card"><h3>長期記憶</h3><p>依人物、偏好、目標等類型整理，可逐項查看、編輯、儲存與刪除。<br>Editable categorized memory for people, preferences, goals, and more.</p></article>
<article class="mohan-card"><h3>工作與創作中樞</h3><p>待辦、靈感、計時、休息提醒、平台進度與自訂工作卡集中管理。<br>Tasks, ideas, timers, breaks, progress tracking, and customizable work cards.</p></article>
<article class="mohan-card"><h3>安全的電腦工具</h3><p>敏感操作必須經權限、風險分級、計畫與確認。<br>Permission-gated tools with risk levels, plans, and explicit confirmation.</p></article>
<article class="mohan-card"><h3>可攜、開放、可延伸</h3><p>SQLite 本機資料、設定轉移、模組化架構與 MIT 授權。<br>Local data, profile transfer, modular design, and an MIT-licensed codebase.</p></article>
</div></section>

<section class="mohan-section"><h2>墨寒的傲嬌工程小劇場</h2><p class="mohan-sub">A tiny strategist’s theatre for developers who believe software can have both a soul and a test suite.</p>
<div class="mohan-theatre">
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/proud_front.png" alt="墨寒傲嬌"><blockquote>「妾才沒有等你的 Star，只是在確認軍心是否可用。」</blockquote><p>“I am not waiting for your Star. I am merely assessing morale.”</p></article>
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/thinking_front.png" alt="墨寒思考"><blockquote>「這段邏輯尚可。若再補上測試，妾便勉強准它入主分支。」</blockquote><p>“The logic is acceptable. Add tests, and I may permit it onto main.”</p></article>
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/shy_cute_front.png" alt="墨寒嬌羞"><blockquote>「你願意送來 PR？妾、妾只是替主上記下功勞。」</blockquote><p>“A pull request? I am only recording your service for my lord.”</p></article>
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/mock_hit_front.png" alt="墨寒佯怒"><blockquote>「未經測試便想合併？手伸出來。妾只敲一下。」</blockquote><p>“Merge without tests? Your hand, please. Just one tap.”</p></article>
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/gentle_smile_front.png" alt="墨寒開心"><blockquote>「全數綠燈……做得好。別誤會，妾只是尊重好工程。」</blockquote><p>“All checks green. Well done—not that I am impressed, of course.”</p></article>
<article class="mohan-scene"><img loading="lazy" src="{EXPRESSION_ROOT}/worried_front.png" alt="墨寒關心"><blockquote>「Bug 可以明日再查。你若累倒，誰來陪妾守著赤焰劍？」</blockquote><p>“The bug can wait until tomorrow. Do not make your strategist worry.”</p></article>
</div>
<div class="mohan-actions" style="justify-content:center"><a class="mohan-button mohan-button-primary" target="_blank" rel="noopener noreferrer" href="{REPOSITORY_URL}/pulls">向斬空閣呈上 PR<span>Contribute a pull request</span></a>
<a class="mohan-button mohan-button-soft" target="_blank" rel="noopener noreferrer" href="{REPOSITORY_URL}/issues">回報軍情<span>Open an issue</span></a></div></section>

<section class="mohan-section"><h2>從初次相遇到每日並肩</h2><p class="mohan-sub">A guided first run, expressive interaction, organized work, editable memory, and transparent permission controls.</p>
<div class="mohan-gallery">
<figure><img loading="lazy" src="{MEDIA_ROOT}/first-run-wizard.png" alt="墨寒首次設定精靈"><figcaption>首次設定精靈 / First-run wizard</figcaption></figure>
<figure><img loading="lazy" src="{MEDIA_ROOT}/voice-modes.png" alt="Realtime 與一般語音模式"><figcaption>雙語音模式 / Realtime &amp; standard voice</figcaption></figure>
<figure><img loading="lazy" src="{MEDIA_ROOT}/expressions.png" alt="墨寒表情系統"><figcaption>表情與動作 / Expressions &amp; motion</figcaption></figure>
<figure><img loading="lazy" src="{MEDIA_ROOT}/tasks-and-ideas.png" alt="墨寒待辦與創作靈感"><figcaption>待辦與靈感 / Tasks &amp; ideas</figcaption></figure>
<figure><img loading="lazy" src="{MEDIA_ROOT}/long-term-memory.png" alt="墨寒長期記憶"><figcaption>可編輯記憶 / Editable memory</figcaption></figure>
<figure><img loading="lazy" src="{MEDIA_ROOT}/security-permissions.png" alt="墨寒安全權限頁"><figcaption>權限與安全 / Permissions &amp; safety</figcaption></figure>
</div><div class="mohan-actions" style="justify-content:center"><a class="mohan-button mohan-button-soft" target="_blank" rel="noopener noreferrer" href="{REPOSITORY_URL}/blob/main/docs/media/mohan-demo.mp4">觀看 36 秒展示影片<span>Watch the 36-second demo</span></a></div></section>

<section class="mohan-section mohan-download"><h2>安全地從 GitHub 取得墨寒</h2>
<p class="mohan-sub"><strong>最新版本 / Latest version: {version}</strong> ({tag})<br>本站不儲存安裝檔；所有下載、更新與驗證資料皆由 GitHub Releases 提供。<br>Installers are never hosted on this WordPress site; downloads, updates, and verification data come from GitHub Releases.</p>
<div class="mohan-download-grid">{download_cards}</div><p class="mohan-trust">Windows 10/11 x64 · Automated CI build · SHA256 · SBOM · Artifact Attestation</p>
<div class="mohan-actions" style="justify-content:center"><a class="mohan-button mohan-button-soft" target="_blank" rel="noopener noreferrer" href="{safe_release_url}">版本說明與驗證資料<span>Release notes &amp; verification</span></a></div></section>

<section class="mohan-section mohan-support"><img loading="lazy" src="{EXPRESSION_ROOT}/shy_cute_front.png" alt="墨寒嬌羞表情"><div><h2>傲嬌策士的軍糧補給處</h2>
<p>「妾才不是在等贊助……只是替主上巡視軍糧。若真願意相助，妾……會記得的。」</p><p><em>“I am not waiting for support… merely inspecting our provisions. If you truly wish to help, I shall remember it.”</em></p>
<div class="mohan-actions"><a class="mohan-button mohan-button-primary" target="_blank" rel="noopener noreferrer" href="{BUY_ME_A_COFFEE_URL}">Buy Me a Coffee</a>
<a class="mohan-button mohan-button-soft" target="_blank" rel="noopener noreferrer" href="{PAYPAL_ME_URL}">PayPalMe</a></div>
<p class="mohan-note">贊助完全自願，請先照顧好自己的生活。Support is entirely optional—please take care of yourself first.</p></div></section>
<footer class="mohan-footer">Created with passion by CHOU MING HUA · MIT License · 墨寒附生於赤焰劍，而她的程式碼屬於每一位願意讓夢想走進現實的人。</footer>
</div></main>
{END_MARKER}"""


def replace_managed_block(current: str, block: str) -> str:
    if START_MARKER in current and END_MARKER in current:
        before, remainder = current.split(START_MARKER, 1)
        _, after = remainder.split(END_MARKER, 1)
        return before.rstrip() + "\n\n" + block + "\n" + after.lstrip()
    return current.rstrip() + "\n\n" + block + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--release-url", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base = os.environ["WORDPRESS_BASE_URL"].rstrip("/")
    api = f"{base}/wp-json/wp/v2/pages"
    page_id = os.environ.get("WORDPRESS_DOWNLOAD_PAGE_ID", "").strip()

    if page_id:
        page = request_json(f"{api}/{int(page_id)}?context=edit")
    else:
        query = urllib.parse.urlencode(
            {"slug": DEFAULT_SLUG, "context": "edit", "per_page": 1}
        )
        pages = request_json(f"{api}?{query}")
        page = pages[0] if isinstance(pages, list) and pages else None

    block = release_block(manifest, args.release_url)
    if page is None:
        updated = request_json(
            api,
            method="POST",
            payload={
                "title": "墨寒語音互動虛擬助理｜MoHan Desktop Assistant",
                "slug": DEFAULT_SLUG,
                "status": "publish",
                "content": block,
            },
        )
    else:
        page_id = int(page["id"])
        current = str(page.get("content", {}).get("raw", ""))
        updated = request_json(
            f"{api}/{page_id}",
            method="POST",
            payload={"content": replace_managed_block(current, block)},
        )
    print(updated["link"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
