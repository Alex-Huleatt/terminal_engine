import curses, random
from collections import defaultdict
from time import sleep
import dungeon
import inspect

from base import *
from util import *


TIME_UNIT = .017

color_map = {
'white':curses.COLOR_WHITE,
'black':curses.COLOR_BLACK,
'magenta':curses.COLOR_MAGENTA,
'cyan':curses.COLOR_CYAN,
'red':curses.COLOR_RED,
'green':curses.COLOR_GREEN,
'yellow':curses.COLOR_YELLOW,
'blue':curses.COLOR_BLUE
}


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
        self = ColorController.get_instance()
        if (text, bg) in self.pairs:
            return self.pairs[(text, bg)]

        else:
            self.pairs[(text, bg)] = self.counter
            curses.init_pair(self.counter, color_map[text], color_map[bg])
            self.counter += 1
            return self.counter - 1

#--------------------- 
#Container classes
        
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
        self.default_color = ColorController.get_color('black', 'black')


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
        '''Each iteration, anything not explicitly drawn that was previously drawn is redrawn to the value specified in the rules, or the default'''
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

        self.dc.add_rule('vis', lambda p:p in self.w.visible, ' ', color = ColorController.get_color("white","white"))
        self.dc.add_rule('outside', lambda p:p.y>= world_height or p.x >= world_width, ' ', color = ColorController.get_color("white", "white"))

        ctx = SharedContext()
        ctx.world = self.w
        ctx.draw_controller = dc
        self.ctx = ctx

    def get_draw_controller(self):
        return self.dc

    def draw_player_stats(self):
        pl = self.ctx.get_player_pos()[0]
        buffs = sorted(map(str, pl.get_buffs()))
        hp = pl.get_hp()//10
        enemy_count = len(self.w.get_all_of_type(Spooker))

        st = "Enemies remaining:" + str(enemy_count)
        self.dc.draw(BufferedChar.from_string(st, Pair(0, self.w.width+1), 1, ColorController.get_color("black", "white")))

        self.dc.draw(BufferedChar.from_string(' '*(hp), Pair(1, self.w.width+1), 1, ColorController.get_color("red", "red")))

        for i in range(len(buffs)):
            b = buffs[i]
            self.dc.draw(BufferedChar.from_string(str(b), Pair(i+2,self.w.width+1), 1, ColorController.get_color("black", "white")))

    def tock(self):
        self.handle_input()
        
        self.w.update()

        old_vis = self.w.visible
        self.w.calc_visibility()
        chrs = self.w.get_draws()

        self.dc.update(old_vis^self.w.visible) #explicitly update only the cells that changed visibility.

        for c in chrs:
            self.dc.draw(c)

        self.draw_player_stats()

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
        self.log(handler)
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

    def get_player_pos(self):
        return self.world.get_all_of_type(Player)

    def get_unit_at_pos(self, pos):
        snp = self.get_snapshot()
        return snp[pos]

    def get_world(self):
        return self.world   




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

        self.cached_snapshot = None

        self.by_type = defaultdict(list)

    def add(self, e):
        assert isinstance(e, Entity)

        self.entities.append(e)

    def snapshot(self):
        if self.cached_snapshot is not None:
            return self.cached_snapshot
        snp = defaultdict(list)
        by_type = defaultdict(list)
        for e in self.entities:
            cpy = e.copy()
            snp[cpy.get_pos().rounded()].append(cpy)

            by_type[type(e)].append(e)
        self.by_type = by_type
        self.cached_snapshot = snp
        return snp

    def get_all_of_type(self, typ):
        return self.by_type[typ]

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
        snp = defaultdict(list)
        by_type = defaultdict(list)
        for e in self.entities:
            e.update()
            if e.get_pos().rounded() in self.visible:
                self.visible_ent.add(e)

            if not e.is_dead():
                survived.append(e)
                snp[e.get_pos().rounded()].append(e)
                for t in inspect.getmro(type(e)):
                    by_type[t].append(e)
            else:
                SharedContext.get_instance().log(e.__class__.__name__+" has died at " + str(e.get_pos()))

        self.entities = survived
        self.by_type = by_type
        self.cached_snapshot = snp


class MobileEntity(Entity):

    def __init__(self, pos):
        super(MobileEntity, self).__init__(pos)

        self.rom_timer = 0
        self.base_rom = 0
        self.last_direction = 0

    def get_base_rom(self):
        return self.base_rom

    def set_base_rom(self, new_val):
        self.base_rom = new_val

    def get_rom_timer(self):
        return self.rom_timer

    def set_rom_timer(self, new_val):
        self.rom_timer = new_val

    def get_last_direction(self):
        return self.last_direction

    def try_move(self, direction):
        self.last_direction = direction
        if self.get_rom_timer() == 0:
            ctx = SharedContext.get_instance()
            all_units = ctx.get_snapshot()

            new_pos = self.get_pos() + Pair.get_direction(direction)
            if len(filter(lambda e:e.is_collidable(), all_units[new_pos])) > 0:
                return False
            else:
                self.set_pos(new_pos)
                self.set_rom_timer(self.get_base_rom())
                
                return True
        return False

    def absolute_move(self, direction):
        self.last_direction = direction
        if self.get_rom_timer() == 0:
            self.set_pos(self.get_pos() + Pair.get_direction(direction))
            self.set_rom_timer(self.get_base_rom())

    def can_move(self, pos):
        ctx = SharedContext.get_instance()
        all_units = ctx.get_snapshot()
        return len(filter(lambda e:e.is_collidable(), all_units[pos])) == 0

    def move_toward(self, pos):
        min_p = None
        for n in self.get_pos().get_neighbors():
            if self.can_move(n) and (min_p is None or n.euclidean(pos) < min_p.euclidean(pos)):
                min_p = n

        if self.get_pos().euclidean(pos) < min_p.euclidean(pos):
            return
        self.try_move(self.get_pos().direction_to(min_p))

    def move_away(self, pos):
        max_p = None
        for n in self.get_pos().get_neighbors():
            if self.can_move(n) and (max_p is None or n.euclidean(pos) > max_p.euclidean(pos)):
                max_p = n

        self.try_move(self.get_pos().direction_to(max_p))

    def update(self):
        super(MobileEntity, self).update()

        self.set_rom_timer(max(0, self.get_rom_timer()-1))

class Player(MobileEntity):

    def __init__(self, pos):
        super(Player, self).__init__(pos)

        ctx = SharedContext.get_instance()

        ctx.register_key(KeyHandler(self, curses.KEY_UP, lambda k:self.try_move(UP)))
        ctx.register_key(KeyHandler(self, curses.KEY_RIGHT, lambda k:self.try_move(RIGHT)))
        ctx.register_key(KeyHandler(self, curses.KEY_DOWN, lambda k:self.try_move(DOWN)))
        ctx.register_key(KeyHandler(self, curses.KEY_LEFT, lambda k:self.try_move(LEFT)))
        ctx.register_key(KeyHandler(self, ord(' '), lambda k:self.shoot())) #spacebar

        self.base_rof = 25
        self.rof_timer = 0

        self.set_base_rom(2)

        self.hp = 500

    def get_str(self):
        return '&'

    def get_color_pair(self):
        return ColorController.get_color('magenta', 'white')

    def is_collidable(self):
        return False

    def is_transparent(self):
        return True

    def get_hp(self):
        return self.hp

    def get_base_rof(self):
        return self.base_rof

    def set_base_rof(self, new_rof):
        self.base_rof = new_rof
        self.rof_timer = min(self.rof_timer, new_rof)

    def shoot(self):
        if self.rof_timer == 0:
            SharedContext.get_instance().add_entity(Fireball(self.get_pos(), self.get_last_direction()))
            self.rof_timer = self.base_rof

    def update(self):
        super(Player,self).update()
        self.rof_timer = max(0, self.rof_timer-1)

        here = SharedContext.get_instance().get_snapshot()[self.get_pos()]
        if any([isinstance(a, Spooker) for a in here]):
            self.hp -= 1

    def is_dead(self):
        return self.hp <= 0

class Spooker(MobileEntity):
    
    def __init__(self, pos):
        super(Spooker, self).__init__(pos)

        self.set_base_rom(5)
        self.rom_timer = 0

        self.hp = 100

        self.flash_timer = 0


    def get_color_pair(self):
        player = SharedContext.get_instance().get_player_pos()[0]
        if self.get_pos().euclidean(player.get_pos()) < 2:
            if self.flash_timer % 4 < 2:
                return ColorController.get_color('black', 'white')
            else:
                return ColorController.get_color('white', 'black')
        return ColorController.get_color('red', 'white')

    def is_transparent(self):
        return False 

    def is_collidable(self):
        return True

    def update(self):
        self.flash_timer += 1
        ctx = SharedContext.get_instance()
        all_pos = ctx.get_snapshot()

        if any([isinstance(p,Fireball) for p in all_pos[self.get_pos()]]):
            self.hp -= 50

        if self.get_pos() in ctx.get_visible_posns():
            
            pl = ctx.get_player_pos()[0]
            
            pl_pos = pl.get_pos()
            dis = pl_pos.euclidean(self.get_pos()) 

            if dis < 5 :
                self.move_toward(pl_pos)

            elif dis > 5:
                self.move_away(pl_pos)

        self.rom_timer = max(0,self.rom_timer-1)
        
    def is_dead(self):
        return self.hp <= 0

    def get_str(self):
        return '@'

class FastSpooker(Spooker):

    def __init__(self, pos):
        super(FastSpooker, self).__init__(pos)

        self.set_base_rom(3)

        self.hp = 50

    def get_color_pair(self):
        player = SharedContext.get_instance().get_player_pos()[0]
        if self.get_pos().euclidean(player.get_pos()) < 2:
            if self.flash_timer % 4 < 2:
                return ColorController.get_color('black', 'white')
            else:
                return ColorController.get_color('white', 'black')
        return ColorController.get_color('blue', 'white')

class Fireball(MobileEntity):
    def __init__(self, pos, direction):
        super(Fireball, self).__init__(pos)
        self.direction = direction
        self.outside_vision_count = 0
        self.ded = False

        self.set_base_rom(2)

    def get_color_pair(self):
        return ColorController.get_color('red', 'yellow')

    def get_str(self):
        return 'O'

    def is_collidable(self):
        return False

    def update(self):
        super(Fireball, self).update()

        ctx = SharedContext.get_instance()
        here = ctx.get_snapshot()[self.get_pos()]
        for h in here:
            if h.is_collidable():
                self.ded=True


        me = self.get_pos().rounded()

        if me not in ctx.get_visible_posns():
            self.outside_vision_count += 1
        else:
            self.outside_vision_count = 0

        self.absolute_move(self.direction)

    def is_dead(self):
        return self.ded or self.outside_vision_count > 4

class Wall(Entity):
    def __init__(self, pos):
        super(Wall, self).__init__(pos)

    def is_transparent(self):
        return False

    def get_color_pair(self):
        return ColorController.get_color('green', 'green')

    def get_str(self):
        return ' '

class BreakableWall(Wall):

    def __init__(self, pos):
        super(BreakableWall, self).__init__(pos)

        self.hp = 3

    def get_str(self):
        return '#'

    def get_color_pair(self):
        return ColorController.get_color("black","green")

    def update(self):
        ctx = SharedContext.get_instance()
        fireballs = ctx.get_world().get_all_of_type(Fireball)
        if any([f.get_pos() == self.get_pos() for f in fireballs]):
            self.hp -= 1
        if self.hp == 0:
            t = random.choice(powerup_types)
            ctx.add_entity(Potion(self.get_pos(), t, powerup_durations[t]))

    def is_dead(self):
        return not bool(self.hp)

class Potion(Entity):
    def __init__(self, pos, bufftype, duration):
        super(Potion, self).__init__(pos)


        self.bufftype = bufftype
        self.duration = duration
        self.applied = False

    def update(self):
        super(Potion, self).update()
        ctx = SharedContext.get_instance()
        player = ctx.get_player_pos()[0]
        if self.get_pos() == player.get_pos():
            player.receive_buff(self.bufftype(player, self.duration))
            self.applied = True

    def is_dead(self):
        return self.applied

    def get_str(self):
        return 'U'

    def get_color_pair(self):
        return ColorController.get_color('black', 'white')

    def is_collidable(self):
        return False

class Buff(object):
    def __init__(self, unit, duration):
        self.unit = unit
        self.duration = duration

    def get_duration(self):
        return self.duration

    def apply(self):
        return 

    def tick(self):
        self.duration -= 1

    def cleanup(self):
        return 

    def __str__(self):
        return self.__class__.__name__

class Haste(Buff):
    def __init__(self, unit, duration):
        assert isinstance(unit, MobileEntity)
        super(Haste, self).__init__(unit, duration)
        

    def apply(self):
        self.old_rom = self.unit.get_base_rom()
        self.unit.set_base_rom(0)

    def cleanup(self):
        self.unit.set_base_rom(self.old_rom)

class Ghost(Buff):

    def apply(self):
        self.old_f = self.unit.try_move
        self.unit.try_move = self.unit.absolute_move

    def cleanup(self):
        self.unit.try_move = self.old_f

class Sith(Buff):

    def apply(self):
        self.old_base_rof = self.unit.get_base_rof()
        self.unit.set_base_rof(8)

    def cleanup(self):
        self.unit.set_base_rof(self.old_base_rof)

class Vision(Buff):
    def tick(self):
        super(Vision, self).tick()
        world = SharedContext.get_instance().get_world()
        world.visible_ent |= set(world.get_all_of_type(Spooker))
        self.w = world

powerup_types = [Vision, Haste, Sith, Ghost]
powerup_durations = {Vision:10, Haste:200, Sith:350, Ghost:150}



def main():
    try:
        mc = MainController(world_height=60, world_width=180)
        player = Player(Pair(20,20))
        mc.w.add(player)
        walls, en, powerups, rooms = dungeon.weird_dungeon(mc.w.height, mc.w.width, powerup_density=.3)
        wall_pos = []
        for i in range(mc.w.height):
            for j in range(mc.w.width):
                if walls[i][j]:
                    wall_pos.append(Pair(i,j))

        en = map(lambda p:Pair(p[0], p[1]), en)
        powerups = map(lambda p:Pair(p[0], p[1]), powerups)

        for w in wall_pos:
            if random.random() < .99:
                wa = Wall(w)
            else:
                wa = BreakableWall(w)

            mc.w.add(wa)

        for e in en:
            t = random.choice([Spooker, FastSpooker])
            if t == FastSpooker:
                mc.w.add(FastSpooker(e))
            elif t == Spooker:
                mc.w.add(Spooker(e))

        for p in powerups:
            tp = random.choice(powerup_types)
            pot = Potion(p, tp, powerup_durations[tp])
            mc.w.add(pot)

        mc.dc.full_draw()
        while not player.is_dead():
            mc.tock()
            sleep(TIME_UNIT)
    finally:
        curses.endwin()
        log = SharedContext.get_instance().log_list

        print 'Logged:',log

main()
