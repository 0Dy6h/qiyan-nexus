# Code Coverage

本文档说明如何生成和查看代码覆盖率报告。

## 安装依赖

pytest-cov 已添加到 `[dev]` 依赖中。如果尚未安装，运行：

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 生成覆盖率报告

### 方法 1：使用脚本（推荐）

```powershell
cd backend
.\run-coverage.ps1
```

可选参数：
- `-CoverageThreshold 80`：设置最低覆盖率门槛（默认 80%）

### 方法 2：手动运行

```powershell
cd backend
& .\.uv-test-venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

## 查看报告

### 终端报告

测试运行后会在终端显示覆盖率摘要和缺失行数。

### HTML 报告

打开 `backend/htmlcov/index.html` 查看详细的交互式覆盖率报告：

```powershell
# Windows
start backend/htmlcov/index.html

# 或直接在浏览器打开
# file:///D:/Projects/Tcm_tech/backend/htmlcov/index.html
```

## 覆盖率目标

当前项目覆盖率目标：**≥ 80%**

## 覆盖率报告文件

以下文件已添加到 `.gitignore`：
- `.coverage` - 覆盖率数据文件
- `htmlcov/` - HTML 报告目录
- `coverage.xml` - XML 格式报告（用于 CI）
- `*.cover` - 其他覆盖率文件
- `.pytest_cache/` - pytest 缓存

## CI/CD 集成

未来可在 `.github/workflows/ci.yml` 的 backend job 中添加：

```yaml
- name: Generate coverage report
  run: python -m pytest --cov=app --cov-report=xml --cov-report=term-missing

- name: Upload coverage to Codecov (optional)
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
```

## 常见问题

### Q: 覆盖率低于 80% 怎么办？

A: 
1. 查看 HTML 报告，识别未覆盖的代码
2. 为关键路径添加测试
3. 对于不需要测试的代码（如 `if __name__ == "__main__"`），可以使用 `# pragma: no cover` 标记

### Q: 某些模块不需要计入覆盖率

A: 在 `pyproject.toml` 中配置排除：

```toml
[tool.coverage.run]
omit = [
    "app/core/config.py",
    "tests/*",
]
```

### Q: 如何只查看特定模块的覆盖率？

A: 
```powershell
& .\.uv-test-venv\Scripts\python.exe -m pytest --cov=app.services --cov-report=term-missing
```
