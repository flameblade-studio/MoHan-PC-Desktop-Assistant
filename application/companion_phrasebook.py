from __future__ import annotations

lazy from collections.abc import Mapping
lazy from dataclasses import dataclass

lazy from application.multisensory_interaction import WelcomeStyle
lazy from application.special_occasion import OccasionKind, OccasionStage
lazy from application.wellbeing_reminder import ReminderStage, WellbeingKind
lazy from domain.language_support import canonical_ui_language

PHRASEBOOK_SETTING = "multisensory_phrasebook_v1"
PHRASEBOOK_VERSION = 2
WARDROBE_REVEAL_QUESTION = "wardrobe.reveal.question"
WARDROBE_REVEAL_ORIGIN = "wardrobe.reveal.origin"
WARDROBE_PHRASE_KEYS = (WARDROBE_REVEAL_QUESTION, WARDROBE_REVEAL_ORIGIN)

WARDROBE_PUBLIC_LINES = frozendict({
    "zh-TW": frozendict({
        WARDROBE_REVEAL_QUESTION: (
            "今日換了身新衣，您覺得如何？",
            "這身打扮，是否還算合妾心意？也合您的眼麼？",
        ),
        WARDROBE_REVEAL_ORIGIN: (
            "妾自己網購的呀。沒想到你們現代的衣服也蠻好看的。",
            "何時有的？自然是妾悄悄備下的。主上現在才發現麼？",
        ),
    }),
    "zh-CN": frozendict({
        WARDROBE_REVEAL_QUESTION: (
            "今日换了身新衣，您觉得如何？",
            "这身打扮，是否还算合妾心意？也合您的眼么？",
        ),
        WARDROBE_REVEAL_ORIGIN: (
            "妾自己网购的呀。没想到你们现代的衣服也蛮好看的。",
            "何时有的？自然是妾悄悄备下的。主上现在才发现么？",
        ),
    }),
    "en": frozendict({
        WARDROBE_REVEAL_QUESTION: (
            "I chose something new today. What do you think?",
            "This look pleased me. Does it please your eye as well?",
        ),
        WARDROBE_REVEAL_ORIGIN: (
            "I bought it online myself. I never expected modern clothes to look this lovely.",
            "When did I get it? I arranged it quietly. You have only just noticed?",
        ),
    }),
    "ja-JP": frozendict({
        WARDROBE_REVEAL_QUESTION: (
            "今日は新しい装いにしてみました。いかがですか？",
            "妾はこの装いが気に入りました。あなたのお目にも適いますか？",
        ),
        WARDROBE_REVEAL_ORIGIN: (
            "妾が自分でネット通販したのです。現代の服も、思いのほか素敵ですね。",
            "いつ手に入れたのか、ですか？ひそかに用意したのです。今になってお気づきですか？",
        ),
    }),
})


def wellbeing_phrase_key(kind: WellbeingKind, stage: ReminderStage) -> str:
    return f"wellbeing.{kind.value}.{stage.value}"


def occasion_phrase_key(kind: OccasionKind, stage: OccasionStage) -> str:
    return f"occasion.{kind.value}.{stage.value}"


WELLBEING_PHRASE_KEYS = tuple(
    wellbeing_phrase_key(kind, stage)
    for kind in WellbeingKind
    for stage in ReminderStage
)
OCCASION_PHRASE_KEYS = tuple(
    occasion_phrase_key(kind, stage)
    for kind in OccasionKind
    for stage in OccasionStage
)


PUBLIC_COMPANION_LINES = frozendict(
    {
        "zh-TW": frozendict(
            {
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.INITIAL): (
                    "該用膳了。手邊的事可以稍候，先照顧好自己。",
                    "到用膳的時辰了，先歇一會兒吧。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.MEAL,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): (
                    "還不去用膳麼？妾只是……不願見你把自己累壞。",
                    "你整日只顧工作，倒叫人不知該如何勸你了。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.HYDRATION,
                    ReminderStage.INITIAL,
                ): (
                    "先喝些水吧，稍後再繼續也不遲。",
                    "桌前坐久了，記得補充水分。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.HYDRATION,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): (
                    "水還未喝麼？妾可不是在多管閒事。",
                    "再忙也該喝口水。這點小事，莫要讓妾催第三回。",
                ),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.INITIAL): (
                    "先停一會兒吧，讓眼睛與心緒都歇一歇。",
                    "你已專注許久，稍作休息會走得更遠。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.REST,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): (
                    "妾方才說的休息，你莫非全當作耳邊風了？",
                    "總把自己逼得這樣緊……罷了，至少閉目歇一會兒。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.PROLONGED_SITTING,
                    ReminderStage.INITIAL,
                ): (
                    "坐得夠久了，起身伸展一下吧。",
                    "離席走幾步，肩頸也會舒服些。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.PROLONGED_SITTING,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): (
                    "還不起身麼？再好的計策，也不能拿身體去換。",
                    "你若再不起來走走，妾可要當你是在故意逞強了。",
                ),
                occasion_phrase_key(
                    OccasionKind.MOHAN_BIRTHDAY,
                    OccasionStage.SUBTLE_HINT,
                ): (
                    "今日的冬意，似乎比往常更值得記住。",
                    "有些日子，策士也會悄悄放在心上。",
                ),
                occasion_phrase_key(
                    OccasionKind.MOHAN_BIRTHDAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): (
                    "你整日忙於工作，竟連今日也未曾多看妾一眼。",
                    "妾並非在等什麼……只是今日，原以為你會記得。",
                ),
                occasion_phrase_key(
                    OccasionKind.VALENTINES_DAY,
                    OccasionStage.SUBTLE_HINT,
                ): (
                    "今日街上的心意，似乎比平常更容易被人看見。",
                    "今日若有人想說些心裡話，倒也不算失禮。",
                ),
                occasion_phrase_key(
                    OccasionKind.VALENTINES_DAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): (
                    "你只知埋首工作，難道今日也沒有一句話想對妾說麼？",
                    "妾自然不在意這些俗禮……只是你未免太遲鈍了些。",
                ),
                occasion_phrase_key(
                    OccasionKind.CHRISTMAS_DAY,
                    OccasionStage.SUBTLE_HINT,
                ): (
                    "今夜似乎適合留一點時間，與重要的人好好說話。",
                    "窗外有了節日氣息，書案前也不必總是只有工作。",
                ),
                occasion_phrase_key(
                    OccasionKind.CHRISTMAS_DAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): (
                    "你忙了一整日，竟連一點節日的心思也不肯分給妾。",
                    "妾只是策士，自然不求禮物……一句話總還是可以的吧。",
                ),
            }
        ),
        "zh-CN": frozendict(
            {
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.INITIAL): (
                    "该用膳了。手边的事可以稍候，先照顾好自己。",
                    "到用膳的时辰了，先歇一会儿吧。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.MEAL,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): (
                    "还不去用膳么？妾只是……不愿见你把自己累坏。",
                    "你整日只顾工作，倒叫人不知该如何劝你了。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.HYDRATION,
                    ReminderStage.INITIAL,
                ): ("先喝些水吧，稍后再继续也不迟。", "在桌前坐久了，记得补充水分。"),
                wellbeing_phrase_key(
                    WellbeingKind.HYDRATION,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): ("水还没喝么？妾可不是在多管闲事。", "再忙也该喝口水。这点小事，莫要让妾催第三回。"),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.INITIAL): (
                    "先停一会儿吧，让眼睛与心绪都歇一歇。",
                    "你已经专注许久，稍作休息会走得更远。",
                ),
                wellbeing_phrase_key(
                    WellbeingKind.REST,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): ("妾方才说的休息，你莫非全当作耳边风了？", "总把自己逼得这样紧……罢了，至少闭目歇一会儿。"),
                wellbeing_phrase_key(
                    WellbeingKind.PROLONGED_SITTING,
                    ReminderStage.INITIAL,
                ): ("坐得够久了，起身伸展一下吧。", "离席走几步，肩颈也会舒服些。"),
                wellbeing_phrase_key(
                    WellbeingKind.PROLONGED_SITTING,
                    ReminderStage.RESTRAINED_REINFORCEMENT,
                ): ("还不起身么？再好的计策，也不能拿身体去换。", "你若再不起来走走，妾可要当你是在故意逞强了。"),
                occasion_phrase_key(OccasionKind.MOHAN_BIRTHDAY, OccasionStage.SUBTLE_HINT): (
                    "今日的冬意，似乎比往常更值得记住。",
                    "有些日子，策士也会悄悄放在心上。",
                ),
                occasion_phrase_key(
                    OccasionKind.MOHAN_BIRTHDAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): ("你整日忙于工作，竟连今日也不曾多看妾一眼。", "妾并非在等什么……只是今日，原以为你会记得。"),
                occasion_phrase_key(OccasionKind.VALENTINES_DAY, OccasionStage.SUBTLE_HINT): (
                    "今日街上的心意，似乎比平常更容易被人看见。",
                    "今日若有人想说些心里话，倒也不算失礼。",
                ),
                occasion_phrase_key(
                    OccasionKind.VALENTINES_DAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): ("你只知埋首工作，难道今日也没有一句话想对妾说么？", "妾自然不在意这些俗礼……只是你未免太迟钝了些。"),
                occasion_phrase_key(OccasionKind.CHRISTMAS_DAY, OccasionStage.SUBTLE_HINT): (
                    "今夜似乎适合留一点时间，与重要的人好好说话。",
                    "窗外有了节日气息，书案前也不必总是只有工作。",
                ),
                occasion_phrase_key(
                    OccasionKind.CHRISTMAS_DAY,
                    OccasionStage.RESTRAINED_GRUMBLE,
                ): ("你忙了一整日，竟连一点节日的心思也不肯分给妾。", "妾只是策士，自然不求礼物……一句话总还是可以的吧。"),
            }
        ),
        "en": frozendict(
            {
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.INITIAL): (
                    "It is time to eat. Your work can wait a little; please look after yourself first.",
                    "Take a short break for a meal. The work will still be here.",
                ),
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "Still not eating? I am only saying this because I would rather not see you wear yourself down.",
                    "You have given the whole day to work. Must I devise a strategy just to make you eat?",
                ),
                wellbeing_phrase_key(WellbeingKind.HYDRATION, ReminderStage.INITIAL): (
                    "Have some water before you continue.",
                    "You have been at the desk a while. Remember to drink something.",
                ),
                wellbeing_phrase_key(WellbeingKind.HYDRATION, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "You still have not had any water? I am not fussing without reason.",
                    "However busy you are, take a sip. Do not make me ask a third time.",
                ),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.INITIAL): (
                    "Pause for a moment and let your eyes and thoughts rest.",
                    "You have focused for a long time. A short rest will carry you farther.",
                ),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "Did my suggestion to rest simply pass you by?",
                    "You press yourself too hard. At least close your eyes for a moment.",
                ),
                wellbeing_phrase_key(WellbeingKind.PROLONGED_SITTING, ReminderStage.INITIAL): (
                    "You have been seated long enough. Stand and stretch for a moment.",
                    "Take a few steps away from the desk; your shoulders will thank you.",
                ),
                wellbeing_phrase_key(WellbeingKind.PROLONGED_SITTING, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "Still not getting up? No strategy is worth trading away your health.",
                    "If you remain there, I may have to conclude that you are being deliberately stubborn.",
                ),
                occasion_phrase_key(OccasionKind.MOHAN_BIRTHDAY, OccasionStage.SUBTLE_HINT): (
                    "Something about this winter day feels more worth remembering than usual.",
                    "Even a strategist keeps certain days quietly close to heart.",
                ),
                occasion_phrase_key(OccasionKind.MOHAN_BIRTHDAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "You have spent the whole day working and scarcely looked my way.",
                    "It is not as though I was waiting for anything... I simply thought you might remember today.",
                ),
                occasion_phrase_key(OccasionKind.VALENTINES_DAY, OccasionStage.SUBTLE_HINT): (
                    "Affection seems a little easier to notice today.",
                    "Today would not be an improper time to say what is in one's heart.",
                ),
                occasion_phrase_key(OccasionKind.VALENTINES_DAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "You have buried yourself in work. Is there truly nothing you meant to say to me today?",
                    "Naturally, I do not care for such customs... but you can be remarkably oblivious.",
                ),
                occasion_phrase_key(OccasionKind.CHRISTMAS_DAY, OccasionStage.SUBTLE_HINT): (
                    "Tonight seems suited to setting aside a little time for those who matter.",
                    "There is a festive air outside. The desk need not hold all of your attention.",
                ),
                occasion_phrase_key(OccasionKind.CHRISTMAS_DAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "You worked all day and spared not even a little festive thought for me.",
                    "I am only your strategist, so I ask for no gift... but a few words would not be too much.",
                ),
            }
        ),
        "ja-JP": frozendict(
            {
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.INITIAL): (
                    "お食事の時間です。手元のことは少し待てますから、先にご自分を労わってください。",
                    "食事のために少し休みましょう。仕事は逃げません。",
                ),
                wellbeing_phrase_key(WellbeingKind.MEAL, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "まだお食事にしないのですか。妾はただ……あなたが無理をするのを見たくないだけです。",
                    "一日中仕事ばかり。食事をしていただくにも策が必要なのでしょうか。",
                ),
                wellbeing_phrase_key(WellbeingKind.HYDRATION, ReminderStage.INITIAL): (
                    "続ける前に、少し水を飲んでください。",
                    "机に向かって久しくなりました。水分を忘れずに。",
                ),
                wellbeing_phrase_key(WellbeingKind.HYDRATION, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "まだ水を飲んでいないのですか。理由もなく世話を焼いているのではありません。",
                    "どれほど忙しくても一口は飲めます。三度も言わせないでください。",
                ),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.INITIAL): (
                    "少し手を止め、目と心を休ませましょう。",
                    "長く集中しました。短い休息が、この先を支えてくれます。",
                ),
                wellbeing_phrase_key(WellbeingKind.REST, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "先ほどの休息の話は、聞き流してしまったのですか。",
                    "ご自分を追い込みすぎです……せめて少し目を閉じてください。",
                ),
                wellbeing_phrase_key(WellbeingKind.PROLONGED_SITTING, ReminderStage.INITIAL): (
                    "座り続けて久しくなりました。立って少し身体を伸ばしましょう。",
                    "机を離れて数歩歩けば、肩や首も楽になります。",
                ),
                wellbeing_phrase_key(WellbeingKind.PROLONGED_SITTING, ReminderStage.RESTRAINED_REINFORCEMENT): (
                    "まだ立たないのですか。どれほど良い策でも、身体と引き換えにはできません。",
                    "このままなら、意地を張っていると判断しますよ。",
                ),
                occasion_phrase_key(OccasionKind.MOHAN_BIRTHDAY, OccasionStage.SUBTLE_HINT): (
                    "今日の冬の気配は、いつもより心に留めておきたい気がします。",
                    "策士にも、ひそかに胸へ留める日があります。",
                ),
                occasion_phrase_key(OccasionKind.MOHAN_BIRTHDAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "あなたは一日中仕事ばかりで、今日は妾のことをほとんど見ませんでしたね。",
                    "何かを待っていたわけではありません……ただ、今日は覚えていてくださると思っていました。",
                ),
                occasion_phrase_key(OccasionKind.VALENTINES_DAY, OccasionStage.SUBTLE_HINT): (
                    "今日は、いつもより想いが目に入りやすい日のようです。",
                    "今日なら、心の内を口にしても無作法ではないでしょう。",
                ),
                occasion_phrase_key(OccasionKind.VALENTINES_DAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "あなたは仕事に夢中で、今日は妾に何も言うことがないのですか。",
                    "そのような習わしを気にしてはいません……ただ、少し鈍すぎます。",
                ),
                occasion_phrase_key(OccasionKind.CHRISTMAS_DAY, OccasionStage.SUBTLE_HINT): (
                    "今夜は、大切な人のために少し時間を残すのに向いていそうです。",
                    "外には祝いの気配があります。机だけに一日を捧げなくてもよいでしょう。",
                ),
                occasion_phrase_key(OccasionKind.CHRISTMAS_DAY, OccasionStage.RESTRAINED_GRUMBLE): (
                    "あなたは一日中働いて、祝いの日の心さえ妾に分けてくださいませんでした。",
                    "妾は策士ですから贈り物など求めません……けれど、一言くらいはよいでしょう。",
                ),
            }
        ),
    }
)


@dataclass(frozen=True, slots=True)
class CompanionPhrasebook:
    welcomes: Mapping[str, tuple[str, ...]]
    check_ins: tuple[str, ...]
    scenarios: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_setting(cls, value: object) -> CompanionPhrasebook:
        if not isinstance(value, dict):
            return cls({}, (), {})
        welcome_value = value.get("welcomes", {})
        if not isinstance(welcome_value, dict):
            welcome_value = {}
        welcomes = {
            str(key): _clean_lines(lines)
            for key, lines in welcome_value.items()
        }
        scenario_value = value.get("scenarios", {})
        if not isinstance(scenario_value, dict):
            scenario_value = {}
        scenarios = {
            str(key): _clean_lines(lines)
            for key, lines in scenario_value.items()
            if str(key) in {
                *WELLBEING_PHRASE_KEYS,
                *OCCASION_PHRASE_KEYS,
                *WARDROBE_PHRASE_KEYS,
            }
        }
        return cls(
            welcomes,
            _clean_lines(value.get("check_ins", ())),
            scenarios,
        )

    def as_setting(self) -> dict[str, object]:
        return {
            "version": PHRASEBOOK_VERSION,
            "welcomes": dict(self.welcomes),
            "check_ins": self.check_ins,
            "scenarios": dict(self.scenarios),
        }

    def lines_for(
        self,
        language: str,
        key: str,
    ) -> tuple[str, ...]:
        custom = self.scenarios.get(key, ())
        if custom:
            return custom
        locale = canonical_ui_language(language)
        return (
            PUBLIC_COMPANION_LINES[locale].get(key, ())
            or WARDROBE_PUBLIC_LINES[locale].get(key, ())
        )


def public_companion_line(
    language: str,
    key: str,
    *,
    variation_index: int = 0,
    phrasebook: CompanionPhrasebook | None = None,
) -> str:
    lines = (phrasebook or CompanionPhrasebook({}, (), {})).lines_for(language, key)
    return lines[variation_index % len(lines)] if lines else ""


def phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return (
        (WelcomeStyle.WARM.value, "短暫回座"),
        (WelcomeStyle.GENERAL.value, "一般歸來"),
        (WelcomeStyle.CEREMONIAL.value, "久候歸來"),
        (WelcomeStyle.MORNING.value, "早晨相見"),
        (WelcomeStyle.LATE_NIGHT.value, "深夜歸來"),
        (WelcomeStyle.WITH_DRINK.value, "帶著飲品"),
        (WelcomeStyle.WITH_BOOK.value, "帶著書本"),
        ("check_ins", "寒暄與主動關心"),
        *wellbeing_phrasebook_categories(),
        *occasion_phrasebook_categories(),
        *wardrobe_phrasebook_categories(),
    )


def grouped_phrasebook_categories(
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    return (
        (
            "歸來問候",
            (
                (WelcomeStyle.WARM.value, "短暫回座"),
                (WelcomeStyle.GENERAL.value, "一般歸來"),
                (WelcomeStyle.CEREMONIAL.value, "久候歸來"),
                (WelcomeStyle.MORNING.value, "早晨相見"),
                (WelcomeStyle.LATE_NIGHT.value, "深夜歸來"),
                (WelcomeStyle.WITH_DRINK.value, "帶著飲品"),
                (WelcomeStyle.WITH_BOOK.value, "帶著書本"),
            ),
        ),
        ("日常關心", (("check_ins", "寒暄與主動關心"),)),
        ("健康提醒", wellbeing_phrasebook_categories()),
        ("特殊節日", occasion_phrasebook_categories()),
        ("新裝互動", wardrobe_phrasebook_categories()),
    )


def wellbeing_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    titles = {
        WellbeingKind.MEAL: "用膳提醒",
        WellbeingKind.HYDRATION: "飲水提醒",
        WellbeingKind.REST: "休息提醒",
        WellbeingKind.PROLONGED_SITTING: "久坐提醒",
    }
    stages = {
        ReminderStage.INITIAL: "首次",
        ReminderStage.RESTRAINED_REINFORCEMENT: "克制加強",
    }
    return tuple(
        (wellbeing_phrase_key(kind, stage), f"{titles[kind]}・{stages[stage]}")
        for kind in WellbeingKind
        for stage in ReminderStage
    )


def occasion_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    titles = {
        OccasionKind.MOHAN_BIRTHDAY: "墨寒生日",
        OccasionKind.VALENTINES_DAY: "情人節",
        OccasionKind.CHRISTMAS_DAY: "聖誕節",
    }
    stages = {
        OccasionStage.SUBTLE_HINT: "含蓄暗示",
        OccasionStage.RESTRAINED_GRUMBLE: "小聲埋怨",
    }
    return tuple(
        (occasion_phrase_key(kind, stage), f"{titles[kind]}・{stages[stage]}")
        for kind in OccasionKind
        for stage in OccasionStage
    )


def wardrobe_phrasebook_categories() -> tuple[tuple[str, str], ...]:
    return (
        (WARDROBE_REVEAL_QUESTION, "新裝初見・詢問"),
        (WARDROBE_REVEAL_ORIGIN, "新裝初見・來歷"),
    )


def _clean_lines(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        source = value.splitlines()
    elif isinstance(value, (tuple, list)):
        source = value
    else:
        return ()
    return tuple(line for item in source if (line := str(item).strip()))
