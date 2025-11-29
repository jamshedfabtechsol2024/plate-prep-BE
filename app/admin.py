from django.contrib import admin
from app import models

@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
        "is_superuser",
        "role",
        "is_active",
    )

@admin.register(models.PagePermission)
class PagePermissionAdmin(admin.ModelAdmin):
    list_display = ("id","user", "page_name", "can_view", "can_edit", "can_create", "can_delete")
    list_filter = ("id","user", "page_name")

@admin.register(models.Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ["id","dish_name","cusinie_type", "food_cost","status"]
    
@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id","name","recipe"]

@admin.register(models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["id","title","quantity","unit"]

@admin.register(models.Essentials)
class EssentialsAdmin(admin.ModelAdmin):
    list_display = ["id", "title","recipe"]

@admin.register(models.Steps)
class StepsAdmin(admin.ModelAdmin):
    list_display = ["id", "title","recipe"]

@admin.register(models.Starch_Preparation)
class StarchPreparationAdmin(admin.ModelAdmin):
    list_display = ["id", "title","recipe"]
    
@admin.register(models.Starch_Preparation_Steps)
class StarchPreparationStepAdmin(admin.ModelAdmin):
    list_display = ["id", "step"]

@admin.register(models.Design_Your_Plate)
class DesignYourPlateAdmin(admin.ModelAdmin):
    list_display = ["id","recipe"]

@admin.register(models.Design_Your_Plate_Steps)
class DesignYourPlateStepsAdmin(admin.ModelAdmin):
    list_display = ["id","step"]

@admin.register(models.Predefined_Ingredients)
class PredefinedIngredientsAdmin(admin.ModelAdmin):
    list_display = ["id", "type","name"]

@admin.register(models.Predefined_Starch)
class PredefinedStarchAdmin(admin.ModelAdmin):
    list_display = ["id", "type","name"]

@admin.register(models.Predefined_Vegetable)
class PredefinedVegetableAdmin(admin.ModelAdmin):
    list_display = ["id", "type","name"]

@admin.register(models.Cooking_Deviation_Comment)
class CookingDeviationCommentsAdmin(admin.ModelAdmin):
    list_display = ["id", "step","recipe"]

@admin.register(models.Real_time_Variable_Comment)
class RealTimeVariableCommentAdmin(admin.ModelAdmin):
    list_display = ["id", "step","recipe"]

@admin.register(models.Recipe_Process_Audit)
class RecipeProcessAudit(admin.ModelAdmin):
    list_display = "id","changes_made","datetime","changed_by"
    
@admin.register(models.Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ["id","rating","comment","recipe"]

@admin.register(models.Select_Holiday)
class SelectHolidayAdmin(admin.ModelAdmin):
    list_display = ["id","holiday"]

@admin.register(models.Message)
class RecipeMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "message","task_id",'user']

@admin.register(models.Schedule_Dish)
class ScheduleDishAdmin(admin.ModelAdmin):
    list_display  = ["id","dish","season", "schedule_datetime", "status"]

@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "task_description", "prority"]

@admin.register(models.Wine)
class WineAdmin(admin.ModelAdmin):
    list_display = ["id", "wine_name", "wine_type", "reason_for_pairing", "flavor"]

@admin.register(models.recipe_images)
class RecipeImageAdmin(admin.ModelAdmin):
    list_display = ["id","recipe","image"]

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id","title","message","related_dish"]

@admin.register(models.Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "description", "image", "is_deleted"]

@admin.register(models.MenuCategoryies)
class MenuCategoriesAdmin(admin.ModelAdmin):
    list_display = ["id","category_name"]

@admin.register(models.MenuItems)
class MenuItemsAdmin(admin.ModelAdmin):
    list_display = ["id","item_name","category","item_price","item_description"]

admin.site.register(models.MenuTemplate)
admin.site.register(models.MenuTemplateItems)
admin.site.register(models.Plan)
admin.site.register(models.Resturant)
admin.site.register(models.LoginLog)
admin.site.register(models.DictionaryCategory)
admin.site.register(models.DictionaryItem)