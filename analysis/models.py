from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class FoodItem(models.Model):
    """
    Individual dish/food item eaten in a meal.
    """

    PORTION_CHOICES = [
        ("less", "Less"),
        ("normal", "Normal"),
        ("more", "More"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal = models.ForeignKey(
        "Meal", on_delete=models.CASCADE, related_name="food_items"
    )

    name = models.CharField(max_length=255)
    portion_size = models.CharField(max_length=10, choices=PORTION_CHOICES)

    # Nutritional info (per item)
    calories = models.FloatField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    carbohydrates = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)
    sugar = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.portion_size})"


class Meal(models.Model):
    """
    A meal uploaded by a user, containing multiple food items.
    """

    MEAL_TYPE_CHOICES = [
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("dinner", "Dinner"),
        ("snack", "Snack"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="meals")
    image = models.ImageField(upload_to="meal_images/")
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES)

    # Aggregated nutrition for the full meal
    total_calories = models.FloatField(null=True, blank=True)
    total_protein = models.FloatField(null=True, blank=True)
    total_carbohydrates = models.FloatField(null=True, blank=True)
    total_fat = models.FloatField(null=True, blank=True)
    total_fiber = models.FloatField(null=True, blank=True)
    total_sugar = models.FloatField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.meal_type} at {self.timestamp:%Y-%m-%d %H:%M}"


class AnalysisTask(models.Model):
    """
    Tracks Celery tasks for analysing a meal.
    Useful for checking async status.
    """

    TASK_STATUS = [
        ("PENDING", "Pending"),
        ("STARTED", "Started"),
        ("SUCCESS", "Success"),
        ("FAILURE", "Failure"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meal = models.ForeignKey(
        Meal, on_delete=models.CASCADE, related_name="analysis_tasks"
    )
    celery_task_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"Task {self.celery_task_id} ({self.status})"
