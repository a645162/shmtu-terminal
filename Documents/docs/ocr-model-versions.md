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

## 相关链接

- C++ OCR Server 模型管理：[Documents/docs/ocr-server-model-management](https://a645162.github.io/shmtu-cas-ocr-server/guide/model-management)
- 模型训练与导出：[shmtu-cas-ocr-model V2 文档](https://a645162.github.io/shmtu-cas-ocr-model/usage/v2-quickstart)
- V1 旧文档：[shmtu-cas-ocr-model V1 概览](https://a645162.github.io/shmtu-cas-ocr-model/usage/v1-overview)
