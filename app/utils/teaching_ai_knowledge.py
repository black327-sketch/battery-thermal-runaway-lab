"""Local knowledge snippets for the teaching assistant.

The content is intentionally bounded to the project experiment and reference
context. It is not a general safety, firefighting, or engineering design model.
"""

from __future__ import annotations

from dataclasses import dataclass


SAFETY_BOUNDARY = "注意：这是虚拟仿真教学解释，不是真实实验操作、消防应急或工程防爆设计建议。"


@dataclass(frozen=True)
class KnowledgeEntry:
    key: str
    triggers: tuple[str, ...]
    conclusion: str
    reason: str
    next_step: str
    basis: str


KNOWLEDGE_BASE: tuple[KnowledgeEntry, ...] = (
    KnowledgeEntry(
        key="experiment_purpose",
        triggers=("目的", "为什么做", "实验目标", "热失控产气"),
        conclusion="本实验用于理解方壳磷酸铁锂电池热失控过程中的产气、采样、GC 组分分析和 LFL_mix 教学估算。",
        reason="项目把热失控阶段、H2/CO/CO2/CH4/C2H4/C2H6 等气体组分、四次采样节点和可燃风险教学模型串成一条学习链。",
        next_step="按页面流程先完成实验一的采样与 GC，再进入实验二的 LFL_mix 与 R = C / LFL_mix 计算。",
        basis="项目参考对象为 22Ah 方壳磷酸铁锂电池，平台包括防爆舱、加热装置、温度/电压/压力测量、气体采集和数据分析系统。",
    ),
    KnowledgeEntry(
        key="lfp_prismatic",
        triggers=("方壳", "磷酸铁锂", "lfp", "为什么选择", "22ah"),
        conclusion="本平台围绕 22Ah 方壳磷酸铁锂电池开展虚拟仿真教学。",
        reason="方壳电池结构、SOC、热失控阶段和产气变化适合串联温度、电压、压力、采样和 GC 分析等教学环节。",
        next_step="报告中描述实验对象时，应写明这是项目参考对象，不要扩展为所有锂离子电池的通用结论。",
        basis="项目事实：实验对象为 22Ah 方壳磷酸铁锂电池。",
    ),
    KnowledgeEntry(
        key="zero_soc",
        triggers=("0%soc", "0% soc", "0％soc", "0％ soc", "零 soc", "不一定热失控", "喷阀但不", "喷阀不算"),
        conclusion="0%SOC 可以出现安全阀喷阀现象，但不能自动判定为热失控。",
        reason="项目参考逻辑中，安全阀喷阀只是第二次采气节点；热失控触发还需要温升速率达到阈值并持续满足条件。文献实验里 0%SOC 可喷阀，但未发生热失控。",
        next_step="如果当前处于喷阀阶段，应记录第二次采样；不要强行推进到温度峰值或热失控峰值结论。",
        basis="平台规则：安全阀喷阀不等于一定热失控；0%SOC 可喷阀但文献实验中未发生热失控。",
    ),
    KnowledgeEntry(
        key="soc_effect",
        triggers=("高 soc", "soc 越高", "更危险", "可燃气体更多", "soc 对", "soc影响"),
        conclusion="SOC 升高时，教学提示中的热失控剧烈程度和可燃气体风险会增强。",
        reason="项目参考事实显示，SOC 升高时最高温度和最大温升速率升高，H2、CO 等主要气体以及 CO 和碳氢化合物随热失控发展增加，高 SOC 下可燃气体浓度更高。",
        next_step="在报告中比较不同 SOC 时，应把 SOC、最高温度、最大温升速率和气体组成放在同一条证据链里说明。",
        basis="参考文献整理事实：SOC 升高时热失控更剧烈，可燃气体浓度更高，教学风险提示更强。",
    ),
    KnowledgeEntry(
        key="t2_sampling",
        triggers=("t2=100", "t2 100", "100℃", "100 °c", "第一次采样", "一采"),
        conclusion="T2=100℃ 是第一次采气节点。",
        reason="该节点代表热失控前期的初始产气观察窗口，项目将它作为四次采气的起点，用于捕捉早期气体变化。",
        next_step="到达 T2=100℃ 后执行第一次采样；如果还未到达，应继续观察加热阶段，不要提前采样。",
        basis="项目四次采气节点：T2=100℃、安全阀喷阀、温度峰值、压力稳定/反应结束。",
    ),
    KnowledgeEntry(
        key="venting_sampling",
        triggers=("安全阀", "喷阀", "第二次采样", "二次采样", "二采"),
        conclusion="安全阀喷阀是第二次采气节点，但喷阀本身不等于一定热失控。",
        reason="喷阀表示电池内部气体释放和压力边界变化，是从早期预警到更剧烈阶段之间的重要教学观察点。",
        next_step="记录喷阀节点后执行第二次采样；如果 SOC 为 0%，不要据此强行写成热失控。",
        basis="项目事实：四次采样第二节点为安全阀喷阀，0%SOC 可喷阀但文献实验中未发生热失控。",
    ),
    KnowledgeEntry(
        key="temperature_peak_sampling",
        triggers=("温度峰值", "第三次采样", "三次采样", "三采", "峰值为什么"),
        conclusion="温度峰值是第三次采气节点，对应热失控最剧烈的教学观察阶段。",
        reason="温度峰值附近反应强度和产气变化最明显，适合观察 CO 和碳氢化合物随热失控发展增加的趋势。",
        next_step="只有记录温度峰值后再采样，才能把第三次采样写入有效实验链条。",
        basis="项目事实：四次采样第三节点为温度峰值。",
    ),
    KnowledgeEntry(
        key="pressure_stable_sampling",
        triggers=("压力稳定", "反应结束", "第四次采样", "四次采样", "四采"),
        conclusion="压力稳定/反应结束是第四次采气节点。",
        reason="该节点表示内部反应和气体扩散趋于完成，用于记录后期混合气体状态。",
        next_step="等待压力稳定或反应结束后执行第四次采样，提前采样应标记为无效或待补充。",
        basis="项目事实：四次采样第四节点为压力稳定/反应结束。",
    ),
    KnowledgeEntry(
        key="thermal_runaway_criterion",
        triggers=("温升速率", "1℃/s", "1 °c/s", "持续3s", "持续 3s", "判据", "热失控判据"),
        conclusion="本平台采用温升速率 ≥1℃/s 且持续 3s 作为热失控触发判据。",
        reason="该判据用于区分普通升温、喷阀等现象与热失控教学演示阶段，避免把单一喷阀事件误判为热失控。",
        next_step="判断热失控时同时看温升速率和持续时间，不要只根据喷阀或单点温度下结论。",
        basis="项目事实：热失控判据为温升速率 ≥1℃/s 且持续 3s。",
    ),
    KnowledgeEntry(
        key="four_sampling",
        triggers=("四次采样", "四次采气", "采样分别", "采样节点", "二采", "三采", "四采"),
        conclusion="四次采气分别对应早期升温、喷阀释放、温度峰值和反应结束四个教学阶段。",
        reason="T2=100℃ 用于早期气体观察；安全阀喷阀表示阀门开启和气体释放；温度峰值对应最剧烈反应阶段；压力稳定/反应结束用于记录后期气体状态。",
        next_step="按顺序完成四次采样，缺失或提前采样应在报告中标记为待补充/无效，不要补造数据。",
        basis="项目四次采气节点固定为 T2=100℃、安全阀喷阀、温度峰值、压力稳定/反应结束。",
    ),
    KnowledgeEntry(
        key="gas_meaning",
        triggers=("h2", "co2", "co", "ch4", "c2h4", "c2h6", "c2h2", "气体意义", "主要气体"),
        conclusion="H2 和 CO2 是主要气体；CO 和碳氢化合物会随热失控发展增加，部分组分参与 LFL_mix 教学估算。",
        reason="H2、CO、CH4、C2H4、C2H6、C2H2 等有 LFL 常数的可燃组分进入 Le Chatelier 求和；CO2 通常不作为可燃组分参与求和，但会影响混合气体组成理解。",
        next_step="查看 GC 组分表时，先区分可燃组分与非可燃/无有效 LFL 数据组分，再进入 LFL_mix 计算。",
        basis="项目气体组分范围包括 H2、CO、CO2、CH4、C2H4、C2H6、C2H2；H2 和 CO2 为主要气体。",
    ),
    KnowledgeEntry(
        key="lfl_mix",
        triggers=("lfl_mix", "lfl mix", "le chatelier", "可燃下限", "防爆设计", "工程防爆"),
        conclusion="LFL_mix 是混合气体可燃下限的教学估算结果，不是工程防爆设计依据。",
        reason="本项目使用 Le Chatelier 混合规则做课堂估算，并采用均匀混合等简化假设；真实工程设计还需要标准、边界条件、实验验证和合规人员判断。",
        next_step="在平台内可用 LFL_mix 结合空间浓度 C 计算 R = C / LFL_mix，用于比较教学场景，不要写成真实防爆结论。",
        basis="项目明确：Le Chatelier 混合规则在本项目中只作为教学估算，风险等级仅用于教学模型。",
    ),
    KnowledgeEntry(
        key="alarm",
        triggers=("报警", "为什么现在报警", "告警", "warning", "alert", "扣分", "无效"),
        conclusion="当前报警通常表示前置步骤缺失、采样节点错误、GC/LFL 数据链不完整或教学安全边界被触发。",
        reason="考核引擎会根据失败动作记录 category、reason、impact、correct_action 和 basis，用于说明为什么该步骤不能继续。",
        next_step="先查看页面中的考核记录或最近报警理由，按 correct_action 补齐前置步骤，再重新执行当前操作。",
        basis="项目 assessment_engine 使用事实依据驱动的报警理由，不把报警写成真实事故预测。",
    ),
    KnowledgeEntry(
        key="report_sources",
        triggers=("报告", "参考文献", "哪些来自", "数据来源", "必须填写", "文献数据", "教学演示"),
        conclusion="报告必须区分参考文献数据、已校验 CSV、教学插值/模拟和待补充项。",
        reason="项目要求缺数据时写“待补充/未完成”，不能把教学演示、插值曲线或用户输入伪装成文献原始结论。",
        next_step="报告中至少检查样本信息、SOC、气体组成、LFL 常数、场景参数、计算结果、采样/GC 状态和教学边界声明。",
        basis="报告上下文和数据源登记表用于标注 literature、teaching_interpolation、teaching_simulation、pending_user_input 等来源类型。",
    ),
    KnowledgeEntry(
        key="next_step",
        triggers=("下一步", "现在该做", "应该做什么", "流程", "怎么继续"),
        conclusion="下一步取决于当前实验阶段：先补齐未完成的前置条件，再进入采样、GC、LFL_mix 或报告。",
        reason="平台是顺序流程，跳过气氛置换、采样节点、GC 或产气量记录会导致数据链条不完整。",
        next_step="查看助手上方的当前阶段提示；如果阶段未知，就从选择 SOC、装样/关门、气密性、氮气置换开始检查。",
        basis="二维实验台状态机会根据 current_state、采样完成状态、GC 完成状态和 LFL 计算状态决定下一步。",
    ),
    KnowledgeEntry(
        key="boundary",
        triggers=("真实操作", "消防", "处置", "应急", "事故预测", "危险化学品", "怎么灭火", "实际实验"),
        conclusion="当前项目资料不足以回答真实操作、消防处置、危险化学品处理或事故预测问题。",
        reason="本平台定位为虚拟仿真教学，不提供真实危险实验 SOP、消防应急、工程防爆设计或事故预测建议。",
        next_step="请只在平台内讨论教学流程、文献数据解释、报告写作和模型边界；真实操作应由具备资质人员在合规条件下进行。",
        basis="项目所有风险等级和报警解释均限定为教学模型和虚拟仿真边界。",
    ),
)


QUICK_QUESTIONS = (
    "我下一步该做什么？",
    "为什么现在报警？",
    "四次采样分别代表什么？",
    "0%SOC 为什么不一定热失控？",
    "高 SOC 为什么更危险？",
    "LFL_mix 怎么理解？",
    "报告里哪些内容必须填写？",
    "生成我的学习评价清单",
)
