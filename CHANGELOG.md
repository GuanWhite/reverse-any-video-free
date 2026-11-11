# Changelog

本项目使用语义化版本。`MAJOR` = 工作流/契约不兼容变更；`MINOR` = 新增免费能力或参考文档；`PATCH` = 脚本修复与文档修订。与上游 `main` 分支不联动，每次同步上游都会在此记录新的 blob SHA。

## 1.0.0 — 2026-11-11

首个独立、无 Pro 依赖的蒸馏版本。

**蒸馏基线**

- 上游 `heygen-com/hyperframes` `main` 分支，SKILL.md blob `ad95dd9d8dae854f2ebd01ab6573d55e1d52daf2`（5,289 bytes），references 同一分支快照。
- 上游许可证 Apache-2.0，LICENSE 原文副本 10,763 bytes。

**新增**

- `SKILL.md`：零账号承诺、三条铁律、明确的 Pro 命令禁止清单、三阶段工作流与参考路由。
- `scripts/`：`hf_free.py`（公共库）、`probe.py`、`cuts.py`、`frames.py`、`diff.py`、`doctor.py`、`selftest.py`。
  - 逐帧 MAD + 自适应局部基线的切点检测，含跳切/推近的低置信提示；
  - 连续帧导出、ROI 字幕带事件、帧号→时间向下截断；
  - ffmpeg PSNR/SSIM、切点比对、音画偏移估计、内容缺失段、最差帧并排图与 Markdown 报告。
- `references/`：measurement / rebuild / composition / verification 四份自包含参考。
- `docs/`：DEPENDENCIES、LIMITATIONS、PRO_REMOVAL、DIFF_FROM_UPSTREAM。
- `README.md`、`NOTICE`、`LICENSE`、`examples/minimal-project/`。

**移除**

- `reverse start` 门禁与 probe、`billing`、`auth`、credit 限额、`--plan` / `--max-credits`、`events` 遥测、`cloud render`。
- `measure cuts/frames/events/face`、`hyperframes diff`、`diff --sbs`（改为本地脚本）。
- HeyGen 生成式人像重拍与动画整镜生成（改为裁切降级并明确标注能力损失）。
- 对 `/hyperframes`、`/hyperframes-cli`、`/media-use` 等 skill 的加载依赖。

**保留**

- 帧级测量口径、分层重建策略、墨迹框/字幕带/背板/运动模糊等匹配方法与全部 CSS/SVG 配方。
- 原音轨整条直挂、绝不整帧播放原片、单 Agent 通读、"修一轮再停"、状态文件中"命令是笔记不是脚本"。
- 上游合规条款：只复刻有权使用的视频。

**验证**

- `python scripts/selftest.py`：11/11 通过，全程离线。合成片 320×180@30fps/180 帧，切点真值帧 60/120 均被检出；同片 diff 漏切 0、多切 0、PSNR `inf`、SSIM `1.0`。
- `python scripts/doctor.py`：必需依赖全部 OK，`account_required: false`、`network_required: false`。
