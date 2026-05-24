# 账单统计模块详细设计

**版本**: 1.0
**日期**: 2026-05-25
**模块**: 账单统计 (Bill Statistics)

---

## 1. 概述

账单统计模块为用户提供消费数据的全面分析，包括支出趋势、分类占比、消费排行等统计功能。

---

## 2. 核心数据模型

### 2.1 StatisticsSummary (总览)

| 字段 | 类型 | 说明 |
|------|------|------|
| total_expense | f64 | 时间范围内总支出 |
| total_income | f64 | 时间范围内总收入 |
| net_expense | f64 | 净支出 (收入-支出) |
| daily_average | f64 | **日均消费** |
| expense_count | u32 | 支出笔数 |
| income_count | u32 | 收入笔数 |

### 2.2 DailyTrendItem (每日趋势)

| 字段 | 类型 | 说明 |
|------|------|------|
| date | String | 日期 (yyyy-MM-dd) |
| expense | f64 | 当日支出 |
| income | f64 | 当日收入 |

### 2.3 CategoryItem (分类占比)

| 字段 | 类型 | 说明 |
|------|------|------|
| name | String | 分类名称 |
| value | f64 | 分类总金额 |
| count | u32 | 交易笔数 |
| color | String | 图表颜色 (hex) |

### 2.4 MealDistItem (用餐分布)

| 字段 | 类型 | 说明 |
|------|------|------|
| name | String | 用餐时段 (早餐/午餐/晚餐/非用餐) |
| count | u32 | 交易笔数 |
| amount | f64 | 总金额 |

### 2.5 ConsumptionBucketItem (消费区间分布)

| 字段 | 类型 | 说明 |
|------|------|------|
| range | String | 金额区间 (<10元/10-20元/20-50元/50-100元/>100元) |
| count | u32 | 交易笔数 |
| amount | f64 | 总金额 |

### 2.6 MerchantRankingItem (商户排行)

| 字段 | 类型 | 说明 |
|------|------|------|
| merchant | String | 商户名称 (目标用户) |
| count | u32 | 交易笔数 |
| amount | f64 | 总金额 |

### 2.7 CategorySummary (分类详情)

| 字段 | 类型 | 说明 |
|------|------|------|
| category | String | 分类名称 |
| total_amount | f64 | 分类总金额 |
| count | u32 | 交易笔数 |
| daily_average | f64 | 该分类日均消费 |
| avg_per_transaction | f64 | 单笔平均金额 |

---

## 3. 计算方式详解

### 3.1 日均消费 (Daily Average)

**公式**:
```
日均消费 = 总支出金额 / 实际有消费的天数
```

**实现逻辑**:
1. 从数据库获取时间范围内所有"交易成功"的账单记录
2. 筛选出状态为"交易成功"的记录 (status_str = "交易成功")
3. 计算总支出: 对所有支出的 money 字段取绝对值求和
4. 统计有消费的天数: 对 date_str 去重得到唯一日期集合
5. 用总支出除以唯一日期数量得到日均

**边界处理**:
- 如果没有消费记录: daily_average = 0
- 如果只有1天有消费: daily_average = 当日总支出
- 公式可简写为: `expense / unique_dates.len().max(1)`

**Rust实现** (`statistics.rs`):
```rust
let days = {
    let unique_dates: HashSet<&str> = models.iter()
        .map(|m| m.date_str.as_str())
        .collect();
    (unique_dates.len() as f64).max(1.0)
};

daily_average: expense / days
```

### 3.2 分类占比计算

1. 对每笔交易使用分类器判断其类型
2. 按类型分组求和
3. 计算百分比: `分类金额 / 总金额 * 100%`

### 3.3 用餐时段判定

基于交易时间戳判断所属用餐时段:
- 早餐: 6:00 - 9:00
- 午餐: 11:00 - 13:00
- 晚餐: 17:00 - 19:00
- 非用餐时段: 其他时间

---

## 4. API接口

### 4.1 获取统计总览
```
get_statistics_summary(identity_id, date_start?, date_end?) -> StatisticsSummary
```

### 4.2 获取每日趋势
```
get_daily_trend(identity_id, date_start?, date_end?) -> Vec<DailyTrendItem>
```

### 4.3 获取分类分布
```
get_category_distribution(identity_id, date_start?, date_end?) -> Vec<CategoryItem>
```

### 4.4 获取用餐分布
```
get_meal_distribution(identity_id, date_start?, date_end?) -> Vec<MealDistItem>
```

### 4.5 获取消费区间分布
```
get_consumption_distribution(identity_id, date_start?, date_end?) -> Vec<ConsumptionBucketItem>
```

### 4.6 获取商户排行
```
get_merchant_ranking(identity_id, date_start?, date_end?) -> Vec<MerchantRankingItem>
```

### 4.7 获取分类详情
```
get_category_summary(identity_id, category, date_start?, date_end?) -> CategorySummary
```

---

## 5. 时间范围参数

| 参数 | 类型 | 说明 |
|------|------|------|
| date_start | Option<String> | 开始日期 (yyyy-MM-dd 或 yyyy.MM.dd) |
| date_end | Option<String> | 结束日期 |

- 两个参数都为 None 时，查询全部历史数据
- 只有 start: 查询从 start 到当前
- 只有 end: 查询从开始到 end
- 两者都有: 查询指定范围

---

## 6. 预置时间范围

### 本周
- start = 本周一
- end = 今天

### 本月
- start = 当月1日
- end = 当月最后一天

### 本学期
- 9月至次年1月: 9月1日 → 当月底
- 2月至8月: 2月1日 → 当月底

---

## 7. 数据筛选规则

所有统计API默认只包含**交易成功**的记录:
```sql
WHERE status_str = '交易成功'
```

交易状态的枚举值（供参考）:
- `交易成功`
- `交易失败`
- `已撤销`
- `等待支付`