# Pro 依赖移除清单

逐条对照上游 `heygen-com/hyperframes` `main` 分支 `skills/reverse-any-video/`（SKILL.md blob `ad95dd9d`，5,289 bytes）及其 `references/`。**判定依据**：上游 SKILL.md 与 `references/start.md` 明确写出 "Reverse is a HyperFrames Pro feature"；`hyperframes-cli/references/cloud.md` 明确写出 `cloud render` 按 credit 计费；`media-use/SKILL.md` 的生成类能力列在 "HyperFrames credits" 列且需登录；本机已安装的开源 `hyperframes` 包 `dist/` 中检索不到 `reverse` / `measure` / `diff` 命令实现，说明它们属于 Reverse 功能组而非开源 CLI 通用命令。

| # | 上游依赖 | 位置 | 性质 | 本 skill 的处理 | 能力影响 |
| --- | --- | --- | --- | --- | --- |
| 1 | `npx hyperframes reverse start <video> --dir <project>` | SKILL.md §open | **Pro 门禁**，同时是唯一的 probe 来源 | 移除；`scripts/probe.py` 输出画布 / 精确分数帧率 / 帧数时长 | 无损失，字段更全（含 codec、音轨信息） |
| 2 | `reverse start` 返回的 `signed_in` / `plan` (`free`/`pro`) / `upgrade_url` / `subscribe_command` | `start.md`「Signed in on Free」 | Pro 订阅门禁 | 整段删除；不判断计划、不展示升级链接 | 无损失（不再需要计划） |
| 3 | `npx hyperframes billing subscribe` / `billing add-credits --needed N` | `start.md` | 计费，且规定由使用者自己执行 | 整段删除；不生成任何 `billing` 命令 | 无损失 |
| 4 | `npx hyperframes auth status` / `auth login` / `auth login --device` | `start.md`「Not signed in yet」 | 登录依赖（HeyGen 账号） | 整段删除；`doctor.py` 明确输出 `account_required: false` | 无损失 |
| 5 | 使用量提示、`usage`、credit limit、`--max-credits`、`--plan` 估价 | SKILL.md、`people.md`、`start.md` | 额度与计费 | 全部删除；`REVERSE_FREE.md` 禁止写价格/额度 | 无损失 |
| 6 | `npx hyperframes events --skill=reverse-any-video [--event=skill_completed]` | SKILL.md usage beacon、`start.md` | 遥测 / 联网 | 删除；本 skill 无任何遥测与网络调用 | 无损失 |
| 7 | `npx hyperframes measure cuts` | SKILL.md「The original decides the frame」 | Reverse 功能组 | `scripts/cuts.py`：全片逐帧 MAD + 自适应局部基线峰值 | 等价；跳切/推近另列低置信提示，需人工确认 |
| 8 | `npx hyperframes measure frames --range --roi` | 同上 | Reverse 功能组 | `scripts/frames.py`：导出连续帧 + manifest + contact sheet | 等价；单次上限 600 帧 |
| 9 | `npx hyperframes measure events --roi` | `match.md` | Reverse 功能组 | `cuts.py --roi x,y,w,h` 测字幕带像素切换帧 | 等价 |
| 10 | `npx hyperframes measure face --against --from --to` | `people.md` | Reverse 功能组 / 服务于 HeyGen 重拍 | 不实现；改用人物框裁切 + 原音轨 | **有损失**：不再做人脸框自动对齐 |
| 11 | `npx hyperframes transcribe` | `match.md` | 开源免费本地 ASR | 保留为**可选**（`composition.md` / `measurement.md`）；字幕切换时刻仍以像素为准 | 无损失 |
| 12 | `npx hyperframes media-use generate --type video/image --motion --mask --reference` | `people.md`、`animated.md` | HeyGen 生成，登录 + credits | 全部删除；人物与整镜改为按框/整镜裁切 | **有损失**：不重拍人脸、不去除烧录字、不生成新画面 |
| 13 | `npx hyperframes media-use resolve --type logo` | SKILL.md「Every layer」 | 免费但依赖 HeyGen 登录目录 | 改为从原帧按框裁切或直接使用品牌原始素材 | 极小；仍禁止手绘 Logo |
| 14 | HeyGen 重拍链路：plate / inpaint / `--allow-cuts` / `cuts_inside` / 30 分钟等待 / `generation_failed` 重试 | `people.md` 全篇 | Pro + credits | 整篇删除 | 见 #12 |
| 15 | 动画片的生成式整镜、`--first-frame` 与 motion 互斥、手动 retime（`data-media-start` / `data-playback-rate`） | `animated.md` | Pro + credits | 不生成；能用代码承载的层仍重建，其余整镜裁切并标注不可编辑 | **有损失**：动画层不可解耦 |
| 16 | `npx hyperframes remove-background -o .webm` | `people.md`「Text behind the person」 | 开源免费本地能力 | 保留为**可选**；无该 CLI 时用 ffmpeg 抠像或标注为近似 | 轻微 |
| 17 | `npx hyperframes check` | SKILL.md「Check once」 | 开源免费本地 CLI | 保留为**可选**，契约摘要内嵌在 `composition.md` | 无损失 |
| 18 | `npx hyperframes cloud render --fps --quality high` | SKILL.md、cloud.md | **按 credit 计费** | 删除；只用本地 `npx hyperframes render` 或等价 HTML→视频渲染 | 无损失（本地渲染确定性相同） |
| 19 | 分数帧率 / 非标准画幅导致云端失败时的回落逻辑 | SKILL.md | 云端相关 | 删除；本地只有一条路径 | 无损失 |
| 20 | `npx hyperframes diff <video> . --at` / `diff <video> <out>` / `diff --sbs` | SKILL.md、start.md | Reverse 功能组 | `scripts/diff.py` + `scripts/frames.py`；PSNR/SSIM、切点比对、最差帧并排图、Markdown 报告 | 等价；音画偏移改为 10 ms 分辨率的估计值 |
| 21 | `npx hyperframes snapshot --review`、`preview`、`present` | 上游其它 skill | 开源免费 | 保留为可选 | 无损失 |
| 22 | `init --video --keep-original --skip-transcribe --skip-skills` | `start.md` | 开源免费 CLI | 改为手工复制原片到 `assets/source.mp4`（`composition.md`） | 无损失 |
| 23 | `REVERSE.md`（含价格/额度字段、命令笔记与 `--plan` 复检规则） | SKILL.md | 状态文件 | 改名 `REVERSE_FREE.md`；保留"命令是笔记不是脚本"规则，**删掉所有计费字段** | 无损失 |
| 24 | 插件安装规则 `plugin-installation.md`、`/hyperframes`、`/hyperframes-cli`、`/media-use` skill 引用 | SKILL.md / 全篇 | 依赖其它 skill 存在 | 全部自包含：`references/` 内嵌契约、配方与命令 | 无损失，可移植性提高 |
| 25 | 「Reverse videos the person has the right to use」 | SKILL.md | 合规条款 | **保留**并写进 SKILL.md 开头 | 无损失 |

## 结论

- 移除 **16 项**账号 / 计费 / 云端 / 遥测 / 生成式依赖（#2–#6、#10–#15、#18–#19、#23 计费部分、#24）；
- 用本地脚本等价替换 **7 项**测量与验收能力（#1、#7–#9、#20）；
- 保留 **5 项**开源免费能力且全部降级为可选（#11、#16–#17、#21–#22）；
- 明确保留 **3 项核心能力**：逐帧测量口径、分层重建与匹配配方、量化验收闭环；
- 明确承认 **3 项能力损失**：生成式重拍人脸、去除烧录字、动画整镜解耦。详见 `LIMITATIONS.md`。

全局扫描方式（发布前必须执行）：

```bash
grep -RniE "reverse start|billing|auth login|auth status|cloud render|media-use generate|media-use resolve|measure (cuts|frames|events|face)|hyperframes diff|hyperframes events|credits|HeyGen|--max-credits|--plan" . --exclude-dir=.git
```

只允许该命令在**说明性文档**（本文件、`LIMITATIONS.md`、`DIFF_FROM_UPSTREAM.md`）里命中；`SKILL.md`、`references/`、`scripts/` 中不得出现任何作为**可执行指令**的命中。
