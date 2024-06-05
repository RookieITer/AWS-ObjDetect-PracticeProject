import boto3
import os
import sys
import uuid
from urllib.parse import unquote_plus
from PIL import Image
import PIL.Image

s3_client = boto3.client('s3')



def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        # 计算新的尺寸，使得最长边为150px
        ratio = max(image.size) / 150
        new_size = (int(image.size[0] / ratio), int(image.size[1] / ratio))
        # 重设图像尺寸
        image = image.resize(new_size, Image.Resampling.LANCZOS)  # 使用Image.Resampling.LANCZOS代替Image.ANTIALIAS
        image.save(resized_path)

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = unquote_plus(record['s3']['object']['key'])
        tmpkey = key.replace('/', '')
        download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)
        upload_path = '/tmp/resized-{}'.format(tmpkey)
        s3_client.download_file(bucket, key, download_path)
        resize_image(download_path, upload_path)
        s3_client.upload_file(upload_path, '{}-resized'.format(bucket), 'resized-{}'.format(key))

# import boto3
# import os
# import sys
# import uuid
# from urllib.parse import unquote_plus
# from PIL import Image
# import PIL.Image
            
# s3_client = boto3.client('s3')
            
# def resize_image(image_path, resized_path):
#   with Image.open(image_path) as image:
#     image.thumbnail(tuple(x / 3 for x in image.size))
#     image.save(resized_path)
            
# def lambda_handler(event, context):
#   for record in event['Records']:  # 遍历每个记录
#     # 例如：事件包含两个记录，第一个记录是bucket: 'example-bucket' 和 key: 'images/pic1.jpg'
#     bucket = record['s3']['bucket']['name']  # 获取存储桶名称
#     # 例如：'example-bucket'
#     key = unquote_plus(record['s3']['object']['key'])  # 获取对象键并解码
#     # 例如：'images/pic1.jpg'
#     tmpkey = key.replace('/', '')  # 去掉键中的斜杠
#     # 例如：'imagespic1.jpg'
#     download_path = '/tmp/{}{}'.format(uuid.uuid4(), tmpkey)  # 生成下载路径
#     # 例如：'/tmp/123e4567-e89b-12d3-a456-426614174000imagespic1.jpg'
#     upload_path = '/tmp/resized-{}'.format(tmpkey)  # 生成上传路径
#     # 例如：'/tmp/resized-imagespic1.jpg'
#     s3_client.download_file(bucket, key, download_path)  # 从S3下载文件到下载路径
#     # 例如：从 'example-bucket' 下载 'images/pic1.jpg' 到 '/tmp/123e4567-e89b-12d3-a456-426614174000imagespic1.jpg'
#     resize_image(download_path, upload_path)  # 调整图像大小
#     # 例如：调整 '/tmp/123e4567-e89b-12d3-a456-426614174000imagespic1.jpg' 的大小并保存到 '/tmp/resized-imagespic1.jpg'
#     s3_client.upload_file(upload_path, '{}-resized'.format(bucket), 'resized-{}'.format(key))  # 上传调整后的图像到S3
#     # 例如：将 '/tmp/resized-imagespic1.jpg' 上传到 'example-bucket-resized' 并命名为 'resized-images/pic1.jpg'