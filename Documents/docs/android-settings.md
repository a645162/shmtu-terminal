# Android 多级设置页结构与 Tauri 映射表

`SettingsScreen` 是 Android 端的多级设置入口, 对齐 Tauri `SettingsDialog` 的全部 10 个 Tab。

## 1. 多级布局（自适应手机/平板）

| 屏幕宽度 | 布局 |
|---------|------|
| `< 600dp`（手机） | 单列 LazyColumn, 点击 → 弹 Dialog 二级页 |
| `>= 600dp`（平板） | 左侧 NavigationRail 列出 10 个分组, 右侧 inline detail |

由 `isWide = configuration.screenWidthDp >= 600` 自动切换。

## 2. 10 个分组（与 Tauri `SettingsDialog.tsx` 一一对应）

| # | 标题 | Tauri Tab | Android 入口 | 关键字段 |
|---|------|---------|-------------|----------|
| 1 | 界面 | `ui` | `AppearanceSettingsScreen` | `themeMode` + `decimalPlaces` |
| 2 | 首页图表 | `home` | `HomeChartSettingsScreen` | `homeTrendRange` + `homeCategoryRange` |
| 3 | 验证码 | `captcha` | `OcrSettingsScreen` (沿用旧) | `captchaMode` + `ocrRetryCount` |
| 4 | 同步 | `sync` | `SyncSettingsScreen` | `syncMaxPages` + `earlyStop` + `skipGrad` + `autoMerge` + `autoSyncEnabled` + `interval` + `range` |
| 5 | 数据 | `data` | `DataSettingsScreen` | (去重按钮, 调 `BillDedupeRepository`) |
| 6 | 分类规则 | `classification` | `ClassificationSettingsScreen` | (立即同步, 调 `BillRulesManager.downloadAll()`) |
| 7 | 安全 | `security` | `SecuritySettingsScreen` + `StartupLockActivity` | `enableStartupProtection` + `startupPasswordHash` (SHA-256) |
| 8 | 更新 | `update` | `UpdateSettingsScreen` | `autoCheckUpdate` + `checkIntervalHours` + 跳浏览器 |
| 9 | 调试 | `debug` | `DebugSettingsScreen` | (错误日志写入 `filesDir/frontend_errors.log`) |
| 10 | 关于 | (隐含) | `AboutScreen` (沿用旧) | - |

## 3. 数据流

`FeatureSettingsStore`（Hilt @Singleton, 独立 SharedPreferences `feature_settings`）提供所有字段:

```kotlin
@Singleton
class FeatureSettingsStore @Inject constructor(@ApplicationContext context: Context) {
    val themeMode: StateFlow<String>
    val decimalPlaces: StateFlow<Int>
    val homeTrendRange: StateFlow<String>
    val homeCategoryRange: StateFlow<String>
    val syncMaxPages: StateFlow<Int>
    val syncEarlyStop: StateFlow<Int>
    val syncSkipGraduated: StateFlow<Boolean>
    val syncAutoMerge: StateFlow<Boolean>
    val autoSyncEnabled: StateFlow<Boolean>
    val autoSyncInterval: StateFlow<Int>
    val autoSyncRange: StateFlow<String>
    val enableStartupProtection: StateFlow<Boolean>
    val startupPasswordHash: StateFlow<String?>
    val autoCheckUpdate: StateFlow<Boolean>
    val checkIntervalHours: StateFlow<Int>
    // ... 共 20+ 字段
}
```

**为什么独立于 `SettingsDataStore`?** KSP 1.0.21 + Hilt 2.59 解析 `SettingsDataStore` 时, 加任何新字段都会触发 KSP 内部 bug。`FeatureSettingsStore` 是**独立**的 Store, 避开 KSP bug。

## 4. 跨包共享方案

| 场景 | 方案 |
|------|------|
| SettingsScreen 直接读字段 | `LocalFeatureStore.current` (Composable) |
| PeriodicBillSyncWorker 读字段 | **InputData 传值**, Worker 不直接引用 store |
| HomeViewModel 读字段 | `Application` 构造 + SharedPreferences 直读 |
| DataSettingsScreen 去重 | Hilt 注入 `BillDedupeRepository` |

## 5. 接线关系

```
                                MainActivity
                                     │
                                     ↓
                            AppNavigation (Compose NavHost)
                                     │
                                     ↓
                                SettingsScreen
                                       │ hiltViewModel()
                                       ↓
                          SettingsViewModelWrapper
                                       │
                                       ↓
                          CompositionLocalProvider
                          (LocalFeatureStore provides ...)
                                       │
                            ┌──────────┴──────────┐
                            ↓                     ↓
                  AppearanceSettingsScreen   SyncSettingsScreen
                                                ...
                                                ↓
                                      DataSettingsScreen
                                                ↓
                                      BillDedupeRepository
```

## 6. 启动密码

`StartupLockActivity` 在用户启用"启动保护"时拦截:

```
[图标] → StartupLockActivity
            ↓
        读 feature_settings SharedPreferences
            ↓
   ┌────────┴────────┐
   │ enabled &&     │ 是 → 显示密码输入
   │ hash 非空 ?    │
   └────────┬────────┘
            ↓
         否 → finish() + startActivity(MainActivity)
```

Manifest 注册 `android:theme="@android:style/Theme.Translucent.NoTitleBar"` 保持透明。

## 7. 与 Tauri `SettingsDialog` 的差异

| 维度 | Tauri | Android |
|------|-------|---------|
| 形态 | 模态 Dialog (700px 宽) | 多级 (NavigationRail + detail) |
| 适配 | 单一布局 | 手机/平板自适应 |
| 启动密码 | `crypto::CryptoService` | `SHA256` 哈希直接对比 |
| 自动检查更新 | `tauri-plugin-updater` | 跳浏览器到 release 页面 |
| 去重 | Rust SQL + 命令 | Room SQL (`BillDao.dedupeByTransactionNo`) |

## 8. SettingsViewModelWrapper

```kotlin
@HiltViewModel
class SettingsViewModelWrapper @Inject constructor(
    val featureStore: FeatureSettingsStore,
    val rulesManager: BillRulesManager,
    val dedupeRepository: BillDedupeRepository
) : ViewModel()
```

`AppNavigation` 在 `composable(SETTINGS.route)` 内 `hiltViewModel()` 拿到 wrapper, 传给 `SettingsScreen`。

## 9. 后续改进

- [ ] Hilt/KSP bug 解决后, 移除 `FeatureSettingsStore`, 改回 `SettingsDataStore` 扩展
- [ ] 把 `SettingsViewModelWrapper` 合并到 `SettingsViewModel`
- [ ] GitHub release 检查用 OkHttp + JSON 解析 (而不只是跳浏览器)
