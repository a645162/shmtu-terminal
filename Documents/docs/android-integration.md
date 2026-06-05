# Android 端集成 shmtu-cas-kotlin 指南

`shmtu-terminal-android` 已集成 `shmtu-cas-kotlin/cas_android_lib`，本节描述集成方式与依赖关系。

## 1. 项目模块结构

```
shmtu-terminal-android/
├── app/                     # Android 主应用 (UI + Hilt)
│   ├── src/main/java/cn/edu/shmtu/terminal/android/
│   │   ├── data/            # Repository, Room, DataStore, Hilt Module
│   │   ├── domain/          # Use Cases, Repository Interfaces, Models
│   │   └── ui/              # Compose Screens + ViewModels
├── lib/shmtu-cas-kotlin/    # 共享库
│   ├── cas_lib/             # 纯 JVM
│   ├── cas_android_lib/     # Android wrapper (Hilt)
│   └── cas_cli/             # CLI 演示
├── shmtu_ocr/               # 本地 NCNN OCR 模块
└── settings.gradle.kts
```

## 2. Gradle 配置

### settings.gradle.kts

```kotlin
include(":app", ":shmtu_ocr", ":cas_lib", ":cas_android_lib")
project(":cas_lib").projectDir = file("lib/shmtu-cas-kotlin/cas_lib")
project(":cas_android_lib").projectDir = file("lib/shmtu-cas-kotlin/cas_android_lib")
project(":shmtu_ocr").projectDir = file("shmtu_ocr")
```

### app/build.gradle.kts

```kotlin
dependencies {
    implementation(project(":cas_lib"))
    implementation(project(":cas_android_lib"))
    implementation(libs.okhttp)
    implementation(libs.hilt.android)
    ksp(libs.hilt.android.compiler)
    implementation(libs.room.runtime)
    ksp(libs.room.compiler)
    implementation(libs.work.runtime.ktx)
    ksp(libs.hilt.work.compiler)
}
```

## 3. Hilt Module 接线

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object DataStoreModule {
    @Provides @Singleton
    fun provideEpayAuth(): EpayAuth = EpayAuth()
    
    @Provides @Singleton
    fun provideBillRulesManager(@ApplicationContext ctx: Context): BillRulesManager = ...
}
```

`EpayAdapter` 包装:

```kotlin
@Singleton
class EpayAdapter @Inject constructor(
    private val secureStorage: SecureStorage,
    @ApplicationContext private val context: Context,
    val billDbManager: BillDatabaseManager,
    private val billRulesManager: BillRulesManager
) {
    fun getEpayAuth(accountId: Long): EpayAuth = ...
    suspend fun submitLogin(...) = ...
    suspend fun fetchBillPage(...) = ...
    fun parseBillList(html: String): List<Map<String, String>> = ...
}
```

## 4. 数据流（关键集成点）

### 同步

```kotlin
class RoomBillStore(...) : BillStore {
    override fun merge(newBills: List<BillItem>) {
        val entities = newBills.map { bill ->
            val cat = billRulesManager.classifier?.classifyKey(bill.billType, bill.targetUser)
            val pos = billRulesManager.positionTranslator?.translate(bill.targetUser)
            BillEntity(
                ..., type = bill.billType,
                category = cat ?: "other",
                position = pos?.position,
                room = pos?.room,
                building = pos?.position
            )
        }
        accountDb.billDao().insertAll(entities)
        identityDb.billDao().insertAll(entities)
    }
}
```

### 统计

```kotlin
override fun getCategoryBreakdown(...): Flow<List<CategoryBreakdown>> {
    return mergedBills(identityId).map { bills ->
        bills.filterSuccessful().filterByRange(start, end).filterNot(::isIncome)
            .groupBy { it.category ?: "other" }
            .mapValues { (_, items) -> items.sumOf { abs(it.moneyValue()) } }
            ...
    }
}
```

## 5. TOML 规则加载

```kotlin
@Singleton
class BillRulesManager @Inject constructor(@ApplicationContext context: Context) {
    val localDir = File(context.filesDir, "bill")
    suspend fun ensureLocalFiles() { ... }   // 启动时: 缺失则从 GitHub 下载
    fun readFile(name: String): String { ... }
    suspend fun downloadAll() { ... }
}
```

加载顺序: `filesDir/bill/<name>` → `assets/bill/<name>` → `defaultRules()` 兜底

## 6. 常见问题

**Q: 为什么 `BillClassifier` 在 `cas_lib` 包不在 `app` 包?**
A: 让 cas_lib 是纯 JVM 库, 方便将来跨端共享 (iOS / CLI / 服务端)。

**Q: `cas_android_lib` 和 `cas_lib` 区别?**
A: `cas_lib` 是纯 JVM; `cas_android_lib` 是 Android wrapper, 把 cas_lib 包装成 Hilt module。

**Q: 怎么贡献新功能?**
A: 在 `cas_lib` 加纯 JVM 实现 → 在 `cas_android_lib` 加 Hilt 包装 → 在 `app` 调用。

## 7. 调试技巧

```bash
adb shell run-as cn.edu.shmtu.terminal.android ls files/bill/
adb shell run-as cn.edu.shmtu.terminal.android cat files/bill/rules.toml
```

## 8. 跨端共享约束

`cas_lib` 严格保持:
- 无 `android.*` 依赖
- 纯 JVM 17 字节码

可编译成 Android / JVM / CLI / (部分 Web)。
