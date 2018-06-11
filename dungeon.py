import random

def weird_dungeon(height, width, enemy_density=.5, powerup_density = .2):
    gr = [[0]*width for i in range(height)]
    rooms = []
    def helper(gr, rooms, lowx, lowy, highx, highy):
        if highx-lowx <= 3 or highy - lowy <= 3:
            return 

        width,height = random.randint(3, highx-lowx-1), random.randint(3, highy-lowy-1)
        px, py = random.randint(lowx, highx-width-1), random.randint(lowy, highy-height-1)
        rooms.append((py, px, py+height, px+width))

        removed = [1]*(width * 2 + height * 2)
        for i in range(max(int(len(removed)/20.), 5)):
            removed[random.randint(0,len(removed)-1)] = 0

        for i in range(px, px+width):
            if removed.pop():
                gr[py][i]=1
            if removed.pop():
                gr[py+height][i]=1

        for i in range(py, py+height):
            if removed.pop():
                gr[i][px]=1
            if removed.pop():
                gr[i][px+width]=1

        gr[py+height][px+width] = 1

        helper(gr, rooms, lowx, lowy, highx, py-2) #above
        helper(gr, rooms, lowx, py,  px-2, highy) #left
        helper(gr, rooms, px+width+2, py, highx, highy) #right
        helper(gr, rooms, px, py+height+2, px+width, highy) #below

        helper(gr, rooms, px+2, py+2, px+width - 2, py+height - 2) #inside
    helper(gr, rooms, 2, 2, width-2, height-2)
    
    for i in range(width):
        gr[0][i] = 1
        gr[height-1][i]=1

    for i in range(height):
        gr[i][0]=1
        gr[i][width-1]=1

    enemies = []
    power_ups = []
    for k in range(int(len(rooms)*enemy_density + 1)):
        room = random.choice(rooms)
        ly, lx, hy, hx = room

        py, px = random.randint(ly+1,hy-2), random.randint(lx+1, hx-2)

        enemies.append((py, px))

    for k in range(int(len(rooms)*powerup_density + 1)):
        room = random.choice(rooms)
        ly, lx, hy, hx = room

        py, px = random.randint(ly+1,hy-2), random.randint(lx+1, hx-2)


        power_ups.append((py, px))

    return gr, enemies, power_ups

