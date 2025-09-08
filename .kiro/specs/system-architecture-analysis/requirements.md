# Requirements Document

## Introduction

本需求文档旨在分析当前LangGraph项目的系统架构，对比README.md中定义的Mono Repo规范，识别架构差异并提出改进建议。

### 发现的主要差异

1. **Agent目录结构不完整** - 根目录agents/下的hello和ping agent缺少独立的pyproject.toml、langgraph.json和.env文件
2. **缺失共享工具目录** - 根目录没有common/目录用于共享工具和工具类
3. **缺失全局配置目录** - 根目录没有config/目录用于全局环境变量和配置
4. **依赖管理不符合规范** - 根目录所有依赖集中在一个pyproject.toml中，而非按agent分离
5. **配置文件结构问题** - 根目录agents/下缺少agent级别的独立配置文件
6. **项目结构不一致** - medical-claims-processor/目录已经符合规范，但根目录agents/不符合
7. **Agent层级结构错误** - medical-claims-processor/agents/下的子agent应该提升到顶级agents/目录，实现扁平化结构
8. **文档与实际不符** - README.md提到src/agent/graph.py但实际不存在src目录
9. **包管理工具混用** - 根目录使用setuptools，medical-claims-processor使用poetry

目标是重构项目结构以完全符合Mono Repo规范，提高代码组织性、可维护性和可扩展性。

## Requirements

### Requirement 1

**User Story:** 作为开发者，我希望重构agents目录结构以符合Mono Repo规范，使每个agent具有独立的配置和依赖管理。

#### Acceptance Criteria

1. WHEN 重构hello agent THEN 应该创建agents/hello/pyproject.toml文件定义其依赖
2. WHEN 重构hello agent THEN 应该创建agents/hello/langgraph.json文件定义其配置
3. WHEN 重构hello agent THEN 应该创建agents/hello/.env文件用于环境变量
4. WHEN 重构ping agent THEN 应该创建agents/ping/pyproject.toml文件定义其依赖
5. WHEN 重构ping agent THEN 应该创建agents/ping/langgraph.json文件定义其配置
6. WHEN 重构ping agent THEN 应该创建agents/ping/.env文件用于环境变量
7. WHEN 重构agent包结构 THEN 应该将graph.py移动到正确的包目录中

### Requirement 2

**User Story:** 作为开发者，我希望创建common目录来管理共享工具和工具类，避免代码重复。

#### Acceptance Criteria

1. WHEN 创建common目录 THEN 应该包含pyproject.toml文件定义共享依赖
2. WHEN 创建common包 THEN 应该包含__init__.py文件使其成为Python包
3. WHEN 创建共享工具 THEN 应该包含db_utils.py用于数据库访问辅助功能
4. WHEN 创建共享工具 THEN 应该包含s3_utils.py用于S3文件处理工具
5. WHEN 创建共享工具 THEN 应该包含logging.py用于自定义日志设置
6. IF agent需要共享工具 THEN agent应该能够通过import common.xxx导入工具

### Requirement 3

**User Story:** 作为开发者，我希望创建config目录来管理全局配置，实现统一的配置管理策略。

#### Acceptance Criteria

1. WHEN 创建config目录 THEN 应该包含global.env文件用于全局环境变量
2. WHEN 创建config目录 THEN 应该包含logging.yaml文件用于全局日志配置
3. WHEN 配置全局环境变量 THEN global.env应该包含所有agent共享的配置项
4. WHEN 配置日志系统 THEN logging.yaml应该定义统一的日志格式和级别
5. IF agent需要特定配置 THEN agent的.env文件应该覆盖全局配置

### Requirement 4

**User Story:** 作为开发者，我希望重构根目录配置文件，使其符合Mono Repo的组合配置模式。

#### Acceptance Criteria

1. WHEN 更新根目录langgraph.json THEN 应该引用各个agent的独立配置
2. WHEN 更新根目录pyproject.toml THEN 应该只包含项目级别的元数据和开发工具配置
3. WHEN 配置依赖关系 THEN 根目录应该能够管理所有agent和common包的依赖
4. WHEN 配置构建系统 THEN 应该支持独立构建和部署各个agent

### Requirement 5

**User Story:** 作为开发者，我希望统一项目结构和包管理工具，确保整个项目的一致性。

#### Acceptance Criteria

1. WHEN 检查包管理 THEN 整个项目应该使用统一的包管理工具（推荐poetry）
2. WHEN 检查文档 THEN README.md应该与实际项目结构保持一致
3. WHEN 对比子项目 THEN 根目录agents/结构应该与medical-claims-processor/agents/结构保持一致
4. WHEN 检查配置 THEN 所有agent都应该遵循相同的配置模式
5. IF 存在不一致 THEN 应该选择最佳实践并统一应用

### Requirement 6

**User Story:** 作为开发者，我希望将medical-claims-processor的子agent提升到顶级agents目录，实现扁平化的agent组织结构。

#### Acceptance Criteria

1. WHEN 重构agent结构 THEN 应该将document_classifier移动到agents/document-classifier/目录
2. WHEN 重构agent结构 THEN 应该将medical_data_extractor移动到agents/medical-data-extractor/目录
3. WHEN 重构medical-claims-processor THEN 应该将其转换为协调服务或API网关，放在agents/medical-claims-processor/目录
4. WHEN 调整配置 THEN 每个提升的agent应该有独立的pyproject.toml、langgraph.json和.env文件
5. WHEN 更新根配置 THEN 根目录的langgraph.json应该包含所有顶级agent的配置引用

### Requirement 7

**User Story:** 作为开发者，我希望确保重构后的系统能够正常工作，并且向后兼容现有功能。

#### Acceptance Criteria

1. WHEN 完成重构 THEN 所有agent（hello、ping、document-classifier、medical-data-extractor、medical-claims-processor）应该能够正常运行
2. WHEN 测试系统 THEN langgraph dev命令应该能够正确启动所有agent
3. WHEN 验证配置 THEN 每个agent应该能够读取其独立的配置和环境变量
4. WHEN 测试共享工具 THEN agent应该能够正确导入和使用common包中的工具
5. WHEN 验证提升的agent THEN document-classifier和medical-data-extractor应该作为独立agent正常工作