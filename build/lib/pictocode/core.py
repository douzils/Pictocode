"""
Core Pictocode logic (canvas and elements management).
"""

class Canvas:
    def __init__(self):
        self.elements = []

    def add_element(self, element):
        self.elements.append(element)

class Element:
    def __init__(self, x, y):
        self.x = x
        self.y = y
