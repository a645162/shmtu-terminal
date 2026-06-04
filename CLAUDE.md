# SHMTU Terminal

上海海事大学校园终端应用，包含三个客户端子模块、四个 Server 子模块和浏览器插件子模块：

- **shmtu-terminal-tauri** — Tauri v2 桌面应用 (Rust 后端 + React/TypeScript 前端)
- **shmtu-terminal-desktop** — .NET 8 桌面应用及 CAS/OCR 库
- **shmtu-terminal-android** — Android 客户端 (Kotlin)
- **Server/shmtu-cas-ocr-server** — C++ OCR 服务 (Drogon + ncnn, 支持 CPU/Vulkan GPU)
- **Server/shmtu-service-monitor** — 服务监控
- **Server/smu-badminton** — 羽毛球场预约系统 (FastAPI + NCNN OCR, SQLite)
- **Server/shmtu-server-unofficial** — Spring Boot 后端服务 (Kotlin JVM)，引用 shmtu-cas-kotlin 的 cas_lib (JVM) 子模块
- **Plugin/shmtu-cas-ocr-crx** — 浏览器扩展 (Chrome Extension)，用于 CAS 验证码 OCR 自动识别

## API

只要不是RESTful API,所有的lib的API没有任何历史包袱，如果确实需要重写，则直接重写，不需要考虑任何的兼容！

## 子模块开发命令

### shmtu-terminal-tauri

```bash
cd shmtu-terminal-tauri
npm install                    # 安装前端依赖
npm run dev                    # 启动 Vite 开发服务器
npm run tauri dev              # 启动 Tauri 开发模式（前后端联动）
npm run build                  # 前端构建 (tsc + vite)
cargo check --manifest-path src-tauri/Cargo.toml   # Rust 类型检查
cargo clippy --manifest-path src-tauri/Cargo.toml  # Rust lint
npx tsc --noEmit               # TypeScript 类型检查
```

### shmtu-terminal-desktop

```bash
cd shmtu-terminal-desktop
dotnet build                   # 编译解决方案
dotnet run --project shmtu-terminal-desktop   # 运行桌面应用
python3 Scripts/run_ocr_server.py run 5000    # 启动 OCR 服务器
python3 Scripts/run_dotnet_demo.py            # 运行 CAS 演示
```

### shmtu-terminal-android

```bash
cd shmtu-terminal-android
./gradlew assembleDebug        # 构建 Debug APK
./gradlew installDebug         # 安装到设备
```

### Server/shmtu-cas-ocr-server

```bash
cd Server/shmtu-cas-ocr-server
# Docker 多阶段构建 (CPU/Vulkan)
docker build -f Dockerfile --target runtime-cpu -t shmtu-ocr-server:cpu .
docker build -f Dockerfile --target runtime-gpu -t shmtu-ocr-server:vulkan .
# System 依赖构建 (需 Docker builder 镜像)
python3 scripts/_common.py     # 查看构建目录结构
./scripts/ci_build_system_vulkan.sh  # CI 构建 Vulkan 版本
```

### Server/smu-badminton

```bash
cd Server/smu-badminton
pip install -e .                                          # 安装 (可编辑模式)
python -m smu_badminton.server_fastapi                    # 启动开发服务器 (端口 5002, 自动重载)
BOOKING_DEBUG=1 python -m smu_badminton.server_fastapi    # 调试模式 (详细预约日志)
docker-compose up --build                                 # 生产部署
python -m pytest tests/ -v                                # 运行全部测试
python -m pytest tests/unit/ -v                           # 仅单元测试
python -m pytest tests/integration/ -v                    # 仅集成测试
```

### Server/shmtu-server-unofficial

```bash
cd Server/shmtu-server-unofficial
git submodule update --init --recursive                    # 初始化嵌套子模块 (shmtu-cas-kotlin)
./gradlew projects                                        # 查看项目结构 (含 cas-lib 子项目)
./gradlew compileKotlin                                   # 编译项目
./gradlew bootRun                                         # 启动 Spring Boot 开发服务器
```

## 架构要点

- Tauri 子模块是主要开发焦点，后端 Rust 负责同步/存储/加密，前端 React + Fluent UI
- 同步流程支持三种验证码模式：手动输入、远程 OCR、本地 ONNX
- 身份 (Identity) → 多账号 (Account) 层级结构，支持身份级和账号级增量/全量同步
- .NET 子模块提供 CAS 认证库和 OCR ONNX 推理服务
- OCR Server 子模块使用多阶段 Dockerfile，支持 CPU (`runtime-cpu`) 和 Vulkan GPU (`runtime-gpu`) 两个构建目标
- CI Workflow (`.github/workflows/build-system-vulkan.yml`) 采用 CPU/Vulkan 并行构建 → GHCR 推送 → DockerHub/阿里云并行分发模式
- Badminton 子模块是 FastAPI 羽毛球场预约系统，集成 CAS 认证 + NCNN OCR 验证码识别，支持即时预约和定时预约（多线程并发抢场）
- Badminton 核心流程：CAS 登录 → OCR 识别验证码 → 查询场地可用性 → 即时/定时预约；定时预约使用 barrier 同步多线程同时发起请求
- Badminton 使用线程安全 SQLite (WAL 模式) 存储预约记录和任务持久化，公开可用性缓存 60s TTL 跨用户共享
- shmtu-server-unofficial 是 Spring Boot 后端服务，通过 Gradle include 引用 shmtu-cas-kotlin 的 cas_lib (JVM) 子模块作为依赖，嵌套子模块结构：shmtu-terminal → Server/shmtu-server-unofficial → lib/shmtu-cas-kotlin

## 共享库同步规则

`shmtu-cas-kotlin` 同时作为以下两个项目的 git submodule：

- `shmtu-terminal-android/lib/shmtu-cas-kotlin`
- `Server/shmtu-server-unofficial/lib/shmtu-cas-kotlin`

**修改库后的同步流程**：在任一项目中修改 `shmtu-cas-kotlin` 并 push 后，必须在另一个项目中 `cd lib/shmtu-cas-kotlin && git pull origin main` 拉取最新提交，然后更新该项目的 submodule 引用并提交。

**自动提交规则**：对任何 lib 子模块（shmtu-cas-kotlin 等）的修改，只要测试通过（编译/单元测试），即自动提交并 push，无需额外确认。

## 文档更新规则

如果目标项目存在Documents目录，则更新代码的同时，如果行为发生改变，则应该一并更新文档！
