"""Built-in food database.

Every entry stores macros per 100 g plus:
  serving_g : grams in one "default" portion (used for bare quantities like "2 eggs")
  units     : grams per named unit for this food (cup, slice, piece, ...)
  aliases   : other names people type
Values are USDA-style approximations, good enough for day-to-day tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Food:
    name: str
    kcal: float
    protein: float
    carbs: float
    fat: float
    serving_g: float
    units: dict[str, float] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    source: str = "database"
    serving_unit: str = "serving"   # what one serving is called: "scoop", "bar", "slice", ...

    def macros_for(self, grams: float) -> dict[str, float]:
        k = grams / 100.0
        return {
            "kcal": round(self.kcal * k, 1),
            "protein": round(self.protein * k, 1),
            "carbs": round(self.carbs * k, 1),
            "fat": round(self.fat * k, 1),
        }


def F(name, kcal, p, c, f, serving_g, units=None, aliases=None) -> Food:
    return Food(name, kcal, p, c, f, serving_g, units or {}, aliases or [])


def food_from_serving(name: str, serving_g: float, kcal: float, protein: float, carbs: float, fat: float,
                      serving_unit: str = "serving", aliases: list[str] | None = None,
                      source: str = "custom") -> Food:
    """Build a Food straight off a nutrition label: the macros for ONE serving of `serving_g` grams.

    Internally everything is per 100 g, so "2 scoops" or "45g" of the food both come out exact.
    The serving word ("scoop", "bar") is registered as a unit alongside "serving".
    """
    if serving_g <= 0:
        raise ValueError("serving_g must be positive")
    k = 100.0 / serving_g
    unit = (serving_unit or "serving").strip().lower() or "serving"
    units = {"serving": serving_g, unit: serving_g}
    clean_aliases = []
    for a in aliases or []:
        a = a.strip().lower()
        if a and a != name.strip().lower() and a not in clean_aliases:
            clean_aliases.append(a)
    return Food(name.strip().lower(), round(kcal * k, 4), round(protein * k, 4), round(carbs * k, 4),
                round(fat * k, 4), serving_g, units, clean_aliases, source, unit)


FOODS: list[Food] = [
    # ---- Eggs & dairy -------------------------------------------------------
    F("egg", 143, 12.6, 0.7, 9.5, 50, {"piece": 50, "large": 50, "medium": 44, "small": 38},
      ["eggs", "whole egg", "boiled egg", "fried egg", "scrambled egg", "scrambled eggs", "boiled eggs", "fried eggs", "omelette", "omelet"]),
    F("egg white", 52, 10.9, 0.7, 0.2, 33, {"piece": 33, "cup": 243}, ["egg whites"]),
    F("whole milk", 61, 3.2, 4.8, 3.3, 244, {"cup": 244, "glass": 250, "tbsp": 15}, ["milk", "full fat milk", "full cream milk"]),
    F("skim milk", 34, 3.4, 5.0, 0.1, 244, {"cup": 244, "glass": 250}, ["skimmed milk", "nonfat milk", "fat free milk"]),
    F("2% milk", 50, 3.3, 4.8, 2.0, 244, {"cup": 244, "glass": 250}, ["semi skimmed milk", "reduced fat milk", "low fat milk"]),
    F("almond milk", 15, 0.6, 0.6, 1.1, 240, {"cup": 240, "glass": 250}, ["unsweetened almond milk"]),
    F("oat milk", 45, 1.0, 7.0, 1.5, 240, {"cup": 240, "glass": 250}, []),
    F("greek yogurt", 59, 10.0, 3.6, 0.4, 170, {"cup": 245, "container": 170, "tub": 170, "tbsp": 15}, ["greek yoghurt", "nonfat greek yogurt", "plain greek yogurt"]),
    F("yogurt", 61, 3.5, 4.7, 3.3, 170, {"cup": 245, "container": 170, "tub": 170}, ["yoghurt", "plain yogurt", "curd", "dahi"]),
    F("cottage cheese", 98, 11.1, 3.4, 4.3, 113, {"cup": 226}, []),
    F("cheddar cheese", 403, 24.9, 1.3, 33.1, 28, {"slice": 28, "cup": 113, "oz": 28.35}, ["cheddar", "cheese"]),
    F("mozzarella", 280, 28.0, 3.1, 17.0, 28, {"slice": 28, "cup": 112}, ["mozzarella cheese"]),
    F("parmesan", 431, 38.5, 4.1, 28.6, 5, {"tbsp": 5, "cup": 100}, ["parmesan cheese", "parmigiano"]),
    F("feta", 264, 14.2, 4.1, 21.3, 28, {"cup": 150}, ["feta cheese"]),
    F("cream cheese", 342, 6.2, 4.1, 34.0, 15, {"tbsp": 15}, []),
    F("butter", 717, 0.9, 0.1, 81.1, 14, {"tbsp": 14, "tsp": 5, "pat": 5}, []),
    F("paneer", 296, 18.3, 1.2, 22.0, 100, {"cube": 15, "cup": 120}, ["indian cottage cheese"]),
    F("whey protein", 400, 80.0, 8.0, 5.0, 30, {"scoop": 30}, ["protein powder", "whey", "protein shake", "protein scoop"]),
    # ---- Meat & poultry -----------------------------------------------------
    F("chicken breast", 165, 31.0, 0, 3.6, 174, {"piece": 174, "breast": 174, "oz": 28.35},
      ["chicken", "grilled chicken", "grilled chicken breast", "chicken breast cooked", "chicken fillet", "chicken tenders", "chicken tenderloin"]),
    F("chicken thigh", 209, 26.0, 0, 10.9, 90, {"piece": 90, "thigh": 90}, ["chicken thighs", "thighs"]),
    F("chicken wings", 290, 27.0, 0, 19.5, 34, {"piece": 34, "wing": 34}, ["wings", "chicken wing", "buffalo wings"]),
    F("rotisserie chicken", 190, 27.0, 0, 8.0, 140, {"cup": 140}, []),
    F("ground beef", 250, 26.0, 0, 15.0, 113, {"patty": 113, "oz": 28.35}, ["beef mince", "minced beef", "beef", "hamburger meat", "ground beef 85%"]),
    F("lean ground beef", 176, 27.0, 0, 7.0, 113, {"patty": 113}, ["ground beef 93%", "lean beef mince", "extra lean ground beef"]),
    F("steak", 271, 26.0, 0, 18.0, 225, {"piece": 225, "oz": 28.35}, ["sirloin", "ribeye", "ribeye steak", "sirloin steak", "beef steak", "new york strip", "filet mignon"]),
    F("pork chop", 231, 25.7, 0, 13.9, 150, {"piece": 150, "chop": 150}, ["pork chops", "pork"]),
    F("pork tenderloin", 143, 26.0, 0, 3.5, 113, {}, ["pork loin"]),
    F("bacon", 541, 37.0, 1.4, 42.0, 8, {"slice": 8, "strip": 8, "rasher": 8}, ["bacon strips", "bacon rashers", "streaky bacon"]),
    F("ham", 145, 21.0, 1.5, 6.0, 28, {"slice": 28}, ["deli ham", "sliced ham"]),
    F("turkey breast", 135, 30.0, 0, 1.0, 85, {"slice": 28, "oz": 28.35}, ["turkey", "deli turkey", "sliced turkey", "turkey slices"]),
    F("ground turkey", 189, 27.0, 0, 8.5, 113, {"patty": 113}, ["turkey mince", "minced turkey"]),
    F("sausage", 301, 12.0, 2.0, 27.0, 50, {"piece": 50, "link": 50}, ["sausages", "pork sausage", "breakfast sausage", "sausage link"]),
    F("chicken sausage", 170, 14.0, 3.0, 11.0, 85, {"piece": 85, "link": 85}, []),
    F("lamb", 258, 25.0, 0, 17.0, 113, {"chop": 100, "oz": 28.35}, ["lamb chop", "lamb chops", "mutton"]),
    F("hot dog", 290, 10.0, 2.0, 26.0, 52, {"piece": 52, "link": 52}, ["hot dogs", "frankfurter", "wiener"]),
    F("pepperoni", 494, 23.0, 1.0, 44.0, 28, {"slice": 2}, []),
    F("beef jerky", 410, 33.0, 11.0, 26.0, 28, {"piece": 10, "oz": 28.35}, ["jerky"]),
    # ---- Fish & seafood -----------------------------------------------------
    F("salmon", 208, 20.4, 0, 13.4, 170, {"fillet": 170, "piece": 170, "oz": 28.35}, ["salmon fillet", "grilled salmon", "baked salmon", "atlantic salmon"]),
    F("smoked salmon", 117, 18.3, 0, 4.3, 56, {"slice": 28}, ["lox"]),
    F("tuna", 116, 25.5, 0, 1.0, 142, {"can": 142, "tin": 142, "pouch": 74}, ["canned tuna", "tuna in water", "tin of tuna", "can of tuna", "tuna can"]),
    F("tuna steak", 132, 28.0, 0, 1.3, 170, {"piece": 170}, ["ahi tuna", "seared tuna"]),
    F("shrimp", 99, 24.0, 0.2, 0.3, 85, {"piece": 7, "cup": 145}, ["prawns", "prawn", "shrimps"]),
    F("cod", 82, 18.0, 0, 0.7, 170, {"fillet": 170, "piece": 170}, ["white fish", "cod fillet", "haddock", "tilapia", "fish fillet"]),
    F("sardines", 208, 24.6, 0, 11.5, 92, {"can": 92, "tin": 92, "piece": 12}, ["canned sardines", "tin of sardines"]),
    F("fish sticks", 249, 11.0, 22.0, 13.0, 28, {"piece": 28, "stick": 28}, ["fish fingers"]),
    F("crab", 83, 18.0, 0, 0.7, 85, {}, ["crab meat"]),
    F("scallops", 111, 20.5, 5.4, 0.8, 85, {"piece": 20}, ["scallop"]),
    # ---- Grains, bread, pasta -----------------------------------------------
    F("white rice", 130, 2.7, 28.2, 0.3, 158, {"cup": 158, "bowl": 200, "scoop": 90}, ["rice", "cooked rice", "steamed rice", "jasmine rice", "basmati rice", "white rice cooked"]),
    F("brown rice", 112, 2.3, 23.5, 0.8, 195, {"cup": 195, "bowl": 200}, ["brown rice cooked"]),
    F("fried rice", 163, 5.0, 24.0, 5.5, 200, {"cup": 200, "bowl": 250, "plate": 300}, ["egg fried rice", "chicken fried rice"]),
    F("quinoa", 120, 4.4, 21.3, 1.9, 185, {"cup": 185}, ["cooked quinoa"]),
    F("oats", 379, 13.2, 67.7, 6.5, 40, {"cup": 81, "scoop": 40, "serving": 40}, ["oatmeal", "rolled oats", "dry oats", "porridge oats", "quick oats"]),
    F("cooked oatmeal", 71, 2.5, 12.0, 1.5, 234, {"cup": 234, "bowl": 250}, ["porridge", "cooked oats", "bowl of oatmeal", "bowl of porridge"]),
    F("overnight oats", 150, 6.0, 24.0, 3.5, 250, {"jar": 250, "cup": 250}, []),
    F("bread", 265, 9.0, 49.0, 3.2, 30, {"slice": 30, "piece": 30}, ["white bread", "slice of bread", "toast", "sliced bread"]),
    F("whole wheat bread", 247, 13.0, 41.0, 3.4, 30, {"slice": 30, "piece": 30}, ["wholemeal bread", "brown bread", "whole grain bread", "wheat bread", "whole wheat toast"]),
    F("sourdough", 289, 12.0, 56.0, 2.0, 50, {"slice": 50, "piece": 50}, ["sourdough bread", "sourdough toast"]),
    F("bagel", 250, 10.0, 49.0, 1.5, 100, {"piece": 100}, ["bagels", "plain bagel"]),
    F("english muffin", 235, 8.0, 46.0, 1.8, 57, {"piece": 57}, []),
    F("croissant", 406, 8.2, 45.8, 21.0, 57, {"piece": 57}, ["croissants", "butter croissant"]),
    F("tortilla", 312, 8.0, 51.0, 8.0, 45, {"piece": 45, "large": 70, "small": 30}, ["flour tortilla", "tortillas", "wrap", "wraps"]),
    F("corn tortilla", 218, 5.7, 44.6, 2.9, 26, {"piece": 26}, ["corn tortillas"]),
    F("pita", 275, 9.1, 55.7, 1.2, 60, {"piece": 60}, ["pita bread", "pitta"]),
    F("naan", 310, 9.0, 50.0, 8.0, 90, {"piece": 90}, ["naan bread", "garlic naan"]),
    F("roti", 297, 8.0, 46.0, 9.0, 40, {"piece": 40}, ["chapati", "chapathi", "phulka", "rotis", "chapatis"]),
    F("dosa", 168, 3.9, 29.0, 3.7, 100, {"piece": 100}, ["masala dosa", "plain dosa"]),
    F("idli", 130, 4.0, 27.0, 0.4, 40, {"piece": 40}, ["idlis", "idly"]),
    F("pasta", 131, 5.0, 25.0, 1.1, 140, {"cup": 140, "bowl": 250, "plate": 300}, ["cooked pasta", "spaghetti", "penne", "fusilli", "linguine", "macaroni", "noodles", "fettuccine", "rigatoni"]),
    F("mac and cheese", 164, 6.7, 20.0, 6.6, 200, {"cup": 200, "bowl": 250}, ["macaroni and cheese", "mac n cheese"]),
    F("ramen", 436, 9.5, 63.0, 17.0, 85, {"packet": 85, "pack": 85, "bowl": 400}, ["instant noodles", "instant ramen", "maggi", "cup noodles"]),
    F("cereal", 379, 7.0, 84.0, 3.0, 40, {"cup": 40, "bowl": 50}, ["breakfast cereal", "corn flakes", "cornflakes", "cheerios"]),
    F("granola", 471, 10.0, 64.0, 20.0, 45, {"cup": 110, "handful": 30}, []),
    F("couscous", 112, 3.8, 23.2, 0.2, 157, {"cup": 157}, []),
    F("pancake", 227, 6.4, 28.0, 9.7, 77, {"piece": 77}, ["pancakes"]),
    F("waffle", 291, 7.9, 33.0, 14.0, 75, {"piece": 75}, ["waffles"]),
    F("crackers", 500, 7.0, 62.0, 25.0, 15, {"piece": 5}, ["cracker", "ritz crackers", "saltines"]),
    F("rice cake", 387, 8.0, 82.0, 2.8, 9, {"piece": 9}, ["rice cakes"]),
    # ---- Legumes ------------------------------------------------------------
    F("black beans", 132, 8.9, 23.7, 0.5, 172, {"cup": 172, "can": 425}, ["beans", "canned black beans"]),
    F("chickpeas", 164, 8.9, 27.4, 2.6, 164, {"cup": 164, "can": 400}, ["garbanzo beans", "chana", "chole", "chickpea"]),
    F("lentils", 116, 9.0, 20.1, 0.4, 198, {"cup": 198, "bowl": 250}, ["lentil", "dal", "daal", "dhal", "cooked lentils"]),
    F("kidney beans", 127, 8.7, 22.8, 0.5, 177, {"cup": 177, "can": 400}, ["rajma", "red beans"]),
    F("baked beans", 94, 5.0, 17.0, 0.4, 130, {"cup": 254, "can": 415}, []),
    F("edamame", 121, 11.9, 8.9, 5.2, 155, {"cup": 155}, []),
    F("tofu", 76, 8.1, 1.9, 4.8, 100, {"block": 350, "cup": 250}, ["firm tofu", "bean curd"]),
    F("tempeh", 192, 20.3, 7.6, 10.8, 100, {}, []),
    F("hummus", 166, 7.9, 14.3, 9.6, 30, {"tbsp": 15, "cup": 245}, []),
    # ---- Vegetables ---------------------------------------------------------
    F("broccoli", 35, 2.4, 7.2, 0.4, 91, {"cup": 91, "head": 300, "floret": 11}, ["steamed broccoli", "broccoli florets"]),
    F("spinach", 23, 2.9, 3.6, 0.4, 30, {"cup": 30, "handful": 30, "bag": 140}, ["baby spinach", "raw spinach"]),
    F("cooked spinach", 23, 3.0, 3.8, 0.3, 180, {"cup": 180}, ["sauteed spinach", "palak"]),
    F("kale", 49, 4.3, 8.8, 0.9, 67, {"cup": 67, "handful": 30}, []),
    F("lettuce", 15, 1.4, 2.9, 0.2, 47, {"cup": 47, "head": 300, "leaf": 10}, ["romaine", "iceberg lettuce", "romaine lettuce"]),
    F("mixed greens", 20, 1.8, 3.5, 0.2, 60, {"cup": 30, "handful": 30}, ["salad greens", "spring mix", "arugula", "rocket", "green salad", "side salad", "salad"]),
    F("tomato", 18, 0.9, 3.9, 0.2, 123, {"piece": 123, "cup": 180, "slice": 20}, ["tomatoes"]),
    F("cherry tomatoes", 18, 0.9, 3.9, 0.2, 17, {"piece": 17, "cup": 149}, ["cherry tomato", "grape tomatoes"]),
    F("cucumber", 15, 0.7, 3.6, 0.1, 100, {"piece": 300, "cup": 104, "slice": 7}, ["cucumbers"]),
    F("carrot", 41, 0.9, 9.6, 0.2, 61, {"piece": 61, "cup": 128, "baby": 10}, ["carrots", "baby carrots"]),
    F("bell pepper", 26, 1.0, 6.0, 0.3, 120, {"piece": 120, "cup": 92}, ["bell peppers", "capsicum", "red pepper", "green pepper", "peppers"]),
    F("onion", 40, 1.1, 9.3, 0.1, 110, {"piece": 110, "cup": 160, "slice": 14}, ["onions", "red onion", "white onion"]),
    F("garlic", 149, 6.4, 33.1, 0.5, 3, {"clove": 3, "piece": 3, "tsp": 3}, ["garlic clove"]),
    F("mushrooms", 22, 3.1, 3.3, 0.3, 70, {"cup": 70, "piece": 18}, ["mushroom", "button mushrooms", "cremini"]),
    F("zucchini", 17, 1.2, 3.1, 0.3, 196, {"piece": 196, "cup": 124}, ["courgette", "zucchinis"]),
    F("asparagus", 20, 2.2, 3.9, 0.1, 134, {"cup": 134, "spear": 16, "piece": 16}, []),
    F("green beans", 31, 1.8, 7.0, 0.2, 100, {"cup": 100}, ["string beans"]),
    F("peas", 81, 5.4, 14.5, 0.4, 145, {"cup": 145}, ["green peas", "frozen peas"]),
    F("corn", 86, 3.3, 19.0, 1.4, 145, {"cup": 145, "ear": 90, "cob": 90}, ["sweet corn", "corn on the cob", "sweetcorn"]),
    F("potato", 87, 1.9, 20.1, 0.1, 173, {"piece": 173, "cup": 150, "small": 120, "large": 300}, ["potatoes", "baked potato", "boiled potato", "boiled potatoes", "roast potatoes", "roasted potatoes"]),
    F("mashed potatoes", 113, 2.0, 17.0, 4.2, 210, {"cup": 210, "scoop": 100}, ["mashed potato", "mash"]),
    F("french fries", 312, 3.4, 41.0, 15.0, 117, {"cup": 117, "small": 71, "medium": 117, "large": 154, "serving": 117}, ["fries", "chips", "fried potatoes", "mcdonalds fries"]),
    F("sweet potato", 90, 2.0, 20.7, 0.2, 150, {"piece": 150, "cup": 200, "large": 250}, ["sweet potatoes", "baked sweet potato", "yam"]),
    F("cauliflower", 25, 1.9, 5.0, 0.3, 107, {"cup": 107, "head": 600}, ["cauliflower rice"]),
    F("cabbage", 25, 1.3, 5.8, 0.1, 89, {"cup": 89}, ["coleslaw mix"]),
    F("brussels sprouts", 36, 3.4, 7.1, 0.3, 88, {"cup": 88, "piece": 19}, ["brussel sprouts", "sprouts"]),
    F("eggplant", 25, 1.0, 5.9, 0.2, 82, {"cup": 82, "piece": 450}, ["aubergine", "brinjal"]),
    F("avocado", 160, 2.0, 8.5, 14.7, 150, {"piece": 150, "half": 75, "cup": 150, "slice": 15}, ["avocados", "half avocado", "half an avocado"]),
    F("guacamole", 160, 2.0, 9.0, 14.0, 30, {"tbsp": 15, "cup": 230}, ["guac"]),
    F("olives", 115, 0.8, 6.3, 10.7, 15, {"piece": 4, "cup": 135}, ["olive", "black olives", "green olives"]),
    F("pickles", 12, 0.5, 2.4, 0.2, 35, {"piece": 35, "spear": 35, "slice": 7}, ["pickle", "dill pickle"]),
    F("kimchi", 15, 1.1, 2.4, 0.5, 75, {"cup": 150, "tbsp": 15}, []),
    F("salsa", 36, 1.5, 7.0, 0.2, 30, {"tbsp": 15, "cup": 260}, []),
    F("seaweed snack", 500, 25.0, 25.0, 33.0, 5, {"packet": 5, "pack": 5, "sheet": 0.3}, ["seaweed", "nori"]),
    # ---- Fruit --------------------------------------------------------------
    F("banana", 89, 1.1, 22.8, 0.3, 118, {"piece": 118, "small": 100, "large": 136, "cup": 150}, ["bananas"]),
    F("apple", 52, 0.3, 13.8, 0.2, 182, {"piece": 182, "small": 150, "large": 220, "cup": 125}, ["apples", "red apple", "green apple"]),
    F("orange", 47, 0.9, 11.8, 0.1, 131, {"piece": 131, "cup": 180}, ["oranges", "navel orange"]),
    F("mandarin", 53, 0.8, 13.3, 0.3, 88, {"piece": 88}, ["mandarins", "clementine", "clementines", "tangerine", "satsuma"]),
    F("strawberries", 32, 0.7, 7.7, 0.3, 150, {"cup": 150, "piece": 12, "handful": 50}, ["strawberry"]),
    F("blueberries", 57, 0.7, 14.5, 0.3, 148, {"cup": 148, "handful": 50}, ["blueberry"]),
    F("raspberries", 52, 1.2, 11.9, 0.7, 123, {"cup": 123, "handful": 40}, ["raspberry"]),
    F("blackberries", 43, 1.4, 9.6, 0.5, 144, {"cup": 144, "handful": 40}, ["blackberry"]),
    F("grapes", 69, 0.7, 18.1, 0.2, 151, {"cup": 151, "piece": 5, "handful": 50}, ["grape", "red grapes", "green grapes"]),
    F("watermelon", 30, 0.6, 7.6, 0.2, 280, {"cup": 152, "slice": 280, "wedge": 280}, []),
    F("cantaloupe", 34, 0.8, 8.2, 0.2, 160, {"cup": 160, "slice": 100}, ["melon", "rockmelon", "honeydew"]),
    F("pineapple", 50, 0.5, 13.1, 0.1, 165, {"cup": 165, "slice": 84, "ring": 84}, []),
    F("mango", 60, 0.8, 15.0, 0.4, 207, {"piece": 207, "cup": 165, "slice": 30}, ["mangoes", "mangos"]),
    F("peach", 39, 0.9, 9.5, 0.3, 150, {"piece": 150}, ["peaches", "nectarine"]),
    F("pear", 57, 0.4, 15.2, 0.1, 178, {"piece": 178}, ["pears"]),
    F("plum", 46, 0.7, 11.4, 0.3, 66, {"piece": 66}, ["plums"]),
    F("cherries", 63, 1.1, 16.0, 0.2, 138, {"cup": 138, "piece": 8, "handful": 50}, ["cherry"]),
    F("kiwi", 61, 1.1, 14.7, 0.5, 69, {"piece": 69}, ["kiwis", "kiwifruit"]),
    F("pomegranate", 83, 1.7, 18.7, 1.2, 87, {"cup": 174, "piece": 280}, ["pomegranate seeds", "pomegranate arils"]),
    F("dates", 277, 1.8, 75.0, 0.2, 24, {"piece": 24}, ["date", "medjool dates", "medjool date"]),
    F("raisins", 299, 3.1, 79.2, 0.5, 30, {"cup": 145, "handful": 30, "box": 43, "tbsp": 9}, []),
    F("dried mango", 319, 2.5, 78.6, 1.2, 40, {"piece": 10, "handful": 40}, []),
    F("dried cranberries", 308, 0.2, 82.8, 1.1, 40, {"cup": 120, "handful": 40}, ["craisins"]),
    F("applesauce", 42, 0.2, 11.3, 0.1, 122, {"cup": 244, "pouch": 90}, ["apple sauce"]),
    F("coconut", 354, 3.3, 15.2, 33.5, 45, {"cup": 80, "piece": 45}, ["fresh coconut", "coconut meat"]),
    F("lemon", 29, 1.1, 9.3, 0.3, 58, {"piece": 58, "wedge": 7}, ["lemons", "lime", "limes"]),
    F("fruit salad", 50, 0.6, 12.5, 0.2, 200, {"cup": 175, "bowl": 250}, ["mixed fruit", "fruit cup", "fruit bowl"]),
    # ---- Nuts, seeds, spreads ----------------------------------------------
    F("almonds", 579, 21.2, 21.6, 49.9, 28, {"piece": 1.2, "handful": 28, "cup": 143, "oz": 28.35}, ["almond"]),
    F("walnuts", 654, 15.2, 13.7, 65.2, 28, {"piece": 4, "half": 2, "handful": 28, "cup": 117}, ["walnut"]),
    F("cashews", 553, 18.2, 30.2, 43.9, 28, {"piece": 1.5, "handful": 28, "cup": 137}, ["cashew"]),
    F("peanuts", 567, 25.8, 16.1, 49.2, 28, {"piece": 1, "handful": 28, "cup": 146}, ["peanut", "roasted peanuts", "salted peanuts"]),
    F("pistachios", 560, 20.2, 27.2, 45.3, 28, {"piece": 0.7, "handful": 28, "cup": 123}, ["pistachio"]),
    F("pecans", 691, 9.2, 13.9, 72.0, 28, {"piece": 2, "half": 1, "handful": 28}, ["pecan"]),
    F("macadamia nuts", 718, 7.9, 13.8, 75.8, 28, {"piece": 2.5, "handful": 28}, ["macadamias", "macadamia"]),
    F("mixed nuts", 607, 20.0, 21.0, 54.0, 28, {"handful": 28, "cup": 137}, ["nuts", "trail mix"]),
    F("peanut butter", 588, 25.1, 20.0, 50.4, 32, {"tbsp": 16, "tsp": 5, "scoop": 32}, ["pb", "natural peanut butter", "crunchy peanut butter"]),
    F("almond butter", 614, 21.0, 18.8, 55.5, 32, {"tbsp": 16, "tsp": 5}, []),
    F("nutella", 539, 6.3, 57.5, 30.9, 37, {"tbsp": 19, "tsp": 6}, ["hazelnut spread", "chocolate spread"]),
    F("chia seeds", 486, 16.5, 42.1, 30.7, 28, {"tbsp": 12, "tsp": 4, "scoop": 28}, ["chia"]),
    F("flaxseed", 534, 18.3, 28.9, 42.2, 10, {"tbsp": 10, "tsp": 3}, ["flax", "ground flaxseed", "flax seeds", "flaxseeds"]),
    F("pumpkin seeds", 559, 30.2, 10.7, 49.1, 28, {"tbsp": 8, "handful": 28}, ["pepitas"]),
    F("sunflower seeds", 584, 20.8, 20.0, 51.5, 28, {"tbsp": 8, "handful": 28}, []),
    F("hemp seeds", 553, 31.6, 8.7, 48.8, 30, {"tbsp": 10}, ["hemp hearts"]),
    F("jam", 278, 0.4, 68.9, 0.1, 20, {"tbsp": 20, "tsp": 7}, ["jelly", "strawberry jam", "fruit preserves", "marmalade"]),
    F("honey", 304, 0.3, 82.4, 0, 21, {"tbsp": 21, "tsp": 7}, []),
    F("maple syrup", 260, 0, 67.0, 0.1, 20, {"tbsp": 20, "tsp": 7}, ["syrup", "pancake syrup"]),
    F("sugar", 387, 0, 100.0, 0, 4, {"tsp": 4, "tbsp": 12.5, "cube": 4, "packet": 4}, ["white sugar", "brown sugar"]),
    # ---- Oils, dressings, sauces -------------------------------------------
    F("olive oil", 884, 0, 0, 100.0, 14, {"tbsp": 14, "tsp": 4.5, "drizzle": 5}, ["oil", "extra virgin olive oil", "evoo", "cooking oil", "vegetable oil", "canola oil", "avocado oil"]),
    F("coconut oil", 862, 0, 0, 100.0, 14, {"tbsp": 14, "tsp": 4.5}, []),
    F("ghee", 900, 0, 0, 100.0, 13, {"tbsp": 13, "tsp": 4.3}, ["clarified butter"]),
    F("mayonnaise", 680, 1.0, 0.6, 75.0, 14, {"tbsp": 14, "tsp": 5}, ["mayo"]),
    F("ketchup", 101, 1.0, 27.4, 0.1, 17, {"tbsp": 17, "tsp": 6, "packet": 9}, ["tomato ketchup", "tomato sauce"]),
    F("mustard", 66, 4.4, 5.8, 4.0, 5, {"tbsp": 15, "tsp": 5}, []),
    F("bbq sauce", 172, 0.8, 40.8, 0.6, 17, {"tbsp": 17}, ["barbecue sauce"]),
    F("soy sauce", 53, 8.1, 4.9, 0.6, 16, {"tbsp": 16, "tsp": 5}, []),
    F("hot sauce", 12, 0.5, 1.8, 0.4, 5, {"tbsp": 15, "tsp": 5, "dash": 1}, ["sriracha", "tabasco", "chili sauce"]),
    F("ranch dressing", 430, 1.3, 7.0, 45.0, 30, {"tbsp": 15}, ["ranch"]),
    F("caesar dressing", 470, 1.9, 6.0, 49.0, 30, {"tbsp": 15}, []),
    F("vinaigrette", 300, 0.2, 5.0, 31.0, 30, {"tbsp": 15}, ["balsamic vinaigrette", "italian dressing", "salad dressing", "dressing"]),
    F("marinara sauce", 50, 1.4, 8.0, 1.5, 125, {"cup": 250, "tbsp": 16}, ["pasta sauce", "tomato pasta sauce", "spaghetti sauce", "marinara"]),
    F("alfredo sauce", 180, 3.0, 4.0, 17.0, 60, {"cup": 240, "tbsp": 15}, []),
    F("pesto", 460, 5.0, 6.0, 46.0, 30, {"tbsp": 15}, []),
    F("tzatziki", 100, 4.0, 5.0, 7.0, 30, {"tbsp": 15}, []),
    F("sour cream", 198, 2.4, 4.6, 19.4, 30, {"tbsp": 15, "dollop": 30}, []),
    F("heavy cream", 340, 2.1, 2.8, 36.1, 15, {"tbsp": 15, "cup": 238, "splash": 15}, ["cream", "whipping cream", "double cream"]),
    F("gravy", 50, 2.0, 5.0, 2.0, 60, {"cup": 233, "tbsp": 15}, []),
    F("coconut milk", 230, 2.3, 5.5, 23.8, 60, {"cup": 240, "can": 400, "tbsp": 15}, ["canned coconut milk"]),
    # ---- Meals & composite dishes ------------------------------------------
    F("pizza", 266, 11.0, 33.0, 10.0, 107, {"slice": 107, "piece": 107, "large slice": 140, "whole": 850}, ["cheese pizza", "pizza slice", "slice of pizza", "pepperoni pizza", "margherita pizza"]),
    F("cheeseburger", 295, 15.0, 27.0, 14.0, 200, {"piece": 200, "burger": 200}, ["burger", "hamburger", "beef burger", "double cheeseburger"]),
    F("chicken burger", 250, 15.0, 28.0, 9.0, 220, {"piece": 220, "burger": 220}, ["chicken sandwich", "crispy chicken sandwich", "grilled chicken sandwich"]),
    F("sandwich", 250, 12.0, 28.0, 10.0, 200, {"piece": 200, "half": 100}, ["turkey sandwich", "ham sandwich", "club sandwich", "blt", "sub", "hoagie"]),
    F("grilled cheese", 350, 13.0, 30.0, 20.0, 120, {"piece": 120}, ["grilled cheese sandwich", "cheese toastie", "toastie"]),
    F("pb&j", 320, 11.0, 42.0, 13.0, 120, {"piece": 120}, ["pbj", "peanut butter and jelly", "peanut butter sandwich", "peanut butter and jelly sandwich"]),
    F("burrito", 206, 9.0, 26.0, 7.5, 350, {"piece": 350}, ["chicken burrito", "bean burrito", "burrito bowl", "chipotle burrito", "chipotle bowl"]),
    F("taco", 226, 9.0, 20.0, 12.0, 100, {"piece": 100}, ["tacos", "beef taco", "chicken taco", "beef tacos", "chicken tacos"]),
    F("quesadilla", 300, 12.0, 28.0, 16.0, 180, {"piece": 180, "half": 90}, ["chicken quesadilla", "cheese quesadilla"]),
    F("sushi", 143, 6.0, 25.0, 2.0, 30, {"piece": 30, "roll": 240, "plate": 240}, ["sushi roll", "california roll", "salmon roll", "maki", "sushi rolls"]),
    F("chicken curry", 140, 11.0, 6.0, 8.0, 250, {"cup": 240, "bowl": 300, "plate": 350}, ["curry", "butter chicken", "chicken tikka masala", "tikka masala", "korma"]),
    F("chicken stir fry", 120, 11.0, 8.0, 5.0, 300, {"cup": 200, "bowl": 300, "plate": 350}, ["stir fry", "stir-fry", "beef stir fry", "veggie stir fry"]),
    F("spaghetti bolognese", 150, 8.0, 18.0, 5.0, 350, {"bowl": 350, "plate": 400, "cup": 220}, ["bolognese", "spag bol", "pasta bolognese", "spaghetti with meat sauce"]),
    F("lasagna", 135, 8.0, 13.0, 5.5, 250, {"piece": 250, "slice": 250, "serving": 250}, ["lasagne"]),
    F("chicken noodle soup", 36, 2.5, 4.0, 1.2, 250, {"cup": 245, "bowl": 350, "can": 300}, ["soup", "noodle soup"]),
    F("tomato soup", 60, 1.5, 10.0, 1.8, 250, {"cup": 245, "bowl": 350, "can": 300}, []),
    F("chili", 110, 9.0, 11.0, 3.5, 250, {"cup": 250, "bowl": 350}, ["chili con carne", "beef chili", "chilli"]),
    F("chicken salad", 120, 12.0, 6.0, 5.5, 300, {"bowl": 300, "cup": 150}, ["grilled chicken salad", "caesar salad", "chicken caesar salad"]),
    F("greek salad", 90, 3.0, 5.0, 7.0, 250, {"bowl": 250, "cup": 150}, []),
    F("poke bowl", 130, 9.0, 16.0, 3.5, 400, {"bowl": 400}, ["poke", "salmon poke bowl", "tuna poke bowl"]),
    F("acai bowl", 120, 2.0, 24.0, 2.5, 350, {"bowl": 350}, ["acai"]),
    F("smoothie", 65, 1.5, 14.0, 0.6, 350, {"cup": 250, "glass": 350, "bottle": 400}, ["fruit smoothie", "berry smoothie", "banana smoothie"]),
    F("protein bar", 380, 30.0, 35.0, 12.0, 60, {"piece": 60, "bar": 60}, ["quest bar", "protein bars", "rxbar", "clif bar"]),
    F("granola bar", 471, 8.0, 64.0, 20.0, 40, {"piece": 40, "bar": 40}, ["granola bars", "nature valley bar", "oat bar", "cereal bar"]),
    F("chicken nuggets", 296, 15.5, 16.0, 19.0, 17, {"piece": 17, "nugget": 17}, ["nuggets", "mcnuggets", "chicken nugget"]),
    F("fried chicken", 246, 19.0, 9.0, 15.0, 140, {"piece": 140}, ["kfc", "fried chicken thigh", "fried chicken breast", "popeyes chicken"]),
    F("fish and chips", 195, 10.0, 18.0, 9.5, 400, {"plate": 400, "serving": 400}, []),
    F("pad thai", 150, 7.0, 20.0, 5.0, 350, {"plate": 350, "bowl": 350}, []),
    F("biryani", 165, 8.0, 22.0, 5.5, 300, {"plate": 300, "bowl": 300, "cup": 200}, ["chicken biryani", "veg biryani", "mutton biryani"]),
    F("samosa", 262, 4.7, 24.0, 17.0, 50, {"piece": 50}, ["samosas"]),
    F("dumplings", 190, 8.0, 22.0, 8.0, 30, {"piece": 30}, ["dumpling", "gyoza", "potstickers", "momos", "momo"]),
    F("spring roll", 200, 5.0, 25.0, 9.0, 60, {"piece": 60}, ["spring rolls", "egg roll", "egg rolls"]),
    F("falafel", 333, 13.3, 31.8, 17.8, 17, {"piece": 17}, ["falafels"]),
    F("shawarma", 180, 14.0, 15.0, 7.0, 300, {"piece": 300, "wrap": 300}, ["chicken shawarma", "doner", "doner kebab", "kebab", "gyro"]),
    F("omelette with cheese", 190, 13.0, 1.5, 15.0, 150, {"piece": 150}, ["cheese omelette", "cheese omelet"]),
    F("avocado toast", 220, 6.0, 22.0, 13.0, 110, {"piece": 110, "slice": 110}, []),
    F("french toast", 229, 7.7, 25.0, 11.0, 65, {"piece": 65, "slice": 65}, []),
    F("hash browns", 265, 3.0, 28.0, 16.0, 55, {"piece": 55, "patty": 55, "cup": 150}, ["hash brown", "hashbrowns"]),
    F("mac and cheese bowl", 164, 6.7, 20.0, 6.6, 300, {"bowl": 300}, []),
    # ---- Snacks & sweets ----------------------------------------------------
    F("potato chips", 536, 7.0, 53.0, 35.0, 28, {"bag": 28, "small bag": 28, "handful": 15, "oz": 28.35, "large bag": 150}, ["crisps", "lays", "doritos", "tortilla chips", "chips bag", "bag of chips"]),
    F("popcorn", 387, 12.0, 78.0, 4.5, 24, {"cup": 8, "bag": 80, "bowl": 40}, ["popped popcorn", "microwave popcorn", "air popped popcorn"]),
    F("pretzels", 380, 10.0, 80.0, 2.6, 28, {"handful": 28, "piece": 6, "bag": 40}, ["pretzel"]),
    F("dark chocolate", 546, 4.9, 61.0, 31.0, 20, {"square": 10, "piece": 10, "bar": 100, "oz": 28.35}, ["chocolate", "70% dark chocolate", "dark chocolate square"]),
    F("milk chocolate", 535, 7.7, 59.4, 29.7, 43, {"bar": 43, "square": 7, "piece": 7}, ["chocolate bar", "hershey bar", "dairy milk", "kitkat", "kit kat", "snickers", "twix", "mars bar"]),
    F("cookie", 488, 5.7, 64.0, 24.0, 30, {"piece": 30, "small": 15, "large": 60}, ["cookies", "chocolate chip cookie", "chocolate chip cookies", "biscuit", "biscuits", "oreo", "oreos"]),
    F("brownie", 466, 6.0, 50.0, 29.0, 56, {"piece": 56, "square": 56}, ["brownies"]),
    F("cake", 350, 4.5, 50.0, 15.0, 80, {"slice": 80, "piece": 80}, ["chocolate cake", "birthday cake", "slice of cake", "vanilla cake", "cheesecake"]),
    F("muffin", 377, 5.5, 53.0, 16.0, 110, {"piece": 110}, ["muffins", "blueberry muffin", "chocolate muffin"]),
    F("donut", 452, 4.9, 51.0, 25.0, 60, {"piece": 60}, ["doughnut", "donuts", "doughnuts", "glazed donut"]),
    F("ice cream", 207, 3.5, 24.0, 11.0, 66, {"scoop": 66, "cup": 132, "bowl": 132, "pint": 400, "cone": 100}, ["vanilla ice cream", "chocolate ice cream", "gelato"]),
    F("frozen yogurt", 127, 3.0, 22.0, 3.6, 87, {"scoop": 87, "cup": 174}, ["froyo"]),
    F("candy", 390, 0, 96.0, 0, 40, {"piece": 5, "bag": 40, "handful": 30}, ["gummy bears", "gummies", "sweets", "skittles", "haribo", "jelly beans", "lollies"]),
    F("croissant chocolate", 440, 8.0, 46.0, 25.0, 70, {"piece": 70}, ["pain au chocolat", "chocolate croissant"]),
    F("pastry", 400, 6.0, 45.0, 22.0, 80, {"piece": 80}, ["danish", "danish pastry", "cinnamon roll", "cinnamon bun"]),
    F("pie", 265, 2.5, 38.0, 12.0, 125, {"slice": 125, "piece": 125}, ["apple pie", "pumpkin pie", "slice of pie"]),
    F("energy drink", 45, 0, 11.0, 0, 250, {"can": 250, "bottle": 500}, ["red bull", "monster", "monster energy"]),
    F("gum", 250, 0, 65.0, 0, 3, {"piece": 3, "stick": 3}, ["chewing gum"]),
    # ---- Drinks -------------------------------------------------------------
    F("coffee", 1, 0.1, 0, 0, 240, {"cup": 240, "mug": 350, "shot": 30, "espresso": 30}, ["black coffee", "americano", "espresso", "cold brew", "drip coffee"]),
    F("latte", 50, 3.3, 5.0, 2.0, 350, {"cup": 350, "small": 240, "medium": 350, "large": 470, "grande": 470, "tall": 350, "venti": 590}, ["cafe latte", "flat white", "cappuccino", "oat latte", "oat milk latte", "milk coffee", "coffee with milk"]),
    F("mocha", 90, 3.0, 12.0, 3.5, 350, {"cup": 350, "grande": 470}, ["caramel macchiato", "frappuccino", "iced mocha", "pumpkin spice latte"]),
    F("tea", 1, 0, 0.3, 0, 240, {"cup": 240, "mug": 350}, ["green tea", "black tea", "herbal tea", "chai tea", "iced tea", "unsweetened tea"]),
    F("chai", 60, 1.5, 9.0, 2.0, 200, {"cup": 200, "glass": 200}, ["masala chai", "chai latte", "milk tea"]),
    F("orange juice", 45, 0.7, 10.4, 0.2, 248, {"cup": 248, "glass": 250, "bottle": 450}, ["oj", "juice", "apple juice", "fruit juice"]),
    F("soda", 41, 0, 10.6, 0, 355, {"can": 355, "bottle": 500, "cup": 240, "glass": 250, "large": 600}, ["coke", "coca cola", "pepsi", "sprite", "fanta", "cola", "soft drink", "pop", "fizzy drink"]),
    F("diet soda", 0, 0, 0, 0, 355, {"can": 355, "bottle": 500, "cup": 240}, ["diet coke", "coke zero", "pepsi max", "zero sugar soda", "sparkling water"]),
    F("beer", 43, 0.5, 3.6, 0, 355, {"can": 355, "bottle": 355, "pint": 473, "glass": 355}, ["lager", "ipa", "pint of beer", "light beer"]),
    F("wine", 83, 0.1, 2.6, 0, 150, {"glass": 150, "bottle": 750}, ["red wine", "white wine", "rose", "glass of wine", "prosecco", "champagne"]),
    F("spirits", 231, 0, 0, 0, 44, {"shot": 44, "glass": 44, "double": 88}, ["vodka", "whiskey", "whisky", "rum", "gin", "tequila", "bourbon", "shot of vodka", "shot of whiskey"]),
    F("cocktail", 150, 0, 13.0, 0, 150, {"glass": 150}, ["margarita", "mojito", "gin and tonic", "old fashioned", "espresso martini", "cosmopolitan"]),
    F("water", 0, 0, 0, 0, 250, {"cup": 240, "glass": 250, "bottle": 500, "liter": 1000, "litre": 1000}, ["sparkling water", "still water"]),
    F("coconut water", 19, 0.7, 3.7, 0.2, 240, {"cup": 240, "bottle": 330, "glass": 250}, []),
    F("hot chocolate", 77, 3.5, 12.0, 2.3, 250, {"cup": 250, "mug": 350}, ["hot cocoa", "cocoa"]),
    F("gatorade", 25, 0, 6.0, 0, 590, {"bottle": 590, "cup": 240}, ["sports drink", "powerade", "electrolyte drink"]),
    F("chocolate milk", 83, 3.2, 10.3, 3.4, 240, {"cup": 240, "glass": 250, "bottle": 400}, []),
    F("kombucha", 13, 0, 3.0, 0, 240, {"bottle": 480, "cup": 240, "glass": 250}, []),
    F("lemonade", 40, 0.1, 10.4, 0.1, 250, {"cup": 240, "glass": 250, "bottle": 500}, []),
]


def all_foods() -> list[Food]:
    return FOODS
