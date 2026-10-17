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
