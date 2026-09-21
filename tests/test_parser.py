import unittest

from food_tracker.foods import FOODS
from food_tracker.parser import FoodIndex, extract_measure, parse_text

INDEX = FoodIndex(FOODS)


def parse(text):
    return parse_text(text, INDEX)


class MeasureTests(unittest.TestCase):
    def check(self, text, qty, unit, food):
        m = extract_measure(text)
        self.assertEqual((m.qty, m.unit, m.food_text), (qty, unit, food), text)

    def test_forms(self):
        self.check("2 eggs", 2, None, "eggs")
        self.check("150g chicken breast", 150, "g", "chicken breast")
        self.check("150 g of chicken breast", 150, "g", "chicken breast")
        self.check("chicken breast 200g", 200, "g", "chicken breast")
        self.check("chicken breast (200 g)", 200, "g", "chicken breast")
        self.check("a banana", 1, None, "banana")
        self.check("an apple", 1, None, "apple")
        self.check("half a cup of rice", 0.5, "cup", "rice")
        self.check("1/2 cup oats", 0.5, "cup", "oats")
        self.check("1 1/2 cups rice", 1.5, "cup", "rice")
        self.check("2 slices of toast", 2, "slice", "toast")
        self.check("a couple of eggs", 2, None, "eggs")
        self.check("a dozen eggs", 12, None, "eggs")
        self.check("two and a half cups of rice", 2.5, "cup", "rice")
        self.check("6oz salmon", 6, "oz", "salmon")
        self.check("2x protein bar", 2, None, "protein bar")
        self.check("protein bar x2", 2, None, "protein bar")
        self.check("two large eggs", 2, "large", "eggs")
        self.check("half an avocado", 0.5, None, "avocado")
        self.check("1 tbsp peanut butter", 1, "tbsp", "peanut butter")
        self.check("rice 1 cup", 1, "cup", "rice")
        self.check("banana", None, None, "banana")
        self.check("2 tablespoons of olive oil", 2, "tbsp", "olive oil")
        self.check("500ml milk", 500, "ml", "milk")


class ParseTests(unittest.TestCase):
    def names(self, text):
        return [(i.food.name if i.food else None, i.grams) for i in parse(text)]

    def test_multi_item(self):
        self.assertEqual(
            self.names("2 eggs, 2 slices of toast and a banana"),
            [("egg", 100.0), ("bread", 60.0), ("banana", 118.0)],
        )

    def test_grams_and_oz(self):
        self.assertEqual(self.names("150g chicken breast with 1 cup rice"),
                         [("chicken breast", 150.0), ("white rice", 158.0)])
        self.assertEqual(self.names("6oz salmon"), [("salmon", 170.1)])

    def test_protected_and(self):
        self.assertEqual(self.names("mac and cheese"), [("mac and cheese", 200.0)])
        self.assertEqual(self.names("a pb&j and a glass of milk"),
                         [("pb&j", 120.0), ("whole milk", 250.0)])

    def test_phrase_and_fuzzy(self):
        self.assertEqual(self.names("grilled chicken breast with lemon and herbs")[0][0], "chicken breast")
        self.assertEqual(self.names("chiken breast 100g"), [("chicken breast", 100.0)])
        self.assertEqual(self.names("2 scoops whey"), [("whey protein", 60.0)])

    def test_units_fallback(self):
        # egg has no "cup" unit -> generic 240g
        self.assertEqual(self.names("1 cup egg"), [("egg", 240.0)])
        # size multiplier when food has no explicit unit
        self.assertEqual(self.names("large banana"), [("banana", 136.0)])
        self.assertEqual(self.names("small apple"), [("apple", 150.0)])

    def test_unknown(self):
        items = parse("2 eggs and a plate of zorbulax")
        self.assertEqual(items[0].food.name, "egg")
        self.assertIsNone(items[1].food)
        self.assertEqual((items[1].qty, items[1].unit, items[1].food_text), (1, "plate", "zorbulax"))

    def test_absurd_amount_rejected(self):
        items = parse("banana 20250921")
        self.assertIsNone(items[0].food)
        self.assertEqual(parse("2 bananas")[0].grams, 236.0)

    def test_macros(self):
        item = parse("100g chicken breast")[0]
        self.assertEqual(item.macros, {"kcal": 165.0, "protein": 31.0, "carbs": 0.0, "fat": 3.6})


if __name__ == "__main__":
    unittest.main()
