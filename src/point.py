from dataclasses import dataclass
from math import sqrt


@dataclass
class Point:
    x: float
    y: float
    z: float

    def __add__(self, other):
        return Point(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z,
        )

    def __sub__(self, other):
        return Point(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z,
        )

    def __mul__(self, scalar):
        return Point(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar,
        )

    __rmul__ = __mul__

    def __abs__(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def sq_abs(self):
        return self.x**2 + self.y**2+self.z**2
        
        