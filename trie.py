class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.data = None


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word, data=None):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.data = data

    def search(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                return False, None
            node = node.children[char]
        return node.is_end_of_word, node.data

    def starts_with(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return False
            node = node.children[char]
        return True
