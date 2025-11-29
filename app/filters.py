import django_filters
from django.forms.widgets import TextInput
from django_filters import CharFilter, BooleanFilter, DateFilter, NumberFilter,ChoiceFilter,TimeFilter, DateTimeFilter, rest_framework as filters
from app.models import *
from django.db.models.query_utils import Q
from app import choices
from functools import reduce
from operator import or_


def placeholder(text):
    return TextInput(attrs={"placeholder": text})


class UserFilter(django_filters.FilterSet):
    email = CharFilter(field_name='email', lookup_expr='icontains')
    role = CharFilter(field_name='role', lookup_expr='iexact')
    city = CharFilter(field_name='city', lookup_expr='icontains')
    country = CharFilter(field_name='country', lookup_expr='icontains')
    is_active = BooleanFilter(field_name='is_active')
    created_at = DateFilter(field_name='created_at', lookup_expr='date')
    postal_code = CharFilter(field_name='postal_code', lookup_expr='icontains')
    phone_number = CharFilter(field_name='phone_number', lookup_expr='icontains')
    resturant = CharFilter(field_name='resturant', lookup_expr='exact')
    is_deleted = BooleanFilter(field_name='is_deleted')


    class Meta:
        model = User
        fields = ['email','resturant', 'role', 'city', 'country', 'is_active', 'created_at', 'postal_code', 'phone_number']

class WineFilter(django_filters.FilterSet):
    wine_name = CharFilter(field_name='wine_name', lookup_expr='icontains')
    wine_type = CharFilter(field_name='wine_type', lookup_expr='iexact')
    flavor_profile = CharFilter(field_name='flavor_profile', lookup_expr='icontains')
    price = NumberFilter(field_name='price', lookup_expr='iexact')

    class Meta:
        model = Wine
        fields = '__all__'

class RecipeFilter(django_filters.FilterSet):
    dish_name = django_filters.CharFilter(field_name='dish_name', lookup_expr='icontains')
    preparation_time = django_filters.NumberFilter(field_name='preparation_time', lookup_expr='exact')
    food_cost = django_filters.NumberFilter(field_name='food_cost', lookup_expr='exact')
    station_to_prepare_dish = django_filters.CharFilter(field_name='station_to_prepare_dish', lookup_expr='icontains')
    description = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    availability = django_filters.CharFilter(field_name='availability', lookup_expr='icontains')
    cusinie_type = django_filters.CharFilter(method='filter_cuisine_type')
    ingredients = django_filters.CharFilter(method='filter_by_ingredients')
    predefined_ingredients = django_filters.CharFilter(method='filter_by_predefined_ingredients')
    search = django_filters.CharFilter(method='global_search')
    wine_type = django_filters.CharFilter(method='filter_by_wine_type')
    main_dish = django_filters.CharFilter(field_name='main_dish', lookup_expr='exact')
    proteins = django_filters.CharFilter(method='filter_by_proteins')
    region = django_filters.CharFilter(method='filter_by_region')
    profile = django_filters.CharFilter(method='filter_by_profile')
    flavor = django_filters.CharFilter(method='filter_by_flavor')
    tag = django_filters.CharFilter(field_name='recipe_tag__name', lookup_expr='icontains')
    ingredients = filters.BaseInFilter(field_name='recipe_ingredient__title', lookup_expr='in')
    resturant = django_filters.CharFilter(field_name='resturant', lookup_expr='exact')
    is_draft = django_filters.BooleanFilter(field_name='is_draft')
    status = django_filters.ChoiceFilter(choices=choices.RecipeStatus.choices, field_name='status', lookup_expr='iexact')
    is_deleted = django_filters.BooleanFilter(field_name='is_deleted')
    
    def global_search(self, queryset, name, value):
        return queryset.filter(
            Q(dish_name__icontains=value) |
            Q(description__icontains=value) |
            Q(cusinie_type__category_name__icontains=value) |  
            Q(availability__icontains=value) |
            Q(status__icontains=value) |
            Q(station_to_prepare_dish__icontains=value) |
            Q(predefined_ingredients__name__icontains=value) |  
            Q(wine_pairing__wine_type__icontains=value)
        ).distinct()

    def filter_by_ingredients(self, queryset, name, value):
        ingredients = [ingredient.strip() for ingredient in value.split(',') if ingredient.strip()]
        
        if ingredients:
            query = reduce(or_, (Q(predefined_ingredients__name__icontains=ingredient) for ingredient in ingredients))
            return queryset.filter(query).distinct()
        
        return queryset

    def filter_by_predefined_ingredients(self, queryset, name, value):
        return queryset.filter(predefined_ingredients__name__icontains=value).distinct()

    def filter_by_wine_type(self, queryset, name, value):
        return queryset.filter(wine_pairing__wine_type__icontains=value).distinct()

    def filter_by_proteins(self, queryset, name, value):
        return queryset.filter(wine_pairing__proteins__icontains=value).distinct()
    
    def filter_by_region(self, queryset, name, value):
        return queryset.filter(wine_pairing__region_name__icontains=value).distinct()
    
    def filter_by_profile(self, queryset, name, value):
        return queryset.filter(wine_pairing__profile__icontains=value).distinct()
    
    def filter_by_flavor(self, queryset, name, value):
        return queryset.filter(wine_pairing__flavor__icontains=value).distinct()

    def filter_cuisine_type(self, queryset, name, value):
        if value:
            return queryset.filter(cusinie_type__id__icontains=value)
        return queryset

    class Meta:
        model = Recipe
        fields = [
            'dish_name', 'preparation_time', 'food_cost', 'station_to_prepare_dish','tag',
            'description', 'availability', 'cusinie_type', 'ingredients', 'search', 'wine_type'
        ]

class ScheduleDishFilter(django_filters.FilterSet):
    dish = CharFilter(field_name='dish__dish_name', lookup_expr='icontains')
    schedule_datetime = DateFilter(field_name='schedule_datetime', lookup_expr='date')
    season = CharFilter(field_name='season', lookup_expr='icontains')
    holiday = CharFilter(field_name='holiday__holiday', lookup_expr='icontains')
    status = CharFilter(field_name='status', lookup_expr='iexact')
    assign_to = CharFilter(field_name='assign_to__username', lookup_expr='icontains')

    class Meta:
        model = Schedule_Dish
        fields = '__all__'

class TaskFilter(django_filters.FilterSet):
    task_name = CharFilter(field_name='task_name__dish_name', lookup_expr='icontains')
    task_description = CharFilter(field_name='task_description', lookup_expr='icontains')
    status = ChoiceFilter(choices=choices.TaskGenericStatus.choices)
    priority = ChoiceFilter(choices = choices.PriorityGenericLevel.choices)
    kitchen_station = CharFilter(field_name='kitchen_station', lookup_expr='icontains')
    staff = CharFilter(field_name='staff__username', lookup_expr='icontains')
    started_at = TimeFilter(lookup_expr='gt')
    completed_at = TimeFilter(lookup_expr='gt')
    
    class Meta:
        model = Task
        fields = 'task_name','task_description','status','priority','kitchen_station','staff','started_at','completed_at'

class MessageFilter(django_filters.FilterSet):
    task_id = CharFilter(field_name='task_id__id', lookup_expr='exact')
    message = CharFilter(field_name='message', lookup_expr='icontains')
    user = CharFilter(field_name='user__username', lookup_expr='icontains')
    created_at = DateFilter(field_name='created_at', lookup_expr='date')

    class Meta:
        model = Message
        fields = '__all__'

class TagFilter(django_filters.FilterSet):
    name = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Tag
        fields = ['name']

class IngredientFilter(django_filters.FilterSet):
    title = CharFilter(field_name='title', lookup_expr='icontains')
    quantity = CharFilter(field_name='quantity', lookup_expr='icontains')
    unit = CharFilter(field_name='unit', lookup_expr='icontains')

    class Meta:
        model = Ingredient
        fields = '__all__'
        
class EssentialsFilter(django_filters.FilterSet):
    title = CharFilter(field_name='title', lookup_expr='icontains')
    quantity = NumberFilter(field_name='quantity', lookup_expr='exact')

    class Meta:
        model = Essentials
        fields = '__all__'

class StepsFilter(django_filters.FilterSet):
    title = CharFilter(field_name='title', lookup_expr='icontains')
    recipe = CharFilter(field_name='recipe__dish_name', lookup_expr='icontains')

    class Meta:
        model = Steps
        fields = '__all__'

class StarchPreparationFilter(django_filters.FilterSet):
    title = CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = Starch_Preparation
        fields = ['title']

class StarchPreparationStepsFilter(django_filters.FilterSet):
    step = CharFilter(field_name='step', lookup_expr='icontains')
    starch_preparation = CharFilter(field_name='starch_preparation__starch_name', lookup_expr='icontains')

    class Meta:
        model = Starch_Preparation_Steps
        fields = 'step', 'starch_preparation'

class PredefinedIngredientsFilter(django_filters.FilterSet):
    step = CharFilter(field_name='step', lookup_expr='icontains')

    class Meta:
        model = Predefined_Ingredients
        fields = ['step']

class CookingDeviationCommentFilter(django_filters.FilterSet):
    step = CharFilter(field_name='step', lookup_expr='icontains')

    class Meta:
        model = Cooking_Deviation_Comment
        fields = ['step']

class RealTimeVariableCommentFilter(django_filters.FilterSet):
    step = CharFilter(field_name='step', lookup_expr='icontains')

    class Meta:
        model = Real_time_Variable_Comment
        fields = ['step']

class RecipeProcessAuditFilter(django_filters.FilterSet):
    dish_name = CharFilter(field_name='dish_name__dish_name', lookup_expr='icontains')
    changed_by = CharFilter(field_name='changed_by__username', lookup_expr='icontains')
    datetime = DateTimeFilter()
    changes_made = CharFilter(lookup_expr='icontains')
    role = ChoiceFilter(choices=choices.Usertypes.choices)

    class Meta:
        model = Recipe_Process_Audit
        fields = '__all__'

class RatingFilter(django_filters.FilterSet):
    recipe = CharFilter(field_name='recipe__dish_name', lookup_expr='icontains')
    rating = NumberFilter(field_name='rating', lookup_expr='exact')
    comment = CharFilter(field_name='comment', lookup_expr='icontains')

    class Meta:
        model = Rating
        fields = '__all__'

class SelectHolidayFilter(django_filters.FilterSet):
    holiday = CharFilter(field_name='holiday', lookup_expr='icontains')

    class Meta:
        model = Select_Holiday
        fields = '__all__'


class TemplateGenerationRecipeFilter(filters.FilterSet):
    main_dish = filters.BaseInFilter(field_name='main_dish', lookup_expr='in')

    class Meta:
        model = Recipe
        fields = ['main_dish']