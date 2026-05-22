# Backend uploads

本目录用于本地 PDF 上传运行时文件，默认由 `POST /api/uploads/pdf` 写入。

- 运行时 PDF 文件不提交。
- 本目录可安全清空；下一次上传会重新生成文件。
- 如需覆盖路径，设置 `UPLOAD_STORAGE_DIR`。
- 测试应使用临时目录，不依赖这里的具体文件。
