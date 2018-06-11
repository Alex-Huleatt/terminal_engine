from util import * 

class Entity(object): #base class

    def __init__(self, pos):
        assert isinstance(pos, Pair)

        self.pos = pos
        self.buffs = set()

    def is_transparent(self):
        return True

    def get_pos(self):
        return self.pos.rounded()

    def get_color_pair(self):
        return 0

    def get_str(self):
        return 'E'

    def get_draw_priority(self): #behavior not implemented
        return 0

    def get_chars(self):
        return [BufferedChar(self.get_pos(), self.get_str(), self.get_color_pair())]

    def update(self):
        to_remove = set()
        for b in self.buffs:
            b.tick()
            if b.get_duration() == 0:
                to_remove.add(b)
                b.cleanup()
        self.buffs -= to_remove

    def copy(self):
        return self

    def is_dead(self):
        return False

    def set_pos(self, p):
        self.pos = p

    def is_collidable(self):
        return True

    def __str__(self):
        return '[%s: @%s]'%(type(self), self.get_pos())

    def receive_buff(self, buff):
        buff.apply()
        self.buffs.add(buff)

    def get_buffs(self):
        return self.buffs

