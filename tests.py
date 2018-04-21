from elasticsearch.exceptions import NotFoundError
import os
import time
import unittest

from elastic_connection import es, mappings
from find_store import StoreLocator, convert_from_meter
from settings import ES_INDEX

def setUpModule():
    if os.environ.get('ENVIRONMENT') != 'testing':
        raise Exception('Please set ENVIRONMENT=testing')

class TestStoreLocator(unittest.TestCase):
    def setUp(self):
        try:
            es.indices.delete(ES_INDEX)
        except NotFoundError:
            pass
        es.indices.create(ES_INDEX, body=mappings)
        # create dummy data
        for i in range(10):
            j = str(i)
            store = {
                'name': j + 'name',
                'store_location': j + 'location',
                'address': j + 'address',
                'city': j + 'city',
                'state': j + 'state',
                'zip_code': j * 5,
                # using ints here would make each store be far far apart
                'latlong': {'lat': i * .00001, 'lon': i * .00001},
                'county': j + 'county',
            }
            es.index(index=ES_INDEX, doc_type='store', body=store)

        # wait for records
        time.sleep(1)
        print(es.search(index=ES_INDEX, body={'query': {'match_all': {}}}))

    def tearDown(self):
        es.indices.delete(ES_INDEX)

    def test_store_search_no_count(self):
        locator = StoreLocator(latitude=0, longitude=0)
        stores = locator._store_search()

        hits = stores['hits']['hits']

        self.assertEqual(len(hits), 1)

        # closest store is the one at 0,0
        self.assertEqual(hits[0]['_source']['name'], '0name')

    def test_store_search(self):
        locator = StoreLocator(latitude=0, longitude=0)
        # return 4 stores
        stores = locator._store_search(count=4)

        hits = stores['hits']['hits']

        self.assertEqual(len(hits), 4)

        for i, hit in enumerate(hits):
            self.assertEqual(hit['_source']['name'], str(i) + 'name')

    def test_get_stores_formatted_text(self):
        locator = StoreLocator(latitude=10 * .00001, longitude=10 * .00001)
        output = locator.get_stores_formatted()


        self.assertEqual(
            output,
            (
                '9name: 9address, 9city, 9state 99999 '
                '| 0.0009817913030925446 mi away'
            )
        )

class TestUtils(unittest.TestCase):
    def test_convert_from_meter(self):
        self.assertEqual(
            convert_from_meter(1, 'mi'),
            0.000621371
        )

        self.assertEqual(
            convert_from_meter(2, 'mi'),
            0.000621371 * 2
        )

        self.assertEqual(
            convert_from_meter(1, 'km'),
            .001
        )
        self.assertEqual(
            convert_from_meter(2, 'km'),
            .002
        )

    def test_convert_from_meter_zero(self):
        self.assertEqual(
            convert_from_meter(0, 'km'),
            0
        )

        self.assertEqual(
            convert_from_meter(0, 'mi'),
            0
        )

    def test_convert_from_meter_wrong_unit(self):
        with self.assertRaises(ValueError):
            convert_from_meter(1, 'mile')
