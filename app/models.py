from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext as _
from django.utils import timezone
from datetime import date, timedelta
from app import choices
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        abstract = True
        ordering = ["-created_at"]
        
class Page(models.Model):
    def __str__(self):
        return self.name
   
class Plan(BaseModel):
    plan_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=5, decimal_places=2)
    plan_type = models.CharField(max_length=10,choices=choices.PlanTypeChoices.choices)


    def __str__(self):
        return f"{self.plan_name}"

class Resturant(BaseModel):
    resturant_name = models.CharField(max_length=255)
    street_address = models.CharField(max_length=255,null=True,blank=True)
    city = models.CharField(max_length=255,null=True,blank=True)
    state = models.CharField(max_length=255,null=True,blank=True)
    zipcode = models.CharField(max_length=255,null=True,blank=True)
    country = models.CharField(max_length=255,null=True,blank=True)
    phone = models.CharField(max_length=255,null=True,blank=True)
    email = models.EmailField(null=True,blank=True)
    social_media = models.JSONField(null=True,blank=True)
    plan = models.ForeignKey(Plan,on_delete=models.SET_NULL,null=True,blank=True)
    plan_start_date = models.DateField(null=True,blank=True)
    plan_end_date = models.DateField(null=True,blank=True)

    def save(self, *args, **kwargs):
        is_plan_changed = False

        if self.pk:
            old_instance = Resturant.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.plan != self.plan:
                is_plan_changed = True

        if self.plan and (not self.plan_start_date or is_plan_changed):
            self.plan_start_date = date.today()

            # Set end date based on plan type
            plan_type = self.plan.plan_type
            if plan_type == choices.PlanTypeChoices.MONTHLY:
                self.plan_end_date = self.plan_start_date + timedelta(days=30)
            elif plan_type == choices.PlanTypeChoices.BIANNUALLY:
                self.plan_end_date = self.plan_start_date + timedelta(days=182)
            elif plan_type == choices.PlanTypeChoices.ANNUALLY:
                self.plan_end_date = self.plan_start_date + timedelta(days=365)
            else:
                # Fallback/default if type is missing or unexpected
                self.plan_end_date = self.plan_start_date + timedelta(days=30)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.resturant_name}"


class User(AbstractUser, BaseModel):
    profile = models.ImageField(upload_to="user_profile",null=True, blank=True)
    profile_image_url = models.URLField(null=True, blank=True, max_length=500)
    email = models.EmailField(_("Email"), unique=True, null=False)
    role = models.CharField(max_length=10, choices=choices.Usertypes.choices, default=choices.Usertypes.ADMIN)
    phone_number = models.CharField(max_length=20, default ="")
    date_of_birth = models.DateField(null=True, blank=True)
    street_address = models.CharField(max_length=256, default="")
    city = models.CharField(max_length=256, default="")
    state_province = models.CharField(max_length=256, default="")
    postal_code = models.CharField(max_length=20, default="")
    country = models.CharField(max_length=256, default="")
    is_password_changed = models.BooleanField(default=False)
    resturant = models.ForeignKey(Resturant,on_delete=models.SET_NULL,null=True,blank=True)

    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        if self.profile_image_url:
            self.profile = self.profile_image_url
        elif self.profile:
            self.profile_image_url = self.profile
        super().save(*args, **kwargs)

class PagePermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="page_permissions",null=True,blank=True)
    page_name = models.CharField(max_length=255)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "page_name")

    def __str__(self):
        return f"Permissions for {self.user.username} on {self.page_name}"
    
class Wine(models.Model):
    wine_name = models.CharField(max_length=100, default="")
    wine_type = models.CharField(max_length=50, default="")
    flavor = models.TextField(default="")
    profile = models.TextField(default="")
    reason_for_pairing = models.TextField(default="")
    proteins = models.CharField(max_length=255,null=True,blank=True)
    region_name = models.CharField(max_length=255,null=True,blank=True)

    class Meta:
        unique_together = ['wine_name', 'wine_type']
        
    def __str__(self):
        return f"{self.wine_name} ({self.wine_type})"

class RecipeImage_extra(BaseModel):
    image = models.ImageField(upload_to="recipe_images",null=True,blank=True)
    image_url = models.URLField(null=True, blank=True, max_length=500)
    def __str__(self):
        return str(self.id)

class Predefined_Ingredients(BaseModel):
    type = models.CharField(max_length=255,null=True,blank=True)
    name = models.CharField(max_length=256, unique=True,null=True,blank=True)
    
    def __str__(self):
        return self.name + " " + str(self.id)

class Predefined_Starch(BaseModel):
    type = models.CharField(max_length=255,null=True,blank=True)
    name = models.CharField(max_length=256, unique=True,null=True,blank=True)
    
    def __str__(self):
        return self.name + " " + str(self.id)

class Predefined_Vegetable(BaseModel):
    type = models.CharField(max_length=255,null=True,blank=True)
    name = models.CharField(max_length=256, unique=True,null=True,blank=True)
    
    def __str__(self):
        return self.name + " " + str(self.id)

class MenuCategoryies(BaseModel):
    category_name = models.CharField(max_length=256, unique=True,null=True,blank=True)
    
    def __str__(self):
        return self.category_name

class Recipe(BaseModel):
    wine_pairing = models.ManyToManyField(Wine, related_name="recipe_wine", blank=True, null=True)
    resturant = models.ForeignKey('Resturant', on_delete=models.SET_NULL, related_name="recipe_restaurant", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="recipe_user",null=True,blank=True)
    predefined_ingredients = models.ManyToManyField("Predefined_Ingredients",null=True,blank=True, related_name="recipe_predefined_ingredients")
    predefined_starch = models.ManyToManyField("Predefined_Starch",null=True,blank=True, related_name="recipe_predefined_starch")
    predefined_vegetables = models.ManyToManyField("Predefined_Vegetable",null=True,blank=True, related_name="recipe_predefined_vegetables")
    video = models.FileField(upload_to="recipe_videos", null=True, blank=True)
    manual_video = models.URLField(max_length=500, blank=True, null=True)
    cusinie_type = models.ForeignKey(MenuCategoryies, on_delete=models.SET_NULL, related_name="recipe_cusine_type", null=True, blank=True)
    dish_name = models.CharField(max_length=250, null=True, blank=True)
    preparation_time = models.CharField(max_length=100, null=True, blank=True)
    food_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    station_to_prepare_dish = models.CharField(max_length=256, null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True, max_length=500)
    description = models.TextField(null=True, blank=True)
    availability = models.CharField(max_length=256, choices=choices.Availability.choices, default = choices.Availability.AVAILABLE)
    status = models.CharField(max_length=256, choices=choices.RecipeStatus.choices, default = choices.RecipeStatus.PUBLIC)
    video_id = models.UUIDField(blank=True, null=True)
    is_draft = models.BooleanField(default=False)
    center_of_plate = models.CharField(max_length=256, null=True, blank=True)
    main_dish = models.CharField(max_length=256, null=True, blank=True)
    is_schedule = models.BooleanField(null=True,blank=True,default=False)
    caseCost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    caseWeightLb= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    servingWeightOz= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    servingsInCase= models.DecimalField(max_digits=10, decimal_places=2, null=True,blank=True) #servingsInCase
    costPerServing= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    foodCostPct= models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    salePrice= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    manualCostPerServing= models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.dish_name if self.dish_name else "N/A" + " " + str(self.id)

class recipe_images(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_image")
    image = models.ImageField(upload_to="recipe_image",null=True,blank=True)
    image_url = models.URLField(null=True, blank=True, max_length=500)

    def __str__(self):
        return str(self.id) + " " + str(self.recipe.dish_name + " " + str(self.recipe.id))
    
class Tag(BaseModel):
    name = models.CharField(max_length=100,null=True,blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_tag")
    
    def __str__(self):
        return self.name
    
class Ingredient(BaseModel):
    title = models.CharField(max_length=256,null=True,blank=True)
    quantity = models.CharField(max_length=256,null=True,blank=True)
    unit = models.CharField(max_length=256,null=True,blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredient", null=True, blank=True)
    
    def __str__(self):
        return self.title

class Essentials(BaseModel):
    title = models.CharField(max_length=256,null=True,blank=True)
    quantity = models.CharField(max_length=256,null=True,blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_essentials")
    unit = models.CharField(max_length=256, null=True, blank=True)
    def __str__(self):
        return self.title

class Steps(BaseModel):
    title = models.CharField(max_length=256,null=True,blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_steps")
    
    
    def __str__(self):
        return self.title
    
class Starch_Preparation(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="starch_preparation")
    image = models.ImageField(upload_to="starch_preparation", null=True, blank=True)
    title = models.CharField(max_length=256,null=True,blank=True)
    image_url = models.URLField(null=True, blank=True, max_length=500)
    def __str__(self):
        return self.title + " " + str(self.id)
    
class Starch_Preparation_Steps(BaseModel):
    step =  models.CharField(max_length=256,null=True,blank=True)
    starch_preparation = models.ForeignKey(Starch_Preparation, on_delete=models.CASCADE, related_name="starch")
       
    def __str__(self):
        return self.step + " " + str(self.id)
    
class Design_Your_Plate(BaseModel):
    image = models.ImageField(upload_to="design_your_plate", null=True, blank=True)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_Design_your_plate")
    image_url = models.URLField(null=True, blank=True, max_length=500)
    def __str__(self):
        return str(self.id)
    
class Design_Your_Plate_Steps(BaseModel):
    design_plate = models.ForeignKey(Design_Your_Plate, on_delete=models.CASCADE, related_name="design_steps")
    step = models.TextField(null=True,blank=True)

    def __str__(self):
        return self.step + " " + str(self.id)

class Cooking_Deviation_Comment(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_cooking_deviation_comment")
    step = models.CharField(max_length=256,null=True,blank=True)
 
    
    def __str__(self):
        return self.step

class Real_time_Variable_Comment(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_real_time_variable_comment")
    step = models.CharField(max_length=256,null=True,blank=True)
    
    def __str__(self):
        return self.step

class Recipe_Process_Audit(BaseModel):
    dish_name = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="manaul_dish_audit")
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="changed_by_audit",null=True,blank=True)
    changes_made = models.TextField(null=True,blank=True)
    datetime = models.DateTimeField(default=timezone.now)
    resturant = models.ForeignKey(Resturant, on_delete=models.SET_NULL, related_name="recipe_audit_restaurant", null=True, blank=True)

    def __str__(self):
        return self.changes_made + self.changed_by.username

class Rating(BaseModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="Rating")
    rating = models.PositiveSmallIntegerField(null=True,blank=True)
    comment = models.TextField(blank=True,  null=True)
    
    def __str__(self):
        return str(self.id) + str(self.rating) + self.comment
    
class Select_Holiday(BaseModel):
    holiday = models.CharField(max_length=256,null=True,blank=True)
    
    def __str__(self):
        return self.holiday
    
class Schedule_Dish(BaseModel):
    dish = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="dish_schedule")
    holiday = models.ForeignKey(Select_Holiday, on_delete=models.CASCADE, related_name="schedule_dish_holiday")
    schedule_datetime = models.DateTimeField(null=True,blank=True)
    season = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=15,  choices = choices.ScheduleStatus.choices, default=choices.ScheduleStatus.PENDING)
    job = models.CharField(max_length=256, null=True, blank=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="schedule_creator", null=True, blank=True)
    
    def __str__(self):
        return str(self.id) + str(self.dish) + str(self.schedule_datetime)
    
class Task(BaseModel):
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="staff",null=True,blank=True)
    task_name = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="task_name", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="staff_user",null=True,blank=True)
    task_description = models.TextField(null=True,blank=True)
    status = models.CharField(max_length=15, choices=choices.TaskGenericStatus.choices, default=choices.TaskGenericStatus.ASSIGNED)
    prority = models.CharField(max_length=15,null=True,blank=True, choices = choices.PriorityGenericLevel.choices, default = choices.PriorityGenericLevel.LOW)
    started_at = models.TimeField(blank=True, null=True)
    completed_at = models.TimeField(blank=True, null=True)
    kitchen_station = models.CharField(max_length=256,null=True,blank=True, default="")
    attachment_video_link = models.URLField(null=True,blank=True)
    due_date = models.DateTimeField(null=True,blank=True)
    other_task_name = models.CharField(max_length=256, null=True, blank=True)
    image = models.ImageField(upload_to="task_image", null=True, blank=True)
    image_url = models.URLField(null=True, blank=True, max_length=500)
    video = models.URLField(null=True, blank=True, max_length=500)
    resturant = models.ForeignKey(Resturant, on_delete=models.SET_NULL, related_name="task_restaurant", null=True, blank=True)
    
    def __str__(self):
        return str(self.id) + " " +self.task_name.dish_name + self.staff.username

class Message(BaseModel):
    task_id = models.ForeignKey(Task, on_delete=models.CASCADE,related_name="task")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="user",null=True,blank=True)
    message = models.TextField(null=True,blank=True)

class Notification(BaseModel):
    title = models.CharField(max_length=256)
    message = models.TextField(null=True,blank=True)
    related_dish = models.ForeignKey(to=Recipe, on_delete=models.CASCADE, related_name="related_dish")
    seen_by_users = models.ManyToManyField(User, related_name="seen_notifications")

    def __str__(self):
        return self.title + " " + str(self.id)

class MenuItems(BaseModel):
    category = models.ForeignKey(MenuCategoryies, on_delete=models.CASCADE, related_name="menu_category")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="menu_item_e", null=True, blank=True)
    item_name = models.CharField(max_length=256,null=True,blank=True)
    item_price = models.CharField(max_length=256,null=True,blank=True)
    item_description = models.TextField(null=True,blank=True)
    
    def __str__(self):
        return self.item_name + " " + str(self.id)

class Menu(BaseModel):
    menu_item = models.ManyToManyField(MenuItems, related_name="menu_item")
    recipes = models.ManyToManyField(Recipe, related_name="menu_recipes")
    title = models.CharField(max_length=256, unique=True,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    image = models.ImageField(upload_to='menu/',null=True,blank=True)    
    image_url = models.URLField(null=True, blank=True, max_length=500)
    def __str__(self):
        return str(self.id) + " " + self.title + " " + self.description
    
class MenuTemplateItems(BaseModel):
    recipe_id = models.IntegerField()
    main_dish = models.CharField(max_length=255)
    recipe_name = models.CharField(max_length=255)
    ingredients = models.TextField(null=True,blank=True)
    food_cost = models.DecimalField(max_digits=5, decimal_places=2,null=True,blank=True)
    is_special = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.main_dish} - {self.recipe_name}"

class MenuTemplate(BaseModel):
    title = models.CharField(max_length=255)
    sub_title = models.CharField(max_length=255,null=True,blank=True)
    location = models.CharField(max_length=255,null=True,blank=True)
    start_time = models.TimeField(null=True,blank=True)
    end_time = models.TimeField(null=True,blank=True)
    price_per_person = models.DecimalField(max_digits=5, decimal_places=2,null=True,blank=True)
    global_note = models.TextField(null=True, blank=True)
    logo_url = models.TextField(null=True,blank=True)
    sections = models.JSONField(null=True,blank=True)
    warning_note = models.TextField(null=True,blank=True)
    format = models.CharField(max_length=255,null=True, blank=True)
    template_type = models.CharField(max_length=255,null=True,blank=True)
    offer_text = models.TextField(null=True,blank=True)
    items = models.ManyToManyField(MenuTemplateItems,related_name='menu_items')
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="menu_template_restaurant", null=True, blank=True)

    def __str__(self):
        return f"{self.title}"


class LoginLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"


class InstructionalVideo(BaseModel):
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="instructional_video_restaurant", null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=[('youtube', 'YouTube'), ('local', 'Local')], default='youtube')
    source = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Video for {self.resturant.resturant_name} - {self.title} - {self.id}"

class ShiftNote(BaseModel):
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="shift_note_restaurant", null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="shift_note_created_by", null=True, blank=True)
    date = models.DateField(default=date.today)
    shift = models.CharField(max_length=50, choices=[('morning', 'Morning'), ('afternoon', 'Afternoon'), ('evening', 'Evening')], default='morning')
    note = models.TextField(null=True, blank=True)


    def __str__(self):
        return f"Shift Note for {self.resturant.resturant_name} - {self.created_at}"

class DictionaryCategory(BaseModel):
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="dictionary_restaurant", null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class DictionaryItem(BaseModel):
    category = models.ForeignKey(DictionaryCategory, on_delete=models.CASCADE, related_name="items")
    term = models.CharField(max_length=255)
    definition = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)


    def __str__(self):
        return f"{self.term} ({self.category.name})"


class EditorTemplate(BaseModel):
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="editor_restaurant", null=True, blank=True)
    title = models.CharField(max_length=255)
    image = models.URLField(null=True, blank=True, max_length=500)
    source = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "Editor"
        verbose_name_plural = "Editors"

class EditorImage(BaseModel):
    resturant = models.ForeignKey(Resturant, on_delete=models.CASCADE, related_name="editor_image_restaurant", null=True, blank=True)
    image = models.URLField(null=True, blank=True, max_length=500)

    class Meta:
        verbose_name = "Editor Image"
        verbose_name_plural = "Editor Images"