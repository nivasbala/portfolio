from langchain.prompts import ChatPromptTemplate
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import llm, workflow, task, agent, tool, retrieval

from logger import logger # TODO change this later

classification_instruction = """
You are a helpful Datadog assistant trained to classify customer queries into different categories.
The categories include:
- Product: Questions related to purchasing products.
- Product Pricing: Questions about the cost of products prices.
- Licenses: Questions about licenses
- Comparison: Questions about comparing licenses
Your task is to classify the following customer query into one of these categories.
If you are not able to classify the into the above categories, classify as Unknown.
"""
# Classify the Question
@task(name="categorize_user_question")
def classify_question(model, query):

    logger.info(f"Classify Question: {query}")
    classify_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", classification_instruction),
            ("human", "{query}")
        ]
    )

    # Use classify_prompt and query to create a formatted output
    formatted_prompt = classify_prompt.format_prompt(query=query).to_string()
    #print(formatted_prompt)

    output = model.invoke([{"role": "user", "content": formatted_prompt}])
    #print("Model output Type: ")
    #print(type(output))

    classify_string = output.content

    #LLMObs.annotate(output_data=str(classify_output.strip()))

    LLMObs.annotate(input_data=query, output_data=classify_string)
    logger.info(f"Question {query} - Classified as: {classify_string}")

    return classify_string