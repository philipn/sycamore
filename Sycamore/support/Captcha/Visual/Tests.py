""" Captcha.Visual.Tests

Visual CAPTCHA tests
"""
#
# PyCAPTCHA Package
# Copyright (C) 2004 Micah Dowty <micah@navi.cx>
#

from Sycamore.support.Captcha.Visual import Text, Backgrounds, Distortions, ImageCaptcha, Colors
from Sycamore.support.Captcha import Words, Numbers
import random

__all__ = ["PseudoGimpy", "AngryGimpy", "AntiSpam"]


class PseudoGimpy(ImageCaptcha):
    """A relatively easy CAPTCHA that's somewhat easy on the eyes"""
    def getLayers(self):
        word = Numbers.pick()
        self.addSolution(word)
        return [
            random.choice([
                Backgrounds.CroppedImage(),
                Backgrounds.TiledImage(),
            ]),
            Text.TextLayer(word, borderSize=1),
            Distortions.SineWarp(),
            ]


class AngryGimpy(ImageCaptcha):
    """A harder but less visually pleasing CAPTCHA"""
    def getLayers(self):
        word = Numbers.pick()
        self.addSolution(word)
        return [
            Backgrounds.SolidColor(Colors.RandomColor()),
            Backgrounds.RandomDots(colors=Colors.RandomColors(5), numDots=200),
            Text.TextLayer(word, borderSize=1, textColor=Colors.RandomColor()),
            Distortions.WigglyBlocks(),
            ]

class HappyGimpy(ImageCaptcha):
    """A harder but less visually pleasing CAPTCHA"""
    def getLayers(self):
        word = Words.defaultWordList.pick()
        self.addSolution(word)
        randomColors = [(76,62,255), (240,0,0), (0,255,18), (194,217,0), (159,139,104)]
        rectColors = ["red"]
        #for i in range(0, len(randomColors)-1):
        #  id = random.randint(0, len(randomColors)-1)
        #  color = randomColors.pop(id)
        #  rectColors.append(color)

        return [
            Backgrounds.SolidColor(color=random.choice(randomColors)),
            Backgrounds.RandomRects(colors=rectColors),
            Text.TextLayer(word, borderSize=1, textColor="black", borderColor="black"),
            Distortions.WigglyBlocks(),
            ]

class BWGimpy(ImageCaptcha):
    """A harder but less visually pleasing CAPTCHA"""
    solid_white = Backgrounds.SolidColor(color="white")

    def __init__(self, word=None):
        self.word = word
        ImageCaptcha.__init__(self) 

    def getLayers(self):
        return [
            BWGimpy.solid_white,
            Text.TextLayer(self.word, borderSize=1, textColor="black", borderColor="black"),
            Backgrounds.RandomDots(colors=("white",)),
            Distortions.SineWarp(),
            ]

class AntiSpam(ImageCaptcha):
    """A fixed-solution CAPTCHA that can be used to hide email addresses or URLs from bots"""
    fontFactory = Text.FontFactory(20, "vera/VeraBd.ttf")
    defaultSize = (512,50)

    def getLayers(self, solution="murray@example.com"):
        self.addSolution(solution)

        textLayer = Text.TextLayer(solution,
                                   borderSize = 2,
                                   fontFactory = self.fontFactory)

        return [
            Backgrounds.CroppedImage(),
            textLayer,
            Distortions.SineWarp(amplitudeRange = (2, 4)),
            ]

### The End ###
