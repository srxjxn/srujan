// node --test web/parser.test.mjs   (mirrors tests/test_parser.py)
import { test } from "node:test";
import assert from "node:assert/strict";
import { FOODS } from "./foods.js";
import { FoodIndex, extractMeasure, parseText, foodFromServing, normalizeUnitWord } from "./parser.js";

const INDEX = new FoodIndex(FOODS);
const names = (t) => parseText(t, INDEX).map((i) => [i.food ? i.food.name : null, i.grams]);
const check = (text, qty, unit, food) => {
  const m = extractMeasure(text);
  assert.deepEqual([m.qty, m.unit, m.foodText], [qty, unit, food], text);
};

test("measure forms", () => {
  check("2 eggs", 2, null, "eggs");
  check("150g chicken breast", 150, "g", "chicken breast");
  check("150 g of chicken breast", 150, "g", "chicken breast");
  check("chicken breast 200g", 200, "g", "chicken breast");
  check("chicken breast (200 g)", 200, "g", "chicken breast");
  check("a banana", 1, null, "banana");
  check("an apple", 1, null, "apple");
  check("half a cup of rice", 0.5, "cup", "rice");
  check("1/2 cup oats", 0.5, "cup", "oats");
  check("1 1/2 cups rice", 1.5, "cup", "rice");
  check("2 slices of toast", 2, "slice", "toast");
  check("a couple of eggs", 2, null, "eggs");
  check("a dozen eggs", 12, null, "eggs");
  check("two and a half cups of rice", 2.5, "cup", "rice");
  check("6oz salmon", 6, "oz", "salmon");
  check("2x protein bar", 2, null, "protein bar");
  check("protein bar x2", 2, null, "protein bar");
  check("two large eggs", 2, "large", "eggs");
  check("half an avocado", 0.5, null, "avocado");
  check("1 tbsp peanut butter", 1, "tbsp", "peanut butter");
  check("rice 1 cup", 1, "cup", "rice");
  check("banana", null, null, "banana");
  check("2 tablespoons of olive oil", 2, "tbsp", "olive oil");
  check("500ml milk", 500, "ml", "milk");
});

test("multi item", () => {
  assert.deepEqual(names("2 eggs, 2 slices of toast and a banana"), [["egg", 100], ["bread", 60], ["banana", 118]]);
  assert.deepEqual(names("150g chicken breast with 1 cup rice"), [["chicken breast", 150], ["white rice", 158]]);
  assert.deepEqual(names("6oz salmon"), [["salmon", 170.1]]);
  assert.deepEqual(names("two and a half cups of rice and 3 eggs"), [["white rice", 395], ["egg", 150]]);
});

test("protected phrases", () => {
  assert.deepEqual(names("mac and cheese"), [["mac and cheese", 200]]);
  assert.deepEqual(names("a pb&j and a glass of milk"), [["pb&j", 120], ["whole milk", 250]]);
});

test("phrase and fuzzy", () => {
  assert.equal(names("grilled chicken breast with lemon and herbs")[0][0], "chicken breast");
  assert.deepEqual(names("chiken breast 100g"), [["chicken breast", 100]]);
  assert.deepEqual(names("2 scoops whey"), [["whey protein", 60]]);
});

test("unit fallbacks", () => {
  assert.deepEqual(names("1 cup egg"), [["egg", 240]]);
  assert.deepEqual(names("large banana"), [["banana", 136]]);
  assert.deepEqual(names("small apple"), [["apple", 150]]);
});

test("unknown and absurd", () => {
  const items = parseText("2 eggs and a plate of zorbulax", INDEX);
  assert.equal(items[0].food.name, "egg");
  assert.equal(items[1].food, null);
  assert.deepEqual([items[1].qty, items[1].unit, items[1].foodText], [1, "plate", "zorbulax"]);
  assert.equal(parseText("banana 20250921", INDEX)[0].food, null);
  assert.equal(parseText("2 bananas", INDEX)[0].grams, 236);
});

test("macros", () => {
  assert.deepEqual(parseText("100g chicken breast", INDEX)[0].macros, { kcal: 165, protein: 31, carbs: 0, fat: 3.6 });
});

test("saved foods: label helper and unit words", () => {
  const whey = foodFromServing({ name: "Gold Standard Whey", servingG: 31, kcal: 120, protein: 24, carbs: 3, fat: 1.5, servingUnit: "scoops", aliases: ["whey", "Protein Shake", "whey"] });
  assert.equal(whey.name, "gold standard whey");
  assert.equal(whey.serving_unit, "scoop");
  assert.deepEqual(whey.units, { serving: 31, scoop: 31 });
  assert.deepEqual(whey.aliases, ["whey", "protein shake"]);
  assert.throws(() => foodFromServing({ name: "x", servingG: 0, kcal: 1 }));
  for (const [word, want] of [["scoops", "scoop"], ["Scoop", "scoop"], ["tablespoons", "tbsp"], ["", "serving"], [null, "serving"], ["g", "serving"], ["pods", "pod"], ["patties", "patty"]]) {
    assert.equal(normalizeUnitWord(word), want, String(word));
  }
});

test("saved foods: log by the serving", () => {
  const whey = foodFromServing({ name: "gold standard whey", servingG: 31, kcal: 120, protein: 24, carbs: 3, fat: 1.5, servingUnit: "scoop", aliases: ["whey"] });
  const bar = foodFromServing({ name: "rx bar", servingG: 52, kcal: 210, protein: 12, carbs: 24, fat: 9, servingUnit: "bar" });
  const index = new FoodIndex([...FOODS, whey, bar]);
  const item = parseText("2 scoops whey", index)[0];
  assert.equal(item.food, whey);
  assert.equal(item.grams, 62);
  assert.deepEqual(item.macros, { kcal: 240, protein: 48, carbs: 6, fat: 3 });
  assert.equal(parseText("1.5 servings of gold standard whey", index)[0].macros.kcal, 180);
  assert.equal(parseText("half a scoop of whey", index)[0].macros.protein, 12);
  assert.equal(parseText("whey", index)[0].grams, 31);
  assert.equal(parseText("45g gold standard whey", index)[0].macros.kcal, 174.2);
  assert.deepEqual(parseText("2 rx bars and 2 eggs", index).map((i) => [i.food.name, i.grams]), [["rx bar", 104], ["egg", 100]]);
  index.reset(FOODS);
  assert.equal(parseText("1 scoop whey protein", index)[0].food.source, undefined);   // built-in again
});
