# Documents — 文档总览

> 版本：1.0 | 更新日期：2026-06-04
>
> 本目录收录 `shmtu-terminal` 聚合仓库的**横切式 / 跨子模块**的设计文档与开发日志。
>
> **VitePress 站点源码位于 `Documents/docs/`**（`cd Documents && npm install && npm run docs:dev`）。
> 浏览入口：[`docs/`](./docs/)（VitePress 站点），按下方表格的链接访问各专题。

---

## 〇、目录结构

```
Documents/
├── README.md                        # 本文件
├── package.json                     # vitepress 依赖与脚本
├── docs/                            # VitePress 站点（被 GH Pages 部署）
│   ├── .vitepress/config.ts
│   ├── index.md                     # 站点首页
│   ├── overview.md                  # 总览与索引
│   ├── data-model.md                # 跨子模块数据模型
│   ├── feature-spec.md              # 功能规划
│   ├── ui-design.md                 # 界面设计
│   ├── statistics-design.md         # 账单统计模块
│   └── dev/
│       ├── index.md                 # 开发日志归档
│       ├── daily-average.md
│       ├── docker-bundled.md
│       └── multi-server-monitor.md
└── dev/                             # 开发日志原始文件（与 docs/dev 同步）
    ├── 2026-05-25-daily-average-calculation.md
    ├── 2026-05-29-docker-bundled-image.md
    └── 2026-05-29-multi-server-monitor.md
```

---

## 一、专题设计文档

| 文档 | 主题 |
| --- | --- |
| [`docs/data-model.md`](./docs/data-model.md) | 数据模型（Identity / Account / BillOriginal / BillMerged ...） |
| [`docs/feature-spec.md`](./docs/feature-spec.md) | 功能规划（P0/P1/P2 + 客户端对标） |
| [`docs/ui-design.md`](./docs/ui-design.md) | 界面设计（Avalonia 多窗口 vs Tauri 单页多路由） |
| [`docs/statistics-design.md`](./docs/statistics-design.md) | 账单统计模块详细设计 |

## 二、开发日志

| 日期 | 文档 | 主题 |
| --- | --- | --- |
| 2026-05-25 | [`docs/dev/daily-average.md`](./docs/dev/daily-average.md) | 账单统计「日均消费」计算规则 |
| 2026-05-29 | [`docs/dev/docker-bundled.md`](./docs/dev/docker-bundled.md) | OCR Server bundled 镜像变体 |
| 2026-05-29 | [`docs/dev/multi-server-monitor.md`](./docs/dev/multi-server-monitor.md) | 多 OCR 服务健康监控 |

## 三、本地预览

```bash
cd Documents
npm install
npm run docs:dev      # http://localhost:5173
npm run docs:build    # 产物: Documents/docs/.vitepress/dist
npm run docs:preview  # 预览构建产物
```

## 四、跨模块依赖速查

| 业务能力 | 主要实现位置 | 文档 |
| --- | --- | --- |
| CAS / 一卡通认证 + 验证码 | `Lib/shmtu-cas-python` / `Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin` / `shmtu-terminal-tauri/src-tauri/vendor/shmtu-cas-rs` | `Lib/shmtu-cas-python/Documents/docs` |
| 浏览器端 OCR 自动填表 | `Plugin/shmtu-cas-ocr-crx` | `Plugin/shmtu-cas-ocr-crx/Documents/docs` |
| OCR 识别（HTTP 服务） | `Server/shmtu-cas-ocr-server` (C++ ncnn) | `docs/dev/docker-bundled.md` |
| 桌面应用 (Rust) | `shmtu-terminal-tauri` | 仓库自带 README / Rust doc |
| 桌面应用 (.NET) | `shmtu-terminal-desktop` | 仓库自带 README |
| Android | `shmtu-terminal-android` | 仓库自带 README |

## 五、贡献规范

1. **新增专题文档**：放在 `Documents/docs/<topic>.md`，并在 `docs/overview.md` 中追加索引。
2. **新增开发日志**：放在 `Documents/dev/YYYY-MM-DD-<topic>.md`（ISO 日期），**同步**复制到 `docs/dev/<topic>.md` 并在 `docs/dev/index.md` 中追加索引。
3. **文档与代码同步**：根据根目录 `CLAUDE.md` 的「文档更新规则」，**当代码行为变化时必须同步更新相关文档**。
4. **风格约定**：标题用 `#` / `##` / `###` 三级以内；表格超过 4 列时拆分为多张；代码块标注语言。
