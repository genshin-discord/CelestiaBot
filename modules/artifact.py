from enkapy import Enka

ArtifactType = {'EQUIP_BRACER': 'Flower',
                'EQUIP_NECKLACE': 'Feather',
                'EQUIP_SHOES': 'Sands',
                'EQUIP_RING': 'Goblet',
                'EQUIP_DRESS': 'Circlet'}

ArtifactNonEval = {'Goblet': ['ATK%', 'HP%', 'DEF%'],
                   'Circlet': ['Healing Bonus', 'DEF%', 'ATK%', 'HP%']}

ArtifactEvalRule = {'Crit RATE': 2, 'Crit DMG': 1}

ArtifactPropText = {"FIGHT_PROP_BASE_ATTACK": "Base ATK",
                    "FIGHT_PROP_HP": "Flat HP",
                    "FIGHT_PROP_ATTACK": "Flat ATK",
                    "FIGHT_PROP_DEFENSE": "Flat DEF",
                    "FIGHT_PROP_HP_PERCENT": "HP%",
                    "FIGHT_PROP_ATTACK_PERCENT": "ATK%",
                    "FIGHT_PROP_DEFENSE_PERCENT": "DEF%",
                    "FIGHT_PROP_CRITICAL": "Crit RATE",
                    "FIGHT_PROP_CRITICAL_HURT": "Crit DMG",
                    "FIGHT_PROP_CHARGE_EFFICIENCY": "Energy Recharge",
                    "FIGHT_PROP_HEAL_ADD": "Healing Bonus",
                    "FIGHT_PROP_ELEMENT_MASTERY": "Elemental Mastery",
                    "FIGHT_PROP_PHYSICAL_ADD_HURT": "Physical DMG Bonus",
                    "FIGHT_PROP_FIRE_ADD_HURT": "Pyro DMG Bonus",
                    "FIGHT_PROP_ELEC_ADD_HURT": "Electro DMG Bonus",
                    "FIGHT_PROP_WATER_ADD_HURT": "Hydro DMG Bonus",
                    "FIGHT_PROP_WIND_ADD_HURT": "Anemo DMG Bonus",
                    "FIGHT_PROP_ICE_ADD_HURT": "Cryo DMG Bonus",
                    "FIGHT_PROP_ROCK_ADD_HURT": "Geo DMG Bonus"}


class ArtifactData:
    name: str
    main_stat: dict
    sub_stats: list
    icon: str
    score: float
    type: str
    level: int


class EnkaArtifact:
    def __init__(self, e):
        self.e: Enka = e

    @classmethod
    async def create(cls):
        e = Enka()
        await e.load_lang()
        e.timeout = 60
        return cls(e)

    @staticmethod
    def parse_stats(stat):
        stat_text = stat.prop
        if stat_text in ArtifactPropText:
            stat_text = ArtifactPropText[stat_text]
        return {'prop': stat_text, 'value': stat.value}

    @staticmethod
    def evaluate(artifact: ArtifactData):
        if artifact.level < 20:
            return 0
        score = 0
        if artifact.type in ArtifactNonEval and artifact.main_stat['prop'] in ArtifactNonEval[artifact.type]:
            return score
        for sub in artifact.sub_stats:
            if sub['prop'] in ArtifactEvalRule:
                score += sub['value'] * ArtifactEvalRule[sub['prop']]
        if artifact.main_stat['prop'] in ['Crit RATE', 'Crit DMG']:
            score *= 1.1695
        score = int(score * 100) / 100.0
        return score

    async def fetch_artifact_user(self, uid):
        data = await self.e.fetch_user(uid)
        for character in data.characters:
            for artifact in character.artifacts:
                ad = ArtifactData()
                ad.icon = artifact.flat.icon
                ad.name = f'{artifact.flat.setNameText} {artifact.flat.nameText}'
                ad.main_stat = self.parse_stats(artifact.flat.main_stat)
                ad.sub_stats = []
                ad.level = artifact.data.level - 1
                for stat in artifact.flat.sub_stats:
                    ad.sub_stats.append(self.parse_stats(stat))
                if artifact.flat.equipType in ArtifactType:
                    ad.type = ArtifactType[artifact.flat.equipType]
                else:
                    ad.type = artifact.flat.equipType
                ad.score = self.evaluate(ad)
                yield ad
