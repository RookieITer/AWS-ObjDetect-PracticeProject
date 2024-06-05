import json
import boto3
from botocore.exceptions import ClientError

# Initialize boto3 clients
sns = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('user-notification')


def lambda_handler(event, context):
    try:
        print("Received event: " + json.dumps(event))
        body = json.loads(event['body'])
        email = body['email']
        tags = body['tags'].split(',')

        # Create a unique SNS topic for the user if not already created
        response = table.get_item(Key={'email': email})
        print("DynamoDB get_item response:", response)

        if 'Item' in response:
            topic_arn = response['Item']['topic_arn']
        else:
            topic_name = email.replace('@', '_').replace('.', '_') + '_topic'
            topic_response = sns.create_topic(Name=topic_name)
            topic_arn = topic_response['TopicArn']

        # Check for existing subscriptions and delete them if necessary
        existing_subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        print("Existing subscriptions:", existing_subscriptions)

        for subscription in existing_subscriptions['Subscriptions']:
            if subscription['Endpoint'] == email and subscription['SubscriptionArn'] != 'Deleted':
                try:
                    sns.unsubscribe(SubscriptionArn=subscription['SubscriptionArn'])
                except ClientError as e:
                    print(f"Error unsubscribing: {e.response['Error']['Message']}")
                    return {
                        'statusCode': 500,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                            'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,DELETE'
                        },
                        'body': json.dumps(f"Error unsubscribing: {e.response['Error']['Message']}")
                    }

        # Subscribe the user's email to the SNS topic
        sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )

        # Update the user's subscription in DynamoDB
        table.update_item(
            Key={'email': email},
            UpdateExpression="set tags = :t, topic_arn = :a",
            ExpressionAttributeValues={':t': tags, ':a': topic_arn},
            ReturnValues="UPDATED_NEW"
        )

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,DELETE'
            },
            'body': json.dumps('Subscription processed successfully!')
        }
    except ClientError as e:
        print(f"ClientError: {e.response['Error']['Message']}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,DELETE'
            },
            'body': json.dumps(f"Error processing subscription: {e.response['Error']['Message']}")
        }
    except Exception as e:
        print(f"Exception: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,GET,POST,DELETE'
            },
            'body': json.dumps(f"Error processing subscription: {str(e)}")
        }