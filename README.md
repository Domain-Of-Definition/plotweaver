# PlotWeaver

PlotWeaver 是一款 AI 小说转剧本工具，面向中文多章节小说改编场景。系统支持上传包含 3 章以上内容的 TXT/DOCX/EPUB 小说文本，并通过 AI 管线生成结构化 ScreenYAML 剧本和可导出的中文剧本文本。

## 功能范围

- 支持 TXT、DOCX、EPUB 单文件上传。
- 系统要求输入小说至少包含 3 个章节。
- PDF/OCR 不在 v1 范围内，上传 PDF 会提示先转换为 TXT/DOCX/EPUB。
- 按章节调用大模型，按场景通过 SSE 流式输出进度和预览片段。
- 输出 ScreenYAML v2.3，可用于编辑、校验和下载。
- 输出中文剧本预览，支持黑底/白底主题切换。
- 支持导出 YAML 和 TXT 剧本文本。
- 生成过程中可以停止输出，页面会保留已生成结果。

## 技术栈与依赖

- 前端：React、Vite、TypeScript、Lucide React
- 后端：FastAPI、Pydantic v2、PyYAML、python-docx、python-multipart
- EPUB 解析：EbookLib、BeautifulSoup
- AI：OpenAI-compatible Chat Completions API

## 项目结构

```text
backend/
  app/
    chapter_parser.py      # 上传解析与章节识别
    config.py              # 环境变量配置
    converter.py           # 按章转换与 SSE 输出
    draft_adapter.py       # LLM 草稿结构兼容适配
    llm_client.py          # OpenAI-compatible 客户端
    main.py                # FastAPI 入口
    models.py              # ScreenYAML 与 LLM Draft 模型
    normalizer.py          # 角色 ID 归一化与动作去主语
    prompt_templates.py    # 章节转换 Prompt
    sse.py                 # SSE 事件格式化
    validator.py           # ScreenYAML 校验
    yaml_service.py        # YAML / C-Fountain / TXT 渲染
  tests/
  .env.example
  requirements.txt

frontend/
  src/
    main.tsx
    styles.css

ScreenYAML-v2.3-schema.md
C-Fountain-v1-rendering.md
开发与测试流程.md
```

## API

- `GET /api/health`：后端健康检查。
- `POST /api/upload`：上传 TXT/DOCX/EPUB，返回文件格式、字数、章节数和章节标题。
- `POST /api/convert/stream`：上传 TXT/DOCX/EPUB，并通过 SSE 流式返回转换事件。
- `POST /api/validate-yaml`：校验 ScreenYAML 文本。

SSE 事件包括：

- `progress`
- `chapter_started`
- `scene_completed`
- `validation_result`
- `final_yaml`
- `error`
- `done`

## 环境变量

复制示例文件并填写密钥：

```powershell
Copy-Item backend\.env.example backend\.env
```

关键变量：

```text
OPENAI_API_KEY=你的模型接口密钥
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.2
OPENAI_RESPONSE_FORMAT=json_object
FRONTEND_ORIGIN=http://localhost:5173
```

如果你的模型服务不支持 `response_format={"type":"json_object"}`，请设置：

```text
OPENAI_RESPONSE_FORMAT=none
```

## 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

后端默认地址：

```text
http://localhost:8000
```

健康检查：

```text
http://localhost:8000/api/health
```

## 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

## 验证命令

后端单元测试：

```powershell
cd backend
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m pytest -o cache_dir=$env:TEMP\plotweaver-pytest-cache tests
```

后端语法检查：

```powershell
python -m compileall backend\app
```

前端类型检查：

```powershell
cd frontend
npx tsc -b
```

前端构建：

```powershell
cd frontend
npm run build
```

如果 Windows 上出现 `spawn EPERM`，通常是 esbuild 子进程被权限策略或安全软件拦截。可以先确认 `npx tsc -b` 是否通过，再检查安全软件、目录权限或重新安装前端依赖。

## 交付文档

- [ScreenYAML v2.3 Schema 规范](./ScreenYAML-v2.3-schema.md)
- [C-Fountain v1 渲染与导出规则](./C-Fountain-v1-rendering.md)
- [开发与测试流程](./开发与测试流程.md)

## Demo 视频

https://www.bilibili.com/video/BV16DE46ZEX5/

## 截图展示

<img width="1887" height="901" alt="47C1D5D70EB69A138597884DB159672A" src="https://github.com/user-attachments/assets/c6cee6d3-f9a8-4bc7-8271-7402adb76c68" />

