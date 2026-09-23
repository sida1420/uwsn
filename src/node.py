class Node:
    """
    One node of a routing tree for a single round. The base station is
    the root (conventionally id=-1); its children are cluster heads;
    their children are member sensors.
    """

    def __init__(self, idx, prev=None, isCH=False, isRelay=False):
        self.id = idx
        self.prev = prev
        self.isCH = isCH
        self.isRelay = isRelay
        self.nxts = []

    def add_next(self, node):
        self.nxts.append(node)

    def set_previous(self, node):
        self.prev = node

    def __repr__(self):
        return f"Node(id={self.id}, isCH={self.isCH}, isRelay={self.isRelay}, children={[n.id for n in self.nxts]})"
