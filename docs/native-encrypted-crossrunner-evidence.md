# OpenClaw 原生加密備份：第二獨立環境還原實測

結果：**PASS，僅限全新假資料與以下測試範圍。正式部署仍 NO-GO。**

日期：2026-11-17（Europe/London，當日 UTC+0）
測試 commit：`bdae4fba387b648656920bdde7cc51c5f87d5cc8`
OpenClaw：`2026.10.5`，固定 upstream commit `1b58cb9a1b4f4353e1add63c8506db4d890962e8`。

## 實際證據

[Actions run #44091074529](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44091074529)：
- 第一個獨立 GitHub-hosted runner：[produce job 134065996347](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44091074529/job/134065996347)，SUCCESS。
- 第二個獨立 GitHub-hosted runner：[restore job 134069235269](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44091074529/job/134069235269)，SUCCESS。
- 已透過 GitHub API 直接讀取兩份完成的 job 日誌，非截圖或沿用上一輪 PASS。

第一台建立全新假資料，完成真實 OpenClaw Gateway／Agent 與本機假模型回覆，停止 Gateway 後執行原生 storage init/test、backup create --to、backup verify。只匯出新建立的加密 storage 目錄（包含復原所需 location marker），另附靜態檔案 SHA-256 清單。第二台獨立取得同一固定版本原始碼並重新建置，使用另外兩個全新 named volumes；沒有接入第一台的 state volume。

第二台完成日誌（2026-11-17 13:25 UTC）：

```text
SECOND_HOST_INDEPENDENT_TRANSFER_DIGEST_AND_LAYOUT=PASS
THIS_RUNNER_NONROOT_NO_NETWORK_NO_BINDS_READ_ONLY_ROOT=PASS
OFFSITE_BACKUP_IS_OPENCLAW_AUTHENTICATED_CIPHERTEXT=PASS
TRANSFER_STORE_NO_KNOWN_PLAINTEXT_OR_DUMMY_PASSPHRASE=PASS
Assets verified: 2
Canonical SQLite inventory verified.
Backup archive restored to staging: /tmp/restored
Archive entries restored: 25
SECOND_HOST_CONFIG_FIXTURE_AND_ALL_WORKSPACE_SHA256=PASS files=3
SECOND_HOST_WRONG_RESTORE_REJECTED_WITH_NO_OUTPUT=PASS exit=1
FICTIONAL_OFFSITE_CIPHERTEXT_INTENTIONALLY_TAMPERED=PASS
SECOND_HOST_TAMPER_RESTORE_REJECTED_WITH_NO_OUTPUT=PASS exit=1
SECOND_HOST_NATIVE_ENCRYPTED_RESTORE=PASS
```

靜態逐檔比對涵蓋 openclaw.json、fictional-proof.txt 與完整 workspace（本 fixture 僅一個 workspace 檔），共 3 檔。比對也要求 workspace 檔案集合完全相同。SQLite 經官方 archive inventory 驗證，但未與執行前的可變資料庫逐位元比對；未啟動第二台還原後的 Agent。

錯誤密碼與篡改案例實際執行官方 backup restore；測試要求非零 exit、錯誤訊息符合密碼／解密／認證失敗，且目標不存在或沒有檔案，避免把任意錯誤當成拒絕測試通過。篡改是在第二台對密文最後一個 byte 翻轉一個 bit。

## 邊界與限制

兩台 runtime 均檢查 UID 10001、network none、唯讀根目錄、cap-drop ALL、no-new-privileges、無 host bind、Docker socket、裝置或公開 port，只使用自己新建的 Docker named volumes；producer 另實際測試 IPv4／IPv6 無外網。套件下載及建置準備仍使用 runner 網路，不是完整供應鏈認證。

只使用公開、硬編碼的假密碼及假 token，沒有傳入真實 OpenClaw／模型／通訊憑證。密文確認 OCSTOR1 格式，storage 所有檔案掃描未發現已知 fixture 明文或假密碼；這不等於任意秘密掃描或真實密碼保管／保密驗證。公開假密碼使此樣本不能被視為對知道程式碼的觀察者保密。

僅上傳假資料 artifact `native-encrypted-fiction-44091074529`，大小 72,278 bytes，ZIP SHA-256：
`bda5222fb4bf0af967f26aefa95d02fed396beab5017f29b17bb4e6810f85f21`。
設定保留一天，API 到期時間為 2026-11-18 13:21:56 UTC。未將真實資料或憑證加入 repository／artifact。

本次重新產生 fixture；上一輪 native encrypted pilot 沒有匯出 artifact，因此不是對上一輪那份實體備份進行還原。本次證明的是新產生的原生加密備份跨兩台獨立 runner 還原。

未存取、查詢或修改 Mac mini、歷史 OpenClaw／Hermes 或正式資料；未合併 PR、部署或改動 main。測試程式和本紀錄僅位於未合併 lab 分支。這不證明真實主機復原、持久異地儲存、真實秘密保管、完整 Agent 復原功能或 G0–G7 正式准入。

最小下一步：本項假資料跨環境還原驗收已完成；保留證據並維持 PR 草稿、正式部署 NO-GO。無需 Edward 提供真實密碼或手動操作。
