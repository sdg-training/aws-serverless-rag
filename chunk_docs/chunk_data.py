import json
import os
import boto3

def chunk(event, context):
    print("S3 Event received:", json.dumps(event))

    # Initialize the Bedrock Agent client
    bedrock_agent = boto3.client('bedrock-agent')

    # fetch knowledgebase ID / bedrock_datasource ID from parameter store
    ssm = boto3.client('ssm')
    
    get_knowledge_base_id_response = ssm.get_parameter(Name="/rag-lab/knowledgebase/id")
    print("Knowledge Base ID response from SSM:", get_knowledge_base_id_response)   
    knowledge_base_id = get_knowledge_base_id_response["Parameter"]["Value"]

    get_data_source_id_response = ssm.get_parameter(Name="/rag-lab/datasource/id")
    print("Data Source ID response from SSM:", get_data_source_id_response)
    data_source_id_unsplitted = get_data_source_id_response["Parameter"]["Value"]
    
    data_source_id = data_source_id_unsplitted.split('|')[1]
    print('final data source id: ', data_source_id)

    try:
        # Correct method name is start_ingestion_job
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=knowledge_base_id,
            dataSourceId=data_source_id
        )

        print("Ingestion Job Started:", response)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Ingestion job initiated successfully",
                "ingestionJobId": response['ingestionJob']['ingestionJobId'],
                "status": response['ingestionJob']['status']
            })
        }

    except bedrock_agent.exceptions.ValidationException as e:
        print(f"Validation Error: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Validation error: {str(e)}"})
        }
    except bedrock_agent.exceptions.ResourceNotFoundException as e:
        print(f"Resource Not Found: {e}")
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Resource not found: {str(e)}"})
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
