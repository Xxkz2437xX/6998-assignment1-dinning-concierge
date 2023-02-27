import json
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import random
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.vendored import requests
from botocore.exceptions import ClientError

REGION = 'us-east-1'
HOST = 'search-restaurants-3wzu7y54f46vgomhfx7tir5onu.us-east-1.es.amazonaws.com'
INDEX = 'restaurants'

def query(term):
    print(term)
    q = {'size': 20, 'query': {'multi_match': {'query': term}}}
    client = OpenSearch(hosts=[{
        'host': HOST,
        'port': 443
    }],
                        http_auth=get_awsauth(REGION, 'es'),
                        use_ssl=True,
                        verify_certs=True,
                        connection_class=RequestsHttpConnection)
    res = client.search(index=INDEX, body=q)
    hits = res['hits']['hits']
    result = []
    while len(result) !=3:
        index = random.randint(0,19)
        RestaurantID = hits[index]['_source']['RestaurantID']
        if RestaurantID not in result:
            result.append(RestaurantID)
    return result


def send_email(recipient, body_text):
    ses_client = boto3.client('ses',region_name='us-east-1')
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': "restaurant suggestions",
                },
            },
            Source="kz2437@columbia.edu",
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    
    
    
def get_awsauth(region, service):
    cred = boto3.Session().get_credentials()
    return AWS4Auth(cred.access_key,
                    cred.secret_key,
                    region,
                    service,
                    session_token=cred.token)

  
def lambda_handler(event, context):
    print('Received event: ' + json.dumps(event))
    sqs_client = boto3.client('sqs',region_name='us-east-1' )
    sqs_response = sqs_client.receive_message(
        QueueUrl="https://sqs.us-east-1.amazonaws.com/260389976155/DiningConcierge",
        AttributeNames=['SentTimestamp'],
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All'],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    print(sqs_response)
    
    if sqs_response: # when response_from_sqs is not empty
        Location = sqs_response['Messages'][0]["MessageAttributes"]['Location']["StringValue"]
        Cuisine = sqs_response['Messages'][0]["MessageAttributes"]['Cuisine']["StringValue"]
        Date = sqs_response['Messages'][0]["MessageAttributes"]['Date']["StringValue"]
        Time = sqs_response['Messages'][0]["MessageAttributes"]['Time']["StringValue"]
        People = sqs_response['Messages'][0]["MessageAttributes"]['People']["StringValue"]
        Email = sqs_response['Messages'][0]["MessageAttributes"]['Email']["StringValue"]
       
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('yelp')
        recommendation = []
        for Business_ID in query(Cuisine):
            dynamodb_response = table.query(KeyConditionExpression=Key('Business_ID').eq(Business_ID))
            recommendation.append({
                "name": dynamodb_response['Items'][0]["Name"],
                "address": dynamodb_response['Items'][0]["Address"]
            })
        
        # send message from ses
        text_message = "Hello! Here are my " + Cuisine + " restaurant suggestions for "+ People +" people, for "+Date+" at "+Time+" : 1. "+recommendation[0]["name"]+" located at "+ recommendation[0]["address"]+", 2. "+recommendation[1]["name"]+" located at "+ recommendation[1]["address"]+", 3. "+recommendation[2]["name"]+" located at "+ recommendation[2]["address"]+". Enjoy your meal!"                               
        send_email(Email, text_message)
        sqs_client.delete_message(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/260389976155/DiningConcierge",
            ReceiptHandle=sqs_response['Messages'][0]['ReceiptHandle']
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
            },
            'body': json.dumps({'results': text_message})
        }
        
        
    else: # when response_from_sqs is empty
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': '*',
            },
            'body': json.dumps("SQS queue is now empty")
        }
