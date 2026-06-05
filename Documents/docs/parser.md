# BillParser 账单解析

`cn.edu.shmtu.cas.parser.BillParser` 负责把 SHMTU 校园门户的 HTML 页面解析为强类型 `BillItem` 列表。

## 1. 使用方法

```kotlin
import cn.edu.shmtu.cas.parser.BillParser
import cn.edu.shmtu.cas.datatype.BillItem

val parser = BillParser()
val items: List<BillItem> = parser.parseBillItems(html)
```

或一次性:

```kotlin
val result: BillParseResult = parser.parseBillPage(html)
// result.bills: List<BillItem>
// result.totalPages: Int
```

## 2. HTML 结构 (JSoup 选择器)

```
#aazone\\.zone_show_box_1 > table > tbody
   └── tr (每行一条账单)
        ├── td[0]: 日期 + 时间
        │   ├── div[0]: "2024.03.15"
        │   └── div[1]: "123456" (HHMMSS)
        ├── td[1]: 类型 + 交易号
        │   ├── a/div[0]: 类型名 ("消费" / "中行云充值" / ...)
        │   └── div[1]: 交易号文本 "交易号：20240315xxxxx"
        ├── td[2]: 对方账户 ("A食堂1楼大餐厅" / "中行" / ...)
        ├── td[3]: 金额 ("¥12.34")
        ├── td[4]: 支付方式 ("校园卡" / "微信" / ...)
        ├── td[5]: 状态 ("交易成功" / "交易失败")
        └── td[6]: (操作)
```

## 3. 解析后的 BillItem 字段

```kotlin
data class BillItem(
    val dateStr: String,           // "2024.03.15"
    val timeStr: String,           // "123456"
    val timeStrFormat: String,     // "12:34:56"
    val dateTimeFormat: String,    // "2024.03.15 12:34:56"
    val timestamp: Long,           // 秒级 epoch
    val billType: String,          // "消费" / "中行云充值" / "电费缴费" / ...
    val transactionNo: String,     // "20240315xxxxx"
    val targetUser: String,        // "A食堂1楼大餐厅" / "中行" / ...
    val amount: String,            // "¥12.34"  (带 ¥ 和逗号)
    val money: Float,              // 12.34f     (纯数字)
    val paymentMethod: String,     // "校园卡" / "微信" / "支付宝" / ...
    val status: BillItemStatus     // 强类型 (Success / Pending / Failed)
)
```

## 4. 数字处理

- **money (String)**: 保留原始格式 "¥1,234.56" (用于显示)
- **money (Float)**: 转成 float 12.34f (用于计算)
- 转换函数: `String.toFloatOrNull() ?: 0f`

```kotlin
private fun String.onlyFloatDigits(): String = this.replace("[^\\d.]".toRegex(), "")
private fun String.onlyDigits(): String = this.replace("[^\\d]".toRegex(), "")
```

## 5. 时间戳生成

```kotlin
private fun parseDateTime(dateStr: String, timeStr: String): Long {
    val dateTimeStr = "${dateStr.trim()} ${timeStr.trim().replace(Regex("(\\d{2})(\\d{2})(\\d{2})"), "$1:$2:$3")}"
    return try {
        val formatter = DateTimeFormatter.ofPattern("yyyy.MM.dd HH:mm:ss")
        LocalDateTime.parse(dateTimeStr, formatter)
            .atZone(ZoneId.systemDefault())
            .toEpochSecond()
    } catch (_: Exception) { 0L }
}
```

- 输入时间格式: HHMMSS (6 位无分隔符)
- 输出: 秒级 epoch (本地时区)
- 解析失败返回 0L (Android Room 不会存储 1970-01-01, 但 UI 上要小心)

## 6. 状态映射

```kotlin
enum class BillItemStatus { SUCCESS, PENDING, FAILED, UNKNOWN }

fun fromString(text: String): BillItemStatus = when (text.trim()) {
    "交易成功" -> SUCCESS
    "待支付" -> PENDING
    "交易失败" -> FAILED
    else -> UNKNOWN
}
```

Android 端 BillEntity.status 字段存的是 `status.name` 字符串, 可能为 "SUCCESS" 或 "交易成功" (老数据兼容)。

## 7. 与 Tauri Rust 端对齐

| 维度 | Tauri (Rust) | cas_lib (Kotlin) |
|------|-------------|------------------|
| HTML 解析库 | `scraper` / `kuchiki` | Jsoup 1.22.2 |
| 选择器 | CSS selectors | Jsoup `select()` |
| 数字解析 | `parse::<f64>()` | `toFloatOrNull() ?: 0f` |
| 时间戳 | `chrono` | `java.time.LocalDateTime` |
| 状态枚举 | Rust enum | Kotlin enum class |

## 8. 边界情况处理

| 异常 | 处理 |
|------|------|
| HTML 没有 #aazone.zone_show_box_1 | 返回空 list |
| tr 子元素不是 7 个 | skip 这一行 |
| 金额包含特殊字符 | `onlyFloatDigits()` 过滤 |
| 交易号带前缀 "交易号：" | `onlyDigits()` 过滤 |
| 时间格式非 HHMMSS | regex 转换; 失败返回 0L |
| 状态文本无法识别 | UNKNOWN |

## 9. 测试

`cas_lib` 内有 BillParser 单元测试 (见 cas_lib/src/test/)。关键测试用例:

```kotlin
@Test
fun parseStandardBill() {
    val html = """
        <html><body>
        <div id="aazone.zone_show_box_1">
            <table><tbody>
            <tr>
                <td><div>2024.03.15</div><div>123456</div></td>
                <td><div>消费</div><div>交易号：1234567890</div></td>
                <td>A食堂1楼大餐厅</td>
                <td>¥12.34</td>
                <td>校园卡</td>
                <td>交易成功</td>
                <td>查看</td>
            </tr>
            </tbody></table>
        </div>
        </body></html>
    """.trimIndent()
    val items = BillParser().parseBillItems(html)
    assertEquals(1, items.size)
    val bill = items[0]
    assertEquals("A食堂1楼大餐厅", bill.targetUser)
    assertEquals("消费", bill.billType)
    assertEquals(12.34f, bill.money)
    assertEquals(BillItemStatus.SUCCESS, bill.status)
}
```

## 10. 已知问题

- JSoup 解析大 HTML (1MB+) 时占用内存, 可考虑流式解析
- `onlyDigits()` 过滤后丢失前导零, 交易号长度可能变化 (老账单短)
- `status` 文本与 Rust 端不完全一致 (Tauri 用中文, Kotlin 用 enum name)
