#!/usr/bin/env python
"""测试文档处理功能"""

import asyncio
import sys
import os
import json

sys.path.insert(0, '.')
from api.services.langgraph_processor import LangGraphProcessor

async def test():
    processor = LangGraphProcessor(s3_bucket='medical-claims-documents')
    result = await processor.process_document('documents/cms1500_filled_dummy.pdf')
    return result

if __name__ == "__main__":
    # 设置环境变量
    os.environ['AWS_ACCESS_KEY_ID'] = 'test'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:4566'
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 使用命令行指定的文件
        s3_key = sys.argv[1]
        if not s3_key.startswith('documents/'):
            s3_key = f'documents/{s3_key}'
    else:
        # 默认文件
        s3_key = 'documents/cms1500_filled_dummy.pdf'
    
    print(f'正在处理文档: {s3_key}...')
    
    async def test_specific():
        processor = LangGraphProcessor(s3_bucket='medical-claims-documents')
        result = await processor.process_document(s3_key)
        return result
    
    result = asyncio.run(test_specific())
    
    # 格式化输出结果
    print('\n========== 文档分析结果 ==========')
    print(f"\n📄 文档分类:")
    print(f"  - 文档类型: {result['classification']['document_type']}")
    print(f"  - 推荐处理器: {result['classification']['recommended_processor']}")
    print(f"  - 置信度: {result['classification']['confidence']:.2%}")
    print(f"  - 识别原因: {result['classification']['reason']}")
    indicators = result['classification']['indicators_found']
    print(f"  - 发现的指标: {', '.join(indicators[:3]) if indicators else '无'}")
    
    print(f"\n📊 文件信息:")
    print(f"  - 文件大小: {result['file_info']['size']} bytes")
    print(f"  - 内容类型: {result['file_info']['content_type']}")
    
    print(f"\n💊 提取的医疗数据:")
    data = result['extracted_data']
    if hasattr(data, '__dict__'):
        print(f"  - 患者姓名: {data.patient_name}")
        print(f"  - 出生日期: {data.patient_dob}")
        print(f"  - 保险ID: {data.insurance_id}")
        print(f"  - 诊断代码: {', '.join(data.diagnosis_codes)}")
        print(f"  - 程序代码: {', '.join(data.procedure_codes)}")
        print(f"  - 总费用: ${data.total_charge:.2f}")
    else:
        print(f"  {data}")
    
    print(f"\n✅ 验证结果:")
    val = result['validation']
    if hasattr(val, '__dict__'):
        print(f"  - 有效性: {'是' if val.is_valid else '否'}")
        print(f"  - 完整性: {val.completeness:.1f}%")
        if val.issues:
            print(f"  - 问题: {val.issues}")
    else:
        print(f"  {val}")
    
    print("\n========== 处理完成 ==========")