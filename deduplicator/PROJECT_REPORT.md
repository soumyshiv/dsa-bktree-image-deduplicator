# Metric Space Image Deduplication via Burkhard-Keller Trees (BK-Tree)
**Course:** Data Structures & Algorithms (DSA)  
**Project Category:** Advanced Non-Linear Metric Trees & Algorithmic Optimization

---

## 1. Abstract & Problem Statement
Traditional duplicate detection algorithms rely on exact hashing (e.g., MD5, SHA-256) which collapse under the slightest 1-pixel alteration, compression artifact, or camera tilt ($O(1)$ lookup for exact duplicates, but $O(N)$ failure for near-duplicates). 

Conversely, naive near-duplicate detection requires comparing a query image against all $N$ images in an $O(N)$ exhaustive linear scan, which is computationally prohibitive for large collections.

This project implements a **Burkhard-Keller Tree (BK-Tree)** in a **discrete metric space** paired with a **100-bit multi-channel perceptual hash**. By utilizing the **Triangle Inequality**, the search space is pruned systematically, reducing search complexity from linear $O(N)$ to sub-linear $O(N^\alpha)$ where $\alpha < 1$.

---

## 2. Theoretical Foundations: Metric Spaces
A set $X$ with a real-valued distance function $d: X \times X \to \mathbb{R}$ is a **metric space** if and only if it satisfies four fundamental axioms for all $x, y, z \in X$:

1. **Non-negativity:**  
   $$d(x, y) \ge 0$$
2. **Identity of Indiscernibles:**  
   $$d(x, y) = 0 \iff x = y$$
3. **Symmetry:**  
   $$d(x, y) = d(y, x)$$
4. **Triangle Inequality:**  
   $$d(x, z) \le d(x, y) + d(y, z)$$

### The Metric: Hamming Distance
Each image is represented as a 100-bit perceptual feature vector $H \in \{0, 1\}^{100}$.  
The distance between two hashes $H_1, H_2$ is the **Hamming Distance**:
$$d_H(H_1, H_2) = \sum_{i=1}^{100} (H_{1}[i] \oplus H_{2}[i])$$
The Hamming distance is a mathematically proven discrete metric satisfying all four axioms, making it strictly compatible with the BK-Tree.

---

## 3. Data Structure: Burkhard-Keller Tree (BK-Tree)

### Node Representation
Each `BKNode` contains:
* `img_hash`: The 100-bit perceptual hash vector acting as the pivot for this subtree.
* `paths`: A dynamic list of file paths (handles exact duplicates where $d = 0$).
* `children`: A hash map where `key = distance` (integer from $1$ to $100$) and `value = BKNode`.

### Insertion Algorithm ($O(\log N)$ average)
1. If root is null, create root with $(H, \text{path})$.
2. If root exists, compute distance $d = d_H(H, \text{curr.hash})$.
3. If $d = 0$, append path to `curr.paths` (collision handling).
4. If child at edge distance $d$ exists, recurse down: $\text{curr} = \text{curr.children}[d]$.
5. Else, create new `BKNode` at `curr.children[d]`.

### Mathematical Proof of Triangle Inequality Pruning
Given:
* Query target hash $Q$
* Current node (pivot) hash $P$ with $d_1 = d(Q, P)$
* Tolerance threshold $\tau$ (find all images with $d(Q, X) \le \tau$)
* A child node $C$ connected by an edge of weight $d_2 = d(P, C)$

By the Triangle Inequality:
$$d(Q, P) \le d(Q, C) + d(P, C) \implies d(Q, C) \ge |d_1 - d_2|$$
$$d(Q, C) \le d(Q, P) + d(P, C) \implies d(Q, C) \le d_1 + d_2$$

Combining these bounds:
$$|d_1 - d_2| \le d(Q, C) \le d_1 + d_2$$

Therefore, a subtree rooted at child $C$ can contain a valid match ($d(Q, C) \le \tau$) **only if**:
$$d_1 - \tau \le d_2 \le d_1 + \tau$$

**Pruning Rule:**  
Any branch where $d_2 < d_1 - \tau$ or $d_2 > d_1 + \tau$ is **guaranteed to contain 0 valid matches** and is safely pruned from traversal!

---

## 4. Complexity Analysis

| Operation | Naive Linear Scan | BK-Tree (Average Case) | BK-Tree (Worst Case) |
|---|---|---|---|
| **Tree Construction** | $O(1)$ (append to list) | $O(N \log N)$ | $O(N^2)$ (degenerate tree) |
| **Search / Query** | $O(N)$ exhaustive | $O(N^\alpha), \alpha < 1$ (Sub-linear) | $O(N)$ (tolerance $\tau \to \infty$) |
| **Auxiliary Space** | $O(N)$ array | $O(N)$ tree nodes | $O(N)$ tree nodes |
| **Queue Pop Operation** | N/A | $O(1)$ (`collections.deque`) | $O(1)$ |

---

## 5. Key Algorithmic Upgrades
1. **Live Algorithmic Benchmark Engine:**  
   Every query executes both the pruned BK-Tree search and a naive $O(N)$ linear scan on the identical dataset, reporting real-time execution times in milliseconds, exact nodes inspected, and speedup ratio.
2. **$O(1)$ Deque Queue:**  
   Replaced $O(k)$ array shifts (`list.pop(0)`) with double-ended queue `collections.deque.popleft()`.
3. **Tree Inspection & Structural Analytics:**  
   Calculates tree height, node distribution, and branching factors on demand.
