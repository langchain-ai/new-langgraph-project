# Docker部署指南

本项目支持使用Docker和LocalStack在本地模拟AWS环境进行开发和测试。项目采用简化架构，仅使用LocalStack模拟S3服务，不依赖PostgreSQL或Redis。

## 快速开始

### 1. 环境准备

```bash
# 复制环境变量配置文件
cp .env.example .env

# 编辑.env文件，填入你的OpenAI API Key（如果需要使用OpenAI）
# OPENAI_API_KEY=your_actual_api_key_here
```

### 2. 启动LocalStack（仅AWS服务模拟）

```bash
# 使用Makefile命令
make dev-up

# 或者直接使用docker-compose
docker-compose -f docker-compose.dev.yml up -d

# 查看日志
make dev-logs
```

### 3. 启动完整应用（包括API服务）

```bash
# 构建Docker镜像
make docker-build

# 启动所有服务
make docker-up

# 或使用部署脚本
./scripts/deploy.sh up
```

## 服务端口

启动后，以下服务将可用：

- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **LocalStack**: http://localhost:4566

## 测试API

```bash
# 健康检查
curl http://localhost:8000/health

# 测试文档分类
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "s3_key": "test/sample-cms1500.pdf",
    "process_type": "classify"
  }'

# 或使用Makefile
make test-api
```

## LocalStack S3测试

```bash
# 安装awscli-local
pip install awscli-local

# 列出S3 bucket
awslocal s3 ls

# 上传文件到LocalStack S3
awslocal s3 cp tests/test-files/cms1500-sample.txt s3://medical-documents/incoming/

# 列出bucket内容
awslocal s3 ls s3://medical-documents/incoming/
```

## Docker Compose配置

项目包含两个docker-compose配置文件：

1. **docker-compose.dev.yml** - 仅LocalStack，用于开发
2. **docker-compose.yml** - 完整服务栈（LocalStack + API服务）

## 常用命令

```bash
# 开发环境
make dev-up       # 启动LocalStack
make dev-down     # 停止LocalStack
make dev-logs     # 查看LocalStack日志

# Docker环境
make docker-build # 构建镜像
make docker-up    # 启动所有服务
make docker-down  # 停止所有服务
make docker-logs  # 查看服务日志

# 清理
make clean        # 清理所有容器和数据卷

# 测试
make test         # 运行测试
make test-api     # 测试API端点
```

## 故障排除

### LocalStack无法启动
```bash
# 检查Docker是否运行
docker ps

# 检查端口是否被占用
lsof -i:4566

# 清理并重启
make clean
make dev-up
```

### API无法连接到LocalStack
确保环境变量正确设置：
```bash
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

### 权限问题
```bash
# 确保脚本有执行权限
chmod +x scripts/*.sh
```

## 项目结构

```
ai-agents/
├── Dockerfile                # API服务Docker镜像
├── docker-compose.yml        # 完整服务栈配置
├── docker-compose.dev.yml    # 开发环境配置（仅LocalStack）
├── Makefile                  # 便捷命令
├── scripts/
│   ├── deploy.sh            # 部署脚本
│   └── localstack-init.sh   # LocalStack初始化脚本
├── .env.example             # 环境变量模板
└── tests/test-files/        # 测试文件
```

## 注意事项

1. LocalStack社区版对Textract的支持有限，完整功能需要Pro版
2. 首次启动需要下载Docker镜像，可能需要几分钟
3. 确保Docker Desktop分配了足够的内存（建议至少4GB）
4. 生产环境请使用实际的AWS服务，而不是LocalStack