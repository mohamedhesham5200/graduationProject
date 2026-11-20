from flask import Flask, request, jsonify
# import gradio as gr
import os
from model import generate_roadmap, initialize_data
import logging
import json
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize data on startup
logger.info("Initializing application data")
initialize_data()

@app.route('/')
def home():
    logger.info("Received request to home endpoint")
    return "Welcome to ToniBot Learning Roadmap Generator! Use /generate to create a roadmap."

@app.route('/generate', methods=['POST'])
def generate():
    logger.info("Received POST request to /generate")
    data = request.get_json()
    logger.debug(f"Request data: {data}")
    
    user_interests = data.get('interests', 'math')
    user_level = data.get('level', 'intermediate')
    category = data.get('category', user_interests)
    num_stages = int(data.get('num_stages', 5))

    if not 3 <= num_stages <= 7:
        logger.error(f"Invalid num_stages: {num_stages}, must be between 3 and 7")
        return jsonify({
            "success": False,
            "error": "Number of stages must be between 3 and 7",
            "data": None
        }), 400

    roadmap = generate_roadmap(user_interests, user_level, category, num_stages)
    # Log the response safely using json.dumps to handle the dictionary
    logger.info(f"Generated roadmap response: {json.dumps(roadmap)[:200]}...")  # Log first 200 chars
    return jsonify(roadmap)


# def gradio_interface(interests, level, category, num_stages):
#     logger.info(f"Gradio interface called with interests: {interests}, level: {level}, category: {category}, num_stages: {num_stages}")
#     num_stages = int(num_stages)
#     if not 3 <= num_stages <= 7:
#         logger.error(f"Invalid num_stages in Gradio: {num_stages}")
#         return "Error: Number of stages must be between 3 and 7"
    
#     roadmap = generate_roadmap(interests, level, category, num_stages)
    
#     # Format the roadmap data for display
#     if roadmap["success"]:
#         stages = roadmap["data"]["roadmap"]["stages"]
#         formatted_output = ""
#         for stage in stages:
#             formatted_output += f"Stage {stage['stage_number']}:\n"
#             formatted_output += f"Id: {stage['Id']}\n" 
#             formatted_output += f"Title: {stage['title']}\n"
#             formatted_output += f"Description: {stage['description']}\n"
#             formatted_output += f"Level: {stage['level']}\n"
#             formatted_output += f"URL: {stage['url']}\n"
#             if 'explanation' in stage:
#                 formatted_output += f"Explanation: {stage['explanation']}\n"
#             formatted_output += "\n"
#         return formatted_output
#     else:
#         return f"Error: {roadmap['error']}"



# with gr.Blocks() as demo:
#     gr.Markdown("### ToniBot Learning Roadmap Generator")
#     interests = gr.Textbox(label="What do you want to learn? (e.g., design)")
#     level = gr.Dropdown(["beginner", "intermediate", "advanced"], label="Your current level")
#     category = gr.Textbox(label="Category (e.g., design)")
#     num_stages = gr.Slider(3, 7, value=5, step=1, label="Number of stages")
#     output = gr.Textbox(label="Generated Roadmap")
#     gr.Button("Generate Roadmap").click(
#         fn=gradio_interface,
#         inputs=[interests, level, category, num_stages],
#         outputs=output
#     )


# if __name__ == '__main__':
#     port = int(os.environ.get('PORT', 7860))
#     logger.info(f"Starting Gradio server on port {port}")
#     demo.launch(server_name="0.0.0.0", server_port=port)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)