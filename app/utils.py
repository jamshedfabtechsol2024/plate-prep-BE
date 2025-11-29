from apscheduler.schedulers.background import BackgroundScheduler
from django.core.signals import request_finished
import os, json, threading, logging, requests, time
from typing import List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.prompts.prompts import wine_paring, menu_generation, video_script_prompt, translate_prompt
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from rest_framework.response import Response
from project import settings
from dateutil.parser import isoparse
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
from ast import literal_eval

scheduler = BackgroundScheduler()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CulinaryConfig:
    """Configuration settings for the Culinary AI Assistant."""
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2000
    
class CulinaryAIException(Exception):
    """Custom exception for Culinary AI-related errors."""
    pass

class CulinaryAI:
    def __init__(self, config: Optional[CulinaryConfig] = None):
      
        self.config = config or CulinaryConfig()
        self._initialize_environment()
        self._setup_llm()
        self._setup_prompts()
        
    def _initialize_environment(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise CulinaryAIException("OpenAI API key not found in environment variables")
            
    def _setup_llm(self) -> None:
        try:
            self.llm = ChatOpenAI(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                openai_api_key=self.api_key
            )
        except Exception as e:
            logger.error(f"Error setting up LLM: {str(e)}")
            raise CulinaryAIException(f"Failed to initialize LLM: {str(e)}")
            
    def _setup_prompts(self) -> None:
        """Set up prompt templates."""
        self.wine_pairing_prompt = ChatPromptTemplate.from_template(wine_paring)
        self.menu_generation_prompt = ChatPromptTemplate.from_template(menu_generation)
        self.video_script_prompt = ChatPromptTemplate.from_template(video_script_prompt)
        
    def get_wine_pairing(self, dish: str) -> str:
        try:
            logger.info(f"Generating wine pairing for dish: {dish}")
            chain = self.wine_pairing_prompt | self.llm | StrOutputParser()
            return chain.invoke({"dish": dish})
        except Exception as e:
            logger.error(f"Error generating wine pairing: {str(e)}")
            raise CulinaryAIException(f"Failed to generate wine pairing: {str(e)}")
            
    def generate_menu(
        self,
        available_ingredients: List[str],
        cuisine_style: str,
        target_audience: str,
        price_range: float,
        dietary_preferences: Optional[str] = "",
        theme: Optional[str] = "festival",
        dietary_restrictions: Optional[str] = None,
        menu_class: Optional[str] = None,
    ) -> str:
        try:
            logger.info(f"Generating menu for {cuisine_style} cuisine with {dietary_preferences} preferences")
            logger.info(f"Available ingredients: {dietary_restrictions}")
            chain = self.menu_generation_prompt | self.llm | StrOutputParser()
            return chain.invoke({
                "available_ingredients": available_ingredients,
                "cuisine_style": cuisine_style,
                "dietary_preferences": dietary_preferences,
                "theme": theme,
                "target_audience": target_audience,
                "price_range": price_range,
                "dietary_restrictions": dietary_restrictions,
                "menu_class": menu_class
            })
        except Exception as e:
            logger.error(f"Error generating menu: {str(e)}")
            raise CulinaryAIException(f"Failed to generate menu: {str(e)}")

    def generate_video_script(self, previous_menu, language: str):
        try:
            prompt = translate_prompt.format(menu=previous_menu, language=language)
            menu = self.llm.invoke(prompt)
            # logger.info(f"Generating video script for menu: {menu}")
            # chain = self.video_script_prompt | self.llm | StrOutputParser()
            # print(chain.invoke({"menu": menu}), "chain")
            return menu.content
        except Exception as e:
            logger.error(f"Error generating video script: {str(e)}")
            raise CulinaryAIException(f"Failed to generate video script: {str(e)}")     

def start_scheduler():
    if not scheduler.running:
        scheduler.start()

_user = threading.local()
def set_current_user(user):
    _user.value = user

def get_current_user():
    return getattr(_user, 'value', None)

def clear_current_user(sender, **kwargs):
    _user.value = None
request_finished.connect(clear_current_user)

def store_wine_pairings(json_data, recipe_id=None):
    from app import models

    try:
        if isinstance(json_data, str):
            wine_pairings = json.loads(json_data)
        else:
            wine_pairings = json_data
        
        recipe = get_object_or_404(models.Recipe, id=recipe_id)
        new_wine_ids = []
        for pairing in wine_pairings:
            wine, created = models.Wine.objects.get_or_create(
                wine_name=pairing.get('wine_name'),
                wine_type=pairing.get('wine_type'),
                defaults={
                    'flavor': pairing.get('flavor', ''),
                    'profile': pairing.get('profile', ''),
                    'proteins':pairing.get('proteins', ''),
                    'reason_for_pairing': pairing.get('reason_for_pairing', ''),
                    'region_name': pairing.get('region_name', ''),

                },
            )

            new_wine_ids.append(wine.id)
        if new_wine_ids:
            recipe.wine_pairing.clear()

        wines_to_add = models.Wine.objects.filter(
            wine_name__in=[p.get('wine_name') for p in wine_pairings],
            wine_type__in=[p.get('wine_type') for p in wine_pairings]
        )
        recipe.wine_pairing.add(*wines_to_add)

        return True
    except Exception as e:
        logger.error(f"Error in store_wine_pairings: {str(e)}")
        return False

def image_url_to_context(image_url):
    image_response = requests.get(image_url)
    image_name = image_url.split("/")[-1]
    if image_response.status_code == 200:
        return ContentFile(image_response.content, name=image_name)

culinaryAi = CulinaryAI()
    
def fetch_and_get_wine_pairing(dish_description, recipe_id):
    try:
        if not dish_description:
            return Response({"error": "Dish description is required."}, status=400)

        wine_pairing = culinaryAi.get_wine_pairing(dish_description)
        res = store_wine_pairings(wine_pairing, recipe_id)
        if not res:
            return Response({"error": "An error occurred while saving the wine pairing data."}, status=400)

        return Response({"wine_pairing": wine_pairing}, status=200)

    except Exception as e:
        logger.error(f"Error in wine pairing recommendation: {str(e)}")
        return Response({"error": f"An error occurred while processing the wine pairing: {str(e)}"}, status=400)

def generate_video_and_save(recipe_id, recipe_name, introduction, steps, ingredient, last_words, template_id, title, language, welcome, to, plateprep, training_phrase, ingridiants_start=None):
    synthesia_url = settings.SYNTHESIA_URL
    from app import models

    try:
        payload = {
            "templateData": {
                "dish_name": recipe_name,
                "introduction": introduction,
                # "name": name_chef,
                "list": ingredient,
                "steps": steps,
                "end_with_thanks":last_words,
                "welcome": welcome,
                "to": to,
                "plateprep": plateprep,
                "training_phrase": training_phrase,
                "ingridiants_start": ingridiants_start,
                "description": "A flavorful and aromatic dish consisting of grilled chicken coated in fresh herbs, served with creamy garlic mashed potatoes, making every bite irresistible.",
            },
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": settings.SYNTHESIA_KEY
        }
        translated = culinaryAi.generate_video_script(
            previous_menu=payload.get('templateData'),
            language=language
        )
        translated_template_data = literal_eval(translated)

        # Now rebuild the full payload using translated templateData but rest same
        translated_payload = {
            "test": False,
            "templateData": translated_template_data,
            "visibility": "private",
            "templateId": template_id,
            "title": title,
        }
        video_create = requests.post(synthesia_url, json=translated_payload, headers=headers)
        print("video_create", video_create.json())
        video_id = json.loads(video_create.text).get('id')
        url = f"https://api.synthesia.io/v2/videos/{video_id}"

        download_url = download_synthesia_video(
        video_id=video_id,
        api_key=settings.SYNTHESIA_KEY,
        max_attempts=100)

        if download_url:
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            filename = download_url.split("filename%3D%22")[-1].split("%22")[0] if "filename%3D%22" in url else "video.mp4"
            video_content = ContentFile(response.content, name=filename)

        recipe_instance = models.Recipe.objects.get(id=recipe_id)
        if recipe_instance.video:
            recipe_instance.video.delete(save=False)
        recipe_instance.video_id = video_id
        recipe_instance.video.save(filename, video_content, save=False)
        recipe_instance.save()
        return Response({"video_id": video_id}, status=200)
    
    except Exception as e:
        logger.error(f"Error in generating video: {str(e)}")
        return Response({"error": f"An error occurred while generating the video: {str(e)}"}, status=400)


def delete_video_from_synthesia(video_id):
    url = f"https://api.synthesia.io/v2/videos/{video_id}"

    headers = {
        "accept": "application/json",
        "Authorization": settings.SYNTHESIA_KEY
    }
    response = requests.delete(url, headers=headers)
    return response

def format_datetime(date_string):
    try:
        dt = isoparse(date_string) 
        formatted_datetime = dt.strftime('%b %d, %Y, %I:%M %p') 
        return formatted_datetime

    except ValueError:
        return "Invalid datetime string"

def download_synthesia_video(video_id: str, api_key: str, max_attempts: int = 100) -> Optional[str]:
    url = f"https://api.synthesia.io/v2/videos/{video_id}"
    headers = {
        "accept": "application/json",
        "Authorization": api_key
    }

    attempts = 0
    while attempts < max_attempts:
        try:
            download_video_link = requests.get(url, headers=headers)
            download_video_link.raise_for_status() 
            
            response_data = json.loads(download_video_link.text)
            video_status = response_data.get('status')
            
            print(f"Current video status: {video_status}")
            if video_status == "complete":
                download_url = response_data.get("download")
                if download_url:
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    return download_url
                else:
                    raise ValueError("Download URL not found in response")
            
            elif video_status == 'failed':
                raise ValueError(f"Video processing failed: {response_data.get('message', 'Unknown error')}")
            
            else:
                print(f"Video not ready yet. Attempt {attempts + 1}/{max_attempts}. Waiting 10 seconds...")
                time.sleep(10)
                attempts += 1
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            time.sleep(10)
            attempts += 1
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse response: {e}")
            time.sleep(10)
            attempts += 1

    raise TimeoutError(f"Video not ready after {max_attempts} attempts")

class S3FileUtility:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    def generate_presigned_url(self, key, operation="put_object", expiration=3600):
        """Generate presigned URL for upload/download"""
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod=operation,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            return None

    def check_file_exists(self, key):
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    def delete_file(self, key):
        """Delete file from S3"""
        try:
            res = self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return res
        except ClientError:
            return False

    @staticmethod
    def get_profile_picture(self, email):
        try:
            key = f"profile_pictures/{email}.jpg"
            image_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
            
            return image_url
        except ClientError:
            return False


# Get OpenAI API key from environment variables
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("OPENAI_API_KEY is not set in the environment variables.")
    exit(1)

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

def spell_checker(input_text):
    prompt = (
        f"""
        Please check the following text for any spelling mistakes. If any mistakes are found, correct them.If any spelling mistakes are present, correct only those mistakes and return the corrected text. If there are no spelling mistakes, return the text unchanged. only  return the word not like this 'The corrected text is:' just return the corrected word.

        example: 
        input: data  # this input of user but spell is correct so return same word
        return: data

        input {input_text}
        """
    )
    try:
        logger.info("Sending request to OpenAI API for spell checking.")
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a spelling correction tool."},
                {"role": "user", "content": f"{prompt}"}
            ],
            temperature=0  
        )
        
        corrected_text = completion.choices[0].message.content.strip()
        logger.info("Received response from OpenAI API.")
        return corrected_text
    except Exception as e:
        logger.error(f"Error in spell checking: {e}")
        return "An error occurred while checking spelling."
