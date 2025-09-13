#!/usr/bin/env python3
"""
测试 PDF 预处理 handler 的功能
使用 LocalStack S3 中的文件进行测试
"""

import sys
import os
import boto3
import io
import json
from pathlib import Path

# 添加 tests 目录到路径
sys.path.insert(0, '/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/tests')

# 导入 handler 模块
import handler

# 配置 S3 客户端（LocalStack）
s3_client = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

# 覆盖 handler 中的 s3 客户端
handler.s3 = s3_client

def test_single_pdf(pdf_key, output_prefix):
    """测试单个 PDF 文件的处理"""
    
    bucket_name = 'medical-documents'
    output_bucket = 'medical-documents'
    
    print(f"\n{'='*60}")
    print(f"测试文件: {pdf_key}")
    print(f"{'='*60}")
    
    try:
        # 1. 从 S3 获取 PDF 文件
        print(f"1. 从 S3 下载: s3://{bucket_name}/{pdf_key}")
        response = s3_client.get_object(Bucket=bucket_name, Key=pdf_key)
        pdf_bytes = response['Body'].read()
        file_size = len(pdf_bytes)
        print(f"   文件大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # 分析 PDF 详情
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"   PDF 页数: {doc.page_count}")
        if doc.page_count > 0:
            page = doc[0]
            rect = page.rect
            print(f"   第一页尺寸: {rect.width:.0f} x {rect.height:.0f} pt")
        doc.close()
        
        # 2. 处理 PDF - 处理所有页面
        print(f"\n2. 开始处理 PDF...")
        print(f"   输出位置: s3://{output_bucket}/{output_prefix}/")
        
        import time
        start_time = time.time()
        
        # 调用处理函数，处理所有页面
        handler.process_pdf_bytes_to_s3(
            pdf_bytes=pdf_bytes,
            out_bucket=output_bucket,
            out_prefix=output_prefix,
            dpi=300,
            page_from=1,
            page_to=None  # 处理所有页面
        )
        
        end_time = time.time()
        process_time = end_time - start_time
        
        print(f"   ✓ 处理完成")
        print(f"   ⏱️  处理耗时: {process_time:.2f} 秒")
        
        # 3. 验证输出文件
        print(f"\n3. 验证输出文件...")
        response = s3_client.list_objects_v2(
            Bucket=output_bucket,
            Prefix=output_prefix
        )
        
        if 'Contents' in response:
            output_files = response['Contents']
            print(f"   生成了 {len(output_files)} 个文件:")
            for obj in output_files:
                key = obj['Key']
                size = obj['Size']
                print(f"   - {key} ({size:,} bytes)")
                
                # 生成访问 URL
                url = f"http://localhost:4566/{output_bucket}/{key}"
                print(f"     URL: {url}")
        else:
            print("   ✗ 没有找到输出文件")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_lambda_handler():
    """测试 Lambda handler 函数"""
    print(f"\n{'='*60}")
    print("测试 Lambda Handler")
    print(f"{'='*60}")
    
    # 设置环境变量
    os.environ['OUTPUT_BUCKET'] = 'medical-documents'
    os.environ['OUTPUT_PREFIX_BASE'] = 'lambda-processed/'
    os.environ['DPI'] = '300'
    
    # 模拟 S3 PUT 事件
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "medical-documents"
                    },
                    "object": {
                        "key": "black_and_white.pdf"
                    }
                }
            }
        ]
    }
    
    print("\n模拟 Lambda 事件:")
    print(json.dumps(event, indent=2))
    
    try:
        result = handler.lambda_handler(event, {})
        print(f"\nLambda 执行结果: {result}")
        return result.get('ok', False)
    except Exception as e:
        print(f"\n❌ Lambda 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("="*70)
    print("📋 black_and_white.pdf 处理测试")
    print("="*70)
    
    # 专门测试 misaligned.pdf
    from datetime import datetime
    timestamp = datetime.now().strftime("%H%M%S")
    
    # 清理之前的测试文件
    print("\n清理旧的测试文件...")
    try:
        response = s3_client.list_objects_v2(
            Bucket='medical-documents',
            Prefix='test_misaligned_'
        )
        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(Bucket='medical-documents', Key=obj['Key'])
            print(f"   删除了 {len(response['Contents'])} 个旧文件")
    except:
        pass
    
    # 测试 black_and_white.pdf
    test_files = [
        ("black_and_white.pdf", f"test_bw_{timestamp}"),  # 黑白文档
    ]
    
    # 测试单个文件处理
    success_count = 0
    for pdf_key, output_prefix in test_files:
        if test_single_pdf(pdf_key, output_prefix):
            success_count += 1
    
    print(f"\n{'='*70}")
    print(f"📊 测试完成: {success_count}/{len(test_files)} 成功")
    
    # 测试 Lambda handler
    print("\n" + "="*70)
    if test_lambda_handler():
        print("✓ Lambda handler 测试成功")
    else:
        print("✗ Lambda handler 测试失败")
    
    print(f"\n{'='*70}")
    print("测试完成！")
    print("处理后的图像已保存到 S3")
    print("可以通过 URL 访问查看处理效果")

if __name__ == "__main__":
    main()