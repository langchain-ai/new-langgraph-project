#!/usr/bin/env python3
"""测试图像预处理功能。"""

import asyncio
import os
import logging
import boto3
from common.image_preprocessing import PDFImagePreprocessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置LocalStack环境
os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


def test_preprocessing():
    """测试PDF预处理功能。"""
    
    print("\n" + "="*60)
    print("测试图像预处理功能")
    print("="*60 + "\n")
    
    # 初始化S3客户端
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    # 测试文件
    test_files = [
        ("medical-documents", "2_page_with_back.pdf"),
        ("medical-documents", "misaligned.pdf")
    ]
    
    for bucket, key in test_files:
        print(f"\n📄 测试文件: s3://{bucket}/{key}")
        print("-" * 40)
        
        try:
            # 从S3下载PDF
            response = s3.get_object(Bucket=bucket, Key=key)
            pdf_bytes = response['Body'].read()
            print(f"✅ 下载成功: {len(pdf_bytes)/1024:.1f}KB")
            
            # 测试不同配置
            configs = [
                {"dpi": 300, "remove_red": True, "auto_rotate": True},
                {"dpi": 200, "remove_red": False, "auto_rotate": True},
            ]
            
            for i, config in enumerate(configs):
                print(f"\n配置 {i+1}: DPI={config['dpi']}, 去红={config['remove_red']}, 自动旋转={config['auto_rotate']}")
                
                # 创建预处理器
                preprocessor = PDFImagePreprocessor(**config)
                
                try:
                    # 预处理PDF
                    result = preprocessor.preprocess_pdf_bytes(pdf_bytes)
                    
                    print(f"✅ 预处理成功:")
                    print(f"   - 处理了 {len(result)} 页")
                    
                    for page_num, (image_array, png_bytes) in enumerate(result):
                        print(f"   - 第{page_num+1}页: 图像尺寸={image_array.shape}, PNG大小={len(png_bytes)/1024:.1f}KB")
                    
                except Exception as e:
                    print(f"❌ 预处理失败: {e}")
                    
        except Exception as e:
            print(f"❌ 无法加载文件: {e}")


async def test_with_hcfa_reader():
    """测试集成到HCFA Reader的预处理。"""
    from agents.hcfa_reader import graph
    
    print("\n" + "="*60)
    print("测试HCFA Reader集成预处理")
    print("="*60 + "\n")
    
    # 配置上下文
    context = {
        "s3_bucket": "medical-documents",
        "aws_region": "us-east-1",
        "enable_validation": True,
        "max_pages": 3,
        "enable_preprocessing": True,  # 启用预处理
        "preprocessing_dpi": 300
    }
    
    # 测试文件
    test_files = ["2_page_with_back.pdf", "misaligned.pdf"]
    
    for s3_key in test_files:
        print(f"\n📄 测试: {s3_key}")
        print("-" * 40)
        
        # 初始状态
        initial_state = {
            "s3_key": s3_key,
            "s3_bucket": "medical-documents"
        }
        
        try:
            # 执行图
            result = await graph.ainvoke(
                initial_state,
                config={"configurable": context}
            )
            
            print("✅ 处理完成")
            print(f"   文档类型: {result.get('document_type', 'unknown')}")
            print(f"   是否CMS-1500: {result.get('is_cms1500', False)}")
            print(f"   置信度: {result.get('confidence', 0):.2f}")
            print(f"   使用预处理: {result.get('use_preprocessed', False)}")
            print(f"   页数: {result.get('page_count', 0)}")
            
            if result.get('is_cms1500'):
                patient = result.get('patient_info', {})
                if patient.get('name'):
                    print(f"   患者姓名: {patient.get('name')}")
                
                indicators = result.get('indicators_found', [])
                if indicators:
                    print(f"   找到指标: {', '.join(indicators[:3])}")
            
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()


def main():
    """运行所有测试。"""
    
    print("\n" + "🚀 " * 20)
    print("图像预处理测试套件")
    print("🚀 " * 20)
    
    # 检查LocalStack
    print("\n🔍 检查LocalStack服务...")
    
    try:
        s3 = boto3.client(
            's3',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        buckets = s3.list_buckets()
        print(f"✅ S3可用。存储桶: {[b['Name'] for b in buckets['Buckets']]}")
        
    except Exception as e:
        print(f"❌ LocalStack问题: {e}")
        print("请确保Docker服务正在运行:")
        print("docker-compose up -d")
        return
    
    # 运行测试
    test_preprocessing()
    asyncio.run(test_with_hcfa_reader())
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    main()