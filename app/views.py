from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from app import filters, models, serializers, choices, permissions, pagination
from app.account_activation_token import account_activation_token 
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as filter, status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.db.models import FloatField, IntegerField, Sum, Subquery, OuterRef, Avg, Count
from datetime import datetime
from rest_framework.decorators import action
from app.utils import scheduler, CulinaryAI, store_wine_pairings, image_url_to_context, generate_video_and_save, delete_video_from_synthesia, S3FileUtility, spell_checker, scheduler
from app.tasks import create_or_update_schedule_dish
from rest_framework_simplejwt.tokens import RefreshToken
from project import settings
from django.db import transaction
import logging, json
from smtplib import SMTPException
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Prefetch
from django.db.models.functions import ExtractMonth
import calendar
from app.permissions import IsAdminOrHeadChef, IsSubscribedORSuperUser, TaskEditDeletePermission, IsAdminOrHeadChefOrStaff


logger = logging.getLogger(__name__)
culinary_ai = CulinaryAI()
host_email = settings.EMAIL_HOST_USER
FRONTEND_URL = settings.FRONTEND_URL
s3_utility = S3FileUtility()


from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import now
from rest_framework import permissions

scheduler = BackgroundScheduler()
scheduler.start()

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = serializers.CustomTokenObtainPairSerializer

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = serializers.CustomTokenRefreshSerializer

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "password/acc_activated.html")
    else:
        return HttpResponse("Activation link is invalid!")

class RegisterAPI(ModelViewSet):
    serializer_class = serializers.UserSerializer
    permission_classes = []
    
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    http_method_names = ['post']
    queryset = models.User.objects.none()
    filterset_class = filters.UserFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        return Response({
            "user": serializer.data,
            "access_token": access_token,
            "refresh_token": refresh_token,
        }, status=201)
        
class PasswordResetRequestViewSet(ViewSet):
    
    def create(self, request, *args, **kwargs):
    
        serializer = serializers.PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = models.User.objects.get(email=email)
            except models.User.DoesNotExist:
                return Response({'error': 'User with this email does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            
            uid = user.pk
            token = default_token_generator.make_token(user)
            reset_url = f'{FRONTEND_URL}forgot-password/{uid}/{token}/'
            try:
                send_mail('Password Reset', f'Click the following link to reset your password: {reset_url}', host_email, [email], fail_silently=False)
            except SMTPException as e:
                raise SMTPException("Failed to send password reset email") from e
            except Exception as e:
                raise Exception("An unexpected error occurred while sending email") from e

            return Response({'success': 'Password reset link sent'}, status=status.HTTP_200_OK)

class PasswordResetConfirmViewSet(ViewSet):
    def create(self, request, *args, **kwargs):

        serializer = serializers.PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uid = serializer.validated_data['id']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = models.User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, models.User.DoesNotExist):
                return Response({'error': 'Invalid ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            if default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({'success': 'Password reset successful'}, status=status.HTTP_200_OK)
            
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetailsViewSet(ModelViewSet):
    serializer_class = serializers.UserDetailSerializer
    queryset = models.User.objects.filter(is_deleted=False)
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_class = filters.UserFilter
    search_fields = ['first_name', 'last_name', 'email', "street_address"]
    ordering_fields = ['id','first_name', 'email']
    ordering = ['-id']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def get_serializer_context(self):
        return super().get_serializer_context()
        
    @action(detail=False, methods=['get'], url_name="change_password", permission_classes=[IsAuthenticated])
    def change_password(self, request):
        user = request.user
        new_password = request.query_params.get("new_password")
        if new_password:
            try:
                validate_password(new_password)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)

        user.set_password(new_password)
        user.is_password_changed = True
        user.save()
        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        user = request.user
        serializer = serializers.ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            old_password = serializer.validated_data.get("old_password")
            new_password = serializer.validated_data.get("new_password")

            if not user.check_password(old_password):
                return Response({"old_password": ["Old password is incorrect."]},
                                status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get_queryset(self):
        
        user = self.request.user
        # only for list request
        if user.role == choices.Usertypes.SUPER_ADMIN or user.is_superuser:
            if self.action == 'list':
                return models.User.objects.exclude(id=self.request.user.id).order_by('-id')
        elif user.role == choices.Usertypes.ADMIN:
            if self.action == 'list':
                return self.queryset.exclude(id=self.request.user.id).filter(resturant=user.resturant).order_by('-id')
        else:
            return self.queryset.filter(id=user.id)
    
    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @action(detail=False, methods=['get'], url_name="get_staff")
    def get_staff(self, request):
        staff = self.queryset.filter(role=choices.Usertypes.STAFF, is_active=True)
        page = self.paginate_queryset(staff)
        if page is not None:
            serializer = serializers.UserDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.UserDetailSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=False,methods=['get'],url_path='get-deleted')
    def get_deleted(self,request):
        user = request.user
        if user.is_superuser:
            deleted = models.User.objects.filter(role=choices.Usertypes.ADMIN,is_deleted=True).order_by('-id')
        else:
            deleted = models.User.objects.filter(is_deleted=True,resturant=user.resturant).order_by('-id')
        deleted = self.filter_queryset(deleted)
        page = self.paginate_queryset(deleted)
        if page is not None:
            serializer = serializers.UserDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = serializers.UserDetailSerializer(deleted, many=True)
        return Response(serializer.data)

    @action(detail=False,methods=['post'],url_path='restore')
    def restore(self,request):
        id = request.data.get('id')
        user = models.User.objects.filter(pk=id).first()
        if not user:
            return Response({'message':'User not found'},status=status.HTTP_400_BAD_REQUEST)
        
        elif user.role == choices.Usertypes.ADMIN:
            resturant = user.resturant
            resturant_users = self.queryset.filter(resturant=resturant,is_deleted=True)
            for user in resturant_users:
                if user.is_deleted:
                    user.is_deleted = False
                    user.save()
            user.is_deleted = False
            user.save()
        user.is_deleted = False
        user.save()
        return Response({'message':'User Restored Successfully.'})

    @action(detail=False, methods=['get'], url_name="get_staff_list")
    def get_staff_list(self, request):
        staff = self.queryset.filter(role=choices.Usertypes.STAFF, is_active=True).values('id', "first_name", "last_name", "email",).order_by('-id')
        return Response({'staff':staff}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def profile(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        if user.is_superuser:
            if instance.role == choices.Usertypes.ADMIN:
                resturant = instance.resturant
                resturant_users = self.queryset.filter(resturant=resturant).exclude(id=instance.id).exclude(id=user.id)
                for user in resturant_users:
                    user.is_deleted = True
                    user.save()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class LogoutView(ModelViewSet):
    serializer_class = serializers.UserSerializer
    queryset = models.User.objects.none()
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
        except:
            pass
        logout(request)
        return Response({"status": "User Logged out successfully"})
    
class TagViewSet(ModelViewSet):
    queryset = models.Tag.objects.filter(is_deleted = False)
    serializer_class = serializers.TagSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_class = filters.TagFilter
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class IngredientViewSet(ModelViewSet):
    queryset = models.Ingredient.objects.filter(is_deleted=False)
    serializer_class = serializers.IngredientSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_class = filters.IngredientFilter
    filterset_fields = ['recipe']
    http_method_names = ['get']
    pagination_class = None
    def get_queryset(self):
        queryset = models.Ingredient.objects.all()
        queryset = queryset.order_by('title').distinct('title')
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class StepViewSet(ModelViewSet):
    queryset = models.Steps.objects.filter(is_deleted=False).order_by('id')
    serializer_class = serializers.StepSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    # filterset_class = filters.StepsFilter
    filterset_fields = ['recipe']
    pagination_class = None
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class StarchPreparationViewSet(ModelViewSet):
    queryset = models.Starch_Preparation.objects.filter(is_deleted=False)
    serializer_class = serializers.StarchPreparationSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_class = filters.StarchPreparationFilter
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class RecipeViewSet(ModelViewSet):
    queryset = models.Recipe.objects.all().prefetch_related('recipe_ingredient', 'predefined_ingredients')
    serializer_class = serializers.RecipeSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_fields = ['cusinie_type']
    filterset_class = filters.RecipeFilter
    pagination_class = pagination.CustomPageNumberPagination
    search_fields = ['dish_name', 'cusinie_type__category_name', 'description', 'availability', 'status', 'recipe_ingredient__title', 'predefined_ingredients__name']

    def get_serializer_class(self):
        if self.action in ['list']:
            return serializers.ListRecipeSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdminOrHeadChef()]
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset.filter(is_deleted=False).order_by("-id")
        elif user.role in [choices.Usertypes.ADMIN, choices.Usertypes.HEAD_CHEF]:
            queryset = queryset.filter(
                Q(status=choices.RecipeStatus.PUBLIC, is_deleted=False)
                | Q(is_deleted=False, user=user),resturant=user.resturant
            ).order_by("-id")
            return queryset
        else:
            return queryset.filter(status=choices.RecipeStatus.PUBLIC, is_deleted=False, resturant=user.resturant).order_by("-id")

    def filter_queryset(self, queryset):
        """
        Manually apply filter_backends inside action methods.
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    @action(detail=False, methods=['get'], url_path='get-all')
    def get_all(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.filter(
            resturant=user.resturant
        ).order_by("-id")

        # Apply filtering
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializers.ListRecipeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.ListRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='get-draft')
    def get_draft(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.filter(
            Q(status=choices.RecipeStatus.PUBLIC, is_deleted=False, is_draft=True)
            | Q(is_deleted=False, is_draft=True, user=user),resturant=user.resturant
        ).order_by("-id")
        
        # Apply filtering
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializers.ListRecipeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.ListRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='get-deleted')
    def get_deleted(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.filter(
            Q(status=choices.RecipeStatus.PUBLIC, is_deleted=True)
            | Q(is_deleted=True, user=user),resturant=user.resturant
        ).order_by("-id")

        # Apply filtering
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializers.ListRecipeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.ListRecipeSerializer(queryset, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['get'], url_path='get-live')
    def get_live(self, request, *args, **kwargs):
        user = request.user
        queryset = self.queryset.filter(
            Q(is_draft=False,status=choices.RecipeStatus.PUBLIC, is_deleted=False)
            | Q(is_deleted=False,is_draft=False, status=choices.RecipeStatus.PUBLIC , user=user),
            resturant=user.resturant
        ).order_by("-id")

        # Apply filtering
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializers.ListRecipeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = serializers.ListRecipeSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['patch'], url_path='restore')
    def restore(self, request, *args, **kwargs):
        recipe_id = request.data.get('pk')
        if not recipe_id:
            return Response({"error": "Recipe ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        recipe.is_deleted = False
        recipe.save()
        return Response({"message": "Recipe Restored successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='delete')
    def delete_recipe(self, request, *args, **kwargs):
        # get id from queryparams
        recipe_id = request.query_params.get('pk')
        if not recipe_id:
            return Response({"error": "Recipe ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        recipe.delete()
        return Response({"message": "Recipe Deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


    # def get_permissions(self):
    #     if self.request.method == 'GET':
    #         self.permission_classes = [AllowAny] 
    #     return super().get_permissions()        

    def perform_create(self, serializer):
        # try:
            with transaction.atomic():
                
                Images = self.request.data.get('recipe_image', [])
                starch_preparation_image = self.request.data.get('starch_preparation_image', None)
                plate_design_image = self.request.data.get('plate_design_image', None)

                recipe = serializer.save(user=self.request.user,resturant=self.request.user.resturant)

                steps_data = (self.request.data.get("steps", []))
                tags = (self.request.data.get("tags", []))
                ingredient = (self.request.data.get("ingredients", []))
                # center_of_plate = json.loads(self.request.data.get("centerOfPlate", "{}"))
                essential = (self.request.data.get("essential", []))
                starch_preparation = (self.request.data.get("starch_preparation", {}))
                design_your_plate = (self.request.data.get("design_your_plate", []))
                cooking_deviation_comment = (self.request.data.get("cooking_deviation_comment", []))
                real_time_variable_comment = (self.request.data.get("real_time_variable_comment", []))
                
                if Images:
                    for image in Images:
                        models.recipe_images.objects.create(recipe=recipe, image_url=image)


                if steps_data:
                    for step_data in steps_data:
                        serializer = serializers.StepSerializer(data=step_data)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)
                if tags:
                    for tag in tags:
                        serializer = serializers.TagSerializer(data=tag)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)

                if ingredient:
                    for ingredient_data in ingredient:
                        serializer = serializers.IngredientSerializer(data=ingredient_data)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)

                if essential:
                    for essential_data in essential:
                        serializer = serializers.EssentialsSerializer(data=essential_data)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)
                
                if starch_preparation:
                    starch_steps_data = starch_preparation.pop('steps', [])
                    image = starch_preparation_image
                    serializer = serializers.StarchPreparationSerializer(data={**starch_preparation})
                    if serializer.is_valid():
                        starch_instance=serializer.save(recipe=recipe, image_url=image)
                    else:
                        raise ValidationError(serializer.errors)

                    for step_data in starch_steps_data:
                        serializer = serializers.StarchPreparationStepsSerializer(data=step_data)
                        if serializer.is_valid():
                            serializer.save(starch_preparation=starch_instance)
                        else:
                            raise ValidationError(serializer.errors)
                
                if design_your_plate:
                    design_plate_data = {"recipe": recipe} 
                    image = plate_design_image
                    plate_steps_data = design_your_plate.pop('steps', [])
                    
                    design_your_plate_serializer = serializers.DesignYourPlateSerializer(data=design_plate_data)
                    if design_your_plate_serializer.is_valid():
                        design_your_plate_instance = design_your_plate_serializer.save(image_url=image, recipe=recipe)
                    else:
                        raise ValidationError(design_your_plate_serializer.errors)
                    
                    for step_data in plate_steps_data:
                        step_serializer = serializers.DesignYourPlateStepsSerializer(data=step_data)
                        if step_serializer.is_valid():
                            step_serializer.save(design_plate=design_your_plate_instance)
                        else:
                            raise ValidationError(step_serializer.errors)
                
                if cooking_deviation_comment:
                    for deviation_comment_data in cooking_deviation_comment:
                        serializer = serializers.CookingDeviationCommentSerializer(data=deviation_comment_data)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)
                        
                if real_time_variable_comment:
                    for variable_comment_data in real_time_variable_comment:
                        serializer = serializers.RealTimeVariableCommentSerializer(data=variable_comment_data)
                        if serializer.is_valid():
                            serializer.save(recipe=recipe)
                        else:
                            raise ValidationError(serializer.errors)
                return recipe
            print("created.")
        # except ValidationError as e:
        #     raise serializers.ValidationError(str(e))
        # except Exception as e:
        #     raise serializers.ValidationError(f"An unexpected error occurred:  {e}")
    
    def update(self, request, *args, **kwargs):
        # try:
        with transaction.atomic():
            instance = self.get_object()
            steps_data = (self.request.data.get("steps", []))
            tags = (self.request.data.get("tags", []))
            ingredient = (self.request.data.get("ingredients", []))
            essential = (self.request.data.get("essential", []))
            starch_preparation = (self.request.data.get("starch_preparation", {}))
            design_your_plate = (self.request.data.get("design_your_plate", []))
            cooking_deviation_comment = (self.request.data.get("cooking_deviation_comment", []))
            real_time_variable_comment = (self.request.data.get("real_time_variable_comment", []))
            starch_preparation_image = self.request.data.get('starch_preparation_image', None)
            plate_design_image = self.request.data.get('plate_design_image', None)
            Images = self.request.data.get('recipe_image')
            
            recipe_serializer = self.get_serializer(instance, data=request.data, partial=True, context=self.get_serializer_context())
            recipe_serializer.is_valid(raise_exception=True)
            recipe = recipe_serializer.save(user=self.request.user)
            existing_images = models.recipe_images.objects.filter(recipe=recipe)
            provided_image_ids = set()
            if Images:
                for image in Images:
                    
                        recipe_image = models.recipe_images.objects.create(
                            recipe=recipe,
                            image_url=image
                        )
                        provided_image_ids.add(recipe_image.id)

                

                existing_images.exclude(id__in=provided_image_ids).delete()

            provided_step_ids = set()
            if steps_data:
                for step_data in steps_data:
                    step_id = step_data.pop("id", None)
                    serializer = serializers.StepSerializer(data=step_data)
                    if serializer.is_valid():
                        step_instance, _ = models.Steps.objects.update_or_create(
                            id=step_id,
                            defaults={'title': serializer.validated_data.get('title'), 'recipe': recipe}
                        )
                        provided_step_ids.add(step_instance.id)
                    else:
                        raise ValidationError(serializer.errors)
                models.Steps.objects.filter(recipe=recipe).exclude(id__in=provided_step_ids).delete()

            provided_tag_ids = set()
            if tags:
                for tag in tags:
                    tag_id = tag.pop('id', None)
                    serializer = serializers.TagSerializer(data=tag)
                    
                    if serializer.is_valid():
                        tag_instance, _ = models.Tag.objects.update_or_create(
                            id=tag_id,
                            defaults={'name': serializer.validated_data.get('name'), 'recipe': recipe}
                        )
                        provided_tag_ids.add(tag_instance.id)
                    else:
                        raise ValidationError(serializer.errors)
                models.Tag.objects.filter(recipe=recipe).exclude(id__in=provided_tag_ids).delete()

            if ingredient:
                for ingredient_data in ingredient:
                    ingredient_id = ingredient_data.pop('id', None)
                    serializer = serializers.IngredientSerializer(data=ingredient_data)
                    if serializer.is_valid():
                        ingredient_instance, _ = models.Ingredient.objects.update_or_create(
                            id=ingredient_id,
                            defaults={
                                'title': serializer.validated_data.get('title'),
                                'recipe': recipe,
                                'quantity': serializer.validated_data.get('quantity'),
                                'unit': serializer.validated_data.get('unit')
                            }
                        )
                    else:
                        raise ValidationError(serializer.errors)


            provided_essential_ids = set()
            if essential:
                for essential_data in essential:
                    essential_id = essential_data.pop('id', None)
                    serializer = serializers.EssentialsSerializer(data=essential_data)
                    if serializer.is_valid():
                        essential_instance, _ = models.Essentials.objects.update_or_create(
                            id=essential_id,
                            defaults={
                                'title': serializer.validated_data.get('title'),
                                'recipe': recipe,
                                'quantity': serializer.validated_data.get('quantity'),
                                'unit': serializer.validated_data.get('unit')
                            }
                        )
                        provided_essential_ids.add(essential_instance.id)
                    else:
                        raise ValidationError(serializer.errors)
                models.Essentials.objects.filter(recipe=recipe).exclude(id__in=provided_essential_ids).delete()

            provided_starch_ids = set()
            # if isinstance(starch_preparation_image, str) and starch_preparation_image.startswith('http'):
            #         starch_preparation_image = image_url_to_context(starch_preparation_image)
            if starch_preparation:
                starch_steps_data = starch_preparation.pop('steps', [])
                starch_id = starch_preparation.pop('id', None)
                starch_instance,_ = models.Starch_Preparation.objects.update_or_create(
                    id=starch_id,
                    defaults={'image_url':starch_preparation_image, "recipe":recipe, "title":starch_preparation.get('title')}
                    
                )
                provided_starch_ids.add(starch_instance.id)

                provided_step_ids = set()
                if starch_steps_data:
                    for step_data in starch_steps_data:
                        serializer = serializers.StarchPreparationStepsSerializer(data=step_data)
                        step_id = step_data.pop("id", None)

                        if serializer.is_valid():
                            step_instance, _ = models.Starch_Preparation_Steps.objects.update_or_create(
                                id=step_id, 
                                defaults={'step': serializer.validated_data.get('step'), 'starch_preparation': starch_instance}
                            )
                        provided_step_ids.add(step_instance.id)

                    models.Starch_Preparation_Steps.objects.filter(starch_preparation=starch_instance).exclude(id__in=provided_step_ids).delete()
                    models.Starch_Preparation.objects.filter(recipe=recipe).exclude(id__in=provided_starch_ids).delete()

            provided_design_plate_ids = set()
            if design_your_plate:
                plate_id = design_your_plate.pop('id', None)

                # if isinstance(plate_design_image, str) and plate_design_image.startswith('http'):
                #         plate_design_image = image_url_to_context(plate_design_image)

                design_your_plate_instance, _ = models.Design_Your_Plate.objects.update_or_create(
                    id=plate_id,
                    defaults={'image_url': plate_design_image, "recipe":recipe}
                )
                provided_design_plate_ids.add(design_your_plate_instance.id)
                provided_design_plate_step_ids = set()
                plate_steps_data = design_your_plate.pop('steps', [])
                if plate_steps_data:
                    for step_data in plate_steps_data:
                        serializer = serializers.DesignYourPlateStepsSerializer(data=step_data)
                        if serializer.is_valid():
                            step_instance = serializer.save(design_plate=design_your_plate_instance)
                            provided_design_plate_step_ids.add(step_instance.id)
                        else:
                            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    models.Design_Your_Plate_Steps.objects.filter(design_plate=design_your_plate_instance).exclude(id__in=provided_design_plate_step_ids).delete()
                    models.Design_Your_Plate.objects.filter(recipe=recipe).exclude(id__in=provided_design_plate_ids).delete()

            provided_deviation_comment_ids = set()
            if cooking_deviation_comment:
                for deviation_comment_data in cooking_deviation_comment:
                    serializer = serializers.CookingDeviationCommentSerializer(data={**deviation_comment_data, "recipe": recipe})
                    if serializer.is_valid():
                        devivation_instance = serializer.save(recipe=recipe)
                        provided_deviation_comment_ids.add(devivation_instance.id)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                models.Cooking_Deviation_Comment.objects.filter(recipe=recipe).exclude(id__in=provided_deviation_comment_ids).delete()


            provided_variable_comment_ids = set()
            if real_time_variable_comment:
                for variable_comment_data in real_time_variable_comment:
                    serializer = serializers.RealTimeVariableCommentSerializer(data=variable_comment_data)
                    if serializer.is_valid():
                        variable_comment_id = variable_comment_data.pop('id', None)
                        variable_instance, _ = models.Real_time_Variable_Comment.objects.update_or_create(
                            id=variable_comment_id,
                            defaults={'step': serializer.validated_data.get('step'), 'recipe': recipe}
                        )
                        provided_variable_comment_ids.add(variable_instance.id)
                    else:
                        raise serializers.ValidationError(serializer.errors)
                models.Real_time_Variable_Comment.objects.filter(recipe=recipe).exclude(id__in=provided_variable_comment_ids).delete()
        
        return Response(recipe_serializer.data, status=status.HTTP_200_OK)

        # except ValidationError as e:
        #     raise serializers.ValidationError(str(e))
        # except Exception as e:
        #     raise serializers.ValidationError(f"An unexpected error occurred:  {e}")

    # def get_serializer_context(self):
    #     return super().get_serializer_context()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def best_selling(self, request):
        recipes = models.Recipe.objects.filter(status=choices.RecipeStatus.PUBLIC, is_draft=False,resturant=self.request.user.resturant)\
            .annotate(completed_task_count=Count('task_name', filter=Q(task_name__status=choices.TaskGenericStatus.COMPLETED)))\
            .order_by('-completed_task_count')[:4]
            

        serializer = serializers.RecipeWineSerializer(recipes, many=True, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def recipe_videos(self, request):
        try:
            if request.user.is_superuser:
                queryset = models.Recipe.objects.exclude(Q(video__isnull=True) | Q(video='') | Q(video_id__isnull=True)).values('id', 'dish_name', 'video')
                queryset = self.filter_queryset(queryset)
            else:
                queryset = models.Recipe.objects.exclude(Q(video__isnull=True) | Q(video='') | Q(video_id__isnull=True)).filter(resturant=self.request.user.resturant).values('id', 'dish_name', 'video')
            page = self.paginate_queryset(queryset)
            if page is not None:
                for recipe in page:
                    if recipe['video']:
                        video_url = recipe['video'].url if hasattr(recipe['video'], 'url') else recipe['video']
                        recipe['video'] = request.build_absolute_uri(settings.MEDIA_URL + video_url.split('media/')[-1])
                
                return self.get_paginated_response(page)
            
            for recipe in queryset:
                if recipe['video']:
                    video_url = recipe['video'].url if hasattr(recipe['video'], 'url') else recipe['video']
                    recipe['video'] = request.build_absolute_uri(settings.MEDIA_URL + video_url.split('media/')[-1])
            
            return Response({
                "recipes": list(queryset)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'] )
    def get_public_recipes(self, request):
        try:
            queryset = self.filter_queryset(models.Recipe.objects.filter(
                status=choices.RecipeStatus.PUBLIC, is_draft=False,is_deleted=False
            ).filter(Q(video__isnull=True) | Q(video=''),resturant=self.request.user.resturant).values('id', 'dish_name', 'description', 'food_cost','main_dish'))
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                return self.get_paginated_response(page)
            
            return Response({"recipes": list(queryset)}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def delete_videos(self, request, pk):
        if pk:
            recipe = self.get_object()
            video_id = recipe.video_id
            if not video_id:
                return Response({"message": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
            
            response = delete_video_from_synthesia(video_id)
            if response.status_code == 204:
                recipe.video = None
                recipe.video_id=None
                recipe.save()
                return Response({"message": "Video deleted successfully"}, status=status.HTTP_200_OK)

            else:
                return Response({"message": "Something went wrong!"}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"message": "Recipe id not provided"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_name="get_private_recipes")
    def get_private_recipes(self, request):
        recipes = models.Recipe.objects.filter(status=choices.RecipeStatus.PRIVATE, is_deleted=False, is_draft=False,is_schedule=False,resturant=self.request.user.resturant).order_by('-id').values('id','dish_name')
        return Response(recipes, status=status.HTTP_200_OK)
        
    def destroy(self, *args, **kwargs):
        pk = kwargs.get('pk')
        print(pk)
        print("deleting...")
        instance = models.Recipe.objects.get(pk=pk)
        print("instance",instance)
        if instance.manual_video:
            print("video")
            key = instance.manual_video.split('/')[-1]
            s3_utility.delete_file(key)
            instance.manual_video_key = None
            instance.manual_video = None
        instance.is_deleted = True
        instance.save()
        print("deleted")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="request_upload", permission_classes=[IsAdminOrHeadChef, IsAuthenticated])
    def request_upload(self, request):
        try:
            serializer = serializers.FileUploadRequestSerializer(
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            return Response({"presigned_url": serializer.generate_presigned_url(), "expires_in": "60 minutes", "key" : request.data.get("file") }, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError({"detail": [str(e)]})
        

class TemplateGenerationViewset(ReadOnlyModelViewSet):
    queryset = models.Recipe.objects.filter(is_deleted=False,is_draft=False,status=choices.RecipeStatus.PUBLIC)
    serializer_class = serializers.TemplateGenerationSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_class = filters.TemplateGenerationRecipeFilter
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset.filter(is_deleted=False)
        elif user.role in[choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF,choices.Usertypes.ADMIN]:
            return queryset.filter(is_deleted=False, resturant=user.resturant)
        return queryset

    

    @action(detail=False, methods=['get'], url_path='get-recipes')
    def get_recipes(self, request):
        ids_param = request.query_params.get('ids')
        if not ids_param:
            return Response({"detail": "No IDs provided."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            id_list = [int(i.strip()) for i in ids_param.split(',') if i.strip().isdigit()]
        except ValueError:
            return Response({"detail": "Invalid IDs provided."}, status=status.HTTP_400_BAD_REQUEST)
        filtered_qs = self.queryset.filter(id__in=id_list)
        serializer = serializers.GetRecipeSerializer(filtered_qs, many=True)
        serialized_data = serializer.data
        for data in serialized_data:
            data['recipe_name'] = data['dish_name']
            del data['dish_name']
            data['is_special'] = False
        return Response(serialized_data)
        
class MenuTemplateViewSet(ModelViewSet):
    queryset = models.MenuTemplate.objects.filter(is_deleted=False)
    serializer_class = serializers.MenuTemplateSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_fields = ['resturant']

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.MenuTemplateListSerializer
        return serializers.MenuTemplateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset.filter(is_deleted=False)
        elif user.role in[choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF,choices.Usertypes.ADMIN]:
            return queryset.filter(is_deleted=False, resturant=user.resturant)
        return queryset
    

class StarchPreparationStepsViewSet(ModelViewSet):
    queryset = models.Starch_Preparation_Steps.objects.filter(is_deleted=False)
    serializer_class = serializers.StarchPreparationStepsSerializer
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filter_class = filters.Starch_Preparation_Steps
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class DesignYourPlateViewSet(ModelViewSet):
    queryset = models.Design_Your_Plate.objects.filter(is_deleted=False)
    serializer_class = serializers.DesignYourPlateSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class DesignYourPlateStepsViewSet(ModelViewSet):
    queryset = models.Design_Your_Plate_Steps.objects.filter(is_deleted=False)
    serializer_class = serializers.DesignYourPlateStepsSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    
class PredefinedIngredientsViewSet(ModelViewSet):
    queryset = models.Predefined_Ingredients.objects.all()
    serializer_class = serializers.PredefinedIngredientsSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    

    
class PredefinedStarchViewSet(ModelViewSet):
    queryset = models.Predefined_Starch.objects.all()
    serializer_class = serializers.PredefinedStarchSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

    
class PredefinedVegetableViewSet(ModelViewSet):
    queryset = models.Predefined_Vegetable.objects.all()
    serializer_class = serializers.PredefinedVegetableSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    

class CookingDeviationCommentViewSet(ModelViewSet):
    queryset = models.Cooking_Deviation_Comment.objects.all()
    serializer_class = serializers.CookingDeviationCommentSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class RealTimeVariableCommentViewSet(ModelViewSet):
    queryset = models.Real_time_Variable_Comment.objects.all()
    serializer_class = serializers.RealTimeVariableCommentSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class RecipeProcessAuditViewSet(ModelViewSet):
    queryset = models.Recipe_Process_Audit.objects.filter(is_deleted=False)
    serializer_class = serializers.RecipeProcessAuditSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.filter(is_deleted=False)
        elif user.role in [choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF, choices.Usertypes.ADMIN]:
            return self.queryset.filter(is_deleted=False, changed_by__resturant=user.resturant)
        return self.queryset.none()

    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
        
class RatingViewSet(ModelViewSet):
    queryset = models.Rating.objects.all()
    serializer_class = serializers.RatingSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class SelectHolidayViewSet(ModelViewSet):
    queryset = models.Select_Holiday.objects.all()
    serializer_class = serializers.SelectHolidaySerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    https_method_names = ['get']
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    
class ScheduleDishViewSet(ModelViewSet):
    queryset = models.Schedule_Dish.objects.filter(is_deleted=False)
    serializer_class = serializers.ScheduleDishSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filter_class = filters.ScheduleDishFilter

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.filter(schedule_datetime__gt=timezone.now())
        elif user.role in [choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF, choices.Usertypes.ADMIN]:
            return self.queryset.filter(creator__resturant=user.resturant,schedule_datetime__gt=timezone.now())
        return self.queryset.none()
    
    @action(detail=False, methods=['post'])
    def schedule(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule_datetime = serializer.validated_data['schedule_datetime']
        dish_id = serializer.validated_data['dish'].id

        job = scheduler.add_job(
            create_or_update_schedule_dish,
            'date',
            run_date=schedule_datetime,
            args=[dish_id]
        )
        serializer.save(job = job.id, creator=request.user)
        recipe = models.Recipe.objects.get(id=dish_id)
        recipe.is_schedule = True
        recipe.save()
        return Response(
            {"message": "Dish scheduled successfully.", "job_id": job.id},
            status=status.HTTP_200_OK
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        recipe = models.Recipe.objects.get(id=instance.dish.id)
        recipe.is_schedule = False
        recipe.save()
        job = scheduler.get_job(instance.job)
        if job:
            scheduler.remove_job(instance.job)
        instance.job = None
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class TaskViewSet(ModelViewSet):
    queryset = models.Task.objects.all()
    serializer_class = serializers.TaskSerializer
    permission_classes = [IsAuthenticated, TaskEditDeletePermission,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filter_class = filters.TaskFilter
    search_fields = ['task_description', 'kitchen_station', 'other_task_name', 'staff__first_name','user__first_name','task_name__dish_name']

    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.filter(is_deleted=False)
        if user.role in [choices.Usertypes.ADMIN,choices.Usertypes.HEAD_CHEF]:
            return self.queryset.filter(is_deleted=False,resturant=user.resturant)
        elif user.role == choices.Usertypes.STAFF:
            return self.queryset.filter(Q(user=user) | Q(staff=user), is_deleted=False, resturant=user.resturant)
        else:
            return self.queryset.none()
    
    
    def get_serializer_class(self):
        if self.action == "list":
            return serializers.TaskListSerializer
        return self.serializer_class
    
    def get_serializer_context(self):
        return super().get_serializer_context()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user,resturant=self.request.user.resturant, status=choices.TaskGenericStatus.ASSIGNED)

    @action(detail=True, methods='get')
    def get_completed_task(self, request):
        res = models.Task.objects.filter(status=choices.TaskGenericStatus.COMPLETED)
        return Response(serializers.TaskSerializer(res,many=True, context=self.get_serializer_context()).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_name='get_all_task')
    def get_all_task(self,request):
        res = models.Task.objects.all().exclude(is_deleted=True)
        return Response(serializers.TaskSerializer(res,many=True).data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsAdminOrHeadChefOrStaff])
    def update_task_status(self, request, pk):

        task = self.get_object()
        status = request.data.get('status')
        if status:
            task.status = status
            task.save()
            serializer = serializers.TaskSerializer(task, context=self.get_serializer_context())
            return Response(serializer.data)
        else:
            return Response({"error": "Please provide status"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def task_detail(self, request, pk):
        task = get_object_or_404(models.Task, pk=pk)
        serializer = serializers.TaskSerializer(task, context=self.get_serializer_context())
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        if self.request.user.role == 'S':
            raise ValidationError({"detail": "You don't have permission to delete a task."})
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
        
class WineViewSet(ModelViewSet):
    queryset = models.Wine.objects.all()
    serializer_class = serializers.WineSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    http_method_names = ['get']
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    

class AdminDashboardViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]

    def list(self, request, *args, **kwargs):
        start_date_param = request.GET.get('start_date', None)
        end_date_param = request.GET.get('end_date', None)

        user = self.request.user
        try:
            # Base filter including date range if provided
            date_filter = Q(is_deleted=False)

            if start_date_param or end_date_param:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date() if start_date_param else datetime(1900, 1, 1).date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date() if end_date_param else datetime.today().date()
                date_filter &= Q(created_at__date__range=[start_date, end_date])

            # Single Query for Task Counts
            task_aggregation = models.Task.objects.filter(date_filter).filter(resturant=user.resturant).aggregate(
                total_task=Count("id"),
                assigned_task=Count("id", filter=Q(status=choices.TaskGenericStatus.ASSIGNED)),
                pending_task=Count("id", filter=Q(status=choices.TaskGenericStatus.IN_PROGRESS)),
                completed_task=Count("id", filter=Q(status=choices.TaskGenericStatus.COMPLETED)),
                cancelled_task=Count("id", filter=Q(status=choices.TaskGenericStatus.CANCELLED)),
                total_sales=Sum("task_name__food_cost", filter=Q(status=choices.TaskGenericStatus.COMPLETED))
            )

            users = models.User.objects.filter(date_filter & Q(is_active=True)).filter(resturant=user.resturant)
            total_users = users.count()
            # Staff Count
            total_staff = users.filter(role=choices.Usertypes.STAFF).count()


            # Distinct Dish Count
            total_dishes = models.Recipe.objects.filter(date_filter).filter(resturant=user.resturant).values("dish_name").distinct().count()

            # Best Selling Dish Query
            average_rating_subquery = models.Rating.objects.filter(
                recipe=OuterRef("task_name__id")
            ).values("recipe").annotate(average_rating=Avg("rating")).values("average_rating")

            total_count_subquery = models.Rating.objects.filter(
                recipe=OuterRef("task_name__id")
            ).values("recipe").annotate(total_count=Count("rating")).values("total_count")

            best_selling_dish = models.Task.objects.filter(
                date_filter & Q(status=choices.TaskGenericStatus.COMPLETED)
            ).filter(resturant=user.resturant).values("task_name__dish_name", "task_name__id").annotate(
                total=Sum("task_name__food_cost"),
                average_rating=Subquery(average_rating_subquery, output_field=FloatField()),
                total_rating_count=Subquery(total_count_subquery, output_field=IntegerField())
            ).order_by("-total")[:5]

            # Response Data
            data = {
                'total_users': total_users,
                'total_staff': total_staff,
                'total_task': task_aggregation["total_task"],
                'total_sales': task_aggregation["total_sales"] or 0,
                'total_dishes': total_dishes,
                'assigned_task': task_aggregation["assigned_task"],
                'pending_task': task_aggregation["pending_task"],
                'completed_task': task_aggregation["completed_task"],
                'cancelled_task': task_aggregation["cancelled_task"],
                'best_selling_dish': best_selling_dish,
            }

            return Response(data)
        
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

class SuperAdminDashboardViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated,IsAdminUser]

    def list(self, request, *args, **kwargs):
        try:
            start_date_param = request.GET.get('start_date', None)
            end_date_param = request.GET.get('end_date', None)

            date_filter = Q()
            start_date = datetime(1900, 1, 1).date()
            end_date = datetime.today().date()
            if start_date_param or end_date_param:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date() if start_date_param else datetime(1900, 1, 1).date()
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date() if end_date_param else datetime.today().date()
                date_filter &= Q(created_at__date__range=[start_date, end_date])

            users = models.User.objects.filter(date_filter).exclude(is_superuser=True, is_staff=True)
            total_users = users.count()
            active_users = users.filter(is_deleted=False)
            active_users_count = active_users.count()
            inactive_users = users.filter(is_deleted=True).count()
            revenue = models.Resturant.objects.filter(
                plan__isnull=False,
                created_at__date__range=[start_date, end_date]
            ).aggregate(
                total_revenue=Sum('plan__price')
            )
            
            data = [
                {'total_users':total_users},
                {'active_users':active_users_count},
                {'inactive_users':inactive_users},
                {'total_revenue': revenue['total_revenue'] or 0.0}
            ]

            return Response(data)

        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='get-monthly-users')
    def get_monthly_users(self, request):
        try:
            current_year = datetime.today().year

            start_date_param = request.GET.get('start_date', f"{current_year}-01-01")
            end_date_param = request.GET.get('end_date', f"{current_year}-12-31")

            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()

            users = models.User.objects.filter(
                created_at__date__range=[start_date, end_date]
            ).values(
                'created_at__year', 'created_at__month'
            ).annotate(
                user_count=Count('id')
            ).order_by('created_at__month')

            user_data_map = {item['created_at__month']: item['user_count'] for item in users}

            full_year_data = []
            for month in range(1, 13):
                full_year_data.append({
                    "year": current_year,
                    "month": month,
                    "user_count": user_data_map.get(month, 0)
                })

            return Response(full_year_data, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='get-yearly-revenue')
    def get_yearly_revenue(self, request):
        try:
            year_param = request.GET.get('year')
            if year_param:
                year = int(year_param)
            else:
                year = datetime.today().year

            restaurants = models.Resturant.objects.filter(
                plan__isnull=False,
                plan_start_date__year=year
            )

            monthly_data = restaurants.annotate(
                month=ExtractMonth('plan_start_date')
            ).values('month').annotate(
                total_revenue=Sum('plan__price')
            ).order_by('month')

            revenue_map = {item['month']: float(item['total_revenue']) for item in monthly_data}

            result = []
            for month in range(1, 13):
                result.append({
                    "month": calendar.month_name[month],
                    "total_revenue": revenue_map.get(month, 0.0)
                })

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MessageViewSet(ModelViewSet):
    queryset = models.Message.objects.all()
    serializer_class = serializers.MessageSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]

    def get_serializer_context(self):
        return super().get_serializer_context()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class WinePairViewSet(ViewSet):
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    
    @action(detail=False, methods=['post'])
    def get_wine_pairing(self, request):

        try:
            dish_description = request.data.get("dish_description", "")
            recipe_id = request.data.get("recipe_id", None)
            if not dish_description:
                return Response({"error": "Dish description is required."}, status=400)
            
            wine_pairing = culinary_ai.get_wine_pairing(dish_description)
            res = store_wine_pairings(wine_pairing, recipe_id)
            
            if not res:
                return Response({"error": "An error occurred while saving the wine pairing data."}, status=400)
            return Response({"wine_pairing": wine_pairing}, status=200)
        
        except Exception as e:
            logger.error(f"Error in wine pairing recommendation: {str(e)}")
            return Response({"error": f"An error occurred while processing the wine pairing : {str(e)}"}, status=400)

class RecipeWineViewSet(ModelViewSet):
    queryset = models.Recipe.objects.filter(status=choices.RecipeStatus.PUBLIC, is_deleted=False, wine_pairing__isnull=False).prefetch_related('wine_pairing').distinct()
    serializer_class = serializers.RecipeWineSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    search_fields = ['dish_name']
    filterset_class = filters.RecipeFilter
    http_method_names = "get"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset.filter(is_deleted=False)
        elif user.role in [choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF, choices.Usertypes.ADMIN]:
            return self.queryset.filter(is_deleted=False, resturant=user.resturant)
        return self.queryset.none()

    
class ExtraImageViewSet(ModelViewSet):
    queryset = models.RecipeImage_extra.objects.all()
    serializer_class = serializers.ExtraImagesSerializer
    permission_classes = [IsAuthenticated, IsAdminOrHeadChef,IsSubscribedORSuperUser]

    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()


class RecipeVideoGenerationViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrHeadChef,IsSubscribedORSuperUser]
    http_method_names = ['post']
    

    @action(detail=False, methods=['post'])
    def generate_video(self, request):
        serializer = serializers.RecipeVideoGenerationSerializer(data=request.data)
        if serializer.is_valid():
            transformed_data = serializer.data
            response = generate_video_and_save(
                recipe_id=transformed_data['recipe'],
                recipe_name=transformed_data['recipe_name'],
                introduction=transformed_data['introduction'],
                # name_chef=transformed_data['name_chef'],zz
                steps=transformed_data['steps_text'],
                ingredient=transformed_data['ingredients_list'],
                last_words=transformed_data['last_words'],
                template_id=transformed_data['template_id'],
                title=transformed_data['title'],
                language=transformed_data['language'],
                welcome="WELCOME",
                to="TO",
                plateprep="PLATEPREP",
                training_phrase="THIS IS THE TRAINING VIDEO OF",
                ingridiants_start="Let's begin by gathering the ingredients. You will need:",
            )
            if response.status_code == 200:
                recipe = models.Recipe.objects.get(id=transformed_data['recipe'])
                video_url = None
                if recipe.video:
                    video_url = request.build_absolute_uri(settings.MEDIA_URL + recipe.video.name.split('media/')[-1])
                
                return Response({
                        "id": recipe.id,
                        "title": recipe.dish_name,
                        "video": video_url,
                    },
                    status=200
                )
            else:
                return Response(
                    {"error": "Failed to generate video"},
                    status=400
                )
                
        else:
            return Response(serializer.errors, status=400)


class NotificationViewSet(ModelViewSet):
    serializer_class = serializers.NotificationSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    http_method_names = ["get"]

    def get_queryset(self):
        return models.Notification.objects.filter(related_dish__resturant=self.request.user.resturant).order_by('-created_at')
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def mark_as_seen(self, request, pk=None):
        try:
            notification = self.get_object()
            user = request.user

            if not notification.seen_by_users.filter(id=user.id).exists():
                notification.seen_by_users.add(user)
                notification.save()

                return Response({
                    "message": "Notification marked as seen."
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "message": "Notification was already seen by user."
                }, status=status.HTTP_200_OK)

        except models.Notification.DoesNotExist:
            return Response({
                "message": "Notification not found."
            }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({
                "message": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class AIRecipeGenerationViewSet(ViewSet):   

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdminOrHeadChef,IsSubscribedORSuperUser])
    def generate_recipe(self, request):
        serializer = serializers.AIRecipeGenerationSerializer(data=request.data)
        
        if serializer.is_valid():
            validated_data = serializer.validated_data

            try:
                print(validated_data)
                result = culinary_ai.generate_menu(**validated_data)
                # result = recipe_data
                return Response({'result': result}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MenuCategoriesViewSet(ModelViewSet):
    serializer_class = serializers.CategorySerializer
    queryset = models.MenuCategoryies.objects.all().order_by('category_name')
    permission_classes = [IsAuthenticated, IsSubscribedORSuperUser]
    http_method_names = ["get"]
    pagination_class =  None
    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [IsAuthenticated, IsSubscribedORSuperUser]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class MenuViewSet(ModelViewSet):
    serializer_class = serializers.MenuSerializer
    queryset = models.Menu.objects.all()
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)
    
    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()
    
    def get_serializer_class(self):
        if self.action == "list":
            return serializers.MenuListSerializer
        return super().get_serializer_class()
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(is_deleted=False)
        return queryset

class MenuItemsViewSet(ModelViewSet):
    serializer_class = serializers.MenuItemSerializer
    queryset = models.MenuItems.objects.all()
    permission_classes = [IsAuthenticated, IsSubscribedORSuperUser]

    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

# class GrammarCheckView(APIView):
#     def post(self, request, *args, **kwargs):
#         serializer = serializers.GrammarCheckSerializer(data=request.data)
#         if serializer.is_valid():
#             result = serializer.create(serializer.validated_data)
#             return Response(result, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetPresingedUrl(ModelViewSet):
    queryset = models.User.objects.none()
    permission_classes = [IsAuthenticated, IsAdminOrHeadChef,IsSubscribedORSuperUser]
    serializer_class = serializers.FileUploadRequestSerializer
    http_method_names = ['post']

    @action(detail=False, methods=["post"], url_path="request_upload", permission_classes=[IsAdminOrHeadChef, IsAuthenticated])
    def request_upload(self, request):
        try:
            serializer = serializers.FileUploadRequestSerializer(
                data=request.data,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            return Response({"presigned_url": serializer.generate_presigned_url(), "expires_in": "60 minutes", "key" : request.data.get("file") }, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError({"detail": [str(e)]})

class SpellCheckAPI(APIView):
    def post(self, request):
        serializer = serializers.SpellCheckSerializer(data={"data": request.data})
        if serializer.is_valid():
            corrected_data = {}
            for field, value in serializer.validated_data["data"].items():
                if isinstance(value, dict) and "title" in value and "index" in value:
                    corrected_data[field] = {
                        "title": spell_checker(value["title"]),
                        "index": value["index"]
                    }
                else:
                    corrected_data[field] = value
            return Response(corrected_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginLogViewSet(ReadOnlyModelViewSet):
    queryset = models.LoginLog.objects.all().order_by('-timestamp')
    serializer_class = serializers.LoginLogSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        elif user.role in [choices.Usertypes.HEAD_CHEF, choices.Usertypes.STAFF, choices.Usertypes.ADMIN]:
            return self.queryset.filter(user__resturant=user.resturant)
        return self.queryset.none()


class InstructionVideoViewSet(ModelViewSet):
    queryset = models.InstructionalVideo.objects.all()
    serializer_class = serializers.InstructionVideoSerializer
    permission_classes = [AllowAny]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class ShiftNoteViewSet(ModelViewSet):
    queryset = models.ShiftNote.objects.all()
    serializer_class = serializers.ShiftNoteSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_fields = {
        "resturant": ["exact"],
        "created_by": ["exact"],
        "date": ["exact", "range"],
        "shift": ["exact"]
    }

    search_fields = ['note', 'created_by__first_name', 'created_by__last_name']
    
    def get_queryset(self):
        return super().get_queryset().filter(resturant=self.request.user.resturant)


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()


class DictionaryCategoryViewset(ModelViewSet):
    queryset = models.DictionaryCategory.objects.filter(is_deleted=False)
    serializer_class = serializers.DictionaryCategorySerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)

class DictionaryItemsViewset(ModelViewSet):
    queryset = models.DictionaryItem.objects.filter(is_deleted=False)
    serializer_class = serializers.DictionaryItemSerializer
    permission_classes = [IsAuthenticated,IsSubscribedORSuperUser]
    filter_backends = [DjangoFilterBackend, filter.SearchFilter, filter.OrderingFilter]
    filterset_fields = {
        "category": ["exact"],
        "term": ["exact", "icontains"],
        "definition": ["exact", "icontains"],
    }
    search_fields = ['term', 'definition']
    

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True  # Assuming the model has this field
        instance.save()
        return Response({"detail": "Object soft deleted."}, status=status.HTTP_204_NO_CONTENT)


class EditorViewset(ModelViewSet):
    serializer_class = serializers.EditorTemplateSerializer

    def get_queryset(self):
        return models.EditorTemplate.objects.filter(resturant=self.request.user.resturant)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.EditorSmallDetailsSerializer
        return super().get_serializer_class()

class EditorImageViewset(ModelViewSet):
    serializer_class = serializers.EditorImageSerializer

    def get_queryset(self):
        return models.EditorImage.objects.filter(resturant=self.request.user.resturant)