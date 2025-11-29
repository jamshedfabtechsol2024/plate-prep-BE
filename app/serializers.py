from django.utils import timezone
from rest_framework.serializers import ModelSerializer
from app import models, choices
from rest_framework import serializers
from django.db.models import Avg, Count
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from dateutil import parser
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from datetime import date, timedelta, datetime
import json, re
from app.utils import format_datetime
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import AuthenticationFailed
from collections import defaultdict
from app.utils import S3FileUtility
# import language_tool_python 

s3_utility = S3FileUtility()

def BuildTime(created_at):
    today = timezone.now().date()
    if today == created_at.date():
        date = created_at.time().strftime("%I:%M %p")
    else:
        date = f"{created_at.date()} {created_at.time().strftime('%I:%M %p')}"
    return date

class PlanViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Plan
        fields =["plan_name","plan_type"]



class ResturantSerializer(serializers.ModelSerializer):
    plan = PlanViewSerializer(read_only=True)
    class Meta:
        model = models.Resturant
        fields = '__all__'
        read_only_fields = ['created_at','updated_at','plan_start_date', 'plan_end_date']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    resturant = ResturantSerializer()
    class Meta:
        model = models.User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "role",
            "is_password_changed",
            "resturant",

        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            "is_password_changed":{'read_only':True}
        }


    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


    def create(self, validated_data):

        from django.db import transaction
        with transaction.atomic():
            password = validated_data.pop('password', None)
            resturant = validated_data.pop('resturant', None)
            
            resturant = models.Resturant.objects.create(**resturant)
            user = models.User(
                **validated_data,
                username=validated_data.get('email'),
                resturant=resturant
            )
            if password:
                user.set_password(password)
            
            user.save()


            return user

    def update(self, instance, validated_data):
       
        with transaction.atomic():
            password = validated_data.pop('password', None)
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            
            if password:
                try:
                    validate_password(password)
                except ValidationError as e:
                    raise serializers.ValidationError(e.messages)
                instance.set_password(password)
            
            instance.save()
            return instance
        
class PagePermissionSerializer(ModelSerializer):
    class Meta:
        model = models.PagePermission
        fields = "__all__"

class UserDetailSerializer(ModelSerializer):
    role_name = serializers.SerializerMethodField()
    is_password_changed = serializers.SerializerMethodField()
    date_of_birth = serializers.DateField()
    email = serializers.EmailField()
    resturant = ResturantSerializer(read_only=True)
    profile = serializers.URLField(required=False, allow_null=True)
    class Meta:
        model = models.User
        fields = "id","first_name","last_name","email","role","profile","profile_image_url","phone_number","date_of_birth","street_address","city","state_province","postal_code","country","is_active","role_name", "is_password_changed","is_deleted","resturant"
        extra_kwargs = {
            'password': {'write_only': True},
            "is_superuser": {'write_only': True},
        }
    def validate_email(self, value):
        if not self.instance:
            user_exists = models.User.objects.filter(email=value).exists()
            if user_exists:
                raise serializers.ValidationError("User already exists.")
        return value

    def validate_phone_number(self, value):
        if not value:
            raise serializers.ValidationError("Phone number field is required.")
        if not isinstance(value, str):
            raise serializers.ValidationError("Phone number field must be a string.")
        if not re.match(r'^[\d\+\-\(\)\s]+$', value):
            raise serializers.ValidationError(
                "Phone number can only contain digits, +, -, (), and spaces."
            )
        
        if not self.instance:
            if self.Meta.model.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("User already exists.")
        return value

    
    def validate_date_of_birth(self, value):
        today = date.today()
        eighteen_years_ago = today - timedelta(days=18 * 365.25) 
        if value > eighteen_years_ago:
            raise serializers.ValidationError("User must be at least 18 years old to work here.")
        return value

    def _send_welcome_email(self, user, password):
        subject = "Your Account Password"
        message = (
            f"Hello {user.first_name},\n\n"
            f"Your account has been created successfully. "
            f"Your temporary password is: {password}\n\n"
            f"Your Login Email is: {user.email}\n\n"
            f"Please log in and change your password immediately for security.\n\n"
            f"Thank you.\n"
            f"Team Plate Prep"
        )
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )


    def create(self, validated_data):
        with transaction.atomic():

            password = validated_data.pop('password', None)
            if not password:
                password = 'aszx1234' 
            current_user = self.context['request'].user
            user = models.User(**validated_data,resturant=current_user.resturant)
            user.set_password(password)
            user.save()
            

            self._send_welcome_email(user, password)
            return user

    def update(self, instance, validated_data):
        with transaction.atomic():

            password = validated_data.pop('password', None)
            if password:
                try:
                    validate_password(password)
                except ValidationError as e:
                    raise serializers.ValidationError(e.messages)
            
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance

    def to_representation(self, instance):
        response = super().to_representation(instance)
        return response
    
    def get_role_name(self,obj):
        return obj.get_role_display()
    
    def get_is_password_changed(self,obj):
        return obj.is_password_changed


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['is_password_changed'] = user.is_password_changed
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_deleted:
            raise AuthenticationFailed("Your account is deleted by admin. Please contact admin.")

        data['role'] = self.user.role
        data['is_password_changed'] = self.user.is_password_changed
        if not self.user.is_superuser:
            data['is_subscribed'] = True if self.user.resturant and self.user.resturant.plan else False
        else:
            data['superadmin'] = True

        request = self.context.get("request")
        if request:
            ip = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT")
            models.LoginLog.objects.create(user=self.user, ip_address=ip, user_agent=user_agent)
            
        return data

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = RefreshToken(attrs['refresh'])
        user_id=refresh.get('user_id')
        user = get_object_or_404(models.User,id=user_id)
        if user.is_deleted:
            raise AuthenticationFailed("your account is deleted by admin. please contact admin.")
        data['role'] = refresh.get('role', None)
        data['is_password_changed'] = refresh.get('is_password_changed', None)

        return data

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tag
        fields = ("id", "name")

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Ingredient
        fields = ("id", "title", "quantity", "unit","recipe")

class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Steps
        fields = ("id", "title")

class StarchPreparationSerializer(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField(required=False)

    class Meta:
        model = models.Starch_Preparation
        fields = ("id", "title", "image","steps","image_url")

    def get_steps(self, obj):
        step = models.Starch_Preparation_Steps.objects.filter(starch_preparation=obj)
        return StarchPreparationStepsSerializer(step, many=True).data
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image and request:
            response['image'] = request.build_absolute_uri(instance.image.url)
        return response
        
class StarchPreparationStepsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Starch_Preparation_Steps
        fields = ("id", "step")

class DesignYourPlateSerializer(serializers.ModelSerializer):
    steps = serializers.SerializerMethodField()
    class Meta:
        model = models.Design_Your_Plate
        fields = ("id", "image", "steps","image_url")

    def get_steps(self, obj):
        step = models.Design_Your_Plate_Steps.objects.filter(design_plate=obj)
        return DesignYourPlateStepsSerializer(step, many=True).data

    def to_representation(self, instance):
        response = super().to_representation(instance)
        request = self.context.get('request')
        if instance.image and request:
            response['image'] = request.build_absolute_uri(instance.image.url)
        return response
    
class DesignYourPlateStepsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Design_Your_Plate_Steps
        fields = ("id", "step")

class PredefinedIngredientsSerializer(ModelSerializer):
    class Meta:
        model = models.Predefined_Ingredients
        fields = ['id','name','type']

class PredefinedStarchSerializer(ModelSerializer):
    class Meta:
        model = models.Predefined_Starch
        fields = ['id','name','type']

class PredefinedVegetableSerializer(ModelSerializer):
    class Meta:
        model = models.Predefined_Vegetable
        fields = ['id','name','type']

        
class CookingDeviationCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Cooking_Deviation_Comment
        fields = ("id", "step")


class RealTimeVariableCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Real_time_Variable_Comment
        fields = "id", "step"

        
class RecipeProcessAuditSerializer(ModelSerializer):
    dish_name = serializers.CharField(source='dish_name.dish_name')
    class Meta:
        model = models.Recipe_Process_Audit
        fields = "__all__"
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['role'] = instance.changed_by.get_role_display()
        response['changed_by'] = instance.changed_by.username

        dt_str = response.get('datetime')
        if dt_str:
            try:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))

                if 4 <= dt.day <= 20 or 24 <= dt.day <= 30:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(dt.day % 10, 'th')

                response['datetime'] = dt.strftime(f"%B %d{suffix}, %I:%M %p")

            except ValueError:
                response['datetime'] = dt_str

        return response

    
class RatingSerializer(ModelSerializer):
    class Meta:
        model = models.Rating
        fields = "id","rating","comment"

class SelectHolidaySerializer(ModelSerializer):
    class Meta:
        model = models.Select_Holiday
        fields = "__all__"

class ScheduleDishSerializer(ModelSerializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=models.Recipe.objects.all())
    class Meta:
        model = models.Schedule_Dish
        exclude = 'updated_at',
    def validate_schedule_datetime(self, value):
        try:
            if isinstance(value, str):
                value = parser.isoparse(value)
        except ValueError:
            raise serializers.ValidationError(
                "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ)"
            )

        if value <= timezone.now():
            raise serializers.ValidationError("Schedule date must be in the future.")
        
        return value

    def validate(self, data):
        if not all(key in data for key in ['dish', 'schedule_datetime', 'holiday']):
            raise serializers.ValidationError(
                "All required fields (dish, schedule_datetime, holiday) must be provided."
            )

        dish = data['dish']
        existing_schedule = models.Schedule_Dish.objects.filter(
            dish=dish,
            is_deleted=False
        ).order_by('schedule_datetime').first()

        if existing_schedule:
            raise serializers.ValidationError({
                "dish": f"This dish is already scheduled on {format_datetime(str(existing_schedule.schedule_datetime))}."
            })
        return data
    
    def validate_dish(self, value):
        if value.status == choices.RecipeStatus.PUBLIC:
            raise serializers.ValidationError("You cannot schedule a public dish.")
        return value
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['created_at'] = format_datetime(str(instance.created_at))
        response['schedule_datetime'] = format_datetime(str(instance.schedule_datetime))
        response['dish'] = {'name':instance.dish.dish_name,
                            "id":instance.dish.id}
        response['status'] = {
            'name': instance.get_status_display(),
            "value": instance.status
        }
        response['holiday']={
            "name":instance.holiday.holiday,
            "id":instance.holiday.id
        }
        return response
    
class EssentialsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Essentials
        fields = ("id", "title", "quantity","unit")


class RecipeSerializer(ModelSerializer):
    rating = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField(read_only=True)
    ingredient = serializers.SerializerMethodField(read_only=True)
    essential = serializers.SerializerMethodField(read_only=True)
    steps = serializers.SerializerMethodField(read_only=True)
    starch_preparation = serializers.SerializerMethodField(read_only=True)
    design_your_plate = serializers.SerializerMethodField(read_only=True)
    Cooking_Deviation_Comment = serializers.SerializerMethodField(read_only=True)
    Real_time_Variable_Comment = serializers.SerializerMethodField(read_only=True)
    dish_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    manual_video = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # predefined_ingredients = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    food_cost = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cusinie_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    youtube_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    status = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    availability = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = models.Recipe
        exclude = ("user",)
    
    # def validate_predefined_ingredients(self, predefined_ingredients):
    #     if isinstance(predefined_ingredients, str):
    #         try:
    #             predefined_ingredients = json.loads(predefined_ingredients)
    #         except json.JSONDecodeError:
    #             raise serializers.ValidationError({"predefined_ingredients": "Invalid format. Expected a list."})
    #     if not isinstance(predefined_ingredients, list):
    #         raise serializers.ValidationError({"predefined_ingredients": "Expected a list."})
    #     return predefined_ingredients

    def validate_manual_video(self, value):
        if value != None:
            try:
                key = value.split('/')[-1]
                res = s3_utility.check_file_exists(key)
                if not res:
                    raise ValidationError({"manual_video": "File does not exist on aws"}, code=400)
                return value
            except:
                raise ValidationError({"manual_video": "File does not exist on aws"}, code=400)
    
    def validate_food_cost(self, value):
        if value == None:
            return None
        return value

    def validate_cusinie_type(self, value):
        
        if value == None:
            return None
        instance = models.MenuCategoryies.objects.filter(id=value).first()
        if not instance:
            raise serializers.ValidationError("Invalid cusinie type")
        return instance

    def validate_youtube_url(self, value):
        if value == None:
            return None
        return value

    def validate_status(self, value):
        if value == None:
            return None
        return value

    def validate_availability(self, value):
        if value == None:
            return None
        return value

    def validate_dish_name(self, value):
        request = self.context.get('request')
        title = models.Recipe.objects.filter(dish_name=value).exists()
        if title and request.method == "post":
            raise serializers.ValidationError("A recipe with this name already exists.")
        return value
    
    def get_rating(self, obj):
        rating_data = models.Rating.objects.filter(recipe=obj).aggregate(average_rating=Avg('rating'),
            total_count=Count('rating'))
        average = rating_data['average_rating'] if rating_data['average_rating'] is not None else 0
        total_count = rating_data['total_count']
        return {"average_rating": round(average, 3), "total_count": total_count}
    
    def get_tags(self, obj):
        tag = models.Tag.objects.filter(recipe = obj.id)
        return TagSerializer(tag, many=True).data
    
    def get_ingredient(self,obj):
        ingredient = models.Ingredient.objects.filter(recipe=obj.id)
        return IngredientSerializer(ingredient, many=True).data
    
    def get_essential(self, obj):
        essentail = models.Essentials.objects.filter(recipe=obj.id)
        return EssentialsSerializer(essentail, many=True).data
    
    def get_steps(self, obj):
        steps = models.Steps.objects.filter(recipe=obj.id).order_by('id')
        return StepSerializer(steps, many=True).data
    
    def get_starch_preparation(self, obj):
        starch = models.Starch_Preparation.objects.filter(recipe=obj.id).first()
        return StarchPreparationSerializer(starch, context=self.context).data
    
    def get_design_your_plate(self, obj):
        design = models.Design_Your_Plate.objects.filter(recipe=obj).first()
        return DesignYourPlateSerializer(design, context=self.context).data
    
    def get_Cooking_Deviation_Comment(self,obj):
        pre = models.Cooking_Deviation_Comment.objects.filter(recipe=obj.id)
        return CookingDeviationCommentSerializer(pre, many=True).data
    
    def get_Real_time_Variable_Comment(self,obj):
        pre = models.Real_time_Variable_Comment.objects.filter(recipe=obj.id)
        return RealTimeVariableCommentSerializer(pre, many=True).data

    def to_representation(self, instance):
        response =  super().to_representation(instance)
        request = self.context.get('request')

        response['availability'] = {
            "name":instance.get_availability_display(),
            "value":instance.availability
        }
        response['status'] = {
            'name':instance.get_status_display(),
            "value":instance.status
        }

        images = instance.recipe_image.all()
        response['recipe_image'] = RecipeImagesSerializer(images, many=True, context=self.context).data

        wines = instance.wine_pairing.all()
        response['wine_pairing'] = WineSerializer(wines, many=True).data

        predefined_ingredients = instance.predefined_ingredients
        response['predefined_ingredients'] = PredefinedIngredientsSerializer(predefined_ingredients, many=True).data
        
        predefined_starch = instance.predefined_starch
        response['predefined_starch'] = PredefinedStarchSerializer(predefined_starch, many=True).data
        
        predefined_vegetables = instance.predefined_vegetables
        response['predefined_vegetables'] = PredefinedVegetableSerializer(predefined_vegetables, many=True).data

        response['video'] = request.build_absolute_uri(instance.video.url) if instance.video else None
        if instance.cusinie_type:
            response['cusinie_type'] = {
                'id':instance.cusinie_type.id,
                'category_name':instance.cusinie_type.category_name
            }
        return response

class MessageSerializer(ModelSerializer):
    task_name = serializers.CharField(source='task_id.task_name.dish_name', read_only=True)
    message_creator_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_profile = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = models.Message
        fields = "id","task_id","message","task_name","message_creator_name","created_at","user_profile"
    
    def get_user_profile(self, obj):
        request = self.context.get('request')
        user = obj.user 
        user_details = {
            "id": user.id,
            "full_name": user.get_full_name(),
        }
        if user_details and request:
            if user.profile and hasattr(user.profile, 'url'):
                user_details["profile_image_url"] = request.build_absolute_uri(user.profile.url)
            else:
                user_details["profile_image_url"] = None
        else:
            user_details["profile_image_url"] = None
        return user_details

class TaskSerializer(ModelSerializer):
    staff_email = serializers.CharField(source='staff.email', read_only=True)
    staff_full_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    staff_profile = serializers.ImageField(source='staff.profile', read_only=True)
    messages = serializers.SerializerMethodField(read_only=True)
    youtube_url = serializers.CharField(source='task_name.youtube_url', read_only=True)
    task_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Task
        fields = "id","staff","staff_full_name" ,"task_name","task_description","status","prority","started_at","completed_at","kitchen_station","attachment_video_link", "youtube_url","due_date","staff_email","staff_profile","messages","task_details", "other_task_name", 'video','image'
    
    def validate(self, data):
        video = data.get('video')
        if video:
            try:
                key = video.split('/')[-1]
                res = s3_utility.check_file_exists(key)
                if not res:
                    raise ValidationError({"video": "File does not exist on aws"}, code=400)
            except:
                raise ValidationError({"video": "File does not exist on aws"}, code=400)
        return data
    
    def get_task_details(self, obj):
        if obj.task_name:
            return RecipeSerializer(obj.task_name, context=self.context).data
        return None
    
    def get_messages(self,obj):
        msg = models.Message.objects.filter(task_id__id = obj.id)
        return MessageSerializer(msg, many=True, context=self.context).data
    
    def get_prority_name(self,obj):
        return obj.get_prority_display()
    
    

    def to_representation(self, instance):
        response = super().to_representation(instance)
        if instance.task_name:
            response['task_name'] = {
                "task_name": instance.task_name.dish_name,
                "id ": instance.task_name.id
            }
        response['status'] = {
            "value" : instance.status,
            "name": instance.get_status_display()
        } 
        response['prority'] = {
            "value" : instance.prority,
            "name": instance.get_prority_display()
        }
        response['staff_detail'] = UserDetailSerializer(instance.staff, context=self.context).data
        response['assigned_by'] = instance.user.get_full_name()
        return response

class TaskListSerializer(ModelSerializer):
    staff_email = serializers.CharField(source='staff.email', read_only=True)
    staff_full_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    staff_profile = serializers.ImageField(source='staff.profile', read_only=True)
    youtube_url = serializers.CharField(source='task_name.youtube_url', read_only=True)
    class Meta:
        model = models.Task
        fields = "__all__"

    
    def get_prority_name(self,obj):
        return obj.get_prority_display()
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        if response['task_name']:
            response['task_name'] = {
                "task_name": instance.task_name.dish_name,
                "id ": instance.task_name.id
            }
        response['status'] = {
            "value" : instance.status,
            "name": instance.get_status_display()
        } 
        response['prority'] = {
            "value" : instance.prority,
            "name": instance.get_prority_display()
        }
        response['assigned_by'] = instance.user.get_full_name()
        return response
        
class WineSerializer(ModelSerializer):
    class Meta:
        model = models.Wine
        fields = "__all__"

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    id = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()

class ExtraImagesSerializer(ModelSerializer):
    class Meta:
        model = models.RecipeImage_extra
        fields = ("id","image","image_url")

class RecipeWineSerializer(ModelSerializer):
    rating = serializers.SerializerMethodField()
    class Meta:
        model = models.Recipe
        fields = "id","description","dish_name","rating"
    
    def get_rating(self, obj):
        rating_data = models.Rating.objects.filter(recipe=obj).aggregate(average_rating=Avg('rating'),
            total_count=Count('rating'))
        average = rating_data['average_rating'] if rating_data['average_rating'] is not None else 0
        total_count = rating_data['total_count']
        return {"average_rating": round(average, 3), "total_count": total_count}

    def to_representation(self, instance):
        response = super().to_representation(instance)
        images = instance.recipe_image.all()
        response['recipe_image'] = ExtraImagesSerializer(images, many=True, context=self.context).data

        wines = instance.wine_pairing.all()
        response['wine_pairing'] = WineSerializer(wines, many=True).data

        ingredients = instance.recipe_ingredient.all()
        response['ingredients'] = IngredientSerializer(ingredients, many=True).data

        response['price'] = instance.food_cost

        return response

class RecipeImagesSerializer(ModelSerializer):  
    # image = serializers.ImageField()
    image_url = serializers.CharField()
    class Meta:
        model = models.recipe_images
        fields = "id","image_url"
    
    # def validate_image(self, value):
    #     if not value:
    #         raise serializers.ValidationError("The image field is required.")
    #     if not hasattr(value, "name") or not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
    #         raise serializers.ValidationError("The image must be a valid image file (PNG, JPG, JPEG).")
    #     return value

class RecipeVideoGenerationSerializer(serializers.Serializer):
    title = serializers.CharField(required=True)
    recipe = serializers.PrimaryKeyRelatedField(queryset=models.Recipe.objects.all())
    introduction = serializers.CharField(required=True)
    # name_chef = serializers.CharField(required=True)
    steps = serializers.ListField(child=serializers.CharField(allow_blank=False),required=True,allow_empty=False)
    ingredient = serializers.ListField(child=serializers.CharField(allow_blank=False),required=True,allow_empty=False)
    last_words = serializers.CharField(required=True)
    template_id = serializers.UUIDField(required=True)
    language = serializers.CharField(required=True, allow_blank=False)

    def validate_ingredient(self, value):
        
        if len(value) > 18:
            raise serializers.ValidationError("The ingredients list cannot contain more than 18 items.")
        
        for item in value:
            if len(item) > 30:
                raise serializers.ValidationError(f"'{item}' exceeds 30 characters limit.")
        return value    
    
    def validate_recipe(self, value):
        if value.video and value.video_id:
            raise serializers.ValidationError(
                "This recipe already has a video. Please delete the existing video before creating a new one."
            )
        return value
       
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        recipe_instance = models.Recipe.objects.get(id=ret['recipe'])

        return {
            "recipe": recipe_instance.id,
            "recipe_name": recipe_instance.dish_name,
            "introduction": ret['introduction'],
            # "name_chef": ret['name_chef'],
            "steps_text": ", ".join(f"{step}" for step in ret['steps']),
            "ingredients_list": "\n".join([f"• {ingredient}" for ingredient in ret['ingredient']]),
            "last_words": ret['last_words'],
            "template_id": ret['template_id'],
            "title": ret['title'],
            "language": ret['language']
        }

class NotificationSerializer(serializers.ModelSerializer):
    is_seen = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Notification
        fields = ['id', 'title', 'message', 'related_dish_id', 'is_seen', 'created_at']
    
    def get_is_seen(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return request.user in obj.seen_by_users.all()
        return False
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'created_at'):
            data['created_at'] = format_datetime(str(instance.created_at))
        return data

class AIRecipeGenerationSerializer(serializers.Serializer):
    available_ingredients = serializers.ListField(child=serializers.CharField(max_length=100),allow_empty=False,)
    cuisine_style = serializers.CharField(max_length=50, required=True)
    dietary_preferences = serializers.CharField(max_length=50, required=False, allow_blank=True, default="", allow_null=True)
    # theme = serializers.CharField(max_length=50, required=True)
    target_audience = serializers.CharField(max_length=100, required=True)
    price_range = serializers.IntegerField(min_value=1, required=True)
    dietary_restrictions = serializers.CharField(max_length=100, required=False)
    menu_class = serializers.CharField(max_length=100, required=False)

    def validate_available_ingredients(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Available ingredients must be a list.")
        
        for ingredient in value:
            if not isinstance(ingredient, str):
                raise serializers.ValidationError(f"Ingredient '{ingredient}' must be a string.")

        return value

class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=models.MenuCategoryies.objects.all(),
        error_messages={
            "does_not_exist": "Category does not exist.",
        }
    )
    class Meta:
        model = models.MenuItems
        fields = ['id','recipe', 'category', 'item_name', 'item_price', 'item_description']

class IngredientTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Ingredient
        fields = ['title']

class MenuSerializer(serializers.ModelSerializer):
    menu_item = serializers.ListField(write_only=True)
    recipes = serializers.ListField(write_only=True)
    class Meta:
        model = models.Menu
        fields = ['id', "title", "description", "image", "created_at", "menu_item", "recipes"]
        read_only_fields = ['created_at']
    
    # def validate(self, data):
    #     recipes = data.get('recipes', [])
    #     if not isinstance(recipes, list) or not recipes:
    #         raise serializers.ValidationError("Invalid format: 'recipes' should be a list containing a JSON string.")

    #     try:
    #         recipe_ids = json.loads(recipes[0])
    #     except (json.JSONDecodeError, TypeError):
    #         raise serializers.ValidationError("Invalid format: 'recipes' must be a valid JSON-encoded list of integers.")

    #     if not isinstance(recipe_ids, list):
    #         raise serializers.ValidationError("Invalid format: Decoded recipes must be a list of integers.")

    #     for recipe_id in recipe_ids:
    #         if not isinstance(recipe_id, int):
    #             raise serializers.ValidationError(f"Invalid recipe ID: {recipe_id} is not an integer.")

    #         if not models.Recipe.objects.filter(id=recipe_id).exists():
    #             raise serializers.ValidationError(f"Recipe with id {recipe_id} does not exist.")

    #     return data

    @transaction.atomic
    def create(self, validated_data):
        menu_items_data = validated_data.pop('menu_item', [])
        recipes_data = validated_data.pop('recipes', [])
        menu = models.Menu.objects.create(**validated_data)
        for item_data in json.loads(menu_items_data[0]):
            item_serializer = MenuItemSerializer(data=item_data)
            if item_serializer.is_valid():
                menu_item = item_serializer.save()
                menu.menu_item.add(menu_item)
            else:
                raise serializers.ValidationError(item_serializer.errors)
        recipe_ids = json.loads(recipes_data[0])
        recipes = models.Recipe.objects.filter(id__in=recipe_ids)
        menu.recipes.set(recipes)
        return menu

    @transaction.atomic
    def update(self, instance, validated_data):
        menu_items_data = validated_data.pop('menu_item', [])
        recipes_data = validated_data.pop('recipes', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        existing_menu_item_ids = set(instance.menu_item.values_list('id', flat=True))
        new_menu_item_ids = set()

        for item_data in json.loads(menu_items_data[0]):
            item_id = item_data.get('id', None)
            if item_id and models.MenuItems.objects.filter(id=item_id).exists():
                menu_item = models.MenuItems.objects.get(id=item_id)
                item_serializer = MenuItemSerializer(menu_item, data=item_data, partial=True)
                if item_serializer.is_valid():
                    menu_item = item_serializer.save()
                else:
                    raise serializers.ValidationError(item_serializer.errors)
            else:
                item_serializer = MenuItemSerializer(data=item_data)
                if item_serializer.is_valid():
                    menu_item = item_serializer.save()
                else:
                    raise serializers.ValidationError(item_serializer.errors)
            new_menu_item_ids.add(menu_item.id)
            instance.menu_item.add(menu_item)
        items_to_delete = existing_menu_item_ids - new_menu_item_ids
        models.MenuItems.objects.filter(id__in=items_to_delete).delete()
        recipe_ids = json.loads(recipes_data[0])
        recipes = models.Recipe.objects.filter(id__in=recipe_ids)
        instance.recipes.set(recipes)
        return instance

    def to_representation(self, instance):
        response = super().to_representation(instance)
        categorized_menu_items = defaultdict(list)
        for item in instance.menu_item.all().values('id', 'category', 'item_name', 'item_price', 'item_description',"recipe"):
            category = get_object_or_404(models.MenuCategoryies, id=item['category'])
            category_name = category.category_name
            item['ingredients'] = models.Ingredient.objects.filter(recipe=item['recipe']).values_list('title',flat=True)
            categorized_menu_items[category_name].append(item)
        recipes = instance.recipes.all().values('id', 'dish_name',"description","food_cost")

        return {
            "id": response["id"],
            "title": response["title"],
            "description": response["description"],
            "image": response["image"],
            "created_at": format_datetime(str(instance.created_at)),
            "category_name": categorized_menu_items,
            "recipes": list(recipes)
        }
    
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenuCategoryies
        fields = ['id', 'category_name']
    
    def validate_category_name(self, value):
        exists = models.MenuCategoryies.objects.filter(category_name__iexact=value).exists()
        if exists:
            raise serializers.ValidationError("Category with same name already exists.")
        return value

class MenuListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Menu
        fields = ['id',"title","description","image","created_at"]
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['created_at'] = format_datetime(str(instance.created_at))
        return response

import django.utils.timezone as timezone

# Patch for DRF < 3.15 expecting timezone.utc
if not hasattr(timezone, "utc"):
    timezone.utc = timezone.utc

class FileUploadRequestSerializer(serializers.Serializer):
    file = serializers.CharField(max_length=255, required=True)
    
    def generate_presigned_url(self):
        try:
            return s3_utility.generate_presigned_url(self.validated_data['file'])
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError({"detail": [str(e)]})

class NestedFieldSerializer(serializers.Serializer):
    title = serializers.CharField()
    index = serializers.IntegerField()

class SpellCheckSerializer(serializers.Serializer):
    data = serializers.DictField(child=NestedFieldSerializer())


# class GrammarCheckSerializer(serializers.Serializer):
#     text = serializers.CharField(required=True)
#     corrected_text = serializers.CharField(read_only=True)
#     suggestions = serializers.JSONField(read_only=True)

#     def validate_text(self, value):
#         if not value:
#             raise serializers.ValidationError("Text cannot be empty.")
#         return value

#     def create(self, validated_data):
#         text = validated_data['text']
#         tool = language_tool_python.LanguageTool("en-US")  # Requires Java

#         matches = tool.check(text)

#         suggestions = []
#         corrected_text =  text # Start with the original text
#         for match in reversed(matches):  # Process corrections from end to start
#             start, end = match.offset, match.offset + match.errorLength
#             if match.replacements:
#                 corrected_text = corrected_text[:start] + match.replacements[0] + corrected_text[end:]
            
#             suggestions.append({
#                 "error": match.ruleId,
#                 "message": match.message,
#                 "suggested_corrections": match.replacements,
#                 "context": match.context
#             })

#         return {
#             "input_text": text,
#             "corrected_text": corrected_text,
#             "suggestions": suggestions
#         }


class ListRecipeSerializer(serializers.ModelSerializer):
    recipe_image = RecipeImagesSerializer(many=True, read_only=True)

    class Meta:
        model = models.Recipe
        fields = ["id", "dish_name", "description", "is_draft", "recipe_image","is_deleted"]

class TemplateGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Recipe
        fields = ['id','main_dish','dish_name']

class GetRecipeSerializer(serializers.ModelSerializer):
    ingredients = serializers.SerializerMethodField()

    class Meta:
        model = models.Recipe
        fields = ['id', 'main_dish', 'dish_name', 'ingredients', 'food_cost']

    def get_ingredients(self, obj):
        predefined = obj.predefined_ingredients.values_list('name', flat=True)
        recipe_ings = obj.recipe_ingredient.values_list('title', flat=True)
        return list(predefined) + list(recipe_ings)

class MenuTemplateItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenuTemplateItems
        fields = ['id', 'recipe_id', 'main_dish', 'recipe_name', 'ingredients', 'food_cost', 'is_special']

class MenuTemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MenuTemplate
        fields = ['id','title','sub_title','logo_url']

class MenuTemplateSerializer(serializers.ModelSerializer):
    items = MenuTemplateItemsSerializer(many=True)

    class Meta:
        model = models.MenuTemplate
        fields = ['id', 'title','sub_title','location','start_time','end_time','price_per_person', 'global_note', 'logo_url', 'items',"sections","warning_note","format","template_type", "offer_text"]

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        user = self.context['request'].user
        menu_template = models.MenuTemplate.objects.create(**validated_data,resturant=user.resturant)
        for item_data in items_data:
            item = models.MenuTemplateItems.objects.create(**item_data)
            menu_template.items.add(item)
        return menu_template

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.clear()
            for item_data in items_data:
                item = models.MenuTemplateItems.objects.create(**item_data)
                instance.items.add(item)

        return instance

class LoginLogSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = models.LoginLog
        fields = '__all__'
    
    def get_user(self, obj):
        if obj.user:
            return {
                "full_name": obj.user.get_full_name(),
                "email": obj.user.email,
                "role": obj.user.role,
            }
        return None


class InstructionVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InstructionalVideo
        fields = ['id', 'title', "description", 'type','source']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['resturant'] = request.user.resturant if hasattr(request.user, 'resturant') else None
        return super().create(validated_data)

class ShiftNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ShiftNote
        fields = ['id', 'created_by', 'date', 'shift', 'note']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user if hasattr(request.user, 'resturant') else None
        validated_data['resturant'] = request.user.resturant if hasattr(request.user, 'resturant') else None
        return super().create(validated_data)

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['created_by'] = {
            "id": instance.created_by.id,
            "full_name": instance.created_by.get_full_name() if instance.created_by else None
        }
        return response

class DictionaryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DictionaryCategory
        fields = ['id', 'name', "description"]
    
    def validate_name(self, value):
        exists = models.DictionaryCategory.objects.filter(name__iexact=value).exists()
        if exists:
            raise serializers.ValidationError("Category with same name already exists.")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['resturant'] = request.user.resturant if hasattr(request.user, 'resturant') else None
        return super().create(validated_data)

class DictionaryItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=models.DictionaryCategory.objects.all(),
        error_messages={
            "non_filed_error": "Category does not exist.",
        }
    )

    class Meta:
        model = models.DictionaryItem
        fields = ['id', 'term', 'definition','description', 'category']
    
    def validate_term(self, value):
        exists = models.DictionaryItem.objects.filter(term__iexact=value).exists()
        if exists:
            raise serializers.ValidationError("Item with same term already exists.")
        return value

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['category'] = {
            "id": instance.category.id,
            "name": instance.category.name
        }
        return response
    
class EditorTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EditorTemplate
        fields = ['id', 'title', 'image', 'source']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['resturant'] = request.user.resturant if hasattr(request.user, 'resturant') else None
        return super().create(validated_data)
    

class EditorSmallDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EditorTemplate
        fields = ['id', 'title', 'image']
    

class EditorImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EditorImage
        fields = ['id', 'image']
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['resturant'] = request.user.resturant if hasattr(request.user, 'resturant') else None
        return super().create(validated_data)
