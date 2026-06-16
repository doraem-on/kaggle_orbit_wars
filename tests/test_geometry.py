import unittest
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from geometry import distance, angle_between, line_intersects_circle, predict_planet_pos

class TestGeometry(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(distance((0, 0), (3, 4)), 5.0)
        
    def test_angle_between(self):
        self.assertAlmostEqual(angle_between((0, 0), (1, 1)), math.pi / 4)
        
    def test_line_intersects_circle(self):
        # Line from (0,0) to (10,0), circle at (5,0) with radius 2 -> intersects
        self.assertTrue(line_intersects_circle((0, 0), (10, 0), (5, 0), 2))
        
        # Line from (0,0) to (10,0), circle at (5,5) with radius 2 -> no
        self.assertFalse(line_intersects_circle((0, 0), (10, 0), (5, 5), 2))
        
        # Line barely grazing the circle
        self.assertTrue(line_intersects_circle((0, 0), (10, 0), (5, 2), 2))

    def test_predict_planet_pos(self):
        # Planet at (50, 60), center (50,50), r=10. Angle = pi/2
        # After 1 turn with angular_velocity pi/2, should be at (40, 50) i.e., angle pi
        pos = predict_planet_pos(50, 60, 1, math.pi / 2, (50, 50))
        self.assertAlmostEqual(pos[0], 40.0)
        self.assertAlmostEqual(pos[1], 50.0)

if __name__ == '__main__':
    unittest.main()
