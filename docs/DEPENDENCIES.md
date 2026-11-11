# 依赖与权限清单

**一句话：账号 0 个、token 0 个、网络请求 0 个、遥测 0 条、付费命令 0 条。** 加载本 skill 只需要把目录放进 Agent 的 skills 目录；运行工具链只需要本机 Python 与 ffmpeg。

## 1. 必需依赖

| 依赖 | 最低版本 | 用途 | 是否联网 | 是否需账号 |
| --- | --- | --- | --- | --- |
| Python | 3.10+（`scripts/` 用标准库 + 类型注解） | 全部测量与验收脚本 | 否 | 否 |
| ffmpeg | 4.x+（本机验证 7.1） | 解码、逐帧 rawvideo、PNG 导出、PSNR/SSIM、编码 | 否 | 否 |
| 一个可读写的本地目录 | — | 工程、`report/`、JSON/PNG 输出 | 否 | 否 |

**可选增强（缺失不影响核心链路）**

| 依赖 | 用途 | 缺失时 |
| --- | --- | --- |
| ffprobe | 精确读取 `nb_frames` / `r_frame_rate` | `probe.py` 自动改用 `ffmpeg -i ... -f null -` 解析流信息并数帧，`frames_source` 会标记来源 |
| Pillow | contact sheet、最差帧并排图、RGB 帧导出 | `frames.py` 回落到 ffmpeg 导出 PNG；`diff.py` 保留两侧独立 PNG，报告注明无并排图 |
| `imageio-ffmpeg`（Python 包） | 当系统 PATH 没有 ffmpeg 时提供自带二进制 | 只是 ffmpeg 的一种发现途径，不是独立依赖 |
| HyperFrames 开源 CLI（Node.js 22+ / Chrome） | 本地 `render` / `check` / `preview` / `snapshot` / `transcribe` / `remove-background` | 用 `references/composition.md` 的 B 路径（任意 HTML→视频渲染器 + ffmpeg） |
| GSAP 或其它 seekable 动画库 | 工程里的 timeline | 使用者自行选择；离线时把库文件放进 `assets/`，不要引 CDN |

> 本 skill **不自动安装、不自动下载**任何依赖或二进制。缺 ffmpeg 时 `doctor.py` 给出指引后停止。

## 2. 明确不需要 / 明确禁止

| 类别 | 内容 |
| --- | --- |
| 账号 | HyperFrames Pro、HeyGen 账号、任何 API Key、任何登录态 |
| 计费 | 订阅、credits、add-on credits、`billing`、`--plan` 估价、`--max-credits` |
| 网络 | 云端渲染、模型生成、素材目录搜索、遥测上报、字体/库 CDN |
| 命令 | `reverse start`、`measure *`、`hyperframes diff`、`cloud render`、`media-use generate/resolve`、`auth *`、`events`、`usage` |

完整逐条对照见 `PRO_REMOVAL.md`。

## 3. 二进制发现顺序（`hf_free.py`）

`find_binary()` 只查本机，从不联网：

1. 环境变量 `FFMPEG_BINARY` / `FFPROBE_BINARY`（绝对路径）；
2. `PATH` 中的 `ffmpeg` / `ffprobe`；
3. `imageio_ffmpeg.get_ffmpeg_exe()`（仅 ffmpeg）；
4. 常见本地位置：`~/.workbuddy/binaries/ffmpeg/`、`~/scoop/apps/ffmpeg/current/bin/`、WinGet Links、`/usr/local/bin`、`/usr/bin`、`/opt/homebrew/bin`、`C:/Program Files/ffmpeg/bin/`。

```bash
export FFMPEG_BINARY=/absolute/path/to/ffmpeg      # 自定义位置
export FFPROBE_BINARY=/absolute/path/to/ffprobe
python scripts/doctor.py --json
```

## 4. 权限清单

| 权限 | 范围 | 说明 |
| --- | --- | --- |
| 文件读取 | 使用者指定的源视频、本工程目录 | 不扫描、不遍历其它目录；不读取任何凭据文件 |
| 文件写入 | 工程目录、`report/`、传入的 `--out` 路径 | 不写系统目录、不写入 home 下的配置 |
| 子进程 | 仅本机 `ffmpeg` / `ffprobe`，以及可选的用户显式选择的免费渲染器 | 不执行 shell 字符串，全部用参数数组调用；不调用 `npx` 除非使用者按文档自行执行 |
| 网络 | **无** | 脚本中不出现任何 socket / HTTP / 下载调用 |
| 凭据 | **无** | 不读取环境变量中的 token，不访问钥匙串，不写 `.env` |
| 遥测 / 统计 | **无** | 没有 usage beacon，没有 events 上报 |
| 系统修改 | 无注册表、无服务、无开机项、无全局安装 | `py_compile` 产生的 `__pycache__` 仅在本目录 |

`doctor.py --json` 会在 `permissions` 字段里输出同一份清单，便于其它 Agent 在加载时自检。

## 5. 安装与自检

```bash
# 1. 放进任意 Agent 的 skills 目录（示例）
cp -r reverse-any-video-free ~/.workbuddy/skills/

# 2. 依赖自检
python scripts/doctor.py

# 3. 全链路离线自测（生成合成视频，约数秒）
python scripts/selftest.py
```

`selftest.py` 不下载任何素材：用 ffmpeg lavfi 生成 6 秒 320×180@30fps、含两个硬切（帧 60/120）与正弦音轨的测试片，然后跑 doctor → probe → cuts → frames → diff 并断言结果。发布基线为 **11/11 通过**。

## 6. 各平台提示

- **Windows**：ffmpeg 常不在 PATH；脚本会自动查 `~/.workbuddy/binaries/ffmpeg/`，也可设 `FFMPEG_BINARY`。路径中的盘符冒号已在 ffmpeg filtergraph 中规避（`stats_file` 使用相对名 + `cwd`）。
- **macOS / Linux**：`brew install ffmpeg` 或直接设环境变量；无需 sudo 安装到系统目录也能工作。
- **无 Chrome 环境**：仍可完成测量、重建规范与工程产出；渲染按 `composition.md` B 路径自行接一个免费渲染器。
