class Node:
    def __init__(self, img_hash, file_path):
        self.img_hash = img_hash
        # We use a list to store paths in case of exact duplicates (distance = 0)
        self.paths = [file_path]
        # Children are stored in a dictionary where the key is the Hamming distance
        self.children = {}

class BKTree:
    def __init__(self):
        self.root = None

    def add(self, img_hash, file_path):
        if self.root is None:
            self.root = Node(img_hash, file_path)
            return
        
        curr = self.root
        while True:
            # ImageHash allows us to subtract hashes to get the Hamming distance
            dist = img_hash - curr.img_hash 
            
            if dist == 0:
                curr.paths.append(file_path)
                return
            if dist in curr.children:
                curr = curr.children[dist]
            else:
                curr.children[dist] = Node(img_hash, file_path)
                return

    def search(self, target_hash, tolerance):
        results = []
        if self.root is None:
            return results
        
        candidates = [self.root]
        while candidates:
            curr = candidates.pop(0)
            dist = target_hash - curr.img_hash
            
            # If it's within our tolerance, add it to results
            if dist <= tolerance:
                results.extend(curr.paths)
                
            # BK-Tree Optimization: Only search branches that could possibly have matches
            for d, child in curr.children.items():
                if (dist - tolerance) <= d <= (dist + tolerance):
                    candidates.append(child)
        
        return results