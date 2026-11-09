#!/usr/bin/env python3
"""把一段 mp4 变成可读的「画面证据包」：关键帧 + 切点统计 + 联系表。

用法:
    python3 scripts/extract_frames.py <video.mp4> <out_dir> [--cuts 40]

产出:
    <out_dir>/f_00.jpg ...            均匀抽帧（默认 24 张，JPEG q=3，长边 960）
    <out_dir>/contact.jpg             4 列联系表（带时间戳烧字）
    <out_dir>/report.json             时长 / 帧率 / 均匀抽帧时间点 / 切点数量 / 平均镜头长度
"""
import json
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,avg_frame_rate:format=duration",
             "-of", "json", path])
    d = json.loads(r.stdout)
    st = d["streams"][0]
    num, den = st["avg_frame_rate"].split("/")[:2]
    fps = float(num) / float(den) if float(den) else 0.0
    return dict(width=st["width"], height=st["height"], fps=round(fps, 3),
                duration=round(float(d["format"]["duration"]), 2))


def mmss(s):
    return f"{int(s)//60}:{int(s) % 60:02d}"


def cuts(path, thr=0.32):
    """硬切检测：showinfo 里每条 pts_time 就是一个切点。"""
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-filter:v",
             f"select='gt(scene,{thr})',showinfo", "-f", "null", "-"])
    ts = []
    for line in r.stderr.splitlines():
        if "pts_time:" in line:
            try:
                ts.append(float(line.split("pts_time:")[1].split()[0]))
            except ValueError:
                pass
    return sorted(ts)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, out = sys.argv[1], sys.argv[2]
    n = 24
    if "--cuts" in sys.argv:
        n = int(sys.argv[sys.argv.index("--cuts") + 1])
    os.makedirs(out, exist_ok=True)

    meta = probe(src)
    dur = meta["duration"]
    pts = [round(dur * (i + 0.5) / n, 2) for i in range(n)]

    for i, t in enumerate(pts):
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", src,
             "-frames:v", "1", "-vf", "scale='min(960,iw)':-2",
             "-q:v", "3", os.path.join(out, f"f_{i:02d}.jpg")])

    # 联系表：4 列，每格烧时间戳
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", os.path.join(out, "f_%02d.jpg"),
         "-vf", "drawtext=text='%{pts\\:hms}':x=8:y=8:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6,"
         "tile=4x6:margin=6:padding=6", "-q:v", "3", os.path.join(out, "contact.jpg")])

    cut_ts = cuts(src)
    rep = dict(meta=meta, frames=pts, cut_count=len(cut_ts),
               avg_shot=round(dur / max(len(cut_ts), 1), 2),
               cuts=[round(t, 1) for t in cut_ts[:80]])
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    print(f"时长 {mmss(dur)} · {meta['width']}x{meta['height']} · {meta['fps']}fps")
    print(f"抽帧 {n} 张 → {out}/")
    print(f"硬切 {len(cut_ts)} 次 · 平均镜头 {rep['avg_shot']}s")


if __name__ == "__main__":
    main()
