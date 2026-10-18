# 🌲 Burkhard-Keller (BK-Tree) Metric Space Image Deduplicator

> **Course:** Data Structures & Algorithms (DSA)  
> **Topic:** Advanced Non-Linear Metric Trees & Triangle Inequality Pruning  
> **Architectural Paradigm:** Dual-Surface Suite (Modern Web Dashboard + Desktop GUI)  
> **Student:** Soumyshiv Das (Registration No: `2502051963`)

### 📄 Academic Project Report & Coursework Deliverables
- **Official Final Report (21 Pages, PDF)**: [`report/SoumyshivDas.2502051963.pdf`](report/SoumyshivDas.2502051963.pdf)
- **Official Presentation (12 Slides, 16:9 PPTX)**: [`report/SoumyshivDas.2502051963.pptx`](report/SoumyshivDas.2502051963.pptx)
- **Comprehensive Academic Report (Markdown)**: [`report/PROJECT_REPORT.md`](report/PROJECT_REPORT.md)
- **Standalone LaTeX Source (Overleaf / pdfLaTeX)**: [`report/DSA_Project_Report.tex`](report/DSA_Project_Report.tex)
- **Automated Deliverable Builders**: [`report/generate_report.py`](report/generate_report.py), [`report/generate_pptx.py`](report/generate_pptx.py)

---

## 🚀 Quickstart: Run Directly from GitHub

Get the entire suite running on macOS, Windows, or Linux in **under 60 seconds**:

### 1. Clone the Repository
```bash
git clone https://github.com/soumyshiv/dsa-bktree-image-deduplicator.git
cd dsa-bktree-image-deduplicator
```

### 2. (Optional but Recommended) Create a Virtual Environment
```bash
# On macOS / Linux:
python3 -m venv venv
source venv/bin/activate

# On Windows (Command Prompt / PowerShell):
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
> *(On macOS systems without an active virtualenv, you can run: `python3 -m pip install -r requirements.txt`)*

---

### 4. Launch the Application

#### 🌟 Option A: Flagship Modern Web Studio (Recommended)
```bash
python3 run.py
```
* Automatically opens in your browser at **`http://localhost:8080`**.
* **Zero extra server dependencies**: Built on Python's native `http.server`.
* Features the **Duplicate Clusters** tab, **Interactive Visual Diff Slider**, live $O(N)$ benchmark telemetry, and a **"⚡ Load Demo Dataset"** one-click button with 72 pre-bundled test images.

#### 🖥️ Option B: Native Desktop GUI (CustomTkinter Edition)
```bash
python3 run.py --desktop
```
* Standalone desktop window for local batch culling, EXIF inspection, and recycle bin staging.


---

## 🎯 Problem Statement & Theoretical Foundations

### The Problem
* **Exact Hashing (MD5, SHA-256):** Provides $O(1)$ lookup for byte-for-byte identical files, but collapses under a single-pixel modification, slight crop, compression artifact, or camera tilt ($0\%$ recall).
* **Naive Linear Scan:** Compares a query image against all $N$ images via pairwise distance, costing an impractical $O(N)$ comparisons per query.

### The Solution: Metric Space & BK-Tree
This project maps images into a **discrete metric space** using a **100-bit multi-channel perceptual hash** $H \in \{0, 1\}^{100}$ and indexes them using a **Burkhard-Keller Tree (BK-Tree)**.

A set $X$ with distance function $d: X \times X \to \mathbb{R}$ is a **metric space** because the **Hamming Distance** strictly satisfies all 4 fundamental axioms:
1. **Non-negativity:** $d(x, y) \ge 0$
2. **Identity of Indiscernibles:** $d(x, y) = 0 \iff x = y$
3. **Symmetry:** $d(x, y) = d(y, x)$
4. **Triangle Inequality:** $d(x, z) \le d(x, y) + d(y, z)$

---

## ⚡ The Triangle Inequality Pruning Proof

Given:
* Query image hash $Q$
* Current tree pivot node $P$ with distance $d_1 = d(Q, P)$
* Tolerance threshold $\tau$ (find all images with $d(Q, X) \le \tau$)
* A subtree branch connected to child $C$ with edge weight $d_2 = d(P, C)$

Applying the Triangle Inequality:
$$d(Q, P) \le d(Q, C) + d(P, C) \implies d(Q, C) \ge |d_1 - d_2|$$
$$d(Q, C) \le d(Q, P) + d(P, C) \implies d(Q, C) \le d_1 + d_2$$

Combining both bounds:
$$|d_1 - d_2| \le d(Q, C) \le d_1 + d_2$$

**The Pruning Rule:**  
A child branch at distance $d_2$ can only contain a valid match ($d(Q, C) \le \tau$) if:
$$d_1 - \tau \le d_2 \le d_1 + \tau$$

Any branch outside this range $[d_1 - \tau, d_1 + \tau]$ is **mathematically proven to contain zero matches** and is safely pruned from traversal in $O(1)$!

---

## 📊 Algorithmic Complexity Comparison

| Metric / Operation | Naive Exhaustive Scan | BK-Tree (Average Case) | BK-Tree (Worst Case) |
|---|---|---|---|
| **Tree Construction** | $O(1)$ (append) | $O(N \log N)$ | $O(N^2)$ (degenerate tree) |
| **Search Time** | $O(N)$ linear | $O(N^\alpha)$ where $\alpha < 1$ (Sub-linear) | $O(N)$ (as $\tau \to \infty$) |
| **Auxiliary Memory** | $O(N)$ array | $O(N)$ tree nodes | $O(N)$ tree nodes |
| **Queue Pop Operation** | N/A | $O(1)$ (`collections.deque.popleft()`) | $O(1)$ |

---

## 🧪 Verification & Automated Testing Suite

The project includes property-based mathematical verification and empirical complexity benchmarking:

### 1. Run Automated Unit & Metric Axiom Tests
```bash
python3 -m unittest deduplicator/tests/test_bktree.py -v
```
* **Metric Axiom Tests:** Strictly proves that the 100-bit perceptual Hamming metric satisfies all 4 mathematical axioms (Non-negativity, Identity of Indiscernibles, Symmetry, and Triangle Inequality over 1,000 random triads).
* **Equivalence Guarantee:** Proves that BK-Tree Triangle Inequality pruning produces the exact same result set as an exhaustive $O(N)$ linear scan across all tolerance thresholds.
* **Connected Component Clustering:** Validates Disjoint Set Union (DSU) duplicate partitioning and highest-resolution master election.

### 2. Run Algorithmic Benchmark Suite & Report Generator
```bash
python3 deduplicator/benchmark_suite.py
```
* Profiles dataset scales $N \in [50, 100, 250, 500, 1000]$ across multiple tolerance radii $\tau \in [8, 12, 16]$.
* Generates an academic Markdown benchmark report with speedup and pruning statistics: [`BENCHMARK_RESULTS.md`](file:///Users/soumyshivdas/Documents/College/DSA%20project/deduplicator/BENCHMARK_RESULTS.md).

---

## 📁 Repository Structure

```
.
├── run.py                     # Unified entrypoint launcher (Web Studio & Desktop GUI)
├── requirements.txt           # Project dependencies (Pillow, numpy, customtkinter)
├── sample_images/             # Bundled demo dataset (exact & near-duplicates)
├── README.md                  # Project documentation & grading guide
│
├── report/                    # Official Academic Coursework Deliverables
│   ├── SoumyshivDas.2502051963.pdf  # Final 21-Page Official Project Report (PDF)
│   ├── PROJECT_REPORT.md      # Comprehensive Academic Markdown Report
│   ├── DSA_Project_Report.tex # Standalone LaTeX Source (for Overleaf / pdfLaTeX)
│   └── generate_report.py     # Automated report compilation script
│
└── deduplicator/              # Core Implementation & Dashboards
    ├── web_app.py             # Multi-threaded HTTP server, caching, & REST API
    ├── index.html             # Flagship Web Studio (Clusters tab, Curtain Slider, SVG Visualizer)
    ├── app.py                 # CustomTkinter Desktop GUI edition
    ├── bktree.py              # BKTree, BKNode, DisjointSetUnion, & Medoid Balancer
    ├── hash_logic.py          # 100-bit perceptual hashing & exact SHA-256 pre-filter
    ├── benchmark_suite.py     # Standalone empirical benchmark profiler & report generator
    ├── BENCHMARK_RESULTS.md   # Generated complexity comparison report
    └── tests/
        └── test_bktree.py     # Automated unit & metric space axiom tests
```
