import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMO_TABLE_NAME'])

def safeget(dct, *keys):
    try:
        for key in keys:
            try:
                dct = dct[key]
            except KeyError:
                return ""
        return dct
    except: 
        return ""

def lambda_handler(event, context):
	print(event)
	records = event['Records']
	for record in records: 
		print(record)

		if record['eventName'] == "INSERT" and safeget(record, 'dynamodb', 'Keys', 'sk', 'S') == "vote":
			vote = int(safeget(record, 'dynamodb', 'NewImage', 'vote', 'N'))
			print(f"Registered vote: {str(vote)}")

			# Get the current vote count. 
			response = table.query(
			    KeyConditionExpression=Key('pk').eq(f"vote") & Key('sk').eq('results')
			)

			if len(response['Items']) == 0:
				# Seed the database with our results key. 
				table.put_item(Item={'pk': 'vote', 'sk': 'results', f"{str(vote)}": 1})
			else: 
				results = response['Items'][0]
				count = int(results.get(f"{str(vote)}", 0))
				update = table.update_item(
				    Key={
				        'pk': "vote",
				        'sk': "results"
				    },
				    UpdateExpression=f"set #vote = :vote",
				    ExpressionAttributeValues={
				        ":vote": (count + 1) # Increment the vote
				    },
				    ExpressionAttributeNames={"#vote": f"{str(vote)}"},
				    ReturnValues="UPDATED_NEW"
				)
				print(update)

	return event