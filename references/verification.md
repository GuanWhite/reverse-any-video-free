# 验收：渲染 → 逐帧 diff → 一轮修复

上游用 `hyperframes check` → `cloud render`（按 credit 计费）→ `hyperframes diff`（Reverse 功能组）。本 skill 改为**本地渲染 + `scripts/diff.py`**，等价输出仍然包含漏切/多切、时长、音画偏移、内容缺失区间与最差帧并排图。

## 1. 建造中：免渲染抽查

```bash
python scripts/frames.py --video source.mp4 --range 58,64 --out frames/cut60 --sheet
```

把自建帧与原帧按同一帧号并排看。也可在装了开源 CLI 时用 `npx hyperframes snapshot --at t,t,…` 看工程帧。这个阶段不追求分数，只确认镜头骨架和入场方向没错。

## 2. 结构检查（可选，免费）

```bash
npx hyperframes check --json
```

修掉结构性错误；但**原片本身就有的配色、极小的字、故意的低对比，即使被 check 报警也保留** —— 目标是复刻原片，不是通过通用设计规范。没有这个 CLI 时按 `references/composition.md` 的 12 条契约自查。

## 3. 本地渲染（免费，无账号）

```bash
npx hyperframes render --quality looks -o out.mp4
```

- 只走**本地** `render`；分数帧率、非 16:9 / 9:16 / 1:1 的画面、云端渲染失败等情况在上游会触发回落逻辑，这里本来就只有本地一条路，无需回落。
- 渲染是耗时步骤：短视频前台跑；长片用 `references/composition.md` 的 B 路径逐段渲染，或把命令放到后台并把日志留在本项目目录，不要静默吞掉失败。
- 渲染后确认文件非空、`probe.py` 读出的尺寸/帧率/帧数与 `probe.json` 一致，再抽几帧解码看一眼。

## 4. 逐帧 diff

```bash
python scripts/diff.py --original source.mp4 --render out.mp4 --out report/ --cuts-original cuts.json
```

产出：

| 文件 | 内容 |
| --- | --- |
| `report/diff.json` | 机器可读全量结果 |
| `report/diff_report.md` | 人读报告：汇总表、切点、最差帧表 |
| `report/sbs_XXXXXX.png` | 最差帧并排图（原片 \| 你的），需 Pillow |
| `report/original/`、`report/yours/` | 最差帧的原始 PNG |

`diff.py` 的检查项：

- **画布 / fps / 帧数 / 时长**：两个 probe 全字段对比，`duration` 一律按 `frames / fps` 计算；
- **切点**：对渲染结果重新跑一次切点检测，与原片以 ±1 帧容差比对，输出 `missing_cuts` / `extra_cuts` / `matched`；
- **逐帧 PSNR / SSIM**：ffmpeg `psnr` / `ssim` 滤镜，按帧序号对齐（不依赖容器时间戳）；同片比对应得到 `inf` 与 `1.0`；
- **内容缺失区间**：连续低于 22 dB 的帧段；
- **音画偏移**：100 Hz 响度包络互相关，±2 秒、10 ms 分辨率；
- **最差时刻**：默认 5 帧，导出两侧帧并拼成并排图。

不传 `--cuts-original` 时脚本会自动对两边各跑一次切点检测；复用已有的 `cuts.json` 更快也更一致。`--no-audio-offset` 可跳过音频估计，`--worst N` 控制导出帧数。

## 5. 怎么读报告、什么时候停

**只修报告点名、并且肉眼能看出的问题**：缺的切点或元素、错的时间、错的尺寸/字重/颜色。不要为了把 PSNR 从 38 抬到 40 去改原片本来就有的颗粒或压缩噪声 —— 像素指标对颗粒和替换字体天然不友好。

修完 → 再渲染一次 → 再 `diff.py` 一次 → **然后停**。上游明确要求"Render and diff once more, then stop"，本 skill 沿用：无限迭代既不会收敛，也会掩盖真正的时间错误。最后一次的数字写进 `REVERSE_FREE.md`。

## 6. 交付

```bash
npx hyperframes preview     # 可选，免费；让使用者在编辑器里继续改
```

- 打开并排图与 `report/diff_report.md`，说明哪些是近似；
- 打开工程预览，说明可继续编辑；
- 写 `REVERSE_FREE.md`：重建/裁切/整镜保留各有哪些、替换字体等近似项、最后一次 diff 的关键数字；
- 文件里**不写**价格、额度、账号或登录信息；
- 记录里的命令是笔记不是脚本：恢复会话时按配方重建（含每个参数），不要照抄执行。

## 已知判定偏差

| 情况 | 报告会怎样 | 该怎么判断 |
| --- | --- | --- |
| 原片有颗粒 / 强压缩 | PSNR、SSIM 偏低 | 看观感，不追像素分数 |
| 替换了字体 | 文字区域分数明显低 | 按墨迹框复核后记为近似 |
| 溶解 / 甩镜 | 可能多报一个切点 | 用 `frames.py` 读连续帧确认 |
| 音轨被重编码过 | offset 出现非 0 | 先改回音轨直挂，再判断画面 |
| VFR 或帧率不一致 | 帧数 / 时长差异常 | 先转 CFR 并按 `probe.json` 对齐 |
