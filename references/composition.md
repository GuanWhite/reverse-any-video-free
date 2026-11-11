# 可编辑 HTML 时间轴工程

产出物必须是一个**可编辑、可 seek 的 HTML 工程**，而不是一个铺了原片背景的 mp4。下面的契约摘要改编自 HyperFrames 开源 `hyperframes/SKILL.md`（Apache-2.0），本 skill 自带，不要求安装或加载上游 skill。完整示例见 `examples/minimal-project/`。

## 目录形状

```
project/
├── index.html            # 根合成：只放场景宿主、媒体与音频
├── compositions/         # 一个场景一个子合成，短可读 id
├── assets/
│   ├── source.mp4        # 原片原样拷贝（音轨来源）
│   ├── cut_00060.png     # 从原帧按框裁出的子素材
│   └── fonts/            # 非内置字体放这里并写 @font-face
├── probe.json / cuts.json / frames/ / report/
└── REVERSE_FREE.md
```

## 根合成

```html
<div id="root" data-composition-id="root"
     data-width="1920" data-height="1080"
     data-fps="30000/1001" data-duration="12.345678">
  <audio id="source-audio" src="assets/source.mp4" data-start="0" data-duration="12.345678"></audio>
  <!-- 每个镜头一个子合成宿主 -->
</div>
```

- `data-width` / `data-height` / `data-fps` / `data-duration` 全部取自 `probe.json`。
- `data-duration = frames / fps`，不是音频长度。
- 分数帧率写分数，不要写小数。

## 契约要点（12 条摘要）

1. 每个定时元素有 `class="clip"`、`data-start`、`data-duration`（秒），只在 `[start, start+duration)` 显示；结束态落在其结束前。`data-track-index` 只是编辑器的轨道，绘制顺序看 `z-index`。
2. 片长取根合成的 `data-duration`：超出被截，提前结束会定格最后一帧。
3. 每个子合成构建一条**暂停的** timeline，并在 tween 注册完之后写入 `window.__timelines["<data-composition-id>"] = tl`。
4. 禁止 `Date.now()`、未设种子的 `Math.random()`、网络请求、定时器、`repeat: -1`。画面只能是 timeline 时间的函数。
5. 不要对 `.clip` 直接 tween `display` / `visibility` / `autoAlpha`；动画放在子元素上。
6. 不要在被 GSAP 变换的元素上写 CSS `transform`；动 transform，不动 `left/top/width/height`。
7. 不调用 `play()` / `pause()` / 媒体 seek。`<video>` 保留声音才标 `data-has-audio="true"`，否则一律 `muted`。
8. 每个 `<audio>` 必须有 `id`，否则不进混音。媒体上不要加 `crossorigin`。时间打在 `<video>` 上，不打在它的容器上。
9. 只有内置字体能按名字解析；其他字体要用 `@font-face` 指向 `assets/fonts/` 里的文件。
10. 资源路径写 `assets/...`，不带前导 `/`，子合成里也一样。
11. 对素材的调色、颗粒、模糊、暗角走本地处理（ffmpeg / `media-treatment`），不要用 CSS filter 冒充。
12. 场景文件把样式、标记、脚本放在 `<template>` 内，根元素样式化为 `#root`。

## 可编辑性

- 一场景一子合成，id 短且可读；根文件只放宿主、媒体、音频。
- 定时元素**写在 HTML 里**，不由脚本动态生成，每个有稳定 `id`。
- 文案、品牌色、可替换素材做成变量（`data-var-text`、`data-var-src`、`var(--id)`）。
- 一类元素一条轨道：`data-track-kind="graphics"`，所有字幕组放同一个 `captions` 宿主。
- 内容落在 90% 动作安全框内，字幕与关键文字在 80% 字幕安全框内。

## 音轨直挂

原片原样拷入 `assets/source.mp4`，用一条 `<audio src="assets/source.mp4">` 覆盖全片；所有重建的画面 clip 与裁切片段静音。这样音画天然对齐，也让 `diff.py` 的音画偏移估计有稳定基准。

如果渲染器不接受"用 mp4 当 audio 源"，退路是**无损抽取**（`ffmpeg -i source.mp4 -vn -c:a copy assets/source_audio.m4a`）并保留原始时间基；仍不要重编码。取舍写进 `REVERSE_FREE.md`。

## 免费渲染路径（均无需账号）

**A · HyperFrames 开源 CLI（推荐）** — 免费、本地、无登录：

```bash
npx hyperframes check --json                      # 可选：结构/布局/对比度检查
npx hyperframes render --quality looks -o out.mp4  # 本地 headless Chrome + ffmpeg
npx hyperframes preview                           # 交给使用者继续编辑
```

需要 Node.js 22+ 与本机 Chrome/Chromium；这是 README 明确说明的开源免费用法，不是 Pro 功能。只要不调用 `cloud render`、`auth`、`billing`，就不产生账号依赖。

**B · 任意 HTML→视频渲染器** — 不装 HyperFrames 时：用 Puppeteer / Playwright 打开 `index.html`，按帧号 seek 到每条 `window.__timelines[...]` 的对应时间，逐帧截图，再交给 ffmpeg 编码：

```bash
ffmpeg -framerate 30000/1001 -i frames/%06d.png -i assets/source.mp4 -map 0:v -map 1:a -c:a copy -c:v libx264 -pix_fmt yuv420p out.mp4
```

注意 seek 必须由时间驱动、每帧可重复，不能依赖真实时间或 `requestAnimationFrame`。渲染器是**可替换环节**：本 skill 的独立性体现在测量、重建规范与验收三段，任何能确定性渲染 HTML 时间轴的免费工具都能接上。

## 验收输入

渲染完成后把 `out.mp4` 交给 `scripts/diff.py`（见 `references/verification.md`）。若两个视频尺寸或帧率不同，先按 `probe.json` 对齐再比，`diff.py` 会把差异写进报告而不是静默通过。
