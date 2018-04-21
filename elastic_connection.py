import elasticsearch

es = elasticsearch.Elasticsearch()

mappings = {
  'mappings': {
    'store': {
      'properties': {
        'name': { 'type': 'text'  },
        'store_location': { 'type': 'text'  },
        'address': { 'type': 'text' },
        'city': { 'type': 'text' },
        'state': { 'type': 'text' },
        'zip_code': { 'type': 'text' },
        'latlong': { 'type': 'geo_point' },
        'county': { 'type': 'text' },
      }
    }
  }
}
