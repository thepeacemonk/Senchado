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
        unlock_level=2,
        color_start="#11998e",
        color_end="#38ef7d",
        description="Finely ground powder of specially grown and processed green tea leaves."
    ),
    "genmaicha": TeaFlavor(
        id="genmaicha",
        name="Genmaicha",
        unlock_level=3,
        color_start="#96c93d",
        color_end="#D7D7A0",
        description="Green tea mixed with roasted popped brown rice."
    ),
    "gyokuro": TeaFlavor(
        id="gyokuro",
        name="Gyokuro",
        unlock_level=5,
        color_start="#00b09b",
        color_end="#96c93d",
        description="A shaded green tea. Sweet and full of umami."
    ),
    "hojicha": TeaFlavor(
        id="hojicha",
        name="Hōjicha",
        unlock_level=8,
        color_start="#9D50BB",
        color_end="#6E48AA",
        description="Rosted green tea. Low caffeine and reddish-brown color."
    ),
    "jasmine": TeaFlavor(
        id="jasmine",
        name="Jasmine",
        unlock_level=10,
        color_start="#FDFC47",
        color_end="#24FE41",
        description="Tea scented with aroma from jasmine blossoms."
    ),
    "sakura": TeaFlavor(
        id="sakura",
        name="Sakura Tea",
        unlock_level=12,
        color_start="#ff9a9e",
        color_end="#fecfef",
        description="Pickled cherry blossoms in hot water. A taste of spring."
    ),
     "oolong": TeaFlavor(
        id="oolong",
        name="Oolong",
        unlock_level=15,
        color_start="#F2994A",
        color_end="#F2C94C",
        description="A traditional semi-oxidized Chinese tea."
    ),
    "puerh": TeaFlavor(
        id="puerh",
        name="Pu-erh",
        unlock_level=18,
        color_start="#5D4157",
        color_end="#A8CABA",
        description="Fermented and aged dark tea."
    ),
    "earl_grey": TeaFlavor(
        id="earl_grey",
        name="Earl Grey",
        unlock_level=20,
        color_start="#bdc3c7",
        color_end="#2c3e50",
        description="Black tea flavored with oil of bergamot."
    ),
    "white_peony": TeaFlavor(
        id="white_peony",
        name="White Peony",
        unlock_level=25,
        color_start="#E0EAFC",
        color_end="#CFDEF3",
        description="A sweet, mild white tea made from young leaves and buds."
    ),
    "darjeeling": TeaFlavor(
        id="darjeeling",
        name="Darjeeling First Flush",
        unlock_level=28,
        color_start="#EACDA3",
        color_end="#D6AE7B",
        description="The 'Champagne of Teas' from the Himalayas. Floral and muscatel."
    ),
    "milk_oolong": TeaFlavor(
        id="milk_oolong",
        name="Milk Oolong",
        unlock_level=32,
        color_start="#FFF6B7",
        color_end="#F6416C",
        description="Known as Jin Xuan. Naturally creamy and buttery texture."
    ),
    "masala_chai": TeaFlavor(
        id="masala_chai",
        name="Masala Chai",
        unlock_level=36,
        color_start="#D99EC9",
        color_end="#F6F0C4",
        description="Spiced black tea with cardamom, cinnamon, and ginger."
    ),
    "silver_needle": TeaFlavor(
        id="silver_needle",
        name="Silver Needle",
        unlock_level=40,
        color_start="#E6E6E6",
        color_end="#ffffff",
        description="Bai Hao Yinzhen. Use only the tea buds. Delicate and sweet."
    ),
    "lapsang": TeaFlavor(
        id="lapsang",
        name="Lapsang Souchong",
        unlock_level=45,
        color_start="#A770EF",
        color_end="#CF8BF3",
        description="Smoked over pine wood fires. Strong and savory."
    ),
    "dragon_well": TeaFlavor(
        id="dragon_well",
        name="Dragon Well",
        unlock_level=52,
        color_start="#B8E986",
        color_end="#50C9C3",
        description="Longjing. Pan-roasted green tea with chestnut notes."
    ),
    "keemun": TeaFlavor(
        id="keemun",
        name="Keemun",
        unlock_level=58,
        color_start="#fc4a1a",
        color_end="#f7b733",
        description="Famed Chinese black tea. Fruity, winey, and floral."
    ),
    "biluochun": TeaFlavor(
        id="biluochun",
        name="Biluochun",
        unlock_level=64,
        color_start="#a8ff78",
        color_end="#78ffd6",
        description="'Green Snail Spring'. Tightly rolled spiral leaves."
    ),
    "tie_guan_yin": TeaFlavor(
        id="tie_guan_yin",
        name="Tie Guan Yin",
        unlock_level=70,
        color_start="#4CA1AF",
        color_end="#C4E0E5",
        description="'Iron Goddess of Mercy'. Premium rolled oolong with orchid aroma."
    ),
    "golden_monkey": TeaFlavor(
        id="golden_monkey",
        name="Golden Monkey",
        unlock_level=75,
        color_start="#CAC531",
        color_end="#F3F9A7",
        description="Black tea made of leaves and golden buds. Savory and malty."
    ),
    "junshan": TeaFlavor(
        id="junshan",
        name="Junshan Silver Needle",
        unlock_level=80,
        color_start="#F2994A",
        color_end="#F2C94C",
        description="A rare Yellow Tea from Junshan Island."
    ),
    "oriental_beauty": TeaFlavor(
        id="oriental_beauty",
        name="Oriental Beauty",
        unlock_level=85,
        color_start="#FF512F",
        color_end="#DD2476",
        description="Bug-bitten oolong with honey-like sweetness."
    ),
    "taiping": TeaFlavor(
        id="taiping",
        name="Taiping Houkui",
        unlock_level=90,
        color_start="#1D976C",
        color_end="#93F9B9",
        description="'Monkey Chief'. Enormous flat leaves and orchid fragrance."
    ),
    "yellow_gold": TeaFlavor(
        id="yellow_gold",
        name="Yellow Gold Tea",
        unlock_level=95,
        color_start="#FFD700",
        color_end="#FDB931",
        description="Unique tea leaves coated in edible 24ct gold."
    ),
    "da_hong_pao": TeaFlavor(
        id="da_hong_pao",
        name="Da Hong Pao",
        unlock_level=100,
        color_start="#800000",
        color_end="#A52A2A",
        description="'Big Red Robe'. The most expensive legendary oolong."
    ),

}

def get_tea_by_id(tea_id: str) -> TeaFlavor:
    return TEAS.get(tea_id, TEAS["sencha"])

def get_available_teas(level: int) -> List[TeaFlavor]:
    return [tea for tea in TEAS.values() if tea.unlock_level <= level]
