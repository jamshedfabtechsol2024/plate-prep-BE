import time
import base64
import logging
import datetime
import requests
import threading
from app import models
from typing import Optional
from app.ai_image import Image
from django.utils import timezone
from django.dispatch import receiver
import django.utils.timezone as timezone
from datetime import datetime, timedelta
from app.starch_image import StarchImage
from app.middleware import get_current_user
from django.db.models.signals import post_save
from app.utils import fetch_and_get_wine_pairing
from django.contrib.auth.signals import user_logged_in
from app.serializers import FileUploadRequestSerializer
from apscheduler.schedulers.background import BackgroundScheduler


logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()
scheduler.start()


EXCLUDED_FIELDS = [
    "created_at",
    "updated_at",
    "is_deleted",
    "recipe",
    "image",
    "video",
    "video_id",
]


# @receiver(post_save, sender=models.Wine)
@receiver(post_save, sender=models.Steps)
@receiver(post_save, sender=models.Predefined_Ingredients)
@receiver(post_save, sender=models.Cooking_Deviation_Comment)
@receiver(post_save, sender=models.Design_Your_Plate)
@receiver(post_save, sender=models.Starch_Preparation)
@receiver(post_save, sender=models.Essentials)
@receiver(post_save, sender=models.Tag)
@receiver(post_save, sender=models.Recipe)
@receiver(post_save, sender=models.Real_time_Variable_Comment)
def log_recipe_and_process_update(sender, instance, created, **kwargs):

    user = get_current_user()
    if user is None or not user.is_authenticated:
        return

    recipe = instance.recipe if hasattr(instance, "recipe") else instance
    changes = []

    if created:
        pass
    else:
        for field in instance._meta.fields:
            if field.name in EXCLUDED_FIELDS:
                continue

            new_value = field.value_from_object(instance)
            original_value = getattr(instance, f"__original_{field.name}", None)

            if field.name != "id" and new_value != original_value:
                changes.append(
                    {sender.__name__: instance.id, field.name: f"{new_value}"}
                )

        if changes:
            changes_made = "\n".join(
                [
                    f"{key}: {value}"
                    for change in changes
                    for key, value in change.items()
                ]
            )
            res = models.Recipe_Process_Audit.objects.create(
                dish_name=recipe,
                changed_by=user,
                changes_made=changes_made,
                datetime=timezone.now(),
            )

    def set_original_values(sender, instance, **kwargs):
        for field in instance._meta.fields:
            if field.name not in EXCLUDED_FIELDS:
                setattr(
                    instance,
                    f"__original_{field.name}",
                    field.value_from_object(instance),
                )

    for model in [
        models.Wine,
        models.Steps,
        models.Predefined_Ingredients,
        models.Cooking_Deviation_Comment,
        models.Design_Your_Plate,
        models.Starch_Preparation,
        models.Starch_Preparation_Steps,
        models.Design_Your_Plate_Steps,
        models.Essentials,
        models.Tag,
        models.Recipe,
        models.Real_time_Variable_Comment,
    ]:
        post_save.connect(set_original_values, sender=model)


# @receiver(post_save, sender=models.Recipe)
# def create_wine_pairing(sender, instance, created, **kwargs):
#     def handle_wine_pairing():
#         instance.refresh_from_db()
#         images = instance.recipe_image.all()

#         if images.exists():
#             pass  # Skip image generation if images already exist
#         else:
#             image=Image()
#             base64_image = image.image(dish_name=instance.dish_name, ingredients=list(instance.recipe_ingredient.values_list('title', flat=True)))
#             print("Base64 Image:", base64_image)
#             if base64_image:
#                 # Convert base64 to bytes
#                 try:
#                     image_data = base64.b64decode(base64_image.split(',')[-1])
#                     image_name = f"{instance.dish_name.replace(' ', '_')}_{instance.id}.png"

#                     # Generate presigned URL
#                     serializer = FileUploadRequestSerializer(data={'file': image_name})
#                     serializer.is_valid(raise_exception=True)
#                     presigned_url = serializer.generate_presigned_url()

#                     # Upload to S3
#                     response = requests.put(presigned_url, data=image_data, headers={'Content-Type': 'image/png'})
#                     if response.status_code == 200:
#                         # Store the S3 URL in the database
#                         s3_url = presigned_url.split('?')[0]
#                         models.recipe_images.objects.create(recipe=instance, image_url=s3_url)
#                     else:
#                         logger.error(f"Failed to upload image to S3 for recipe {instance.id}: {response.text}")
#                 except Exception as e:
#                     logger.error(f"Error processing image for recipe {instance.id}: {str(e)}")
#                     return

#         try:
#             ingredients_list = list(instance.recipe_ingredient.values_list('title', flat=True))
#             predefined_list = list(instance.predefined_ingredients.values_list('name', flat=True))
#             all_ingredients = ingredients_list + predefined_list

#             if all_ingredients:
#                 if len(all_ingredients) > 1:
#                     ingredients_text = ", ".join(all_ingredients[:-1]) + ", and " + all_ingredients[-1]
#                 else:
#                     ingredients_text = all_ingredients[0]
#                 description = f"{instance.dish_name} with {ingredients_text}"
#             else:
#                 description = instance.dish_name
#             if not instance.is_draft:
#                 fetch_and_get_wine_pairing(description, instance.id)
#         except Exception as e:
#             logger.error(f"Error in create_wine_pairing signal for recipe {instance.id}: {str(e)}")

#     transaction.on_commit(handle_wine_pairing)


# Patch for DRF < 3.15 expecting timezone.utc
if not hasattr(timezone, "utc"):
    timezone.utc = datetime.timezone.utc


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT")
    models.LoginLog.objects.create(user=user, ip_address=ip, user_agent=user_agent)



class ImageUploadService:
    """Service class to handle image upload operations to S3"""

    @staticmethod
    def upload_to_s3(image_data: bytes, filename: str) -> Optional[str]:
        """
        Upload image data to S3 and return the URL

        Args:
            image_data: Base64 decoded image bytes
            filename: Name for the uploaded file

        Returns:
            S3 URL if successful, None otherwise
        """
        try:
            serializer = FileUploadRequestSerializer(data={"file": filename})
            serializer.is_valid(raise_exception=True)
            presigned_url = serializer.generate_presigned_url()

            response = requests.put(
                presigned_url,
                data=image_data,
                headers={"Content-Type": "image/png"},
                timeout=30,
            )

            if response.status_code == 200:
                return presigned_url.split("?")[0]
            else:
                logger.error(
                    f"S3 upload failed with status {response.status_code}: {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return None

    @staticmethod
    def process_base64_image(base64_image: str) -> Optional[bytes]:
        """
        Convert base64 image string to bytes

        Args:
            base64_image: Base64 encoded image string

        Returns:
            Image bytes if successful, None otherwise
        """
        try:
            if not base64_image:
                return None
            return base64.b64decode(base64_image.split(",")[-1])
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            return None


# Background job functions
def generate_recipe_image_job(recipe_id):
    """
    Background job to generate and upload recipe image
    """
    try:
        recipe = models.Recipe.objects.get(id=recipe_id)

        # Check if images already exist
        if recipe.recipe_image.exists():
            logger.info(f"Recipe {recipe_id} already has images, skipping generation")
            return

        # Generate image
        ingredients = list(recipe.recipe_ingredient.values_list("title", flat=True))
        image_generator = Image()
        base64_image = image_generator.image(
            dish_name=recipe.dish_name, ingredients=ingredients
        )

        if not base64_image:
            logger.warning(f"No image generated for recipe {recipe_id}")
            return

        # Process and upload image
        image_data = ImageUploadService.process_base64_image(base64_image)
        if not image_data:
            logger.error(f"Failed to process image data for recipe {recipe_id}")
            return

        filename = f"{recipe.dish_name.replace(' ', '_')}_{recipe_id}.png"
        s3_url = ImageUploadService.upload_to_s3(image_data, filename)

        if s3_url:
            # Save to database
            models.recipe_images.objects.create(recipe=recipe, image_url=s3_url)
            logger.info(f"Successfully created image for recipe {recipe_id}")
        else:
            logger.error(f"Failed to upload image for recipe {recipe_id}")

    except models.Recipe.DoesNotExist:
        logger.error(f"Recipe {recipe_id} not found")
    except Exception as e:
        logger.error(f"Error generating recipe image for {recipe_id}: {str(e)}")


def generate_wine_pairing_job(recipe_id):
    """
    Background job to generate wine pairing
    """
    try:
        recipe = models.Recipe.objects.select_related().get(id=recipe_id)

        if recipe.is_draft:
            logger.info(f"Skipping wine pairing for draft recipe {recipe_id}")
            return

        # Get ingredients description
        ingredients_list = list(
            recipe.recipe_ingredient.values_list("title", flat=True)
        )
        predefined_list = list(
            recipe.predefined_ingredients.values_list("name", flat=True)
        )
        all_ingredients = ingredients_list + predefined_list

        if not all_ingredients:
            description = recipe.dish_name
        elif len(all_ingredients) == 1:
            description = f"{recipe.dish_name} with {all_ingredients[0]}"
        else:
            ingredients_text = (
                ", ".join(all_ingredients[:-1]) + ", and " + all_ingredients[-1]
            )
            description = f"{recipe.dish_name} with {ingredients_text}"

        fetch_and_get_wine_pairing(description, recipe_id)
        logger.info(f"Wine pairing generated for recipe {recipe_id}")

    except models.Recipe.DoesNotExist:
        logger.error(f"Recipe {recipe_id} not found")
    except Exception as e:
        logger.error(f"Error generating wine pairing for recipe {recipe_id}: {str(e)}")


def generate_starch_image_job(starch_prep_id):
    """
    Background job to generate starch preparation image
    """
    try:
        starch_prep = models.Starch_Preparation.objects.get(id=starch_prep_id)

        if starch_prep.image_url:
            logger.info(f"Starch preparation {starch_prep_id} already has image")
            return

        # Get preparation steps
        steps = starch_prep.starch.order_by("id").values_list("step", flat=True)
        steps_text = " ".join(steps)

        # Generate image
        image_generator = StarchImage()
        base64_image = image_generator.image(
            dish_name=starch_prep.title, steps=steps_text
        )

        if not base64_image:
            logger.warning(
                f"No image generated for starch preparation {starch_prep_id}"
            )
            return

        # Process and upload image
        image_data = ImageUploadService.process_base64_image(base64_image)
        if not image_data:
            logger.error(
                f"Failed to process image data for starch preparation {starch_prep_id}"
            )
            return

        filename = f"{starch_prep.title.replace(' ', '_')}_{starch_prep_id}.png"
        s3_url = ImageUploadService.upload_to_s3(image_data, filename)

        if s3_url:
            starch_prep.image_url = s3_url
            starch_prep.save()
            logger.info(
                f"Successfully created image for starch preparation {starch_prep_id}"
            )
        else:
            logger.error(
                f"Failed to upload image for starch preparation {starch_prep_id}"
            )

    except models.Starch_Preparation.DoesNotExist:
        logger.error(f"Starch preparation {starch_prep_id} not found")
    except Exception as e:
        logger.error(f"Error generating starch image for {starch_prep_id}: {str(e)}")


class JobSchedulerService:
    """Service to manage background jobs using APScheduler"""

    @staticmethod
    def schedule_job_with_delay(func, args, delay_seconds=1, job_id_prefix="job"):
        """Schedule a job to run after a delay"""
        try:
            job_id = f"{job_id_prefix}_{args[0]}_{int(time.time())}"
            run_time = datetime.now() + timedelta(seconds=delay_seconds)

            scheduler.add_job(
                func=func,
                args=args,
                trigger="date",
                run_date=run_time,
                id=job_id,
                replace_existing=True,
                max_instances=1,
            )
            logger.info(f"Scheduled job {job_id} to run at {run_time}")
            return job_id
        except Exception as e:
            logger.error(f"Error scheduling job {job_id_prefix}: {str(e)}")
            return None

    @staticmethod
    def schedule_recipe_image_generation(recipe_id, delay_seconds=1):
        """Schedule recipe image generation job"""
        return JobSchedulerService.schedule_job_with_delay(
            generate_recipe_image_job, [recipe_id], delay_seconds, "recipe_image"
        )

    @staticmethod
    def schedule_wine_pairing_generation(recipe_id, delay_seconds=2):
        """Schedule wine pairing generation job"""
        return JobSchedulerService.schedule_job_with_delay(
            generate_wine_pairing_job, [recipe_id], delay_seconds, "wine_pairing"
        )

    @staticmethod
    def schedule_starch_image_generation(starch_prep_id, delay_seconds=10):
        """Schedule starch image generation job with delay for steps to be saved"""
        starch_perp = models.Starch_Preparation.objects.get(id=starch_prep_id)
        if starch_perp.image_url:
            logger.info(
                f"Starch preparation {starch_prep_id} already has image, skipping generation"
            )
            return None
        logger.info(
            f"Scheduling starch image generation for {starch_prep_id} after {delay_seconds}s delay"
        ) 
        return JobSchedulerService.schedule_job_with_delay(
            generate_starch_image_job, [starch_prep_id], delay_seconds, "starch_image"
        )


# Alternative: Simple threading approach (fallback if APScheduler has issues)
class ThreadingJobService:
    """Fallback service using threading for background jobs"""

    @staticmethod
    def run_delayed_job(func, args, delay_seconds=1):
        """Run a job in a separate thread after a delay"""

        def delayed_execution():
            try:
                time.sleep(delay_seconds)
                func(*args)
            except Exception as e:
                logger.error(f"Error in threaded job: {str(e)}")

        thread = threading.Thread(target=delayed_execution, daemon=True)
        thread.start()
        logger.info(
            f"Started background thread for {func.__name__} with {delay_seconds}s delay"
        )


# Signal receivers - Now lightweight and fast
@receiver(post_save, sender=models.Recipe)
def handle_recipe_post_save(sender, instance, created, **kwargs):
    """
    Handle recipe post-save operations - schedule background jobs
    """
    try:
        # Try APScheduler first, fallback to threading
        try:
            JobSchedulerService.schedule_recipe_image_generation(
                instance.id, delay_seconds=1
            )
            JobSchedulerService.schedule_wine_pairing_generation(
                instance.id, delay_seconds=2
            )
            logger.info(f"Scheduled APScheduler jobs for recipe {instance.id}")
        except Exception as e:
            logger.warning(f"APScheduler failed, using threading fallback: {str(e)}")
            # Fallback to threading
            ThreadingJobService.run_delayed_job(
                generate_recipe_image_job, [instance.id], 1
            )
            ThreadingJobService.run_delayed_job(
                generate_wine_pairing_job, [instance.id], 2
            )
            logger.info(f"Scheduled threading jobs for recipe {instance.id}")

    except Exception as e:
        logger.error(f"Error scheduling jobs for recipe {instance.id}: {str(e)}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log user login information - this is fast so keep synchronous
    """
    try:
        ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")

        models.LoginLog.objects.create(
            user=user, ip_address=ip_address, user_agent=user_agent
        )
        logger.info(f"Login logged for user {user.id}")

    except Exception as e:
        logger.error(f"Error logging user login for user {user.id}: {str(e)}")


@receiver(post_save, sender=models.Starch_Preparation)
def handle_starch_preparation_post_save(sender, instance, created, **kwargs):
    """
    Handle starch preparation post-save operations - schedule background job
    """
    try:
        # Try APScheduler first, fallback to threading
        try:
            if not instance.image_url:
                JobSchedulerService.schedule_starch_image_generation(
                    instance.id, delay_seconds=10
                )
                logger.info(
                    f"Scheduled APScheduler job for starch preparation {instance.id}"
                )
            else:
                logger.info(
                    f"Starch preparation {instance.id} already has image, skipping generation"
                )
                return
            
        except Exception as e:
            logger.warning(f"APScheduler failed, using threading fallback: {str(e)}")
            # # Fallback to threading
            # ThreadingJobService.run_delayed_job(
            #     generate_starch_image_job, [instance.id], 10
            # )
            # logger.info(f"Scheduled threading job for starch preparation {instance.id}")

    except Exception as e:
        logger.error(
            f"Error scheduling job for starch preparation {instance.id}: {str(e)}"
        )


# Graceful shutdown
import atexit


def shutdown_scheduler():
    """Shutdown scheduler gracefully"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")


atexit.register(shutdown_scheduler)
