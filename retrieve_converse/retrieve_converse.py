import json
import boto3
import os

def retrieve_kb_chunk(event, context):

    print("Event received:", json.dumps(event))

    # Step 1. Extract user query
    body = json.loads(event["body"])
    print("Request body:", body)
    # user_query = body.get("query")
    user_query = body["query"]

    # return error if no user_query available
    if not user_query:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing user query."})
        }

    # Step 2. Fetch knowledge base ID and model ID from SSM
    ssm = boto3.client("ssm")
    try:
        get_knowledge_base_id_response = ssm.get_parameter(Name="/rag-lab/knowledgebase/id")
        knowledge_base_id = get_knowledge_base_id_response["Parameter"]["Value"]
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to fetch config from SSM: {str(e)}"})
        }

    #Step 3: call retrieve api to Retrieve relevant data chunks from Bedrock Knowledge base
    try:

        bedrock = boto3.client("bedrock-agent-runtime", region_name="eu-central-1")

        kb_response = bedrock.retrieve(
            retrievalQuery={
                'text': user_query
            },
            knowledgeBaseId=knowledge_base_id,
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5,
                }
            }

        )

        # Step 4: Pass kb_response to bedrock converse api to get final response
        return augment_kb_response(kb_response, user_query)

    except Exception as e:
        print("Error calling Converse API:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Converse API failed: {str(e)}"})
        }

#  function to call bedrock converse api
def augment_kb_response(kb_response, user_query):

    # fetch guardrail id and version from ssm
    ssm = boto3.client("ssm")
    try:
        get_bedrock_guardrail_id_response = ssm.get_parameter(Name="/rag-lab/bedrock/guardrail-id")
        bedrock_guardrail_id = get_bedrock_guardrail_id_response["Parameter"]["Value"]

        get_bedrock_guardrail_version_response = ssm.get_parameter(Name="/rag-lab/bedrock/guardrail-version")
        bedrock_guardrail_version = get_bedrock_guardrail_version_response["Parameter"]["Value"]
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to fetch config from SSM: {str(e)}"})
        }
 
    # Define a system prompt
    system_prompt = """ You are a Cloud and AI expert. Provide answers in CLEAN, SINGLE-PARAGRAPH format.

        STRICT FORMATTING RULES - MUST FOLLOW:
        1. **NO numbered lists**: Do not use "1.", "2.", "3." or any numbered formatting
        2. **NO line breaks**: Entire response must be a single continuous paragraph
        3. **Bullet formatting**: If listing items, use • with normal spacing: "Key points • First item • Second item"
        4. **NO indentation**: No spaces or tabs at the beginning of lines
        5. **NO markdown**: No **, *, #, or any formatting symbols

        RESPONSE TEMPLATE - FOLLOW EXACTLY:
        "[1-2 sentence direct answer]. [Supporting details in continuous sentences]. [If listing: Additional aspects include • Item one • Item two • Item three]. [Brief conclusion if needed]."

        BAD EXAMPLES TO AVOID:
        1. "Key points:\n   1. First point\n   2. Second point"
        2. "Themes include:\n   * Theme one\n   * Theme two"
        3. Any response with line breaks or numbered lists

        GOOD EXAMPLES:
        1. "Amazon's 2021 message emphasized pandemic resilience and growth. The company helped millions during COVID-19 while expanding services. Key achievements • Reached 200 million Prime members • Grew to 1.3 million employees • Supported 1.9 million small businesses. AWS reached $50 billion run rate, showing continued innovation." 
        2. "AWS provides scalable cloud solutions including compute, storage, and databases. Key features • On-demand availability • Global infrastructure • Flexible pricing. Organizations use these to improve agility and reduce costs." 

        If context insufficient: "Based on available information, I cannot provide a complete answer."

        CRITICAL: Your entire response must be one paragraph with no line breaks or numbered lists.
    """

    # Define a user prompt template
    user_prompt_template = """Here is some additional context:
        <context>
        {contexts}
        </context>

        Please provide an answer to this user query:
        <query>
        {user_query}
        </query>

        The response should be specific and use statistics or numbers when possible.
    """

    contexts = [rr['content']['text'] for rr in kb_response['retrievalResults'] ]

    # Set the Bedrock model to use for text generation
    model_id = "eu.anthropic.claude-3-5-sonnet-20240620-v1:0"

    # Build Converse API request
    converse_request = {
        "system": [
            {"text": system_prompt}
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "text": user_prompt_template.format(contexts=contexts, user_query=user_query)
                    }
                ]
            }
        ],
        "inferenceConfig": {
            "temperature": 0.4,
            "topP": 0.9,
            "maxTokens": 500
        }
    }

    try:
        bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")

        # Call Bedrock's Converse API to generate the final answer to user query with guardrail enforcement
        converse_response = bedrock.converse(
            modelId=model_id,
            system=converse_request['system'],
            messages=converse_request["messages"],
            inferenceConfig=converse_request["inferenceConfig"],
            guardrailConfig={
                "guardrailIdentifier": bedrock_guardrail_id,
                "guardrailVersion": bedrock_guardrail_version,
                "trace": "enabled"
            }
        )

        # show bedrock intervention traces
        trace = converse_response.get("trace", {})
        guardrail_trace = trace.get("guardrail", {})

        if guardrail_trace:
            print("Guardrail trace detected:")

            # Input interventions (user prompt, system prompt, KB context)
            input_assessments = guardrail_trace.get("inputAssessments", [])
            for assessment in input_assessments:
                print("Input assessment:")
                print(json.dumps(assessment, indent=2))

            # Output interventions (model response)
            output_assessments = guardrail_trace.get("outputAssessments", [])
            for assessment in output_assessments:
                print("Output assessment:")
                print(json.dumps(assessment, indent=2))
        else:
            print("No guardrail interventions detected.")

        # save bedrock converse_response and extract final message
        print(json.dumps(converse_response))
        llm_message = converse_response["output"]["message"]["content"][0]["text"]
        print(llm_message)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
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