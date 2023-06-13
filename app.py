from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SimpleSequentialChain
from flask import Flask, jsonify, request, make_response
from flask_debugtoolbar import DebugToolbarExtension
import os
import openai
from flask_cors import CORS
import logging
from dotenv import load_dotenv
import os

# Load the environment variables from the .env file
load_dotenv()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

app = Flask(__name__)
logger = logging.getLogger(__name__)
CORS(app)
debug = DebugToolbarExtension(app)


# LLM Templates

competitors_template = PromptTemplate(
    input_variables=["company"],
    template="provide me a list of companies that are competitors of {company}",
)

products_template = PromptTemplate(
    input_variables=["company"],
    template="generate a detailed comparative analysis report on {company} products",
)


personalize_template = PromptTemplate(
    input_variables=["email"],
    template="rewrite this for in a way to maximize response or closing deals: {email}",
)

welcome_template = PromptTemplate(
    input_variables=["customerName", "productName"],
    template="Create a Customer Service Welcome Message for {customerName} to introduce {productName}",
)

followup_template = PromptTemplate(
    input_variables=["prospectName", "followUpReason", "note"],
    template="Create a sales follow up for {prospectName} with the folowing reasons {followUpReason} and persoanlize with:{note}",
)

caption_template = PromptTemplate(
    input_variables=["postContent", "postTone"],
    template="Write a social media caption for {postContent} with an {postTone} tone",
)

create_post_template = PromptTemplate(
    input_variables=["platform", "postObjective", "postContent"],
    template="Create a social media post for {platform} with {postObjective} and {postContent}",
)


# Market Research
@app.route("/api/market-research", methods=["POST"])
def market_research():
    user_prompt = request.json["prompt"]
    llm = OpenAI(temperature=0.9)
    companies_chain = LLMChain(llm=llm, prompt=competitors_template)
    details_chain = LLMChain(llm=llm, prompt=products_template)
    api_respond_companies = companies_chain.run(user_prompt)
    api_respond_details = details_chain.run(api_respond_companies)
    
    # WE COULD ALSO CHAIN BOTH OF CHAINS
    # sequential_chain = SimpleSequentialChain(chains=[companies_chain, details_chain])
    # response = sequential_chain.run(user_prompt)

    return jsonify(
        {
            "id": user_prompt,
            "competitors": api_respond_companies.strip(),
            "analyze": api_respond_details.strip(),
        }
    )


# Personalize Mail Route
@app.route("/api/personalize-email", methods=["POST"])
def personalize_email():
    user_prompt = request.json["prompt"]
    llm = OpenAI(temperature=0.9)
    personalize_chain = LLMChain(llm=llm, prompt=personalize_template)
    api_respond = personalize_chain.run(user_prompt)
    return jsonify({"data": api_respond})


# CRM Route
@app.route("/api/crm", methods=["POST"])
def CRM_api():
    req = request.get_json()

    if not req:
        return make_response("Bad request", 400)

    if "customerName" in req and "productName" in req:
        return welcome_customer_request(req)
    elif "prospectName" in req and "followUpReason" in req and "note" in req:
        return followup_request(req)
    else:
        return make_response("Bad request", 400)


def welcome_customer_request(req):
    customer_name = req["customerName"]
    product_name = req["productName"]

    try:
        llm = OpenAI(temperature=0.9)
        CRM_chain = LLMChain(llm=llm, prompt=welcome_template)
        api_respond = CRM_chain.run(
            {"customerName": customer_name, "productName": product_name}
        )
        logger.info(api_respond)
        return jsonify({"data": api_respond.strip()})
    except Exception as e:
        logger.error(
            f"Error occurred while processing the customer product request: {str(e)}"
        )
        return make_response("Internal Server Error", 500)


def followup_request(req):
    prospect_name = req["prospectName"]
    follow_reason = req["followUpReason"]
    note = req["note"]
    try:
        llm = OpenAI(temperature=0.9)
        CRM_chain = LLMChain(llm=llm, prompt=followup_template)
        api_respond = CRM_chain.run(
            {
                "prospectName": prospect_name,
                "followUpReason": follow_reason,
                "note": note,
            }
        )
        logger.info(api_respond.strip())
        print(api_respond)
        return jsonify({"data": api_respond.strip()})
    except Exception as e:
        logger.error(
            f"Error occurred while processing the customer product request: {str(e)}"
        )
        return make_response("Internal Server Error", 500)


# Marketing Route
@app.route("/api/marketing", methods=["POST"])
def marketing_api():
    req = request.get_json()

    if not req:
        return make_response("Bad request", 400)

    if "postContent" in req and "postTone" in req:
        return caption_create(req)
    elif "platform" in req and "postObjective" in req and "postContent" in req:
        return create_post(req)
    else:
        return make_response("Bad request", 400)


def caption_create(req):
    post_content = req["postContent"]
    post_tone = req["postTone"]

    try:
        llm = OpenAI(temperature=0.9)
        marketing_chain = LLMChain(llm=llm, prompt=caption_template)
        api_respond = marketing_chain.run(
            {"postContent": post_content, "postTone": post_tone}
        )
        logger.info(api_respond)
        print(api_respond)
        return jsonify({"data": api_respond.strip()})
    except Exception as e:
        logger.error(
            f"Error occurred while processing the customer product request: {str(e)}"
        )
        return make_response("Internal Server Error", 500)


def create_post(req):
    platform = req["platform"]
    post_objective = req["postObjective"]
    post_contet = req["postContent"]
    try:
        llm = OpenAI(temperature=0.9)
        marketing_chain = LLMChain(llm=llm, prompt=create_post_template)
        api_respond = marketing_chain.run(
            {
                "platform": platform,
                "postObjective": post_objective,
                "postContent": post_contet,
            }
        )
        logger.info(api_respond.strip())
        print(api_respond)
        return jsonify({"data": api_respond.strip()})
    except Exception as e:
        logger.error(
            f"Error occurred while processing the customer product request: {str(e)}"
        )
        return make_response("Internal Server Error", 500)
