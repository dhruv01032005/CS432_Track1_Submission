from bisect import bisect_left, bisect_right

class BPlusTreeNode:
    # Initialize a tree node as either a leaf or internal node container.
    def __init__(self, leaf=False):
        self.leaf = leaf
        self.keys = []
        self.values = []
        self.children = []
        self.next = None

class BPlusTree:
    # Initialize the B+ tree with a minimum degree and an empty leaf root.
    def __init__(self, t=3):
        if t < 2:
            raise ValueError("B+ Tree minimum degree t must be >= 2")
        self.root = BPlusTreeNode(leaf=True)
        self.t = t

    # Traverse down from the root to find the leaf that should contain the key.
    def _find_leaf(self, key):
        node = self.root
        while not node.leaf:
            idx = bisect_right(node.keys, key)
            node = node.children[idx]
        return node

    # Return the leftmost leaf node for full in-order scans.
    def _leftmost_leaf(self):
        node = self.root
        while not node.leaf:
            node = node.children[0]
        return node

    # Look up and return the value associated with a key, or None if absent.
    def search(self, key):
        leaf = self._find_leaf(key)
        idx = bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            return leaf.values[idx]
        return None

    # Insert or update a key-value pair while preserving B+ tree balance rules.
    def insert(self, key, value):
        root = self.root
        if len(root.keys) == (2 * self.t) - 1:
            temp = BPlusTreeNode()
            self.root = temp
            temp.children.insert(0, root)
            self._split_child(temp, 0)
            self._insert_non_full(temp, key, value)
        else:
            self._insert_non_full(root, key, value)

    # Insert a key-value pair into a node that is guaranteed not to be full.
    def _insert_non_full(self, node, key, value):
        if node.leaf:
            idx = bisect_left(node.keys, key)
            if idx < len(node.keys) and node.keys[idx] == key:
                node.values[idx] = value
                return
            node.keys.insert(idx, key)
            node.values.insert(idx, value)
        else:
            idx = bisect_right(node.keys, key)
            if len(node.children[idx].keys) == (2 * self.t) - 1:
                self._split_child(node, idx)
                if key >= node.keys[idx]:
                    idx += 1
            self._insert_non_full(node.children[idx], key, value)

    # Split a full child node and promote the separator key into its parent.
    def _split_child(self, parent, index):
        t = self.t
        child = parent.children[index]
        new_node = BPlusTreeNode(leaf=child.leaf)

        if child.leaf:
            mid = t - 1
            new_node.keys = child.keys[mid:]
            new_node.values = child.values[mid:]
            child.keys = child.keys[:mid]
            child.values = child.values[:mid]
            new_node.next = child.next
            child.next = new_node

            parent.keys.insert(index, new_node.keys[0])
            parent.children.insert(index + 1, new_node)
        else:
            mid = t - 1
            promote_key = child.keys[mid]
            new_node.keys = child.keys[mid + 1:]
            new_node.children = child.children[mid + 1:]
            child.keys = child.keys[:mid]
            child.children = child.children[:mid + 1]

            parent.keys.insert(index, promote_key)
            parent.children.insert(index + 1, new_node)

    # Delete a key by delegating to the rebuild-based internal deletion routine.
    def delete(self, key):
        return self._delete(self.root, key)

    # Remove a key by rebuilding the tree from all entries except that key.
    def _delete(self, node, key):
        value = self.search(key)
        if value is None:
            return False

        all_items = self.get_all()
        self.root = BPlusTreeNode(leaf=True)
        for k, v in all_items:
            if k != key:
                self.insert(k, v)
        return True

    # Replace the stored value for an existing key.
    def update(self, key, new_value):
        leaf = self._find_leaf(key)
        idx = bisect_left(leaf.keys, key)
        if idx < len(leaf.keys) and leaf.keys[idx] == key:
            leaf.values[idx] = new_value
            return True
        return False

    # Return all key-value pairs with keys inside the inclusive range.
    def range_query(self, start_key, end_key):
        if start_key > end_key:
            return []

        node = self._find_leaf(start_key)
        result = []
        while node:
            for idx, key in enumerate(node.keys):
                if key < start_key:
                    continue
                if key > end_key:
                    return result
                result.append((key, node.values[idx]))
            node = node.next
        return result

    # Return every key-value pair in sorted key order.
    def get_all(self):
        node = self._leftmost_leaf()
        result = []
        while node:
            for idx, key in enumerate(node.keys):
                result.append((key, node.values[idx]))
            node = node.next
        return result

    # Build and optionally render a Graphviz visualization of the current tree.
    def visualize_tree(self, as_figure=True):
        try:
            from graphviz import Digraph
        except ImportError as exc:
            raise ImportError(
                "graphviz is required for tree visualization. Install with 'pip install graphviz'."
            ) from exc

        dot = Digraph("BPlusTree")
        dot.attr(rankdir="TB", splines="polyline")
        dot.attr(
            "node",
            shape="box",
            style="rounded",
            fontname="Helvetica",
            color="#333333",
        )
        self._add_nodes(dot, self.root)
        self._add_edges(dot, self.root)

        # When the root is also a leaf, include a visual root so the output still looks like a tree.
        if self.root.leaf:
            root_id = "virtual_root"
            dot.node(root_id, "Root", shape="circle", style="filled", fillcolor="#e8f1ff")
            dot.edge(root_id, str(id(self.root)))

        if not as_figure:
            return dot

        try:
            from IPython.display import Image
        except ImportError as exc:
            raise ImportError(
                "IPython is required to display tree figures inline. Install with 'pip install ipython'."
            ) from exc

        image_data = dot.pipe(format="png")
        return Image(data=image_data)

    # Escape text so it is safe to embed inside Graphviz node labels.
    def _escape_label_text(self, text):
        return str(text).replace("\\", "\\\\").replace("\n", "\\n")

    # Add Graphviz nodes recursively for all internal and leaf tree nodes.
    def _add_nodes(self, dot, node):
        node_id = str(id(node))
        if node.leaf:
            if node.keys:
                pairs = [
                    f"{self._escape_label_text(k)}: {self._escape_label_text(node.values[i])}"
                    for i, k in enumerate(node.keys)
                ]
                label = "Leaf\\n" + "\\n".join(pairs)
            else:
                label = "Leaf\\nempty"
        else:
            if node.keys:
                label = "Internal\\nkeys: " + ", ".join(self._escape_label_text(k) for k in node.keys)
            else:
                label = "Internal\\nroot"

        dot.node(node_id, label)
        if not node.leaf:
            for child in node.children:
                self._add_nodes(dot, child)

    # Add Graphviz edges for child links and dashed leaf-level next pointers.
    def _add_edges(self, dot, node):
        node_id = str(id(node))
        if node.leaf:
            if node.next is not None:
                dot.edge(node_id, str(id(node.next)), style="dashed", color="gray", constraint="false")
            return

        for child in node.children:
            child_id = str(id(child))
            dot.edge(node_id, child_id)
            self._add_edges(dot, child)