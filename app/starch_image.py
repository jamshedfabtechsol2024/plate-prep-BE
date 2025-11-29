from openai import OpenAI
import os
import time
import base64
from dotenv import load_dotenv
load_dotenv()

class StarchImage:

    def image(self, dish_name, steps, max_retries=5, wait_seconds=5):

        last_exception = None

        for attempt in range(max_retries):
            try: 

                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                prompt = f"""
                Generate a high-quality, realistic food image of the dish called '{dish}'.
                Show the ENTIRE plate fully visible from edge to edge — absolutely no cropping or zooming.
                Use a TOP-DOWN camera angle (flat lay) so the full plate fits naturally inside the frame.
                Leave some clean space around the plate so all edges are clearly visible.

                The dish is prepared using the following steps:
                {steps}

                The final image should clearly show the prepared starch ingredient exactly as described in the steps.
                Do not add any extra items or decorations that are not part of the preparation.
                Ensure the food looks appetizing, natural, and suitable for a recipe illustration.
                """

                response = client.responses.create(
                    model="gpt-4.1",  
                    input=prompt,
                    tools=[{"type": "image_generation"}],
                )

                for output in response.output:
                    if output.type == "image_generation_call":
                        # img_b64 = output.result
                        # open("output.png", "wb").write(base64.b64decode(img_b64))
                        # print("Output saved: output.png")
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


# dish_name = "Toasted Sourdough Bread"
# steps = "Slice a loaf of sourdough bread into 1-inch thick slices. Preheat a skillet or griddle over medium heat. Brush both sides of each slice lightly with olive oil or softened butter. Place slices on the skillet and toast for 2–3 minutes per side, until golden brown and crisp. Remove from heat and sprinkle lightly with sea salt, if desired. Serve warm alongside the soup, perfect for dipping."

# image=Image()
# output = image.image(dish_name=dish_name, steps=steps)