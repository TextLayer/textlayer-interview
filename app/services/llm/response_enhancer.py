from app.services.llm.session import LLMSession
from flask import current_app as app
from app import logger

class ResponseEnhancer:
    def make_response_better(self,question,sql,results,schema):
        llm_session = LLMSession(
            chat_model = app.config.get("CHAT_MODEL"),
            embedding_model = app.config.get("EMBEDDING_MODEL"))
        prompt = self._build_enhancement_prompt(question,sql,results,schema)

        try:
            response = llm_session.chat(messages=prompt)
            better_response = response.choices[0].message.content

            logger.info(f"fixed response")
            return better_response
        
        except Exception as e:
            logger.error(f"Error in response enhancer: {e}")
            return f"Here is the response: \n\n{response}"
    
    def _build_enhancement_prompt(self,question,sql,results,schema):
         return [
            {"role": "system", "content": f"""You're helping someone understand their business data. They asked a question, got some SQL results, and now need to actually understand what it means.

What they asked: "{question}"
The SQL that ran: {sql}
What came back: {results[:2000]}

This is financial data - accounts, customers, products, time periods, that kind of stuff.

Your job is to:
1.Explain what they're looking at in plain English
2.Point out anything interesting in the data
3.Suggest what they might want to look at next
4.Keep the original table but add context around it

Write it like you're explaining to a colleague, not writing a formal report. Be helpful and conversational.

Use this EXACT format with delimiters:

[EXPLANATION_START]
Quick summary of what you found...
[EXPLANATION_END]

[TABLE_START]
{results}
[TABLE_END]

[INSIGHTS_START]
1.Key insight 1
2. Key insight 2  
3. Key insight 3
[INSIGHTS_END]

[NEXT_STEPS_START]
1.Question they might want to ask next
2. Another suggestion
[NEXT_STEPS_END]

Don't use emojis or icons. Keep it professional."""},
            
            {"role": "user", "content": f"Help me understand these results for: '{question}'"}
        ]
    def figure_out_next_steps(self,question,sql):
        question = question.lower()

        if 'hierarchy' in question or 'join' in sql and 'parentid' in sql:
            return "looking_at_hierarchy"
        elif 'region' in question or 'customer' in sql:
            return "regional_stuff"  
        elif any(word in question for word in ['time', 'quarter', 'year', 'month']):
            return "time_analysis"
        elif 'revenue' in question or 'account' in question:
            return "account_stuff"
        else:
            return "general_question"