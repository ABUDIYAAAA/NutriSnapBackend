import io
import requests
from PIL import Image
from celery import shared_task
from django.conf import settings
from .models import Meal, FoodItem

import google.generativeai as genai
from groq import Groq


genai.configure(api_key="AIzaSyBDk7ceBZ1u9UeDVf8vZJ7V77rNyUMuiKU")
groq_client = Groq(api_key="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")


@shared_task
def analyse_meal(meal_id):
    """
    Full pipeline:
    1. Use Gemini to detect dishes
    2. Crop images for each dish
    3. Re-analyse per dish
    4. Aggregate and save in DB
    """
    meal = Meal.objects.get(id=meal_id)

    # 1️⃣ Download original image
    resp = requests.get(meal.image_url)
    image = Image.open(io.BytesIO(resp.content))

    # 2️⃣ Ask Gemini to detect bounding boxes
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = """
    You are a food detector. Return a JSON list of bounding boxes for dishes in this image.
    Format: [{"name": "dish name", "box": [x,y,width,height]}]
    """
    gemini_response = model.generate_content([prompt, image])
    dish_boxes = gemini_response.text  # assume Gemini returns JSON

    import json

    dishes = json.loads(dish_boxes)

    total_nutrition = {
        "calories": 0,
        "protein": 0,
        "carbohydrates": 0,
        "fat": 0,
        "fiber": 0,
        "sugar": 0,
    }

    # 3️⃣ Loop through dishes and crop each
    for d in dishes:
        x, y, w, h = d["box"]
        cropped = image.crop((x, y, x + w, y + h))

        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        buf.seek(0)

        # 4️⃣ Re-send cropped dish to Gemini/Groq for nutrition
        nutri_prompt = f"""
        Analyse this dish '{d['name']}' and return JSON:
        {{
          "calories": int,
          "protein": float,
          "carbohydrates": float,
          "fat": float,
          "fiber": float,
          "sugar": float
        }}
        """
        nutri_response = model.generate_content([nutri_prompt, cropped])
        nutrition = json.loads(nutri_response.text)

        # 5️⃣ Save FoodItem
        food_item = FoodItem.objects.create(
            meal=meal,
            name=d["name"],
            portion_size="normal",  # placeholder
            calories=nutrition["calories"],
            protein=nutrition["protein"],
            carbohydrates=nutrition["carbohydrates"],
            fat=nutrition["fat"],
            fiber=nutrition["fiber"],
            sugar=nutrition["sugar"],
        )

        # accumulate totals
        for k in total_nutrition:
            total_nutrition[k] += nutrition[k]

    # 6️⃣ Save back to Meal
    meal.total_calories = total_nutrition["calories"]
    meal.total_protein = total_nutrition["protein"]
    meal.total_carbohydrates = total_nutrition["carbohydrates"]
    meal.total_fat = total_nutrition["fat"]
    meal.total_fiber = total_nutrition["fiber"]
    meal.total_sugar = total_nutrition["sugar"]
    meal.save()

    return {"meal_id": meal.id, "dishes": len(dishes)}
