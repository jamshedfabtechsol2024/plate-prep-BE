
from app import models, choices

def create_or_update_schedule_dish(dish_id):
    try:
        dish = models.Recipe.objects.get(id=dish_id)
        dish.status = choices.RecipeStatus.PUBLIC
        dish.save()   
        send_in_app_notifications_to_all(
            title="New Recipe Available!",
            message=f"The recipe '{dish.dish_name}' is now public and available to make.",
            related_dish_id=dish.id,
        )
    except (models.Recipe.DoesNotExist, models.User.DoesNotExist, models.Select_Holiday.DoesNotExist) as e:
        print(f"Failed to create Schedule_Dish: {e}")

def send_in_app_notifications_to_all(title, message, related_dish_id):
    try:
        recipe = models.Recipe.objects.get(id=related_dish_id)
        notification = models.Notification.objects.create(
            title=title,
            message=message,
            related_dish_id=recipe.id
        )
        notification.seen_by_users.set([])
        print(f"Notification created: {notification.title}")
        return notification
    except Exception as e:
        print(f"Failed to send notifications to all users: {e}")
        return None
