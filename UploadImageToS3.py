import json
import base64
import boto3

s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    try:
        # 从事件中获取并解析主体
        body = json.loads(event['body'])
        
        # 从解析后的主体中获取图像数据和文件名
        image_data = body['image_data']
        file_name = body['file_name']
        user_email = body['user_email']
        
        # 解码Base64图像数据
        image = base64.b64decode(image_data)
        
        # 硬编码S3桶名称
        bucket_name = 'tan-image-bucket'
        
        # 上传图像到S3
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=image)
        
        # 准备传递给 ObjectDetectionFunction 的参数
        payload = {
            'image_data': image_data,
            'file_name': file_name,
            'user_email': user_email
        }
        
        # 调用 ObjectDetectionFunction
        response = lambda_client.invoke(
            FunctionName='ObjectDetectionFunction',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read())
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Image uploaded successfully!',
                'object_detection_result': response_payload
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(f'Error uploading image: {str(e)}')
        }


