#!/usr/bin/env python3
"""
测试 PDF 处理性能
"""

import sys
import time
import statistics
sys.path.insert(0, '/Users/xiong_ge/Desktop/MyCode/shoreline/ai-agents/tests')

import handler
import boto3

# 配置 S3
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)
handler.s3 = s3

print("="*60)
print("⏱️  PDF 处理性能测试")
print("="*60)

# 下载测试文件
print("\n准备测试文件...")
response = s3.get_object(Bucket='medical-documents', Key='misaligned.pdf')
pdf_bytes = response['Body'].read()
print(f"文件大小: {len(pdf_bytes):,} bytes")

# 测试 1: 多次运行取平均
print("\n📊 测试 1: 300 DPI 重复测试 (5次)")
print("-"*40)
times = []
for i in range(5):
    start = time.time()
    handler.process_pdf_bytes_to_s3(
        pdf_bytes=pdf_bytes,
        out_bucket='medical-documents',
        out_prefix=f'benchmark/test_{i}',
        dpi=300,
        page_from=1,
        page_to=1
    )
    end = time.time()
    elapsed = end - start
    times.append(elapsed)
    print(f"第 {i+1} 次: {elapsed:.3f} 秒")

avg_time = statistics.mean(times)
std_dev = statistics.stdev(times) if len(times) > 1 else 0
print(f"\n平均时间: {avg_time:.3f} 秒")
print(f"标准差: {std_dev:.3f} 秒")
print(f"最快: {min(times):.3f} 秒")
print(f"最慢: {max(times):.3f} 秒")

# 测试 2: 不同 DPI
print("\n📊 测试 2: 不同 DPI 性能")
print("-"*40)
dpi_results = {}
for dpi in [150, 200, 300, 400]:
    start = time.time()
    handler.process_pdf_bytes_to_s3(
        pdf_bytes=pdf_bytes,
        out_bucket='medical-documents',
        out_prefix=f'benchmark/dpi_{dpi}',
        dpi=dpi,
        page_from=1,
        page_to=1
    )
    end = time.time()
    elapsed = end - start
    dpi_results[dpi] = elapsed
    
    # 获取输出文件大小
    response = s3.list_objects_v2(
        Bucket='medical-documents',
        Prefix=f'benchmark/dpi_{dpi}'
    )
    if 'Contents' in response:
        file_size = response['Contents'][0]['Size']
        print(f"DPI {dpi}: {elapsed:.3f} 秒, 输出大小: {file_size:,} bytes")
    else:
        print(f"DPI {dpi}: {elapsed:.3f} 秒")

# 测试 3: 多页文档（如果有）
print("\n📊 测试 3: 多页文档测试")
print("-"*40)

# 测试 2_page_with_back.pdf（两页）
try:
    response = s3.get_object(Bucket='medical-documents', Key='2_page_with_back.pdf')
    pdf_2pages = response['Body'].read()
    print(f"测试文件: 2_page_with_back.pdf ({len(pdf_2pages):,} bytes)")
    
    start = time.time()
    handler.process_pdf_bytes_to_s3(
        pdf_bytes=pdf_2pages,
        out_bucket='medical-documents',
        out_prefix='benchmark/2pages',
        dpi=300,
        page_from=1,
        page_to=None  # 处理所有页
    )
    end = time.time()
    elapsed = end - start
    print(f"处理 2 页耗时: {elapsed:.3f} 秒")
    print(f"平均每页: {elapsed/2:.3f} 秒")
    
except Exception as e:
    print(f"无法测试多页文档: {e}")

print("\n" + "="*60)
print("📈 性能总结")
print("="*60)
print(f"单页处理平均时间 (300 DPI): {avg_time:.3f} 秒")
print(f"处理速度: {1/avg_time:.1f} 页/秒")
print(f"预估 100 页文档处理时间: {avg_time*100:.1f} 秒 ({avg_time*100/60:.1f} 分钟)")

print("\nDPI 对性能的影响:")
base_time = dpi_results.get(300, 1)
for dpi, time_taken in sorted(dpi_results.items()):
    ratio = time_taken / base_time
    print(f"  DPI {dpi}: {ratio:.2f}x 相对时间")