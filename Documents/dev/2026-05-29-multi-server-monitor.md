# SHMTU Service Monitor — 多服务器监控

## 概述

Service Monitor 从 v1（扁平服务列表）升级到 v2（服务器组 → 实例 两级模型），支持监控多个逻辑服务器组，每组可包含多个 OCR 服务实例。

## 数据模型

### v1（旧）

```
Service (id, name, service_type, base_url, poll_interval_secs, created_at)
  └── ServiceStatus (id, service_id, status, ...)
```

### v2（新）

```
MonitorServer (id, name, description, created_at)
  └── ServiceInstance (id, server_id, name, service_type, base_url, poll_interval_secs, created_at)
       └── ServiceStatus (id, instance_id, status, availability_level, models_loaded,
                          pending_requests, queue_capacity, utilization_percent,
                          avg_response_ms, total_requests, success_count, failure_count,
                          polled_at, response_time_ms)
```

### 自动迁移

启动时若检测到旧版 `services` 表，会自动：
1. 创建 `Default Server` 服务器组
2. 将所有旧 Service 迁移为该组下的 Instance
3. 迁移历史状态数据
4. 删除旧表

## API 参考

### 服务器组 (Servers)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/servers` | 创建服务器组 |
| GET | `/api/servers` | 列出所有服务器组 |
| GET | `/api/servers/{id}` | 获取服务器组详情 |
| DELETE | `/api/servers/{id}` | 删除服务器组（级联删除实例） |
| GET | `/api/servers/{id}/detail` | 获取服务器组详情 + 实例状态 |

#### 创建服务器组

```json
POST /api/servers
{
  "name": "生产环境 OCR 集群",
  "description": "主校区服务器"
}
```

#### 服务器组详情响应

```json
GET /api/servers/1/detail
{
  "server": { "id": 1, "name": "生产环境 OCR 集群", "description": "主校区服务器", "created_at": "..." },
  "instances": [
    {
      "instance": { "id": 1, "server_id": 1, "name": "OCR #1", "service_type": "dotnet-ocr", "base_url": "http://192.168.1.10:21600", ... },
      "latest_status": { "status": "healthy", "models_loaded": true, "response_time_ms": 12.5, ... }
    }
  ]
}
```

### 实例 (Instances)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/servers/{server_id}/instances` | 在指定服务器组下注册实例 |
| GET | `/api/servers/{server_id}/instances` | 列出服务器组下所有实例 |
| GET | `/api/instances/{id}` | 获取实例详情 |
| DELETE | `/api/instances/{id}` | 删除实例 |
| GET | `/api/instances/{id}/status` | 获取实例最新状态 |
| GET | `/api/instances/{id}/history` | 获取实例历史状态 |

#### 注册实例

```json
POST /api/servers/1/instances
{
  "name": "OCR #1",
  "service_type": "dotnet-ocr",
  "base_url": "http://192.168.1.10:21600",
  "poll_interval_secs": 10
}
```

支持的 `service_type`: `dotnet-ocr`, `cpp-ocr`, `rust-ocr`

### Dashboard

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard` | 获取按服务器组分组的仪表盘数据 |

```json
{
  "total_servers": 2,
  "total_instances": 5,
  "healthy_instances": 4,
  "busy_instances": 1,
  "unavailable_instances": 0,
  "servers": [...]
}
```

## OCR 服务器端变更

三个 OCR 服务器（.NET、C++、Rust）的 `/api/health` 和 `/api/status` 端点新增可选字段 `serverName`。

### .NET OCR Server

配置方式 (`appsettings.json`):
```json
{
  "OcrServer": {
    "ServerName": "主校区生产服务器"
  }
}
```

响应示例:
```json
{
  "status": "healthy",
  "modelsLoaded": true,
  "poolSize": 4,
  "serverName": "主校区生产服务器"
}
```

### C++ OCR Server

`ServerConfig` 新增 `server_name` 字段，通过命令行参数或配置传入。

### Rust OCR Server

新增 CLI 参数 `--server-name`:
```bash
shmtu-ocr-server --server-name "主校区Rust服务器"
```

## 部署

### Docker Compose 示例

```yaml
version: '3'
services:
  monitor:
    build: ./shmtu-service-monitor
    ports:
      - "3100:3100"
    environment:
      - MONITOR_PORT=3100
      - DATABASE_URL=sqlite:shmtu_monitor.db?mode=rwc
      - POLL_INTERVAL_SECS=10

  ocr-dotnet:
    build: ./shmtu-cas-ocr-server
    environment:
      - OcrServer__ServerName=生产OCR集群-Node1

  ocr-cpp:
    build: ./shmtu-cas-ocr-server/cpp
    command: ./shmtu-cas-ocr-server --server-name "生产OCR集群-Node2"

  ocr-rust:
    build: ./shmtu-cas-rs/ocr/shmtu-ocr-server
    command: ./shmtu-ocr-server --server-name "生产OCR集群-Node3"
```

### 注册监控

启动 monitor 后，通过 API 注册服务器组和实例：

```bash
# 1. 创建服务器组
curl -X POST http://localhost:3100/api/servers \
  -H "Content-Type: application/json" \
  -d '{"name": "生产环境 OCR 集群", "description": "主校区服务器"}'

# 2. 注册实例（假设服务器组 ID 为 1）
curl -X POST http://localhost:3100/api/servers/1/instances \
  -H "Content-Type: application/json" \
  -d '{"name": "OCR #1", "service_type": "dotnet-ocr", "base_url": "http://ocr-dotnet:21600"}'

curl -X POST http://localhost:3100/api/servers/1/instances \
  -H "Content-Type: application/json" \
  -d '{"name": "OCR #2", "service_type": "cpp-ocr", "base_url": "http://ocr-cpp:21600"}'

# 3. 查看仪表盘
curl http://localhost:3100/api/dashboard
```

## 前端路由

| 路径 | 页面 |
|------|------|
| `/` | Dashboard（按服务器组展示） |
| `/servers` | 服务器组管理（CRUD + 展开查看实例） |
| `/servers/:id` | 服务器组详情（实例卡片列表） |
| `/instances/:id` | 实例详情（状态 + 时间线图表） |
