from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TeaFlavor:
    id: str
    name: str
    unlock_level: int
    color_start: str
    color_end: str
    description: str

# Defined tea flavors
TEAS: Dict[str, TeaFlavor] = {
    "sencha": TeaFlavor(
        id="sencha",
        name="Sencha",
        unlock_level=1,
        color_start="#56ab2f",
        color_end="#a8e063",
        description="A classic Japanese green tea. Refreshing and grassy."
    ),
    "matcha": TeaFlavor(
        id="matcha",
        name="Matcha",
        unlock_level=5,
        color_start="#11998e",
        color_end="#38ef7d",
        description="Finely ground powder of specially grown and processed green tea leaves."
    ),
    "genmaicha": TeaFlavor(
        id="genmaicha",
        name="Genmaicha",
        unlock_level=10,
        color_start="#96c93d",
        color_end="#D7D7A0",
        description="Green tea mixed with roasted popped brown rice."
    ),
    "gyokuro": TeaFlavor(
        id="gyokuro",
        name="Gyokuro",
        unlock_level=15,
        color_start="#00b09b",
        color_end="#96c93d",
        description="A shaded green tea. Sweet and full of umami."
    ),
    "hojicha": TeaFlavor(
        id="hojicha",
        name="Hōjicha",
        unlock_level=20,
        color_start="#9D50BB",
        color_end="#6E48AA",
        description="Rosted green tea. Low caffeine and reddish-brown color."
    ),
    "jasmine": TeaFlavor(
        id="jasmine",
        name="Jasmine",
        unlock_level=25,
        color_start="#FDFC47",
        color_end="#24FE41",
        description="Tea scented with aroma from jasmine blossoms."
    ),
    "sakura": TeaFlavor(
        id="sakura",
        name="Sakura Tea",
        unlock_level=30,
        color_start="#ff9a9e",
        color_end="#fecfef",
        description="Pickled cherry blossoms in hot water. A taste of spring."
    ),
     "oolong": TeaFlavor(
        id="oolong",
        name="Oolong",
        unlock_level=35,
        color_start="#F2994A",
        color_end="#F2C94C",
        description="A traditional semi-oxidized Chinese tea."
    ),
    "puerh": TeaFlavor(
        id="puerh",
        name="Pu-erh",
        unlock_level=40,
        color_start="#5D4157",
        color_end="#A8CABA",
        description="Fermented and aged dark tea."
    ),
    "white_peony": TeaFlavor(
        id="white_peony",
        name="White Peony",
        unlock_level=50,
        color_start="#E0EAFC",
        color_end="#CFDEF3",
        description="A sweet, mild white tea made from young leaves and buds."
    ),
    "milk_oolong": TeaFlavor(
        id="milk_oolong",
        name="Milk Oolong",
        unlock_level=60,
        color_start="#FFF6B7",
        color_end="#F6416C",
        description="Known as Jin Xuan. Naturally creamy and buttery texture."
    ),
    "silver_needle": TeaFlavor(
        id="silver_needle",
        name="Silver Needle",
        unlock_level=70,
        color_start="#E6E6E6",
        color_end="#ffffff",
        description="Bai Hao Yinzhen. Use only the tea buds. Delicate and sweet."
    ),
    "lapsang": TeaFlavor(
        id="lapsang",
        name="Lapsang Souchong",
        unlock_level=80,
        color_start="#A770EF",
        color_end="#CF8BF3",
        description="Smoked over pine wood fires. Strong and savory."
    ),
    "dragon_well": TeaFlavor(
        id="dragon_well",
        name="Dragon Well",
        unlock_level=90,
        color_start="#B8E986",
        color_end="#50C9C3",
        description="Longjing. Pan-roasted green tea with chestnut notes."
    ),
    "keemun": TeaFlavor(
        id="keemun",
        name="Keemun",
        unlock_level=100,
        color_start="#fc4a1a",
        color_end="#f7b733",
        description="Famed Chinese black tea. Fruity, winey, and floral."
    ),

}

def get_tea_by_id(tea_id: str) -> TeaFlavor:
    return TEAS.get(tea_id, TEAS["sencha"])

def get_available_teas(level: int) -> List[TeaFlavor]:
    return [tea for tea in TEAS.values() if tea.unlock_level <= level]
