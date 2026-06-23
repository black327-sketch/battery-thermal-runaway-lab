# DOCX_FIX_REPORT

生成时间：2026-06-18 18:27

## 根因

实验报告 Word/docx 生成失败的主要风险点在 `app/utils/report_docx.py`：

1. 文件前半段已经改为复用 `generate_formal_report(ctx)` 的 Markdown，但后半段仍保留一大段旧版不可达实现。
2. 旧版实现中存在乱码、未闭合字符串、残留格式化片段和不一致的表格处理逻辑，容易在后续维护或局部导入时引发语法/运行时问题。
3. 原实现对空报告、非 dict 输入、表格列数不一致、None 值和 Markdown 列表/标题的防御不足。
4. `requirements.txt` 未声明 `python-docx`，新环境可能安装依赖后仍无法生成 Word 文件。

## 修改文件

- `app/utils/report_docx.py`
- `app/pages/7_实验报告生成.py`
- `tests/test_report_generator.py`
- `requirements.txt`
- `pytest.ini`

## 修复方式

1. 重写 `report_docx.py` 为单一职责的 Markdown-to-docx 渲染器。
2. `generate_docx(ctx)` 继续支持报告上下文 dict，并始终复用 `generate_formal_report(ctx)` 生成的同一份 Markdown。
3. 新增 `markdown_to_docx_bytes(markdown_text)`，明确输入输出：输入 Markdown 字符串，输出 docx `bytes`。
4. 空报告或异常上下文会生成带提示的 docx，而不是崩溃。
5. Markdown 标题、段落、项目符号列表、编号列表和简单 pipe 表格均可转换。
6. 表格列数不一致时按最大列数自动补空单元格。
7. 中文字体优先设置为 `Microsoft YaHei`，不依赖系统字体存在才能运行。
8. 保持下载 mime：
   `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

## 测试结果

- `python -m compileall -q app tests`：通过
- `pytest -q`：`227 passed`
- 直接调用 `generate_docx(...)`：返回非空 bytes，并可被 `python-docx` 打开
- Playwright 实际下载 Word 文件：已保存到 `artifacts/report-download-test.docx`
- 下载文件验证：`python-docx` 可打开，包含 30 个段落、8 个表格

## 仍需注意

1. 当前 docx 转换器支持项目报告所需的基础 Markdown，不是通用 Markdown 完整渲染器。
2. 数学公式会以普通段落形式写入 Word，未转换为 Word 原生公式对象。
3. `python-docx` 已补充到 `requirements.txt`，新环境需要重新安装依赖。
