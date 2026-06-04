# 开发日志归档

> 版本：1.0 | 更新日期：2026-06-04
>
> 命名规范：`YYYY-MM-DD-<topic>.md`

## 目录

| 日期 | 文档 | 主题 |
| --- | --- | --- |
| 2026-05-25 | [daily-average.md](./daily-average.md) | 账单统计「日均消费」计算规则（区分无消费日、跨自然月、补录场景） |
| 2026-05-29 | [docker-bundled.md](./docker-bundled.md) | OCR Server bundled 镜像变体（CPU / GPU / Vulkan × 是否含模型权重），模型来源 GitHub Releases `v1.0-ONNX` / `v1.0-NCNN` |
| 2026-05-29 | [multi-server-monitor.md](./multi-server-monitor.md) | 多 OCR 服务健康监控（`shmtu-service-monitor`）的设计与并发探测策略 |

## 新增日志流程

1. 在 `Documents/dev/` 下新建 `YYYY-MM-DD-<topic>.md`
2. 在本页表格追加一行（保持**日期正序**）
3. 在 `docs/overview.md` 的「开发日志」小节同步追加一行
