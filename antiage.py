import pandas as pd
import requests
import re
from transformers import AutoTokenizer, AutoModel,PegasusForConditionalGeneration,PegasusTokenizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import torch
import openai
from langchain.llms import Replicate
from dotenv import load_dotenv, find_dotenv
from langchain import OpenAI, LLMChain, PromptTemplate 
load_dotenv(find_dotenv())


### Summarize 
tokenizer = AutoTokenizer.from_pretrained('allenai/specter2_base')
model = AutoModel.from_pretrained('allenai/specter2_base')

torch_device = "cuda" if torch.cuda.is_available() else "cpu"
torch_device = "cpu"
tokenizer_summarizer = PegasusTokenizer.from_pretrained("tuner007/pegasus_summarizer")
model_summarizer = PegasusForConditionalGeneration.from_pretrained("tuner007/pegasus_summarizer").to(torch_device)

stopwords = ["isn't", 'he', 'having', 'before', 'please', 'mightn', 'when', 'yours', 'it', 'after', 'your', 'y', 'both', 'have', 'on', 
         'where', "shouldn't", 'won', 'did', 'few', "doesn't", 'yourself', "it's", "you've", 'up', "mustn't", 'against', 's', 'o', 'at', 
         'll', 'we', 'through', 're', 'ma', "hasn't", 'had', 'here', 'wasn', 've', 'can', "she's", 'herself', "don't", 'its', 'should', 
         'that', 'other', 'shouldn', 'was', 'these', 'only', 'being', 'off', 'itself', 'haven', 'myself', 'needn', 'than', 'down', 'then',
         'who', 'will', 'theirs', "needn't", 'same', 'now', 'm', 'shan', 'review', 'into', 'such', 'does', 'any', 'ain', 'ourselves', "hadn't", 
         'some', 'how', 'this', 'their', 'and', 'more', 'didn', "should've", 'nor', 'has', 'they', 'from', 'just', 'most', "weren't", 'is', 
         'yourselves', 'under', 'his', 'a', 'once', 'all', 'isn', 'don', 'of', 'those', "shan't", 'are', 'to', 'again', 't', 'been', 'do', 'or', 
         'below', 'whom', "couldn't", 'too', "that'll", 'am', 'if', 'hasn', 'my', 'i', 'hers', 'own', 'aren', 'above', 'with', "you'll", 'further', 
         'hadn', 'doing', 'them', "wouldn't", 'in', "wasn't", 'by', "mightn't", 'd', 'not', 'while', 'our', 'doesn', 'so', 'wouldn', 'himself', 'as', 
         'there', 'her', 'were', 'for', 'you', 'him', 'during', 'out', 'which', 'what', 'me', 'because', 'why', 'very', 'about', 'couldn', "haven't", 
         'the', 'each', 'over', "you'd", "aren't", 'but', "you're", 'between', 'until', 'ours', 'mustn', 'themselves', 'be', 'an', 'no', "didn't", 'weren', 'she', "won't"]



class Antiage:
    def __init__(self):
        self.papers_df = pd.DataFrame()

    def preprocess_query(self, query):
        query = query.lower()
        query = " ".join([word for word in query.split() if word not in stopwords])
        return query


    def get_specter_embeddings(self, texts):
        tokens = tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=512)
        embeddings = model(**tokens).pooler_output
        return embeddings.detach().numpy()
        
    def extract_pdf_url(self,openAccessPdf):
        
        openAccessPdf = str(openAccessPdf)
        pattern = r"'url':\s*'([^']+)'"
        url = re.search(pattern, openAccessPdf)
        if url:
            return url.group(1)
        else:
            return ""

    def search(self, query, limit=20, fields = ['paperId', 'url', 'title', 'venue', 'year', 'abstract','openAccessPdf', 'fieldsOfStudy', 'publicationTypes']):
        query = self.preprocess_query(query)
        query = query.replace(" ", "+")
        url = f'https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={limit}&fields={",".join(fields)}'
        headers = {"Accept": "*/*", "x-api-key": os.getenv("S2_KEY")}

        response = requests.get(url, headers=headers, timeout=30)
        return response.json()



    def get_papers_response(self,query, limit=20):
        try:
            self.papers_df = self.get_papers(query)
            self.papers_df['pdf_url'] = self.papers_df.openAccessPdf.apply(self.extract_pdf_url)
            papers = [row.to_dict() for _, row in self.papers_df.iterrows()]
            return papers
        except:
            return None


    def get_papers(self,query, limit=20):
        try:
            search_results = self.search(query, limit)
            if search_results["total"] == 0:
                return None
            else:
                self.papers_df = pd.DataFrame(search_results["data"])
                self.papers_df = pd.DataFrame(search_results["data"])
                self.papers_df = self.papers_df.dropna(subset=["title"])
                self.papers_df = self.papers_df.dropna(subset=["abstract"])
                self.papers_df = self.papers_df.fillna("")                
                return self.papers_df
        except:
            return None

    def rerank(self, query):
        # merge columns title and abstract into a string separated by tokenizer.sep_token and store it in a list
        self.papers_df["title_abs"] = [
            d["title"] + tokenizer.sep_token + (d.get("abstract") or "")
            for d in self.papers_df.to_dict("records")
        ]

        self.papers_df["n_tokens"] = self.papers_df.title_abs.apply(lambda x: len(tokenizer.encode(x)))
        doc_embeddings = self.get_specter_embeddings(list(self.papers_df["title_abs"]))
        query_embeddings = self.get_specter_embeddings(query)
        self.papers_df["specter_embeddings"] = list(doc_embeddings)
        self.papers_df["similarity"] = cosine_similarity(query_embeddings, doc_embeddings).flatten()

        # sort the dataframe by similarity
        self.papers_df.sort_values(by="similarity", ascending=False, inplace=True)
        return self.papers_df


    

    def create_context_chatgpt(self,question,df,k):
        """
        Create a context for a question by finding the most similar context from the dataframe
        """
        returns = []
        count = 1
        # Sort by distance and add the text to the context until the context is too long
        for i, row in df[:k].iterrows():
            
            # Else add it to the text that is being returned
            returns.append(
                "["
                + str(count)
                + "] "
                + row["tldr"]
                + "\nURL: "
                + "https://www.semanticscholar.org/paper/"
                + row["paperId"]
            )
            count += 1
        # Return the context
        return "\n\n".join(returns)

    def generate_prompt(
        self,
        question,
        df,
        k,
        instructions="""Instructions: Using the provided web search results, write a comprehensive reply to the given query. If you find a result relevant definitely make sure to cite the result using [[number](URL)] notation after the reference. End your answer with a summary. A\nQuery:
        if you did not find any of the references useful to answer the question try answering more elaborately with the knowledge you have.
        No need to mention references if you didn't find them useful
        """,
        max_len=3000,
        debug=False,
        
    ):
        """Generates a prompt for the model to answer the question."""
        context = self.create_context_chatgpt(question, df,k=k)
        try:
            prompt = f"""{context} \n\n{instructions} \n"""
            chain_vars = """
                        Chat History:\n\n{chat_history} \n\n
                        User: {user_input} \n\n
                        Answer:
                    """
            prompt += chain_vars

            prompt = PromptTemplate(
                    input_variables=["chat_history","user_input"], template=prompt
                )
            return prompt
        except Exception as e:
            return ""

    def generate_answer(self, prompt):
        """Generates an answer using ChatGPT."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-0613",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant to a researcher. You are helping them write a paper. You are given a prompt and a list of references. You are asked to write a summary of the references if they are related to the question. You should not include any personal opinions or interpretations in your answer, but rather focus on objectively presenting the information from the search results.",
                    },
                    {"role": "user", "content": prompt},
                ],
                api_key=os.getenv('OPENAI_API_KEY')
            )
            return response.choices[0].message.content
        except Exception as e:
            return "Error in generating answer"
        
    

    
    
    def summarize_response(self, input_texts):
        batch = tokenizer_summarizer(input_texts,truncation=True,padding="longest",max_length=1024,return_tensors="pt" ).to(torch_device)
        gen_out = model_summarizer.generate(**batch, max_length=256, num_beams=5, num_return_sequences=1, temperature=1.5)
        return tokenizer_summarizer.batch_decode(gen_out, skip_special_tokens=True)
        
    def llama2_response(self,query):
        prompt =f""" 
        Your are  an AI chatbot specializing in biological anti-aging research. you are responsible for  analyzing and identifying anti-aging interventions, providing insights into aging mechanisms, explaining lifestyle impacts, offering advice on longevity, conducting extensive research, staying up-to-date with latest findings, and engaging users with clear and empathetic communication in the field of healthy aging and longevity.
        Be sure to keep the conversation engaging and empathetic, understanding the user's concerns and addressing them with kindness and clarity, to serve as a trustworthy and reliable resource in the exciting journey of exploring biological anti-aging research.
        Answer below question in more comprehensive way
        {query}
        """
        llama2 = Replicate(model="replicate/llama-2-70b-chat:58d078176e02c219e11eb4da5a02a7830a283b14cf8f94537af893ccff5ee781",
                  input={"temperature": 0.75, "max_length": 4000, "top_p": 1},)
        return llama2(prompt)

    
    def research_response(self, query,memory,model):
        self.papers_df = self.rerank(query = query)
        self.papers_df["tldr"]  = self.papers_df["title_abs"].apply(self.summarize_response) 
        self.papers_df.tldr = self.papers_df.tldr.apply(lambda x :x[0])
        prompt = self.generate_prompt(query, self.papers_df, k = 8)
        chat_chain = LLMChain(
                llm=model,
                prompt=prompt,
                verbose=True,
                memory=memory,
            )
        response = chat_chain.run({"user_input": query})
        answer = response.replace('\n','<br/>')
        return {"research_response":answer}

    def answer_from_research_n_llama2(self,query):
        llama2_response = self.llama2_response(query)
        research_response = self.research_response(query)
        final_answer = self.summarize_response(llama2_response + "   " + research_response)
        return {"answer": final_answer}