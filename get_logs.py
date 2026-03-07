import boto3
import json

client = boto3.client('lambda', region_name='ap-south-1')
# wait we don't have credentials
