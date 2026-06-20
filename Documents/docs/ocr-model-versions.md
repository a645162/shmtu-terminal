---
title: OCR 模型 v1 / v2 共存
---

# OCR 模型 v1 / v2 共存

SHMTU Terminal 系列 4 端（Tauri 桌面 / Avalonia 桌面 / Android / C++ OCR Server）现已同时支持 v1 与 v2 两套模型。
**v2 是默认推荐**，v1 保留仅作向后兼容与对比验证。

## 快速对照

| 维度 | v1 (legacy) | v2 (new, **默认**) |
|---|---|---|
| 模型数量 | 3 个独立模型 | **1 个** (Tri-Slot Decoder) |
| 一次前向推理 | 4 次（先判等号样式，再算子，再两数字） | **1 次** |
| 输入图像 | RGB 3×224×224，ImageNet mean/std 归一化 | 灰度 1×64×192，`[0, 1]` 直接归一化 |
| 默认 backbone | resnet18 / resnet34 | `mobilenet_v3_small` |
| 权重文件命名 | `resnet18_equal_symbol_latest.fp16.bin` 等 6 个文件 | `mobilenet_v3_small.trislot_decoder.v2_0.fp16.{onnx\|param\|bin}` |
| 运算符类别 | 6 类（含中文运算符） | 3 类（`+`、`-`、`×`） |
| 是否需要先判等号样式 | 是（先识别等号区） | **否**（整图端到端） |
| Release Tag | `v1.0-NCNN` / `v1.0-ONNX` | `v2.0.x`（含 `model-assets.json` 清单） |

## 各端切换入口

| 端 | UI / 配置项 | 持久化位置 | 默认值 |
|---|---|---|---|
| Tauri 桌面 | 设置 → OCR → 模型版本 | `config.json` (`ocr.model_version`) | `v2` |
| Avalonia 桌面 (`shmtu-terminal-desktop`) | 设置 → OCR → 模型版本 | 用户配置文件 | `v2` |
| Android (`shmtu_ocr`) | 设置 → 模型版本 | DataStore | `v2` |
| C++ CLI (`shmtu_cas_ocr_cli`) | `--model-version v1\|v2` | 命令行参数 | `v2` |
| C++ OCR Server (`shmtu_cas_ocr_server`) | `--model-version` / `OCR_MODEL_VERSION` 环境变量 / HTTP 请求体 `version` 字段 | 配置 + 运行时覆盖 | `v2` |
| C++ Server (Docker) | 启动时通过环境变量注入 | `docker-compose.yml` `OCR_MODEL_VERSION` | `v2` |

> **注意**：HTTP 请求体里增加 `version` 字段为运行时按次覆盖；服务端本身仍然受启动配置控制的默认版本约束。返回 JSON 字段不变。

## 下载策略

v2 走 **asset manifest 智能匹配**：

1. 客户端构造 `{tag, backbone, precision, engine}` 维度组合。
2. 拉取 release 根目录下的 [`model-assets.json`](https://github.com/a645162/shmtu-cas-ocr-model/releases) 清单。
3. 按维度查找匹配的资产文件名（如 `mobilenet_v3_small.trislot_decoder.v2_0.fp16.onnx`）。
4. GitHub 与 Gitee 互为 fallback，最多重试 3 次。
5. 不需要单独的 `SHA256SUMS.txt`（manifest 内已携带 hash 字段）。

v1 沿用 **硬编码文件列表 + SHA256SUMS.txt**：

1. 固定拉取 6 个权重文件（`equal_symbol` / `operator` / `digit` × `.param`/`.bin`）。
2. 下载 `SHA256SUMS.txt` 校验。
3. GitHub 与 Gitee 互为 fallback。

## Docker 镜像默认行为

C++ OCR Server 的 Docker 镜像（`runtime-cpu` / `runtime-gpu` 默认目标）**默认捆绑 v2 fp16 mobilenet_v3_small 单模型权重**：

- 镜像体积更小（单文件替代 6 文件）。
- 启动零等待，开箱即用。
- 如需使用 v1，挂载宿主机 `./models/v1/` 目录并设置 `OCR_MODEL_VERSION=v1` 即可。

bundled 镜像（`-bundled` 标签）目前仅打包 v2；如需 v1 bundled 镜像请自行修改 `Dockerfile` 多阶段 COPY。

## 各端代码示例

### Tauri / Rust (`shmtu-cas-rs`)

```rust
use shmtu_ocr::{CasOcr, ModelVersion};

let ocr = CasOcr::builder()
    .model_version(ModelVersion::V2)        // 默认就是 V2，可省略
    .model_dir("./models")
    .use_gpu(cfg!(feature = "vulkan"))
    .build()?;

ocr.ensure_models_async(None).await?;
ocr.load_model()?;
let result = ocr.predict(bitmap)?;
println!("{} = {}", result.expr, result.result);
```

### Avalonia / .NET (`shmtu-ocr-onnx-lib`)

```csharp
using shmtu.captcha.onnx;

using var ocr = new CasOcr(
    modelDirectoryPath: "./models",
    useGpu: false,
    version: ConstValue.ModelVersion.V2     // 默认 v2
);
await ocr.EnsureModelsAsync();              // 缺失则自动下载
ocr.LoadModel();
var (result, expr, eq, op, d1, d2) = ocr.PredictValidateCode("captcha.png");
```

### Android (Kotlin NCNN)

```kotlin
val ocr = SHMTU_NCNN_Model(
    context = applicationContext,
    modelDir = File(filesDir, "models"),
    version = ModelVersion.V2,              // 默认 V2
    useGpu = false
)
ocr.ensureModels { progress -> /* ... */ }
ocr.loadModel()
val result = ocr.predictValidateCode(bitmap)
```

### C++ CLI

```bash
# 默认 v2
./shmtu_cas_ocr_cli captcha.png

# 显式指定 v1
./shmtu_cas_ocr_cli --model-version v1 captcha.png
```

### C++ Server (HTTP)

```bash
# 启动时设置默认版本
./shmtu_cas_ocr_server --model-version v2 --model-dir ./models

# 启动后单次请求覆盖
curl -X POST http://localhost:21600/api/ocr \
  -H 'Content-Type: application/json' \
  -d '{"imageBase64": "...", "version": "v1"}'
```

## 迁移建议

- 新部署：直接使用 v2，无任何额外配置。
- 现有 v1 部署：在设置面板切换至 v1 验证通过后再切换到 v2；如需保留 v1 行为可在配置中显式指定。
- A/B 对比：v1/v2 在同一台机器上可同时存在（不同目录），切换无副作用。

## 把手机 / Tauri 桌面变成 OCR 推理服务器

为方便 **同网段多设备** 共享一份 NCNN / ONNX 推理资源,SHMTU Terminal 在 Android 与 Tauri
桌面端额外暴露了 **RESTful OCR 服务器**,端点契约与 [shmtu-cas-rs/ocr-http](https://github.com/a645162/shmtu-cas-rs)
完全一致,可直接被现有 `CaptchaOcrHttp` 客户端复用。

### 核心特性

| 项 | 行为 |
|---|---|
| 端点 | `POST /api/ocr`  (请求 `{"imageBase64": "..."}`) |
| 响应 | `{"success": true, "expression": "3+5=8", "result": 8, "modelVersion": "V2"}` |
| 健康检查 | `GET /api/health` 返回 `{models_loaded, model_version, status}` |
| 状态 / 信息 | `GET /api/status` (含计数 / 平均耗时) 与 `GET /api/info` (含 token / IP) |
| 鉴权 | `Authorization: Bearer <token>` 或 `?token=<token>` |
| **懒加载** | **首次** `POST /api/ocr` 收到请求时才加载模型,后续请求复用热模型 (毫秒级) |
| 默认端口 | Android: `5000` ; Tauri: `5000` (可在设置面板修改) |
| **访问范围** | `loopback_only` (仅 127.0.0.1)、`lan` (0.0.0.0，默认)、`custom_ip` (绑定指定网卡 IP) |
| 配置持久化 | Android: SharedPreferences `ocr_server_scope` / `ocr_server_bind_addr` ; Tauri: `[captcha].ocr_server_scope` / `ocr_server_bind_addr` |

### Android (`shmtu-terminal-android`)

- 模块: `app/src/main/java/cn/edu/shmtu/terminal/android/data/ocrserver/`
  - `OcrServerSettings` — 端口 / token / 模型版本 / v2 backbone+precision / scope 持久化
  - `OcrServerScope` 枚举 — `LOOPBACK_ONLY` / `LAN` / `CUSTOM_IP`
  - `OcrWebServer` — 基于 NanoHTTPD, `start(port, bindHost)` 由 scope 决定 bind IP; 首次 POST 触发 `NcnnModelLoader.ensureLoaded`
  - `OcrServerService` — 前台服务 (常驻通知 + 启停控制)
- 协议对齐: 与 `CaptchaOcrHelper.buildExprString` 直接对接,保证 v1/v2 自动兼容
- 触发: 设置面板开关 / `ocr_server_auto_start=true` 自启 / 通知栏 Action

### Tauri 桌面 (`shmtu-terminal-tauri`)

- 模块: `src-tauri/src/ocr_server/`
  - `OcrHttpServerManager` — 端口 / token / 计数 / 启停
  - `ensure_loaded_lazy` — 首次请求在 `spawn_blocking` 中调 `OcrBackend::load`,与现有
    `commands::captcha::do_test_captcha` 的 `local_onnx` 模式 **复用同一个 `AppState.local_ocr` 实例**
    (不会重复加载)
- 配置: `[captcha].ocr_server_enabled` / `ocr_server_port` / `ocr_server_scope` / `ocr_server_bind_addr` 写入 `app_config.toml`
- Tauri 命令: `ocr_server_start({port?, scope?, bind_addr?})` / `stop` / `status` / `rotate_token`
- 自动启动: 启动时若 `ocr_server_enabled = true`,在 `setup` 同步闭包内用
  `tauri::async_runtime::block_on` 拉起 HTTP 监听器

### 访问范围说明

| Scope | Bind IP | 可达范围 | 使用场景 |
|---|---|---|---|
| `loopback_only` | `127.0.0.1` | 仅本机进程 | 安全敏感环境,仅供同机 Tauri/CLI 调用 |
| `lan` (默认) | `0.0.0.0` | 本机 + 同局域网所有设备 | 家庭/实验室,多设备共享推理 |
| `custom_ip` | 用户指定的 IP | 仅绑定该网卡 | 多网卡机器选特定网段,或绑定 VPN IP |

两台客户端互相调用时，调用方需通过 `/api/info` 返回的 `bindAddress` + `ips` 字段确认目标 IP 可达。

### 客户端调用示例 (任意 4 端)

```kotlin
val client = CaptchaOcrHttp("http://192.168.1.100:5000/?token=ABC...")
val expr = client.ocrByHttp(captchaPngBytes)  // 返回 "3+5=8"
val answer = expr.substringAfter("=").trim()  // "8"
```

### 与 Rust 端 `shmtu-ocr-server` (CLI) 的差异

| 维度 | Rust `shmtu-ocr-server` | Android `OcrWebServer` | Tauri `OcrHttpServerManager` |
|---|---|---|---|
| 启动模型 | 启动时 `OcrBackend::load` 预加载 | **懒加载** (首次请求) | **懒加载** (首次请求) |
| 后端 | Rust ONNX | NCNN (NCNN + OpenCV Mobile) | ONNX (ort) |
| 端口 | 默认 `21600` (CLI 可调) | 默认 `5000` | 默认 `5000` |
| 进程模型 | 独立 CLI / Docker | 嵌入 app 前台服务 | 嵌入 Tauri 主进程 |
| 客户端 | 同上 | 同上 | 同上 |

三者协议层兼容,客户端无需感知后端差异。

## 相关链接

- C++ OCR Server 模型管理：[Documents/docs/ocr-server-model-management](https://a645162.github.io/shmtu-cas-ocr-server/guide/model-management)
- 模型训练与导出：[shmtu-cas-ocr-model V2 文档](https://a645162.github.io/shmtu-cas-ocr-model/usage/v2-quickstart)
- V1 旧文档：[shmtu-cas-ocr-model V1 概览](https://a645162.github.io/shmtu-cas-ocr-model/usage/v1-overview)
