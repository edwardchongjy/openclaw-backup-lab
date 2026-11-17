# OpenClaw 原生加密備份：第二個獨立環境復原驗證

## 最終結果：PASS（只限本輪合成資料範圍）

- [完整成功工作 #44090241882](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44090241882)，測試 commit `ca66633eb154d72c6bcc845583412df2b432fb9b`。已直接讀取兩個已完成 jobs 的完整實際 logs，非僅引用綠色狀態。
- [produce job 134063175055](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44090241882/job/134063175055)：SUCCESS；Worker ID `0a00e3eb-9fa4-43de-9580-6c79fe13b885`。
- [restore job 134066331557](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44090241882/job/134066331557)：SUCCESS；Worker ID `924536d8-18a6-45ec-b36d-ca585469b777`。兩個 Worker ID 不同。
- 還原端於 13:20:31 UTC 官方驗證 2 個 assets、32 個封存項目及 canonical SQLite inventory；13:20:34 完成 staging 還原及指定 8/8 檔案大小/SHA-256 比對；13:20:35 完成篡改拒絕測試。
- 原生密文物件為 62,310 bytes。transfer tar SHA-256：`bbc01a1563eb83e1f4c2c1b0c5ba3438532f0f706911e67e55f799d56505002a`，接收端以獨立 producer job output 比對成功。
- [測試 artifact 14331737343](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44090241882/artifacts/14331737343)：ZIP 71,832 bytes，ZIP digest `645ad1f900a13a6a24d9a445c4d6754c70979f176f22dbf64974454aade0acb3`；到期時間 2026-11-18 13:16:56 UTC。ZIP digest 與 transfer tar digest 屬不同層，不能混用。

實際 log 中逐項核對的標記：

```text
SECOND_INDEPENDENT_RUNNER_TRANSFER_SHA256_MATCH=PASS
INDEPENDENT_RUNNER_OFFICIAL_VERIFY=PASS
WRONG_PASSPHRASE_NATIVE_RESTORE_REFUSED=PASS
WRONG_KEY_REJECTION_LEFT_NO_RESTORED_FILES=PASS
SOURCE_AND_RESTORED_CORPUS_CONFIG_8_OF_8_SHA256_MATCH=PASS
RESTORED_CONFIG_RETAINS_FICTIONAL_MODEL_ROUTE=PASS
RESTORE_STAGING_ONLY_NO_ACTIVATION=PASS
TAMPERED_CIPHERTEXT_NATIVE_RESTORE_REFUSED=PASS
TAMPER_REJECTION_LEFT_NO_RESTORED_FILES=PASS
NATIVE_ENCRYPTED_CROSS_RUNNER_TEST=PASS
```

指定 corpus 的實測還原雜湊：

```text
RESTORED_FILE_SHA256 "workspace/cross-fixture/empty.txt" e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
RESTORED_FILE_SHA256 "workspace/cross-fixture/nested/message.txt" 8547119ae4b4fbfa286d995283b4ed23599797e0ea0dd101bee35c408a5f86d1
RESTORED_FILE_SHA256 "workspace/cross-fixture/繁體中文 空格.txt" 0d7a4d7e1d81add643c5c0f02acee3ddcfb363f0cfc6200c7baa1b37c4054199
RESTORED_FILE_SHA256 "workspace/cross-fixture/binary.bin" c8f5d0341d54d951a71b136e6e2afcb14d11ed8489a7ae126a8fee0df6ecf193
RESTORED_FILE_SHA256 "state/cross-fixture.json" fcd29db6a777e938415b6fc2d076005be90eaa04953009255d29700762173237
RESTORED_FILE_SHA256 "state/openclaw.json" 1ba16d619a6aae4bcf07f30a0456838b2d873cfea8a0e8a2bd8cc65eb5f585ff
RESTORED_FILE_SHA256 "state/fictional-proof.txt" 8e2cafe7c4df1fcc5154f6679622c191f8921e81aad35bbcff9ad0f6bc195555
RESTORED_FILE_SHA256 "workspace/persisted-fake-note.txt" a7cd4fac03a4afbc60635961e319de34fc3d34f3b935ffcb3481cc7c2e1838d1
```

PASS 不代表全部正式資料覆蓋、還原後 Agent 功能、真實保密性、獨立安全認證或正式系統准入。受保護 main 仍在 `5e0a1870f856bbea6b99bf48ae3fe31cb4e3450f`；PR #1 草稿未合併。正式部署 NO-GO。

日期：2026-11-17（Europe/London，當日 UTC+0）。

本輪只驗證全新虛構資料的原生加密備份跨環境 staging 還原；未授權、未進行正式部署或舊系統操作。測試在另開的 `lab/native-encrypted-crossrunner-20261117` 分支執行，未更新 PR #1 的來源分支。

## 測試固定來源與邊界

- 基於 PR #1 的 `43de26491a442ea8d4326f85e800b48ae1c4ff1d`；讀取原生加密前次工作 #44082717633 的已完成實際 job log，而非只依賴 PR 文字。
- OpenClaw `2026.10.5`，upstream `1b58cb9a1b4f4353e1add63c8506db4d890962e8`。
- Node `24.16.0`，基底映像固定 digest `sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203`。
- `produce` 與 `restore` 是兩個獨立的 GitHub-hosted Ubuntu 24.04 jobs，分別建置固定來源、建立各自的新 Docker state/storage volumes。透過 artifact 交換的只有測試儲存位置內容及獨立的預期檔案雜湊；未傳送來源 live-state volume。
- 測試容器為 UID 10001、唯讀 rootfs、`--network none`、全部 Linux capabilities 移除、`no-new-privileges`、無 host-directory bind、無 host Docker socket 或 published ports。每個 Node CLI/helper 容器啟動前檢查實際 `docker inspect`。只有新建測試 volumes 與 private tmpfs 可寫。
- 源 Gateway 使用本機虛構 provider，並在備份前停止。還原端起初沒有來源 state/workspace，僅建立最小 storage 設定，未重建 Agent。
- 假密碼為公開 fixture；沒有真實 OpenClaw/provider/channel 憑證。本測試不能證明對已知公開測試密碼的觀察者保密。

## 實際驗證方法

1. 官方 `storage init/test`，`backup create --to ciarchive --namespace ci-fresh-fiction`，`backup verify --from ciarchive --namespace ci-fresh-fiction latest`。
2. 檢查加密物件 `OCSTOR1\n`；掃描輸出 storage，拒絕出現測試密碼或已知測試內容。artifact 設一天到期。
3. 生產 job 以獨立 job output 傳出 transfer tar SHA-256。接收 job 必須比對相同 digest，並在匯入前拒絕連結、特殊檔案、越界路徑、重複名稱或超限項目。
4. 第二個 job 官方驗證封存與 canonical SQLite inventory。錯誤假密碼實際嘗試 `backup restore`，要求非零退出、解密/密碼錯誤訊息，且失敗目標沒有檔案。
5. 正確密碼實際還原至新 staging 位置。8 個指定檔案逐一比對備份前的大小與 SHA-256：空檔、巢狀文字、繁體中文含空格檔名、4096-byte binary、JSON、設定、原始虛構 state/workspace markers。這是指定測試 corpus 的逐檔比對，並非宣稱所有正式資料已驗證。
6. 在接收端故意翻轉 ciphertext 的最後一 byte，再次實際 `backup restore`；要求非零退出、驗證/解密錯誤，以及空失敗目標。還原後不啟動 Gateway、不套用至 live state。

## 必須保留的失敗紀錄

[首次工作 #44088666968](https://github.com/edwardchongjy/openclaw-backup-lab/actions/runs/44088666968)，commit `867c30f360aff7fa8048d2cd265796c7ef94a6a5`：producer 成功；restore 已實際還原 32 項、8 檔雜湊相符及拒絕錯誤密碼，但額外 helper 錯誤假設 `cfg.agents.list` 存在，出現 `TypeError`，因此整體 FAILURE，篡改測試尚未執行。不能標成全項 PASS。

修正僅將錯誤的設定欄位檢查換成此固定版本已寫入的虛構模型 route 檢查；8 個檔案的 hash/size、原生 verify/restore、隔離及負向測試要求保留。修正後以新工作完整重跑兩個 jobs。

## 範圍限制與最小下一步

只證明本輪合成資料與固定版本的跨 runner 原生加密復原行為。未測長期獨立備份服務、真實 key escrow/輪替、live state 靜態加密或正式機器復原。依賴下載/建置在一次性 runner 上仍可連外；隔離容器內的執行無外網，非完整供應鏈認證。

Mac mini、運作中的舊 OpenClaw、Hermes、真實或受保護歷史資料與其 aliases 均不屬測試輸入；未做正式連線/路徑探測、合併、部署或正式資料刪除。PR #1 維持草稿未合併，受保護 main 不變，G0–G7 與正式部署維持 NO-GO。

本輪驗證完成後保留可重現測試與實際紀錄即可；Edward 無需手動操作。任何真實憑證、正式機器或正式部署另行授權。
