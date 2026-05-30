# Docker Bundled 镜像构建方案

> 日期: 2026-05-29

## 概述

为 .NET OCR Server 和 C++ OCR Server 新增 **bundled** 镜像变体，将模型权重文件打包进镜像，开箱即用无需额外挂载。

## 模型文件来源

模型托管在独立仓库的 GitHub Releases 中：

| 类型 | Release Tag | 仓库 |
|------|-------------|------|
| ONNX (.NET) | `v1.0-ONNX` | `a645162/shmtu-cas-ocr-model` |
| NCNN (C++) | `v1.0-NCNN` | `a645162/shmtu-cas-ocr-model` |

### 下载 URL 格式

```
https://github.com/a645162/shmtu-cas-ocr-model/releases/download/{TAG}/{FILENAME}
```

### ONNX 模型文件 (v1.0-ONNX)

Release: https://github.com/a645162/shmtu-cas-ocr-model/releases/tag/v1.0-ONNX

- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-ONNX/resnet18_operator_latest.onnx`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-ONNX/resnet18_equal_symbol_latest.onnx`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-ONNX/resnet34_digit_latest.onnx`

### NCNN 模型文件 (v1.0-NCNN)

Release: https://github.com/a645162/shmtu-cas-ocr-model/releases/tag/v1.0-NCNN

- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet18_operator_latest.fp16.bin`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet18_operator_latest.fp16.param`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet18_equal_symbol_latest.fp16.bin`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet18_equal_symbol_latest.fp16.param`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet34_digit_latest.fp16.bin`
- `https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN/resnet34_digit_latest.fp16.param`

## 镜像标签规范

### .NET OCR Server

| 变体 | 标签示例 | 说明 |
|------|----------|------|
| CPU | `1.0.0`, `latest` | 不含模型 |
| GPU | `1.0.0-gpu`, `latest-gpu` | 不含模型 |
| CPU Bundled | `1.0.0-bundled`, `latest-bundled` | 含 ONNX 模型 |
| GPU Bundled | `1.0.0-gpu-bundled`, `latest-gpu-bundled` | 含 ONNX 模型 |

### C++ OCR Server

| 变体 | 标签示例 | 说明 |
|------|----------|------|
| CPU | `1.0.0-cpu`, `latest-cpu` | 不含模型 |
| Vulkan | `1.0.0-vulkan`, `latest-vulkan` | 不含模型 |
| CPU Bundled | `1.0.0-cpu-bundled`, `latest-cpu-bundled` | 含 NCNN fp16 模型 |
| Vulkan Bundled | `1.0.0-vulkan-bundled`, `latest-vulkan-bundled` | 含 NCNN fp16 模型 |

## Docker 镜像内部路径

| 组件 | 模型目录 | 环境变量 |
|------|----------|----------|
| .NET Server | `/app/models` | `OcrServer__ModelDirectory=/app/models` |
| C++ Server | `/app/models` | `SHMTU_MODEL_DIR=/app/models` |

Bundled 镜像中模型已通过 `COPY models/ /app/models/` 预置，程序可直接调用无需额外配置。

## Dockerfile 变更

### .NET Server (`shmtu-dotnet-lib/ocr/Dockerfile`)

新增两个 target：

```dockerfile
FROM runtime-cpu AS runtime-cpu-bundled
COPY models/ /app/models/

FROM runtime-gpu AS runtime-gpu-bundled
COPY models/ /app/models/
```

### C++ Server - vcpkg 构建 (`Dockerfile`)

```dockerfile
FROM runtime-cpu AS runtime-cpu-bundled
COPY models/ /app/models/

FROM runtime-gpu AS runtime-gpu-bundled
COPY models/ /app/models/
```

### C++ Server - system 构建 (`Dockerfile.runtime-system-cpu` / `Dockerfile.runtime-system-vulkan`)

```dockerfile
FROM shmtu-cas-ocr-server:cpu AS bundled
COPY models/ /app/models/
```

> 注意: system 构建的 `FROM` 引用的是本地镜像 tag（由 `docker_build_system.sh` 先构建），与 vcpkg 构建的 stage name 引用方式不同。

## CI/CD 流程

### .NET Server CI (`docker-publish.yml`)

1. **Checkout** + **下载模型** (curl 从 GitHub Releases)
2. 构建 base 镜像 → 推送 GHCR
3. 构建 bundled 镜像 → 推送 GHCR
4. GHCR → DockerHub (base + bundled)
5. GHCR → 阿里云 ACR (base + bundled)

模型下载命令：
```bash
MODEL_BASE="https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-ONNX"
mkdir -p ocr/models
for f in resnet18_operator_latest.onnx resnet18_equal_symbol_latest.onnx resnet34_digit_latest.onnx; do
  curl -fSL -o "ocr/models/${f}" "${MODEL_BASE}/${f}"
done
```

### C++ Server CI (`build-system-vulkan.yml`)

1. **Checkout** + **下载模型** (curl 从 GitHub Releases)
2. `docker_build_system.sh` 构建基础镜像 + bundled 镜像
3. GHCR: tag + push (base + bundled)
4. GHCR → DockerHub (base + bundled)
5. GHCR → 阿里云 ACR (base + bundled)

模型下载命令：
```bash
MODEL_BASE="https://github.com/a645162/shmtu-cas-ocr-model/releases/download/v1.0-NCNN"
mkdir -p models
for f in resnet18_operator_latest.fp16.bin resnet18_operator_latest.fp16.param \
         resnet18_equal_symbol_latest.fp16.bin resnet18_equal_symbol_latest.fp16.param \
         resnet34_digit_latest.fp16.bin resnet34_digit_latest.fp16.param; do
  curl -fSL -o "models/${f}" "${MODEL_BASE}/${f}"
done
```

## Docker Compose

两个 docker-compose.yml 中的 volumes 映射已默认注释：

```yaml
# volumes:
#   # 模型文件映射 (bundled 镜像无需挂载)
#   - ./models:/app/models
```

使用 bundled 镜像时无需取消注释；使用非 bundled 镜像时取消注释即可挂载本地模型。

## Gitee 镜像同步

与 GitHub 类似，Gitee 也可配置镜像同步。如需在 Gitee 上发布 bundled 镜像：

1. 在 Gitee Release 上传模型文件
2. 修改 CI 中 `MODEL_BASE` URL 指向 Gitee Release
3. 或使用 Gitee Container Registry 替代 DockerHub/阿里云

## 本地构建

```bash
# .NET Server
cd shmtu-terminal-desktop/shmtu-dotnet-lib
docker build --target runtime-cpu-bundled -f ocr/Dockerfile -t shmtu-ocr-server:cpu-bundled ocr/

# C++ Server (vcpkg)
cd Server/shmtu-cas-ocr-server
docker build --target runtime-cpu-bundled -f Dockerfile -t shmtu-cas-ocr-server:cpu-bundled .

# C++ Server (system)
./scripts/docker_build_system.sh cpu  # 自动构建 cpu + cpu-bundled
```
