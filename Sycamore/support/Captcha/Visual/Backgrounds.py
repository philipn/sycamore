""" Captcha.Visual.Backgrounds

Background layers for visual CAPTCHAs
"""
#
# PyCAPTCHA Package
# Copyright (C) 2004 Micah Dowty <micah@navi.cx>
#

from Sycamore.support.Captcha.Visual import Layer, Pictures
import random, os, math
import ImageDraw, Image


class SolidColor(Layer):
    """A solid color background. Very weak on its own, but good
       to combine with other backgrounds.
       """
    def __init__(self, color="white"):
        self.color = color

    def render(self, image):
        image.paste(self.color)


class Grid(Layer):
    """A grid of lines, with a given foreground color.
       The size is given in pixels. The background is transparent,
       so another layer (like SolidColor) should be put behind it.
       """
    def __init__(self, size=16, foreground="black"):
        self.size = size
        self.foreground = foreground
        self.offset = (random.uniform(0, self.size),
                       random.uniform(0, self.size))

    def render(self, image):
        draw = ImageDraw.Draw(image)

        for i in xrange(image.size[0] / self.size + 1):
            draw.line( (i*self.size+self.offset[0], 0,
                        i*self.size+self.offset[0], image.size[1]), fill=self.foreground)

        for i in xrange(image.size[0] / self.size + 1):
            draw.line( (0, i*self.size+self.offset[1],
                        image.size[0], i*self.size+self.offset[1]), fill=self.foreground)


class TiledImage(Layer):
    """Pick a random image and a random offset, and tile the rendered image with it"""
    def __init__(self, imageFactory=Pictures.abstract):
        self.tileName = imageFactory.pick()
        self.offset = (random.uniform(0, 1),
                       random.uniform(0, 1))

    def render(self, image):
        tile = Image.open(self.tileName)
        for j in xrange(-1, int(image.size[1] / tile.size[1]) + 1):
            for i in xrange(-1, int(image.size[0] / tile.size[0]) + 1):
                dest = (int((self.offset[0] + i) * tile.size[0]),
                        int((self.offset[1] + j) * tile.size[1]))
                image.paste(tile, dest)


class CroppedImage(Layer):
    """Pick a random image, cropped randomly. Source images should be larger than the CAPTCHA."""
    def __init__(self, imageFactory=Pictures.nature):
        self.imageName = imageFactory.pick()
        self.align = (random.uniform(0,1),
                      random.uniform(0,1))

    def render(self, image):
        i = Image.open(self.imageName)
        image.paste(i, (int(self.align[0] * (image.size[0] - i.size[0])),
                        int(self.align[1] * (image.size[1] - i.size[1]))))


def distance(point, set):
      x, y = point
      min = None
      for p1, p2 in set:
         d = math.sqrt((p1 - x)**2 + (p2 - y)**2)
         if not min or d < min:
           min = d
      return min

class RandomDots(Layer):
    """Draw random colored dots"""
    def __init__(self, colors=("white", "black"), dotSize=10, numDots=40, density=20):
        self.colors = colors
        self.dotSize = dotSize
        self.numDots = numDots
        self.seed = random.random()
        self.density = density


    def render(self, image):
        draw = ImageDraw.Draw(image)

        r = random.Random(self.seed)
        added_points = []
        for i in xrange(self.numDots):
            bx = int(r.uniform(0, image.size[0]-self.dotSize))
            by = int(r.uniform(0, image.size[1]-self.dotSize))
            # make sure our dots aren't too close together
            while self.density and added_points and distance((bx,by), added_points) < self.density:
                bx += self.density/2
                by += self.density/2
            added_points.append((bx,by))
            xoffset = self.dotSize
            yoffset = self.dotSize

            dotcolor = random.choice(self.colors)
            draw.ellipse( (bx, by,
              bx+xoffset, by+yoffset), outline=dotcolor, fill=dotcolor)


class RandomRects(Layer):
    """Draw random colored dots"""
    def __init__(self, colors=("white", "black"), rectSize=20, numRects=1000):
        self.colors = colors
        self.rectSize = rectSize
        self.numRects = numRects
	self.seed = random.random()

    def render(self, image):
        r = random.Random(self.seed)
        for i in xrange(self.numRects):
            bx = int(r.uniform(0, image.size[0]-self.rectSize))
            by = int(r.uniform(0, image.size[1]-self.rectSize))
            xoffset = random.randint(0, self.rectSize*1)
            yoffset = random.randint(0, self.rectSize*1)
            image.paste(r.choice(self.colors), (bx, by,
                                                bx+xoffset,
                                                by+yoffset))



### The End ###
