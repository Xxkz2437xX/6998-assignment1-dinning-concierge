import json
import time
import os
import logging
import boto3
import re
regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']

def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    if 'sessionAttributes' in sessionState:
        return sessionState['sessionAttributes']
    return {}

def get_slot(intent_request, slotName):
    slots = get_slots(intent_request)
    if slots is not None and slotName in slots and slots[slotName] is not None:
        logger.debug('resolvedValue={}'.format(slots[slotName]['value']['resolvedValues']))
        return slots[slotName]['value']['interpretedValue']
    else:
        return None

def elicit_slot(session_attributes, intent_request, slots, slot_to_elicit, slot_elicitation_style, message):
    return {'sessionState': {'dialogAction': {'type': 'ElicitSlot',
                                              'slotToElicit': slot_to_elicit,
                                              'slotElicitationStyle': slot_elicitation_style
                                              },
                             'intent': {'name': intent_request['sessionState']['intent']['name'],
                                        'slots': slots,
                                        'state': 'InProgress'
                                        },
                             'sessionAttributes': session_attributes,
                             'originatingRequestId': 'fa1cdd8d-56f3-4d96-a843-c5aef1215f79'
                             },
            'sessionId': intent_request['sessionId'],
            'messages': [ message ],
            'requestAttributes': intent_request['requestAttributes']
            if 'requestAttributes' in intent_request else None
            }

def build_validation_result(isvalid, violated_slot, slot_elicitation_style, message_content):
    return {'isValid': isvalid,
            'violatedSlot': violated_slot,
            'slotElicitationStyle': slot_elicitation_style,
            'message': {'contentType': 'PlainText', 
            'content': message_content}
            }

def GetItemInDatabase(postal_code):
    return None


def isvalid_location(location):
    print("Debug: location is:",location)
    locations = ['new york', 'manhattan']
    if not location:
        return build_validation_result(False,'Location','SpellByWord','Not valid input')
    if location.lower() not in locations:
        return build_validation_result(False, 'Location', 'SpellByWord', 'Please enter a location in New York')
    return {'isValid': True}


def isvalid_cuisine(cuisine):
    print("Debug: cuisine is:",cuisine)
    if not cuisine :
        return build_validation_result(False,
                                       'cuisine',
                                       'SpellByWord',
                                       '')
    cuisines = ['indian','japanese','european','chinese','mexican']
    if cuisine.lower() not in cuisines:
        return build_validation_result(False,
                                       'cuisine',
                                       'SpellByWord',
                                       'This cuisine is not available')
    print("Debug: cuisine is: ",cuisine, "+1111111")
    return {'isValid': True}


def isvalid_date(date):
    print("Debug: date is:",date)
    if not date:
        return build_validation_result(False,'date', 'SpellByWord','Please enter a valid Dining date')
    else:
        return {'isValid': True}
    

def isvalid_time(time):
    print("Debug: time is:",time)
    if not time:
        return build_validation_result(False,'time', 'SpellByWord','')
    if time:
        return {'isValid': True}
    
    return build_validation_result(False,'time', 'SpellByWord','Please enter a valid Dining Time')


def isvalid_people(num_people):
    print("Debug: num_people is:",num_people)
    if not num_people:
         return build_validation_result(False,'people', 'SpellByWord','')
    num_people = int(num_people)
    if num_people > 20 or num_people < 1:
        return build_validation_result(False,
                                  'people',
                                  'SpellByWord',
                                  'Range of 1 to 20 people allowed')
    return {'isValid': True}


def isvalid_email(email):
    print("Debug: email is:",email)
    if not email:
        return build_validation_result(False, 'email', 'SpellByWord', '')
    if not re.fullmatch(regex, email):
       return build_validation_result(False, 'email', 'SpellByWord', 'Email must contain @')
    return {'isValid': True}



def validate_reservation(intent_request):
    Date = get_slot(intent_request, 'Date')
    Time = get_slot(intent_request, 'Time')
    Email = get_slot(intent_request, 'Email')
    Cuisine = get_slot(intent_request, 'Cuisine')
    People = get_slot(intent_request, 'People')
    Location = get_slot(intent_request, 'Location')
    if isvalid_location(Location)['isValid']:
        return isvalid_location(Location)
    if isvalid_cuisine(Cuisine)['isValid']:
        return isvalid_cuisine(Cuisine)
    if isvalid_date(Date)["isValid"]:
        return isvalid_date(Date)
    if isvalid_time(Time)['isValid']:
        return isvalid_time(Time)
    if isvalid_people(People)['isValid']:
        return isvalid_people(People)
    if isvalid_email(Email)['isValid']:
        return isvalid_email(Email)
    return {'isValid': True}


def make_restaurant_reservation(intent_request):
    print("Debug: Entered make_restaurant_reservation" )
    slots = get_slots(intent_request)
    Date = get_slot(intent_request, 'Date')
    Time = get_slot(intent_request, 'Time')
    Email = get_slot(intent_request, 'Email')
    Cuisine = get_slot(intent_request, 'Cuisine')
    People = get_slot(intent_request, 'People')
    Location = get_slot(intent_request, 'Location')
    session_attributes = get_session_attributes(intent_request)

    if intent_request['invocationSource'] == 'DialogCodeHook':
        validation_result = validate_reservation(intent_request)
        print("Debug: Validation result is: ", validation_result)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(
                session_attributes,
                intent_request,
                slots,
                validation_result['violatedSlot'],
                validation_result['slotElicitationStyle'],
                validation_result['message']
            )
    print(slots)
    
    if not Location or not Date or not Time or not People or not Email or not Cuisine:
        return delegate(intent_request, slots)

    else:
        sqs_client = boto3.client('sqs')
        response = sqs_client.send_message(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/260389976155/DiningConcierge",
            MessageAttributes={
                    'Location': {
                        'DataType': 'String',
                        'StringValue': Location
                    },
                    'Cuisine': {
                        'DataType': 'String',
                        'StringValue': Cuisine
                    },
                    'People': {
                        'DataType': 'Number',
                        'StringValue': str(People)
                    },
                    'Date': {
                        'DataType': 'String',
                        'StringValue': Date
                    },
                    'Time': {
                        'DataType': 'String',
                        'StringValue': Time
                    },
                    'Email': {
                        'DataType': 'String',
                        'StringValue': Email
                    }
                },
            MessageBody=('Information about user inputs of Dining Chatbot.'),
            )
        
        print("response", response)
        
        return close(
            intent_request,
            session_attributes,
            'Fulfilled',
            {'contentType': 'PlainText',
             'content': 'You’re all set. Expect my suggestions shortly! Have a good day.'
             }
        )
        
def delegate(intent_request, slots):
    return {
    "sessionState": {
        "dialogAction": {
            "type": "Delegate"
        },
        "intent": {
            "name": intent_request['sessionState']['intent']['name'],
            "slots": slots,
            "state": "ReadyForFulfillment"
        },
        'sessionId': intent_request['sessionId'],
        "requestAttributes": intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }
}
    
def close(intent_request, session_attributes, fulfillment_state, message):
    intent_request['sessionState']['intent']['state'] = fulfillment_state
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': intent_request['sessionState']['intent'],
            'originatingRequestId': '2d3558dc-780b-422f-b9ec-7f6a1bd63f2e'
        },
        'messages': [ message ],
        'sessionId': intent_request['sessionId'],
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }


def dispatch(intent_request):
    intent_name = intent_request['sessionState']['intent']['name']
    response = None
    if intent_name == 'DiningSuggestionsIntent':
        response = make_restaurant_reservation(intent_request)
    return response



logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
def lambda_handler(event, context):
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event={}'.format(json.dumps(event)))
    response = dispatch(event)
    logger.debug("response={}".format(json.dumps(response)))
    return response