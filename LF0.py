import boto3
import json


client = boto3.client('lexv2-runtime')
def lambda_handler(event, context):
    print(event)
    msg_from_user = event["messages"][0]
    print(f"Message from frontend: {msg_from_user}")
    botMessage = "Please try again."
    if msg_from_user is None or len(msg_from_user) < 1:
        return {
            'statusCode': 200,
            'body': json.dumps(botMessage)
        }
    response = client.recognize_text(
            botId='J8JGB8VBHK', 
            botAliasId='TSTALIASID',
            localeId='en_US',
            sessionId='testuser',
            text=msg_from_user["unstructured"]["text"])
    
    msg_from_lex = response.get('messages', [])
    if msg_from_lex:
        print(f"Message from Chatbot: {msg_from_lex[0]['content']}")
        print(response)
        resp = {
            'statusCode': 200,
            'messages': [{"type": "unstructured", 
            "unstructured": {
                "text": json.dumps(msg_from_lex[0]['content'])
            }}]
        }
        return resp
        