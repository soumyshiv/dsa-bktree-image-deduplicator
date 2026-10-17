"""
Burkhard-Keller Tree (BK-Tree) Implementation for Metric Space Indexing.

A BK-Tree is a specialized metric tree data structure designed for fast, sub-linear
nearest-neighbor and range searches in discrete metric spaces.

Metric Space Properties (Triangle Inequality):
    Given elements x, y, z and distance metric d():
    1. d(x, y) >= 0              (Non-negativity)
    2. d(x, y) == 0 <=> x == y   (Identity of indiscernibles)
    3. d(x, y) == d(y, x)        (Symmetry)
    4. d(x, z) <= d(x, y) + d(y, z) (Triangle Inequality)

Search Pruning Principle:
    Let root have hash R, target query hash Q, and tolerance tau.
    For any child node C at edge distance d(R, C) = d_edge:
    By Triangle Inequality:
        |d(Q, R) - d(R, C)| <= d(Q, C) <= d(Q, R) + d(R, C)
    Therefore, child C can contain a match (d(Q, C) <= tau) ONLY IF:
        d(Q, R) - tau <= d_edge <= d(Q, R) + tau
    Any branch outside this range is safely pruned without visiting!
"""

from collections import deque
import os
import time
from typing import Any, Dict, List, Optional, Tuple


class BKNode:
    """Represents a single node in the BK-Tree."""

    def __init__(self, img_hash, file_path: str):
        self.img_hash = img_hash
        # Stores multiple file paths in case of identical hashes (distance = 0)
        self.paths: List[str] = [file_path]
        # Child subtrees mapped by discrete Hamming distance: Dict[int, BKNode]
        self.children: Dict[int, "BKNode"] = {}

    def total_subnodes(self) -> int:
        """Returns total number of nodes in this subtree including self."""
        count = 1
        for child in self.children.values():
            count += child.total_subnodes()
        return count

    def get_max_depth(self) -> int:
        """Returns the maximum depth of this subtree."""
        if not self.children:
            return 1
        return 1 + max(child.get_max_depth() for child in self.children.values())


class SearchBenchmark:
    """Holds runtime and algorithmic pruning statistics for a BK-Tree query."""

    def __init__(
        self,
        nodes_visited: int,
        total_nodes: int,
        bktree_time_ms: float,
        linear_scan_time_ms: float,
    ):
        self.nodes_visited = nodes_visited
        self.total_nodes = total_nodes
        self.nodes_pruned = max(0, total_nodes - nodes_visited)
        self.pruning_ratio = (
            (self.nodes_pruned / total_nodes * 100.0) if total_nodes > 0 else 0.0
        )
        self.bktree_time_ms = max(0.001, bktree_time_ms)
        self.linear_scan_time_ms = max(0.001, linear_scan_time_ms)
        self.speedup = self.linear_scan_time_ms / self.bktree_time_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes_visited": self.nodes_visited,
            "total_nodes": self.total_nodes,
            "nodes_pruned": self.nodes_pruned,
            "pruning_ratio": round(self.pruning_ratio, 1),
            "bktree_time_ms": round(self.bktree_time_ms, 3),
            "linear_scan_time_ms": round(self.linear_scan_time_ms, 3),
            "speedup": round(self.speedup, 1),
        }


class DisjointSetUnion:
    """
    Disjoint Set Union (DSU / Union-Find) with path compression and rank optimization.
    Time Complexity: Amortized O(alpha(N)) ~ O(1) per operation.
    """

    def __init__(self, elements):
        self.parent = {e: e for e in elements}
        self.rank = {e: 0 for e in elements}

    def find(self, item):
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, x, y) -> bool:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
        return True


class BKTree:
    """
    Burkhard-Keller Tree implementation with O(1) deque search
    and live algorithmic performance profiling.
    """

    def __init__(self):
        self.root: Optional[BKNode] = None
        self._total_entries: int = 0  # Total indexed image files
        self._unique_nodes: int = 0   # Total distinct hash nodes

    @property
    def total_entries(self) -> int:
        return self._total_entries

    @property
    def total_nodes(self) -> int:
        return self._unique_nodes

    def add(self, img_hash, file_path: str) -> None:
        """
        Inserts an image hash into the BK-Tree.
        Time Complexity: Average O(log N), Worst-case O(N).
        Space Complexity: O(1) auxiliary per insertion.
        """
        self._total_entries += 1
        if self.root is None:
            self.root = BKNode(img_hash, file_path)
            self._unique_nodes += 1
            return

        curr = self.root
        while True:
            dist = img_hash - curr.img_hash

            if dist == 0:
                # Collision: identical hash (distance 0), append to existing node
                curr.paths.append(file_path)
                return

            if dist in curr.children:
                curr = curr.children[dist]
            else:
                curr.children[dist] = BKNode(img_hash, file_path)
                self._unique_nodes += 1
                return

    def search_with_benchmark(
        self,
        target_hash,
        tolerance: int,
        all_items: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], SearchBenchmark]:
        """
        Performs a range query using Triangle Inequality pruning,
        while simultaneously benchmarking against a naive linear O(N) scan.
        """
        results: List[str] = []
        if self.root is None:
            empty_bench = SearchBenchmark(0, 0, 0.001, 0.001)
            return results, empty_bench

        # --- 1. BK-Tree Range Query with O(1) Deque ---
        nodes_visited = 0
        t0 = time.perf_counter()

        queue = deque([self.root])
        while queue:
            curr = queue.popleft()  # O(1) deque operation
            nodes_visited += 1

            dist = target_hash - curr.img_hash

            # If within tolerance, collect all paths stored in this node
            if dist <= tolerance:
                results.extend(curr.paths)

            # Pruning range: only branches where dist - tolerance <= d <= dist + tolerance
            min_dist = dist - tolerance
            max_dist = dist + tolerance

            for d, child in curr.children.items():
                if min_dist <= d <= max_dist:
                    queue.append(child)

        t1 = time.perf_counter()
        bktree_time_ms = (t1 - t0) * 1000.0

        # --- 2. Live Naive O(N) Linear Scan Benchmark ---
        linear_scan_time_ms = 0.001
        if all_items:
            t_linear_0 = time.perf_counter()
            _dummy_matches = []
            for path, h in all_items.items():
                if (target_hash - h) <= tolerance:
                    _dummy_matches.append(path)
            t_linear_1 = time.perf_counter()
            linear_scan_time_ms = max(0.001, (t_linear_1 - t_linear_0) * 1000.0)

        benchmark = SearchBenchmark(
            nodes_visited=nodes_visited,
            total_nodes=self._unique_nodes,
            bktree_time_ms=bktree_time_ms,
            linear_scan_time_ms=linear_scan_time_ms,
        )

        return results, benchmark

    def search(self, target_hash, tolerance: int) -> List[str]:
        """Standard search interface."""
        matches, _ = self.search_with_benchmark(target_hash, tolerance)
        return matches

    def find_all_duplicate_clusters(
        self,
        tolerance: int,
        all_items: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Global all-pairs duplicate cluster detection.
        Groups all indexed images into equivalence duplicate clusters where
        images within tolerance form connected components.

        Complexity:
            Using BK-Tree range queries: O(N * N^alpha) = O(N^(1+alpha)) where alpha < 1,
            compared to exhaustive pairwise comparison O(N^2).
        """
        t0 = time.perf_counter()
        if not all_items:
            return {
                "clusters": [],
                "total_clusters": 0,
                "total_duplicates": 0,
                "total_savings_mb": 0.0,
                "elapsed_ms": 0.0,
                "tolerance": tolerance,
            }

        paths = list(all_items.keys())
        dsu = DisjointSetUnion(paths)

        # 1. Query BK-Tree for each image to connect near-duplicate components
        for p, h in all_items.items():
            matches = self.search(h, tolerance)
            for m in matches:
                if m in dsu.parent:
                    dsu.union(p, m)

        # 2. Group paths by DSU root
        groups: Dict[str, List[str]] = {}
        for p in paths:
            root = dsu.find(p)
            groups.setdefault(root, []).append(p)

        # 3. Format clusters with size >= 2
        meta_dict = metadata or {}
        clusters = []
        total_redundant = 0
        total_savings_mb = 0.0

        cluster_idx = 1
        for root, group in groups.items():
            if len(group) < 2:
                continue

            # Sort group to find the "best candidate" (highest resolution, largest file size)
            def _score_image(fpath: str) -> Tuple[int, float, str]:
                m = meta_dict.get(fpath, {})
                dim_str = m.get("dimensions", "0 × 0")
                try:
                    w, h = [int(x.strip().split()[0]) for x in dim_str.split("×")]
                    res = w * h
                except Exception:
                    res = 0
                sz = float(m.get("size_mb", 0.0))
                return (res, sz, fpath)

            sorted_group = sorted(group, key=_score_image, reverse=True)
            best_master = sorted_group[0]
            redundant_files = sorted_group[1:]

            # Intra-cluster distances relative to best master
            master_hash = all_items.get(best_master)
            cluster_items = []
            for item_path in sorted_group:
                m = meta_dict.get(item_path, {})
                item_h = all_items.get(item_path)
                dist = (
                    (master_hash - item_h)
                    if (master_hash is not None and item_h is not None)
                    else 0
                )
                sim = (
                    max(0, 100 - dist)
                    if dist <= 22
                    else max(0, int(round(78 - (dist - 22) * 3.5)))
                )
                cluster_items.append({
                    "path": item_path,
                    "filename": os.path.basename(item_path),
                    "is_master": (item_path == best_master),
                    "distance_to_master": dist,
                    "similarity": sim,
                    "dimensions": m.get("dimensions", "N/A"),
                    "size_mb": m.get("size_mb", 0.0),
                    "format": m.get("format", "IMG"),
                })

            redundant_size = sum(
                meta_dict.get(p, {}).get("size_mb", 0.0) for p in redundant_files
            )
            total_redundant += len(redundant_files)
            total_savings_mb += redundant_size

            clusters.append({
                "cluster_id": cluster_idx,
                "master_path": best_master,
                "master_filename": os.path.basename(best_master),
                "items": cluster_items,
                "total_items": len(cluster_items),
                "redundant_count": len(redundant_files),
                "redundant_paths": redundant_files,
                "potential_savings_mb": round(redundant_size, 2),
            })
            cluster_idx += 1

        # Sort clusters by potential size savings descending
        clusters.sort(
            key=lambda c: (c["redundant_count"], c["potential_savings_mb"]),
            reverse=True,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "clusters": clusters,
            "total_clusters": len(clusters),
            "total_duplicates": total_redundant,
            "total_savings_mb": round(total_savings_mb, 2),
            "elapsed_ms": round(elapsed_ms, 2),
            "tolerance": tolerance,
        }

    @classmethod
    def build_balanced(cls, items: List[Tuple[Any, str]]) -> "BKTree":
        """
        Constructs a balanced BK-Tree using medoid pivot selection.
        Instead of arbitrary sequential insertion order, the root is chosen
        as the medoid (the element with minimal sum-of-distances to a sample),
        maximizing subtree dispersion and minimizing tree height.
        """
        tree = cls()
        if not items:
            return tree

        if len(items) == 1:
            h, p = items[0]
            tree.add(h, p)
            return tree

        # Select medoid from sample (up to 64 items for O(K^2) efficiency)
        sample = items[: min(64, len(items))]
        best_idx = 0
        min_total_dist = float("inf")
        for i, (h_i, _) in enumerate(sample):
            tot = sum(h_i - h_j for _, (h_j, _) in enumerate(sample))
            if tot < min_total_dist:
                min_total_dist = tot
                best_idx = i

        # Insert medoid first as root pivot
        pivot_h, pivot_p = items[best_idx]
        tree.add(pivot_h, pivot_p)

        # Insert remaining items
        for i, (h, p) in enumerate(items):
            if i != best_idx:
                tree.add(h, p)

        return tree


    def get_tree_stats(self) -> Dict[str, Any]:
        """Returns structural analytics about the tree."""
        if not self.root:
            return {
                "total_nodes": 0,
                "total_entries": 0,
                "height": 0,
                "root_branching": 0,
            }

        return {
            "total_nodes": self._unique_nodes,
            "total_entries": self._total_entries,
            "height": self.root.get_max_depth(),
            "root_branching": len(self.root.children),
        }

    def get_tree_graph(
        self,
        target_hash=None,
        tolerance: int = 12,
        max_depth: int = 3,
        max_children_per_node: int = 8,
    ) -> Dict[str, Any]:
        """
        Exports tree hierarchy for visualization in the web dashboard.
        Annotates nodes as:
        - 'target': The locked query target
        - 'match': Within tolerance (d <= tau)
        - 'visited': Inspected during search but outside tolerance
        - 'pruned': Skipped due to triangle inequality
        """
        if not self.root:
            return {}

        def _traverse(node: BKNode, edge_dist: int, depth: int, parent_visited: bool) -> Dict[str, Any]:
            filename = os.path.basename(node.paths[0]) if node.paths else "Node"
            
            # Compute distance to target if available
            dist_to_target = None
            status = "unvisited"
            if target_hash is not None:
                dist_to_target = target_hash - node.img_hash
                if dist_to_target == 0:
                    status = "target"
                elif dist_to_target <= tolerance:
                    status = "match"
                elif parent_visited:
                    status = "visited"
                else:
                    status = "pruned"

            children_data = []
            if depth < max_depth:
                sorted_edges = sorted(node.children.keys())[:max_children_per_node]
                for d in sorted_edges:
                    child = node.children[d]
                    # Determine if child branch is within pruning window
                    child_in_window = True
                    if target_hash is not None and dist_to_target is not None:
                        child_in_window = (dist_to_target - tolerance) <= d <= (dist_to_target + tolerance)
                    
                    child_dict = _traverse(child, edge_dist=d, depth=depth + 1, parent_visited=child_in_window)
                    children_data.append(child_dict)

            return {
                "name": filename,
                "path": node.paths[0],
                "hash_str": str(node.img_hash),
                "edge_distance": edge_dist,
                "dist_to_target": dist_to_target,
                "status": status,
                "exact_duplicates_count": len(node.paths),
                "children": children_data,
            }

        return _traverse(self.root, edge_dist=0, depth=1, parent_visited=True)
