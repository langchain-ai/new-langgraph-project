#!/usr/bin/env python
"""测试优化的文档分类性能"""

import asyncio
import time
import os
import sys

sys.path.insert(0, '.')
from agents.document_classifier.graph import graph as classifier_graph

async def test_classification_performance(s3_key: str, bucket: str = 'medical-claims-documents'):
    """测试文档分类性能"""
    
    # 配置环境
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    
    context = {
        "s3_bucket": bucket,
        "aws_region": "us-east-1",
        "confidence_threshold": 0.7
    }
    
    state = {
        "s3_key": s3_key
    }
    
    print(f"\n{'='*60}")
    print(f"📄 测试文档: {s3_key}")
    print(f"{'='*60}")
    
    # 测量分类时间
    start_time = time.time()
    
    result = await classifier_graph.ainvoke(state, context=context)
    
    elapsed_time = time.time() - start_time
    
    # 显示结果
    print(f"\n⏱️  分类耗时: {elapsed_time:.2f} 秒")
    print(f"📊 读取字节: {result.get('bytes_read', 0):,} bytes")
    print(f"📁 文件大小: {result.get('file_size', 0):,} bytes")
    
    # 计算节省的带宽
    if result.get('file_size', 0) > 0:
        bytes_saved = result['file_size'] - result.get('bytes_read', result['file_size'])
        percentage_saved = (bytes_saved / result['file_size']) * 100
        print(f"💾 节省带宽: {bytes_saved:,} bytes ({percentage_saved:.1f}%)")
    
    print(f"\n🔍 分类结果:")
    print(f"  • 文档类型: {result.get('document_type', 'unknown')}")
    print(f"  • 置信度: {result.get('confidence', 0):.2%}")
    print(f"  • 早期检测: {'✅ 是' if result.get('early_detection', False) else '❌ 否'}")
    print(f"  • 原因: {result.get('classification_reason', '')}")
    
    if result.get('indicators_found'):
        print(f"\n📌 发现的指标:")
        for i, indicator in enumerate(result['indicators_found'][:5], 1):
            print(f"  {i}. {indicator}")
    
    return result

async def compare_documents():
    """比较不同文档的分类性能"""
    
    test_documents = [
        "documents/cms1500_filled_dummy.pdf",  # 小文件，强信号
        "documents/multiline_provider_id.pdf",  # 大文件，FORM 1500格式
    ]
    
    print("\n" + "="*60)
    print("🚀 文档分类性能对比测试")
    print("="*60)
    
    total_bytes_read = 0
    total_bytes_size = 0
    total_time = 0
    
    for doc_key in test_documents:
        result = await test_classification_performance(doc_key)
        
        total_bytes_read += result.get('bytes_read', 0)
        total_bytes_size += result.get('file_size', 0)
        
        # 等待一下再测试下一个
        await asyncio.sleep(1)
    
    # 总结
    print("\n" + "="*60)
    print("📈 性能总结")
    print("="*60)
    
    if total_bytes_size > 0:
        total_saved = total_bytes_size - total_bytes_read
        total_percentage = (total_saved / total_bytes_size) * 100
        
        print(f"📊 总文件大小: {total_bytes_size:,} bytes")
        print(f"📖 实际读取: {total_bytes_read:,} bytes")
        print(f"💾 节省带宽: {total_saved:,} bytes ({total_percentage:.1f}%)")
        
        print(f"\n✨ 优化效果:")
        print(f"  • 平均只需读取文件的 {100 - total_percentage:.1f}% 即可完成分类")
        print(f"  • 使用渐进式字节范围读取和早期检测")
        print(f"  • 支持 FORM 1500 等多种CMS-1500变体")

if __name__ == "__main__":
    print("🔧 S3字节范围流式读取优化测试")
    print("  - 64KB → 128KB → 256KB → 512KB 渐进式读取")
    print("  - 发现3个强信号即早期退出")
    print("  - 减少带宽使用和延迟")
    
    asyncio.run(compare_documents())