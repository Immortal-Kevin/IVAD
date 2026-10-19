# P3.7-D 同法人内部交付门禁

日期：2026-10-19。用户已确认公司同法人研发部内部演示授权及空白软件交付要求；这些前提本轮无需再次确认。**SAME_ENTITY_INTERNAL_DELIVERY_STATUS=BLOCKED。不能发送本轮研究目录或历史Lite包代替成品。**

| 状态项 | 本轮判定 |
|---|---|
| BUILD_STATUS | BLOCKED_D2_NO_EXE |
| LOCAL_FUNCTIONAL_STATUS | NOT_TESTED_CANDIDATE；源码14项PASS仅参考 |
| VIDEO_IMPORT_EXTRACTION_STATUS | NOT_TESTED_CANDIDATE；合成共享FFmpeg CLI解码/抽帧PASS仅原型 |
| RF_3050TI_COMPATIBILITY_STATUS | NOT_TESTED；TARGET_3050TI=NOT TESTED |
| LICENSE_PAYLOAD_STATUS | BLOCKED |
| CONFIDENTIALITY_STATUS | NOT_TESTED_PAYLOAD；原资产保护另验 |
| SAME_ENTITY_INTERNAL_DELIVERY_STATUS | BLOCKED，未APPROVED |
| DISTRIBUTION_STATUS | BLOCKED，未GENERAL_DISTRIBUTION_APPROVED |
| PACKAGING_FREEZE | TRUE，已恢复；下一次打包需重新获得用户授权 |

## 具体缺项和责任

| 编号 | 阻断/缺证据 | 解除所需的具体工作 |
|---|---|---|
| D-B01 | 未确认拟采用FFmpeg DLL及静态依赖的完整再分发履约材料 | 开发方取得固定版本/补丁/构建脚本/各静态依赖准确源码与通知，或制作可完整提供材料的最小LGPL共享构建；不靠重命名规避 |
| D-B02 | PyAV尚未链接到该构建；片段编码VFR原型失败 | 开发方完成链接和免费编码路径，校验H.264导入/播放/片段/抽帧/PTS/异常处理；若必须改变格式/精度，先提交实际影响供用户决定 |
| D-B03 | Qt对应源码已准备，但最终模块/复合通知/兼容替换未实测 | 开发方白名单构建，附准确源码/修改声明/许可证/安装说明，在独立副本合法替换兼容DLL后真实EXE启动和退出。不需购买Qt商业版才能继续研究 |
| D-B04 | 便携RF Worker及NVIDIA逐DLL再分发未闭合；4GB门控未实现 | 开发方确定最小Worker和每个CUDA/cuDNN来源/SHA/EULA/redistributable/通知，落实GPU/新鲜显存门控与中文禁用原因；无CPU AI回退，保留基础功能。不能把未经批准删掉Worker的Lite包称为完整P37D |
| D-B05 | 没有候选，无法做干净首启、动态依赖/回退/联网/保密扫描 | 上述门禁闭合后再构建BUILD_CANDIDATE，按全部P0/P1流程真实运行，记录模块/DLL，检查最终所有文件及PYZ，产出SHA清单和实际中文指南 |
| D-B06 | 未访问3050Ti笔记本 | 用户/公司提供OS、驱动、权限、空间和受控测试窗口；目标机未测本身须保持NOT TESTED。若最终仅交付已验收非AI基础功能且AI明确门控，是否可内部交付另按具体证据判定，不能预批准 |
| D-B07 | 编码专利适用性未具体审阅 | 公司结合实际地区/用途审阅所选codec的独立权利条件；不是自动要求购买许可，更不能由“同法人”推导所有runtime可发 |

本轮停止的直接依据是用户第14节第三方DLL再分发权利无法确认，及第11节D2先于D3的顺序。并未证明所有免费方案失败，亦未证明需付费、公开私有数据或改全局环境。工程待办由开发方完成，不将“把材料写成报告”替代实际整改。用户当前无需购买许可证；最明确需用户协助的是目标机信息/访问，以及将来有具体编码限制时的选择。

仅当上述适用于本次范围的许可、保密和必要功能证据闭合，才可新建标记可交付的最终目录并将同法人状态改APPROVED。目标机AI未通过时禁用AI并明确原因，不能阻止视频抽帧/标注；是否满足内部交付需评估最终基础功能与限制，不能把未测试设备填PASS。本轮没有这样的成品或批准。
