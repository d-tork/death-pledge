import unittest
from collections import namedtuple

from deathpledge.api_calls import bing


class BingGeocoordsTestCase(unittest.TestCase):
    def setUp(self):
        self.full_address = '1600 Pennsylvania Ave NW, Washington, DC 20500'
        self.zip_code = 20500

    def test_fetch_geocoords_with_zip_code(self):
        coords = bing.get_coords(address=self.full_address, zip_code=self.zip_code)
        self.assertIsInstance(coords, dict)
        self.assertIn('lat', coords)
        self.assertIsInstance(coords.get('lat'), float)
        self.assertAlmostEqual(coords.get('lat'), 38.89743, places=2)

    def test_fetch_geocoords_without_zip_code(self):
        coords = bing.get_coords(address=self.full_address)
        self.assertIsInstance(coords, dict)
        self.assertIn('lat', coords)
        self.assertIsInstance(coords.get('lat'), float)


class BingCommuteTestCase(unittest.TestCase):
    def setUp(self):
        self.start = (38.89762138428869, -77.03660353579274)
        self.end = (38.88987263256243, -77.00905540262258)

    def test_get_commute(self):
        commute_dict = bing.get_bing_commute_time(
            startcoords=self.start, endcoords=self.end)
        self.assertIsInstance(commute_dict, tuple)
        self.assertIsInstance(commute_dict.commute_time, float)
        self.assertIsInstance(commute_dict.first_leg, str)
        self.assertIsInstance(commute_dict.first_walk, float)


class BingCommuteFirstLegTestCase(unittest.TestCase):
    def setUp(self):
        self.trip = self._create_fake_trip()

    @staticmethod
    def _create_fake_trip():
        trip = {
            'routeLegs': [
                {
                    'itineraryItems': [
                        {'iconType': 'Walk', 'travelDuration': 769},
                        {'iconType': 'Train', 'travelDuration': 900},
                        {'iconType': 'Walk', 'travelDuration': 300},
                    ]
                }
            ],
            'travelDuration': 1969
        }
        return trip

    def test_get_first_leg_of_trip(self):
        first_leg = bing.get_first_leg_from_trip(self.trip)
        self.assertIsInstance(first_leg, dict)
        self.assertIn('mode', first_leg)
        self.assertEqual(first_leg.get('mode'), 'Train')
        self.assertEqual(first_leg.get('walktime'), 12.8)

    def test_unknown_transit_mode_raises_exception(self):
        modified_trip = self._create_fake_trip()
        modified_trip['routeLegs'][0]['itineraryItems'][0]['iconType'] = 'Jitpack'
        with self.assertRaises(ValueError):
            bing.get_first_leg_from_trip(modified_trip)


if __name__ == '__main__':
    unittest.main()
