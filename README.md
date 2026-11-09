# TCL 欧洲 KOL · 爆款视频拆解工具（Video Teardown）

把 GrowClaw 原型（`TechFlow × TCL P8L`）完整复刻成可自托管的静态站点：纯 HTML + CSS，零依赖、零构建，推到 GitHub 后用 Pages（branch 模式）直接打开。

线上地址：https://jingtao-cui.github.io/tcl-kol-teardown/

## 这是什么

一条视频 = 一张「单条洞察卡」，包含六段：

| 区块 | 内容 |
|---|---|
| 01 视频档案与表现 | 封面、播放/粉丝比、点赞率、评论率、时长、频道订阅、标题/描述/对比机型 |
| 02 七维度拆解 | Hook / 切入方式 / 卖点顺序 / 场景 / 转场 / 竞品对比 / CTA，每维带时间码、评分、可复用公式、4 张抽帧 |
| 03 内容结构时间轴 | 章节 × 时间 × 结构标签，加一条「每 30 秒切点数量」节奏柱 |
| 04 为什么爆 | 六个原因，按贡献度排序 |
| 05 评论区侧写 | 高赞原声 + 评论在讨论什么 + 对 TCL/iBLUE 的启示 |
| 06 可复制清单 | Hook 公式、结构模板、证据链四件套、风控与运营 |

## 目录

```
tcl-kol-teardown/
├── index.html              # 当前这条视频的拆解报告（可直接改内容复用）
├── style.css               # 全部样式，配色变量在 :root
├── assets/
│   ├── cover.svg           # 封面占位（换成 cover.jpg 即可）
│   └── frames/*.svg        # 22 张抽帧占位，文件名 = 时间码
├── LICENSE
└── README.md
```

## 本地预览

```bash
cd tcl-kol-teardown
python3 -m http.server 8080
# 打开 http://localhost:8080
```

## 换成真实素材

1. 封面：把 `assets/cover.jpg` 放进 `assets/`，把 `index.html` 里 `assets/cover.svg` 改成 `assets/cover.jpg`。
2. 抽帧：文件名保持与时间码一致（如 `00s-currys.jpg`、`3m55-tcl.jpg`），放进 `assets/frames/`，然后批量改扩展名：

```bash
sed -i '' 's|assets/frames/\([^"]*\)\.svg|assets/frames/\1.jpg|g' index.html   # macOS
sed -i    's|assets/frames/\([^"]*\)\.svg|assets/frames/\1.jpg|g' index.html   # Linux
```

图片统一按 16:9 裁切（页面用 `aspect-ratio:16/9` + `object-fit:cover`，不按比例也能看，但会裁）。

## 加第二条视频

1. 复制一份：`cp index.html reports/samsung-s95f.html`（先 `mkdir reports`）。
2. 改五处即可：`<title>`、hero 标题与 meta chips、`verdict` 结论与评分、七个维度卡里的正文/时间码/评分、页脚抓取日期。
3. 抽帧放到 `assets/frames/` 下同名文件即可，不用改结构。

> 想做「一个入口 + 多条报告」的列表页，再加一个 `index-list.html` 链到 `reports/*.html` 就行，样式直接复用 `.card` / `.sec-head`。

## 推到 GitHub（Pages 自动发布）

```bash
cd tcl-kol-teardown
git init -b main
git add .
git commit -m "init: TCL KOL video teardown"
git remote add origin git@github.com:<你的账号>/tcl-kol-teardown.git
git push -u origin main
```

然后仓库 **Settings → Pages → Build and deployment → Source 选「Deploy from a branch」**，Branch 选 `main`、目录选 `/ (root)`，Save。每次 push 到 main 后 30–60 秒自动重建，地址形如 `https://<账号>.github.io/tcl-kol-teardown/`。

> 想改成 GitHub Actions 部署（可自定义构建步骤），需要 token 具备 `workflow` 权限；把 `pages.yml` 放回 `.github/workflows/` 即可，模板见本次交付的 `pages_workflow_keep/`。

## 口径与合规（页脚已内置，别删）

- 播放 / 点赞 / 评论 / 粉丝数来自平台公开数据；完播率、平均观看时长、受众画像需 KOL 授权回传，公开 API 拿不到。
- 七维度评分是 AI 基于画面、字幕、结构判断，**不是平台官方指标**；镜头切换数按 `ffmpeg scene detection` 统计，非人工逐帧核对。
- 封面与视频截图版权归原创作者，仅用于内部比稿分析，不对外公开发布。

## 技术说明

- 无 JS 框架、无 CDN 依赖、无 cookie；单页纯 CSS 布局，移动端两档断点（980 / 620）。
- 配色集中在 `style.css` 的 `:root`：主色 `--red:#e60012`（TCL 红），底 `--bg:#f4f5f7`，正文 `--ink:#101828`。
- `html{scroll-behavior:smooth}` + 顶部 nav 锚点，对应六段区块 `#profile #dims #timeline #why #comments #playbook`。
