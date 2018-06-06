import curses, random
from collections import defaultdict
from time import sleep
UP = 0
RIGHT = 1
DOWN = 2
LEFT = 3

TIME_UNIT = .017

#--------------------- 
#Container classes

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
            return Pair(*{UP:(-1, 0), RIGHT:(0, 1), DOWN:(1,0), LEFT:(0,-1)}[v])
        else:
            return Pair(*[(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)] [v])

    def get_neighbors(self, ortho=True):
        for d in range(4 if ortho else 8):
            yield self + Pair.get_direction(d, ortho=ortho)

    def rounded(self):
        return Pair(int(self.y+.5), int(self.x+.5))

class BufferedChar():
    def __init__(self, pos, char, color, draw_priority):
        assert isinstance(pos, Pair)
        self.pos = pos
        self.char = char
        self.color = color
        self.draw_priority = draw_priority

class KeyHandler():
    def __init__(self, registree, key, callback):
        self.registree = registree 
        self.key = key
        self.callback = callback
        
class DrawController():
    def __init__(self):
        self.draw_buffer = defaultdict(list)
        self.default_char = ' '

        self.rules = {}
        self.rule_assignments = defaultdict(list)

        self.drawn = set()
        self.to_restore = set()

        self.default_color = 4

    def init_screen(self):
        stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        stdscr.nodelay(1)
        stdscr.keypad(1)

        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_MAGENTA, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_RED)
        self.screen = stdscr
        self.height, self.width = stdscr.getmaxyx()


        return stdscr

    def set_default_char(self, c):
        self.default_char = c

    def set_default_color(self, co):
        self.default_color = co

    def update(self, modified):
        self.to_restore.update(modified)

    def add_rule(self, rule_id, rule, ch, color=1, modified=None):
        ''' Adds a rule, if modified is not none it will only update those cells. rule_id must be unique '''
        assert rule_id not in self.rules
        self.rules[rule_id] = (rule,ch,color)
        if modified is None:
            for i in range(self.height):
                for j in range(self.width):
                    p = Pair(i,j)
                    if rule(p):
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

        if y < self.height and y >= 0 and x < self.width and x >= 0 and (y < self.height - 1 or x < self.width - 1):
            draw_y, draw_x = Pair(y,x).rounded()
            self.screen.addstr(draw_y, draw_x, ch, curses.color_pair(co))

    def full_draw(self):
        ''' prepares to redraw every cell, the subsequent render (restore) will be expensive '''
        for i in range(self.height):
            for j in range(self.width):
                p = Pair(i,j)
                self.to_restore.add(p)

    def restore(self):
        '''Each iteration, anything not explicitly drawn is redrawn to the value specified in the rules, or the default'''
        self.rule_assignments = defaultdict(list)
        for pix in self.to_restore:
            for k in self.rules:
                rule = self.rules[k]
                if rule[0](pix):
                    self._draw_char(pix.y, pix.x, rule[1], rule[2])
                    self.rule_assignments[k].append(pix)
                    break
            else:
                self._draw_char(pix.y, pix.x, self.default_char, self.default_color)

        self.to_restore = set()

    def draw(self, buffered_chars):
        
        for bc in buffered_chars:

            y,x = bc.pos

            color, char = bc.color, bc.char
            self._draw_char(y, x, char, color)
            

            p = bc.pos.rounded()
            if p in self.to_restore:
                self.to_restore.remove(p)

            self.drawn.add(p)


    def render(self):
        self.restore()
        self.to_restore = self.drawn
        self.drawn = set()
        self.screen.refresh()
   
#--------------------

class MainController():
    def __init__(self, world_height=None, world_width=None):
        dc = DrawController()
        scr = dc.init_screen()
        self.dc = dc
        self.screen = scr

        if world_height is None:
            world_height = dc.height

        if world_width is None:
            world_width = dc.width

        w = World(world_height, world_width)
        self.w = w

        self.dc.add_rule('vis', lambda p:p in self.w.visible, ' ')

        ctx = SharedContext()
        ctx.world = self.w
        ctx.draw_controller = dc
        self.ctx = ctx

    def get_draw_controller(self):
        return self.dc


    def tock(self):
        self.handle_input()
        chrs = self.w.get_draws()
        self.w.update()

        old_vis = self.w.visible
        self.w.calc_visibility()

        self.dc.update(old_vis^self.w.visible) #explicitly update these cells

        for c in chrs:
            self.dc.draw(c)

        self.dc.render()

    def handle_input(self): #order not guaranteed
        pressed = set()
        char = self.screen.getch()
        while True:
            if char != -1:
                pressed.add(char)
            else:
                break
            char = self.screen.getch()

        for k in pressed:
            
            for h in self.ctx.key_handlers[k]:
                h.callback(h.key)
     
class SharedContext(): #singleton

    @staticmethod
    def get_instance():
        if not hasattr(SharedContext, '_instance'):
            SharedContext._instance = SharedContext()
        return SharedContext._instance

    def __init__(self):

        if hasattr(SharedContext, '_instance'):
            raise Exception('No.')

        SharedContext._instance = self
        self.log_list = []

        self.key_handlers = defaultdict(list)

        self.draw_controller = None

        self.world = None

    def log(self, val):
        self.log_list.append('%s'%val)

    def register_key(self, handler):
        assert isinstance(handler, KeyHandler)

        self.key_handlers[handler.key].append(handler)

    def deregister_key(self, handler):
        ''' Only looks at key and registree '''
        assert isinstance(handler, KeyHandler)

        self.key_handlers[handler.key] = filter(lambda e: e.registree != handler.registree,self.key_handlers[handler.key])

    def get_snapshot(self):
        return self.world.snapshot()

    def get_visible_posns(self):
        return self.world.visible

    def get_world_bounds(self):
        return (self.world.height, self.world.width)

    def add_entity(self, ent):
        self.world.add(ent)

    def pos_in_world(self, p):
        return self.world.pos_in_world(p)

def get_line( p1,p2,obs,dis=3,extend_prob=.009):
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

def visibility(obs, start, valid, height, width):
    assert isinstance(start, Pair)
    assert isinstance(obs, set)
    i = 0
    vis = set()
    for i in range(0, width):
        vis.update(get_line(start, Pair(0,i), obs))
        vis.update(get_line(start, Pair(height-1, i), obs))

    for i in range(0, height):
        vis.update(get_line(start, Pair(i,0), obs))
        vis.update(get_line(start, Pair(i, width-1), obs))

    return vis

#-------------------

class World():

    def __init__(self, height, width):
        self.height = height
        self.width = width

        self.entities = []
        self.visible = set()

        self.visible_ent = set()

    def add(self, e):
        assert isinstance(e, Entity)

        self.entities.append(e)

    def snapshot(self):
        snp = defaultdict(list)
        for e in self.entities:
            cpy = e.copy()
            snp[cpy.get_pos()].append(cpy)

        return snp

    def calc_visibility(self):
        obs = set()
        for e in self.entities:
            if not e.is_transparent():
                obs.add(e.get_pos())

        valid = lambda n:n.y>=0 and n.y < self.height and n.x>=0 and n.x<self.width
        visible = set()
        for pl in filter(lambda x:isinstance(x,Player), self.entities):
            visible.update(visibility(obs, pl.get_pos(), valid, self.height, self.width))
        self.visible = visible

    def pos_in_world(self, p):
        return p.y >= 0 and p.y < self.height and p.x >= 0 and p.x < self.width

    def get_draws(self):
        for e in self.visible_ent:
            yield e.get_chars()

    def update(self):
        survived = []
        self.visible_ent = set()
        for e in self.entities:
            e.update()
            if e.get_pos().rounded() in self.visible:
                self.visible_ent.add(e)

            if not e.is_dead():
                survived.append(e)
        self.entities = survived


class Entity(object): #base class

    def __init__(self, pos):
        assert isinstance(pos, Pair)

        self.pos = pos
        self.ctx = SharedContext.get_instance()

    def is_transparent(self):
        return True

    def get_pos(self):
        return self.pos

    def get_color_pair(self):
        return 0

    def get_str(self):
        return 'E'

    def get_draw_priority(self):
        return 0

    def get_chars(self):
        return [BufferedChar(self.get_pos(), self.get_str(), self.get_color_pair(), self.get_draw_priority())]

    def update(self):
        pass

    def copy(self):
        return self

    def is_dead(self):
        return False

    def set_pos(self, p):
        self.pos = p

class Player(Entity):

    def __init__(self, pos):
        super(Player, self).__init__(pos)

        ctx = SharedContext.get_instance()

        ctx.register_key(KeyHandler(self, curses.KEY_UP, lambda k:self.try_move(UP)))
        ctx.register_key(KeyHandler(self, curses.KEY_RIGHT, lambda k:self.try_move(RIGHT)))
        ctx.register_key(KeyHandler(self, curses.KEY_DOWN, lambda k:self.try_move(DOWN)))
        ctx.register_key(KeyHandler(self, curses.KEY_LEFT, lambda k:self.try_move(LEFT)))
        ctx.register_key(KeyHandler(self, ord(' '), lambda k:self.shoot())) #spacebar

        self.last_direction = 0

        self.base_rof = 30
        self.rof_timer = 0

    def get_str(self):
        return '&'

    def get_color_pair(self):
        return 2

    def is_transparent(self):
        return True

    def try_move(self, direct):

        ctx = SharedContext.get_instance()
        direction = Pair.get_direction(direct)

        posns = ctx.get_snapshot()

        new_pos = self.get_pos() + direction

        if len(posns[new_pos]) != 0 or not ctx.pos_in_world(new_pos):
            #no
            pass

        else:
            #yes
            self.last_direction = direct
            self.pos = new_pos

    def shoot(self):
        if self.rof_timer == 0:
            fireball_pos = self.get_pos() + Pair.get_direction(self.last_direction)
            SharedContext.get_instance().add_entity(Fireball(fireball_pos, self.last_direction))
            self.rof_timer = self.base_rof

    def update(self):
        self.rof_timer = max(0, self.rof_timer-1)

class Spooker(Entity):
    
    def __init__(self, pos):
        super(Spooker, self).__init__(pos)
        self.mood = 'happy'

    def is_transparent(self):
        return False 

    def update(self):
        if self.get_pos() in SharedContext.get_instance().get_visible_posns():
            self.mood = 'hangry'
        else:
            self.mood = 'happy'

    def get_str(self):
        return '.' if self.mood == 'happy' else '>'

class Fireball(Entity):
    def __init__(self, pos, direction):
        super(Fireball, self).__init__(pos)
        self.direction = direction
        self.speed = .3
        self.outside_vision_count = 0
        
    def get_color_pair(self):
        return 5
    def get_str(self):
        return 'X'

    def update(self):
        ny, nx = Pair.get_direction(self.direction)
        np = Pair(self.speed*ny, self.speed*nx)
        self.set_pos(self.pos + np)

        me = self.get_pos().rounded()
        ctx = SharedContext.get_instance()

        if (me not in ctx.get_visible_posns() or not ctx.pos_in_world(me)):
            self.outside_vision_count += 1
        else:
            self.outside_vision_count = 0


    def is_dead(self):

        return self.outside_vision_count > 4

class Wall(Entity):
    def __init__(self, pos):
        super(Wall, self).__init__(pos)

    def is_transparent(self):
        return False

    def get_color_pair(self):
        return 3

    def get_str(self):
        return '#'

def intersects(a, b):
    a1,a2 = a
    a1x,a1y = a1
    a2x,a2y = a2

    b1,b2 = b
    b1x,b1y = b1
    b2x,b2y = b2

    return not (a2y < b1y or a1y > b2y or a2x < b1x or a1x > b2x)

def intersects_with_any(r, ls):
    for l in ls:
        if intersects(r, l):
            return True
    return False

def get_dungeon(height, width):
    rects = []
    en=[]
    for i in range(300):
        py,px = (random.randint(1,height - 2),random.randint(1,width - 2))
        h,w = random.randint(5,height-2), random.randint(5,width-2)
        j = 0
        while (height/2 in range(py,py+h) and width/2 in range(px,px+w) or intersects_with_any(((py,px),(py+h,px+w)),rects)) and j < 100:

            py,px = (random.randint(1,height-2),random.randint(1,width-2))
            h,w = random.randint(5,height-2), random.randint(5,width-2)

            j+=1

        if j < 100:
            rects.append(((py,px),(py+h,px+w)))

    obs = []
    for r in rects:

        ly,lx = r[0]
        hy,hx = r[1]

        ly+=1
        lx+=1
        hy-=1
        hx-=1

        sds = []
        for i in range(ly,hy+1):

            sds.append((i,lx))
            sds.append((i,hx))

        for i in range(lx,hx+1):
            if (ly,i) not in sds:
                sds.append((ly,i))
            if (hy,i) not in sds:
                sds.append((hy,i))



        #if random.random() < .999:
        for i in range(random.randint(1,5)):
            sds.pop(random.randint(0,len(sds)-1))
        en.append(((ly+hy)/2,(lx+hx)/2))
        obs.extend(sds)
    for i in range(height):
        obs.append((i,0))
        obs.append((i,width-1))

    for i in range(width):
        obs.append((0,i))
        obs.append((height-1,i))

    obs = map(lambda p:Pair(p[0],p[1]), obs)
    return obs


def main():
    try:
        mc = MainController(world_height=60, world_width=60)
        player = Player(Pair(20,20))
        spooker = Spooker(Pair(40,40))
        mc.w.add(player)
        mc.w.add(spooker)

        walls = get_dungeon(mc.w.height, mc.w.width)

        for w in walls:
            wa = Wall(w)
            mc.w.add(wa)

        mc.dc.full_draw()
        while True:
            mc.tock()
            sleep(TIME_UNIT)
        raw_input()
    finally:
        curses.endwin()
        log = SharedContext.get_instance().log_list

        print 'Logged:',log

main()
