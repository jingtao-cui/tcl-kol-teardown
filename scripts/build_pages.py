#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_pages.py · 用执行进度总览里的真实数据，生成每个 KOL 一条的独立数据页

数据来源：Mini LED_ P系列执行进度总览-2.xlsx
  Video Tracker      → 公开数据（播放/点赞/评论/ER）
  Video History      → 每日快照（画流量曲线）
  KOL后台数据汇总     → 后台指标（展示量/CTR/30s 留存/结尾/平均观看/流量来源/受众）

输出：reports/<slug>.html + 更新 reports/manifest.json（供 index 生成汇总页）

用法：
  python3 scripts/build_pages.py "/path/Mini LED_ P系列执行进度总览-2.xlsx"
"""
import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports"


def key(s):
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def num(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v or "").strip().lower().replace(",", "")
    m = re.match(r"([\d.]+)\s*([mk]?)", s)
    if not m:
        return None
    x = float(m.group(1))
    return x * 1e6 if m.group(2) == "m" else x * 1e3 if m.group(2) == "k" else x


def fmt(n):
    if n is None:
        return "—"
    if n >= 1e6:
        return f"{n/1e6:.2f}M".replace(".00M", "M")
    if n >= 1e3:
        return f"{n/1e3:.1f}K".replace(".0K", "K")
    return f"{int(n)}"


def pct(s):
    """'12.3%' / 0.123 / '点击率 5.8%' 都转成百分数数值。"""
    if isinstance(s, (int, float)):
        return round(float(s) * 100, 2) if float(s) <= 1 else float(s)
    m = re.search(r"([\d.]+)\s*%", str(s or ""))
    return float(m.group(1)) if m else None


def mmss_to_sec(s):
    m = re.match(r"(\d+):(\d+)", str(s or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def sec_to_mmss(s):
    return f"{s//60}:{s%60:02d}" if s else "—"


def load(xlsx):
    wb = openpyxl.load_workbook(xlsx, data_only=True)

    ws = wb["KOL后台数据汇总"]
    be = {}
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[0] and num(r[9]):
            be[key(r[0])] = {
                "kol": str(r[0]).strip(), "campaign": r[1], "title": r[2],
                "imp": num(r[3]), "cmt": num(r[4]), "ctr": r[5], "ret": r[6],
                "save": num(r[7]), "share": num(r[8]), "views": num(r[9]),
                "avg": r[10], "source": r[11], "aud": r[12],
            }

    ws = wb["Video Tracker"]
    hdr = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(hdr) if h}
    pub = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        vid = r[idx["Video ID"]]
        if vid and isinstance(r[idx["Views"]], (int, float)) and r[idx["KOL Name"]]:
            pub[key(r[idx["KOL Name"]])] = {
                "kol": str(r[idx["KOL Name"]]).strip(), "vid": vid,
                "url": r[idx["Video URL"]], "campaign": r[idx["Campaign"]],
                "pub": str(r[idx[" Publish Date"]])[:10],
                "views": int(r[idx["Views"]]), "likes": int(r[idx["Likes"]] or 0),
                "cmts": int(r[idx["Comments"]] or 0), "er": r[idx["Engagement Rate"]],
                "tier": str(r[idx["Notes"]] or "").strip(),
            }

    ws = wb["Video History"]
    hdr = [c.value for c in ws[1]]
    i2 = {h: i for i, h in enumerate(hdr) if h}
    hist = {}
    for r in ws.iter_rows(min_row=2, values_only=True):
        vid = r[i2["Video ID"]]
        if vid and isinstance(r[i2["Views"]], (int, float)) and isinstance(r[i2["Age Day"]], (int, float)):
            hist.setdefault(vid, []).append(
                (int(r[i2["Age Day"]]), int(r[i2["Views"]]), int(r[i2["Comments"]] or 0)))
    for v in hist:
        hist[v] = sorted(hist[v])
    return be, pub, hist


def sparkline(points):
    """(age, views) → 简单折线，宽度自适应。"""
    if not points:
        return '<p class="note">该条暂无连续快照，曲线待补。</p>'
    w, h, pad = 880, 190, 28
    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    xmin, xmax = min(xs), max(xs) or 1
    ymax = max(ys) or 1
    ymin = min(ys) * 0.92 if min(ys) < ymax else 0
    if xmax == xmin:
        xmax = xmin + 1
    px = lambda a: pad + (a - xmin) / (xmax - xmin) * (w - pad * 2)
    py = lambda v: h - pad - ((v - ymin) / (ymax - ymin or 1)) * (h - pad * 2)
    d = " ".join(f"{px(pt[0]):.1f},{py(pt[1]):.1f}" for pt in points)
    dots = "".join(f'<circle cx="{px(pt[0]):.1f}" cy="{py(pt[1]):.1f}" r="3.2" fill="#e60012"/>'
                   for pt in points)
    labels = (f'<text x="{pad}" y="{h-6}" class="ax">D{xmin}</text>'
              f'<text x="{w-pad-24}" y="{h-6}" class="ax">D{xmax}</text>'
              f'<text x="{pad}" y="16" class="ax">{fmt(ymax)}</text>'
              f'<text x="{px(points[0][0]):.0f}" y="{py(points[0][1])-8:.0f}" class="ax" text-anchor="start">{fmt(points[0][1])}</text>'
              f'<text x="{px(points[-1][0]):.0f}" y="{py(points[-1][1])-8:.0f}" class="ax" text-anchor="end">{fmt(points[-1][1])}</text>')
    note = ""
    if len(points) <= 2:
        note = '<p class="note">仅 2 个快照点，只能看首末，不能判断中段走势。</p>'
    return (f'<svg viewBox="0 0 {w} {h}" class="line">'
            f'<polyline points="{d}" fill="none" stroke="#e60012" stroke-width="2.2"/>{dots}{labels}</svg>{note}')


def conclusion(p, b):
    """只用数据说话，不编判断。"""
    out = []
    er = pct(p["er"])
    ret30 = pct(b.get("ret"))
    fin = pct(b.get("avg"))
    if er is None:
        out.append("互动率缺失，本条不做互动判断。")
    if er is not None and er < 1:
        out.append(f"互动率 {er:.2f}%，低于 1%——播放主要来自流量位，不是内容自发扩散。")
    elif er is not None and er >= 3:
        out.append(f"互动率 {er:.2f}%，属于评论区被调动起来的那一类，点赞与评论密度都高。")
    else:
        out.append(f"互动率 {er:.2f}%，处在中位——有人看，但没形成讨论。")
    if ret30 is not None and ret30 <= 25:
        out.append(f"30 秒留存只有 {ret30:.0f}%，前 30 秒把大半观众筛掉了，钩子撑不住。")
    if ret30 is not None and ret30 >= 60:
        out.append(f"30 秒留存 {ret30:.0f}%，钩子成立，观众愿意给时间。")
    if fin is not None and fin >= 25:
        out.append(f"结尾仍留 {fin:.1f}%，属于八条里少见的「看到最后」型。")
    if fin is not None and fin <= 10:
        out.append(f"结尾只剩 {fin:.1f}%，中段掉得厉害，问题在结构不在开头。")
    return out


def page(slug, p, b, points):
    er = pct(p["er"])
    ret30 = pct(b.get("ret"))
    fin = pct(b.get("avg"))
    avg_sec = mmss_to_sec(str(b.get("avg") or ""))
    dur = int(avg_sec / (fin / 100)) if avg_sec and fin else None
    imp = b.get("imp")
    ctr = b.get("ctr")
    tier = p["tier"] or ("头部" if p["campaign"] == "MiniLED Education" else "中部")
    bullets = "".join(f"<li>{x}</li>" for x in conclusion(p, b))
    facts = [
        ("播放 Views", fmt(p["views"]), f"{p['views']:,}"),
        ("点赞 Likes", fmt(p["likes"]), f"{p['likes']:,}"),
        ("评论 Comments", fmt(p["cmts"]), f"{p['cmts']:,}"),
        ("互动率 ER", f"{er:.2f}%" if er is not None else "—", "点赞+评论 / 播放"),
        ("展示量 Impressions", fmt(imp), "后台数据"),
        ("点击率 CTR", str(ctr or "—").replace("点击率", "").strip(), "后台数据"),
    ]
    fact_html = "".join(
        f'<div class="fact"><span>{k}</span><b>{v}</b><small>{h}</small></div>' for k, v, h in facts)
    hist_note = f"{len(points)} 个快照点 · D{points[0][0]} → D{points[-1][0]}" if points else "暂无快照"
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{p['kol']} · {str(b.get('title') or '').strip()[:60]}</title>
<link rel="stylesheet" href="../style.css">
<style>
.line{{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:12px}}
.ax{{font-size:10px;fill:#98a2b3;font-family:ui-monospace,monospace}}
.note{{font-size:11.5px;color:#98a2b3;margin:6px 0 0}}
.kv{{display:grid;grid-template-columns:150px 1fr;gap:8px 18px;font-size:13px}}
.kv dt{{color:#667085;font-size:12px}}.kv dd{{margin:0;color:#101828}}
.fact b{{display:block;margin-top:2px}}
.pend{{border:1px dashed #d0d5dd;border-radius:12px;padding:22px;text-align:center;color:#98a2b3;font-size:12.5px;background:#fcfcfd}}
</style></head><body>
<div class="topbar"><div class="wrap">
  <div class="brand"><span class="logo">TCL</span><small>EU KOL · TEARDOWN</small></div>
  <div class="nav"><a href="index.html">← 全部 KOL</a><a href="#profile">数据</a><a href="#curve">曲线</a><a href="#dims">七维度</a></div>
</div></div>
<div class="wrap">
  <div class="hero">
    <span class="kicker">{p['campaign']} · {tier} KOL</span>
    <h1>{str(b.get('title') or p['kol']).strip()}</h1>
    <p class="sub">{p['kol']} · 发布于 {p['pub']}{(' · 时长约 ' + sec_to_mmss(dur)) if dur else ''}</p>
    <div class="hero-meta">
      <span class="chip red">{p['campaign']}</span>
      <span class="chip">{tier} KOL</span>
      <span class="chip green">数据截至 2026-11-09</span>
      <span class="chip">播放 {fmt(p['views'])}</span>
      <span class="chip">ER {f'{er:.2f}%' if er is not None else '—'}</span>
    </div>
  </div>

  <div class="verdict">
    <div class="ico">📊</div>
    <div><h2>数据读出来的是什么</h2>
      <ul class="tight">{bullets}</ul></div>
    <div class="score-big"><b>{fmt(p['views'])}</b><span>VIEWS</span></div>
  </div>

  <section id="profile">
    <div class="sec-head"><span class="sec-no">01</span><h2>档案与表现</h2><span class="hint">公开数据 + 后台数据，均来自执行进度总览</span></div>
    <div class="facts">{fact_html}</div>
    <p class="note">点赞、评论为视频页公开数；展示量、点击率为 KOL 后台截图汇总口径，与公开播放存在平台侧统计差，属正常。</p>
  </section>

  <section>
    <div class="sec-head"><span class="sec-no">02</span><h2>观看质量</h2><span class="hint">后台数据 · 决定这条内容「有没有被看完」</span></div>
    <div class="card pad"><dl class="kv">
      <dt>30 秒留存</dt><dd>{ret30 if ret30 is not None else '—'}{'%' if ret30 is not None else ''}</dd>
      <dt>结尾留存 / 完播</dt><dd>{fin if fin is not None else '—'}{'%' if fin is not None else ''}</dd>
      <dt>平均观看时长</dt><dd>{str(b.get('avg') or '—')}</dd>
      <dt>收藏 / 分享</dt><dd>{fmt(b.get('save'))} / {fmt(b.get('share'))}</dd>
      <dt>主要流量来源</dt><dd>{str(b.get('source') or '—')}</dd>
      <dt>受众分布</dt><dd>{str(b.get('aud') or '—')}</dd>
    </dl></div>
  </section>

  <section id="curve">
    <div class="sec-head"><span class="sec-no">03</span><h2>播放增长曲线</h2><span class="hint">{hist_note}</span></div>
    {sparkline(points)}
  </section>

  <section id="comments">
    <div class="sec-head"><span class="sec-no">04</span><h2>评论区</h2><span class="hint">公开评论 {p['cmts']:,} 条</span></div>
    <div class="pend">评论正文待接入：需要该条评论区截图（最相关前 10 条 + 至少 3 条负面），或直接粘贴评论文本。<br>数量已在表内（{p['cmts']:,} 条），但正文不在数据表里，不臆测情绪占比。</div>
  </section>

  <section id="dims">
    <div class="sec-head"><span class="sec-no">05</span><h2>七维度拆解</h2><span class="hint">Hook / 切入 / 卖点顺序 / 场景 / 转场 / 竞品对比 / CTA</span></div>
    <div class="pend">待抽帧。需要该条视频的关键帧截图（或本地跑 scripts/teardown.py 生成 contact.jpg）。<br>没有画面我不评这七项——分数会变成猜。</div>
  </section>

  <footer><b>口径</b>：公开数据（播放/点赞/评论）取自 Video Tracker 每日快照，抓取时间 2026-11-09；后台指标（展示量/点击率/留存/平均观看/来源/受众）取自 KOL 后台截图汇总，平台口径与公开数存在差异；七维度评分为人工/AI 基于画面判断，非平台指标。<br>
  <b>来源</b>：Mini LED_ P系列执行进度总览-2.xlsx · {p['kol']} · {p['vid']}</footer>
</div></body></html>
"""


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else sys.argv[0]
    be, pub, hist = load(xlsx)

    # 找公开与后台的对应：按 key 精确，再退化到前缀匹配
    pairs = []
    for k, p in pub.items():
        b = be.get(k)
        if not b:
            cand = [v for kk, v in be.items() if kk.startswith(k[:6]) or k.startswith(kk[:6])]
            b = cand[0] if cand else {}
        pairs.append((k, p, b))

    OUT.mkdir(exist_ok=True)
    manifest = []
    for k, p, b in pairs:
        slug = k
        points = hist.get(p["vid"], [])
        (OUT / f"{slug}.html").write_text(page(slug, p, b, points), encoding="utf-8")
        prj = "head" if p["campaign"] == "MiniLED Education" else "mid"
        title = str(b.get("title") or p["kol"]).strip().replace("\n", "")
        manifest.append({
            "slug": slug, "title": title, "subtitle": f"{p['kol']} · {p['campaign']}",
            "project": prj, "kol": p["kol"], "market": "", "duration": "",
            "score": f"{fmt(p['views'])} 播放", "file": f"reports/{slug}.html",
            "views": p["views"], "er": p["er"],
        })
        print(f"{slug:<14} {prj:<5} {fmt(p['views']):>8} 播放  {len(points)} 个快照")

    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共 {len(manifest)} 页 → {OUT}")


if __name__ == "__main__":
    main()
