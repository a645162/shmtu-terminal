# SHMTU Terminal 共享数据库

## 目录结构

```
database/
├── .gitignore
└── bill/
    ├── position.json    # 对方账户→位置翻译表（JSON）
    ├── type.json        # 账单分类→类别规则（JSON）
    ├── schedule.json    # 食堂营业时间表（JSON）
    └── rules.toml       # 统一分类规则（TOML，Tauri用）
```

## 数据格式

### position.json
- `field`: 匹配字段名（`target` = 对方账户）
- `keywords`: `{目标名: {position, room}}`

### type.json
- `{分类名: {name: [关键词], target: [关键词]}}`
- 分类：deposit/electricity/bath/hot_water/cake/canteen/library/hospital/shop/laundry/network/transport

### schedule.json
- 食堂营业时段：早餐6:30-8:30 / 午餐10:45-12:30 / 晚餐16:30-18:15 / 夜宵18:15-21:00

### rules.toml
- TOML格式的统一分类规则（供Tauri classification模块使用）
- 包含 type/position/schedule 三部分

## 账单备注 (Notes)

合并账单表 (`bill_merged`) 支持用户添加字符串备注：
- 前端账单详情弹窗中可编辑备注
- 备注存储在数据库 `notes` 列
- 支持为空（NULL）

## GitHub 云更新

规则文件托管在：`https://github.com/a645162/shmtu-terminal/tree/main/database/bill/`

更新流程：
1. GitHub上修改 JSON/TOML 规则文件
2. 客户端检查版本更新
3. 自动下载新规则到本地 `database/` 目录
4. 备份旧文件（.bak）

## 三端使用

| 端 | 格式 | 加载路径 |
|---|------|---------|
| Rust/Tauri | TOML | `database/bill/rules.toml` |
| C#/Avalonia | JSON | `database/bill/position.json` + `type.json` |
| Android/Kotlin | JSON | assets 或本地下载 |
