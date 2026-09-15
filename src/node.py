


class Node:
    def __init__(self,id, prev=None, isCH=False):
        self.id = id
        self.prev = prev
        self.isCH = isCH
        self.nxts=[]


    def add_next(self, node):
        self.nxts.append(node)

    def set_previous(self, node):
        self.prev = node