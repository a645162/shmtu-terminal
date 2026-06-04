# 总览与索引

> 版本：1.0 | 更新日期：2026-06-04
>
> 本文档是 `shmtu-terminal` 聚合仓库所有横切式文档的**总入口**。

## 专题设计文档

| 文档 | 主题 |
| --- | --- |
| [数据模型](./data-model.md) | Identity / Account / BillOriginal / BillMerged 等核心实体 |
| [功能规划](./feature-spec.md) | P0/P1/P2 三级功能矩阵 + 客户端对标 |
| [界面设计](./ui-design.md) | Avalonia 多窗口 vs Tauri 单页多路由的界面基线 |
| [账单统计模块](./statistics-design.md) | `StatisticsSummary` / `DailyTrendItem` / `CategoryItem` 数据模型 |

## 开发日志

| 日期 | 主题 |
| --- | --- |
| 2026-05-25 | [日均消费计算规则](./dev/daily-average.md) |
| 2026-05-29 | [Docker bundled 镜像变体](./dev/docker-bundled.md) |
| 2026-05-29 | [多 OCR 服务健康监控](./dev/multi-server-monitor.md) |

完整索引与新日志归档格式见 [开发日志归档](./dev/index.md)。

## 跨模块依赖速查

下表把每个业务功能**对应到具体子模块**，便于「看文档 → 改代码」。

| 业务能力 | 主要实现位置 | 子模块文档 |
| --- | --- | --- |
| CAS / 一卡通认证 + 验证码 | `Lib/shmtu-cas-python` / `Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin` / `shmtu-terminal-tauri/src-tauri/vendor/shmtu-cas-rs` | `Lib/shmtu-cas-python/Documents/docs` |
| 浏览器端 OCR 自动填表 | `Plugin/shmtu-cas-ocr-crx` | `Plugin/shmtu-cas-ocr-crx/Documents/docs` |
| OCR 识别（HTTP 服务） | `Server/shmtu-cas-ocr-server` (C++ ncnn) | [dev/2026-05-29-docker-bundled-image.md](./dev/docker-bundled.md) |
| OCR 模型权重 | `Model/shmtu-cas-ocr-model` | — |
| 桌面应用 (Rust) | `shmtu-terminal-tauri` | `shmtu-terminal-tauri/Documents/docs` |
| 桌面应用 (.NET) | `shmtu-terminal-desktop` | `shmtu-terminal-desktop/Documents/docs` |
| Android | `shmtu-terminal-android` | `shmtu-terminal-android/Documents/docs` |
| 羽毛球场预约 | `Server/smu-badminton` | `Server/smu-badminton/Documents/docs` |
| Spring Boot 后端 | `Server/shmtu-server-unofficial` | `Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin/Documents/docs` |
| 多服务监控 | `Server/shmtu-service-monitor` | [dev/2026-05-29-multi-server-monitor.md](./dev/multi-server-monitor.md) |

## 贡献规范

1. **新增专题文档**：放在 `Documents/docs/<topic>.md`，并在本文档「专题设计」表格中追加索引。
2. **新增开发日志**：放在 `Documents/dev/YYYY-MM-DD-<topic>.md`（ISO 日期），并在 `dev/index.md` 与本文档中追加一行。
3. **文档与代码同步**：根据根目录 `CLAUDE.md` 的「文档更新规则」，**当代码行为变化时必须同步更新相关文档**。
4. **风格约定**：标题用 `#` / `##` / `###` 三级以内；表格超过 4 列时拆分为多张；代码块标注语言。
5. **版本头**：每个专题文档顶部建议保留：
   ```markdown
   > 版本：x.y | 更新日期：YYYY-MM-DD
   ```

## 待办与缺失

| 主题 | 状态 | 备注 |
| --- | --- | --- |
| CAS 协议与接口字段表 | 待写 | 需配合 `Lib/shmtu-cas-python` 的源码反推 `ecard.shmtu.edu.cn` 表单字段 |
| Android 端架构 / 模块图 | 待写 | 仓库内有 `Lib/shmtu-cas-kotlin` 但缺少独立文档 |
| Tauri 端架构 / Rust 端模块图 | 待写 | `shmtu-terminal-tauri` 自带 README 是模板 |
| `.NET 桌面端`架构图 | 待写 | `shmtu-terminal-desktop` 缺独立文档 |
| Spring Boot `shmtu-server-unofficial` API 列表 | 待写 | 仅仓库 README |
| 数据导入 / 导出格式规范 | 待写 | `F09` 涉及 CSV / JSON / 钱迹 / 快照多种格式 |
