# 账单分类器 (Classifier)

`cn.edu.shmtu.cas.classifier` 包下提供 4 个核心类，把"对方账户 + 消费类型"字符串映射到有意义的分类标签、楼栋/房间、用餐时段。

## 模块概览

| 类 | 作用 | 数据源 |
|------|------|------|
| `TomlLightweight` | 极简 TOML 解析器（无第三方依赖） | - |
| `BillClassifier` | 类型分类器（充值/电费/食堂/洗澡…） | `type.toml` |
| `PositionTranslator` | 位置翻译器（"A食堂1楼大餐厅" → "海馨楼 / 海馨第1食堂"） | `position.toml` |
| `MealClassifier` | 用餐时段分类器（早/午/晚/夜宵） | `schedule.toml` |

## 1. TomlLightweight

`object TomlLightweight` 提供 `fun parse(text: String): Map<String, Any?>`，支持以下 TOML 子集（与 Tauri `Data/database/bill/*.toml` 完全兼容）：

```toml
# 表格头（嵌套用点号）
[type.deposit]
name = "充值"
match_field = "item_type"          # 字符串字面量
match_names = ["中行云充值"]         # 数组字面量
match_targets = []                  # 空数组

# 数组表格头
[[schedule]]
[schedule.valid_date]
start_date = "2019.9.1"
end_date = "now"                    # "now" 特殊值

[schedule.timetable.breakfast]
name = "早餐"
start_time = "6:30"
end_time = "8:30"
```

支持的语法：
- 注释 `# ...` （在字符串外）
- 字符串字面量 `"..."` / `'...'` （支持 `\"` / `\\` 转义）
- 数组 `[a, b, c]`（嵌套数组在解析后以 String 形式返回）
- 布尔字面量 `true` / `false`（以 String "true"/"false" 返回）
- 数字字面量 / 时间字符串（以 String 原样返回）
- 表格头 `[a.b]`（点号路径）
- 数组表格头 `[[a]]`
- 嵌套 key 段 `"with.dots"`

**不依赖任何第三方库**，自实现 200+ 行 Kotlin，可作为 Android `assets/` 资源或服务端规则文件加载。

## 2. BillClassifier

### 加载方式

```kotlin
// 方式 1: 单独 type.toml
val toml = assets.open("bill/type.toml").bufferedReader().readText()
val classifier = BillClassifier.fromToml(toml)

// 方式 2: 合并 rules.toml (含 type + position + schedule 三段)
val rules = assets.open("bill/rules.toml").bufferedReader().readText()
val classifier = BillClassifier.fromRulesToml(rules)
```

### TOML 格式

```toml
[type.deposit]
name = "充值"
match_field = "item_type"        # "item_type" | "target_user"
match_names = ["中行云充值", "微信充值"]

[type.canteen]
name = "食堂"
match_field = "target_user"
match_targets = ["食堂", "餐厅"]
```

`match_field` 是 Rust 端的"互斥语义"——`item_type` 走 `match_names`，`target_user` 走 `match_targets`，两组**互不越界**。

### 分类方法

```kotlin
// 拿枚举 (用于 in-memory 展示)
val cat: BillCategory = classifier.classify(itemType = "中行云充值", targetUser = "A食堂")

// 拿内部 key (用于 SQL group by)
val key: String = classifier.classifyKey(itemType = "中行云充值", targetUser = "A食堂")
// 返回: "deposit"

// 拿显示名 (中文)
val displayName: String = BillCategory.DEPOSIT.displayName  // "充值"

// 拿 emoji
val emoji: String = BillCategory.DEPOSIT.emoji              // "💰"
```

### 13 个内置分类

| Key | 中文 | emoji | 默认 match_field |
|-----|------|-------|------------------|
| `deposit` | 充值 | 💰 | item_type |
| `electricity` | 电费 | ⚡ | item_type |
| `bath` | 洗澡 | 🚿 | target_user |
| `hot_water` | 热水 | ♨️ | item_type |
| `cake` | 西点 | 🍰 | target_user |
| `canteen` | 食堂 | 🍚 | target_user |
| `library` | 图书馆 | 📚 | target_user |
| `hospital` | 校医院 | 🏥 | target_user |
| `shop` | 超市 | 🛒 | target_user |
| `laundry` | 洗衣 | 👕 | target_user |
| `network` | 网络 | 🌐 | item_type |
| `transport` | 交通 | 🚌 | target_user |
| `other` | 其他 | 💳 | (兜底) |

## 3. PositionTranslator

```kotlin
val translator = PositionTranslator.fromToml(positionToml)

// 精确 + 模糊匹配
val info = translator.translate("A食堂1楼大餐厅")
// PositionInfo(position="海馨楼", room="海馨第1食堂")

val noMatch = translator.translate("未知地点")  // null
```

匹配规则（Tauri 端 `translate` 一致）：
1. 先 `trim` 后做精确 key 匹配
2. 失败后扫描所有 key, 找第一个"被 target_user 包含"的

## 4. MealClassifier

```kotlin
val classifier = MealClassifier.fromToml(scheduleToml)

// 给一个 epoch 秒, 返回 "早餐" / "午餐" / "晚餐" / "夜宵" / null
val meal: String? = classifier.classify(timestamp = 1710475200)
```

匹配规则：
1. 遍历 `[[schedule]]` 段, 选取日期落在 `valid_date` 范围
2. `valid_date.end_date == "now"` 视为无上限
3. 在选中段内按 `breakfast → lunch → dinner → midnight_snack` 顺序检查
4. 匹配规则: `start_time ≤ time < end_time`（左闭右开）

## 5. 加载优先级（Android 端）

`BillRulesManager` 负责加载顺序：
1. 启动时 `ensureLocalFiles()` —— 本地 `filesDir/bill/` 缺失则从 GitHub 下载
2. 运行时读取优先：`filesDir/bill/{rules,type,position,schedule}.toml` 优先，缺失回退到 `assets/bill/*.toml`
3. 失败兜底：使用 `MealClassifier.defaultRules()`（与 Tauri 默认值一致）

## 6. 端到端示例

```kotlin
// 1. 加载所有规则
val rulesToml = billRulesManager.readFile("rules.toml")
val classifier = BillClassifier.fromRulesToml(rulesToml)
val translator = PositionTranslator.fromRulesToml(rulesToml)
val mealClassifier = MealClassifier.fromRulesToml(rulesToml)

// 2. 解析一条账单
val bill = BillItem(...)
val category = classifier.classify(bill.billType, bill.targetUser)  // BillCategory
val categoryKey = classifier.classifyKey(bill.billType, bill.targetUser)  // "deposit"
val pos = translator.translate(bill.targetUser)  // PositionInfo?
val meal = mealClassifier.classify(bill.timestamp)  // "午餐"

// 3. 落库
BillEntity(
    ...,
    type = bill.billType,
    category = categoryKey,        // 落分类
    position = pos?.position,
    room = pos?.room,
    building = pos?.position,
)

// 4. 统计 group by
val stats = bills.groupBy { it.category ?: "other" }
    .mapValues { (_, items) -> items.sumOf { abs(it.money.toDouble()) } }
```

## 7. 与 Tauri Rust 端对齐

| 维度 | Tauri | Android (cas_lib) |
|------|-------|-------------------|
| TOML 解析 | `toml` crate | 自实现 `TomlLightweight` |
| type.toml 字段 | `match_field` + `match_names` + `match_targets` | **完全对齐** |
| 分类方法 | `BillClassifier::classify(name, target)` | `classify(itemType, targetUser)` |
| 位置方法 | `PositionTranslator::translate` | `PositionTranslator.translate` |
| 时段方法 | `BillClassifier::classify_meal` | `MealClassifier.classify(timestamp)` |
| emoji | `BillCategory::emoji` | `BillCategory.emoji` |
| display_name | `BillCategory::display_name` | `BillCategory.displayName` |
