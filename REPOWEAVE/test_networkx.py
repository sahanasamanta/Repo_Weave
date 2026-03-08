import networkx as nx
import json

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({
            'networkx_version': nx.__version__,
            'message': 'Test successful'
        })
    }