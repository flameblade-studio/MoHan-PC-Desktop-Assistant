from __future__ import annotations

lazy from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AzureSpeechRegion:
    identifier: str
    traditional_chinese: str
    simplified_chinese: str
    english: str
    japanese: str
    supports_hd: bool = False
    supports_hd_flash: bool = False

    def label(self, language: str) -> str:
        normalized = str(language or "").strip().lower()
        if normalized == "zh-cn":
            name = self.simplified_chinese
        elif normalized in {"en", "en-us"}:
            name = self.english
        elif normalized in {"ja", "ja-jp"}:
            name = self.japanese
        else:
            name = self.traditional_chinese
        return f"{name} · {self.identifier}"


AZURE_SPEECH_REGIONS: tuple[AzureSpeechRegion, ...] = (
    AzureSpeechRegion("eastasia", "東亞", "东亚", "East Asia", "東アジア"),
    AzureSpeechRegion(
        "southeastasia",
        "東南亞",
        "东南亚",
        "Southeast Asia",
        "東南アジア",
        True,
        True,
    ),
    AzureSpeechRegion(
        "australiaeast",
        "澳洲東部",
        "澳大利亚东部",
        "Australia East",
        "オーストラリア東部",
    ),
    AzureSpeechRegion(
        "centralindia",
        "印度中部",
        "印度中部",
        "Central India",
        "インド中部",
        True,
    ),
    AzureSpeechRegion(
        "japaneast", "日本東部", "日本东部", "Japan East", "東日本"
    ),
    AzureSpeechRegion(
        "japanwest", "日本西部", "日本西部", "Japan West", "西日本"
    ),
    AzureSpeechRegion(
        "koreacentral",
        "韓國中部",
        "韩国中部",
        "Korea Central",
        "韓国中部",
    ),
    AzureSpeechRegion(
        "southafricanorth",
        "南非北部",
        "南非北部",
        "South Africa North",
        "南アフリカ北部",
    ),
    AzureSpeechRegion(
        "canadacentral",
        "加拿大中部",
        "加拿大中部",
        "Canada Central",
        "カナダ中部",
        True,
    ),
    AzureSpeechRegion(
        "canadaeast",
        "加拿大東部",
        "加拿大东部",
        "Canada East",
        "カナダ東部",
    ),
    AzureSpeechRegion(
        "northeurope", "北歐", "北欧", "North Europe", "北ヨーロッパ"
    ),
    AzureSpeechRegion(
        "westeurope", "西歐", "西欧", "West Europe", "西ヨーロッパ", True, True
    ),
    AzureSpeechRegion(
        "francecentral",
        "法國中部",
        "法国中部",
        "France Central",
        "フランス中部",
        True,
    ),
    AzureSpeechRegion(
        "germanywestcentral",
        "德國中西部",
        "德国中西部",
        "Germany West Central",
        "ドイツ中西部",
    ),
    AzureSpeechRegion(
        "italynorth",
        "義大利北部",
        "意大利北部",
        "Italy North",
        "イタリア北部",
    ),
    AzureSpeechRegion(
        "norwayeast",
        "挪威東部",
        "挪威东部",
        "Norway East",
        "ノルウェー東部",
    ),
    AzureSpeechRegion(
        "swedencentral",
        "瑞典中部",
        "瑞典中部",
        "Sweden Central",
        "スウェーデン中部",
        True,
    ),
    AzureSpeechRegion(
        "switzerlandnorth",
        "瑞士北部",
        "瑞士北部",
        "Switzerland North",
        "スイス北部",
    ),
    AzureSpeechRegion(
        "switzerlandwest",
        "瑞士西部",
        "瑞士西部",
        "Switzerland West",
        "スイス西部",
    ),
    AzureSpeechRegion(
        "uksouth", "英國南部", "英国南部", "UK South", "英国南部"
    ),
    AzureSpeechRegion(
        "ukwest", "英國西部", "英国西部", "UK West", "英国西部"
    ),
    AzureSpeechRegion(
        "uaenorth",
        "阿拉伯聯合大公國北部",
        "阿拉伯联合酋长国北部",
        "UAE North",
        "アラブ首長国連邦北部",
    ),
    AzureSpeechRegion(
        "brazilsouth",
        "巴西南部",
        "巴西南部",
        "Brazil South",
        "ブラジル南部",
    ),
    AzureSpeechRegion(
        "qatarcentral",
        "卡達中部",
        "卡塔尔中部",
        "Qatar Central",
        "カタール中部",
    ),
    AzureSpeechRegion(
        "centralus", "美國中部", "美国中部", "Central US", "米国中部"
    ),
    AzureSpeechRegion(
        "eastus", "美國東部", "美国东部", "East US", "米国東部", True, True
    ),
    AzureSpeechRegion(
        "eastus2", "美國東部 2", "美国东部 2", "East US 2", "米国東部 2", True
    ),
    AzureSpeechRegion(
        "northcentralus",
        "美國中北部",
        "美国中北部",
        "North Central US",
        "米国中北部",
    ),
    AzureSpeechRegion(
        "southcentralus",
        "美國中南部",
        "美国中南部",
        "South Central US",
        "米国中南部",
    ),
    AzureSpeechRegion(
        "westcentralus",
        "美國中西部",
        "美国中西部",
        "West Central US",
        "米国中西部",
    ),
    AzureSpeechRegion(
        "westus", "美國西部", "美国西部", "West US", "米国西部"
    ),
    AzureSpeechRegion(
        "westus2", "美國西部 2", "美国西部 2", "West US 2", "米国西部 2", True
    ),
    AzureSpeechRegion(
        "westus3", "美國西部 3", "美国西部 3", "West US 3", "米国西部 3"
    ),
)


def azure_region_options(
    language: str,
    *,
    hd_only: bool = False,
    hd_flash_only: bool = False,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (region.label(language), region.identifier)
        for region in AZURE_SPEECH_REGIONS
        if (not hd_only or region.supports_hd)
        and (not hd_flash_only or region.supports_hd_flash)
    )


def azure_region_identifiers(
    *,
    hd_only: bool = False,
    hd_flash_only: bool = False,
) -> tuple[str, ...]:
    return tuple(
        region.identifier
        for region in AZURE_SPEECH_REGIONS
        if (not hd_only or region.supports_hd)
        and (not hd_flash_only or region.supports_hd_flash)
    )


def azure_region_supports_hd_flash(identifier: str) -> bool:
    normalized = str(identifier or "").strip().lower()
    return any(
        region.identifier == normalized and region.supports_hd_flash
        for region in AZURE_SPEECH_REGIONS
    )
