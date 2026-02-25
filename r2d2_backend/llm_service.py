from typing import Any, Dict

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import OpenAI


competitors_template = PromptTemplate(
    input_variables=["company"],
    template="Provide a list of competitors for {company}.",
)

products_template = PromptTemplate(
    input_variables=["company"],
    template="Generate a detailed comparative analysis for {company} and its products.",
)

personalize_template = PromptTemplate(
    input_variables=["email"],
    template="Rewrite this email to maximize positive response and deal progression: {email}",
)

welcome_template = PromptTemplate(
    input_variables=["customerName", "productName"],
    template="Create a customer welcome message for {customerName} introducing {productName}.",
)

followup_template = PromptTemplate(
    input_variables=["prospectName", "followUpReason", "note"],
    template=(
        "Create a sales follow-up for {prospectName} about {followUpReason}. "
        "Personalize it with this note: {note}"
    ),
)

caption_template = PromptTemplate(
    input_variables=["postContent", "postTone"],
    template="Write a social media caption for {postContent} with a {postTone} tone.",
)

create_post_template = PromptTemplate(
    input_variables=["platform", "postObjective", "postContent"],
    template=(
        "Create a social media post for {platform}. Objective: {postObjective}. "
        "Content context: {postContent}"
    ),
)

sales_call_pipeline_template = PromptTemplate(
    input_variables=["transcriptNotes"],
    template=(
        "You are a B2B sales assistant.\n"
        "Analyze the transcript notes and return exactly these sections.\n\n"
        "SUMMARY:\n"
        "<2-4 sentence summary>\n\n"
        "OBJECTIONS:\n"
        "- <objection>\n"
        "- <objection>\n\n"
        "NEXT_ACTIONS:\n"
        "- <action>\n"
        "- <action>\n\n"
        "FOLLOW_UP_EMAIL_1:\n"
        "<email variant 1>\n\n"
        "FOLLOW_UP_EMAIL_2:\n"
        "<email variant 2>\n\n"
        "FOLLOW_UP_EMAIL_3:\n"
        "<email variant 3>\n\n"
        "Keep the writing concise and practical.\n\n"
        "Transcript notes:\n{transcriptNotes}"
    ),
)


def extract_text(result: Any) -> str:
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        for key in ("text", "output_text", "result"):
            value = result.get(key)
            if isinstance(value, str):
                return value.strip()
    return str(result).strip()


def run_chain(prompt_template: PromptTemplate, inputs: Dict[str, str], openai_api_key: str) -> str:
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    llm = OpenAI(temperature=0.7, openai_api_key=openai_api_key)
    chain = LLMChain(llm=llm, prompt=prompt_template)
    result = chain.invoke(inputs)
    return extract_text(result)
