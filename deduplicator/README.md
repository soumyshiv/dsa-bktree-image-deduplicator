# 🌲 BK-Tree Metric Space Image Deduplicator (Pro Edition)

A high-performance Near-Duplicate Image Detection & Culling Suite built on **Burkhard-Keller Trees (BK-Tree)** in discrete metric space using **100-bit multi-channel perceptual hashing**.

---

## 🚀 How to Run

Activate your conda environment and run:

### 1. Modern Web Dashboard (Recommended)
```bash
python run.py
```
> Automatically opens your default browser at `http://localhost:8080`.  
> Features live algorithmic benchmark telemetry, interactive SVG tree explorer, and dark glassmorphic UI.

### 2. Desktop GUI (CustomTkinter)
```bash
python run.py --desktop
```

---

## 📚 Project Structure

```
deduplicator/
├── web_app.py          # Zero-dependency async HTTP server & REST API
├── index.html          # Modern Single-Page App (Tailwind CSS, SVG Tree visualizer)
├── bktree.py           # Burkhard-Keller Tree with O(1) deque search & graph export
├── hash_logic.py       # 100-bit multi-channel perceptual hash & Hamming metric
├── app.py              # CustomTkinter Desktop GUI edition
├── PROJECT_REPORT.md   # Complete Academic Project Report
└── README.md           # Instructions
```

---

## ⚡ Algorithmic Highlights
* **Metric Space Indexing**: Utilizes discrete Hamming distance satisfying the Triangle Inequality ($d(x, z) \le d(x, y) + d(y, z)$).
* **Search Space Pruning**: Filters out non-matching subtrees in $O(1)$ without visiting.
* **Live Benchmarking**: Automatically benchmarks BK-Tree range search against naive exhaustive $O(N)$ linear scanning in real time.
* **Non-destructive Batch Staging**: Internal Recycle Bin staging before permanent disk deletion.
