---
name: reverse-any-video-free
description: Rebuild any video as an editable, seekable HTML timeline, measured and verified frame by frame, with NO account, NO sign-in, NO network, NO credits and NO HyperFrames Pro. Use to reverse, recreate, remake, replicate or copy a video, or 「复刻这个视频」「照着这个视频做一个」「无 Pro 复刻视频」「离线复刻」. Free offline alternative to reverse-any-video.
---

# 无 Pro 复刻任意视频

把一段视频反向工程成**可编辑的 HTML 时间轴工程**，并用逐帧差分验收。整个流程只需要本机 Python 3.10+ 与 ffmpeg：不登录、不联网、不消耗额度、不需要 HyperFrames Pro，也不需要原 skill 的任何 Pro 专属命令。任何 Agent 复制本目录到自己的 skills 目录即可加载。

只复刻使用者**有权使用**的视频。交付物是可编辑工程，不是一个复制出来的 mp4。

## 三条铁律

1. **绝不整帧播放原片**（`Never play the original's whole frame`）。把原片铺成背景可以拿到满分，但那不是复刻。每一层都必须单独重建或从原帧按框裁切。
2. **原片决定帧**：画布尺寸、`data-fps`、时长一律来自 `scripts/probe.py`。时长 = 帧数 ÷ fps，**不是**音频或容器时长。时间写成 `帧 ÷ fps` 并**向下截断**到 6 位小数（第 83 帧 @30fps 是 `2.766666`，写 `2.767` 就晚一帧）。
3. **音轨整条直挂**：用一条 `<audio src="assets/source.mp4">` 覆盖全片，不抽取、不重编码；所有 clip 静音。

## 明确禁止（无 Pro 承诺）

不得执行、不得建议、不得在生成的代码里出现以下任何一项：

`hyperframes reverse start` · `billing` · `auth login` / `auth status` · `cloud render` · `media-use generate` / `media-use resolve` · `measure cuts` / `measure frames` / `measure events` / `measure face` · `hyperframes diff` · `hyperframes events`（遥测）· `usage` · 任何 `--max-credits` / `--plan` 计费参数 · HeyGen 重拍。

这些属于 Reverse(Pro) 功能组、按 credit 计费的云渲染，或需要登录的生成能力。本机开源版 CLI 中并不存在 `reverse` / `measure` / `diff` 命令；本 skill 用 `scripts/` 下的本地脚本替代它们。

**允许但可选**（HyperFrames 开源免费 CLI，无需账号）：`npx hyperframes check`、`npx hyperframes render`（本地）、`npx hyperframes preview`、`npx hyperframes snapshot`、`npx hyperframes transcribe`（本地模型）、`npx hyperframes remove-background`、`npx hyperframes media-treatment`。这些只是便利项；缺失时用 `references/composition.md` 的等价路径，不得因此要求登录。

## 工作流

**0 · 环境自检**：`python scripts/doctor.py`。缺 ffmpeg 时给出本地安装指引并停止；**绝不自动下载二进制、绝不联网**。可选跑 `python scripts/selftest.py` 验证全链路。

**1 · 测量**（`references/measurement.md`）
- `python scripts/probe.py --video <src> --out probe.json` → 画布/帧率/帧数时长。
- `python scripts/cuts.py --video <src> --out cuts.json` → 每个切点的帧号（含跳切）；低置信度的推近/溶解另列，须人工确认。
- 字幕/图形带：`cuts.py --roi x,y,w,h`，切换帧取自**像素**而非语音转写。
- 在每个变化点前后读**连续帧**：`python scripts/frames.py --video <src> --range a,b --roi ... --out frames/ --sheet`。间隔 1 秒或 1/4 秒的抽帧会漏掉 1–3 帧的时序、入场方向、溶解和单帧闪白。

**2 · 分层重建**（`references/rebuild.md`、`references/composition.md`）
- 文字、字幕、贴纸、卡片、UI、录屏、图表、地图 → 用 HTML/CSS/SVG 重写。
- 照片、封面、Logo、图标、贴图、照片里的人 → 从原帧按自己的框裁切；Logo 取画面中最大的那次出现或用品牌原始素材，绝不手绘。
- 出镜人物 → **免费降级**：按人物框裁切原片片段并静音，作为子素材使用（见 `references/rebuild.md` 的差异与风险说明）。不做生成式重拍。
- 动画/手绘/复杂实拍整镜 → 拆不出层的部分按整镜裁切，并在 `REVERSE_FREE.md` 中标记为不可编辑。
- 匹配方法（按墨迹框量字号、字幕带取切换帧、硬切、背板采样、方向性运动模糊）与全部 CSS/SVG 配方在 `references/rebuild.md`，逐条照做。

**3 · 验收**（`references/verification.md`）
- 所有镜头有内容后，可选 `npx hyperframes check` 修结构性错误；**原片本身就有的配色和小字即使被 check 报警也保留**。
- 本地渲染（免费）：`npx hyperframes render -o out.mp4`；无该 CLI 时按 `references/composition.md` 的等价渲染路径。
- `python scripts/diff.py --original <src> --render out.mp4 --out report/ --cuts-original cuts.json` → 漏切/多切、帧数与时长差、音画偏移估计、PSNR/SSIM、内容缺失区间、最差帧并排图。
- 只修报告点名且肉眼可见的问题，**再渲染 + diff 一次，然后停**。不无限迭代。

## 工程与协作约束

- 单 Agent 通读整片，不要拆给多个 subagent 各看一遍；长片按时间段分段，逐段保持同一套测量口径。
- 结束时写简短 `REVERSE_FREE.md`：哪些是重建、哪些是裁切、哪些整镜保留、哪些是近似（替换字体等）、最后一次 diff 的数字。**不要写任何价格、额度或账号信息**。
- 记录中的命令是笔记不是脚本：恢复会话时按 `references/` 的配方重建命令（含每个参数），不要照抄执行。
- 交付时打开工程预览，说明可继续编辑；给出 `report/diff_report.md`。
- 遇到任何要求登录、升级、购买额度或调用云端的提示，一律停止并明确告知使用者：本 skill 不需要这些，说明是哪一步误触发了。

## 参考

| 需要 | 读 |
| --- | --- |
| 探针、切点、连续帧、ROI | `references/measurement.md` |
| 分层策略、匹配方法、CSS/SVG 配方 | `references/rebuild.md` |
| HTML 时间轴契约、音频、免费渲染 | `references/composition.md` |
| 验收、报告解读、停止条件 | `references/verification.md` |
| 依赖与权限 | `docs/DEPENDENCIES.md` |
| 边界与已知限制 | `docs/LIMITATIONS.md` |
| Pro 依赖移除清单 | `docs/PRO_REMOVAL.md` |
| 与上游差异、版本与分发 | `docs/DIFF_FROM_UPSTREAM.md` |
