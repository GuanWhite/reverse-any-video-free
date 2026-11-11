# reverse-any-video-free

**把任意视频反向工程成可编辑的 HTML 时间轴工程，并逐帧验收 —— 不登录、不联网、不花钱、不需要 HyperFrames Pro。**

这是 [`heygen-com/hyperframes` 的 `skills/reverse-any-video`](https://github.com/heygen-com/hyperframes/blob/main/skills/reverse-any-video/SKILL.md)（官方标注 **Pro**）的独立蒸馏版：保留它决定还原度的核心方法论，把所有账号、计费、云端与生成式依赖换成纯本地的 Python + ffmpeg 实现。任何 Agent 把这个目录放进自己的 skills 目录就能加载，无需任何授权。

> 非 HeyGen 官方项目，与 HeyGen / HyperFrames 无隶属或背书关系。上游以 Apache-2.0 发布，归属与改动见 `NOTICE`、`LICENSE`。

---

## 它保留什么、不做什么

**保留（核心能力）**

- 帧级测量口径：精确画布 / 分数帧率 / 帧数时长、含跳切与推近的切点、连续帧阅读、字幕带 ROI 事件；
- 分层重建：文字与图形用 HTML 重写、子素材按框裁切、原音轨整条直挂、**绝不整帧播放原片**；
- 匹配配方：按墨迹框量字号、像素取字幕切换帧、硬切、背板采样、方向性运动模糊、扫光/渐变/玻璃/描边等 CSS-SVG 配方；
- 量化验收闭环：本地渲染 → 漏切/多切、时长、音画偏移、PSNR/SSIM、内容缺失段、最差帧并排图 → 只修一轮再停；
- 产出**可编辑工程**，不是一个复制出来的 mp4。

**不做**

- 不重拍人脸、不去除原片烧录字、不生成原片没有的画面；
- 不调用 `cloud render`、不检查计划、不生成 `billing` 命令、不上报遥测；
- 不自动下载任何依赖，不读取任何凭据。

逐条对照见 `docs/PRO_REMOVAL.md`，限制见 `docs/LIMITATIONS.md`。

---

## 快速开始

前置：Python 3.10+、本机 ffmpeg（不在 PATH 也可以，脚本会自动找）。

```bash
# 0. 环境自检 + 全链路离线自测（不联网、不下载素材）
python scripts/doctor.py
python scripts/selftest.py

# 1. 测量
python scripts/probe.py --video input.mp4 --out probe.json
python scripts/cuts.py  --video input.mp4 --out cuts.json
python scripts/frames.py --video input.mp4 --range 58,64 --out frames/cut60 --sheet

# 2. 按 references/rebuild.md 与 references/composition.md 建 HTML 工程
#    本地免费渲染（二选一：开源 CLI 或任意 HTML→视频渲染器）
npx hyperframes render --quality looks -o out.mp4

# 3. 验收
python scripts/diff.py --original input.mp4 --render out.mp4 --out report/ --cuts-original cuts.json
#    → report/diff_report.md、report/diff.json、report/sbs_*.png
```

在 Agent 里使用：把本目录复制到 `<agent>/skills/reverse-any-video-free/`，然后说「复刻这个视频」或 `reverse this video`。`SKILL.md` 会自动路由到对应参考文档。

---

## 目录结构

```
reverse-any-video-free/
├── SKILL.md                     # 主文件：三条铁律、禁止清单、工作流、路由
├── README.md                    # 本文件
├── LICENSE                      # Apache-2.0 原文（上游副本）
├── NOTICE                       # 上游归属与改编声明
├── CHANGELOG.md                 # 版本记录
├── references/
│   ├── measurement.md           # 探针、切点、连续帧、ROI、时间换算、声音
│   ├── rebuild.md               # 分层策略 + 匹配方法 + CSS/SVG 配方
│   ├── composition.md           # HTML 时间轴契约、音轨直挂、免费渲染路径
│   └── verification.md          # 验收、报告解读、停止条件、交付
├── scripts/
│   ├── hf_free.py               # 公共库：二进制定位、probe、逐帧读取、峰值检测
│   ├── doctor.py                # 依赖与权限自检
│   ├── probe.py                 # 替代 reverse start 的 probe
│   ├── cuts.py                  # 替代 measure cuts / measure events
│   ├── frames.py                # 替代 measure frames
│   ├── diff.py                  # 替代 hyperframes diff
│   └── selftest.py              # 端到端离线自测
├── docs/
│   ├── DEPENDENCIES.md          # 依赖与权限清单
│   ├── LIMITATIONS.md           # 功能边界与已知限制
│   ├── PRO_REMOVAL.md           # Pro 依赖移除清单（逐条）
│   └── DIFF_FROM_UPSTREAM.md    # 与原 skill 差异、版本与分发信息
└── examples/
    └── minimal-project/         # 可编辑工程骨架模板
```

## 文档索引

| 想了解 | 读 |
| --- | --- |
| 怎么装、需要什么权限 | `docs/DEPENDENCIES.md` |
| 哪些能力被砍了、精度如何 | `docs/LIMITATIONS.md` |
| 每一项 Pro 依赖是怎么移除的 | `docs/PRO_REMOVAL.md` |
| 与上游差在哪、版本与分发方式 | `docs/DIFF_FROM_UPSTREAM.md` |
| 帧级测量的具体做法 | `references/measurement.md` |
| 分层重建与视觉配方 | `references/rebuild.md` |
| HTML 工程契约与渲染 | `references/composition.md` |
| 验收报告怎么看 | `references/verification.md` |

---

## 验证结果（发布基线）

在本机（Windows / Python 3.13.14 / ffmpeg 7.1 / ffprobe / Pillow）执行 `python scripts/selftest.py`，**11/11 通过，全程离线**：

| 检查 | 结果 |
| --- | --- |
| `doctor.py` 必需依赖 | PASS（账号 0、网络 0） |
| `probe.py` 参数精度 | 320×180、`30/1`、180 帧、6.0 s |
| `cuts.py` 切点检出 | 帧 **60** 与 **120**，与合成片真值一致 |
| `frames.py` 连续帧 | 7 帧 + manifest + contact sheet |
| `diff.py` 同片比对 | 漏切 0、多切 0、帧差 0、PSNR `inf`、SSIM `1.0` |
| Markdown 报告与并排图 | 生成成功 |

`doctor.py --json` 的 `account_required`、`network_required` 均为 `false`，`telemetry` 为 `none`。

---

## 版本与授权

- 版本 **1.0.0**，蒸馏基线为上游 `main` 分支 `SKILL.md` blob `ad95dd9d`（2026-11-11 抓取）；详情见 `docs/DIFF_FROM_UPSTREAM.md`。
- Apache License 2.0。改编自 `heygen-com/hyperframes`，保留 `LICENSE` 与 `NOTICE`。
- 合规：只复刻**有权使用**的视频；涉及真人肖像、第三方 Logo、音乐与字体时，授权由使用者负责。
