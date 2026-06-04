---
layout: home

hero:
  name: shmtu-terminal
  text: 文档总览
  tagline: 跨子模块的设计文档与开发日志聚合
  actions:
    - theme: brand
      text: 总览与索引
      link: /overview
    - theme: alt
      text: 数据模型
      link: /data-model
    - theme: alt
      text: 功能规划
      link: /feature-spec
    - theme: alt
      text: 开发日志
      link: /dev/index

features:
  - title: 专题设计
    details: 数据模型 / 功能规划 / 界面设计 / 统计模块 — 跨子模块通用的核心定义
  - title: 开发日志
    details: 按日期归档的关键决策、问题排查与方案记录
  - title: 跨模块依赖
    details: 每个业务能力到具体子模块的索引，方便「看文档 → 改代码」
---

## 这套文档做什么

这套文档是 `shmtu-terminal` 聚合仓库的**横切式索引**，专门收录那些**不属于单一子模块**的跨切面主题：

- 跨子模块通用的数据模型（Identity / Account / Bill）
- 全局功能规划与优先级
- 跨端界面设计基线
- 与具体日期强绑定的开发决策

子模块自身的实现细节请直接查看其仓库内的 `Documents/`。

## 子模块文档入口

| 子模块 | 文档入口 |
| --- | --- |
| Tauri 桌面 | `shmtu-terminal-tauri/Documents/docs` |
| .NET 桌面 | `shmtu-terminal-desktop/Documents/docs` |
| Android | `shmtu-terminal-android/Documents/docs` |
| CAS / OCR Python 库 | `Lib/shmtu-cas-python/Documents/docs` |
| 浏览器扩展 OCR | `Plugin/shmtu-cas-ocr-crx/Documents/docs` |
| OCR Server (C++) | `Server/shmtu-cas-ocr-server/Documents/docs` |
| 羽毛球预约 | `Server/smu-badminton/Documents/docs` |
| Spring Boot 后端 | `Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin/Documents/docs` |
| CAS Rust 库 | `shmtu-terminal-tauri/src-tauri/vendor/shmtu-cas-rs/Documents/docs` |
