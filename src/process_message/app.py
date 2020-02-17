"""
Basic example of SMS and MMS response with Twilio.
Demostrates webhook validation, matching against a master number, and the
use of the Twilio Python helper library.
"""

from __future__ import print_function

import os
import json
import urllib
from twilio.rest import Client
from twilio.request_validator import RequestValidator
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMO_TABLE_NAME'])

client = Client(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])
account_phone = str(os.environ['TWILIO_PHONE_NUMBER'])

def build_params(body):
    params = {}
    for item in body.split("&"):
        kv = item.split("=", 1)
        params[kv[0]] = kv[1]
    return params

# def request_is_valid(event):
#     print("Validating request...")
#     if u'twilioSignature' in event and u'Body' in event \
#             and event['Body'].lower() == "secret":

#         print("Initial validation")

#         form_parameters = {
#             k: urllib.unquote_plus(v) for k, v in event.items()
#             if k != u'twilioSignature'
#         }

#         validator = RequestValidator(os.environ['TWILIO_AUTH_TOKEN'])
#         request_valid = validator.validate(
#             os.environ['REQUEST_URL'],
#             form_parameters,
#             event[u'twilioSignature']
#         )

#         print(f"Request valid? {request_valid}")
#         return request_valid
#     else: 
#         print("Invalid request....")
#         return False

def request_is_valid(event):
    return True

def process_vote():
    pass

def has_voted(phone):
    response = table.query(
        KeyConditionExpression=Key('pk').eq(f"{phone}") & Key('sk').eq('vote')
    )
    return len(response['Items']) > 0
    

def send_message(body, recipient):
    message = client.messages \
                    .create(
                        body=body,
                        from_=account_phone,
                        to=recipient
                     )

def lambda_handler(event, context):
    print(event)
    
    # print("Form params:",form_parameters,"validity:",request_valid)
    # If the request is valid and this is from the master number,
    # give the secret!
    if request_is_valid(event):

        # Parse incoming message
        params = build_params(event['body'])
        phone_from = params['From'].replace('%2B', '+')
        phone_to = params['To'].replace('%2B', '+')
        body = params['Body']
        msg_sid = params['MessageSid']

        # If downcase message equals "vote", then return the vote question. 
        if body.lower() == "vote":
            # Check if user has voted. If not, send the prompt to vote. 
            if has_voted(phone_from):
                send_message("Hey, you've already voted! Quit trying to rig this election.", phone_from)
            else:
                send_message("Thank you for voting! Who are you voting for in the primary?\n1. Bernie Sanders\n2. Pete Buttigieg\n3. Elizabeth Warren\n4. None\n\n(Reply with 1, 2, 3, or 4)", phone_from)
        
        # If message equals 1, 2, 3, or 4, then check for a vote. 
        elif body in ["1", "2", "3", "4"]:
            if has_voted(phone_from):
                # If a user has voted, return an error message.
                send_message("Hey, you've already voted! Quit trying to rig this election.", phone_from)
            else:
                # Save the vote. Count updated in dynamo stream. 
                table.put_item(
                    Item={
                        'pk': f"{phone_from}",
                        'sk': f"vote",
                        'vote': int(body)
                    }
                )

                response = table.query(
                    KeyConditionExpression=Key('pk').eq(f"vote") & Key('sk').eq('results')
                )

                results = response['Items'][0]
                #If a user has not voted, then add the vote & add the thank you message. 
                send_message(f"Thank you for your vote! Here are the current results...\nBernie: {str(results.get('1', '0'))}\nPete: {str(results.get('2', '0'))}\nElizabeth: {str(results.get('3', '0'))}\nNone: {str(results.get('4', '0'))}\n\n\
                    If you want to build cool things with SMS, send us an email at hello@broadwaylab.com.", phone_from)
        else:
            # We received a different message.
            # If user voted, prompt them to text "vote". 
            # else, send them a fun message. 
            if has_voted(phone_from):
                send_message("Thanks for voting. If you want to build cool things with SMS, send us an email at hello@broadwaylab.com.", phone_from)
            else:
                send_message("Hey, we noticed you haven't voted. Text 'vote' to this number", phone_from)

        # Exit function
        return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'\
           '<Response><Message>Message sent</Message></Response>'

    else:
        return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>'\
           '<Response><Message>Invalid webhook</Message></Response>'
