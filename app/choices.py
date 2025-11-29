from django.db import models
class Usertypes(models.TextChoices):
    SUPER_ADMIN = 'SA', 'Super Admin'
    ADMIN = 'A', 'Admin'
    HEAD_CHEF = "HF" , "Head Chef"
    STAFF = "S","Staff"

class PlanTypeChoices(models.TextChoices):
    MONTHLY = 'M','Monthly'
    BIANNUALLY = 'BA','Bi Annually'
    ANNUALLY = 'A','Annually'


class CuisineType(models.TextChoices):
    APPETIZERS = "AP", "Appetizers"
    SOUPS = "SO", "Soups"
    SALADS = "SA", "Salads"
    CHICKEN = "CH", "Chicken"
    LAMB = "LB", "Lamb"
    PORK = "PK", "Pork"
    STEAK = "SK", "Steak"
    FISH = "FS", "Fish"
    SHELLFISH = "SF", "Shellfish"
    VEGETARIAN = "VG", "Vegetarian"
    PASTA = "PS", "Pasta"
    SIDES = "SD", "Sides"
    BEURRE_BLANCS = "BB", "Beurre Blancs"
    FIVE_MOTHER_SAUCE = "FMS", "Five Mother Sauce"
    DESERTS = "DS", "Deserts"
    BEVERAGES = "BV", "Beverages"
    WINES = "WN", "Wines"

class RecipeGenericUnit(models.TextChoices):
    GRAMS = "G", "Grams"
    KILOGRAMS = "K", "Kilograms"

class RecipeStatus(models.TextChoices):
    PUBLIC = "P", "Public"
    PRIVATE = "PR", "Private"

class TaskGenericStatus(models.TextChoices):
    ASSIGNED = 'AS', 'Assigned'
    IN_PROGRESS = "IP", "In Progress"
    COMPLETED = "CP", "Completed"
    CANCELLED = 'CL', 'Cancelled'
    OVERDUE = "OD", "Over Due"

class ScheduleStatus(models.TextChoices):
    IN_PROGRESS = "IP", "In Progress"
    COMPLETED = "CP", "Completed"
    PENDING = "PD", "Pending"

class PriorityGenericLevel(models.TextChoices):
    HIGH = "H", "High"
    MEDIUM = "M", "Medium"
    LOW = "L", "Low"    

class  Availability(models.TextChoices):
    AVAILABLE = "A", "Available"
    LOW_STOCK = "LS", "Low Stock"
    OUT_OFF_STOCK = "OOS", "Out Of Stock"