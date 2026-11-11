# 与原 skill 的差异、版本与分发信息

## 1. 上游基线（可追溯）

| 项 | 值 |
| --- | --- |
| 上游仓库 | `heygen-com/hyperframes`（<https://github.com/heygen-com/hyperframes>） |
| 蒸馏对象 | `skills/reverse-any-video/SKILL.md` 及 `references/{start,match,people,animated}.md` |
| 分支 | `main` |
| SKILL.md blob SHA | `ad95dd9d8dae854f2ebd01ab6573d55e1d52daf2` |
| SKILL.md 大小 | 5,289 bytes |
| 抓取日期 | 2026-11-11 |
| 上游许可证 | Apache License 2.0（见仓库根 `LICENSE`，本仓库 `LICENSE` 为其原文副本，10,763 bytes） |
| 上游定位 | 官方 README 表格标注：`/reverse-any-video` … **HyperFrames Pro** |

**本机对照发现**：本机已安装的 `~/.workbuddy/skills/reverse-any-video/SKILL.md` 正文与 `main` 一致，但 frontmatter `description` 是较旧版本（缺少 `remake` 与中文触发词「复刻这个视频」「照着这个视频做一个」）。本蒸馏以远端 `main` 为准，不以本地旧版为准。

## 2. 文件映射

| 上游 | 本 skill | 变化 |
| --- | --- | --- |
| `SKILL.md` | `SKILL.md` | 重写：删除 Pro 门禁 / 计费 / 登录 / 遥测，加入零依赖承诺与禁止清单，路由改到自有 `references/` 与 `scripts/` |
| `references/start.md` | — | **删除**：全篇是登录、Free→Pro 升级、credits 不足与话术，免费版无对应流程 |
| `references/match.md` | `references/rebuild.md` | **改编保留**：匹配方法、测量口径、CSS/SVG 配方逐条保留；补入免费降级策略 |
| `references/people.md` | `references/rebuild.md` §人物降级 | **删除生成式重拍全链路**，替换为按框裁切 + 边界说明 |
| `references/animated.md` | `references/rebuild.md` §整镜降级 | **删除生成式整镜**，保留"能代码化的层仍重建"的判断原则 |
| `hyperframes/SKILL.md` 的 Contract | `references/composition.md` | **内嵌摘要**，不再依赖其它 skill 被加载 |
| `reverse start` probe | `scripts/probe.py`、`references/measurement.md` | 自建 |
| `measure cuts/frames/events/face` | `scripts/cuts.py`、`scripts/frames.py` | 自建（face 不实现） |
| `hyperframes diff` / `diff --sbs` | `scripts/diff.py`、`references/verification.md` | 自建 |
| `check` / 本地 `render` / `preview` | `references/composition.md` | 保留为**可选**免费路径 |
| `REVERSE.md` | `REVERSE_FREE.md`（运行时生成） | 去掉价格/额度字段，保留"命令是笔记不是脚本" |
| — | `scripts/doctor.py`、`scripts/selftest.py`、`scripts/hf_free.py` | **新增**：环境自检与离线端到端自测 |
| — | `docs/`、`README.md`、`NOTICE`、`CHANGELOG.md`、`examples/` | **新增**：完整配套文档与工程骨架 |

## 3. 行为差异

| 维度 | 上游 | 本 skill |
| --- | --- | --- |
| 启动 | `reverse start` 检查 `signed_in` / `plan`，未登录或 Free 时停下来要求登录或升级 | `doctor.py` 检查本机 Python/ffmpeg，**不检查任何账号** |
| 计费 | `billing` 由使用者执行；额度不足时汇总后一次性给命令 | 无计费概念，不生成 `billing` 命令 |
| 遥测 | `hyperframes events --skill=reverse-any-video` + `skill_completed` | 无任何遥测 |
| 人物 | 每个原镜头单独 HeyGen 重拍，plate inpaint、`--mask`、`measure face` 对齐 | 按人物框裁切原片，静音，跨切点切断 |
| 动画 | 首帧 plate + 生成式整镜 + 手动 retime | 能代码化的层重建，其余整镜裁切并标注不可编辑 |
| 渲染 | 优先 `cloud render`（按 credit 计费），失败回落本地 | 只有本地渲染或等价免费渲染器 |
| 验收 | `hyperframes diff` | `diff.py`（ffmpeg PSNR/SSIM + 切点比对 + 并排图 + Markdown 报告） |
| 交付话术 | `start.md` 规定 "20–50 分钟"、显示并排图、提示可继续编辑、上报完成事件 | 无时间承诺、无事件上报；仍打开并排报告与工程预览 |
| 状态文件 | `REVERSE.md` 允许出现额度/价格相关上下文 | `REVERSE_FREE.md` 明确禁止价格与额度信息 |
| 停止条件 | 修一轮 → 再 render + diff → 停 | **相同**（沿用，防止无限迭代） |
| 合规 | "只复刻有权使用的视频" | **相同** |

## 4. 版本信息

| 项 | 值 |
| --- | --- |
| 本 skill 名称 | `reverse-any-video-free` |
| 当前版本 | **1.0.0** |
| 版本规则 | 语义化版本：`MAJOR` = 工作流/契约不兼容变更；`MINOR` = 新增免费能力或参考文档；`PATCH` = 脚本修复、文档修订 |
| 与上游版本关系 | **不联动**。上游是持续更新的 `main` 分支，本 skill 以 §1 的 blob SHA 为固定蒸馏基线；上游更新不会自动进入本仓库 |
| 同步策略 | 每次同步上游需在 `CHANGELOG.md` 记录新的上游 blob SHA，并重新执行 `PRO_REMOVAL.md` 的全局扫描与 `selftest.py` |
| 运行时版本标识 | `scripts/hf_free.py` 的 `VERSION` 常量；`doctor.py`、`probe.py`、`cuts.py`、`frames.py`、`diff.py` 的 JSON 输出均带 `toolkit` 与 `version` 字段 |
| 状态 | 可用（离线自测 11/11 通过） |

## 5. 分发信息

**分发形态**：一个自包含的目录，无注册表、无包管理器、无安装脚本、无网络依赖。

```bash
# 方式 A：复制目录（任意 Agent）
cp -r reverse-any-video-free <agent-skills-dir>/skills/

# 方式 B：git clone 本仓库后把目录软链/复制到 skills 目录
# 方式 C：直接把 SKILL.md + references/ + scripts/ + docs/ 作为附件交给另一个 Agent
```

- **最低可加载集**：`SKILL.md` + `references/`。仅加载这两项就能理解工作流；`scripts/` 提供可执行能力，`docs/` 提供审计信息，`examples/` 是模板。
- **加载触发**：frontmatter `description` 覆盖 `reverse / recreate / remake / replicate / copy` 与中文「复刻这个视频」「照着这个视频做一个」「无 Pro 复刻视频」「离线复刻」。
- **无需授权**：不读取环境变量中的凭据、不调用 `auth`、不请求任何 token；`doctor.py --json` 可当场证明 `account_required: false` / `network_required: false`。
- **可自由修改**：Apache-2.0 允许修改与再分发，需保留 `LICENSE`、`NOTICE` 并注明改动（见下）。

## 6. 许可证与归属声明

- 上游 `heygen-com/hyperframes` 以 **Apache License 2.0** 发布；本仓库 `LICENSE` 是其原文副本。
- 本 skill 是**衍生/改编作品**：方法与配方来自上游 `skills/reverse-any-video/` 与 `skills/hyperframes/SKILL.md` 的契约摘要，已按 Apache-2.0 第 4 条在 `NOTICE` 中标注来源与改动。
- 本仓库**非 HeyGen 官方项目**，与 HeyGen、HyperFrames 无隶属、无背书关系；"HyperFrames" 相关名称仅用于指明所适配的开源格式与免费 CLI。
- 若上游权利人提出更严格的署名或商标要求，以 `NOTICE` 与上游仓库 LICENSE 为准。
