


class Node:
    def __init__(self,idx, prev=None, isCH=False):
        self.id = idx
        self.prev = prev
        self.isCH = isCH
        self.nxts=[]


    def add_next(self, node):
        self.nxts.append(node)

    def set_previous(self, node):
        self.prev = node