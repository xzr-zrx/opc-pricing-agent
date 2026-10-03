# OPC 竞品监测与智能定价决策 Agent

FastAPI + SQLite + APScheduler + Vue 3。支持本地直接运行和 Docker Compose。

## 福闽AI配置

当前 LLM Gateway 使用 OpenAI-compatible Chat Completions：

- Base URL: `https://fumin.ai/v1`
- 实际请求: `https://fumin.ai/v1/chat/completions`

`.env` 中不要把 `LLM_BASE_URL` 写成完整 `/v1/responses` 或 `/v1/chat/completions`，因为 Gateway 会自动拼接 `/chat/completions`。

复制配置：

```bash
cd backend
cp .env.example .env
```

然后编辑 `.env`：

```env
LLM_BASE_URL=https://fumin.ai/v1
LLM_API_KEY=你的密钥
LLM_MODEL=你在福闽AI模型广场选择的模型ID
LLM_NATIVE_TOOL_CALLING=true
DEMO_FALLBACK_ENABLED=false
```

首次联调建议把 `DEMO_FALLBACK_ENABLED=false`，这样中转 API 出错时不会被 Demo fallback 掩盖。联调成功、准备比赛演示时可改回 `true`。


## Windows 下先单独测试福闽AI

在项目根目录 PowerShell 中执行：

```powershell
$env:FUMIN_API_KEY="你的密钥"
$env:FUMIN_MODEL="你的模型ID"
.\scripts\test-fumin.ps1
```

看到 `HTTP 调用成功` 和模型回复后，再启动本项目。脚本不会把 Key 写入文件。

## 方案 A：VS Code 直接运行（推荐开发时用）

### 后端

```bash
cd backend
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/docs`。

### 前端

另开 VS Code 终端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://127.0.0.1:5173`。

前端开发服务器会把 `/api` 代理到 `127.0.0.1:8000`。

## 方案 B：Docker Compose 本地一键启动

先确保 `backend/.env` 已配置，然后在项目根目录：

```bash
docker compose up -d --build
```

- Web: `http://127.0.0.1:8080`
- API docs: `http://127.0.0.1:8000/docs`

查看日志：

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

停止：

```bash
docker compose down
```

SQLite 数据位于 Docker named volume `opc_data`，普通 `down` 不会删除；`docker compose down -v` 会删除数据库，请谨慎。

## 演示流程

1. 点击“测试 LLM”，先确认真实中转 API 可用。
2. 点击“初始化 Demo 数据”。
3. 点击“推进 Mock 场景”，竞品 A 从 59 元降至 49 元。
4. 点击“立即分析”。
5. 查看建议、证据、风险和 Agent Run 工具调用时间线。

## 测试

```bash
cd backend
python -m pytest -q
```

## 服务器部署（Docker）

Ubuntu 示例：

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git nginx
sudo systemctl enable --now docker nginx
```

把项目上传到服务器，例如 `/opt/opc-pricing-agent`，创建并编辑 `backend/.env`，然后：

```bash
cd /opt/opc-pricing-agent
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs -f backend
```

临时可用 `http://服务器IP:8080` 访问（需云安全组/防火墙放行 TCP 8080）。

正式使用域名时，推荐宿主机 Nginx 反向代理到 `127.0.0.1:8080`。示例见 `deploy/nginx-opc.conf.example`，并用 Certbot 配 HTTPS。
