# TOML 数据库格式规范

`shmtu-terminal-tauri/Data/database/bill/` 目录下 4 个 TOML 文件 + Android 端 `app/src/main/assets/bill/` 是**数据源真值**。本节规定字段格式与加载优先级。

## 1. 文件清单

| 文件 | 段 | 作用 |
|------|----|------|
| `type.toml` | `[type.X]` | 消费类型识别（13 条规则） |
| `position.toml` | `[position.keywords.X]` | 对方账户 → (楼栋, 房间) 翻译（19 条） |
| `schedule.toml` | `[[schedule]]` + `[schedule.timetable.X]` | 用餐时段（4 段 + valid_date 范围） |
| `rules.toml` | 三段合并 | 加载入口（Tauri 端 `db_file_manager.read_file("rules.toml")` 优先用此） |

## 2. type.toml 完整示例

```toml
# 消费类型识别规则 — 根据 item_type 或 target_user 中的关键词匹配分类
# 字段说明:
#   match_field = "item_type"   → 按 match_names 数组匹配 bill.item_type(子串包含)
#   match_field = "target_user" → 按 match_targets 数组匹配 bill.target_user(子串包含)
# 命中顺序: HashMap 迭代顺序,首次命中即返回(其它分类不再评估)

[type.deposit]
name = "充值"
match_field = "item_type"
match_names = ["中行云充值", "微信充值"]

[type.electricity]
name = "电费"
match_field = "item_type"
match_names = ["电费缴费"]

[type.bath]
name = "洗澡"
match_field = "target_user"
match_targets = ["淋浴", "热水"]

[type.hot_water]
name = "热水"
match_field = "item_type"
match_names = ["水控转账"]

[type.cake]
name = "西点"
match_field = "target_user"
match_targets = ["北区西点房"]

[type.canteen]
name = "食堂"
match_field = "target_user"
match_targets = ["食堂", "餐厅"]

[type.library]
name = "图书馆"
match_field = "target_user"
match_targets = ["图书馆"]

[type.hospital]
name = "校医院"
match_field = "target_user"
match_targets = ["校医院"]

[type.shop]
name = "超市"
match_field = "target_user"
match_targets = ["超市", "教育超市"]

[type.laundry]
name = "洗衣"
match_field = "target_user"
match_targets = ["洗衣"]

[type.network]
name = "网络"
match_field = "item_type"
match_names = ["网络缴费", "网费"]

[type.transport]
name = "交通"
match_field = "target_user"
match_targets = ["公交", "地铁", "交通"]
```

**关键约束**：
- `match_field` 是 Rust 端 `from_toml` 的"互斥语义"——`item_type` 走 `match_names`，`target_user` 走 `match_targets`，**两组不越界**。Android 端 `BillClassifier.fromToml()` 严格遵循。
- 命中顺序: 按 HashMap 迭代顺序（与文件 key 顺序一致，因为 Tauri 用 `serde` 解析，Android 用 `LinkedHashMap`）
- 字符串子串匹配（`contains`），非精确匹配

## 3. position.toml 完整示例

```toml
# 位置翻译表 — 对方账户 → (楼栋, 房间)

[position]
field = "target_user"

[position.keywords."A食堂1楼大餐厅"]
building = "海馨楼"
room = "海馨第1食堂"

[position.keywords."A食堂1楼小餐厅"]
building = "海馨楼"
room = "海馨第3食堂"

[position.keywords."A食堂1楼清真餐厅"]
building = "海馨楼"
room = "海馨第5食堂(清真)"

[position.keywords."A食堂2楼大餐厅"]
building = "海馨楼"
room = "海馨第2食堂"

[position.keywords."A食堂2楼小餐厅"]
building = "海馨楼"
room = "海馨第4食堂"

[position.keywords."B食堂1楼"]
building = "海琴楼"
room = "海琴1楼"

[position.keywords."B食堂2楼"]
building = "海琴楼"
room = "海琴2楼"

[position.keywords."C1大餐厅"]
building = "海联楼"
room = "海联1楼"

[position.keywords."C食堂2楼"]
building = "海联楼"
room = "海联2楼"

[position.keywords."海馨第一食堂"]
building = "海馨楼"
room = "海馨第1食堂"

[position.keywords."海馨第二食堂"]
building = "海馨楼"
room = "海馨第2食堂"

[position.keywords."海馨第三食堂"]
building = "海馨楼"
room = "海馨第3食堂"

[position.keywords."海馨第四食堂"]
building = "海馨楼"
room = "海馨第4食堂"

[position.keywords."淋浴"]
building = "公共浴室"
room = "浴室"

[position.keywords."热水"]
building = "公共浴室"
room = "浴室"

[position.keywords."北区西点房"]
building = "海馨楼"
room = "西点房"

[position.keywords."图书馆"]
building = "图书馆"
room = "图书馆"

[position.keywords."校医院"]
building = "校医院"
room = "校医院"

[position.keywords."教育超市"]
building = "校园商业"
room = "教育超市"
```

**关键约束**：
- 表格头 key 含点号时必须用 `"a.b.c"` 引用（如 `[position.keywords."A食堂1楼大餐厅"]`）
- 匹配规则: 先 `trim` 后精确 key 匹配，失败后扫描所有 key 找第一个"被 target_user 包含"

## 4. schedule.toml 完整示例

```toml
# 食堂营业时间表 — 同一格式可定义多个时段规则(按日期范围生效)
# valid_date.end_date == "now" 表示无上限
# 时段匹配:start_time ≤ time < end_time(左闭右开)

[[schedule]]
[schedule.valid_date]
start_date = "2019.9.1"
end_date = "now"

[schedule.timetable.breakfast]
name = "早餐"
start_time = "6:30"
end_time = "8:30"

[schedule.timetable.lunch]
name = "午餐"
start_time = "10:45"
end_time = "12:30"

[schedule.timetable.dinner]
name = "晚餐"
start_time = "16:30"
end_time = "18:15"

[schedule.timetable.midnight_snack]
name = "夜宵"
start_time = "18:15"
end_time = "21:00"
```

**关键约束**：
- 日期格式: `yyyy.M.d`（如 `2019.9.1`）
- 时间格式: `H:mm`（如 `6:30`）
- `end_date = "now"` 是特殊值，Android 端 `MealClassifier` 解析后视为"无上限"
- 多 `[[schedule]]` 段按数组顺序遍历

## 5. rules.toml（合并文件）

把上面 3 段拼在一起就是 `rules.toml`，供 `db_file_manager.read_file("rules.toml")` 单次加载。Android 端 `BillClassifier.fromRulesToml` 会自动按段拆分：type 走分类器，position 走翻译器，schedule 走时段分类器。

## 6. GitHub 加载路径

Tauri Rust 端：
- `GITHUB_RAW_BASE = "https://raw.githubusercontent.com/a645162/shmtu-terminal/main/database/bill"`
- 文件: `{rules,type,position,schedule}.toml`

Android 端 (BillRulesManager)：
- 同一 URL base
- 文件: 同一 4 个
- 本地缓存: `context.filesDir/bill/`
- 写盘前备份: `<name>.bak`

## 7. 加载顺序（Android 端）

```
启动 → ensureLocalFiles()
   ├── 查 filesDir/bill/{rules,type,position,schedule}.toml 是否存在且非空
   │   ├── 是 → 跳过
   │   └── 否 → 从 GitHub 下载到 filesDir/bill/
   └── 失败 → 由 EpayAdapter / BillRepositoryImpl 懒加载时回退到 assets/bill/

运行时 readFile(name):
   1. filesDir/bill/<name> 存在 → 读本地缓存
   2. 否则 → 读 assets/bill/<name> 出厂默认
```

## 8. 端到端测试示例

新增一条 type 规则:

```toml
# type.toml 新增段落
[type.coffee]
name = "咖啡"
match_field = "target_user"
match_targets = ["瑞幸", "星巴克", "Manner"]
```

`BillClassifier` 自动识别:
- `classify("消费", "瑞幸咖啡(海馨店)")` → `BillCategory.OTHER` ← 注意: 因为 key 不在 enum 中
- 需要同步在 `BillClassifier.kt` 内 `enum class BillCategory` 加 `COFFEE` 枚举值 + `displayName` / `emoji` 映射

**所以 type.toml 加新规则需要 KOTLIN 端同步加枚举值**。Tauri 端是用 `format!("{:?}", category)` 输出 Debug 名，无需改 Rust 代码——**两个端有差异**。

## 9. 编辑器

推荐用 VSCode + [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml) 扩展，可获得语法高亮、schema 校验、inline hint。
