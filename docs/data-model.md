# 上海海事大学终端应用 — 数据模型文档

> 版本：1.0 | 更新日期：2026-05-22

---

## 一、核心数据实体

### 1.1 身份（Identity）

一个身份代表一个"人"，如本人、家人。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| name | text | NOT NULL | 身份名称（如"张三"） |
| enable | boolean | DEFAULT true | 是否启用 |
| enable_update | boolean | DEFAULT true | 是否允许同步更新 |
| birthday | text | NULLABLE | 生日（可选） |
| default_remember | boolean | DEFAULT false | 是否记住为默认身份 |
| created_at | text | NOT NULL | 创建时间（ISO 8601） |
| updated_at | text | NOT NULL | 更新时间（ISO 8601） |

**数据库文件**：`Data/identity/<id>.sqlite`

### 1.2 账号（Account）

一个账号对应一个学号/校园卡，属于某个身份。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| identity_id | integer | FK → Identity.id | 所属身份 |
| account_name | text | NOT NULL | 账号名称（如"本科校园卡"） |
| account_id | text | NOT NULL, UNIQUE | 学号（12位数字） |
| password | text | NOT NULL | 密码（加密存储） |
| enable | boolean | DEFAULT true | 是否启用 |
| enable_update | boolean | DEFAULT true | 是否允许同步 |
| expire_date | text | DEFAULT '2099-12-31' | 过期日期 |
| last_update_time | text | DEFAULT '' | 最后同步时间 |
| created_at | text | NOT NULL | 创建时间 |
| updated_at | text | NOT NULL | 更新时间 |

**验证规则**：
- account_id 必须为 12 位数字
- password 非空

### 1.3 账单原始记录（BillOriginal）

从 API 获取的原始账单数据，**只读不允许修改**。每个账号有独立的原始数据表。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| date_str | text | NOT NULL | 日期字符串（原始格式，如"2024.03.15"） |
| time_str | text | NOT NULL | 时间字符串（原始格式，如"123000"） |
| time_str_formatted | text | | 格式化时间（"12:30:00"） |
| date_time_formatted | text | | 格式化日期时间（"2024.03.15 12:30:00"） |
| end_date_time_formatted | text | | 合并记录的结束时间 |
| timestamp | integer | | Unix 时间戳（秒） |
| end_timestamp | integer | | 合并记录的结束时间戳 |
| item_type | text | | 交易名称（如"食堂消费"、"微信充值"） |
| number | text | | 交易号 |
| number_list | text | | 交易号列表（JSON数组，合并记录用） |
| target_user | text | | 对方账户/位置 |
| money_str | text | | 金额字符串（原始） |
| money | real | | 金额数值（正=收入，负=支出） |
| method | text | | 支付方式 |
| status_str | text | | 状态字符串 |
| is_combined | boolean | DEFAULT false | 是否为合并记录 |
| account_id | text | NOT NULL | 所属学号 |
| synced_at | text | | 同步时间 |

**数据库文件**：`Data/account/<account_id>.sqlite`（每账号一个独立数据库）

**唯一性约束**：基于 `number_list` 判断（交易号列表相同的记录视为同一条）

### 1.4 账单合并记录（BillMerged）

身份级别的合并账单，由名下所有账号的原始数据自动同步而来，允许手动增删操作。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| date_str | text | NOT NULL | 日期字符串 |
| time_str | text | NOT NULL | 时间字符串 |
| time_str_formatted | text | | 格式化时间 |
| date_time_formatted | text | | 格式化日期时间 |
| end_date_time_formatted | text | | 合并记录的结束时间 |
| timestamp | integer | | Unix 时间戳 |
| end_timestamp | integer | | 合并记录的结束时间戳 |
| item_type | text | | 交易名称 |
| number | text | | 交易号 |
| number_list | text | | 交易号列表（JSON数组） |
| target_user | text | | 对方账户/位置 |
| money_str | text | | 金额字符串 |
| money | real | | 金额数值 |
| method | text | | 支付方式 |
| status_str | text | | 状态字符串 |
| is_combined | boolean | DEFAULT false | 是否为合并记录 |
| source_account_id | text | | 来源学号（自动同步时填充） |
| is_manual | boolean | DEFAULT false | 是否手动添加的记录 |
| synced_at | text | | 同步/添加时间 |

**数据库文件**：`Data/identity/<identity_id>.sqlite`（每身份一个独立数据库）

### 1.5 操作记录（OperationLog）

对身份数据库的手动操作记录，全量更新后清空。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| operation_type | text | NOT NULL | 操作类型：add / delete / merge |
| record_numbers | text | | 涉及的交易号列表（JSON数组） |
| operation_time | text | NOT NULL | 操作时间（ISO 8601） |
| description | text | | 操作描述 |
| account_id | text | | 关联账号 |

### 1.6 会话信息（SessionInfo）

存储账号的登录会话（cookies），用于恢复登录状态。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | integer | PK, AUTO | 主键 |
| account_id | text | NOT NULL, UNIQUE | 学号 |
| cookies | text | NOT NULL | Cookies 数据（加密存储） |
| login_time | text | | 登录时间 |
| expire_time | text | | 预估过期时间 |
| is_valid | boolean | DEFAULT true | 是否仍有效 |

**数据库文件**：`Data/session.sqlite`

---

## 二、配置数据实体

### 2.1 全局配置（app_config.toml）

应用全局配置文件，TOML 格式。

```toml
[security]
enable_startup_protection = false
password_hash = ""           # SHA-256 哈希

[identity]
remember_default = false
default_identity_id = 0

[captcha]
mode = "manual"              # manual / remote_ocr / local_onnx
remote_ocr_host = ""
remote_ocr_port = 0
onnx_model_path = ""         # 空则使用默认路径
ocr_retry_count = 3

[sync]
max_pages = 100
early_stop_threshold = 5
auto_merge_after_sync = true

[data]
data_directory = "Data"
snapshot_keep_count = 10

[classification]
rules_path = ""              # 空则使用默认路径
rules_update_url = ""        # GitHub 更新源

[update]
auto_check = true
check_interval_hours = 24
last_check_time = ""

[ui]
theme = "light"              # light / dark / system
language = "zh-CN"
```

**文件路径**：`Data/app_config.toml`

### 2.2 分类规则（classification_rules.toml）

账单分类规则配置，TOML 格式，支持 GitHub 云更新。

```toml
# 按消费类型分类
[type]

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
name = "蛋糕"
match_field = "target_user"
match_targets = ["北区西点房"]

[type.canteen]
name = "食堂"
match_field = "target_user"
match_targets = ["食堂", "餐厅"]

# 按位置映射
[position]
field = "target_user"

[position.keywords."A食堂1楼大餐厅"]
building = "海馨楼"
room = "海馨第1食堂"

[position.keywords."A食堂2楼大餐厅"]
building = "海馨楼"
room = "海馨第2食堂"

[position.keywords."A食堂2楼小餐厅"]
building = "海馨楼"
room = "海馨第2食堂小厅"

[position.keywords."B食堂1楼"]
building = "海琴楼"
room = "海琴1楼"

[position.keywords."B食堂2楼"]
building = "海琴楼"
room = "海琴2楼"

[position.keywords."C1大餐厅"]
building = "海联楼"
room = "海联1楼"

[position.keywords."C2大餐厅"]
building = "海联楼"
room = "海联2楼"

# 按用餐时段分类
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

**文件路径**：`Data/classification_rules.toml`

---

## 三、数据流说明

### 3.1 整体数据流

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   CAS/ePay   │     │   本地存储    │     │   UI 展示    │
│   远程服务    │     │   SQLite     │     │   界面渲染    │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │  1. HTTP 请求      │  2. 持久化存储      │  3. 数据读取
       │  获取原始数据       │  写入数据库         │  渲染到界面
       ▼                    ▼                    ▼
  ┌─────────────────────────────────────────────────────┐
  │                    应用核心逻辑层                      │
  │                                                     │
  │  CAS认证 → 账单获取 → 解析 → 存储 → 分类 → 统计 → 展示 │
  └─────────────────────────────────────────────────────┘
```

### 3.2 账单数据详细流

```
CAS/ePay 服务器
      │
      │ ① 登录 + 请求账单页面
      ▼
HTML 页面（分页）
      │
      │ ② HTML 解析（BillHtmlParser / parse_bill_page）
      ▼
BillItem / BillItemInfo 列表
      │
      ├──→ ③ 写入账号原始数据表（只读）
      │         Data/account/<account_id>.sqlite
      │         表: bill_original
      │
      │    ④ 新条目追加到身份合并数据表
      │         Data/identity/<identity_id>.sqlite
      │         表: bill_merged
      │
      ▼
  ⑤ UI 读取合并数据表 → 渲染账单列表
      │
      ├──→ ⑥ 分类引擎应用分类规则
      │         classification_rules.toml
      │         → 类型分类、位置映射、时段分类
      │
      ├──→ ⑦ 统计引擎计算汇总
      │         → 日/周/月消费、分类占比、趋势
      │
      └──→ ⑧ 导出引擎生成文件
                → CSV / JSON / 钱迹格式
```

### 3.3 同步数据流

```
用户触发同步
      │
      ▼
获取当前身份下所有启用账号
      │
      ▼ 遍历每个账号
┌─────────────────────────────┐
│ 检查已保存的会话(cookies)     │
│   ├─ 有效 → 复用会话          │
│   └─ 无效/不存在 → CAS登录    │
│         ├─ 获取验证码          │
│         ├─ 识别验证码          │
│         ├─ 提交登录            │
│         ├─ 保存 cookies       │
│         └─ 跟随重定向          │
└─────────────────────────────┘
      │
      ▼
ePay 账单查询（分页）
      │
      ▼ 逐页处理
┌─────────────────────────────┐
│ 解析 HTML → BillItem 列表    │
│   │                          │
│   ├─ 检查交易号是否已存在     │
│   │   (IBillStore.Contains)  │
│   │                          │
│   ├─ 新条目 → 写入原始表      │
│   │   + 追加到合并表          │
│   │                          │
│   └─ 已知条目 → 计数          │
│       达到阈值 → 提前停止      │
└─────────────────────────────┘
      │
      ▼
同步完成 → 更新 UI → 显示结果
```

---

## 四、本地存储策略

### 4.1 目录结构

```
Data/                                # 数据根目录（可配置）
├── app_config.toml                  # 全局配置文件
├── classification_rules.toml        # 分类规则文件
├── shmtu.terminal.sqlite            # 全局数据库（身份、账号元数据）
├── session.sqlite                   # 会话数据库（cookies）
├── identity/                        # 身份数据库目录
│   ├── 1.sqlite                     # 身份1的合并数据库
│   ├── 2.sqlite                     # 身份2的合并数据库
│   └── ...
├── account/                         # 账号数据库目录
│   ├── 202012345678.sqlite          # 学号1的原始账单数据库
│   ├── 202412345678.sqlite          # 学号2的原始账单数据库
│   └── ...
├── snapshot/                        # 快照目录
│   ├── 2024-03-15_14-30-00.zip      # 快照文件
│   └── ...
├── models/                          # ONNX 模型目录
│   ├── resnet18_equal_symbol_latest.onnx
│   ├── resnet18_operator_latest.onnx
│   └── resnet34_digit_latest.onnx
└── export/                          # 导出文件默认目录
    └── ...
```

### 4.2 数据库加密策略

| 数据库 | 加密方式 | 说明 |
|--------|----------|------|
| shmtu.terminal.sqlite | SQLite 密码加密 | 存储身份和账号元数据，含加密密码 |
| session.sqlite | SQLite 密码加密 | 存储 cookies 等敏感会话信息 |
| identity/*.sqlite | SQLite 密码加密 | 身份合并数据，含消费信息 |
| account/*.sqlite | SQLite 密码加密 | 账号原始账单数据 |

**加密实现**：
- Avalonia：使用 SqlSugar 的 SQLite Password 特性（基于 `Microsoft.Data.Sqlite`）
- Tauri：使用 `sqlcipher` 或 Rust 的 `rusqlite` + 加密扩展
- 所有数据库共用一个密码（启动保护密码，未设置则使用设备唯一标识派生密钥）

### 4.3 数据库表与文件映射

| 数据 | 数据库文件 | 主要表 |
|------|-----------|--------|
| 身份列表 | shmtu.terminal.sqlite | identity |
| 账号列表 | shmtu.terminal.sqlite | account |
| 全局配置 | app_config.toml | — |
| 账号原始账单 | account/\<id\>.sqlite | bill_original |
| 身份合并账单 | identity/\<id\>.sqlite | bill_merged |
| 身份操作记录 | identity/\<id\>.sqlite | operation_log |
| 会话信息 | session.sqlite | session_info |

### 4.4 数据备份与恢复

**快照策略**：
- 快照内容：整个 `Data/` 目录（排除 models 和 export）
- 快照格式：ZIP 压缩包，文件名含时间戳
- 自动保留：默认保留最近 10 个快照，超出自动删除最旧
- 手动创建：用户可在数据管理窗口手动创建快照
- 恢复方式：选择快照 → 解压覆盖当前 Data 目录 → 重启应用

**导入导出策略**：
- 导出格式：JSON（完整数据）、CSV（表格数据）、钱迹格式（记账导入）
- 导入格式：JSON（与导出格式一致）
- 导入时支持选择性导入（指定时间范围）

---

## 五、数据操作规则

### 5.1 原始数据表规则

1. **只读**：原始数据表只能通过同步写入，不允许手动修改或删除
2. **去重**：基于交易号列表判断是否已存在
3. **合并**：同一时段多笔交易可合并为一条记录（BillItem.Merge）
4. **完整**：保留原始字段，不做任何转换或丢失

### 5.2 合并数据表规则

1. **自动同步**：账号原始数据的新条目自动追加到身份合并表
2. **允许手动操作**：
   - 手动添加记录（标记 `is_manual = true`）
   - 手动删除记录（记录操作日志）
3. **操作记录**：所有手动操作写入 `operation_log` 表
4. **全量更新清空日志**：执行全量更新后，操作记录全部清空
5. **手动删除的记录在全量更新后会重新出现**（因原始数据不变）

### 5.3 同步策略

| 同步类型 | 触发方式 | 数据范围 | 日志处理 |
|---------|---------|---------|---------|
| 增量同步（账号级） | 手动/自动 | 仅新增条目 | 不影响日志 |
| 增量同步（身份级） | 手动/自动 | 所有启用账号新增 | 不影响日志 |
| 全量更新（账号级） | 手动 | 该账号所有页 | 清空该账号相关日志 |
| 全量更新（身份级） | 手动 | 所有启用账号所有页 | 清空该身份所有日志 |

### 5.4 Cookies 存储策略

1. 登录成功后保存 cookies 到 `session.sqlite`
2. 下次同步时先尝试恢复 cookies：
   - 发送测试请求（probe_login）
   - 200 = 有效，复用
   - 302 = 过期，重新登录
3. Cookies 加密存储
4. 预估过期时间（CAS 通常 30 分钟无活动过期）

---

## 六、分类引擎说明

### 6.1 分类流程

```
输入：BillItem
      │
      ▼
① 类型分类
  遍历 type 规则：
    匹配 item_type 字段 → 匹配 match_names
    匹配 target_user 字段 → 匹配 match_targets
  输出：type_label（充值/电费/洗澡/热水/蛋糕/食堂/其他）
      │
      ▼
② 位置映射
  遍历 position.keywords：
    精确匹配 target_user 字段
  输出：building + room（海馨楼/海琴楼/海联楼 + 具体窗口）
      │
      ▼
③ 时段分类
  读取当前日期对应的 schedule：
    根据 timestamp 判断时间段
  输出：meal_type（早餐/午餐/晚餐/夜宵/非用餐时段）
      │
      ▼
输出：分类结果
  {
    type: "食堂",
    building: "海馨楼",
    room: "海馨第1食堂",
    meal: "午餐"
  }
```

### 6.2 分类规则优先级

1. 类型分类按规则定义顺序匹配，首次匹配即返回
2. 位置映射为精确匹配，无匹配则保留原始 target_user
3. 时段分类按 schedule 的时间表匹配
4. 所有分类结果均为可选，任一步骤可能无匹配

### 6.3 规则更新

- 本地文件：`Data/classification_rules.toml`
- 云更新源：GitHub 仓库 URL（在设置中配置）
- 更新方式：HTTP GET 下载 → 覆盖本地文件
- 备份：更新前自动备份当前规则文件

---

## 七、导出格式规范

### 7.1 CSV 格式

```csv
日期时间,交易名称,交易号,对方账户,金额,支付方式,状态
2024.03.15 12:30:00,食堂消费,123456789,海馨1楼,-12.50,校园卡,交易成功
2024.03.15 10:00:00,微信充值,987654321,—,+200.00,微信,交易成功
```

- 编码：UTF-8 with BOM（Excel 兼容）
- 表头：中文字段名
- 日期时间格式：`yyyy.MM.dd HH:mm:ss`

### 7.2 JSON 格式

```json
{
  "export_time": "2024-03-15T15:30:00",
  "identity_name": "张三",
  "source": "merged",
  "bills": [
    {
      "date_time_formatted": "2024.03.15 12:30:00",
      "item_type": "食堂消费",
      "number": "123456789",
      "number_list": ["123456789"],
      "target_user": "海馨1楼",
      "money_str": "-12.50",
      "money": -12.50,
      "method": "校园卡",
      "status_str": "交易成功",
      "is_combined": false,
      "classification": {
        "type": "食堂",
        "building": "海馨楼",
        "room": "海馨第1食堂",
        "meal": "午餐"
      }
    }
  ]
}
```

### 7.3 钱迹格式

钱迹 App 导入格式，参考钱迹官方规范：

```json
[
  {
    "type": 1,
    "money": 12.50,
    "category": "餐饮",
    "account": "校园卡",
    "remark": "海馨第1食堂-午餐",
    "time": 1710486600
  }
]
```

- type：0=支出，1=收入
- money：正数金额
- category：映射为钱迹分类体系
- time：Unix 时间戳

---

## 八、枚举类型定义

### BillType（账单类型）

| 值 | 说明 | ePay tab_no |
|----|------|-------------|
| All | 全部 | 1 |
| Success | 交易成功 | 2 |
| NotPaid | 待支付 | 3 |
| Failure | 交易失败 | 4 |

> **注意**：两端库的 tab_no 映射存在差异，以上为统一后的映射，应用层需统一处理。

### BillItemStatus（账单状态）

| 值 | 说明 | 原始值 |
|----|------|--------|
| All | 全部 | #all |
| WaitFor | 待处理 | #waitfor |
| Success | 成功 | 交易成功 |
| Failure | 失败 | #fail |

### CaptchaMode（验证码识别模式）

| 值 | 说明 |
|----|------|
| Manual | 手动输入 |
| RemoteOcr | 远程 OCR 服务器 |
| LocalOnnx | 本地 ONNX 模型 |

### CaptchaAnswerKind（验证码答案类型）

| 值 | 说明 |
|----|------|
| Answer | 直接答案 |
| Expression | 数学表达式（需计算） |

### OperationType（操作类型）

| 值 | 说明 |
|----|------|
| add | 手动添加 |
| delete | 手动删除 |
| merge | 合并操作 |

---

## 九、.gitignore 更新建议

在 `Data/` 目录下添加 `.gitignore`：

```gitignore
# 数据库文件
*.sqlite

# 配置文件（含敏感信息）
app_config.toml

# 会话数据
session.sqlite

# 快照
snapshot/

# ONNX 模型文件
models/

# 导出文件
export/

# 保留目录结构
!.gitkeep
```

各子项目 `.gitignore` 补充：

```gitignore
# 用户数据目录
Data/
```
