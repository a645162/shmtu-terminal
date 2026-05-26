# SHMTU Terminal

上海海事大学校园终端应用，包含三个子模块：

- **shmtu-terminal-tauri** — Tauri v2 桌面应用 (Rust 后端 + React/TypeScript 前端)
- **shmtu-terminal-desktop** — .NET 8 桌面应用及 CAS/OCR 库
- **shmtu-terminal-android** — Android 客户端 (Kotlin)

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

## 架构要点

- Tauri 子模块是主要开发焦点，后端 Rust 负责同步/存储/加密，前端 React + Fluent UI
- 同步流程支持三种验证码模式：手动输入、远程 OCR、本地 ONNX
- 身份 (Identity) → 多账号 (Account) 层级结构，支持身份级和账号级增量/全量同步
- .NET 子模块提供 CAS 认证库和 OCR ONNX 推理服务
