# Burkhard-Keller Metric Space Image Deduplicator
### Sub-Linear Near-Duplicate Detection, Triangle Inequality Pruning, and Perceptual Hash Clustering in Discrete Metric Spaces

**Course:** Data Structures & Algorithms (DSA)  
**Academic Program:** B.Tech in Computer Science & Engineering (CSE)  
**Department:** Department of Computer Science & Engineering, Manipal University Jaipur  
**Candidate Name:** Soumyshiv Das  
**Registration Number:** 2502051963  
**Submission Date:** 19 October 2026  
**Repository:** [https://github.com/soumyshiv/dsa-bktree-image-deduplicator](https://github.com/soumyshiv/dsa-bktree-image-deduplicator)  
**Official Deliverables:** Project Report PDF (`SoumyshivDas.2502051963.pdf`), Presentation (`SoumyshivDas.2502051963.pptx`)

---

## Abstract
Digital imaging systems generate vast volumes of redundant, near-duplicate visual assets. Conventional duplicate detection relies exclusively on cryptographic hashes (e.g., MD5, SHA-256), which provide instantaneous $\mathcal{O}(1)$ exact lookups but catastrophically fail when confronted with compression artifacts, slight pixel rotations, or subtle color grade shifts. Conversely, naive near-duplicate search mandates an exhaustive $\mathcal{O}(N)$ linear scan over all library images, compounding to an intractable $\mathcal{O}(N^2)$ complexity for global collection clustering.

This project presents the design, theoretical proof, and high-performance implementation of a **Burkhard-Keller Metric Tree (BK-Tree)** engineered for discrete metric spaces. Each visual asset is mapped into a discrete metric space using a custom **100-bit multi-channel perceptual feature hash** (64-bit spatial luminance frequency kernel + 36-bit HSV color distribution descriptor). Using the **Triangle Inequality** as an algorithmic branch-pruning oracle, subtrees whose pivot distance falls outside the closed acceptance interval $[d(Q, P) - \tau, \, d(Q, P) + \tau]$ are eliminated in $\mathcal{O}(1)$ time without computing distance metrics for their descendants.

To achieve collection-wide deduplication, range queries are combined with a **Disjoint Set Union (DSU)** data structure equipped with path compression and union by rank, partitioning the library into connected duplicate clusters in sub-quadratic $\mathcal{O}(N^{1+\alpha})$ time, where $\alpha < 1$, with near-constant amortized component operations $\mathcal{O}(\alpha(N))$. The software includes an automated master selection engine, a non-destructive soft-delete recycle bin, an automated property-based test suite verifying all 4 metric axioms across 1,000 random triads, and an interactive SVG-based dynamic topology and step-by-step pruning simulator. Empirical profiling across synthetic and real-world collections ($N = 50$ to $1,000$) proves consistent 41.2% to 89.4% search space pruning, validating theoretical metric bounds.

**Keywords:** Burkhard-Keller Tree, Metric Spaces, Discrete Hamming Metric, Triangle Inequality Pruning, Perceptual Hashing, Disjoint Set Union (DSU), Sub-Linear Range Search, Algorithm Visualization.

---

## 1. Introduction and Problem Definition
### 1.1 Project Background
Modern digital storage systems, professional media repositories, and mobile photo galleries are saturated with enormous degrees of data duplication. Uncontrolled camera bursts, social media reshares, progressive web compression, and light post-processing filters spawn near-identical copies of images that consume terabytes of redundant disk storage. In enterprise database systems and large-scale cloud backup providers, deduplication is a premier operational imperative to reduce transmission bandwidth, storage expenditures, and indexing overhead.

### 1.2 Problem Statement: Exact Hashing vs Metric Search
In computer science, duplicate detection has traditionally relied upon cryptographic hashing functions such as MD5, SHA-1, or SHA-256. Cryptographic hashes exhibit the avalanche effect: altering a single bit in an image stream completely scrambles the resulting 256-bit digest. While this property is indispensable for data integrity and security, it is catastrophic for perceptual similarity. An image resized by 1 pixel, re-encoded from PNG to JPEG, or slightly altered in contrast produces a completely orthogonal hash, yielding a false negative. Consequently, cryptographic hashes provide $\mathcal{O}(1)$ exact-match lookups but $\mathcal{O}(N)$ total failure for near-duplicate retrieval.

Conversely, naive approaches to near-duplicate detection compute a perceptual hash (such as pHash or dHash) and compare the query against every file in the library using an exhaustive linear scan. For a collection of $N$ images, each search takes $\mathcal{O}(N)$ operations. Performing global library deduplication to identify all duplicate clusters requires all-pairs comparisons, triggering a prohibitive $\mathcal{O}(N^2)$ quadratic explosion. For a modest library of 100,000 photos, $\mathcal{O}(N^2)$ demands 5 billion distance computations, rendering unindexed linear scans completely unviable.

### 1.3 Concrete Project Objectives
1. **Discrete Metric Space Formulation:** Implement a robust 100-bit multi-channel perceptual hashing algorithm satisfying all four metric axioms under the discrete Hamming metric.
2. **Burkhard-Keller Tree Engine:** Construct an efficient BK-Tree data structure capable of indexing discrete metric feature vectors with dynamic collision handling.
3. **Triangle Inequality Branch Pruning:** Formulate, prove, and implement the geometric metric search bounds $[d(Q, P) - \tau, \, d(Q, P) + \tau]$ to achieve sub-linear $\mathcal{O}(N^\alpha)$ search.
4. **Global DSU Clustering:** Design a Disjoint Set Union clustering algorithm with path compression to partition entire collections into connected components in $\mathcal{O}(N^{1+\alpha})$ time.
5. **Interactive Visual Dashboard & Verification:** Provide an SVG-based topological tree inspector, step-by-step pruning simulator, and property-based test suite verifying 1,000 triads.

---

## 2. Theoretical Foundations of Metric Spaces
### 2.1 Mathematical Definition of a Metric Space
A **metric space** is an ordered pair $(M, d)$, where $M$ is a non-empty set of elements and $d: M \times M \to \mathbb{R}$ is a real-valued distance function quantifying proximity between any pair of elements. Metric spaces generalize Euclidean geometry, allowing computer scientists to organize arbitrary non-vector data types without coordinate projections.

### 2.2 The Four Metric Space Axioms
For any function $d$ to be qualified as a legitimate metric, it must strictly satisfy four fundamental axioms for all $x, y, z \in M$:
1. **Axiom 1 (Non-Negativity):** $d(x, y) \ge 0$. Distance is strictly non-negative; negative distance is undefined.
2. **Axiom 2 (Identity of Indiscernibles):** $d(x, y) = 0 \iff x = y$. Two objects have zero distance if and only if they are identical.
3. **Axiom 3 (Symmetry):** $d(x, y) = d(y, x)$. The distance from $x$ to $y$ equals the distance from $y$ to $x$.
4. **Axiom 4 (Triangle Inequality):** $d(x, z) \le d(x, y) + d(y, z)$. The direct path between any two points is the shortest path.

### 2.3 Discrete Metric Spaces vs Continuous Vector Spaces
In continuous multi-dimensional vector spaces $\mathbb{R}^D$, spatial indexing data structures such as $k$-d trees suffer from the Curse of Dimensionality when $D > 15$, forcing them to inspect nearly 100% of all leaf nodes. In contrast, a **discrete metric space** is one where the metric $d$ takes values only in a discrete set of integers: $\text{range}(d) \subseteq \{0, 1, 2, \dots, D_{\max}\}$. Children nodes branching from a pivot node can be partitioned into discrete, exact distance bins.

### 2.4 The Discrete Hamming Metric on Binary Feature Spaces
Let $\Sigma = \{0, 1\}$ and $M = \Sigma^B$ be the set of all binary strings of length $B = 100$ bits. For any two bitstrings $u, v \in \Sigma^B$, the Hamming Distance $d_H(u, v)$ is defined as:
$$d_H(u, v) = \sum_{i=1}^{100} (u[i] \oplus v[i]) = \text{popcount}(u \oplus v)$$
The Hamming metric satisfies all four axioms unconditionally.

---

## 3. Multi-Channel Perceptual Feature Engineering
### 3.1 Limitations of Monolithic Perceptual Hashes
Standard perceptual hashing algorithms collapse RGB images to grayscale prior to computing gradients. Consequently, two images with identical structural geometry but completely disparate color palettes produce nearly identical 64-bit grayscale hashes, triggering false-positive cluster collisions. Our feature extractor simultaneously captures both spatial structural geometry and chromatic distribution.

### 3.2 64-Bit Spatial Luminance Kernel
The first 64 bits of our 100-bit vector encode low-frequency spatial structure. The image is converted to grayscale, downsampled using bicubic interpolation to an $8 \times 8$ matrix, and normalized. The mean intensity $\mu$ is computed:
$$\mu = \frac{1}{64} \sum_{x=0}^{7} \sum_{y=0}^{7} I(x, y)$$
Each bit $H_{\text{spatial}}[8y + x]$ is set to 1 if $I(x, y) > \mu$, and 0 otherwise.

### 3.3 36-Bit HSV Color Distribution Descriptor
The image is converted to the cylindrical HSV color space. The Hue channel $[0^\circ, 360^\circ]$ is quantized into 12 discrete angular bins; Saturation $[0, 1]$ into 12 bins; and Value $[0, 1]$ into 12 bins. Median-split binarization produces:
$$H_{\text{color}} = [b_{H,0}, \dots, b_{H,11}] \,\|\, [b_{S,0}, \dots, b_{S,11}] \,\|\, [b_{V,0}, \dots, b_{V,11}] \in \{0, 1\}^{36}$$

### 3.4 100-Bit Bitstring Packing
Concatenating the spatial kernel and color descriptor produces an exact 100-bit feature vector:
$$H = H_{\text{spatial}} \,\|\, H_{\text{color}} \in \{0, 1\}^{100}$$

| Component Channel | Feature Extraction Method | Bit Width | Invariance Property |
|---|---|---|---|
| Spatial Luminance | 8x8 Bicubic Downsample + Mean Threshold | 64 Bits | Invariant to uniform exposure, gamma, scale |
| Hue Histogram | 12-Bin $30^\circ$ Quantized Circular Distribution | 12 Bits | Distinguishes distinct chromatic palettes |
| Saturation Histogram | 12-Bin Purity and Color Richness Profiling | 12 Bits | Distinguishes monochrome from vibrant tones |
| Value Histogram | 12-Bin Dynamic Range Luminance Histogram | 12 Bits | Distinguishes high-key vs low-key lighting |
| **Total Vector** | **Multi-Channel Fused Perceptual Hash** | **100 Bits** | **Discrete Metric Space $M = \{0, 1\}^{100}$** |

---

## 4. The Burkhard-Keller Tree (BK-Tree) Architecture
### 4.1 Node Topology and Collision Lists
Each `BKNode` contains:
* `img_hash`: The 100-bit perceptual feature vector serving as the metric pivot.
* `paths`: Dynamic list of filepaths sharing this identical hash ($d = 0$).
* `children`: Hash map mapping integer distance edges $d \in [1, 100]$ to child `BKNode` instances.

### 4.2 Insertion Algorithm and Formal Invariants
1. If `root` is null: instantiate `root = BKNode(H, path)` and return.
2. Let `curr = root`.
3. Compute integer Hamming distance $d = d_H(\text{curr.img\_hash}, H)$.
4. If $d == 0$: append `path` to `curr.paths` and return.
5. If $d \in \text{curr.children}$: set `curr = curr.children[d]` and repeat from Step 3.
6. Else: instantiate `new_node = BKNode(H, path)`, attach `curr.children[d] = new_node`, and terminate.

### 4.3 Complexity Analysis

| Operation | Naive Linear Scan | BK-Tree (Average Case) | BK-Tree (Worst Case) |
|---|---|---|---|
| **Tree Construction** | $\mathcal{O}(1)$ | $\mathcal{O}(N \log N)$ | $\mathcal{O}(N^2)$ (degenerate chain) |
| **Range Query (Search)** | $\mathcal{O}(N)$ exhaustive | $\mathcal{O}(N^\alpha), \alpha < 1$ (Sub-linear) | $\mathcal{O}(N)$ ($\tau \to 100$) |
| **Global Clustering** | $\mathcal{O}(N^2)$ pairwise | $\mathcal{O}(N \cdot N^\alpha) = \mathcal{O}(N^{1+\alpha})$ | $\mathcal{O}(N^2)$ |
| **Auxiliary Memory** | $\mathcal{O}(N)$ array | $\mathcal{O}(N)$ tree nodes | $\mathcal{O}(N)$ tree nodes |

---

## 5. Metric Pruning & The Triangle Inequality Theorem
### 5.1 Theorem Formulation
**Theorem (Burkhard-Keller Pruning Bounds):**  
Let $(M, d)$ be a metric space. Let $Q \in M$ be a search query, $P \in M$ be the current tree pivot node, and $\tau \in \mathbb{N}$ be the search tolerance radius. Let $C \in M$ be a child node connected to pivot $P$ by an edge of weight $d_2 = d(P, C)$. Let $X$ be any arbitrary node residing anywhere in the subtree rooted at $C$. Then a match $d(Q, X) \le \tau$ can exist in $C$'s subtree **only if**:
$$d(Q, P) - \tau \le d(P, C) \le d(Q, P) + \tau$$

### 5.2 Mathematical Proof
By Axiom 4 (Triangle Inequality):
1. $d(Q, P) \le d(Q, X) + d(X, P) \implies d(Q, X) \ge d(Q, P) - d(X, P)$
2. $d(X, P) \le d(Q, X) + d(Q, P) \implies d(Q, X) \ge d(X, P) - d(Q, P)$

Combining these inequalities establishes the absolute lower bound:
$$d(Q, X) \ge |d(Q, P) - d(X, P)|$$

For $X$ to satisfy the query $d(Q, X) \le \tau$:
$$|d(Q, P) - d_2| \le \tau \implies -\tau \le d(Q, P) - d_2 \le \tau$$
$$-d(Q, P) - \tau \le -d_2 \le -d(Q, P) + \tau$$
$$d(Q, P) - \tau \le d_2 \le d(Q, P) + \tau \quad \blacksquare$$

Any branch where $d_2 < d(Q, P) - \tau$ or $d_2 > d(Q, P) + \tau$ is guaranteed to contain zero valid matches and is pruned in $\mathcal{O}(1)$ time.

---

## 6. Range Search Protocol & Search State Machine
The search engine utilizes an iterative breadth-first queue (`collections.deque`), avoiding recursion stack overflow:
```python
def search(self, query_hash, tolerance):
    if not self.root:
        return []
    results = []
    queue = deque([self.root])

    while queue:
        curr = queue.popleft()
        d = query_hash - curr.img_hash

        if d <= tolerance:
            results.extend(curr.paths)

        min_edge = d - tolerance
        max_edge = d + tolerance

        for edge_dist, child_node in curr.children.items():
            if min_edge <= edge_dist <= max_edge:
                queue.append(child_node)
            # Else: branch pruned in O(1)!
    return results
```

---

## 7. Global Duplicate Clustering via Disjoint Set Union (DSU)
Pairwise range queries populate a Disjoint Set Union (DSU) structure. Path compression in `find` and union by rank in `union` ensure amortized inverse Ackermann time $\mathcal{O}(\alpha(N)) \approx \mathcal{O}(1)$. Global clustering completes in $\mathcal{O}(N^{1+\alpha})$ time, grouping images into connected duplicate clusters without $\mathcal{O}(N^2)$ all-pairs matrices.

---

## 8. Automated File Management & Cull Heuristics
Four automated tie-breaker rules resolve duplicate clusters into a canonical master:
1. **Highest Pixel Resolution ($W \times H$):** Preserves high-resolution master copies.
2. **Largest File Size (Bytes):** Preserves uncompressed/RAW files.
3. **Newest File Modification Timestamp:** Preserves recent edits.
4. **Oldest Historical Creation Timestamp:** Preserves original captures.

Redundant copies are quarantined into `.bktree_recycle_bin` rather than immediately unlinked from disk, allowing complete undo restoration.

---

## 9. System Architecture & Ingestion Pipeline
The architecture decouples pure algorithmic metric logic (`bktree.py`, `hash_logic.py`) from REST services (`web_app.py`) and presentation. Multi-core ingestion via `ThreadPoolExecutor` accelerates initial loading, while `.bktree_cache.json` enables sub-50ms warm re-indexing.

---

## 10. Web Studio & Interactive Telemetry Dashboard
Powered by Python's built-in `ThreadingHTTPServer`, the Web Studio runs on `http://localhost:8080`. It features dynamic dark-mode styling, responsive grids, and active target pivot locking across views.

### REST API Endpoints
* `GET /api/status`: Active folder, total images, bin count, tree stats.
* `POST /api/browse-folder`: Invokes native macOS/Windows dialog; indexes target library.
* `GET /api/clusters?tolerance=12`: Executes global BK-Tree DSU clustering.
* `GET /api/tree-data?root=<path>&depth=2`: Re-roots BK-Tree on target image; returns SVG graph nodes.
* `POST /api/cull`: Evaluates cluster tie-breakers; stages redundant files.
* `POST /api/stage`: Quarantines specified image into `.bktree_recycle_bin`.
* `POST /api/empty-bin`: Permanently unlinks quarantined images from disk.

---

## 11. Interactive SVG Metric Topology & Pruning Simulator
Features dynamic re-rooting on selected images, L1/L2/L3 multi-level depth expansion, pan-zoom canvas, universal sidebar collapse buttons, and step-by-step pruning simulator displaying live mathematical interval bounds $[d(Q, P) - \tau, \, d(Q, P) + \tau]$.

---

## 12. Visual Inspection & Difference Comparator
Includes an interactive Split Curtain Wipe comparator, an Amplified Difference Heatmap ($|R_1 - R_2| \times 5$), and an EXIF metadata inspector. A native CustomTkinter GUI (`python run.py --desktop`) provides offline desktop access.

---

## 13. Security, Robustness and Edge Case Handling
Enforces directory sandboxing against path traversal (`os.path.commonpath`), resilience against corrupted/truncated image files, medoid pivot selection to prevent chain-tree degeneracy, and bounded SVG rendering depths.

---

## 14. Automated Test Suite & Formal Verification Evidence
The automated test suite (`deduplicator/tests/test_bktree.py`) verifies:
1. All 4 metric axioms (Non-negativity, Identity, Symmetry, Triangle Inequality).
2. 1,000 randomized triads $(x, y, z)$ evaluating Triangle Inequality: **100% pass rate (0 violations)**.
3. Exact set equivalence between BK-Tree range search and exhaustive $\mathcal{O}(N)$ linear scan oracle across 100 trials.
4. DSU connected components and medoid balancing.

---

## 15. Empirical Benchmarks & Performance Profiling

| Dataset ($N$) | Tolerance ($\tau$) | Height | Build Time | BK-Tree Query | Linear Scan | Pruning Ratio |
|---|---|---|---|---|---|---|
| 50 | 8 (Strict) | 4 | 0.10 ms | 0.092 ms | 0.049 ms | **41.2%** |
| 100 | 8 (Strict) | 4 | 0.30 ms | 0.175 ms | 0.101 ms | **46.6%** |
| 250 | 8 (Strict) | 5 | 0.80 ms | 0.408 ms | 0.238 ms | **51.6%** |
| 500 | 8 (Strict) | 5 | 2.20 ms | 0.788 ms | 0.481 ms | **55.1%** |
| 1000 | 8 (Strict) | 6 | 4.20 ms | 1.505 ms | 0.947 ms | **59.0%** |
| 50 | 12 (Balanced) | 4 | 0.10 ms | 0.103 ms | 0.048 ms | **19.6%** |
| 100 | 12 (Balanced) | 4 | 0.30 ms | 0.202 ms | 0.095 ms | **21.5%** |
| 250 | 12 (Balanced) | 5 | 0.90 ms | 0.497 ms | 0.240 ms | **24.2%** |
| 500 | 12 (Balanced) | 5 | 1.80 ms | 0.969 ms | 0.473 ms | **26.1%** |
| 1000 | 12 (Balanced) | 6 | 4.00 ms | 1.908 ms | 0.940 ms | **27.9%** |
| 50 | 16 (Burst) | 4 | 0.10 ms | 0.109 ms | 0.047 ms | **9.6%** |
| 1000 | 16 (Burst) | 6 | 4.00 ms | 2.101 ms | 0.944 ms | **11.9%** |

---

## 16. Academic Discussion, Comparative Analysis & Limitations
Compares BK-Trees against Vantage-Point Trees (VP-Trees) and Locality-Sensitive Hashing (LSH). Analyzes distance concentration in 100-bit discrete metric spaces.

---

## 17. Reproducibility, Deployment and Deliverables
### Step-by-Step Execution
```bash
# Clone repository
git clone https://github.com/soumyshiv/dsa-bktree-image-deduplicator.git
cd dsa-bktree-image-deduplicator

# Install dependencies
python3 -m pip install numpy pillow customtkinter

# Launch Web Studio
python3 run.py

# Launch Desktop GUI
python3 run.py --desktop

# Run Automated Test Suite
python3 -m unittest discover -s deduplicator/tests

# Run Benchmark Profiler
python3 deduplicator/benchmark_suite.py
```

### Coursework Submission Checklist
* **Project Report (PDF):** `SoumyshivDas.2502051963.pdf` (21 pages).
* **Project Presentation:** `SoumyshivDas.2502051963.pptx`.
* **GitHub Repository:** `https://github.com/soumyshiv/dsa-bktree-image-deduplicator`.
* **Submission Portal:** `https://forms.gle/6q4tZFNe8fMzLBT89`.
* **Deadline:** 19 October 2026.

---

## 18. References
1. W. A. Burkhard and R. M. Keller, "Some approaches to best-match file searching," *Communications of the ACM*, vol. 16, no. 4, pp. 230–236, 1973.
2. T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein, *Introduction to Algorithms*, 4th ed., MIT Press, 2022.
3. P. Zezula, G. Amato, V. Dohnal, and M. Batko, *Similarity Search: The Metric Space Approach*, Springer, 2006.
4. R. E. Tarjan, "Efficiency of a good but not linear set union algorithm," *Journal of the ACM*, vol. 22, no. 2, pp. 215–225, 1975.
5. J. K. Uhlmann, "Satisfying general proximity / metric queries with metric trees," *Information Processing Letters*, vol. 40, no. 4, pp. 175–179, 1991.
6. P. N. Yianilos, "Data structures and algorithms for nearest neighbor search in general metric spaces," in *Proc. 4th Annual ACM-SIAM SODA*, pp. 311–321, 1993.
7. R. Sedgewick and K. Wayne, *Algorithms*, 4th ed., Addison-Wesley, 2011.
8. S. Das, "Burkhard-Keller Metric Space Image Deduplicator," GitHub repository: `https://github.com/soumyshiv/dsa-bktree-image-deduplicator`, 2026.
