# Runtime state

本目录用于保存本地运行时状态副本，例如 PDF 上传 metadata、parse status、parse result、network task 状态与显式 opt-in 的网络药理学外部响应缓存。

- `literature_state.json` 是运行态文件，不提交。
- `network_tasks_state.json` 是网络药理学 task 运行态文件，不提交。
- `network_cache/` 是 `QIYAN_NETWORK_DATA_PROVIDER=live` 时的外部数据缓存目录，可能包含 PubChem、ChEMBL、UniProt、STRING、KEGG 或 TCMSP 响应副本，不提交。
- seed 数据仍在 `backend/data/literature/sample_*.json`。
- 清空本目录会让应用重新从 seed 数据 bootstrap；清空 `network_cache/` 会让下一次 live network run 重新请求或重新要求导入缓存。
- 不要把本目录内容作为 fixture 修改提交。
