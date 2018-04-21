import csv
import geocoder

from elastic_connection import es, mappings

es.indices.delete('stores')
es.indices.create('stores', body=mappings)

with open('store-locations.csv') as f:
    reader = csv.DictReader(f)

    for row in reader:
        store = {
            'name': row['Store Name'],
            'store_location': row['Store Location'],
            'address': row['Address'],
            'city': row['City'],
            'state': row['State'],
            'zip_code': row['Zip Code'],
            'latlong': {'lat': row['Latitude'], 'lon': row['Longitude']},
            'county': row['County'],
        }

        es.index(index='stores', doc_type='store', body=store)
