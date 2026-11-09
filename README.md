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
├── scripts/teardown.py     # 抽帧 / 镜头统计 / 联系表 / 生成新页
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

## 自己分析一条视频（5 步流水线）

前提：本机有 `ffmpeg` / `ffprobe` 和 Python 的 `Pillow`。

**第 1 步 · 拿到视频**（下载到本地，任意格式 mp4/mov/webm 都行）

```bash
# 有 yt-dlp 的话：
yt-dlp -f "bv*[height<=1080]+ba/b" -o "~/Downloads/%(title)s.%(ext)s" "<视频链接>"
```

**第 2 步 · 先粗扫，摸清时长与节奏**（不用先猜时间码）

```bash
python3 scripts/teardown.py stats ~/Downloads/video.mp4
# → 时长、镜头切点数、平均几秒一个镜头、每 30 秒切点柱（可直接粘进页面）
python3 scripts/teardown.py frames ~/Downloads/video.mp4 --every 30 --out work/scan
# → 每 30 秒一张，先看整体长什么样
```

**第 3 步 · 定关键时间码，精抽**

```bash
python3 scripts/teardown.py frames ~/Downloads/video.mp4 \
  --times 0:00,0:05,0:37,0:55,3:07,3:55 \
  --labels 门店,店内,两台并排,背板,立标准,产品登场 \
  --out work/my-video/frames
# 文件名自动变成 00s-门店.jpg / 3m55-产品登场.jpg，和页面 figcaption 一一对应
```

**第 4 步 · 拼一张联系表，交给多模态读**

```bash
python3 scripts/teardown.py sheet work/my-video/frames --out work/my-video/contact.jpg
```

把 `contact.jpg` 发给我（或直接发 `work/my-video/frames/` 整目录），我一张图就能看到 12–20 帧，接着写七维度拆解、时间轴和结论。**这一步是唯一需要人的地方：判断 Hook、卖点顺序、竞品打法。**

**第 5 步 · 生成新报告页并上线**

```bash
python3 scripts/teardown.py scaffold --slug my-video --title "标题" --subtitle "副标题"
# → reports/my-video.html，抽帧路径自动指向 assets/frames/my-video/
npm 不需要；把 work/my-video/frames/*.jpg 挪到 assets/frames/my-video/，改扩展名后 git push 即可
```

上线后地址：`https://jingtao-cui.github.io/tcl-kol-teardown/reports/<slug>.html`

### 镜头统计说明

`stats` 用 ffmpeg `scene` 检测（默认阈值 0.3）。真人实拍视频通常 0.3 就够；动画 / 同场景长镜头多的视频切点会偏少，把 `--threshold` 降到 `0.2` 再跑。切点数是**近似值**，页面上要按「约」来写。

## 文件怎么命名（8 条一起跑之前先统一）

**格式**：`{市场}_{KOL}_{产品}_{YYYYMMDD}.mp4`，四段用下划线隔开，全 ASCII。

| 段 | 取值 | 例 |
|---|---|---|
| 市场 | 两位国家码 | `UK` / `DE` / `FR` / `ES` / `IT` / `PL` / `NL` / `SE` |
| KOL | 频道名去掉空格和符号 | `HDTVTest` / `Mrwhosetheboss` / `TechInBlack` |
| 产品 | 型号简写 | `P8L` / `X11L` / `C8L` / `C7L` |
| 日期 | 视频发布日期 | `20261031` |

示例：

```
UK_HDTVTest_P8L_20261031.mp4
FR_Nowtech_P8L_20261028.mp4
ES_Tecnonauta_X11L_20261024.mp4
DE_Mrwhosetheboss_C8L_20261020.mp4
```

- **别用中文文件名**，也别带 `(`、`#`、空格 —— 脚本会把它转成 slug，中文和符号会让 URL 变丑。
- 同一个 KOL 有多条，末尾补序号：`UK_HDTVTest_P8L_20261031-2.mp4`。
- 脚本自动生成 slug：`UK_HDTVTest_P8L_20261031` → `uk-hdtvtest-p8l` → 页面地址 `/reports/uk-hdtvtest-p8l.html`。

## 一次处理 8 条（批量）

把 8 个视频放进同一个文件夹（例：`~/Downloads/tcl-8/`），然后一条命令：

```bash
python3 scripts/teardown.py batch ~/Downloads/tcl-8 --every 30
```

产出：

```
work/
├── index.md                     # 8 条一张表：市场 / KOL / 产品 / 时长 / 切点 / 平均镜头
├── index.json
├── uk-hdtvtest-p8l/
│   ├── stats.json               # 切点节奏
│   ├── sweep/                   # 每 30 秒一张，粗扫用
│   └── contact.jpg              # 联系表（发给我读图用）
└── ...
```

单个视频想再精抽关键帧，回到第 3 步用 `frames --times ... --labels ...` 补，输出到同一条的 `work/<slug>/frames/`。

**批量之后怎么交付**：把 8 张 `contact.jpg` 一起发我，我逐条写七维度、结论和时间轴；你确认内容后我用 `scaffold` 生成 8 个页面，一次性 push。

## 两个分析项目怎么分（8 条 = 4 + 4）

两条内容逻辑完全不同，必须分开成两个 project，页面上也分开归类：

| 项目 | 目录名 | 内容特征 | 这组在证明什么 |
|---|---|---|---|
| **头部 KOL · MiniLED 教育** | `head-miniled/` | 频道体量大（40 万粉以上）、以「教你怎么判断」为主、产品出现晚 | 叙事结构、信任建构、把「标准」变成自己的话术 |
| **中部 KOL · P8L vs M80H** | `mid-p8l-m80h/` | 频道体量中等、上来就是两台并排、结论锋利 | 说服效率、实拍证据、CTA 与转化意图 |

### 文件夹结构

```
~/Downloads/tcl-kol/
├── head-miniled/                       # 头部 KOL · MiniLED 教育（4 条）
│   ├── UK_HDTVTest_MiniLED-Edu_20261031.mp4
│   ├── FR_Mathis_MiniLED-Edu_20261027.mp4
│   ├── DE_TechNick_MiniLED-Edu_20261022.mp4
│   └── UK_Mrwhosetheboss_MiniLED-Edu_20261018.mp4
└── mid-p8l-m80h/                       # 中部 KOL · P8L vs M80H（4 条）
    ├── FR_Nowtech_P8L-vs-M80H_20261028.mp4
    ├── ES_Tecnonauta_P8L-vs-M80H_20261024.mp4
    ├── IT_TechInBlack_P8L-vs-M80H_20261020.mp4
    └── ES_ZoneofTech_P8L-vs-M80H_20261016.mp4
```

**文件名四段**：`{市场}_{KOL}_{内容类型}_{日期}.mp4`

- 市场：`UK` / `DE` / `FR` / `ES` / `IT` / `PL` / `NL` / `SE`
- KOL：频道名去空格，`TechInBlack` 不是 `Tech In Black`
- 内容类型：头部组统一写 `MiniLED-Edu`，中部组统一写 `P8L-vs-M80H`
- 日期：发布日 `YYYYMMDD`

不要加 `HEAD_` / `MID_` 前缀 —— **项目靠文件夹区分，不靠文件名**，加了反而让 slug 变长（`head-uk-hdtvtest-miniled-edu`）。

### 两条命令

```bash
python3 scripts/teardown.py batch ~/Downloads/tcl-kol/head-miniled  --name head-miniled  --every 30
python3 scripts/teardown.py batch ~/Downloads/tcl-kol/mid-p8l-m80h  --name mid-p8l-m80h --every 30
```

产出 `work/head-miniled/index.md` 与 `work/mid-p8l-m80h/index.md`，两张表各 4 行，每条一份 `contact.jpg`。

### 生成页面时带上项目归属

```bash
python3 scripts/teardown.py scaffold --slug uk-hdtvtest-miniled \
  --title "Mini LED 到底该怎么看" --project head \
  --kol HDTVTest --market UK --duration 8:50 --score 89
python3 scripts/teardown.py index      # 重新渲染 reports/index.html
```

`--project head|mid` 决定它出现在汇总页哪一节；`index` 每次都按 `reports/manifest.json` 重建，不用手改 HTML。

汇总页地址：`https://jingtao-cui.github.io/tcl-kol-teardown/reports/`

## 口径与合规（页脚已内置，别删）

- 播放 / 点赞 / 评论 / 粉丝数来自平台公开数据；完播率、平均观看时长、受众画像需 KOL 授权回传，公开 API 拿不到。
- 七维度评分是 AI 基于画面、字幕、结构判断，**不是平台官方指标**；镜头切换数按 `ffmpeg scene detection` 统计，非人工逐帧核对。
- 封面与视频截图版权归原创作者，仅用于内部比稿分析，不对外公开发布。

## 技术说明

- 无 JS 框架、无 CDN 依赖、无 cookie；单页纯 CSS 布局，移动端两档断点（980 / 620）。
- 配色集中在 `style.css` 的 `:root`：主色 `--red:#e60012`（TCL 红），底 `--bg:#f4f5f7`，正文 `--ink:#101828`。
- `html{scroll-behavior:smooth}` + 顶部 nav 锚点，对应六段区块 `#profile #dims #timeline #why #comments #playbook`。
