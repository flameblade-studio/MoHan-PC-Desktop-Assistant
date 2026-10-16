### 資安與隱私邊界修復／安全与隐私边界修复／Security and privacy boundary fixes／セキュリティとプライバシー境界の修正

- 完整遮罩稽核敏感內容，將聊天名稱顯示為純文字，並讓個人路徑守衛拒絕無法讀取的文字檔。／完整遮罩审计敏感内容，将聊天名称显示为纯文本，并让个人路径守卫拒绝无法读取的文本文件。／Fully redact sensitive audit content, render speaker names as plain text, and reject unreadable text files in the personal-path guard.／監査の機密内容を完全にマスクし、発話者名をプレーンテキストで表示し、個人パス検査で読み取れないテキストファイルを拒否します。
- 撤銷資料夾與 OAuth 授權後立即阻止舊工作繼續取得權限，並阻擋網站路徑繞過及 WordPress 認證重新導向。／撤销文件夹与 OAuth 授权后立即阻止旧任务继续取得权限，并阻止网站路径绕过及 WordPress 认证重定向。／Invalidate stale work after folder and OAuth revocation, and block website path bypasses and authenticated WordPress redirects.／フォルダーと OAuth の許可取り消し後に古い処理の権限を無効化し、ウェブサイトのパス制限回避と WordPress 認証付きリダイレクトを防止します。
- 驗證 SVG 尺寸、備份描述、人臉向量維度與攜帶檔版本，拒絕無效輸入並保留既有有效資料。／验证 SVG 尺寸、备份描述、人脸向量维度与便携文件版本，拒绝无效输入并保留现有有效数据。／Validate SVG dimensions, backup manifests, face-vector dimensions, and portable-profile versions while preserving valid existing data.／SVG 寸法、バックアップ記述、顔ベクトルの次元、携帯プロファイルのバージョンを検証し、不正な入力を拒否して既存の有効なデータを保持します。
