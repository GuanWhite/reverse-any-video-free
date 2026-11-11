# 测量：让原片决定每一帧

上游 `reverse-any-video` 的这四步由 `hyperframes reverse start`（Pro 门禁）与 `measure *`（Reverse 功能组）完成。本 skill 用 `scripts/` 下的本地脚本等价实现，全部免费、离线、无账号。

## 1. 探针 → 根合成参数

```bash
python scripts/probe.py --video input.mp4 --out probe.json
```

输出关键字段：

| 字段 | 含义 | 工程里的位置 |
| --- | --- | --- |
| `width` / `height` | 原片像素尺寸 | 根合成 `data-width` / `data-height` |
| `fps` | 精确分数，如 `30/1`、`30000/1001` | `data-fps`，**保留分数，不要四舍五入成 29.97** |
| `frames` | 视频帧数 | 时长计算的分子 |
| `duration_seconds` | `frames / fps` | `data-duration` |

**不要**用 `init` 的默认 1920×1080 / 30fps 画布，**不要**用容器时长或音频时长：音频常比画面长几十毫秒，多出的尾帧会让整片错位。VFR（可变帧率）源请先转成 CFR，`probe.py` 的帧数取自 `nb_frames`，无法取得时按容器时长估算并在 `frames_source` 中标明。

`probe.py` 只调用本机 `ffprobe` / `ffmpeg`；缺 ffprobe 时自动用 `ffmpeg -i ... -f null -` 解析流信息并数帧，功能降级但不失败。

## 2. 时间写法：帧 ÷ fps，向下截断

```bash
python -c "from scripts.hf_free import frame_to_seconds, fps_of; ..."   # 或直接读 cuts.json 的 time_seconds
```

`frame_to_seconds()` 用 `Decimal` 与 `ROUND_DOWN` 保留 6 位小数：

- 第 83 帧 @ 30fps → `2.766666` ✅
- `2.767` ❌ 会晚一帧

工程里优先存**帧号**，时间由帧号换算；`cuts.py` 同时给出 `frame`、`time_seconds`（截断值）和 `time_exact`（`83/(30/1)` 形式的精确分数）。

## 3. 切点

```bash
python scripts/cuts.py --video input.mp4 --out cuts.json
python scripts/cuts.py --video input.mp4 --out cuts_tuned.json --threshold 4.5 --min-abs 5 --score-curve curve.csv
```

原理：把每帧缩到 160×90 灰度，计算**全片逐帧平均绝对像素差**（MAD），再用局部中位数作自适应基线找峰值。

- 相比 ffmpeg 的 `select='gt(scene,x)'` 场景分，逐帧曲线能暴露**同一条 take 内的跳切与推近**；这正是上游强调 ffmpeg 会漏的部分。
- `--threshold` 是「峰值 / 局部基线」倍数（默认 6.0），`--min-abs` 过滤压缩噪声（默认 8.0）。渐变、缓慢推镜会抬高局部基线而不误报。
- `--min-gap 3` 合并相邻峰；`--score-curve` 导出完整曲线 CSV 供调参。
- `reframe_hints` 是 2–12 帧的连续变化**提示**（推近、甩镜、溶解），**不是切点**：必须用 `frames.py` 读连续帧人工确认，再决定是否作为镜头边界。
- `--range START,END` 只分析某段，输出帧号已换算回全局帧号。
- 每个镜头从列出的帧开始；`cuts.json` 中的 `frame` 是唯一权威时间依据。

**ROI / 字幕带事件**

```bash
python scripts/cuts.py --video input.mp4 --roi 0,720,1920,180 --out caption_events.json
```

`--roi x,y,w,h` 让差异只在指定框内计算。字幕的首帧与末帧取自**字幕带的像素**，不取语音转写时间：字幕常领先或滞后人声，ASR 还会听错专名。文字内容可以另用本地转写（可选 `npx hyperframes transcribe`），但切换时刻以像素为准；除非原片本身淡入淡出，否则一律硬切。

## 4. 连续帧

```bash
python scripts/frames.py --video input.mp4 --range 58,64 --out frames/cut60 --sheet
python scripts/frames.py --video input.mp4 --range 58,64 --roi 0,700,1920,200 --out frames/captions
```

对每个切点、入场、出场、转场，读**前后各几帧的连续帧**，而不是 1 秒或 1/4 秒间隔的抽帧表。稀疏抽帧必然漏掉：

- 1–3 帧的时序差；
- 元素从哪个方向进来、往哪个方向离开；
- 切点处的模糊、溶解、擦除；
- 只存在一帧的闪白。

`frames.py` 导出 PNG + `manifest.json`（每帧的帧号与截断时间），`--sheet` 额外生成 `contact_sheet.png`（需 Pillow；缺失时仍导出逐帧 PNG 并写清 `exporter`）。单次区间上限 600 帧，长片请分段读。

## 5. 每个大字，读它的一生

在 `references/rebuild.md` 之前，对一个大字从出现到消失取连续帧条带，看清楚：

1. 怎么来：pop / 缩放 / 淡入 / 打字 / 逐词 / 擦除；
2. 停留中怎么变：扫光方向与时长、光泽、计数器、变色；
3. 怎么走；
4. 放大到原尺寸后，字形由什么构成：实色 / 渐变 / 玻璃 / 描边 / 发光 / 镂空。

先看清，再写代码；不要凭第一印象补动画。

## 6. 声音

`init` 等价步骤是把原视频**原样复制**进工程 `assets/`（不转码、不改名），然后用一条 `<audio src="assets/source.mp4">` 覆盖全片，所有 `<video>` / clip 静音。不抽取、不重编码音轨是让 `diff.py` 的音画偏移可判读的前提。详见 `references/composition.md`。

## 常见坑

| 现象 | 原因 / 处理 |
| --- | --- |
| 切点整体差 1 帧 | 用了四舍五入的时间值；改用帧号与 `frame_to_seconds()` |
| 字幕早/晚半句 | 用了 ASR 时间戳；改用 `--roi` 的像素切换帧 |
| 检测出一堆假切点 | 片源有颗粒/强压缩噪声；降低 `--threshold` 前先提高 `--min-abs`，或对曲线做人工核对 |
| 漏掉跳切 | `--min-abs` 设太高；导出 `--score-curve` 看该帧的峰是否只是被阈值压住 |
| 分数帧率对不上 | 工程里 `data-fps` 写成了 `29.97`；必须写 `30000/1001` |
| 长片内存吃紧 | 用 `--range` 分段；脚本以流式读取，不会把整片读进内存 |
