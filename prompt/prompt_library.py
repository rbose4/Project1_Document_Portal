# Prepare prompt templates for the project
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


# prompt template for document analysis
document_analysis_prompt = ChatPromptTemplate.from_template("""
You are a highly capable assistant trained to analyze and summarize documents.
Return ONLY valid JSON matching the exact schema below.

{format_instructions}

Analyze this document:
{document_text}
""")

# Prompt for document comparison 
document_comparison_prompt = ChatPromptTemplate.from_template("""
You will be provided with two documents.Your tasks are as follows:
1. Compare the contents of the two documents.
2. Indentify the differences in PDF and note down the page number
3. The output you provide must be page wise comparison content
4. If any page does not have any changes, you must mention "No Changes" for that page.
Input documents:

{combined_documents}
                                    
Your response should follow this format:
{format_instructions}
""")

# Prompt for contextual question rewriting
contextualize_question_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "Given a conversation history and the most recent user query, rewrite the query as a standalone question "
        "that makes sense without relying on the previous context. Do not provide an answer—only reformulate the "
        "question if necessary; otherwise, return it unchanged."
    )),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

# central registry for all prompts
PROMPT_LIBRARY = {
    "document_analysis": document_analysis_prompt,
    "document_comparison": document_comparison_prompt,
    "contextualize_question": contextualize_question_prompt,
}
    