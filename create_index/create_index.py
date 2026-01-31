import json
import os
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
import time

def create(event, context):

    
    index_name = "88-busta"
    region = 'eu-central-1'

    collection_endpoint = os.environ['COLLECTION_ENDPOINT']


    # set up authentication
    service = 'aoss'

    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    print(credentials) 

    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token
    )


    # Create the OpenSearch client
    host = collection_endpoint.replace("https://", "")
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    
    # Corrected index definition
    index_definition = {
        "settings": {
            "index": {
                "knn": True,
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn.algo_param.ef_search": 512
            }
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024, 
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2"
                    },
                },
                "text": {
                    "type": "text"
                },
                "text-metadata": {
                    "type": "text"
                }
            }
        }
    }
    
    try:
        # Delete index if it exists (for testing)
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"Deleted existing index: {index_name}")
            time.sleep(10)
        
        # Create the index
        response = client.indices.create(index=index_name, body=index_definition)
        print(f"Index creation response: {response}")
        
        # Wait for index to be ready
        print("Waiting for index to be ready...")
        time.sleep(30)
        
        # Verify index exists
        if client.indices.exists(index=index_name):
            print(f"✓ Index {index_name} exists")
            
            # Get index information
            index_info = client.indices.get(index=index_name)
            print(f"Index info: {index_info}")
            
            # List all indexes
            all_indexes = client.cat.indices(format='json')
            print(f"All indexes: {all_indexes}")
            
        else:
            print(f"✗ Index {index_name} does not exist")
            
    except Exception as e:
        print(f"Error: {str(e)}")
