import curses 
from collections import defaultdict

color_map = {
'white':curses.COLOR_WHITE,
'black':curses.COLOR_BLACK,
'magenta':curses.COLOR_MAGENTA,
'cyan':curses.COLOR_CYAN,
'red':curses.COLOR_RED,
'green':curses.COLOR_GREEN,
'yellow':curses.COLOR_YELLOW,
'blue':curses.COLOR_BLUE,
-1:-1
}

UP, RIGHT, DOWN, LEFT = 0, 1, 2, 3

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

        return  (self.y==other.y and self.x==other.x)

    def __getitem__(self, idx):
        if idx == 0:
            return self.y
        if idx == 1:
            return self.x
        raise IndexError("No.")

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

Pair._directions = {
UP:Pair(-1, 0),
RIGHT:Pair(0, 1),
DOWN:Pair(1, 0),
LEFT:Pair(0, -1)
}

class Char():
    def __init__(self, pos, character, color=1):
        self.pos = Pair(pos[0], pos[1])
        self.char = character
        self.color = color


    @staticmethod
    def from_string(st, pos, color=1, direction=RIGHT):
        p = Pair(pos[0],pos[1])
        ls = []
        for i in range(len(st)):
            ls.append(Char(p, st[i], color=color))
            p += Pair._directions[direction]
        return ls

class ColorController():
    def __init__(self):
        if hasattr(ColorController, "_instance"):
            raise Exception('This is a singleton.')
        self.pairs = {}
        self.counter = 1

    @staticmethod
    def get_instance():
        if not hasattr(ColorController, '_instance'):
            ColorController._instance = ColorController()
        return ColorController._instance

    @staticmethod
    def get_color(text, bg):
        assert text in color_map
        assert bg in color_map
        self = ColorController.get_instance()
        if (text, bg) in self.pairs:
            return self.pairs[(text, bg)]

        else:
            self.pairs[(text, bg)] = self.counter
            curses.init_pair(self.counter, color_map[text], color_map[bg])
            self.counter += 1
            return self.counter - 1
        
class DrawController():
    def __init__(self):
        self.draw_buffer = defaultdict(list)
        self.default_char = ' '

        self.rules = {}
        self.rule_assignments = defaultdict(list)

        self.drawn = set()
        self.to_restore = set()

    def init_screen(self):
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.keypad(1)

        curses.start_color()
        curses.use_default_colors()

        self.screen = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.size = stdscr.getmaxyx()
        self.default_color = ColorController.get_color('black', 'black')

        return stdscr

    def set_default_char(self, c):
        self.default_char = c

    def set_default_color(self, co):
        self.default_color = co

    def update(self, modified):
        '''Explicitly update some cells'''
        m = []
        for e in modified:
            m.append(Pair(e[0],e[1]))
        self.to_restore.update(modified)

    def add_rule(self, rule_id, rule, ch, color=1, modified=None):
        ''' Adds a rule, if modified is not none it will only update those cells, if modified is none all cells will be iterated over. rule_id must be unique '''
        assert rule_id not in self.rules
        self.rules[rule_id] = (rule,ch,color)
        if modified is None:
            for i in range(self.height):
                for j in range(self.width):
                    p = Pair(i,j)
                    if rule((i,j)):
                        self.to_restore.add(p)
        else:
            self.to_restore.update(modified)

    def update_rule(self, rule_id, rule, ch, color=1, modified=None):
        self.remove_rule(rule_id)
        self.add_rule(rule_id, rule, ch, color=color, modified=modified)

    def remove_rule(self, rule_id):
        if rule_id in self.rules:
            self.rules.pop(rule_id)
            self.to_restore.update(self.rule_assignments[rule_id])
            self.rule_assignments.pop(rule_id)

    def _draw_char(self, y, x, ch, co):
        if y < self.height and y >= 0 and x < self.width and x >= 0:
            try:
                draw_y, draw_x = Pair(y,x).rounded()
                self.screen.addch(draw_y, draw_x, ch, curses.color_pair(co))
            except curses.error:
                pass

    def full_draw(self):
        '''Function should be called after initialization. Prepares to redraw every cell, the subsequent render (restore) will be expensive.'''
        for i in range(self.height):
            for j in range(self.width):
                p = Pair(i,j)
                self.to_restore.add(p)

    def _restore(self):
        '''Each iteration, anything not explicitly drawn that was previously drawn is redrawn to the value specified in the rules, or the default.'''
        self.rule_assignments = defaultdict(list)
        for pix in self.to_restore:
            for k in self.rules:
                rule = self.rules[k]
                if rule[0](tuple(pix)):
                    self._draw_char(pix.y, pix.x, rule[1], rule[2])
                    self.rule_assignments[k].append(pix)
                    break
            else:
                self._draw_char(pix.y, pix.x, self.default_char, self.default_color)

        self.to_restore = set()

    def draw(self, chars):
        '''Use this function to draw characters to the screen. Receives a list of Char instances.'''
        for bc in chars:
            assert isinstance(bc, Char)

            y,x = bc.pos

            color, char = bc.color, bc.char
            self._draw_char(y, x, char, color)
            
            p = bc.pos.rounded()
            if p in self.to_restore:
                self.to_restore.remove(p)

            self.drawn.add(p)

    def render(self):
        '''Actually draw buffered draws.'''
        self._restore()
        self.to_restore = self.drawn
        self.drawn = set()
        self.screen.refresh()

    def end(self):
        '''Call to restore terminal to normal.'''
        curses.endwin()

'''Really simple keyboard controller. Provided bare minimum, class designed to be added to as necessary.'''
class KeyboardController():

    def __init__(self, screen):
        self.screen = screen
        self.callbacks = defaultdict(set)

    def register_keys(self, keyset, callback):
        '''
        Provided an iterable of characters and a single callback function assigns the callback function to those keys. 
        Callback should receive a single argument for which key was pressed.
        '''
        for k in keyset:
            self.callbacks[ord(k)].add(callback)

    def getkeys(self): #order not guaranteed
        pressed = set()
        char = self.screen.getch()
        while True:
            if char != -1:
                pressed.add(char)
            else:
                break
            char = self.screen.getch()

        for k in pressed:
            for h in self.callbacks[k]:
                h(k)

if __name__ == '__main__':


    def life():
        try:
            from time import sleep
            dc = DrawController()
            dc.init_screen()
            dc.full_draw()
            h,w = dc.size
            CC = ColorController
            y,x = h//2,w//2
            active = [
            (y,x),
            (y,x+1),
            (y+1,x+1),
            (y+1,x+2),
            (y+2,x+1)
            ]
            active = map(lambda p:Pair(p[0],p[1]), active)
            while True:
                for a in active:
                    c = Char(a, ' ', color=CC.get_color("white","white"))
                    dc.draw([c])

                dc.render()

                n_count = defaultdict(int)
                for o in active:
                    for n in o.get_neighbors(ortho=False):
                        n_count[n]+=1

                new_active = []
                for k in n_count.keys():
                    c = n_count[k]
                    if c == 3 and k not in active:
                        new_active.append(k)
                    elif k in active and c in [2,3,4]:
                        new_active.append(k)

                active = new_active
                sleep(.001)
        finally:
            dc.end()
    life()



