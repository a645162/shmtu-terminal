# Android 端账单按 TOML 翻译完整链路

本文档描述 `shmtu-terminal-android` 中一条账单从同步到统计的完整处理流程，**与 Tauri 端行为完全对齐**。

## 1. 数据流总览

```
┌─────────────────────────────────────────────────────────────────────┐
│ 网络层 (EpayAuth)                                                    │
│   • CAS 登录 → getBill(pageNo) → HTML                                │
│   • BillParser.parseBillItems(html) → List<BillItem>                │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 同步层 (SyncAccountBillsUseCase / SyncIdentityBillsUseCase)         │
│   • AccountSyncJob(EpayAuth, BillStore)                              │
│   • 通过 cn.edu.shmtu.cas.sync.syncAccountsParallel 并行同步         │
│   • PeriodicBillSyncWorker (WorkManager) 定时触发                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 落库层 (RoomBillStore.merge)                                          │
│   • BillItem → BillEntity                                            │
│   • BillRulesManager.classifier.classifyKey() → category             │
│   • BillRulesManager.positionTranslator.translate() → pos/room       │
│   • 写入 bills 表 (account 库 + identity 库双写)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 读取层 (BillRepositoryImpl)                                          │
│   • getBillsForIdentity / getBillsForAccount                          │
│   • mergedBills(identityId) 跨库 join                                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 统计层 (BillRepositoryImpl.getCategoryBreakdown 等)                  │
│   • 直接 groupBy { it.category ?: ... } (与 Tauri get_category_       │
│     distribution 完全一致)                                            │
│   • 可选: billClassifier.classifyKey() 即时跑 (老数据兜底)            │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│ UI 层 (BillStatisticsScreen)                                         │
│   • 5 Tab: 总览 / 分类分析 / 位置分布 / 月度对比 / 忘记拔卡            │
│   • CategoryBreakdown 列表 → CategoryDisplay.displayName/emoji/color │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 同步触发 (SyncAccountBillsUseCase)

```kotlin
@Singleton
class SyncAccountBillsUseCase @Inject constructor(...) {
    suspend operator fun invoke(account: Account): SyncResult {
        // 1. 取当前身份 ID
        // 2. 调 EpayAuth.getBill(pageNo) 拉 HTML
        // 3. BillParser.parseBillItems(html) → List<BillItem>
        // 4. 创建 RoomBillStore(accountId, userId, identityId)
        // 5. store.merge(newBills) ← 这里做分类 + 位置翻译 + 落库
        // 6. 返回 SyncResult(newCount, success, errorMessage)
    }
}
```

**WorkManager 触发** (`SHMTUTerminalApp.onCreate`):
```kotlin
val req = PeriodicWorkRequestBuilder<PeriodicBillSyncWorker>(intervalMin, MINUTES)
    .setInputData(inputData.putBoolean(KEY_ENABLED, true))
    .setConstraints(Constraints.Builder().setRequiredNetworkType(CONNECTED).build())
    .build()
WorkManager.getInstance(this).enqueueUniquePeriodicWork(NAME, UPDATE, req)
```

读 `feature_settings` SharedPreferences 的 `auto_sync_enabled` + `auto_sync_interval`，**不走 KSP 注入**（绕开 KSP bug）。

## 3. 落库 (RoomBillStore.merge)

```kotlin
class RoomBillStore @Inject constructor(...) : BillStore {
    var classifier: BillClassifier? = null
    var positionTranslator: PositionTranslator? = null

    override fun merge(newBills: List<BillItem>) {
        val rawEntities = newBills.map { it.toEntity(accountId, studentId) }
        val entities = rawEntities.map { e ->
            val cat = classifier?.classifyKey(e.type, e.targetUser)
            val pos = positionTranslator?.translate(e.targetUser)
            e.copy(
                category = cat ?: "other",
                position = pos?.position ?: e.position,
                room = pos?.room ?: e.room,
                building = pos?.position ?: e.building
            )
        }
        // 双写
        accountDb.billDao().insertAll(entities)
        identityDb.billDao().insertAll(entities)
    }
}
```

**双写逻辑**：每条账单写入两个 Room 数据库
- `account_{studentId}.sqlite` —— 账号原始库（用于账号级去重、原始明细）
- `identity_{id}.sqlite` —— 身份合并库（用于身份级统计、跨账号聚合）

## 4. 读取 (BillRepositoryImpl.mergedBills)

```kotlin
private fun mergedBills(identityId: Long?): Flow<List<BillEntity>> {
    return getDatabases(identityId).flatMapLatest { dbs ->
        if (dbs.isEmpty()) flowOf(emptyList()) else
            combine(dbs.map { it.billDao().getAllBills() }) { results ->
                results.flatMap { it.toList() }
            }
    }
}
```

`getDatabases` 返回身份下所有账号的 DB 列表（多账号合并）。

## 5. 统计 (BillRepositoryImpl.getCategoryBreakdown)

```kotlin
override fun getCategoryBreakdown(identityId: Long?, startDate: String, endDate: String): Flow<List<CategoryBreakdown>> {
    return mergedBills(identityId).map { bills ->
        val merged = bills.filterSuccessful()
            .filterByRange(startDate, endDate)
            .filterNot(::isIncome)
            // 直接用 BillEntity.category 字段 (落库时已分类)
            .groupBy { it.category ?: billClassifier?.classifyKey(it.type, it.targetUser) ?: "other" }
            .mapValues { (_, items) -> items.sumOf { abs(it.moneyValue()) } }
        ...
    }
}
```

**与 Tauri 端对齐**：
- Tauri `get_category_distribution` 用 `BillClassifier::classify(item_type, target_user, 0).type_label` 实时跑
- Android 端用 `BillEntity.category` (落库时算过) + `billClassifier.classifyKey` (老数据兜底)

## 6. 关键表结构 (bills)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Long (PK, auto) | |
| `accountId` | Long | app 域账号 ID |
| `accountLabel` | String | 账号 userId（用于显示） |
| `dateStr` | String | "yyyy.MM.dd" |
| `timeStr` | String | "HHmmss" |
| `dateTimeStrFormat` | String | "yyyy.MM.dd HH:mm:ss" |
| `type` | String | 账单原始 item_type（中行云充值 / 消费 / ...） |
| `transactionNo` | String | 交易号（去重 key） |
| `targetUser` | String | 对方账户（位置/分类 key） |
| `money` | String | "¥12.34" |
| `method` | String | 支付方式 |
| `status` | String | "SUCCESS" / "交易成功" / ... |
| `position` | String? | 楼栋 |
| `room` | String? | 房间/窗口 |
| `notes` | String? | 备注 |
| `category` | String? | 分类 key（"deposit" / "canteen" / ...） |
| `building` | String? | 楼栋（冗余字段，与 position 相同） |

## 7. Schema 迁移历史

| version | 变更 |
|---------|------|
| 1 | 初版（无 category/building/position/room） |
| 2 | 加 category + building 字段 |

`BillDatabase.kt` 用 `version = 2` + `fallbackToDestructiveMigration(false)` 保护 schema 不匹配崩溃。

## 8. 与 Tauri 端映射表

| Tauri 命令 | Android 方法 |
|-----------|---------------|
| `get_bill_statistics(identity_id)` | `BillRepositoryImpl.getCategoryBreakdown()` |
| `get_meal_distribution(identity_id)` | `BillRepositoryImpl.getMealDistribution()` |
| `get_daily_trend(identity_id)` | `BillRepositoryImpl.getDailyTrend()` |
| `get_category_summary(...)` | `BillRepositoryImpl.getStatisticsSummary()` |
| `get_forgot_card_stats(...)` | `BillRepositoryImpl.getForgotCardStats()` |
| `classify_bill(name, target)` | `EpayAdapter.classifyBill(name, target)` |
| `translate_target(target_user)` | `EpayAdapter.translateTarget(target_user)` |
| `get_classification_rules()` | `BillRulesManager.readFile("rules.toml")` |
| `update_database_from_remote()` | `BillRulesManager.downloadAll()` |

## 9. 调试建议

```bash
# 查看本地规则文件
adb shell run-as cn.edu.shmtu.terminal.android cat files/bill/rules.toml

# 查看账单分类落库情况
adb shell run-as cn.edu.shmtu.terminal.android sqlite3 databases/identity_1.sqlite \
    "SELECT type, category, position, room FROM bills ORDER BY id DESC LIMIT 10"
```

如果发现 `category` 全是 null，说明 `BillRulesManager` 在 sync 时未注入到 `RoomBillStore` —— 检查 `SyncAccountBillsUseCase.createStore` 是否正确读取 `epayAdapter.classifier`。
