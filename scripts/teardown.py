#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teardown.py · TCL KOL 视频拆解流水线

四个子命令，对应说话的四步：

  stats    读视频，出时长 / 镜头切点 / 每 30 秒节奏（直接喂给页面的脉冲柱）
  frames   按时间码抽帧，文件名就是时间码（直接对应页面里的 figcaption）
  sheet    把抽帧拼成一张联系表（一张图看清 12–20 帧，方便多模态读）
  scaffold 复制现成版式，生成一条新视频的报告页

用法示例：
  python3 scripts/teardown.py stats  ~/Downloads/video.mp4
  python3 scripts/teardown.py frames ~/Downloads/video.mp4 \
      --times 0:00,0:05,0:37,0:55,3:07,3:55 --labels 门店,店内,两台并排,背板,立标准,产品登场
  python3 scripts/teardown.py sheet  work/techflow-p8l/frames --out work/techflow-p8l/contact.jpg
  python3 scripts/teardown.py scaffold --slug samsung-s95f --title "Samsung S95F 首发评测拆解"

依赖：ffmpeg / ffprobe、Pillow（拼图用）。纯标准库，无其他包。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, **kw):
    """跑外部命令，失败时带回 stderr，避免静默出错。"""
    p = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if p.returncode != 0:
        sys.exit(f"[失败] {' '.join(cmd[:4])} ...\n{p.stderr[-800:]}")
    return p.stdout + p.stderr


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,duration,avg_frame_rate",
               "-show_entries", "format=duration", "-of", "json", str(path)])
    data = json.loads(out)
    st = (data.get("streams") or [{}])[0]
    dur = float(st.get("duration") or data.get("format", {}).get("duration") or 0)
    return {"width": st.get("width"), "height": st.get("height"),
            "duration": dur, "fps": st.get("avg_frame_rate")}


def mmss(seconds):
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"


def slug_time(seconds):
    """0:37 -> 00s ; 3:55 -> 3m55 — 与页面抽帧命名一致。"""
    s = int(round(seconds))
    m, sec = divmod(s, 60)
    return f"{m}m{sec:02d}" if m else f"{sec:02d}s"


# ---------------------------------------------------------------- stats
def cmd_stats(args):
    info = probe(args.video)
    dur = info["duration"]
    if not dur:
        sys.exit("[失败] 读不到时长，视频可能损坏或不是视频文件")

    # 场景切换检测：阈值越低越敏感（默认 0.3）
    # showinfo 走 info 级别日志，必须是 -v info（用 error 会一行都拿不到）
    raw = run(["ffmpeg", "-hide_banner", "-v", "info", "-i", str(args.video),
               "-vf", f"select='gt(scene,{args.threshold})',showinfo",
               "-f", "null", "-"])
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", raw)]
    cuts = [c for c in cuts if 0 < c < dur]

    buckets = int(dur // 30) + (1 if dur % 30 > 3 else 0)
    counts = [0] * buckets
    for c in cuts:
        idx = min(int(c // 30), buckets - 1)
        counts[idx] += 1
    peak = max(counts) or 1

    bars = "\n".join(
        f'        <div class="col{" hi" if c == peak else ("" if c < peak / 3 else " mid")}" '
        f'style="height:{max(6, int(c / peak * 100))}%" '
        f'title="{mmss(i*30)}-{mmss((i+1)*30)} · {c} cuts"></div>'
        for i, c in enumerate(counts))

    result = {
        "video": str(args.video),
        "duration": round(dur, 2),
        "duration_label": mmss(dur),
        "width": info["width"], "height": info["height"], "fps": info["fps"],
        "scene_threshold": args.threshold,
        "cuts_total": len(cuts),
        "avg_shot_seconds": round(dur / (len(cuts) + 1), 2),
        "per_30s": [{"from": mmss(i * 30), "to": mmss((i + 1) * 30),
                     "bucket": i, "cuts": c} for i, c in enumerate(counts)],
        "pulse_html": bars,
    }

    out = Path(args.out or (ROOT / "work" / Path(args.video).stem / "stats.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"时长 {result['duration_label']}（{dur:.1f}s） · {info['width']}×{info['height']}")
    print(f"镜头切点 {len(cuts)} 个 · 平均 {result['avg_shot_seconds']}s/镜头 · 阈值 {args.threshold}")
    if not cuts:
        print("[提示] 没有检测到切点：把 --threshold 调低（0.2 / 0.15），或换更敏感的检测。", file=sys.stderr)
    print("每 30 秒节奏：", " ".join(str(c) for c in counts))
    print(f"\n已写入 {out}")
    print("把 stats.json 里的 pulse_html 粘到报告页的 <div class=\"pulse\"> 里即可。")
    return result


# ---------------------------------------------------------------- frames
def parse_time(t):
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)                      # 秒
    parts = t.split(":")
    parts = [float(p) for p in parts]
    return sum(v * 60 ** i for i, v in enumerate(reversed(parts)))


def cmd_frames(args):
    if not args.times and not args.every:
        sys.exit("[失败] 要么给 --times，要么给 --every 30 先粗扫")
    if args.times:
        times = [parse_time(t.strip()) for t in args.times.split(",") if t.strip()]
    else:
        dur = probe(args.video)["duration"]
        step = args.every
        times, t = [], 0.0
        while t < dur - 0.5:
            times.append(round(t, 2))
            t += step
    labels = [l.strip() for l in (args.labels or "").split(",") if l.strip()]
    outdir = Path(args.out or (ROOT / "work" / Path(args.video).stem / "frames"))
    outdir.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, t in enumerate(times):
        name = slug_time(t)
        if i < len(labels):
            name += "-" + re.sub(r"[^\w\u4e00-\u9fff-]+", "", labels[i])
        dst = outdir / f"{name}.jpg"
        # -ss 放在 -i 前面 = 快速定位；-frames:v 1 只取一帧
        run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", str(args.video),
             "-frames:v", "1", "-vf", f"scale={args.width}:-2", "-q:v", "3",
             "-y", str(dst)])
        saved.append(dst)
        print(f"{mmss(t):>6}  →  {dst.name}")

    # 建一个 manifest，页面里 figcaption 直接照抄
    manifest = [{"time": mmss(t), "file": f.name} for t, f in zip(times, saved)]
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共 {len(times)} 帧 → {outdir}\nmanifest.json 里有时间码与文件名对照。")
    return outdir


# ---------------------------------------------------------------- sheet
def cmd_sheet(args):
    from PIL import Image, ImageDraw
    frames = sorted(Path(args.frames).glob("*.jpg"))
    if not frames:
        sys.exit(f"[失败] {args.frames} 里没有 jpg")

    cols = args.cols
    thumb_w = args.thumb
    rows = (len(frames) + cols - 1) // cols
    try:
        first = Image.open(frames[0])
        ratio = first.height / first.width
    except Exception:
        ratio = 9 / 16
    thumb_h = int(thumb_w * ratio)
    pad, label_h = 8, 22
    W = cols * thumb_w + (cols + 1) * pad
    H = rows * (thumb_h + label_h) + (rows + 1) * pad
    canvas = Image.new("RGB", (W, H), "#f4f5f7")
    draw = ImageDraw.Draw(canvas)

    for i, f in enumerate(frames):
        r, c = divmod(i, cols)
        x = pad + c * (thumb_w + pad)
        y = pad + r * (thumb_h + label_h + pad)
        im = Image.open(f).convert("RGB").resize((thumb_w, thumb_h))
        canvas.paste(im, (x, y))
        draw.text((x + 2, y + thumb_h + 4), f.stem[:28], fill="#344054")

    out = Path(args.out or (Path(args.frames) / "contact.jpg"))
    canvas.save(out, quality=88)
    print(f"联系表 {len(frames)} 帧 → {out}  （{W}×{H}）")


# ---------------------------------------------------------------- scaffold
def cmd_scaffold(args):
    src = ROOT / "index.html"
    dst_dir = ROOT / "reports"
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / f"{args.slug}.html"
    if dst.exists() and not args.force:
        sys.exit(f"[已存在] {dst}，加 --force 覆盖")

    html = src.read_text(encoding="utf-8")
    title = args.title or args.slug
    # 只换「认得出入口」的几处，正文留给分析者改
    html = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", html, count=1)
    html = re.sub(r'(<h1>).*?(<br>)', lambda m: m.group(1) + title + m.group(2),
                  html, count=1, flags=re.S)
    html = re.sub(r'(<h1>.*?<span class="thin">).*?(</span></h1>)',
                  lambda m: m.group(1) + (args.subtitle or "") + m.group(2),
                  html, count=1, flags=re.S)
    # 所有抽帧 src 指向本条视频的目录
    html = html.replace("assets/frames/", f"assets/frames/{args.slug}/")
    dst.write_text(html, encoding="utf-8")
    print(f"已生成 {dst}")
    print("接下来：改 focus（结论/评分）、七个维度正文、时间轴，把 frames 挪到 "
          f"assets/frames/{args.slug}/ 并改扩展名。")


def main():
    ap = argparse.ArgumentParser(description="TCL KOL 视频拆解流水线")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("stats", help="镜头切点与节奏统计")
    s.add_argument("video")
    s.add_argument("--threshold", type=float, default=0.3,
                   help="场景检测阈值，默认 0.3；切点太少就调低到 0.2")
    s.add_argument("--out")
    s.set_defaults(func=cmd_stats)

    f = sub.add_parser("frames", help="按时间码抽帧")
    f.add_argument("video")
    f.add_argument("--times", help="0:00,0:37,3:55 或 37,235（秒）")
    f.add_argument("--every", type=float, help="不指定 times 时，每 N 秒抽一张（先粗扫用）")
    f.add_argument("--labels", help="与 times 一一对应的中文标签，可留空")
    f.add_argument("--width", type=int, default=640)
    f.add_argument("--out")
    f.set_defaults(func=cmd_frames)

    sh = sub.add_parser("sheet", help="拼联系表")
    sh.add_argument("frames")
    sh.add_argument("--out")
    sh.add_argument("--cols", type=int, default=4)
    sh.add_argument("--thumb", type=int, default=320)
    sh.set_defaults(func=cmd_sheet)

    sc = sub.add_parser("scaffold", help="生成新报告页")
    sc.add_argument("--slug", required=True)
    sc.add_argument("--title")
    sc.add_argument("--subtitle")
    sc.add_argument("--force", action="store_true")
    sc.set_defaults(func=cmd_scaffold)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
