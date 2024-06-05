import boto3
import cv2
import numpy as np
import os
import traceback
import json
import base64
import logging
import urllib.parse
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# 设置阈值
confthres = 0.3
nmsthres = 0.1

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('image-metadata')
s3 = boto3.client('s3')


def do_prediction(image, net, LABELS):
    (H, W) = image.shape[:2]
    ln = net.getLayerNames()
    ln = [ln[i - 1] for i in net.getUnconnectedOutLayers()]

    blob = cv2.dnn.blobFromImage(image, 1 / 255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layerOutputs = net.forward(ln)

    boxes = []
    confidences = []
    classIDs = []

    for output in layerOutputs:
        for detection in output:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]

            if confidence > confthres:
                box = detection[0:4] * np.array([W, H, W, H])
                (centerX, centerY, width, height) = box.astype("int")

                x = int(centerX - (width / 2))
                y = int(centerY - (height / 2))

                boxes.append([x, y, int(width), int(height)])
                confidences.append(float(confidence))
                classIDs.append(classID)

    idxs = cv2.dnn.NMSBoxes(boxes, confidences, confthres, nmsthres)

    objects_detected = []
    if len(idxs) > 0:
        for i in idxs.flatten():
            label = LABELS[classIDs[i]]
            objects_detected.append(label)

    return objects_detected
    # objects_detected = []

    # if len(idxs) > 0:
    #     for i in idxs.flatten():
    #         obj = {
    #             "label": LABELS[classIDs[i]],
    #             # "accuracy": confidences[i],
    #             "accuracy": Decimal(str(confidences[i])),
    #             "rectangle": {
    #                 "left": boxes[i][0],
    #                 "top": boxes[i][1],
    #                 "width": boxes[i][2],
    #                 "height": boxes[i][3]
    #             }
    #         }
    #         objects_detected.append(obj)

    # return objects_detected


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError


def lambda_handler(event, context):
    try:
        # 解析传入的Payload
        # 如果从另一个Lambda函数调用，event将直接等于传入的Payload
        # 如果从API Gateway调用，event将是一个包含主体的字典
        send_by_lambda = False
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            send_by_lambda = True
            body = event

        image_data = body['image_data']
        file_name = body['file_name']
        user_email = body['user_email']

        # 从文件名中提取email

        print(f'Email: {user_email}')
        print(f'File Name: {file_name}')
        print(f'Image Data: {image_data}')
        # 硬编码S3桶名称
        bucket_name_original = 'tan-image-bucket'
        bucket_name_thumbnail = 'tan-image-bucket-resized'
        # 生成文件的S3 URL
        s3_url_original = f'https://{bucket_name_original}.s3.amazonaws.com/{file_name}'
        s3_url_thumbnail = f'https://{bucket_name_thumbnail}.s3.amazonaws.com/resized-{file_name}'

        print(f'S3 URL Original: {s3_url_original}')
        print(f'S3 URL Thumbnail: {s3_url_thumbnail}')

        # 保存图像到临时文件
        download_path = f'/tmp/{file_name}'
        with open(download_path, 'wb') as f:
            f.write(base64.b64decode(image_data))

        # # YOLO相关路径
        # yolo_path = "/var/task/yolo_tiny_configs"
        # labelsPath = "coco.names"
        # cfgpath = "yolov3-tiny.cfg"
        # wpath = "yolov3-tiny.weights"

        # 获取当前文件的目录
        current_dir = os.path.dirname(__file__)

        # 配置文件路径
        labelsPath = os.path.join(current_dir, 'yolo_tiny_configs', 'coco.names')
        CFG = os.path.join(current_dir, 'yolo_tiny_configs', 'yolov3-tiny.cfg')
        Weights = os.path.join(current_dir, 'yolo_tiny_configs', 'yolov3-tiny.weights')

        # # 读取标签
        LABELS = open(labelsPath).read().strip().split("\n")
        # # 加载配置和权重文件
        # CFG = os.path.sep.join([yolo_path, cfgpath])
        # Weights = os.path.sep.join([yolo_path, wpath])
        print(f'Labels: {LABELS}')
        print(f'CFG: {CFG}')

        # 加载模型
        net = cv2.dnn.readNetFromDarknet(CFG, Weights)

        # 读取图像
        image = cv2.imread(download_path)

        # 进行对象检测
        print(4444444444)
        result = do_prediction(image, net, LABELS)
        print(5555555555)
        print(f'Object detection result: {result}')
        # 准备DynamoDB条目
        print(6666666666)
        item = {
            'id': file_name,
            'S3URL_Original': s3_url_original,
            'S3URL_Thumbnail': s3_url_thumbnail,
            'Email': user_email,
            'Tags': result
        }
        print(7777777777)
        print(f'Item: {item}')
        print(8888888888)
        # 存储到DynamoDB
        if send_by_lambda:
            table.put_item(Item=item)

        # return {
        #     'statusCode': 200,
        #     'body': json.dumps({'message':'Object detection completed successfully',
        #                        'object_detection_result': item}, default=decimal_default)

        # }
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'message': 'Object detection completed successfully',
                'object_detection_result': item
            }, default=decimal_default)
        }


    except Exception as e:
        print(f'Error in object detection: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error---': 'Error in object detection---',
                'details---': str(e)
            })
        }