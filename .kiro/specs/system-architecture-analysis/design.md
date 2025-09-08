# Design Document

## Overview

本设计文档详细描述了如何重构当前LangGraph项目以符合README.md中定义的Mono Repo规范。设计目标是创建一个统一、可维护、可扩展的多agent系统架构。

## Architecture

### Current State Analysis

**当前结构问题：**
```
project-root/
├── agents/
│   ├── hello/
│   │   ├── __init__.py
│   │   └── graph.py                 # ❌ 缺少配置文件
│   └── ping/
│       ├── __init__.py
│       └── graph.py                 # ❌ 缺少配置文件
├── medical-claims-processor/        # ❌ 应该在agents/下
│   ├── agents/
│   │   ├── document_classifier/     # ❌ 应该提升到顶级
│   │   └── medical_data_extractor/  # ❌ 应该提升到顶级
│   └── ...
├── pyproject.toml                   # ❌ 包含所有依赖
└── langgraph.json                   # ❌ 直接引用agent文件
```

### Target Architecture

**目标结构：**
```
project-root/
├── agents/
│   ├── hello/
│   │   ├── pyproject.toml
│   │   ├── hello/
│   │   │   ├── __init__.py
│   │   │   └── graph.py
│   │   ├── langgraph.json
│   │   └── .env
│   ├── ping/
│   │   ├── pyproject.toml
│   │   ├── ping/
│   │   │   ├── __init__.py
│   │   │   └── graph.py
│   │   ├── langgraph.json
│   │   └── .env
│   ├── document-classifier/
│   │   ├── pyproject.toml
│   │   ├── document_classifier/
│   │   │   ├── __init__.py
│   │   │   └── graph.py
│   │   ├── langgraph.json
│   │   └── .env
│   ├── medical-data-extractor/
│   │   ├── pyproject.toml
│   │   ├── medical_data_extractor/
│   │   │   ├── __init__.py
│   │   │   └── graph.py
│   │   ├── langgraph.json
│   │   └── .env
│   └── medical-claims-processor/
│       ├── pyproject.toml
│       ├── medical_claims_processor/
│       │   ├── __init__.py
│       │   ├── api.py
│       │   └── orchestrator.py
│       ├── langgraph.json
│       └── .env
├── common/
│   ├── pyproject.toml
│   └── common/
│       ├── __init__.py
│       ├── db_utils.py
│       ├── s3_utils.py
│       └── logging.py
├── config/
│   ├── global.env
│   └── logging.yaml
├── pyproject.toml                   # 项目级元数据
└── langgraph.json                   # 组合配置
```

## Components and Interfaces

### 1. Agent Structure Template

每个agent遵循统一的结构模式：

```
agents/{agent-name}/
├── pyproject.toml          # Agent特定依赖
├── {agent_name}/           # Python包目录
│   ├── __init__.py
│   └── graph.py           # LangGraph定义
├── langgraph.json         # Agent配置
└── .env                   # Agent环境变量
```

### 2. Configuration Management

**层次化配置策略：**
1. **全局配置** (`config/global.env`) - 所有agent共享的配置
2. **Agent配置** (`agents/{name}/.env`) - Agent特定配置，覆盖全局配置
3. **LangGraph配置** (`agents/{name}/langgraph.json`) - Agent的图配置

### 3. Dependency Management

**三层依赖管理：**
1. **项目级** (`pyproject.toml`) - 开发工具、测试框架、项目元数据
2. **共享级** (`common/pyproject.toml`) - 共享工具依赖
3. **Agent级** (`agents/{name}/pyproject.toml`) - Agent特定依赖

### 4. Shared Utilities (Common Package)

**共享工具设计：**
```python
# common/common/db_utils.py
class DatabaseConnection:
    """统一的数据库连接管理"""
    
# common/common/s3_utils.py  
class S3FileHandler:
    """S3文件操作工具"""
    
# common/common/logging.py
def setup_logging(agent_name: str):
    """统一的日志配置"""
```

## Data Models

### 1. Agent Configuration Schema

```json
{
  "name": "agent-name",
  "description": "Agent description",
  "python_path": "./agent_name/graph.py:graph",
  "dependencies": ["common"],
  "env_vars": ["API_KEY", "CONFIG_VAR"]
}
```

### 2. Root Configuration Schema

```json
{
  "dependencies": [".", "common"],
  "graphs": {
    "hello": "./agents/hello/langgraph.json",
    "ping": "./agents/ping/langgraph.json",
    "document-classifier": "./agents/document-classifier/langgraph.json",
    "medical-data-extractor": "./agents/medical-data-extractor/langgraph.json",
    "medical-claims-processor": "./agents/medical-claims-processor/langgraph.json"
  },
  "env": ["config/global.env"],
  "image_distro": "wolfi"
}
```

### 3. Package Configuration Template

```toml
[tool.poetry]
name = "agent-name"
version = "0.1.0"
description = "Agent description"
authors = ["Author <email>"]

[tool.poetry.dependencies]
python = "^3.12"
langgraph = "^0.2.6"
common = {path = "../../common", develop = true}

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

## Error Handling

### 1. Configuration Validation

- 启动时验证所有配置文件的完整性
- 检查依赖关系的循环引用
- 验证环境变量的可用性

### 2. Agent Isolation

- 每个agent的错误不应影响其他agent
- 提供详细的错误日志和调试信息
- 支持agent级别的重启和恢复

### 3. Migration Safety

- 保持向后兼容性
- 提供回滚机制
- 分阶段迁移策略

## Testing Strategy

### 1. Unit Testing

- 每个agent独立的单元测试
- 共享工具的测试覆盖
- 配置文件的验证测试

### 2. Integration Testing

- Agent间协作测试
- 端到端工作流测试
- 配置加载和环境变量测试

### 3. Migration Testing

- 重构前后功能对比测试
- 性能基准测试
- 兼容性验证测试

## Implementation Phases

### Phase 1: Foundation Setup
1. 创建common目录和共享工具
2. 创建config目录和全局配置
3. 更新根目录配置文件

### Phase 2: Agent Restructuring  
1. 重构hello和ping agent
2. 提升document-classifier和medical-data-extractor
3. 重构medical-claims-processor为协调服务

### Phase 3: Integration & Testing
1. 更新所有配置引用
2. 运行集成测试
3. 验证功能完整性

### Phase 4: Documentation & Cleanup
1. 更新README.md
2. 清理旧文件和配置
3. 添加使用文档