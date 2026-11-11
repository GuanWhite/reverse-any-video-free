# examples

## minimal-project/index.html

一个**结构模板**，展示逆向工程应有的形状：根合成参数来自 `probe.json`、原音轨整条直挂、文字用 HTML 重建、Logo 按框裁切、每个元素有稳定 id 与精确帧时间、timeline 暂停且可 seek。

它**不含真实素材，不能单独渲染**。使用时：

1. 复制整个目录到你的工程目录；
2. 把原片原样复制成 `assets/source.mp4`；
3. 用 `scripts/probe.py` 的真实数值替换 `data-width` / `data-height` / `data-fps` / `data-duration`；
4. 用 `scripts/cuts.py` 的帧号替换各 clip 的 `data-start` / `data-duration`（`scripts/hf_free.py` 的 `frame_to_seconds()` 负责向下截断换算）；
5. 用 `scripts/frames.py` 裁出子素材放进 `assets/`；
6. 需要动画时把一个 seekable 动画库（如 GSAP）**本地**放进 `assets/`，不要用 CDN；
7. 按 `references/composition.md` 本地渲染，再用 `scripts/diff.py` 验收。

模板里刻意没有 `<video src="assets/source.mp4">` 全屏层 —— 那是 SKILL.md 的第一条铁律所禁止的。

## 想看可运行的验证

直接跑 `python scripts/selftest.py`：它用 ffmpeg lavfi 现场生成带两个硬切的合成视频，完整跑通 probe → cuts → frames → diff，不需要任何示例素材或网络。
