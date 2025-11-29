from django.core.management.base import BaseCommand
from app.models import MenuCategoryies
from app import models

class Command(BaseCommand):
    help = "Populate and update menu categories"

    def handle(self, *args, **options):
        categories = [
            {"category_name": "African"},
            {"category_name": "American"},
            {"category_name": "BBQ / Smoked"},
            {"category_name": "British / Irish"},
            {"category_name": "Brunch / Café"},
            {"category_name": "Caribbean"},
            {"category_name": "Chinese"},
            {"category_name": "Comfort Food"},
            {"category_name": "Eastern European"},
            {"category_name": "French"},
            {"category_name": "Fusion"},
            {"category_name": "German"},
            {"category_name": "Gluten-Free Friendly"},
            {"category_name": "Greek"},
            {"category_name": "Halal"},
            {"category_name": "Indian"},
            {"category_name": "Italian"},
            {"category_name": "Japanese"},
            {"category_name": "Korean"},
            {"category_name": "Kosher"},
            {"category_name": "Latin American"},
            {"category_name": "Mediterranean"},
            {"category_name": "Mexican"},
            {"category_name": "Middle Eastern"},
            {"category_name": "Paleo / Whole30"},
            {"category_name": "Plant-Based / Vegetarian"},
            {"category_name": "Spanish"},
            {"category_name": "Thai"},
            {"category_name": "Vegan"},
            {"category_name": "Vietnamese"},
        ]
        predefined_ingredients = [
            {"type":"Classic Sauces & Reductions","name": "Aioli / Garlic Mayo"},
            {"type":"Classic Sauces & Reductions","name": "Béchamel"},
            {"type":"Classic Sauces & Reductions","name": "Beurre Blanc"},
            {"type":"Classic Sauces & Reductions","name": "Demi-Glace"},
            {"type":"Classic Sauces & Reductions","name": "Espagnole"},
            {"type":"Classic Sauces & Reductions","name": "Gravy"},
            {"type":"Classic Sauces & Reductions","name": "Hollandaise"},
            {"type":"Classic Sauces & Reductions","name": "Pan Jus / Au Jus"},
            {"type":"Classic Sauces & Reductions","name": "Pesto"},
            {"type":"Classic Sauces & Reductions","name": "Romesco"},
            {"type":"Classic Sauces & Reductions","name": "Tomato Sauce"},
            {"type":"Classic Sauces & Reductions","name": "Velouté"},

            {"type": "Dressings & Vinaigrettes", "name": "Blue Cheese Dressing"},
            {"type": "Dressings & Vinaigrettes", "name": "Buttermilk Ranch"},
            {"type": "Dressings & Vinaigrettes", "name": "Caesar Dressing"},
            {"type": "Dressings & Vinaigrettes", "name": "Classic Vinaigrette (3:1 ratio)"},
            {"type": "Dressings & Vinaigrettes", "name": "Green Goddess"},
            {"type": "Dressings & Vinaigrettes", "name": "Honey Mustard"},

            {"type": "Soups, Broths & Stocks", "name": "Beef Stock"},
            {"type": "Soups, Broths & Stocks", "name": "Bisque (shellfish)"},
            {"type": "Soups, Broths & Stocks", "name": "Chicken Stock"},
            {"type": "Soups, Broths & Stocks", "name": "Consommé"},
            {"type": "Soups, Broths & Stocks", "name": "Fish Fumet"},
            {"type": "Soups, Broths & Stocks", "name": "Shellfish Stock"},
            {"type": "Soups, Broths & Stocks", "name": "Vegetable Stock"},

            {"type": "Butters, Compounds & Spreads", "name": "Clarified Butter"},
            {"type": "Butters, Compounds & Spreads", "name": "Compound Butters (e.g., truffle, herb)"},
            {"type": "Butters, Compounds & Spreads", "name": "Garlic Butter"},
            {"type": "Butters, Compounds & Spreads", "name": "Whipped Honey Butter"},

            {"type": "Starches, Grains & Bases", "name": "Mashed Potatoes"},
            {"type": "Starches, Grains & Bases", "name": "Polenta (soft or baked)"},
            {"type": "Starches, Grains & Bases", "name": "Rice Pilaf"},
            {"type": "Starches, Grains & Bases", "name": "Risotto Base"},

            {"type": "Dessert Sauces & Bases", "name": "Chantilly Cream"},
            {"type": "Dessert Sauces & Bases", "name": "Crème Anglaise"},
            {"type": "Dessert Sauces & Bases", "name": "Pastry Cream"},
            {"type": "Dessert Sauces & Bases", "name": "Simple Syrup"},
            {"type": "Dessert Sauces & Bases", "name": "Fruit Coulis"},

            {"type": "Vegetable Purees & Garnishes", "name": "Carrot Purée"},
            {"type": "Vegetable Purees & Garnishes", "name": "Celery Root Purée"},
            {"type": "Vegetable Purees & Garnishes", "name": "Gastrique"},
            {"type": "Vegetable Purees & Garnishes", "name": "Gremolata (herb-lemon garnish)"},
            {"type": "Vegetable Purees & Garnishes", "name": "Vegetable Coulis"},
        ]
        Starches=[
            {"type": "Potato-Based", "name": "Mashed Potatoes (classic, rustic, truffle, garlic)"},
            {"type": "Potato-Based", "name": "Roasted Potatoes (fingerling, Yukon gold, baby reds)"},
            {"type": "Potato-Based", "name": "Pommes Purée (fine French-style mash)"},
            {"type": "Potato-Based", "name": "Duchess Potatoes"},
            {"type": "Potato-Based", "name": "Gratin / Potatoes au Gratin"},
            {"type": "Potato-Based", "name": "Scalloped Potatoes"},
            {"type": "Potato-Based", "name": "French Fries / Frites"},
            {"type": "Potato-Based", "name": "Potato Croquettes"},
            {"type": "Potato-Based", "name": "Tater Tots / Hash Browns"},
            {"type": "Potato-Based", "name": "Sweet Potato Purée / Mash / Fries"},

            {"type": "Rice-Based", "name": "White Rice (long grain, jasmine, basmati)"},
            {"type": "Rice-Based", "name": "Brown Rice"},
            {"type": "Rice-Based", "name": "Wild Rice Blend"},
            {"type": "Rice-Based", "name": "Rice Pilaf"},
            {"type": "Rice-Based", "name": "Saffron Rice"},
            {"type": "Rice-Based", "name": "Sticky Rice / Sushi Rice"},
            {"type": "Rice-Based", "name": "Risotto (parmesan, mushroom, seafood, seasonal)"},
            {"type": "Rice-Based", "name": "Fried Rice (Asian, Cajun, Latin variants)"},
            {"type": "Rice-Based", "name": "Arroz con Gandules / Spanish-Style Rice"},

            {"type": "Grain & Legume-Based", "name": "Couscous (traditional or Israeli pearl)"},
            {"type": "Grain & Legume-Based", "name": "Farro"},
            {"type": "Grain & Legume-Based", "name": "Quinoa"},
            {"type": "Grain & Legume-Based", "name": "Barley"},
            {"type": "Grain & Legume-Based", "name": "Polenta (soft, baked, fried)"},
            {"type": "Grain & Legume-Based", "name": "Grits (cheese, shrimp, creamy)"},
            {"type": "Grain & Legume-Based", "name": "Lentils (du Puy, red, black)"},
            {"type": "Grain & Legume-Based", "name": "Bulgur Wheat"},

            {"type": "Pasta-Based", "name": "Mac & Cheese (classic, upscale, truffle)"},
            {"type": "Pasta-Based", "name": "Fettuccine / Linguine / Spaghetti"},
            {"type": "Pasta-Based", "name": "Orzo"},
            {"type": "Pasta-Based", "name": "Gnocchi (potato or ricotta-based)"},
            {"type": "Pasta-Based", "name": "Ravioli / Stuffed Pasta"},
            {"type": "Pasta-Based", "name": "Lasagna (as a side portion)"},

            {"type": "Other", "name": "Cornbread"},
            {"type": "Other", "name": "Spaetzle"},
            {"type": "Other", "name": "Plantains (mashed, fried)"},
            {"type": "Other", "name": "Cassava / Yuca Mash or Fries"},
            {"type": "Other", "name": "Bread Pudding (savory)"},
            {"type": "Other", "name": "Taro Root"},
            {"type": "Other", "name": "Bread Basket / Artisan Rolls (if served with butter)"}
        ]
        Vegetables=[
            {"type": "Green Vegetables", "name": "Asparagus (grilled, roasted, blanched)"},
            {"type": "Green Vegetables", "name": "Broccoli (steamed, roasted, charred)"},
            {"type": "Green Vegetables", "name": "Brussels Sprouts (roasted, shaved, crispy)"},
            {"type": "Green Vegetables", "name": "Green Beans (sautéed, almondine, blanched)"},
            {"type": "Green Vegetables", "name": "Zucchini (grilled, sautéed, ribbons)"},
            {"type": "Green Vegetables", "name": "Kale (sautéed, creamed, crispy)"},
            {"type": "Green Vegetables", "name": "Spinach (sautéed, creamed, raw)"},
            {"type": "Green Vegetables", "name": "Swiss Chard (braised, sautéed)"},
            {"type": "Green Vegetables", "name": "Collard Greens (braised, Southern-style)"},
            {"type": "Green Vegetables", "name": "Snap Peas / Snow Peas (sautéed, blanched)"},

            {"type": "Root Vegetables", "name": "Carrots (roasted, puréed, glazed)"},
            {"type": "Root Vegetables", "name": "Beets (roasted, pickled, puréed)"},
            {"type": "Root Vegetables", "name": "Parsnips (roasted, puréed)"},
            {"type": "Root Vegetables", "name": "Turnips (mashed, roasted)"},
            {"type": "Root Vegetables", "name": "Celery Root (Celeriac) (puréed, roasted, slaw)"},
            {"type": "Root Vegetables", "name": "Rutabaga (mash, roasted)"},
            {"type": "Root Vegetables", "name": "Radishes (roasted, pickled, raw shaved)"},
            {"type": "Root Vegetables", "name": "Sweet Potatoes (roasted, mash, wedges)"},

            {"type": "Alliums (Onion Family)", "name": "Onions (caramelized, crispy, grilled)"},
            {"type": "Alliums (Onion Family)", "name": "Leeks (braised, puréed, grilled)"},
            {"type": "Alliums (Onion Family)", "name": "Shallots (fried, vinaigrette, roasted)"},
            {"type": "Alliums (Onion Family)", "name": "Scallions (charred, raw, garnish)"},
            {"type": "Alliums (Onion Family)", "name": "Garlic (roasted, minced, confit)"},

            {"type": "Fungi", "name": "Mushrooms (Cremini, Shiitake, Oyster, etc.) (sautéed, roasted, grilled)"},
            {"type": "Fungi", "name": "Portobello (grilled, stuffed, sliced)"},

            {"type": "Seasonal / Specialty", "name": "Cauliflower (steaks, purée, roasted)"},
            {"type": "Seasonal / Specialty", "name": "Romanesco (roasted, grilled)"},
            {"type": "Seasonal / Specialty", "name": "Artichokes (braised, grilled, fried)"},
            {"type": "Seasonal / Specialty", "name": "Fennel (roasted, shaved raw, grilled)"},
            {"type": "Seasonal / Specialty", "name": "Butternut Squash (roasted, puréed)"},
            {"type": "Seasonal / Specialty", "name": "Acorn Squash (roasted, stuffed)"},
            {"type": "Seasonal / Specialty", "name": "Delicata Squash (roasted, crispy)"},

            {"type": "Other Versatile Options", "name": "Corn (grilled, creamed, succotash)"},
            {"type": "Other Versatile Options", "name": "Tomatoes (roasted, blistered, confit)"},
            {"type": "Other Versatile Options", "name": "Bell Peppers (roasted, sautéed, grilled)"},
            {"type": "Other Versatile Options", "name": "Eggplant (grilled, puréed, roasted)"},
            {"type": "Other Versatile Options", "name": "Cabbage (braised, grilled, slaw)"},
            {"type": "Other Versatile Options", "name": "Napa Cabbage / Bok Choy (stir-fried, steamed)"},
            {"type": "Other Versatile Options", "name": "Edamame (steamed, seasoned)"},
            {"type": "Other Versatile Options", "name": "Peas (purée, buttered, succotash)"}
        ]

        data = {
            "Dietary": {
                "description": "Types of eating patterns and food restrictions in relation to health and nutrition.",
                "items": [
                    {"term": "Vegetarian", "definition": "A person who does not eat meat, fish, or poultry.", "description": "Excludes meat, fish, and poultry. Includes plant-based foods, dairy products, and eggs."},
                    {"term": "Vegan", "definition": "A person who does not eat or use any animal products.", "description": "Excludes all animal products including meat, dairy, eggs, and honey. Focuses solely on plant-based foods."},
                    {"term": "Pescatarian", "definition": "A person who eats fish and seafood but no other meat.", "description": "Includes fish and seafood but excludes meat and poultry. Often includes dairy and eggs."},
                    {"term": "Paleo", "definition": "A diet based on whole foods presumed to be eaten in the Paleolithic era.", "description": "Emphasizes whole foods such as lean meats, fish, fruits, vegetables, nuts, and seeds. Excludes processed foods, grains, and legumes."},
                    {"term": "Keto", "definition": "A high-fat, low-carbohydrate diet that induces ketosis.", "description": "High-fat, low-carbohydrate diet aiming to put the body in a state of ketosis. Includes meats, dairy, low-carb vegetables, and healthy fats."},
                    {"term": "Gluten-Free", "definition": "A diet that excludes gluten proteins.", "description": "Avoids all foods containing gluten, found in wheat, barley, and rye. Can include naturally gluten-free foods like fruits, vegetables, meat, rice, and quinoa."},
                    {"term": "Mediterranean", "definition": "A diet inspired by eating habits of Mediterranean countries.", "description": "Emphasizes fruits, vegetables, whole grains, olive oil, fish, lean meats, and moderate wine consumption."},
                    {"term": "Whole30", "definition": "A 30-day elimination program for specific food groups.", "description": "Eliminates sugar, alcohol, grains, legumes, soy, and dairy for 30 days. Focuses on meat, seafood, eggs, vegetables, and healthy fats."},
                    {"term": "Intermittent Fasting", "definition": "An eating pattern cycling between fasting and eating periods.", "description": "Not a diet per se, but an eating pattern such as 16/8 or 5:2."},
                    {"term": "Low-FODMAP", "definition": "A diet low in fermentable carbohydrates to reduce digestive distress.", "description": "Eliminates foods high in fermentable oligo-, di-, monosaccharides, and polyols to help manage IBS and reduce gas and bloating."}
                ]
            },
            "Kitchen Terms": {
                "description": "Common culinary techniques and terminology used in the kitchen.",
                "items": [
                    {"term": "Al Dente", "definition": "Firm to the bite.", "description": "Italian term meaning 'to the tooth,' referring to pasta or vegetables cooked until they are still slightly firm."},
                    {"term": "Blanch", "definition": "Briefly cooking in boiling water then shocking in ice water.", "description": "Used to preserve color, flavor, and texture by plunging food into boiling water then into ice water to stop cooking."},
                    {"term": "Braise", "definition": "Sear then slow-cook in liquid.", "description": "Involves searing food at high temperature and then simmering slowly in liquid, usually in a covered pot."},
                    {"term": "Chiffonade", "definition": "Thinly slicing leafy herbs or vegetables.", "description": "A knife technique for cutting leafy vegetables or herbs into fine ribbons."},
                    {"term": "Julienne", "definition": "Cutting into matchstick-sized strips.", "description": "A knife technique that produces long, thin strips resembling matchsticks."},
                    {"term": "Mise en Place", "definition": "Everything in its place.", "description": "French phrase referring to preparing and organizing all ingredients before cooking."},
                    {"term": "Reduce", "definition": "Thicken and concentrate flavor by simmering.", "description": "Process of intensifying a liquid’s flavor and texture by evaporating water through simmering or boiling."},
                    {"term": "Sauté", "definition": "Quickly cooking in a small amount of fat over high heat.", "description": "Technique for cooking food swiftly in oil or butter to develop flavor and color."},
                    {"term": "Simmer", "definition": "Cooking just below boiling point.", "description": "Gently cooking foods in liquid at a temperature where small bubbles rise occasionally."},
                    {"term": "Sous-vide", "definition": "Vacuum-sealed cooking in a controlled water bath.", "description": "Method where food is sealed in a bag and cooked at a precise, consistent temperature in water for even doneness."},
                    {"term": "Sweat", "definition": "Cooking vegetables in fat without browning.", "description": "Cooking vegetables slowly in fat to soften them and release moisture without color change."},
                    {"term": "Deglaze", "definition": "Dissolve browned bits from pan with liquid.", "description": "Adding liquid to a hot pan to lift and dissolve food particles stuck on the bottom, forming a flavorful base for sauces."},
                    {"term": "Zest", "definition": "Outer colored peel of citrus used for flavor.", "description": "Removing the colored outer layer of citrus fruit with a grater or zester to add aromatic flavor."}
                ]
            },
            "Kitchen Stations": {
                "description": "Distinct sections of a professional kitchen responsible for specific tasks.",
                "items": [
                    {"term": "Garde Manger (Cold Station)", "definition": "Prepares cold dishes and presentations.", "description": "Responsible for salads, cold appetizers, charcuterie, and dressings, often handling final plating of these items."},
                    {"term": "Grill Station", "definition": "Handles grilling and broiling of proteins and vegetables.", "description": "Works with grills, broilers, and planchas to prepare meats and vegetables over direct heat."},
                    {"term": "Sauté Station", "definition": "Prepares pan-fried dishes and sauces.", "description": "Specializes in quick-cooking methods like pan-frying and sautéing, as well as finishing sauces."},
                    {"term": "Fry Station", "definition": "Deep-fries foods to crisp perfection.", "description": "Manages fryers for items such as fries, chicken, and seafood to ensure proper texture and doneness."},
                    {"term": "Roast Station", "definition": "Roasts large cuts of meat and baked dishes.", "description": "In charge of roasting meats, whole animals, and sometimes preparing gratins or similar oven-baked items."},
                    {"term": "Pastry Station", "definition": "Bakes pastries, breads, and desserts.", "description": "Focused on dessert and bread production including pastries, cakes, and relevant sauces or fillings."},
                    {"term": "Soup and Sauce (Saucier) Station", "definition": "Prepares stocks, soups, and sauces.", "description": "Creates foundational liquids and sauces used throughout service, often regarded as a senior station role."},
                    {"term": "Expeditor (Expo) Station", "definition": "Coordinates and inspects final dishes.", "description": "Acts as the communication hub between front-of-house and kitchen, checking tickets and ensuring timely, correct service."},
                    {"term": "Butcher Station", "definition": "Portions and readies meats and poultry.", "description": "Responsible for breaking down, portioning, and preparing all cuts of meat, fish, and poultry."},
                    {"term": "Prep Station", "definition": "Prepares ingredients before service.", "description": "Handles washing, chopping, and portioning ingredients needed by all other stations, often before opening."},
                    {"term": "Beverage Station", "definition": "Manages drink service.", "description": "Prepares all beverages, including cocktails, coffee, tea, and other non-alcoholic drinks."}
                ]
            },
            "Five Mother Sauces": {
                "description": "The five foundational sauces of classical French cuisine.",
                "items": [
                    {"term": "Béchamel Sauce", "definition": "White sauce made from roux and milk.", "description": "A creamy, white sauce from a roux of butter and flour combined with milk; base for sauces like Mornay and used in lasagna and gratins."},
                    {"term": "Velouté Sauce", "definition": "Light sauce made from blond roux and stock.", "description": "Smooth sauce created by mixing a blond roux with a clear stock (chicken, fish, or veal); base for sauces like Supreme and Normandy."},
                    {"term": "Tomato Sauce", "definition": "Rich sauce made from tomatoes and aromatics.", "description": "Made by cooking tomatoes with onions, garlic, and herbs; can be vegetarian or include meat, used for pastas and stews."},
                    {"term": "Espagnole (Brown) Sauce", "definition": "Dark sauce from brown roux and stock.", "description": "Rich sauce from brown roux, tomatoes, mirepoix, and beef or veal stock; base for demi-glace and often enriched with mushrooms or herbs."},
                    {"term": "Hollandaise Sauce", "definition": "Emulsified sauce of egg yolks and butter.", "description": "An emulsion of egg yolks, melted butter, and lemon juice or vinegar; served over eggs Benedict, asparagus, fish, and vegetables."}
                ]
            },
            "Chef Positions": {
                "description": "Key roles and hierarchy within a professional kitchen.",
                "items": [
                    {"term": "Executive Chef (Chef de Cuisine)", "definition": "Head of kitchen operations and menu design.", "description": "Overall in charge of menu creation, staffing, and management of the entire kitchen."},
                    {"term": "Sous Chef", "definition": "Second-in-command to the executive chef.", "description": "Assists the executive chef, oversees day-to-day operations, and manages staff in their absence."},
                    {"term": "Chef de Partie (Station Chef)", "definition": "Leads a specific kitchen station.", "description": "Manages one station (e.g., grill, sauté, pastry) and prepares dishes for that section."},
                    {"term": "Pastry Chef (Pâtissier)", "definition": "Specialist in baked goods and desserts.", "description": "Focuses on pastries, breads, and other dessert preparations."},
                    {"term": "Banquet Chef", "definition": "Coordinates large-scale event meals.", "description": "Plans and executes menus for banquets and catering events."},
                    {"term": "Butcher (Boucher)", "definition": "Prepares and breaks down meats.", "description": "Handles portioning, deboning, and trimming of meat, fish, and poultry."},
                    {"term": "Expediter (Expo)", "definition": "Final checker and communicator.", "description": "Ensures dishes are correct, plated properly, and delivered on time between kitchen and service staff."},
                    {"term": "Sauce Chef (Saucier)", "definition": "Prepares sauces and stocks.", "description": "Responsible for the creation of sauces, stocks, and gravies; considered a senior kitchen role."},
                    {"term": "Garde Manger (Cold Station Chef)", "definition": "Chef for cold dishes and appetizers.", "description": "Prepares salads, cold appetizers, and charcuterie."},
                    {"term": "Commis Chef", "definition": "Junior cook learning station duties.", "description": "Entry-level position assisting chefs in various tasks to learn the ropes."},
                    {"term": "Kitchen Porter (Dishwasher)", "definition": "Supports kitchen cleanliness and prep.", "description": "Handles dishwashing and basic prep tasks to support the kitchen brigade."}
                ]
            }
        }

        existing_categories = set(MenuCategoryies.objects.values_list("category_name", flat=True))
        
        for category in categories:
            if category["category_name"] not in existing_categories:
                MenuCategoryies.objects.create(**category)
        self.stdout.write(self.style.SUCCESS("Menu categories populated successfully."))

        for veg in Vegetables:
            _, _ = models.Predefined_Vegetable.objects.update_or_create(
                name=veg["name"],
                defaults={
                    "type": veg.get("type", None)
                }
            )
        self.stdout.write(self.style.SUCCESS("Vegetables populated successfully."))

        for starch in Starches:
            _, _ = models.Predefined_Starch.objects.update_or_create(
                name=starch["name"],
                defaults={
                    "type": starch.get("type", None)
                }
            )
        self.stdout.write(self.style.SUCCESS("Starches populated successfully."))

        for ing in predefined_ingredients:
            _, _ = models.Predefined_Ingredients.objects.update_or_create(
                name=ing["name"],
                defaults={
                    "type": ing.get("type", None)
                }
            )
        self.stdout.write(self.style.SUCCESS("Ingredients populated successfully."))


        for category_name, category_data in data.items():
            category, _ = models.DictionaryCategory.objects.update_or_create(
                name=category_name,
                defaults={"description": category_data["description"]}
            )

            for item in category_data["items"]:
                models.DictionaryItem.objects.update_or_create(
                    category=category,
                    term=item["term"],
                    defaults={
                        "definition": item["definition"],
                        "description": item["description"]
                    }
                )

        self.stdout.write(self.style.SUCCESS("Dictionary categories and items populated successfully."))

