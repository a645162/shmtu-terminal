# 开发变更日志 - 日均消费计算调整

**日期**: 2026-05-25
**版本**: N/A (未发布)
**影响范围**: Android, Tauri (Rust)

## 变更内容

### 问题描述
原日均消费计算方式为 `总消费金额 / 时间范围总天数`，这种方式会将被忽略的"无消费日"计入平均，导致日均数据偏低，无法准确反映实际消费强度。

### 解决方案
新计算方式为 `总消费金额 / 实际有消费的天数`，只计算有实际交易发生的天数。

### 修改文件

#### Android (Kotlin)
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `domain/model/BillStatistics.kt` | 修改 | `BillOverview` 新增 `dailyAverage` 和 `activeDays` 字段 |
| `data/local/db/dao/BillDao.kt` | 新增 | `getActiveDaysInRange()` 查询活跃天数 |
| `data/repository/BillRepositoryImpl.kt` | 修改 | 整合活跃天数计算，更新 `getBillOverview()` |
| `ui/home/HomeScreen.kt` | 修改 | 显示日均消费卡片 |
| `ui/statistics/BillStatisticsScreen.kt` | 修改 | 统计页面显示日均消费 |

#### Tauri/Rust
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/commands/statistics.rs` | 无需修改 | 已在 `get_statistics_summary()` 中使用 `unique_dates` 计算 |

## 计算公式

```
日均消费 = 总消费金额 / 实际有消费的天数
```

其中：
- **总消费金额**: 时间范围内所有状态为"交易成功"的支出金额绝对值之和
- **实际有消费的天数**: 时间范围内至少有1笔交易的不同日期数量（去重）

## 向后兼容性

- Android: `BillOverview` 新增字段有默认值0，UI需适配
- Tauri: API字段已存在，无影响