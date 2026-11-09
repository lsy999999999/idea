# 流程审查修正：learning-inquiry-v4

默认继续使用完整上下文（当前假说、前序推理、长期记忆）。新会话不等于仅记忆评估。需要输入消融时，原生入口显式传 --continuation-mode memory_only_probe；API 新运行配置使用 continuation_mode: memory_only_probe。默认值均为 full_context。

hypothesis_updates 可声明 depends_on（精确的已提供假说版本引用）；influenced_by 仍表示启发，二者不混用。出现 revision_obligations 后，用 dependency_responses 记录 revise/reaffirm/park/unresolved 及理由。未决假说继续保留，不构成否定或淘汰。仅变更依赖引用不算内容进展。

内审的需要纠正标签是审阅者意见，报告保留 reviewer_status，同时标注引文/计算核验深度和未决状态。作者可以反驳。接受纠正且标记受影响记忆时，必须更改相应内容，不能只改标签。

记忆、问题和假说在提交前校验。长审阅原文不截断。仅记忆模式校验实际读取的记忆身份与版本；原生命令行仍须审计工具访问，不能仅凭输入清单声称严格环境隔离。

代码改变必须使用新运行目录；旧运行保留归档源码和原始结论。详细审查、测试与尚缺实验证据见 /Applications/ideas/research/icml_review_20261109/FLOW_REVIEW_CN.md。
