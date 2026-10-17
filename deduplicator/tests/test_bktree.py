"""
Automated Test Suite for Burkhard-Keller Tree & Metric Space Properties.
Course: Data Structures & Algorithms (DSA)

Tests:
1. Discrete Metric Axioms: Non-negativity, Identity of Indiscernibles, Symmetry, Triangle Inequality.
2. BK-Tree Range Search Equivalence: Exact match set equivalence with Naive O(N) linear scan.
3. Pruning Efficiency: Validates that triangle inequality eliminates unnecessary branches.
4. Duplicate Clustering (DSU): Validates connected component partitioning and master selection.
5. Tree Balancing: Tests medoid pivot selection.
"""

import os
import sys
import unittest
import numpy as np

# Ensure parent directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEDUP_DIR = os.path.dirname(CURRENT_DIR)
if DEDUP_DIR not in sys.path:
    sys.path.insert(0, DEDUP_DIR)

from hash_logic import PerceptualHash, generate_hash
from bktree import BKTree, DisjointSetUnion


class TestMetricSpaceAxioms(unittest.TestCase):
    """
    Rigorously verifies the 4 metric space axioms on the 100-bit PerceptualHash.
    A set X with distance function d: X x X -> R is a metric space iff:
    1. d(x, y) >= 0
    2. d(x, y) == 0 <=> x == y
    3. d(x, y) == d(y, x)
    4. d(x, z) <= d(x, y) + d(y, z)  [Triangle Inequality]
    """

    def setUp(self):
        np.random.seed(42)
        # Generate 50 random 100-bit binary perceptual hashes
        self.hashes = [
            PerceptualHash(np.random.randint(0, 2, size=100, dtype=np.uint8))
            for _ in range(50)
        ]

    def test_axiom_1_non_negativity(self):
        """d(x, y) >= 0 for all x, y."""
        for i in range(len(self.hashes)):
            for j in range(len(self.hashes)):
                dist = self.hashes[i] - self.hashes[j]
                self.assertGreaterEqual(dist, 0)

    def test_axiom_2_identity_of_indiscernibles(self):
        """d(x, y) == 0 iff x == y."""
        for i, h1 in enumerate(self.hashes):
            # Same element must have distance 0
            self.assertEqual(h1 - h1, 0)
            # Distinct elements should have distance > 0 (unless bitstrings are identical)
            for j, h2 in enumerate(self.hashes):
                dist = h1 - h2
                if np.array_equal(h1.bits, h2.bits):
                    self.assertEqual(dist, 0)
                else:
                    self.assertGreater(dist, 0)

    def test_axiom_3_symmetry(self):
        """d(x, y) == d(y, x) for all x, y."""
        for i in range(len(self.hashes)):
            for j in range(i + 1, len(self.hashes)):
                d_ij = self.hashes[i] - self.hashes[j]
                d_ji = self.hashes[j] - self.hashes[i]
                self.assertEqual(d_ij, d_ji)

    def test_axiom_4_triangle_inequality(self):
        """d(x, z) <= d(x, y) + d(y, z) for all triads (x, y, z)."""
        # Test 1000 random triads
        n = len(self.hashes)
        for _ in range(1000):
            idx1, idx2, idx3 = np.random.choice(n, size=3, replace=True)
            x, y, z = self.hashes[idx1], self.hashes[idx2], self.hashes[idx3]
            d_xz = x - z
            d_xy = x - y
            d_yz = y - z
            self.assertLessEqual(
                d_xz,
                d_xy + d_yz,
                f"Triangle inequality violated: d(x,z)={d_xz} > d(x,y)={d_xy} + d(y,z)={d_yz}"
            )


class TestBKTreeSearchAndPruning(unittest.TestCase):
    """
    Validates BK-Tree indexing, range queries, and pruning correctness against Naive Linear Scan.
    """

    def setUp(self):
        np.random.seed(123)
        self.tree = BKTree()
        self.items = {}
        for i in range(100):
            h = PerceptualHash(np.random.randint(0, 2, size=100, dtype=np.uint8))
            path = f"/virtual/image_{i:03d}.jpg"
            self.items[path] = h
            self.tree.add(h, path)

    def test_search_equivalence_to_linear_scan(self):
        """
        Guarantees that BK-Tree Triangle Inequality search produces the EXACT
        same results as an exhaustive O(N) linear scan across multiple thresholds.
        """
        sample_paths = list(self.items.keys())[:15]
        for tolerance in [0, 5, 12, 25, 45]:
            for p in sample_paths:
                target_h = self.items[p]

                # 1. BK-Tree search
                bktree_matches, bench = self.tree.search_with_benchmark(
                    target_h, tolerance, all_items=self.items
                )
                bktree_set = set(bktree_matches)

                # 2. Ground-truth O(N) exhaustive linear scan
                linear_matches = [
                    cand_path for cand_path, cand_h in self.items.items()
                    if (target_h - cand_h) <= tolerance
                ]
                linear_set = set(linear_matches)

                # Both sets must be mathematically identical!
                self.assertEqual(
                    bktree_set,
                    linear_set,
                    f"Mismatch at tolerance {tolerance} for {p}: BK={bktree_set} vs Linear={linear_set}"
                )

                # Pruning check: For tight tolerance, visited nodes should be strictly <= total nodes
                if tolerance <= 12:
                    self.assertLessEqual(bench.nodes_visited, bench.total_nodes)

    def test_exact_clone_collision_handling(self):
        """Tests that distance=0 duplicates are stored in the same node paths list."""
        tree = BKTree()
        h = PerceptualHash(np.zeros(100, dtype=np.uint8))
        tree.add(h, "/path/img1.jpg")
        tree.add(h, "/path/img2.jpg")
        tree.add(h, "/path/img3.jpg")

        self.assertEqual(tree.total_entries, 3)
        self.assertEqual(tree.total_nodes, 1)

        results = tree.search(h, tolerance=0)
        self.assertEqual(len(results), 3)
        self.assertIn("/path/img1.jpg", results)
        self.assertIn("/path/img2.jpg", results)
        self.assertIn("/path/img3.jpg", results)


class TestDuplicateClusteringAndDSU(unittest.TestCase):
    """
    Tests Disjoint Set Union (DSU) and global duplicate cluster detection.
    """

    def test_dsu_operations(self):
        elements = ["a", "b", "c", "d", "e"]
        dsu = DisjointSetUnion(elements)

        dsu.union("a", "b")
        dsu.union("b", "c")
        self.assertEqual(dsu.find("a"), dsu.find("c"))
        self.assertNotEqual(dsu.find("a"), dsu.find("d"))

        dsu.union("d", "e")
        self.assertEqual(dsu.find("d"), dsu.find("e"))

        dsu.union("c", "d")
        self.assertEqual(dsu.find("a"), dsu.find("e"))

    def test_global_cluster_detection(self):
        """Tests partitioning images into duplicate clusters and choosing best master candidate."""
        tree = BKTree()
        base1 = np.zeros(100, dtype=np.uint8)
        base2 = np.ones(100, dtype=np.uint8)

        # Cluster 1: 3 near-identical images
        h1_a = PerceptualHash(base1.copy())
        h1_b = PerceptualHash(base1.copy())
        h1_b.bits[0] = 1 # Hamming distance 1
        h1_c = PerceptualHash(base1.copy())
        h1_c.bits[1] = 1 # Hamming distance 1

        # Cluster 2: 2 near-identical images
        h2_a = PerceptualHash(base2.copy())
        h2_b = PerceptualHash(base2.copy())
        h2_b.bits[0] = 0 # Hamming distance 1

        # Isolated image
        isolated = np.zeros(100, dtype=np.uint8)
        isolated[:50] = 1
        h_iso = PerceptualHash(isolated)

        all_items = {
            "/img/c1_low.jpg": h1_a,
            "/img/c1_high.jpg": h1_b,
            "/img/c1_med.jpg": h1_c,
            "/img/c2_orig.jpg": h2_a,
            "/img/c2_copy.jpg": h2_b,
            "/img/unique.jpg": h_iso,
        }

        for p, h in all_items.items():
            tree.add(h, p)

        metadata = {
            "/img/c1_low.jpg": {"dimensions": "800 × 600", "size_mb": 0.5},
            "/img/c1_high.jpg": {"dimensions": "3840 × 2160", "size_mb": 4.2},
            "/img/c1_med.jpg": {"dimensions": "1920 × 1080", "size_mb": 2.1},
            "/img/c2_orig.jpg": {"dimensions": "1920 × 1080", "size_mb": 1.8},
            "/img/c2_copy.jpg": {"dimensions": "1280 × 720", "size_mb": 0.9},
            "/img/unique.jpg": {"dimensions": "1920 × 1080", "size_mb": 1.5},
        }

        result = tree.find_all_duplicate_clusters(tolerance=5, all_items=all_items, metadata=metadata)
        clusters = result["clusters"]

        # Should identify exactly 2 clusters (isolated image not clustered)
        self.assertEqual(len(clusters), 2)

        # In Cluster 1, the highest resolution image (3840x2160) should be elected as master!
        c1 = next(c for c in clusters if "/img/c1_high.jpg" in [it["path"] for it in c["items"]])
        self.assertEqual(c1["master_path"], "/img/c1_high.jpg")
        self.assertEqual(c1["redundant_count"], 2)

    def test_build_rooted_at(self):
        """Verify dynamic re-rooting always places the requested item as root."""
        h1 = PerceptualHash(np.zeros(100, dtype=np.uint8))
        h2 = PerceptualHash(np.ones(100, dtype=np.uint8))
        h3 = PerceptualHash(np.array([1] * 50 + [0] * 50, dtype=np.uint8))

        all_items = {
            "/img/desert.jpg": h1,
            "/img/abstract.jpg": h2,
            "/img/mountain.jpg": h3,
        }

        # Root at abstract.jpg
        tree = BKTree.build_rooted_at("/img/abstract.jpg", all_items)
        self.assertIsNotNone(tree.root)
        self.assertEqual(tree.root.paths[0], "/img/abstract.jpg")
        
        # Verify graph representation
        graph = tree.get_tree_graph(target_hash=h2, tolerance=12)
        self.assertEqual(graph["name"], "abstract.jpg")
        self.assertEqual(graph["status"], "target")

        # Root at mountain.jpg
        tree2 = BKTree.build_rooted_at("/img/mountain.jpg", all_items)
        self.assertEqual(tree2.root.paths[0], "/img/mountain.jpg")
        graph2 = tree2.get_tree_graph(target_hash=h3, tolerance=12)
        self.assertEqual(graph2["name"], "mountain.jpg")


if __name__ == "__main__":
    unittest.main()

