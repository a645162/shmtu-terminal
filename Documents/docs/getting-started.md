# 快速集成 shmtu-cas-kotlin

`shmtu-cas-kotlin` 是 SHMTU 校园终端的 Kotlin 共享库，提供 CAS 认证、账单解析、TOML 分类规则、OCR 验证码识别等核心能力。

## 1. 模块结构

```
shmtu-cas-kotlin/
├── cas_lib/                 # 纯 JVM 库 (Java 17+)
│   ├── cn.edu.shmtu.cas.auth       # CAS 认证 (EpayAuth, WechatAuth)
│   ├── cn.edu.shmtu.cas.parser    # 账单 HTML 解析 (BillParser, HotWaterParser)
│   ├── cn.edu.shmtu.cas.classifier # TOML 分类器
│   ├── cn.edu.shmtu.cas.datatype   # 数据类型 (BillItem, BillType, BillItemStatus)
│   ├── cn.edu.shmtu.cas.session    # 会话探测
│   ├── cn.edu.shmtu.cas.captcha    # 验证码 (Captcha, CaptchaAnswer)
│   └── cn.edu.shmtu.cas.sync      # 同步框架
├── cas_android_lib/         # Android wrapper
├── cas_cli/                 # CLI demo
└── ocr_app_demo/            # Android OCR demo
```

## 2. JVM 库集成 (cas_lib)

### Gradle 依赖

```kotlin
// settings.gradle.kts
include(":cas_lib")
project(":cas_lib").projectDir = file("shmtu-cas-kotlin/cas_lib")

// build.gradle.kts
dependencies {
    implementation(project(":cas_lib"))
    implementation("org.jsoup:jsoup:1.22.2")
    implementation("com.squareup.okhttp3:okhttp:5.3.2")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.11.0")
}
```

### CAS 登录 (EpayAuth)

```kotlin
import cn.edu.shmtu.cas.auth.EpayAuth

val auth = EpayAuth()
val probe: SessionProbe = auth.probeLogin()
val challenge = auth.prepareChallenge()
val result: LoginSubmitResult = auth.submitLogin(
    username = "2024001", password = "...",
    captchaCode = "1234", execution = challenge.execution
)
```

### 账单抓取

```kotlin
import cn.edu.shmtu.cas.datatype.BillType
import cn.edu.shmtu.cas.parser.BillParser

val html = auth.getBill(page, billType = BillType.ALL)
val items: List<BillItem> = BillParser().parseBillItems(html)
```

### 同步框架

```kotlin
import cn.edu.shmtu.cas.sync.AccountSyncJob
import cn.edu.shmtu.cas.sync.SyncOptions
import cn.edu.shmtu.cas.sync.BillStore

object MyBillStore : BillStore {
    override fun contains(transactionNo: String): Boolean = ...
    override fun merge(newBills: List<BillItem>) { ... }
    override fun clear() { ... }
}

val job = AccountSyncJob(
    context = AccountContext(accountId = "2024001", accountLabel = "海事终端"),
    auth = auth, store = MyBillStore,
    options = SyncOptions.incremental(syncRange = SyncRangePreset.MONTH),
    fullSync = false
)
val summary = cn.edu.shmtu.cas.sync.syncAccountsParallel(jobs, translated = true)
```

## 3. 验证码识别 (本地 ONNX)

```kotlin
import cn.edu.shmtu.cas.captcha.Captcha

val answer = Captcha.ocrByRemoteTcpServerAutoRetry(
    host = "192.168.1.100", port = 8888, imageData = challenge.imageBytes
)
```

## 4. TOML 分类器

见 [classifier.md](./classifier.md)。快速示例：

```kotlin
import cn.edu.shmtu.cas.classifier.BillClassifier

val classifier = BillClassifier.fromToml(typeToml)
val cat = classifier.classify("中行云充值", "A食堂1楼")
```

## 5. Android wrapper (cas_android_lib)

```kotlin
dependencies { implementation(project(":cas_android_lib")) }
```

提供 `EpayAdapter` (Hilt @Singleton) 包装 EpayAuth。

## 6. CLI demo

```bash
cd shmtu-cas-kotlin/cas_cli
./gradlew run --args="2024001 yourpassword"
```

## 7. 常见问题

**Q: TOML 文件不通过 `toml` crate 解析可以吗?**
A: 可以。Android 端 `TomlLightweight` 自实现的极简解析器支持 4 个文件用到的语法子集。

**Q: 怎么更新 type.toml 加新分类?**
A: (1) 在 `type.toml` 加 `[type.coffee]` 段; (2) 在 `BillClassifier.kt` 加 `COFFEE` 枚举值; (3) 加 `displayName` / `emoji`。详见 [toml-format.md § 8](./toml-format.md)。

## 8. 路线图

- [x] CAS 认证 / 账单解析 / TOML 分类器 / GitHub 同步
- [ ] 微信小程序 SDK / iOS Swift wrapper
