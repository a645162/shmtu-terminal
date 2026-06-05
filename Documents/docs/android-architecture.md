# Android 端架构

`shmtu-terminal-android` 采用 **MVVM + Clean Architecture + Hilt DI**，与 Tauri 端 Rust 实现的 service 风格截然不同，但端到端行为一致。

## 1. 分层

```
┌─────────────────────────────────────────────────────────┐
│ UI Layer (Compose + Material3)                          │
│   • Screen (Composable)        — 渲染 UI                 │
│   • ViewModel (Hilt + StateFlow) — 状态管理 + 事件分发  │
│   • LocalFeatureStore (CompositionLocal) — 跨 Composable  │
│     共享 FeatureSettingsStore                             │
└────────────────────────┬────────────────────────────────┘
                         │ collect / stateIn
┌────────────────────────┴────────────────────────────────┐
│ Domain Layer                                            │
│   • UseCase (单职责操作)                                │
│   • Repository Interface (抽象)                          │
│   • Model (业务模型)                                    │
│   • 例: SyncAccountBillsUseCase, BillRepository         │
└────────────────────────┬────────────────────────────────┘
                         │ 实现
┌────────────────────────┴────────────────────────────────┐
│ Data Layer                                              │
│   • Repository Implementation                           │
│   • Room Database + DAO                                 │
│   • SharedPreferences / DataStore                        │
│   • Network: OkHttp / cas_lib.EpayAuth                  │
│   • WorkManager (定时任务)                              │
│   • Hilt Module (依赖注入)                              │
└─────────────────────────────────────────────────────────┘
```

## 2. Hilt 模块拓扑

```
@HiltAndroidApp class SHMTUTerminalApp : Application()
   │
   ├── SingletonComponent (App 全局单例)
   │     ├── SHMTUTerminalApp 本身 (有 @Inject 字段)
   │     ├── BillDatabaseManager (Context)
   │     ├── BillRulesManager (Context)  ← @Singleton
   │     ├── FeatureSettingsStore (Context)
   │     ├── SecureStorage
   │     ├── OkHttpClient (lazy)
   │     └── BillDedupeRepository
   │
   ├── ActivityComponent (每个 Activity 一个)
   │     ├── MainActivity
   │     └── StartupLockActivity
   │
   └── ViewModelComponent (每个 Composable 一个)
         ├── HomeViewModel (IdentityRepository, BillRepository)
         ├── BillStatisticsViewModel
         ├── SettingsViewModelWrapper
         ├── PeriodicBillSyncWorker (@HiltWorker)
         └── ... 8 个 settings ViewModel
```

## 3. Room 数据库

- 动态创建: `BillDatabaseManager` 用 `getAccountDatabase(studentId)` / `getIdentityDatabase(identityId)` 懒加载
- 单数据库结构: `BillEntity` (id, accountId, accountLabel, dateStr, timeStr, dateTimeStrFormat, type, transactionNo, targetUser, money, method, status, position, room, notes, category, building)
- Schema 迁移: 当前 version=2, 用 `fallbackToDestructiveMigration(false)` 保护
- 索引: `Index("accountId")`, `Index("dateTimeStrFormat")`, `Index(value = ["accountId", "transactionNo"], unique = true)` — 保证 (account, tx) 唯一

## 4. Compose UI

- Material3 主题 (`ShmtuterminalandroidTheme`)
- 单 Activity (`MainActivity`) + `NavHost` 导航
- 自适应布局: 手机用单列 LazyColumn, 平板用 NavigationRail
- 状态管理: ViewModel + StateFlow + `collectAsState()`

## 5. 关键设计模式

### 单 Activity + NavHost
- `MainActivity` 是唯一 Activity
- 所有跳转通过 `AppNavigation.kt` 的 `NavHost` + `composable(route)`
- 设置页 + StartupLockActivity 是例外（独立 Activity 拦截）

### 双写 Room
- 每条账单写入两个数据库: `account_{studentId}.sqlite` + `identity_{id}.sqlite`
- 账号级去重用账号库, 身份级统计用身份库

### CompositionLocal 共享 Store
- `LocalFeatureStore` 避免每个 SettingsScreen 单独 hiltViewModel()
- Hilt 注入 `FeatureSettingsStore` 在 `SettingsScreen` 顶层, 然后用 `CompositionLocalProvider` 下传

### 包装 cas_lib
- `EpayAdapter` 包装 `EpayAuth` (cas_lib 纯 JVM 类)
- `BillRulesManager` 包装 4 个分类器 + TOML 加载
- `RoomBillStore` 实现 `BillStore` 接口 (cas_lib 定义)

## 6. 与 Tauri 端架构对比

| 维度 | Tauri (Rust) | Android (Kotlin) |
|------|-------------|------------------|
| 异步运行时 | tokio | kotlinx.coroutines |
| 状态共享 | Arc<Mutex<State>> | StateFlow / SharedPreferences |
| 依赖注入 | trait + dyn (手动) | Hilt |
| 数据库 | sea-orm (SQLite) | Room |
| UI | React + Fluent UI | Compose + Material3 |
| 后台任务 | Tauri Service + tokio interval | WorkManager |

## 7. 关键流程的类图

### 同步流程

```
SyncAccountBillsUseCase
  └── EpayAdapter.fetchBillPage()
        └── EpayAuth.getBill()  ← cas_lib
              └── OkHttp HTTP GET
  └── BillParser.parseBillItems()  ← cas_lib
  └── RoomBillStore.merge()
        ├── classifier.classifyKey()  ← cas_lib
        ├── positionTranslator.translate()  ← cas_lib
        └── billDao.insertAll()  ← Room
              └── account + identity 双写
```

### 统计流程

```
BillStatisticsViewModel
  └── billRepository.getCategoryBreakdown()
        └── BillRepositoryImpl.getCategoryBreakdown()
              ├── mergedBills(identityId)  ← 跨 account 库 join
              ├── filter by date range
              ├── groupBy { it.category }  ← 落库时算的 category key
              └── sumOf { abs(money) }
```

## 8. 测试策略

- **cas_lib** 用 JUnit 单元测试 (Java 17)
- **app** 用 Compose UI 测试 (instrumentedTest) + 业务逻辑单元测试
- 集成测试: 真实 CAS 登录 (需要测试账号)

## 9. 已知限制

- **KSP 1.0.21 + Hilt 2.59** 解析新类型时偶发崩溃 —— 已通过 `FeatureSettingsStore` (独立 SharedPreferences) + `Application` 构造绕开
- **fallbackToDestructiveMigration** 在 schema 变更时会清空用户数据, 未来应写正式 Migration
- **去重操作** 写在大表上可能慢, 没加索引 hint
