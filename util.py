import random
from collections import deque
import heapq
UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3


def sign(x):
    if x < 0:
        return -1

    if x > 0:
        return 1

    if x == 0:
        return 0


class Pair():
    def __init__(self, y, x):
        self.x=x
        self.y=y

    def __add__(self, other):
        return Pair(self.y+other.y, self.x + other.x)

    def __sub__(self, other):
        return Pair(self.y-other.y, self.x - other.x)

    def __eq__(self, other):
        return (self.y,self.x)==(other.y, other.x)

    def __hash__(self):
        return (self.y,self.x).__hash__()

    def __iter__(self):
        yield self.y
        yield self.x

    def __tuple__(self):
        return (self.y,self.x)

    def __str__(self):
        return str((self.y,self.x))

    @staticmethod
    def get_direction(v, ortho=True):
        if ortho:
            return Pair._directions[v]
        else:
            return Pair(*[(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)] [v])

    def get_neighbors(self, ortho=True):
        for d in range(4 if ortho else 8):
            yield self + Pair.get_direction(d, ortho=ortho)

    def rounded(self):
        return Pair(int(self.y+.5), int(self.x+.5))

    def euclidean(self, other):
        return ((self.y-other.y)**2 + (self.x-other.x)**2)**.5

    def direction_to(self, other):
        diff =  other - self
        if abs(diff.y) > abs(diff.x):
            if sign(diff.y) == -1:
                return 0
            else:
                return 2

        else:
            if sign(diff.x) == -1:
                return 3
            else:
                return 1
Pair._directions = {UP:Pair(-1, 0), RIGHT:Pair(0, 1), DOWN:Pair(1,0), LEFT:Pair(0,-1)}

class BufferedChar():
    def __init__(self, pos, char, color):
        assert isinstance(pos, Pair)
        self.pos = pos
        self.char = char
        self.color = color

    @staticmethod
    def from_string(st, upper_left, direction, color):
        res = []
        p = upper_left
        for c in st:
            res.append(BufferedChar(p, c, color))
            p = p + Pair.get_direction(direction)

        return res



class KeyHandler():
    def __init__(self, registree, key, callback):
        self.registree = registree 
        self.key = key
        self.callback = callback

def get_line( p1,p2,obs,dis=8,extend_prob=.009):
    y0,x0=p1
    y1,x1=p2
    r = []
    "Bresenham's line algorithm"
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    sx = -1 if x0 > x1 else 1
    sy = -1 if y0 > y1 else 1
    if dx > dy:
        err = dx / 2.0
        while x != x1:
            if Pair(y, x)in obs or (((x-x0)**2 + (y-y0)**2 > dis**2) and random.random() > extend_prob):break
            r.append(Pair(y, x))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != y1:
            if Pair(y,x)in obs or (((x-x0)**2 + (y-y0)**2 > dis**2) and random.random() > extend_prob):break
            r.append(Pair(y, x))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy        
    r.append(Pair(y,x))
    return r


def get_breadth(start, finish, obs):
    get_breadth.count += 1
    prev = {start:None}
    queue = []

    queue.append((0,start))
    while len(queue) > 0:
        v, current = heapq.heappop(queue)

        for n in current.get_neighbors():
            if n in obs or n in prev:
                continue
            heapq.heappush(queue, (1+n.euclidean(finish), n))
            prev[n]=current
            if n == finish:
                break
        else:
            continue

        break

    pth = deque([finish])
    while current != start and current:
        current = prev[current]
        pth.appendleft(current)
    return pth

get_breadth.count = 0