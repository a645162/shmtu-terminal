# SHMTU Terminal 共享数据库

## 目录结构

```
database/
├── .gitignore
└── bill/
    ├── position.toml    # 对方账户→位置翻译表（TOML）
    ├── type.toml        # 账单分类→类别规则（TOML）
    ├── schedule.toml    # 食堂营业时间表（TOML）
    └── rules.toml       # 合并规则（TOML，含 type / position / schedule）
```

## 数据格式

### position.toml
- `field`: 匹配字段名（`target` = 对方账户）
- `keywords`: `{目标名: {position, room}}`

### type.toml
- `{分类名: {name: [关键词], target: [关键词]}}`
- 分类：deposit/electricity/bath/hot_water/cake/canteen/library/hospital/shop/laundry/network/transport

### schedule.toml
- 食堂营业时段：早餐6:30-8:30 / 午餐10:45-12:30 / 晚餐16:30-18:15 / 夜宵18:15-21:00

### rules.toml
- TOML 格式的合并分类规则（供 Tauri / Android 统一加载）
- 包含 type/position/schedule 三部分

## 账单备注 (Notes)

合并账单表 (`bill_merged`) 支持用户添加字符串备注：
- 前端账单详情弹窗中可编辑备注
- 备注存储在数据库 `notes` 列
- 支持为空（NULL）

## GitHub 云更新

规则文件托管在：`https://github.com/a645162/shmtu-terminal/tree/main/database/bill/`

更新流程：
1. GitHub 上修改 TOML 规则文件
2. 客户端检查版本更新
3. 自动下载新规则到本地 `database/` 目录
4. 备份旧文件（.bak）

## 三端使用

| 端 | 格式 | 加载路径 |
|---|------|---------|
| Rust/Tauri | TOML | `database/bill/rules.toml` |
| Android/Kotlin | TOML | `database/bill/*.toml` / `assets/bill/*.toml` |
