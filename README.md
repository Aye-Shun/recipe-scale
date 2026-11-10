# Recipe Scale

Recipe Scale adjusts ingredient quantities when you want more or fewer servings. Give it a recipe CSV and the old and new serving counts. It prints a new ingredient list in the same order.

## Try the pancake example

Use Python 3.11 or newer. The script uses the standard library.

```sh
python3 recipe_scale.py examples/pancakes.csv --from 4 --to 6
```

```text
4 to 6 servings
2 1/4 cups flour
1 7/8 cups milk
3 eggs
3/4 tsp salt
3 tbsp butter, melted
```

To use your own recipe, save a UTF-8 CSV with the header `quantity,unit,ingredient`. Quantities can be whole numbers, decimals like `0.5`, fractions like `3/4`, or mixed numbers like `1 1/2`. Leave the unit blank for things you count. Put fields that contain commas in quotes.

The script multiplies each amount by the serving ratio using Python's `Fraction`, then prints the result as a reduced fraction or mixed number. It reads the file without changing it. Recipe files can be up to 64 KiB and serving counts must be from 1 to 10,000. Units carry over as written. Cooking times and rounding decisions are up to you.

Run the tests with `python3 -m unittest discover -s tests`.
