部署到 aws 注意事项：

    1.创建一个 S3 bucket
    2.权限允许所有访问
    3.properties 中 Static website hosting 点击编辑，设置index document 为 index.html
    4.permissions 中 Bucket policy 添加：
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::tan-source-code/*"
                }
            ]
        }
    5. 本地文件 package.json 中 homepage设置为 bucket 的 Static website hosting 地址
    6. 控制台 npm run build
    7. 把生成的 dist 文件夹中的所有文件拖到创建的 bucket 中

用 docker 打包依赖：docker run --rm -v ${PWD}:/var/task lambci/lambda:build-python3.8 pip install -r requirements.txt -t /var/task
必须用 docker打包，否则会找不到依赖。

lambda 注意修改内存容量和 timeout，否则会显示程序被 kill 异常。


