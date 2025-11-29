from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate
import os
import time
import base64
# from project import settings
from dotenv import load_dotenv
load_dotenv()

class Image:

    def image(self, dish_name, ingredients, max_retries=5, wait_seconds=5):

        last_exception = None

        for attempt in range(max_retries):
            try: 

                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                prompt_template = ChatPromptTemplate.from_template(
                """Generate a high-quality, realistic image of the dish called '{dish}' made with the following ingredients: {ingredients}.
                Show the ENTIRE plate fully visible from edge to edge — absolutely no cropping or zooming.
                Use a TOP-DOWN camera angle (flat lay) to ensure the full plate fits inside the frame. 
                Leave some space around the plate so its edges are fully visible.
                If the dish is liquid-based (milkshake, soup, curry, chicken shorba), clearly show natural liquid texture without extra water.
                If the dish is not liquid-based, do not add liquid.
                Use restaurant-style presentation with clean lighting and a simple background."""
                )

                final_prompt = prompt_template.format(
                    dish=dish_name,
                    ingredients=", ".join(ingredients)
                )

                response = client.responses.create(
                    model="gpt-4.1",  
                    input=final_prompt,
                    tools=[{
                        "type": "image_generation",
                        "size": "1024x1024"
                    }],
                )

                for output in response.output:
                    if output.type == "image_generation_call":
                        img_b64 = output.result
                        # open("output2.png", "wb").write(base64.b64decode(img_b64))
                        # print("Output saved: output2.png")
                        return output.result

            except Exception as e:
                last_exception = e
                print(f"Error: {str(e)}")
                time.sleep(wait_seconds)  
       
        print("Error: ", str(last_exception))
        return {
            "status": False,
            "message": "Image generation failed after all attempts.",
            "error": str(last_exception)
        }

# dish_name = "Aloo Shorba"
# ingredients = ["potatoes", "onions", "tomatoes", "ginger", "garlic", "green chilies", "spices", "fresh coriander", "water", "oil"]



# image=Image()
# output = image.image(dish_name=dish_name, ingredients=ingredients)