import argparse
import geocoder
import time

from elastic_connection import es
from settings import ES_INDEX

def get_latlong(location_str):
    '''
    Given any string denoting some location, return a lat-long for that
    location. There is a retry here given we are using google's free tier.  In
    case exceptions arise, this process bails out.
    '''
    retries = 3
    attempts = 0
    while attempts < retries:
        attempts += 1
        location = geocoder.google(location_str)
        if location.error and retries>=attempts:
            # We're hitting public api rate limits or some other error, bail
            raise Exception(str(location.error))
        elif location.error:
            # wait for api to allow us to query it
            time.sleep(10)
        else:
            return location.latlng

def convert_from_meter(value, unit_to):
    '''
    Helper function to convert from the default meters used by elasticsearch
    to km or miles.  Ideally this would be better fleshed out than a simple
    meter - mi/km translation.
    '''

    if not unit_to in ('mi', 'km'):
        raise ValueError('unit_to can only be mi or km, got: ' + str(unit_to))

    if unit_to == 'mi':
        return value * 0.000621371
    else:
        return value / 1000


class StoreLocator(object):
    def __init__(self, location_str=None, unit='mi', latitude=None, longitude=None):
        '''
        Inputs:
            location_str: Used for cli utility.  Uses geocoder to get latlong
            unit: defaults to miles, also can use km
            latitude, longitude: so far only used in unit tests but can have
                utility in the cli
        '''

        if not location_str and (latitude is None or longitude is None):
            raise ValueError((
                'Please provide either a location '
                'string, or a latlong combination.'
            ))

        if latitude is not None and longitude is not None:
            self.latitude = latitude
            self.longitude = longitude
        else:
            self.latitude, self.longitude = get_latlong(location_str)

        self.unit = unit
        self.scale = ('10km', '6.2mi')[unit=='mi']

    def _store_search(self, count=1):
        '''
        Queries elasticsearch for the closest store
        '''
        query = {
            'query': {
                'function_score': {
                    'functions': [{
                        'gauss': {
                            'latlong': {
                                'origin': {
                                    'lat': self.latitude,
                                    'lon': self.longitude
                                },
                                'scale': '1mi'
                            }
                        }
                    }]
                }
            },
            'script_fields': {
                'distance': {
                    'script': "doc['latlong'].arcDistance({},{}) * {}".format(
                        self.latitude,
                        self.longitude,
                        convert_from_meter(1.0, self.unit)
                    )
                }
            },
            '_source': True,
            'size': count,

        }
        return es.search(index=ES_INDEX, body=query)

    def get_stores_formatted(self, output='text'):
        '''
        Returns all stores in a usable json format or readable text format.
        Written
        '''

        stores = self._store_search()
        hits = stores['hits']['hits']
        if output == 'json':
            output_json = []
            for hit in hits:
                record = hit['_source']
                record.update(hit['fields'])
                record['distance'] = record['distance'][0]
                output_json.append(record)
            return output_json
        else:
            output_strs = []
            str_template = (
                '%(name)s: %(address)s, %(city)s, %(state)s %(zip_code)s '
                '| %(distance)s %(unit)s away'
            )

            for hit in hits:
                store_json = hit.copy()
                store_json['_source']['distance'] = store_json['fields']['distance'][0]
                store_json['_source']['unit'] = self.unit

                output_strs.append(str_template % store_json['_source'])

            return '\n'.join(output_strs)

def get_stores(arg_dict):
    store_locator = StoreLocator(arg_dict['location'], unit=arg_dict['unit'])
    print(store_locator.get_stores_formatted(output=arg_dict['output']))

def parse_args():
    arg_parser = argparse.ArgumentParser(description='Locate the nearest stores to you.')

    location_group = arg_parser.add_mutually_exclusive_group(required=True)
    location_group.add_argument('--address')
    location_group.add_argument('--zip')

    arg_parser.add_argument('--unit', choices=('mi', 'km'), default='mi')
    arg_parser.add_argument('--output', choices=('text', 'json'), default='text')

    args = arg_parser.parse_args()
    return {
        'location': args.address or args.zip,
        'unit': args.unit,
        'output': args.output,
    }

if __name__ == '__main__':
    arg_dict = parse_args()
    get_stores(arg_dict)
