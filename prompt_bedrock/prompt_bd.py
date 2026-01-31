import json
import boto3
import os

def prompt(event, context):

    print("Event received:", json.dumps(event))
    # 1. Extract query

    body = json.loads(event["body"])
    # user_query = body.get("query")
    user_query = body["query"]

    if not user_query:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing user query."})
        }

    # 2. Fetch knowledge base ID and model ID from SSM
    ssm = boto3.client("ssm")
    try:
        get_knowledge_base_id_response = ssm.get_parameter(Name="/rag-lab/knowledgebase/id")
        knowledge_base_id = get_knowledge_base_id_response["Parameter"]["Value"]
        print('knowledge base id: ', knowledge_base_id)

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to fetch config from SSM: {str(e)}"})
        }

    # Call Bedrock retrieve_and_generate API to retrieve relevant data chunks from kb and generate response to user
    try:
        # Set the Bedrock model to use for text generation
        model_arn = "arn:aws:bedrock:eu-central-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0"

        bedrock = boto3.client("bedrock-agent-runtime", region_name="eu-central-1")

        response = bedrock.retrieve_and_generate(
            input={
                'text': user_query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': model_arn
                    # guardrail configuration can be added here if needed
                }
            }
        )
        # save bedrock response and extract final message
        llm_message = response["output"]["text"]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "response": llm_message,
            })
        }

    except Exception as e:
        print("Error calling Converse API:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Converse API failed: {str(e)}"})
        }
