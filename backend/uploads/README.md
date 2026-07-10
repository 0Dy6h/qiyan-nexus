# Backend uploads

本目录用于本地 PDF 上传运行时文件，默认由 `POST /api/uploads/pdf` 写入。

- 运行时 PDF 文件不提交。
- 不要单独清空本目录：PDF metadata 与 uploaded chunk 还可能存在于对应 runtime state。只在同步删除隔离 runtime，或明确接受 orphan metadata/失效预览链接时清理。
- 如需覆盖路径，设置 `UPLOAD_STORAGE_DIR`。
- 测试应使用临时目录，不依赖这里的具体文件。
