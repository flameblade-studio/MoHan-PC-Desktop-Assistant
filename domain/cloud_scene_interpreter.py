from __future__ import annotations

lazy import re
lazy from dataclasses import dataclass
lazy from enum import StrEnum

lazy from domain.vision_domain import (
    IdentityObservation,
    IdentityState,
    SceneUnderstanding,
)
lazy from domain.vision_provider_contracts import (
    ClaimStatus,
    VisionProviderResult,
    VisualClaim,
)


class SceneFactKind(StrEnum):
    PERSON = "person"
    SCENE = "scene"
    OBJECT = "object"
    ACTIVITY = "activity"


class SceneFactStatus(StrEnum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class InteractionCandidateKind(StrEnum):
    COMMENT = "comment"
    OFFER_LOOKUP = "offer_lookup"


@dataclass(frozen=True, slots=True)
class SceneFact:
    kind: SceneFactKind
    label: str
    status: SceneFactStatus
    confidence: float
    source: str = "openai_vision"


@dataclass(frozen=True, slots=True)
class LocalizedInteractionCandidate:
    kind: InteractionCandidateKind
    text_key: str
    arguments: tuple[tuple[str, str], ...]
    confidence: float
    requires_user_action: bool = False


@dataclass(frozen=True, slots=True)
class CloudSceneInterpretation:
    operation_id: int
    increment: SceneUnderstanding
    facts: tuple[SceneFact, ...]
    interaction_candidates: tuple[LocalizedInteractionCandidate, ...]
    suppressed_claims: int


@dataclass(frozen=True, slots=True)
class MergedSceneUnderstanding:
    scene: SceneUnderstanding
    observed_at: float
    cloud_facts: tuple[SceneFact, ...]
    interaction_candidates: tuple[LocalizedInteractionCandidate, ...]


_GENERIC_LABELS: dict[str, tuple[SceneFactKind, tuple[str, ...]]] = {
    "at_computer": (SceneFactKind.ACTIVITY, ("using a computer", "at a computer")),
    "possible_reading": (SceneFactKind.ACTIVITY, ("reading", "閱讀", "阅读", "読書")),
    "possible_drinking": (SceneFactKind.ACTIVITY, ("drinking", "喝水", "飲用", "饮用")),
    "person": (SceneFactKind.PERSON, ("person", "people", "human figure", "人物", "人影")),
    "book": (SceneFactKind.OBJECT, ("book", "books", "書本", "书本", "本")),
    "cup": (SceneFactKind.OBJECT, ("cup", "mug", "杯子", "カップ")),
    "bottle": (SceneFactKind.OBJECT, ("bottle", "瓶子", "ボトル")),
    "laptop": (SceneFactKind.OBJECT, ("laptop", "notebook computer", "筆電", "笔记本电脑", "ノートパソコン")),
    "keyboard": (SceneFactKind.OBJECT, ("keyboard", "鍵盤", "键盘", "キーボード")),
    "phone": (SceneFactKind.OBJECT, ("phone", "mobile phone", "cell phone", "手機", "手机", "スマートフォン")),
    "desk": (SceneFactKind.OBJECT, ("desk", "table", "桌子", "机", "テーブル")),
    "chair": (SceneFactKind.OBJECT, ("chair", "椅子", "椅子")),
    "indoor": (SceneFactKind.SCENE, ("indoors", "indoor", "room", "室內", "室内", "屋内")),
    "outdoor": (SceneFactKind.SCENE, ("outdoors", "outdoor", "戶外", "户外", "屋外")),
}
_SENSITIVE_OR_EXACT = re.compile(
    r"\b(?:identity|identified|recognized|named|name is|brand|model number|"
    r"book title|title is|author|ethnicity|race|religion|health|medical|"
    r"political|sexual orientation|address|license plate)\b|"
    r"(?:身分|身份|姓名|名為|名为|品牌|型號|型号|書名|书名|作者|"
    r"種族|种族|宗教|健康|醫療|医疗|政治|性傾向|性倾向|地址|車牌|车牌|"
    r"氏名|名前|ブランド|型番|書名|著者|人種|宗教|健康|医療|政治|住所|ナンバー)|"
    r"[\"“”「」『』]",
    re.IGNORECASE,
)
_LOOKUP_LANGUAGE = re.compile(
    r"\b(?:brand|model|title|book|product|logo|which|what is)\b|"
    r"(?:品牌|型號|型号|書名|书名|產品|产品|標誌|标志|查詢|查询|"
    r"ブランド|型番|書名|製品|ロゴ|調べ)",
    re.IGNORECASE,
)
_OBSERVED_MINIMUM = 0.75
_INFERRED_MINIMUM = 0.85


class CloudSceneInterpreter:
    """Convert model-reported claims into conservative provider-neutral context."""

    def interpret(self, result: object) -> CloudSceneInterpretation:
        if not isinstance(result, VisionProviderResult) or not result.succeeded:
            return _empty_interpretation(_operation_id(result))
        understanding = result.understanding
        if understanding is None:
            return _empty_interpretation(result.operation_id)
        facts: list[SceneFact] = []
        candidates: list[LocalizedInteractionCandidate] = []
        suppressed = 0
        seen: set[tuple[SceneFactKind, str, SceneFactStatus]] = set()
        lookup_suggested = False
        for claim in understanding.claims:
            fact = _fact_from_claim(claim)
            if fact is None:
                suppressed += 1
                if _may_need_lookup(claim) and not lookup_suggested:
                    candidates.append(_lookup_candidate())
                    lookup_suggested = True
                continue
            signature = (fact.kind, fact.label, fact.status)
            if signature in seen:
                continue
            seen.add(signature)
            facts.append(fact)
            candidate = _interaction_candidate(fact)
            if candidate is not None:
                candidates.append(candidate)
        increment = SceneUnderstanding(
            IdentityObservation(IdentityState.UNKNOWN),
            (),
            tuple(_activity_code(fact) for fact in facts if _is_activity(fact)),
            tuple(_uncertainty_code(fact) for fact in facts if _is_uncertain(fact)),
        )
        return CloudSceneInterpretation(
            result.operation_id,
            increment,
            tuple(facts),
            tuple(candidates),
            suppressed,
        )

    def merge(
        self,
        local_scene: SceneUnderstanding,
        *,
        local_observed_at: float,
        cloud: CloudSceneInterpretation,
    ) -> MergedSceneUnderstanding:
        if not isinstance(local_scene, SceneUnderstanding):
            raise TypeError("Local scene must be strongly typed.")
        if not isinstance(cloud, CloudSceneInterpretation):
            raise TypeError("Cloud scene interpretation must be strongly typed.")
        local_labels = {
            detection.label.casefold(): detection.confidence
            for detection in local_scene.objects
        }
        cloud_facts = tuple(
            fact
            for fact in cloud.facts
            if not (
                fact.kind is SceneFactKind.OBJECT
                and local_labels.get(fact.label.casefold(), -1.0) >= fact.confidence
            )
        )
        cloud_activities = tuple(
            _activity_code(fact)
            for fact in cloud_facts
            if _is_activity(fact)
        )
        cloud_uncertainty = tuple(
            _uncertainty_code(fact)
            for fact in cloud_facts
            if _is_uncertain(fact)
        )
        merged = SceneUnderstanding(
            local_scene.identity,
            local_scene.objects,
            _ordered_unique((*local_scene.activities, *cloud_activities)),
            _ordered_unique((*local_scene.uncertainty, *cloud_uncertainty)),
        )
        allowed_labels = {(fact.kind.value, fact.label) for fact in cloud_facts}
        candidates = tuple(
            candidate
            for candidate in cloud.interaction_candidates
            if candidate.kind is InteractionCandidateKind.OFFER_LOOKUP
            or (
                ("kind", candidate.arguments[0][1]) in candidate.arguments
                and (candidate.arguments[0][1], candidate.arguments[1][1]) in allowed_labels
            )
        )
        return MergedSceneUnderstanding(
            merged,
            float(local_observed_at),
            cloud_facts,
            candidates,
        )


def _fact_from_claim(claim: VisualClaim) -> SceneFact | None:
    if not isinstance(claim, VisualClaim):
        return None
    if _SENSITIVE_OR_EXACT.search(f"{claim.text} {claim.evidence}"):
        return None
    minimum = (
        _OBSERVED_MINIMUM
        if claim.status is ClaimStatus.OBSERVED
        else _INFERRED_MINIMUM
    )
    if claim.status is ClaimStatus.UNCERTAIN or claim.confidence < minimum:
        return None
    matched = _match_generic_label(f"{claim.text} {claim.evidence}")
    if matched is None:
        return None
    label, (kind, _terms) = matched
    status = (
        SceneFactStatus.OBSERVED
        if claim.status is ClaimStatus.OBSERVED
        else SceneFactStatus.INFERRED
    )
    return SceneFact(kind, label, status, claim.confidence)


def _match_generic_label(
    text: str,
) -> tuple[str, tuple[SceneFactKind, tuple[str, ...]]] | None:
    normalized = text.casefold()
    for label, specification in _GENERIC_LABELS.items():
        if any(_contains_term(normalized, term) for term in specification[1]):
            return label, specification
    return None


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


def _interaction_candidate(
    fact: SceneFact,
) -> LocalizedInteractionCandidate | None:
    if fact.status is not SceneFactStatus.OBSERVED:
        return None
    return LocalizedInteractionCandidate(
        InteractionCandidateKind.COMMENT,
        f"cloud_scene.observed_{fact.kind.value}",
        (("kind", fact.kind.value), ("label", fact.label)),
        fact.confidence,
    )


def _lookup_candidate() -> LocalizedInteractionCandidate:
    return LocalizedInteractionCandidate(
        InteractionCandidateKind.OFFER_LOOKUP,
        "cloud_scene.offer_lookup",
        (),
        1.0,
        True,
    )


def _may_need_lookup(claim: VisualClaim) -> bool:
    return bool(
        claim.status is not ClaimStatus.UNCERTAIN
        and claim.confidence >= _OBSERVED_MINIMUM
        and _LOOKUP_LANGUAGE.search(claim.text)
    )


def _is_activity(fact: SceneFact) -> bool:
    return fact.kind is SceneFactKind.ACTIVITY


def _is_uncertain(fact: SceneFact) -> bool:
    return fact.status is not SceneFactStatus.OBSERVED


def _activity_code(fact: SceneFact) -> str:
    return fact.label


def _uncertainty_code(fact: SceneFact) -> str:
    return f"cloud_{fact.label}_not_confirmed"


def _ordered_unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _operation_id(result: object) -> int:
    value = getattr(result, "operation_id", 0)
    return value if type(value) is int and value >= 0 else 0


def _empty_interpretation(operation_id: int) -> CloudSceneInterpretation:
    return CloudSceneInterpretation(
        operation_id,
        SceneUnderstanding(IdentityObservation(IdentityState.UNKNOWN), (), (), ()),
        (),
        (),
        0,
    )
