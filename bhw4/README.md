# 大作业4 Hash 与 LSH 语义复用

报告入口：[四页 PDF](23300200015_张祺昀_作业4.pdf)，可编辑正文：[大作业4 报告正文](大作业4_报告正文.md)。实验已完成并通过独立复核；姓名、学号已填写，当前 PDF 根据用户修改后的 Markdown 正文生成。

题目要求见 [作业要求原文](作业要求原文.md)，实验口径和事先确定的参数见 [实验方案](实验方案.md)。原文中未随粘贴保留的公式只在方案和报告中补充。

学习与后续改进入口：[方案拆解与学习改进记录](方案拆解与学习改进记录.md)，包含算法推导、代码对应、真实查询案例、指标解释及后续实验记录模板。

采用 BANKING77 历史请求、公开 MiniLM 384 维向量，比较 Brute-force、Exact Hash Only 和 Hash + 随机超平面 LSH。使用 CPU，不训练模型，不调用收费 API。

主实验 N=10,003、非重复查询 300 条，Macro Recall 98.55%，平均候选比例 7.90%；100 个 Exact 查询全部命中。余弦次数减少约 12.65 倍，当前单线程实测检索均时提速约 1.51 倍。另有四组参数消融、三个固定种子和三种历史规模结果。

## 材料

- `数据/`：公开原始 CSV、许可证、数据划分、模型来源与校验值。
- `验证/prepare.py`：下载公开材料、精确去重、固定抽样、生成并缓存向量。
- `验证/experiment.py`：索引、三种方法、参数消融、规模实验及计时。
- `验证/主实验逐查询.json`：每个查询的 Ground Truth、完整候选 ID 和最终结果。
- `验证/实验结果.json`：全部汇总、消融逐查询数据、空间和计时口径。
- `验证/audit.py`：独立 float64 真值、桶集合、摘要碰撞和汇总复核。
- `验证/build_report.py`：从同一组文字与实测结果生成四页 PDF 和 Markdown 正文。
- `验证/markdown_to_pdf.py`：直接读取当前 Markdown 正文生成 PDF，用于编辑正文后的排版与定稿。
- `验证/报告检查.json`：页数、文字、思考题字数、文件校验及视觉验收。
- `.cache/`、`.deps/`：可重建的模型、向量、依赖，不纳入 Git。

## 复现

在仓库根目录、Python 3.12 环境中执行：

```powershell
python -m pip install --target bhw4/.deps -r bhw4/requirements.txt
python bhw4/验证/prepare.py
python bhw4/验证/experiment.py
python bhw4/验证/audit.py
python bhw4/验证/markdown_to_pdf.py --output bhw4/23300200015_张祺昀_作业4.pdf
```

首次准备需要访问 GitHub 和 Hugging Face；之后的实验、审计和报告构建均可离线运行。生成文件覆盖只发生在验证结果与报告中，不修改题目原文及公开原始 CSV。主配置在实验前固定为 k=12、L=46、τ=0.80，不根据消融结果换主配置。

仅更新 PDF 时，执行最后一条命令即可。`build_report.py` 保留为初版正文生成器；它会重建并覆盖 Markdown 正文，当前编辑稿使用 `markdown_to_pdf.py` 转换。

Recall 以余弦阈值集合为准，非人工语义可复用标注；没有历史答案文件，因此本作业验证检索能力，不验证生成答案的事实正确性。100 个 Exact 查询和 300 个非重复查询分别评价。
