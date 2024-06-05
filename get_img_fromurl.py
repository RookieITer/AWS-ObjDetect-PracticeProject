import json
import boto3
from urllib.parse import urlparse
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('image-metadata')


def lambda_handler(event, context):
    status_code = 200
    body = {}
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,DELETE'
    }

    try:
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers
            }

        if event['httpMethod'] == 'POST':
            body = json.loads(event['body'].strip())
            if 'tags' in body:
                if 'type' in body:
                    status_code, body = handle_modify_tags(body)
                else:
                    status_code, body = handle_tags_query(body)
            elif 'url' in body and 'email' in body:
                status_code, body = handle_thumbnail_url_query(body)
        elif event['httpMethod'] == 'DELETE':
            status_code, body = handle_delete_images(json.loads(event['body'].strip()))
        else:
            raise ValueError(f"Unsupported method {event['httpMethod']}")
    except ClientError as e:
        status_code = 400
        body = e.response['Error']['Message']
    except Exception as e:
        status_code = 500
        body = str(e)

    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }


def handle_modify_tags(data):
    try:
        urls = data['url']
        tag_type = data['type']
        tags = data['tags']
        user_email = data['email']

        for url in urls:
            response = table.scan(
                FilterExpression=Attr('S3URL_Thumbnail').eq(url)
            )
            if response['Items']:
                item = response['Items'][0]
                image_email = item.get('Email')

                if image_email == user_email:
                    current_tags = item.get('Tags', [])

                    if tag_type == 1:
                        updated_tags = current_tags + tags
                    elif tag_type == 0:
                        updated_tags = current_tags
                        for tag in tags:
                            while tag in updated_tags:
                                updated_tags.remove(tag)

                    table.update_item(
                        Key={'id': item['id']},
                        UpdateExpression='SET Tags = :tags',
                        ExpressionAttributeValues={':tags': updated_tags}
                    )
                else:
                    return 403, create_response_body('Unauthorized: You cannot modify tags for images that do not belong to you.')

        return 200, create_response_body('Tags updated successfully!')

    except Exception as e:
        return 500, create_response_body(f'Error: {str(e)}')


def handle_tags_query(data):
    tags_query = data['tags']
    email = data['email']
    response = table.scan(FilterExpression=Attr('Email').eq(email))
    items = response['Items']

    thumbnail_url_list_unpresigned = []
    fullsize_url_list_unpresigned = []
    thumbnail_url_list = []
    fullsize_url_list = []
    print("tags_query.items+++++++++++++",tags_query.items())
    #  输出tags_query.items+++++++++++++ dict_items([('person', '1')])
    for item in items:
        tags = item.get('Tags', [])
        tags_count_map = {tag: tags.count(tag) for tag in set(tags)}
        print("tags_count_map--------------",tags_count_map)
        # 输出tags_count_map-------------- {'tennis racket': 1, 'person': 2}
        if all(int(tags_count_map.get(tag, 0)) >= int(count) for tag, count in tags_query.items()):
            thumbnail_url = item['S3URL_Thumbnail']
            fullsize_url = item['S3URL_Original']
            bucket_name1, object_key1 = extract_bucket_and_key_from_url(thumbnail_url)
            bucket_name2, object_key2 = extract_bucket_and_key_from_url(fullsize_url)
            thumbnail_url_presigned = generate_presigned_url(bucket_name1, object_key1)
            fullsize_url_presigned = generate_presigned_url(bucket_name2, object_key2)
            thumbnail_url_list.append(thumbnail_url_presigned)
            fullsize_url_list.append(fullsize_url_presigned)
            thumbnail_url_list_unpresigned.append(thumbnail_url)
            fullsize_url_list_unpresigned.append(fullsize_url)
            
    response_body = create_response_body('Success', {
        'thumbnail_urls': thumbnail_url_list,
        'fullsize_urls': fullsize_url_list,
        'thumbnail_urls_unpresigned': thumbnail_url_list_unpresigned,
        'fullsize_urls_unpresigned': fullsize_url_list_unpresigned
    })

    return 200, response_body


def handle_thumbnail_url_query(data):
    url = data['url']
    email = data['email']
    file_id = extract_id_from_url(url)
    bucket_name, object_key = extract_bucket_and_key_from_url(url)

    response = table.get_item(Key={'id': file_id})
    if 'Item' not in response:
        return 404, create_response_body('Image not found')

    item = response['Item']
    if item['Email'] != email:
        return 403, create_response_body('Unauthorized access')

    presigned_url = generate_presigned_url(bucket_name, object_key)
    return 200, create_response_body('Success', {'presigned_url': presigned_url})


def handle_delete_images(data):
    try:
        urls = data['url']
        user_email = data['email']

        for url in urls:
            response = table.scan(
                FilterExpression=Attr('S3URL_Thumbnail').eq(url)
            )

            if response['Items']:
                item = response['Items'][0]
                image_email = item.get('Email')

                if image_email == user_email:
                    s3.delete_object(Bucket='tan-image-bucket', Key=item['id'])
                    s3.delete_object(Bucket='tan-image-bucket-resized', Key='resized-' + item['id'])

                    table.delete_item(Key={'id': item['id']})
                else:
                    return 403, create_response_body('Unauthorized: You cannot delete images that do not belong to you.')

        return 200, create_response_body('Images deleted successfully!')

    except Exception as e:
        return 500, create_response_body(f'Error: {str(e)}')


def generate_presigned_url(bucket_name, object_key, expiration=3600):
    try:
        response = s3.generate_presigned_url('get_object',
                                             Params={'Bucket': bucket_name,
                                                     'Key': object_key},
                                             ExpiresIn=expiration)
    except Exception as e:
        print(f'Error generating pre-signed URL: {str(e)}')
        raise e
    return response


def extract_id_from_url(url):
    path = urlparse(url).path
    return path.split('/')[-1]


def extract_bucket_and_key_from_url(url):
    parsed_url = urlparse(url)
    bucket_name = parsed_url.netloc.split('.')[0]
    object_key = parsed_url.path.lstrip('/')
    return bucket_name, object_key


def create_response_body(message, additional_body=None):
    body = {'message': message}
    if additional_body:
        body.update(additional_body)
    return body