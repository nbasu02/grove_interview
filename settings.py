import os

if os.environ.get('ENVIRONMENT') == 'testing':
    ES_INDEX = 'stores_test'
else:
    ES_INDEX = 'stores'
