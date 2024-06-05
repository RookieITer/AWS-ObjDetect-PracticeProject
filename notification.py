import json
import boto3
from botocore.exceptions import ClientError

# Initialize boto3 clients
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
image_table = dynamodb.Table('image-metadata')
user_table = dynamodb.Table('user-notification')


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))  # Log the received event

    # Iterate through records in the DynamoDB stream event
    for record in event['Records']:
        print("Processing record:", json.dumps(record))  # Log each record

        # Check if the record is an insert or modify event
        if record['eventName'] in ['INSERT', 'MODIFY']:
            new_image = record['dynamodb']['NewImage']
            tags = [tag['S'] for tag in new_image.get('Tags', {}).get('L', [])]
            email = new_image.get('Email', {}).get('S', '')

            # Get the user's notification preferences
            response = user_table.get_item(Key={'email': email})
            if 'Item' in response:
                user_preferences = response['Item']['tags']
                user_topic_arn = response['Item']['topic_arn']

                # Check if any of the image tags match the user's preferences
                if any(tag in user_preferences for tag in tags):
                    print(f"User {email} has matching tags {tags}")
                    send_sns_notification(user_topic_arn, tags)

    return {
        'statusCode': 200,
        'body': json.dumps('Notifications processed successfully!')
    }


def send_sns_notification(topic_arn, tags):
    message = f"New image uploaded with tags: {', '.join(tags)}"
    subject = "New Image with Your Preferred Tags"

    try:
        response = sns.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject,
        )
        print(f"SNS message sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        print(f"Error sending SNS message: {e.response['Error']['Message']}")