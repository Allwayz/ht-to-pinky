---
name: ht-to-pinky
description: "Convert strict HomeTrans test_case.md files into short Pinky test cases. Use when the user wants HT or HomeTrans cases rewritten for Pinky. Do not use to generate HomeTrans cases, edit SPEC, or drive the phone."
---

# HT to Pinky

把严格的 HomeTrans `test_case.md` 改写成 Pinky 能逐条执行的短用例。只改写，不运行 Pinky，不修改 HomeTrans 产物。

细则和输出模板在 [references/conversion.md](references/conversion.md)。先读它再写文件。

## 输入

只接受 HomeTrans 测试用例契约里的 `test_case.md`：有 `## Scenario List`，每条是 `### Scenario N-M`，字段用全角冒号，动作用 ` -> ` 分隔。

不接受粗需求、SPEC、`review_notes.md`、`pre_test_case.md`，也不接受已经写给 Pinky 的用例。这些文件不能拿来编造新用例。

用户可以另外给三项，没有就不要猜：

- 包名、设备名、界面语言。
- 控件对照：把没有「」的动作换成屏幕上的真实控件，例如 `点击继续` = `点地址框右侧的箭头`。
- 输出路径。

## 步骤

1. 运行校验，确认每份文件都是严格产物：

```bash
python3 <skill_dir>/scripts/extract_ht_cases.py <文件或目录>
```

退出码非 0 就停止，列出脚本报告的错误。不要把缺字段的文件补写成用例。

2. 按 [references/conversion.md](references/conversion.md) 逐条改写。一条 Scenario 变成一条 Pinky 用例，或一条未转换记录。不要把几条合成一条长流程。

3. 写入新文件。用户给了路径就用该路径；否则写到这些 `test_case.md` 共同父目录的同级目录 `pinky/test_case.md`。目标已存在时不要覆盖，改写到 `pinky/test_case-2.md` 并说明。

4. 写完后用原文核对：可执行用例和未转换记录必须覆盖每一条 Scenario，不能多出源文件里没有的场景。

## 硬性限制

- 不修改、不覆盖 HomeTrans 的 `test_case.md`、SPEC 和 review notes。
- 屏幕上的原文保持源文件里的写法，包括英文和符号。
- 没有「」的 `点击继续`、`点击确定`、`点击提交`，没有控件对照时不要猜按钮，整条放入未转换。
- 相机、二维码、手电筒、相机权限整条不转换。文首写明不要点这些入口、不要允许相机。
- 账号删除、账号注销、内容删除整条不转换。不要写出这些步骤。文首写明不要删除账号、不要注销账号、不要删除内容。
- 高度、省略号、单行滚动、像素不留给 Pinky 判断。同一条里其余能看见的测试点可以保留。
- 做不到的步骤（构造返回值、注入数据、没有账号却要进入登录后页面）整条不转换。
- 输出是给人再逐条交给 Pinky 的用例，不是一次可粘贴的整份任务。
