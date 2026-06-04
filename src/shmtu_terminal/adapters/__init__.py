"""子模块适配层占位。

本包作为仓库聚合入口,子模块 (CAS / OCR / 各 Server 等) 由对应的 git
submodule 维护。具体适配实现在后续任务中按需添加:

- CAS 客户端: 透出 `Lib/shmtu-cas-python` 提供的同步/异步接口
- OCR 客户端: 对接 `Server/shmtu-cas-ocr-server` HTTP API
- 同步流程: 与 Tauri 子模块保持协议一致

子模块的本地可编辑安装示例:

    pip install -e ./Lib/shmtu-cas-python
"""
