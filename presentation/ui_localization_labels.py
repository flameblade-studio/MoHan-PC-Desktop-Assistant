"""Display-label tables for the desktop UI (English and Simplified Chinese).

Split out of ``ui_localization`` so that module stays inside the layer-module
line ratchet; ``ui_localization`` re-exports every table unchanged.
"""

from __future__ import annotations

lazy from collections.abc import Mapping

MODE_LABELS: Mapping[str, str] = frozendict(
{'工作': 'Work',
 '陪伴': 'Companion',
 '勿擾': 'Do not disturb',
 '會議': 'Meeting',
 '離席': 'Away',
 '休眠': 'Sleep'}
)

WORK_TYPE_LABELS: Mapping[str, str] = frozendict(
{'一般辦公／行政': 'General office / administration',
 '專案管理': 'Project management',
 '自由工作者／接案': 'Freelance / contract work',
 '創作／內容工作': 'Creative / content work',
 '軟體開發／技術': 'Software development / technology',
 '教育／研究': 'Education / research',
 '銷售／客戶服務': 'Sales / customer service',
 '其他（可自行輸入）': 'Other (enter your own)'}
)

PLATFORM_STATUS_LABELS: Mapping[str, str] = frozendict(
{'尚未開始': 'Not started',
 '準備資料': 'Preparing materials',
 '進行中': 'In progress',
 '待送出': 'Ready to submit',
 '等待回覆': 'Waiting for response',
 '審核中': 'Under review',
 '需修正': 'Needs revision',
 '已排程': 'Scheduled',
 '已完成': 'Completed',
 '已上架': 'Published',
 '暫停': 'Paused'}
)

MEMORY_CATEGORY_LABELS: Mapping[str, str] = frozendict(
{'人物': 'People',
 '偏好': 'Preferences',
 '目標': 'Goals',
 '工作流程': 'Workflows',
 '重要日期': 'Important dates',
 '其他': 'Other'}
)

SIMPLIFIED_MODE_LABELS: Mapping[str, str] = frozendict(
{'工作': '工作', '陪伴': '陪伴', '勿擾': '勿扰', '會議': '会议', '離席': '离席', '休眠': '休眠'}
)

SIMPLIFIED_WORK_TYPE_LABELS: Mapping[str, str] = frozendict(
{'一般辦公／行政': '一般办公／行政',
 '專案管理': '项目管理',
 '自由工作者／接案': '自由职业／承接项目',
 '創作／內容工作': '创作／内容工作',
 '軟體開發／技術': '软件开发／技术',
 '教育／研究': '教育／研究',
 '銷售／客戶服務': '销售／客户服务',
 '其他（可自行輸入）': '其他（可自行输入）'}
)

SIMPLIFIED_PLATFORM_STATUS_LABELS: Mapping[str, str] = frozendict(
{'尚未開始': '尚未开始',
 '準備資料': '准备资料',
 '進行中': '进行中',
 '待送出': '待提交',
 '等待回覆': '等待回复',
 '審核中': '审核中',
 '需修正': '需修改',
 '已排程': '已排期',
 '已完成': '已完成',
 '已上架': '已发布',
 '暫停': '暂停'}
)

SIMPLIFIED_MEMORY_CATEGORY_LABELS: Mapping[str, str] = frozendict(
{'人物': '人物', '偏好': '偏好', '目標': '目标', '工作流程': '工作流程', '重要日期': '重要日期', '其他': '其他'}
)

__all__ = (
    "MEMORY_CATEGORY_LABELS",
    "MODE_LABELS",
    "PLATFORM_STATUS_LABELS",
    "SIMPLIFIED_MEMORY_CATEGORY_LABELS",
    "SIMPLIFIED_MODE_LABELS",
    "SIMPLIFIED_PLATFORM_STATUS_LABELS",
    "SIMPLIFIED_WORK_TYPE_LABELS",
    "WORK_TYPE_LABELS",
)
