import os
import uuid
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage

from .models import Meal
from .tasks import analyse_meal


@csrf_exempt
def upload_meal(request):
    """
    Accepts a file upload (meal image), saves it locally in MEDIA_ROOT,
    creates Meal, triggers Celery task, and returns meal_id.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    user = request.user if request.user.is_authenticated else None

    if "image" not in request.FILES:
        return JsonResponse({"error": "No image file uploaded"}, status=400)

    file = request.FILES["image"]
    filename = f"meals/{uuid.uuid4()}_{file.name}"
    saved_path = default_storage.save(filename, file)  # stored in MEDIA_ROOT
    image_url = os.path.join(settings.MEDIA_URL, saved_path)

    meal_type = request.POST.get("meal_type", "lunch")

    # Create Meal (analysis not yet ready)
    meal = Meal.objects.create(
        user=user,
        image_url=image_url,
        meal_type=meal_type,
        timestamp=timezone.now(),
    )

    # Trigger Celery task
    analyse_meal.delay(meal.id)

    return JsonResponse(
        {
            "message": "Meal uploaded successfully. Analysis started.",
            "meal_id": meal.id,
            "image_url": image_url,
        },
        status=201,
    )


def get_meal_result(request, meal_id):
    """
    Returns analysed result of the meal. Poll until status=done.
    """
    try:
        meal = Meal.objects.get(id=meal_id)
    except Meal.DoesNotExist:
        return JsonResponse({"error": "Meal not found"}, status=404)

    if meal.total_calories is None:
        return JsonResponse({"status": "pending", "meal_id": meal.id})

    food_items = []
    for item in meal.food_items.all():
        food_items.append(
            {
                "name": item.name,
                "portion_size": item.portion_size,
                "nutrition": {
                    "calories": item.calories,
                    "protein": item.protein,
                    "carbohydrates": item.carbohydrates,
                    "fat": item.fat,
                    "fiber": item.fiber,
                    "sugar": item.sugar,
                },
            }
        )

    return JsonResponse(
        {
            "status": "done",
            "meal_id": meal.id,
            "meal_type": meal.meal_type,
            "timestamp": meal.timestamp,
            "image_url": meal.image_url,
            "total_nutrition": {
                "calories": meal.total_calories,
                "protein": meal.total_protein,
                "carbohydrates": meal.total_carbohydrates,
                "fat": meal.total_fat,
                "fiber": meal.total_fiber,
                "sugar": meal.total_sugar,
            },
            "food_items": food_items,
        }
    )
