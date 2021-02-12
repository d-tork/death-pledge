import unittest

from deathpledge.classes import Home
from deathpledge import enrich


class EnrichTestCase(unittest.TestCase):
    @staticmethod
    def _instantiate_new_home():
        home = Home()
        home['full_address'] = '1600 Pennsylvania Ave NW, Washington, DC 20500'
        home['parsed_address'] = {'ZipCode': 20500}
        return home


class EnrichGeocoordsTestCase(EnrichTestCase):
    def setUp(self):
        self.new_home = self._instantiate_new_home()

    def test_new_home_has_no_geocoordds(self):
        with self.assertRaises(KeyError):
            self.new_home['geocoords']

    def test_set_new_geocoords(self):
        enrich.add_coords(self.new_home)
        geocoords_as_dict = self.new_home['geocoords']
        self.assertIsInstance(geocoords_as_dict, dict)

    def test_skip_setting_existing_geocoords(self):
        self._set_fake_coords()
        enrich.add_coords(self.new_home)
        lat_should_be_1 = self.new_home['geocoords'].get('lat')
        self.assertEqual(lat_should_be_1, 1.000)

    def test_existing_geocoords_force_retrieved(self):
        self._set_fake_coords()
        enrich.add_coords(self.new_home, force=True)
        lat_should_not_be_1 = self.new_home['geocoords'].get('lat')
        self.assertNotEqual(lat_should_not_be_1, 1.000)

    def _set_fake_coords(self):
        self.new_home['geocoords'] = dict(lat=1.000, lon=2.000)


class EnrichCommuteTestCase(EnrichTestCase):
    fake_commute = {
        'work_commute': 999,
        'first_walk_mins': 999,
        'first_leg_type': 'jetpack'
    }

    def setUp(self):
        self.new_home = self._instantiate_new_home()
        enrich.add_coords(self.new_home)

    def _set_fake_commute(self):
        self.new_home.update(self.fake_commute)


if __name__ == '__main__':
    unittest.main()
