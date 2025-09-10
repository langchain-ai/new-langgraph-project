#!/usr/bin/env python
"""分析multiline_provider_id.pdf文档"""

import asyncio
import sys
import os
import json

sys.path.insert(0, '.')
from api.services.langgraph_processor import LangGraphProcessor

async def analyze_document():
    processor = LangGraphProcessor(s3_bucket='medical-claims-documents')
    result = await processor.process_document('documents/multiline_provider_id.pdf')
    return result

def format_output(result):
    """格式化输出结果"""
    print('\n' + '=' * 60)
    print('📄 文档识别结果 - multiline_provider_id.pdf')
    print('=' * 60)
    
    # 文档分类信息
    print(f"\n🔍 文档分类:")
    print(f"  文档类型: {result['classification']['document_type']}")
    print(f"  推荐处理器: {result['classification']['recommended_processor']}")
    print(f"  置信度: {result['classification']['confidence']:.2%}")
    print(f"  识别原因: {result['classification']['reason']}")
    
    # 发现的指标
    indicators = result['classification'].get('indicators_found', [])
    if indicators:
        print(f"\n📌 发现的关键指标 ({len(indicators)}个):")
        for i, indicator in enumerate(indicators[:10], 1):
            print(f"  {i}. {indicator}")
    
    # 文件信息
    print(f"\n📊 文件信息:")
    print(f"  文件大小: {result['file_info']['size']:,} bytes")
    print(f"  内容类型: {result['file_info']['content_type']}")
    
    # 提取的数据
    print(f"\n💊 提取的医疗数据:")
    data = result['extracted_data']
    
    if hasattr(data, '__dict__'):
        # 患者信息
        if data.patient_name:
            print(f"\n  患者信息:")
            print(f"    姓名: {data.patient_name}")
            print(f"    出生日期: {data.patient_dob}")
            print(f"    性别: {data.patient_sex if hasattr(data, 'patient_sex') else 'N/A'}")
            print(f"    地址: {data.patient_address if hasattr(data, 'patient_address') else 'N/A'}")
        
        # 保险信息
        if data.insurance_id:
            print(f"\n  保险信息:")
            print(f"    保险ID: {data.insurance_id}")
            print(f"    被保险人: {data.insured_name if hasattr(data, 'insured_name') else 'N/A'}")
        
        # 诊断和程序代码
        if data.diagnosis_codes:
            print(f"\n  诊断代码: {', '.join(data.diagnosis_codes)}")
        if data.procedure_codes:
            print(f"  程序代码: {', '.join(data.procedure_codes)}")
        
        # 财务信息
        if data.total_charge:
            print(f"\n  财务信息:")
            print(f"    总费用: ${data.total_charge:.2f}")
            amount_paid = getattr(data, 'amount_paid', 0)
            print(f"    已支付: ${amount_paid:.2f}")
            balance = getattr(data, 'balance_due', 0)
            print(f"    余额: ${balance:.2f}")
        
        # 提供者信息
        if hasattr(data, 'provider_name') and data.provider_name:
            print(f"\n  医疗提供者:")
            print(f"    名称: {data.provider_name}")
            print(f"    NPI: {data.provider_npi if hasattr(data, 'provider_npi') else 'N/A'}")
            print(f"    税号: {data.provider_tax_id if hasattr(data, 'provider_tax_id') else 'N/A'}")
    else:
        print(f"  {data}")
    
    # 验证结果
    print(f"\n✅ 数据验证:")
    val = result['validation']
    if hasattr(val, '__dict__'):
        print(f"  有效性: {'✓ 通过' if val.is_valid else '✗ 未通过'}")
        print(f"  完整性: {val.completeness:.1f}%")
        if val.issues:
            print(f"  问题:")
            for issue in val.issues:
                print(f"    - {issue}")
    
    print('\n' + '=' * 60)

if __name__ == "__main__":
    # 设置环境变量
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    
    print('正在分析文档...')
    result = asyncio.run(analyze_document())
    
    # 格式化输出
    format_output(result)
    
    # 也输出原始JSON供调试
    print('\n📋 原始JSON数据:')
    print(json.dumps(result, indent=2, default=str))